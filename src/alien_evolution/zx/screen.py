from __future__ import annotations

ZX_SCREEN_W = 256
ZX_SCREEN_H = 192

ZX_COLS = 32
ZX_ROWS = 24

ZX_BITMAP_BYTES = 6144
ZX_ATTR_BYTES = 768

# ZX attribute byte layout:
# bit7 FLASH
# bit6 BRIGHT
# bits5..3 PAPER
# bits2..0 INK

# A conventional 16-color ZX palette approximation (backend-independent values).
# Index mapping: 0..7 normal, 8..15 bright.
ZX_PALETTE_16 = [
    0x000000,  # 0 black
    0x0000D7,  # 1 blue
    0xD70000,  # 2 red
    0xD700D7,  # 3 magenta
    0x00D700,  # 4 green
    0x00D7D7,  # 5 cyan
    0xD7D700,  # 6 yellow
    0xD7D7D7,  # 7 white
    0x000000,  # 8 bright black (kept black)
    0x0000FF,  # 9 bright blue
    0xFF0000,  # 10 bright red
    0xFF00FF,  # 11 bright magenta
    0x00FF00,  # 12 bright green
    0x00FFFF,  # 13 bright cyan
    0xFFFF00,  # 14 bright yellow
    0xFFFFFF,  # 15 bright white
]


def new_zx_screen_buffers() -> tuple[bytearray, bytearray]:
    """Return (bitmap, attr) buffers in *ZX screen memory order*.

    - bitmap: 6144 bytes (same layout as 0x4000..0x57FF on a 48K Spectrum)
    - attr:   768 bytes (same layout as 0x5800..0x5AFF)
    """
    return bytearray(ZX_BITMAP_BYTES), bytearray(ZX_ATTR_BYTES)


# -----------------------------------------------------------------------------
# ZX screen address mapping (bitmap only)
# -----------------------------------------------------------------------------

def zx_bitmap_index(x_byte: int, y: int) -> int:
    """Index in a 6144-byte ZX bitmap buffer for (x_byte 0..31, y 0..191)."""
    x_byte &= 31
    y %= 192
    # Address formula, relative to 0x4000.
    return (((y & 0xC0) << 5) | ((y & 0x07) << 8) | ((y & 0x38) << 2) | x_byte)


def zx_attr_index(x_byte: int, y: int) -> int:
    """Index in a 768-byte ZX attribute buffer for (x_byte 0..31, y 0..191)."""
    x_byte &= 31
    y %= 192
    return ((y >> 3) * 32) + x_byte
