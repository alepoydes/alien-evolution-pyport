from __future__ import annotations

from ..zx.screen import (
    ZX_SCREEN_H,
    ZX_BITMAP_BYTES,
    ZX_ATTR_BYTES,
    ZX_PALETTE_16,
    zx_bitmap_index,
)

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

    if len(bitmap) != ZX_BITMAP_BYTES:
        raise ValueError(f"bitmap must be {ZX_BITMAP_BYTES} bytes")
    if len(attrs) != ZX_ATTR_BYTES:
        raise ValueError(f"attrs must be {ZX_ATTR_BYTES} bytes")

    if border is not None:
        pyxel.cls(border & 0x0F)

    flash_phase &= 1

    if method not in ("rect", "pset"):
        raise ValueError("method must be 'rect' or 'pset'")

    if method == "pset":
        for yy in range(ZX_SCREEN_H):
            row_attr = (yy >> 3) * 32
            for xb in range(32):
                b = bitmap[zx_bitmap_index(xb, yy)]
                a = attrs[row_attr + xb]

                ink = a & 0x07
                paper = (a >> 3) & 0x07
                bright = (a >> 6) & 1
                flash = (a >> 7) & 1

                if flash and flash_phase:
                    ink, paper = paper, ink

                ink_c = _zx_col(ink, bright)
                pap_c = _zx_col(paper, bright)
                x0 = x + (xb << 3)
                y0 = y + yy

                pyxel.pset(x0 + 0, y0, ink_c if (b & 0x80) else pap_c)
                pyxel.pset(x0 + 1, y0, ink_c if (b & 0x40) else pap_c)
                pyxel.pset(x0 + 2, y0, ink_c if (b & 0x20) else pap_c)
                pyxel.pset(x0 + 3, y0, ink_c if (b & 0x10) else pap_c)
                pyxel.pset(x0 + 4, y0, ink_c if (b & 0x08) else pap_c)
                pyxel.pset(x0 + 5, y0, ink_c if (b & 0x04) else pap_c)
                pyxel.pset(x0 + 6, y0, ink_c if (b & 0x02) else pap_c)
                pyxel.pset(x0 + 7, y0, ink_c if (b & 0x01) else pap_c)
        return

    for yy in range(ZX_SCREEN_H):
        row_attr = (yy >> 3) * 32
        y0 = y + yy
        for xb in range(32):
            b = bitmap[zx_bitmap_index(xb, yy)]
            a = attrs[row_attr + xb]

            ink = a & 0x07
            paper = (a >> 3) & 0x07
            bright = (a >> 6) & 1
            flash = (a >> 7) & 1
            if flash and flash_phase:
                ink, paper = paper, ink

            ink_c = _zx_col(ink, bright)
            pap_c = _zx_col(paper, bright)
            x0 = x + (xb << 3)

            for start, length, bit in _BYTE_RUNS[b]:
                col = ink_c if bit else pap_c
                pyxel.rect(x0 + start, y0, length, 1, col)
