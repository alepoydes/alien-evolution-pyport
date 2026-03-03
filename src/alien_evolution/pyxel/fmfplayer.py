from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path
import warnings

from ..fileio.fmf import FMFScreenFrame, FMFScreenReader, FMFTruncatedWarning
from ..zx.screen import ZX_SCREEN_H, ZX_SCREEN_W
from .screen import apply_zx_palette, blit_zx_screen_to_pyxel


def _positive_int(raw: str) -> int:
    try:
        value = int(raw)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid integer value: {raw!r}") from exc
    if value <= 0:
        raise argparse.ArgumentTypeError("value must be > 0")
    return value


def _non_negative_int(raw: str) -> int:
    try:
        value = int(raw)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid integer value: {raw!r}") from exc
    if value < 0:
        raise argparse.ArgumentTypeError("value must be >= 0")
    return value


def run_fmf_player(
    path: str | Path,
    *,
    fps: int = 50,
    display_scale: int = 2,
    margin_x: int = 32,
    margin_y: int = 24,
    loop: bool = False,
    title: str | None = None,
) -> None:
    """Play an FMF screen recording in a Pyxel window."""
    reader = FMFScreenReader(path)
    frame_count = len(reader)
    if frame_count == 0:
        warnings.warn(
            f"{path}: no complete frames available; playback skipped",
            FMFTruncatedWarning,
            stacklevel=2,
        )
        return

    import pyxel

    reader.reset()
    current_frame: FMFScreenFrame = next(reader)
    frame_index = 0
    paused = False

    window_w = ZX_SCREEN_W + margin_x * 2
    window_h = ZX_SCREEN_H + margin_y * 2
    window_title = title or f"FMF Player: {Path(path).name}"

    def _advance_one_frame() -> None:
        nonlocal current_frame, frame_index
        try:
            current_frame = next(reader)
            frame_index += 1
        except StopIteration:
            if not loop:
                return
            reader.reset()
            current_frame = next(reader)
            frame_index = 0

    def _update() -> None:
        nonlocal paused
        if pyxel.btnp(pyxel.KEY_SPACE):
            paused = not paused
        if pyxel.btnp(pyxel.KEY_RIGHT):
            paused = True
            _advance_one_frame()
            return
        if paused:
            return
        _advance_one_frame()

    def _draw() -> None:
        blit_zx_screen_to_pyxel(
            current_frame.screen_bitmap,
            current_frame.screen_attrs,
            x=margin_x,
            y=margin_y,
            border=0,
            flash_phase=(frame_index // 32) & 1,
            method="auto",
        )
        pyxel.text(
            2,
            2,
            f"frame {frame_index + 1}/{frame_count} {'PAUSED' if paused else ''}",
            7,
        )

    pyxel.init(
        window_w,
        window_h,
        title=window_title,
        fps=fps,
        display_scale=display_scale,
    )
    apply_zx_palette()
    pyxel.run(_update, _draw)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fmf-player",
        description="Play FMF screen recording in a Pyxel window.",
    )
    parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help="Input FMF file.",
    )
    parser.add_argument(
        "--fps",
        type=_positive_int,
        default=50,
        help="Playback FPS (default: 50).",
    )
    parser.add_argument(
        "--display-scale",
        type=_positive_int,
        default=2,
        help="Pyxel display scale (default: 2).",
    )
    parser.add_argument(
        "--margin-x",
        type=_non_negative_int,
        default=32,
        help="Horizontal border size in pixels (default: 32).",
    )
    parser.add_argument(
        "--margin-y",
        type=_non_negative_int,
        default=24,
        help="Vertical border size in pixels (default: 24).",
    )
    parser.add_argument(
        "--loop",
        action="store_true",
        help="Loop playback.",
    )
    parser.add_argument(
        "--title",
        default=None,
        help="Window title override.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    run_fmf_player(
        args.input,
        fps=args.fps,
        display_scale=args.display_scale,
        margin_x=args.margin_x,
        margin_y=args.margin_y,
        loop=args.loop,
        title=args.title,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
