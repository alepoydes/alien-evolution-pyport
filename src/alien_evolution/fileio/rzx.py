from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator
import zlib

from ..zx.runtime import FrameInput

_RZX_MAGIC = b"RZX!"
_RZX_HEADER_SIZE = 10
_RZX_BLOCK_ID_INPUT_RECORDING = 0x80
_RZX_INPUT_BLOCK_MIN_LEN = 18
_RZX_INPUT_FLAG_COMPRESSED = 0x00000002

_KEYBOARD_ROWS_STANDARD: tuple[tuple[str, str, str, str, str], ...] = (
    ("CAPS SHIFT", "Z", "X", "C", "V"),
    ("A", "S", "D", "F", "G"),
    ("Q", "W", "E", "R", "T"),
    ("1", "2", "3", "4", "5"),
    ("0", "9", "8", "7", "6"),
    ("P", "O", "I", "U", "Y"),
    ("ENTER", "L", "K", "J", "H"),
    ("SPACE", "SYMBOL SHIFT", "M", "N", "B"),
)


def _u16_le(data: bytes | bytearray | memoryview, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 2], "little")


def _u32_le(data: bytes | bytearray | memoryview, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 4], "little")


@dataclass(frozen=True, slots=True)
class RZXFrameControls:
    """Decoded control state for one RZX frame."""

    frame_index: int
    fetch_counter: int
    joy_kempston: int
    keyboard_rows: tuple[int, ...]
    pressed_keys: tuple[str, ...]
    port_readings: bytes

    def to_frame_input(self) -> FrameInput:
        return FrameInput(
            joy_kempston=self.joy_kempston,
            keyboard_rows=self.keyboard_rows,
        )


@dataclass(frozen=True, slots=True)
class _FrameRecord:
    fetch_counter: int
    port_readings: bytes


