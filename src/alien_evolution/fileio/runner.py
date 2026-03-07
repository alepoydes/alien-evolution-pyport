from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Protocol, TextIO

from .rzx import RZXFrameInputIterator
from ..zx.runtime import AudioEvent, AudioNoteEvent, AudioResetEvent, FrameInput, FrameStepRuntime, StepOutput

_FILEIO_FORMAT = "alien-evolution-fileio-v2"


class ScreenFrameWriter(Protocol):
    """Minimal protocol for sinks that consume rendered screen frames."""

    def write_frame(self, screen_bitmap: bytes | bytearray, screen_attrs: bytes | bytearray) -> None:
        ...


def _parse_frame_input_record(obj: object, *, source: str) -> FrameInput:
    if not isinstance(obj, dict):
        raise ValueError(f"{source}: frame input record must be an object")

    raw_joy = obj.get("joy_kempston", 0)
    if not isinstance(raw_joy, int):
        raise ValueError(f"{source}: joy_kempston must be an integer")

    raw_rows = obj.get("keyboard_rows")
    if raw_rows is None:
        raise ValueError(f"{source}: keyboard_rows is required and must contain 8 integers")
    if not isinstance(raw_rows, (list, tuple)):
        raise ValueError(f"{source}: keyboard_rows must be an array of 8 integers")
    if len(raw_rows) != 8:
        raise ValueError(f"{source}: keyboard_rows must contain exactly 8 integers")

    vals: list[int] = []
    for idx, row in enumerate(raw_rows):
        if not isinstance(row, int):
            raise ValueError(f"{source}: keyboard_rows[{idx}] must be an integer")
        vals.append(row & 0xFF)

    return FrameInput(
        joy_kempston=raw_joy & 0x1F,
        keyboard_rows=tuple(vals),
    )


def iter_jsonl_frame_inputs_from_stream(stream: TextIO, *, source: str) -> Iterator[FrameInput]:
    """Yield frame inputs from a JSONL stream line-by-line."""

    for line_no, line in enumerate(stream, start=1):
        payload = line.strip()
        if not payload or payload.startswith("#"):
            continue
        if payload.startswith("["):
            raise ValueError(
                f"{source}:{line_no}: JSON arrays are not supported; use one JSON object per line",
            )
        obj = json.loads(payload)
        yield _parse_frame_input_record(obj, source=f"{source}:{line_no}")


def iter_jsonl_frame_inputs_from_path(path: Path) -> Iterator[FrameInput]:
    """Yield frame inputs from a JSONL file lazily."""

    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        yield from iter_jsonl_frame_inputs_from_stream(f, source=str(path))


def iter_rzx_frame_inputs(path: Path) -> Iterator[FrameInput]:
    """Yield frame inputs from an RZX recording."""

    return RZXFrameInputIterator(path).iter_frame_inputs()


def load_frame_inputs(path: Path | None) -> list[FrameInput]:
    """Compatibility helper: load JSONL input into a list."""

    if path is None:
        return []
    return list(iter_jsonl_frame_inputs_from_path(path))


def _audio_to_dict(event: AudioEvent) -> dict[str, object]:
    if isinstance(event, AudioNoteEvent):
        return {
            "type": "note",
            "epoch_id": event.epoch_id,
            "start_tick": event.start_tick,
            "duration_ticks": event.duration_ticks,
            "waveform": event.waveform,
            "freq_hz": event.freq_hz,
            "volume": event.volume,
            "source": event.source,
            "priority": event.priority,
        }
    if isinstance(event, AudioResetEvent):
        return {
            "type": "reset",
            "epoch_id": event.epoch_id,
            "cut_tick": event.cut_tick,
            "next_epoch_id": event.next_epoch_id,
        }
    raise TypeError(f"Unsupported audio event: {type(event)!r}")


def _step_output_to_dict(output: StepOutput) -> dict[str, object]:
    delay_after_step_frames = max(0, int(output.timing.delay_after_step_frames))
    return {
        "border_color": output.border_color & 0x07,
        "flash_phase": output.flash_phase & 0x01,
        "screen_bitmap_hex": bytes(output.screen_bitmap).hex(),
        "screen_attrs_hex": bytes(output.screen_attrs).hex(),
        "audio_events": [_audio_to_dict(event) for event in output.audio_events],
        "timing": {
            "delay_after_step_frames": delay_after_step_frames,
        },
    }


def _delay_after_step_frames(output: StepOutput) -> int:
    return max(0, int(output.timing.delay_after_step_frames))


def _advance_runtime_host_frame(runtime: FrameStepRuntime) -> None:
    advance = getattr(runtime, "advance_host_frame", None)
    if callable(advance):
        advance()
        return
    raise RuntimeError(
        "Runtime requested post-step delay but does not implement advance_host_frame()",
    )


def _apply_post_step_delay(runtime: FrameStepRuntime, delay_after_step_frames: int) -> None:
    delay = max(0, int(delay_after_step_frames))
    for _ in range(delay):
        _advance_runtime_host_frame(runtime)


def _write_jsonl_record(stream: TextIO, record: dict[str, object], *, flush: bool) -> None:
    stream.write(json.dumps(record, ensure_ascii=True) + "\n")
    if flush:
        stream.flush()


def run_frame_loop(
    runtime: FrameStepRuntime,
    *,
    frames: int | None,
    input_frames: Iterator[FrameInput] | None,
    input_source: str | None,
    jsonl_output: TextIO | None,
    flush_jsonl: bool = False,
    screen_output: ScreenFrameWriter | None = None,
    reset_runtime: bool = True,
) -> int:
    """Run frame-step runtime with streaming input and optional parallel outputs.

    Rules:
    - `frames is None` means "run until input iterator EOF".
    - if `frames` is set and input iterator ends early, neutral input is used.
    - `jsonl_output` and `screen_output` can be enabled simultaneously.
    """

    if frames is not None and frames < 0:
        raise ValueError(f"frames must be >= 0, got {frames}")

    if reset_runtime:
        runtime.reset()

    if jsonl_output is not None:
        header = {
            "type": "meta",
            "format": _FILEIO_FORMAT,
            "frames": frames,
            "input_source": input_source,
        }
        _write_jsonl_record(jsonl_output, header, flush=flush_jsonl)

    iterator = iter(input_frames) if input_frames is not None else None
    frame_idx = 0
    host_frame_index = 0

    while True:
        if frames is not None and frame_idx >= frames:
            break

        if iterator is None:
            if frames is None:
                break
            frame_input = FrameInput()
        else:
            try:
                frame_input = next(iterator)
            except StopIteration:
                if frames is None:
                    break
                frame_input = FrameInput()

        output = runtime.step(frame_input)
        delay_after_step_frames = _delay_after_step_frames(output)

        if jsonl_output is not None:
            frame_record = {
                "type": "frame",
                "index": frame_idx,
                "host_frame_index": host_frame_index,
                "input": {
                    "joy_kempston": frame_input.joy_kempston,
                    "keyboard_rows": list(frame_input.keyboard_rows),
                },
                "output": _step_output_to_dict(output),
            }
            _write_jsonl_record(jsonl_output, frame_record, flush=flush_jsonl)

        if screen_output is not None:
            screen_output.write_frame(output.screen_bitmap, output.screen_attrs)

        _apply_post_step_delay(runtime, delay_after_step_frames)
        host_frame_index += 1 + delay_after_step_frames
        frame_idx += 1

    return frame_idx
