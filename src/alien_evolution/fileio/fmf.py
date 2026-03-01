from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Iterator
import warnings
import zlib

from ..zx.screen import ZX_ATTR_BYTES, ZX_BITMAP_BYTES, zx_bitmap_index

_FMF_MAGIC_PREFIX = b"FMF_V1"
_FMF_MAGIC_LE = b"FMF_V1e"
_FMF_HEADER_SIZE = 16

_FMF_BLOCK_SCREEN = 0x24  # '$'
_FMF_BLOCK_SOUND = 0x53  # 'S'
_FMF_BLOCK_NEW_FRAME = 0x4E  # 'N'
_FMF_BLOCK_END = 0x58  # 'X'
_FMF_KNOWN_BLOCK_IDS = (
    _FMF_BLOCK_SCREEN,
    _FMF_BLOCK_SOUND,
    _FMF_BLOCK_NEW_FRAME,
    _FMF_BLOCK_END,
)

_FMF_SCREEN_STANDARD = "$"
_FMF_FRAME_TYPE_DEFAULT = "A"
_FMF_SOUND_TYPE_DEFAULT = "U"
_FMF_SOUND_CHANNELS_DEFAULT = "M"

_ACTIVE_X0 = 4
_ACTIVE_Y0 = 24
_ACTIVE_W = 32
_ACTIVE_H = 192
_ACTIVE_Y_CHAR0 = _ACTIVE_Y0 // 8
_ACTIVE_H_CHAR = _ACTIVE_H // 8


class FMFTruncatedWarning(UserWarning):
    """Warning emitted when an FMF stream appears truncated."""


def _require_char(name: str, value: str) -> str:
    if len(value) != 1:
        raise ValueError(f"{name} must be a single character")
    return value


def _u16(data: bytes, offset: int, *, little_endian: bool) -> int:
    return int.from_bytes(
        data[offset : offset + 2],
        "little" if little_endian else "big",
    )


def _pack_u16(value: int, *, little_endian: bool) -> bytes:
    return int(value & 0xFFFF).to_bytes(
        2,
        "little" if little_endian else "big",
    )


def _slice_attr_rows(y: int, height: int) -> int:
    start_row = y // 8
    end_row = (y + height - 1) // 8
    return end_row - start_row + 1


def _encode_rle(payload: bytes) -> bytes:
    """Encode FMF slice payload.

    FMF uses a simple RLE where any pair of equal bytes is followed by a count
    of additional repeats (0..255). So:
    - `cc\\x00` means exactly two `c` bytes,
    - `cc\\x03` means five `c` bytes.
    """

    encoded = bytearray()
    i = 0
    n = len(payload)

    while i < n:
        value = payload[i]
        run = 1
        while i + run < n and payload[i + run] == value and run < 257:
            run += 1

        if run == 1:
            encoded.append(value)
        else:
            encoded.extend((value, value, run - 2))

        i += run

    return bytes(encoded)


def _decode_rle(data: bytes, offset: int, expected_len: int) -> tuple[bytes, int]:
    decoded = bytearray()
    prev_literal: int | None = None
    i = offset

    while len(decoded) < expected_len:
        if i >= len(data):
            raise ValueError(
                "Unexpected end of FMF slice payload while decoding RLE data"
            )

        value = data[i]
        i += 1
        decoded.append(value)

        if prev_literal is not None and prev_literal == value:
            if i >= len(data):
                raise ValueError("Missing RLE repeat counter in FMF slice payload")
            repeat_count = data[i]
            i += 1
            if len(decoded) + repeat_count > expected_len:
                raise ValueError(
                    "RLE payload overrun while decoding FMF slice data"
                )
            if repeat_count:
                decoded.extend([value] * repeat_count)
            prev_literal = None
        else:
            prev_literal = value

    return bytes(decoded), i


@dataclass(frozen=True, slots=True)
class FMFScreenFrame:
    """One reconstructed ZX frame as (bitmap, attrs)."""

    screen_bitmap: bytes
    screen_attrs: bytes

    def __post_init__(self) -> None:
        if len(self.screen_bitmap) != ZX_BITMAP_BYTES:
            raise ValueError(
                f"screen_bitmap must be {ZX_BITMAP_BYTES} bytes, got {len(self.screen_bitmap)}"
            )
        if len(self.screen_attrs) != ZX_ATTR_BYTES:
            raise ValueError(
                f"screen_attrs must be {ZX_ATTR_BYTES} bytes, got {len(self.screen_attrs)}"
            )

    def as_bytes(self) -> bytes:
        return self.screen_bitmap + self.screen_attrs


