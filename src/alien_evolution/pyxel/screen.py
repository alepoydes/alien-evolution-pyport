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
#
# - _ATTR_COLORS packs the two colors into one int: (ink | (paper << 8)).
# - _ATTR_IP_IDX packs them into (paper << 4) | ink for fast indexing into the
#   Image.set LUT (0..255, since both colors are in 0..15).
_ATTR_COLORS: tuple[list[int], list[int]] = ([0] * 256, [0] * 256)
_ATTR_IP_IDX: tuple[list[int], list[int]] = ([0] * 256, [0] * 256)
for phase in (0, 1):
    slot = _ATTR_COLORS[phase]
    idx_slot = _ATTR_IP_IDX[phase]
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
        idx_slot[a] = ink_c | (pap_c << 4)


# -----------------------------------------------------------------------------
# Optional ultra-low-call renderer for Pyxel Web
# -----------------------------------------------------------------------------

_HEX_DIGITS = "0123456789abcdef"

# Lazy table: 256 (bitmap byte) * 256 (paper/ink pair) -> 8-char row snippet.
# Stored as a flat list for fast indexing: lut[(b << 8) | ip].
_BYTE_IP_LUT: list[str] | None = None

# Reusable per-frame buffers for the Image.set renderer (allocated lazily).
_IMAGE_SET_LINES: list[str] | None = None
_IMAGE_SET_PARTS: list[str] | None = None


def _ensure_byte_ip_lut() -> list[str]:
    """Return (and lazily build) the bitmap-byte -> 8px string LUT.

    This is intentionally lazy because alien_evolution.pyxel is imported by
    non-graphical unit tests, and building ~65k strings at import time slows
    tests noticeably.
    """

    global _BYTE_IP_LUT
    if _BYTE_IP_LUT is not None:
        return _BYTE_IP_LUT

    # Build once. Memory footprint is a few MB, but it keeps the per-frame
    # Python work tiny and avoids thousands of draw calls in Pyxel Web.
    lut: list[str] = [""] * (256 * 256)
    hex_digits = _HEX_DIGITS
    for b in range(256):
        # Pre-pull bits once to avoid repeated shifts inside the inner loop.
        b7 = 1 if (b & 0x80) else 0
        b6 = 1 if (b & 0x40) else 0
        b5 = 1 if (b & 0x20) else 0
        b4 = 1 if (b & 0x10) else 0
        b3 = 1 if (b & 0x08) else 0
        b2 = 1 if (b & 0x04) else 0
        b1 = 1 if (b & 0x02) else 0
        b0 = 1 if (b & 0x01) else 0
        base = b << 8
        for ip in range(256):
            ink = ip & 0x0F
            pap = (ip >> 4) & 0x0F
            i = hex_digits[ink]
            p = hex_digits[pap]

            # 8 pixels, MSB -> LSB.
            lut[base | ip] = (
                (i if b7 else p)
                + (i if b6 else p)
                + (i if b5 else p)
                + (i if b4 else p)
                + (i if b3 else p)
                + (i if b2 else p)
                + (i if b1 else p)
                + (i if b0 else p)
            )

    _BYTE_IP_LUT = lut
    return lut


def _auto_blit_method() -> str:
    """Pick a default render method.

    Pyxel Web runs Python under Emscripten/Pyodide. Crossing the Python<->WASM
    boundary per primitive draw call is expensive, so we prefer an Image.set
    based path there.
    """

    import sys

    # Pyodide / Emscripten builds report this platform string.
    if sys.platform == "emscripten":
        return "image"
    return "rect"


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

    if method == "auto":
        method = _auto_blit_method()

    if ENABLE_RUNTIME_CHECKS and method not in ("rect", "pset", "image"):
        raise ValueError("method must be 'rect', 'pset', 'image', or 'auto'")

    if method == "image":
        # Fast path for Pyxel Web: render into an image bank using one bulk
        # Image.set call and then blit the whole 256x192 region in one go.
        #
        # This avoids thousands of primitive draw calls that are expensive on
        # the Python<->WASM bridge.
        if hasattr(pyxel, "images"):
            img0 = pyxel.images[0]
        else:
            img0 = pyxel.image(0)

        lut = _ensure_byte_ip_lut()
        attr_ip = _ATTR_IP_IDX[flash_phase]
        row_base_tbl = _ROW_BASE

        # Build 192 scanlines of 256 hex digits each.
        #
        # Keep allocations low: reuse the outer list (192 strings) and the
        # per-line parts list (32 snippets) across frames.
        global _IMAGE_SET_LINES, _IMAGE_SET_PARTS
        if _IMAGE_SET_LINES is None:
            _IMAGE_SET_LINES = [""] * ZX_SCREEN_H
        if _IMAGE_SET_PARTS is None:
            _IMAGE_SET_PARTS = [""] * 32

        lines = _IMAGE_SET_LINES
        parts = _IMAGE_SET_PARTS

        bitmap_local = bitmap
        attrs_local = attrs
        for yy in range(ZX_SCREEN_H):
            row_attr = (yy >> 3) * 32
            row_base = row_base_tbl[yy]
            for xb in range(32):
                b = bitmap_local[row_base + xb]
                ip = attr_ip[attrs_local[row_attr + xb]]
                parts[xb] = lut[(b << 8) | ip]
            lines[yy] = "".join(parts)

        img0.set(0, 0, lines)
        pyxel.blt(x, y, 0, 0, 0, 256, 192)
        return

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