class RZXFrameInputIterator:
    """Iterate per-frame controls decoded from an RZX file.

    Notes
    - RZX stores only values returned by IN operations; it does not store port
      numbers. Therefore key decoding is heuristic:
      - values with high bits clear (`value & 0xE0 == 0`) are treated as
        Kempston samples,
      - values with high bits set (`value & 0xE0 == 0xE0`) are treated as
        keyboard-row reads in scan order.
    - `keyboard_rows` is reconstructed from sampled keyboard-row values in scan
      order (heuristic, because RZX does not store port numbers).
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._frames = self._read_rzx_frames(self.path)
        self._cursor = 0

    def __iter__(self) -> RZXFrameInputIterator:
        return self

    def __next__(self) -> RZXFrameControls:
        if self._cursor >= len(self._frames):
            raise StopIteration
        frame_index = self._cursor
        record = self._frames[frame_index]
        self._cursor += 1
        return self._decode_controls(
            frame_index=frame_index,
            fetch_counter=record.fetch_counter,
            readings=record.port_readings,
        )

    def __len__(self) -> int:
        return len(self._frames)

    def reset(self) -> None:
        self._cursor = 0

    def iter_frame_inputs(self) -> Iterator[FrameInput]:
        for i, record in enumerate(self._frames):
            yield self._decode_controls(
                frame_index=i,
                fetch_counter=record.fetch_counter,
                readings=record.port_readings,
            ).to_frame_input()

    @staticmethod
    def _read_rzx_frames(path: Path) -> list[_FrameRecord]:
        if not path.exists():
            raise FileNotFoundError(f"RZX file not found: {path}")
        raw = path.read_bytes()
        if len(raw) < _RZX_HEADER_SIZE or raw[:4] != _RZX_MAGIC:
            raise ValueError(f"Not an RZX file: {path}")

        frames: list[_FrameRecord] = []
        cursor = _RZX_HEADER_SIZE
        block_index = 0

        while cursor < len(raw):
            if cursor + 5 > len(raw):
                raise ValueError(f"Truncated RZX block header at offset {cursor}")

            block_id = raw[cursor]
            block_len = _u32_le(raw, cursor + 1)
            if block_len < 5:
                raise ValueError(f"Invalid RZX block length {block_len} at offset {cursor}")
            block_end = cursor + block_len
            if block_end > len(raw):
                raise ValueError(
                    f"RZX block at offset {cursor} exceeds file size: "
                    f"end={block_end}, size={len(raw)}"
                )

            if block_id == _RZX_BLOCK_ID_INPUT_RECORDING:
                frames.extend(
                    RZXFrameInputIterator._parse_input_block(
                        block=raw[cursor:block_end],
                        block_index=block_index,
                    )
                )

            cursor = block_end
            block_index += 1

        return frames

    @staticmethod
    def _parse_input_block(*, block: bytes, block_index: int) -> list[_FrameRecord]:
        if len(block) < _RZX_INPUT_BLOCK_MIN_LEN:
            raise ValueError(
                f"Input recording block #{block_index} too short: {len(block)} bytes"
            )

        num_frames = _u32_le(block, 5)
        flags = _u32_le(block, 14)
        frames_data = block[18:]
        if flags & _RZX_INPUT_FLAG_COMPRESSED:
            try:
                frames_data = zlib.decompress(frames_data)
            except zlib.error as exc:
                raise ValueError(
                    f"Failed to decompress RZX input block #{block_index}: {exc}"
                ) from exc

        records: list[_FrameRecord] = []
        j = 0
        prev_start = 0
        prev_end = 0

        for frame_idx in range(num_frames):
            if j + 4 > len(frames_data):
                raise ValueError(
                    f"Frame table truncated in input block #{block_index}: "
                    f"frame={frame_idx}, offset={j}, size={len(frames_data)}"
                )

            fetch_counter = _u16_le(frames_data, j)
            in_counter = _u16_le(frames_data, j + 2)

            if in_counter == 0xFFFF:
                start = prev_start
                end = prev_end
                j += 4
            else:
                start = j + 4
                end = start + in_counter
                if end > len(frames_data):
                    raise ValueError(
                        f"Frame payload truncated in input block #{block_index}: "
                        f"frame={frame_idx}, end={end}, size={len(frames_data)}"
                    )
                j = end
                prev_start = start
                prev_end = end

            records.append(
                _FrameRecord(
                    fetch_counter=fetch_counter,
                    port_readings=bytes(frames_data[start:end]),
                )
            )

        return records

    @staticmethod
    def _decode_controls(
        frame_index: int,
        fetch_counter: int,
        readings: bytes,
    ) -> RZXFrameControls:
        joy_samples: list[int] = []
        keyboard_samples: list[int] = []

        for value in readings:
            if (value & 0xE0) == 0x00:
                joy_samples.append(value & 0x1F)
            elif (value & 0xE0) == 0xE0:
                keyboard_samples.append(value)

        joy_kempston = joy_samples[-1] if joy_samples else 0
        keyboard_rows = RZXFrameInputIterator._decode_keyboard_rows(keyboard_samples)
        pressed_keys = RZXFrameInputIterator._decode_pressed_keys(keyboard_rows)

        return RZXFrameControls(
            frame_index=frame_index,
            fetch_counter=fetch_counter,
            joy_kempston=joy_kempston,
            keyboard_rows=keyboard_rows,
            pressed_keys=pressed_keys,
            port_readings=readings,
        )

    @staticmethod
    def _decode_keyboard_rows(keyboard_samples: list[int]) -> tuple[int, ...]:
        rows = [0xFF] * len(_KEYBOARD_ROWS_STANDARD)
        for row_index, row_value in enumerate(keyboard_samples[: len(_KEYBOARD_ROWS_STANDARD)]):
            rows[row_index] = row_value & 0xFF
        return tuple(rows)

    @staticmethod
    def _decode_pressed_keys(keyboard_rows: tuple[int, ...]) -> tuple[str, ...]:
        pressed: list[str] = []
        for row_index, row_value in enumerate(keyboard_rows[: len(_KEYBOARD_ROWS_STANDARD)]):
            row_keys = _KEYBOARD_ROWS_STANDARD[row_index]
            for bit_index, key_name in enumerate(row_keys):
                if (row_value & (1 << bit_index)) == 0:
                    pressed.append(key_name)
        return tuple(pressed)