class FMFScreenWriter:
    """Write ZX frames to FMF_V1e movie file.

    This writer records only the standard Spectrum display area and stores each
    frame as one full `$` slice (x=4, y=24, w=32, h=192), followed by an `N`
    frame separator block. `X` is written on close.
    """

    def __init__(
        self,
        path: str | Path,
        *,
        frame_rate_divider: int = 1,
        frame_type: str = _FMF_FRAME_TYPE_DEFAULT,
        sound_type: str = _FMF_SOUND_TYPE_DEFAULT,
        sound_frequency: int = 0,
        sound_channels: str = _FMF_SOUND_CHANNELS_DEFAULT,
        compression: bool = False,
    ) -> None:
        if not (0 <= frame_rate_divider <= 255):
            raise ValueError("frame_rate_divider must be in range 0..255")
        _require_char("frame_type", frame_type)
        _require_char("sound_type", sound_type)
        _require_char("sound_channels", sound_channels)
        if not (0 <= sound_frequency <= 0xFFFF):
            raise ValueError("sound_frequency must be in range 0..65535")

        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._stream: BinaryIO = self.path.open("wb")
        self._compression = bool(compression)
        self._compressor = zlib.compressobj(level=9) if self._compression else None
        self._closed = False

        self._frame_rate_divider = frame_rate_divider & 0xFF
        self._frame_type = frame_type
        self._sound_type = sound_type
        self._sound_frequency = int(sound_frequency)
        self._sound_channels = sound_channels

        self.frames_written = 0
        self._write_header()

    def __enter__(self) -> FMFScreenWriter:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()

    def write_frame(
        self,
        screen_bitmap: bytes | bytearray,
        screen_attrs: bytes | bytearray,
    ) -> None:
        if self._closed:
            raise RuntimeError("Cannot write frame: FMFScreenWriter is closed")

        frame = FMFScreenFrame(bytes(screen_bitmap), bytes(screen_attrs))
        self._write_block(self._build_screen_block(frame))
        self._write_block(self._build_new_frame_block())
        self.frames_written += 1

    def close(self) -> None:
        if self._closed:
            return
        try:
            self._write_block(bytes((_FMF_BLOCK_END,)))
            if self._compressor is not None:
                tail = self._compressor.flush()
                if tail:
                    self._stream.write(tail)
        finally:
            self._closed = True
            self._stream.close()

    def _write_header(self) -> None:
        header = bytearray()
        header.extend(_FMF_MAGIC_LE)
        header.append(ord("Z" if self._compression else "U"))
        header.append(self._frame_rate_divider)
        header.append(ord(_FMF_SCREEN_STANDARD))
        header.append(ord(self._frame_type))
        header.append(ord(self._sound_type))
        header.extend(_pack_u16(self._sound_frequency, little_endian=True))
        header.append(ord(self._sound_channels))
        header.append(0x0A)

        if len(header) != _FMF_HEADER_SIZE:
            raise AssertionError(f"internal error: FMF header size is {len(header)}")

        self._stream.write(header)

    def _write_block(self, raw_block: bytes) -> None:
        if not raw_block:
            return
        if self._compressor is None:
            self._stream.write(raw_block)
            return
        chunk = self._compressor.compress(raw_block)
        if chunk:
            self._stream.write(chunk)

    def _build_new_frame_block(self) -> bytes:
        return bytes(
            (
                _FMF_BLOCK_NEW_FRAME,
                self._frame_rate_divider,
                ord(_FMF_SCREEN_STANDARD),
                ord(self._frame_type),
            )
        )

    @staticmethod
    def _build_screen_block(frame: FMFScreenFrame) -> bytes:
        bitmap_payload = bytearray(_ACTIVE_W * _ACTIVE_H)
        for y in range(_ACTIVE_H):
            row_offset = y * _ACTIVE_W
            for x in range(_ACTIVE_W):
                bitmap_payload[row_offset + x] = frame.screen_bitmap[zx_bitmap_index(x, y)]

        # FMF non-HiRes '$' stores one attribute byte per 8-pixel run on each scanline.
        attr_payload = bytearray(_ACTIVE_W * _ACTIVE_H)
        for y in range(_ACTIVE_H):
            src_offset = (y // 8) * _ACTIVE_W
            dst_offset = y * _ACTIVE_W
            attr_payload[dst_offset : dst_offset + _ACTIVE_W] = frame.screen_attrs[
                src_offset : src_offset + _ACTIVE_W
            ]

        encoded_bitmap = _encode_rle(bytes(bitmap_payload))
        encoded_attrs = _encode_rle(bytes(attr_payload))

        block = bytearray()
        block.append(_FMF_BLOCK_SCREEN)
        block.append(_ACTIVE_X0)
        block.extend(_pack_u16(_ACTIVE_Y0, little_endian=True))
        block.append(_ACTIVE_W)
        block.extend(_pack_u16(_ACTIVE_H, little_endian=True))
        block.extend(encoded_bitmap)
        block.extend(encoded_attrs)
        return bytes(block)


class FMFScreenReader:
    """Iterate ZX frames reconstructed from FMF_V1e file."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._frames = self._read_frames(self.path)
        self._cursor = 0

    def __iter__(self) -> FMFScreenReader:
        return self

    def __next__(self) -> FMFScreenFrame:
        if self._cursor >= len(self._frames):
            raise StopIteration
        frame = self._frames[self._cursor]
        self._cursor += 1
        return frame

    def __len__(self) -> int:
        return len(self._frames)

    def reset(self) -> None:
        self._cursor = 0

    def iter_frames(self) -> Iterator[FMFScreenFrame]:
        return iter(self._frames)

    @staticmethod
    def _read_frames(path: Path) -> list[FMFScreenFrame]:
        if not path.exists():
            raise FileNotFoundError(f"FMF file not found: {path}")

        raw = path.read_bytes()
        if len(raw) < _FMF_HEADER_SIZE:
            raise ValueError(
                f"FMF file too short: expected at least {_FMF_HEADER_SIZE} bytes"
            )
        if not raw.startswith(_FMF_MAGIC_PREFIX):
            raise ValueError(f"Not an FMF_V1* file: {path}")

        endian_tag = chr(raw[6])
        if endian_tag not in ("e", "E"):
            raise ValueError(f"Unsupported FMF endianness marker: {endian_tag!r}")
        little_endian = endian_tag == "e"

        compression_tag = chr(raw[7])
        compressed = compression_tag in ("Z", "z")

        header_screen_type = chr(raw[9])
        if header_screen_type != _FMF_SCREEN_STANDARD:
            raise ValueError(
                f"Unsupported FMF screen type {header_screen_type!r}; only '$' is supported"
            )
        current_screen_type = header_screen_type

        blocks = raw[_FMF_HEADER_SIZE:]
        if compressed:
            blocks = FMFScreenReader._decompress_blocks_tolerant(blocks, path=path)

        bitmap = bytearray(ZX_BITMAP_BYTES)
        attrs = bytearray(ZX_ATTR_BYTES)
        frames: list[FMFScreenFrame] = []

        i = 0
        have_any_screen_data = False
        frame_dirty_since_last_emit = False

        while i < len(blocks):
            block_id = blocks[i]
            i += 1

            if block_id == _FMF_BLOCK_SCREEN:
                if i + 6 > len(blocks):
                    FMFScreenReader._warn_truncated(
                        path=path,
                        detail="truncated FMF '$' block header",
                    )
                    break

                x = blocks[i]
                y = _u16(blocks, i + 1, little_endian=little_endian)
                width = blocks[i + 3]
                height = _u16(blocks, i + 4, little_endian=little_endian)
                i += 6

                if width == 0 or height == 0:
                    raise ValueError("Invalid FMF '$' block dimensions: zero width/height")

                attr_rows = _slice_attr_rows(y, height)
                try:
                    payload, i, attr_mode = FMFScreenReader._decode_screen_payload(
                        blocks,
                        i,
                        width=width,
                        height=height,
                        attr_rows=attr_rows,
                        screen_type=current_screen_type,
                    )
                except ValueError as exc:
                    FMFScreenReader._warn_truncated(
                        path=path,
                        detail=f"incomplete FMF '$' payload ({exc})",
                    )
                    break
                FMFScreenReader._apply_screen_slice(
                    bitmap=bitmap,
                    attrs=attrs,
                    x=x,
                    y=y,
                    width=width,
                    height=height,
                    attr_rows=attr_rows,
                    payload=payload,
                    attr_mode=attr_mode,
                )
                have_any_screen_data = True
                frame_dirty_since_last_emit = True
                continue

            if block_id == _FMF_BLOCK_NEW_FRAME:
                if i + 3 > len(blocks):
                    FMFScreenReader._warn_truncated(
                        path=path,
                        detail="truncated FMF 'N' block",
                    )
                    break
                # Byte layout: frame_rate_divider, screen_type, frame_type.
                screen_type = chr(blocks[i + 1])
                if screen_type != _FMF_SCREEN_STANDARD:
                    raise ValueError(
                        f"Unsupported FMF frame screen type {screen_type!r}; only '$' is supported"
                    )
                current_screen_type = screen_type
                i += 3

                if have_any_screen_data:
                    frames.append(
                        FMFScreenFrame(
                            screen_bitmap=bytes(bitmap),
                            screen_attrs=bytes(attrs),
                        )
                    )
                    frame_dirty_since_last_emit = False
                continue

            if block_id == _FMF_BLOCK_SOUND:
                # Sound block:
                # type(1), frequency(2), channels(1), length_frames_minus_1(2), data(...)
                if i + 6 > len(blocks):
                    FMFScreenReader._warn_truncated(
                        path=path,
                        detail="truncated FMF 'S' block header",
                    )
                    break
                sound_type = chr(blocks[i])
                sound_channels = chr(blocks[i + 3])
                sound_frames = _u16(blocks, i + 4, little_endian=little_endian) + 1
                i += 6
                try:
                    sound_len = sound_frames * FMFScreenReader._sound_frame_size(
                        sound_type,
                        sound_channels,
                    )
                except ValueError as exc:
                    raise ValueError(
                        f"Unsupported FMF sound format in 'S' block: {exc}"
                    ) from exc
                if i + sound_len > len(blocks):
                    FMFScreenReader._warn_truncated(
                        path=path,
                        detail="truncated FMF sound payload",
                    )
                    break
                i += sound_len
                continue

            if block_id == _FMF_BLOCK_END:
                if have_any_screen_data and frame_dirty_since_last_emit:
                    frames.append(
                        FMFScreenFrame(
                            screen_bitmap=bytes(bitmap),
                            screen_attrs=bytes(attrs),
                        )
                    )
                break

            raise ValueError(f"Unsupported FMF block id: 0x{block_id:02X}")

        return frames

    @staticmethod
    def _decode_screen_payload(
        blocks: bytes,
        offset: int,
        *,
        width: int,
        height: int,
        attr_rows: int,
        screen_type: str,
    ) -> tuple[bytes, int, str]:
        _ = attr_rows

        if screen_type in ("$", "C", "X"):
            planes = 2
            mode = "scanline"
        elif screen_type == "R":
            planes = 3
            mode = "scanline_hires"
        else:
            raise ValueError(f"Unsupported FMF screen type {screen_type!r}")

        plane_len = width * height
        next_offset = offset
        payload_parts: list[bytes] = []
        for _ in range(planes):
            part, next_offset = _decode_rle(blocks, next_offset, plane_len)
            payload_parts.append(part)
        payload = b"".join(payload_parts)
        if not FMFScreenReader._looks_like_next_block(blocks, next_offset):
            raise ValueError("screen payload did not end at a valid FMF block boundary")
        return payload, next_offset, mode

    @staticmethod
    def _looks_like_next_block(blocks: bytes, offset: int) -> bool:
        if offset >= len(blocks):
            return True
        return blocks[offset] in _FMF_KNOWN_BLOCK_IDS

    @staticmethod
    def _sound_frame_size(sound_type: str, sound_channels: str) -> int:
        encoding = sound_type.upper()
        channels = sound_channels.upper()

        if channels not in ("M", "S"):
            raise ValueError(f"unsupported channels marker {sound_channels!r}")

        if encoding in ("U", "A"):
            bytes_per_channel = 1
        elif encoding == "P":
            bytes_per_channel = 2
        else:
            raise ValueError(f"unsupported encoding marker {sound_type!r}")

        channel_count = 2 if channels == "S" else 1
        return bytes_per_channel * channel_count

    @staticmethod
    def _decompress_blocks_tolerant(data: bytes, *, path: Path) -> bytes:
        """Decompress FMF block stream, tolerating truncated compressed tail."""
        decomp = zlib.decompressobj()
        out = bytearray()
        chunk_size = 65536
        error: zlib.error | None = None

        for start in range(0, len(data), chunk_size):
            chunk = data[start : start + chunk_size]
            try:
                out.extend(decomp.decompress(chunk))
            except zlib.error as exc:
                error = exc
                break

        try:
            out.extend(decomp.flush())
        except zlib.error as exc:
            if error is None:
                error = exc

        if error is not None:
            FMFScreenReader._warn_truncated(
                path=path,
                detail=f"failed to fully decompress FMF stream ({error})",
            )
        elif not decomp.eof:
            FMFScreenReader._warn_truncated(
                path=path,
                detail="compressed FMF stream ended before end marker",
            )

        return bytes(out)

    @staticmethod
    def _warn_truncated(*, path: Path, detail: str) -> None:
        warnings.warn(
            f"{path}: {detail}; playback will continue with available frames",
            FMFTruncatedWarning,
            stacklevel=2,
        )

    @staticmethod
    def _apply_screen_slice(
        *,
        bitmap: bytearray,
        attrs: bytearray,
        x: int,
        y: int,
        width: int,
        height: int,
        attr_rows: int,
        payload: bytes,
        attr_mode: str,
    ) -> None:
        bitmap_len = width * height
        bitmap_payload = payload[:bitmap_len]
        attr_payload = payload[bitmap_len:]

        for dy in range(height):
            sy = y + dy
            if sy < _ACTIVE_Y0 or sy >= (_ACTIVE_Y0 + _ACTIVE_H):
                continue
            target_y = sy - _ACTIVE_Y0
            row_offset = dy * width
            for dx in range(width):
                sx = x + dx
                if sx < _ACTIVE_X0 or sx >= (_ACTIVE_X0 + _ACTIVE_W):
                    continue
                target_x = sx - _ACTIVE_X0
                bitmap[zx_bitmap_index(target_x, target_y)] = bitmap_payload[
                    row_offset + dx
                ]

        if attr_mode == "scanline":
            for dy in range(height):
                sy = y + dy
                if sy < _ACTIVE_Y0 or sy >= (_ACTIVE_Y0 + _ACTIVE_H):
                    continue
                target_y = sy - _ACTIVE_Y0
                target_attr_row = target_y // 8
                row_offset = dy * width
                for dx in range(width):
                    sx = x + dx
                    if sx < _ACTIVE_X0 or sx >= (_ACTIVE_X0 + _ACTIVE_W):
                        continue
                    target_x = sx - _ACTIVE_X0
                    attrs[(target_attr_row * _ACTIVE_W) + target_x] = attr_payload[
                        row_offset + dx
                    ]
            return

        if attr_mode == "char_rows":
            attr_row_start = y // 8
            for row in range(attr_rows):
                sy_char = attr_row_start + row
                if sy_char < _ACTIVE_Y_CHAR0 or sy_char >= (
                    _ACTIVE_Y_CHAR0 + _ACTIVE_H_CHAR
                ):
                    continue
                target_attr_row = sy_char - _ACTIVE_Y_CHAR0
                row_offset = row * width
                for dx in range(width):
                    sx = x + dx
                    if sx < _ACTIVE_X0 or sx >= (_ACTIVE_X0 + _ACTIVE_W):
                        continue
                    target_x = sx - _ACTIVE_X0
                    attrs[(target_attr_row * _ACTIVE_W) + target_x] = attr_payload[
                        row_offset + dx
                    ]
            return

        raise ValueError(f"internal error: unknown FMF attribute mode {attr_mode!r}")
