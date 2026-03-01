from __future__ import annotations

from ..zx.inputmap import KEY_CHAR_TO_ZX_KEYBOARD_SCAN, ZX_KEYBOARD_ROW_INDEX_BY_PORT
from ..zx.runtime import FrameInput

# Kempston joystick bit layout (classic):
# bit0 RIGHT, bit1 LEFT, bit2 DOWN, bit3 UP, bit4 FIRE


def joy_kempston() -> int:
    """Return a Kempston-like joystick state from Pyxel keys."""
    import pyxel

    v = 0
    if pyxel.btn(pyxel.KEY_RIGHT):
        v |= 0x01
    if pyxel.btn(pyxel.KEY_LEFT):
        v |= 0x02
    if pyxel.btn(pyxel.KEY_DOWN):
        v |= 0x04
    if pyxel.btn(pyxel.KEY_UP):
        v |= 0x08
    if pyxel.btn(pyxel.KEY_SPACE):
        v |= 0x10
    return v


_host_key_table: dict[int, str] | None = None


def _build_host_key_table() -> dict[int, str]:
    import pyxel

    t: dict[int, str] = {}

    for c in range(ord("A"), ord("Z") + 1):
        name = f"KEY_{chr(c)}"
        if hasattr(pyxel, name):
            t[getattr(pyxel, name)] = chr(c + 32)

    for d in "0123456789":
        name = f"KEY_{d}"
        if hasattr(pyxel, name):
            t[getattr(pyxel, name)] = d

    for name, ch in [
        ("KEY_SPACE", " "),
        ("KEY_RETURN", "\n"),
        ("KEY_BACKSPACE", "\b"),
        ("KEY_ESCAPE", "\x1b"),
    ]:
        if hasattr(pyxel, name):
            t[getattr(pyxel, name)] = ch

    return t


def keyboard_rows() -> tuple[int, ...]:
    """Return ZX keyboard matrix row snapshots (8 rows, active-low bits)."""
    import pyxel

    global _host_key_table
    if _host_key_table is None:
        _host_key_table = _build_host_key_table()

    rows = [0xFF] * 8
    shift_pressed = (hasattr(pyxel, "KEY_LSHIFT") and pyxel.btn(pyxel.KEY_LSHIFT)) or (
        hasattr(pyxel, "KEY_RSHIFT") and pyxel.btn(pyxel.KEY_RSHIFT)
    )
    if shift_pressed:
        # Map host shift to ZX CAPS SHIFT.
        rows[0] &= ~(1 << 0)

    for key, ch in _host_key_table.items():
        if not pyxel.btn(key):
            continue
        key_norm = ch if ch in ("\n", "\r", " ") else ch.lower()
        mapped = KEY_CHAR_TO_ZX_KEYBOARD_SCAN.get(key_norm)
        if mapped is None:
            continue
        row_idx = ZX_KEYBOARD_ROW_INDEX_BY_PORT.get(mapped[0])
        if row_idx is None:
            continue
        rows[row_idx] &= ~(1 << mapped[1])

    return tuple(v & 0xFF for v in rows)


def read_frame_input() -> FrameInput:
    """Collect current Pyxel input state in frame-step API form."""
    return FrameInput(
        joy_kempston=joy_kempston(),
        keyboard_rows=keyboard_rows(),
    )
