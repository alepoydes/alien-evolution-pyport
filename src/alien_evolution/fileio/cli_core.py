from __future__ import annotations

import argparse
import sys
from collections.abc import Callable, Iterator, Sequence
from contextlib import ExitStack
from pathlib import Path
from typing import TextIO

from .fmf import FMFScreenWriter
from .runner import (
    iter_jsonl_frame_inputs_from_path,
    iter_jsonl_frame_inputs_from_stream,
    run_frame_loop,
)
from .rzx import RZXFrameInputIterator
from .stateio import load_runtime_state, save_runtime_state
from ..zx.runtime import FrameInput, FrameStepRuntime


RuntimeFactory = Callable[[], FrameStepRuntime]


def _non_negative_int(raw: str) -> int:
    try:
        value = int(raw)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid integer value: {raw!r}") from exc
    if value < 0:
        raise argparse.ArgumentTypeError("frames must be >= 0")
    return value


def _build_parser(*, prog: str, description: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog=prog, description=description)
    parser.add_argument(
        "--frames",
        type=_non_negative_int,
        default=None,
        help=(
            "Frame count. In RZX mode this is additional frames on top of recording length. "
            "In JSONL mode, omit to run until input EOF."
        ),
    )

    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument(
        "--input",
        type=str,
        default=None,
        help="Optional JSONL input source: file path or '-' for stdin.",
    )
    input_group.add_argument(
        "--input-rzx",
        type=Path,
        default=None,
        help="Optional RZX input recording path (file only).",
    )

    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Optional JSONL output target: file path or '-' for stdout.",
    )
    parser.add_argument(
        "--output-fmf",
        type=Path,
        default=None,
        help="Optional FMF output file path.",
    )
    parser.add_argument(
        "--load-state",
        type=Path,
        default=None,
        help="Optional runtime state JSON to load before frame loop.",
    )
    parser.add_argument(
        "--save-state",
        type=Path,
        default=None,
        help="Optional runtime state JSON to save after frame loop.",
    )
    return parser


def _validate_args(
    parser: argparse.ArgumentParser,
    args: argparse.Namespace,
    *,
    supports_fmf_output: bool,
) -> None:
    state_io_requested = args.load_state is not None or args.save_state is not None

    if args.output is None and args.output_fmf is None and not state_io_requested:
        parser.error("at least one of --output/--output-fmf/--load-state/--save-state is required")

    if args.input is not None and args.input.lower().endswith(".rzx"):
        parser.error("RZX input is no longer accepted via --input; use --input-rzx")

    if args.input_rzx is not None and str(args.input_rzx) == "-":
        parser.error("--input-rzx must be a file path; '-' is not supported")

    if args.output_fmf is not None:
        if str(args.output_fmf) == "-":
            parser.error("--output-fmf must be a file path; '-' is not supported")
        if not supports_fmf_output:
            parser.error("--output-fmf is not supported for this runtime")

    if args.output is not None and args.output.lower().endswith(".fmf"):
        parser.error("--output is JSONL-only; use --output-fmf for FMF output")

    if args.frames is None and args.input is None and args.input_rzx is None and not state_io_requested:
        parser.error("--frames is required when no input source is provided")


def _resolve_input_source(
    args: argparse.Namespace,
) -> tuple[Iterator[FrameInput] | None, str | None, int | None]:
    if args.input_rzx is not None:
        rzx_path = Path(args.input_rzx)
        rzx_iter = RZXFrameInputIterator(rzx_path)
        extra_frames = 0 if args.frames is None else args.frames
        total_frames = len(rzx_iter) + extra_frames
        return (rzx_iter.iter_frame_inputs(), str(rzx_path), total_frames)

    if args.input is None:
        return (None, None, args.frames)

    if args.input == "-":
        return (
            iter_jsonl_frame_inputs_from_stream(sys.stdin, source="stdin"),
            "stdin",
            args.frames,
        )

    input_path = Path(args.input)
    return (iter_jsonl_frame_inputs_from_path(input_path), str(input_path), args.frames)


def run_fileio_cli(
    *,
    argv: Sequence[str] | None,
    prog: str,
    description: str,
    runtime_factory: RuntimeFactory,
    supports_fmf_output: bool,
) -> int:
    """Run shared fileio CLI contract for a frame-step runtime."""

    parser = _build_parser(prog=prog, description=description)
    args = parser.parse_args(argv)
    _validate_args(parser, args, supports_fmf_output=supports_fmf_output)

    input_iter, input_source, total_frames = _resolve_input_source(args)
    has_state_io = args.load_state is not None or args.save_state is not None

    with ExitStack() as stack:
        jsonl_output: TextIO | None = None
        flush_jsonl = False
        if args.output is not None:
            if args.output == "-":
                jsonl_output = sys.stdout
                flush_jsonl = True
            else:
                jsonl_path = Path(args.output)
                jsonl_path.parent.mkdir(parents=True, exist_ok=True)
                jsonl_output = stack.enter_context(jsonl_path.open("w", encoding="utf-8"))

        screen_output = None
        if args.output_fmf is not None:
            fmf_path = Path(args.output_fmf)
            fmf_path.parent.mkdir(parents=True, exist_ok=True)
            screen_output = stack.enter_context(FMFScreenWriter(fmf_path))

        runtime = runtime_factory()
        runtime_name = type(runtime).__name__
        loaded_state = False
        if args.load_state is not None:
            load_runtime_state(runtime, Path(args.load_state))
            loaded_state = True

        should_run_loop = (
            total_frames is not None
            or input_iter is not None
            or jsonl_output is not None
            or screen_output is not None
        )
        if should_run_loop:
            executed_frames = run_frame_loop(
                runtime,
                frames=total_frames,
                input_frames=input_iter,
                input_source=input_source,
                jsonl_output=jsonl_output,
                flush_jsonl=flush_jsonl,
                screen_output=screen_output,
                reset_runtime=not loaded_state,
            )
        else:
            if not loaded_state:
                runtime.reset()
            executed_frames = 0

        if args.save_state is not None:
            save_runtime_state(runtime, Path(args.save_state))

    targets: list[str] = []
    if args.output is not None:
        targets.append("stdout(JSONL)" if args.output == "-" else str(Path(args.output)))
    if args.output_fmf is not None:
        targets.append(str(Path(args.output_fmf)))
    if args.save_state is not None:
        targets.append(str(Path(args.save_state)))
    if not targets and has_state_io:
        targets.append("state-only")

    print(
        f"{runtime_name} finished after {executed_frames} frame(s). "
        f"Output: {', '.join(targets)}",
        file=sys.stderr,
    )
    return 0
