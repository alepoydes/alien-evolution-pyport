from __future__ import annotations

from ..zx.screen import (
    ZX_SCREEN_H,
    ZX_BITMAP_BYTES,
    ZX_ATTR_BYTES,
    ZX_PALETTE_16,
    zx_bitmap_index,
)

from ..zx.config import ENABLE_RUNTIME_CHECKS

# Precompute run-length segments for all 8-bit patterns.
# Each entry is list[(start, length, bit)] where bit is 0/1 for paper/ink.
_BYTE_RUNS: list[list[tuple[int, int, int]]] = []
for b in range(256):
    runs: list[tuple[int, int, int]] = []
    cur = (b >> 7) & 1
    start = 0
    length = 1
    for i in range(1, 8):
        bit = (b >> (7 - i)) & 1
        if bit == cur:
            length += 1
        else:
            runs.append((start, length, cur))
            cur = bit
            start = i
            length = 1
    runs.append((start, length, cur))
    _BYTE_RUNS.append(runs)


# Precompute the base bitmap offset for each scanline so that
# index = _ROW_BASE[yy] + xb is equivalent to zx_bitmap_index(xb, yy)
# but avoids a Python function call in the hot loop.
_ROW_BASE: list[int] = [
    (((y & 0xC0) << 5) | ((y & 0x07) << 8) | ((y & 0x38) << 2))
    for y in range(ZX_SCREEN_H)
]


# Precompute ink/paper colors for every attribute byte for both flash phases.
# We pack the two colors into one int: (ink | (paper << 8)).
_ATTR_COLORS: tuple[list[int], list[int]] = ([0] * 256, [0] * 256)
for phase in (0, 1):
    slot = _ATTR_COLORS[phase]
    for a in range(256):
        ink = a & 0x07
        paper = (a >> 3) & 0x07
        bright = (a >> 6) & 1
        flash = (a >> 7) & 1
        if flash and phase:
            ink, paper = paper, ink
        # Inline the _zx_col mapping here so this table can be computed at
        # import time without depending on function definition order.
        ink_c = 0 if ink == 0 else (ink + (8 if bright else 0))
        pap_c = 0 if paper == 0 else (paper + (8 if bright else 0))
        slot[a] = ink_c | (pap_c << 8)


def apply_zx_palette(palette_16: list[int] | None = None) -> None:
    """Apply ZX-like 16-color palette to Pyxel."""
    import pyxel

    palette = list(palette_16 or ZX_PALETTE_16)
    pyxel.colors[: len(palette)] = palette


def _zx_col(ink_or_paper_0_7: int, bright: int) -> int:
    c = ink_or_paper_0_7 & 7
    if c == 0:
        return 0
    return c + (8 if (bright & 1) else 0)


def blit_zx_screen_to_pyxel(
    bitmap: bytearray | bytes,
    attrs: bytearray | bytes,
    *,
    x: int = 0,
    y: int = 0,
    border: int | None = None,
    flash_phase: int = 0,
    method: str = "rect",
) -> None:
    """Draw ZX bitmap+attribute buffers onto the current Pyxel frame."""
    import pyxel

    # Localize hot Pyxel callables to reduce attribute lookup overhead.
    rect = pyxel.rect
    pset = pyxel.pset
    cls = pyxel.cls

    if ENABLE_RUNTIME_CHECKS:
        if len(bitmap) != ZX_BITMAP_BYTES:
            raise ValueError(f"bitmap must be {ZX_BITMAP_BYTES} bytes")
        if len(attrs) != ZX_ATTR_BYTES:
            raise ValueError(f"attrs must be {ZX_ATTR_BYTES} bytes")

    if border is not None:
        cls(border & 0x0F)

    flash_phase &= 1

    if ENABLE_RUNTIME_CHECKS and method not in ("rect", "pset"):
        raise ValueError("method must be 'rect' or 'pset'")

    if method == "pset":
        # Keep the reference implementation for debugging (pixel-accurate but
        # very slow in Python).
        for yy in range(ZX_SCREEN_H):
            row_attr = (yy >> 3) * 32
            row_base = _ROW_BASE[yy]
            for xb in range(32):
                b = bitmap[row_base + xb]
                ap = _ATTR_COLORS[flash_phase][attrs[row_attr + xb]]
                ink_c = ap & 0xFF
                pap_c = (ap >> 8) & 0xFF
                x0 = x + (xb << 3)
                y0 = y + yy

                pset(x0 + 0, y0, ink_c if (b & 0x80) else pap_c)
                pset(x0 + 1, y0, ink_c if (b & 0x40) else pap_c)
                pset(x0 + 2, y0, ink_c if (b & 0x20) else pap_c)
                pset(x0 + 3, y0, ink_c if (b & 0x10) else pap_c)
                pset(x0 + 4, y0, ink_c if (b & 0x08) else pap_c)
                pset(x0 + 5, y0, ink_c if (b & 0x04) else pap_c)
                pset(x0 + 6, y0, ink_c if (b & 0x02) else pap_c)
                pset(x0 + 7, y0, ink_c if (b & 0x01) else pap_c)
        return

    for yy in range(ZX_SCREEN_H):
        row_attr = (yy >> 3) * 32
        row_base = _ROW_BASE[yy]
        y0 = y + yy

        # Merge adjacent segments of the same color across byte boundaries.
        # This can drastically reduce the number of Pyxel API calls on screens
        # with large solid areas (common in menus / borders / HUD).
        cur_x = None
        cur_w = 0
        cur_col = 0
        for xb in range(32):
            b = bitmap[row_base + xb]
            ap = _ATTR_COLORS[flash_phase][attrs[row_attr + xb]]
            ink_c = ap & 0xFF
            pap_c = (ap >> 8) & 0xFF
            x0 = x + (xb << 3)

            for start, length, bit in _BYTE_RUNS[b]:
                col = ink_c if bit else pap_c
                seg_x = x0 + start
                if cur_x is not None and col == cur_col and seg_x == (cur_x + cur_w):
                    cur_w += length
                else:
                    if cur_x is not None:
                        rect(cur_x, y0, cur_w, 1, cur_col)
                    cur_x = seg_x
                    cur_w = length
                    cur_col = col

        if cur_x is not None:
            rect(cur_x, y0, cur_w, 1, cur_col)
