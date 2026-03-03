from __future__ import annotations

from ..zx.inputmap import KEY_CHAR_TO_ZX_KEYBOARD_SCAN, ZX_KEYBOARD_ROW_INDEX_BY_PORT
from ..zx.runtime import FrameInput

# Kempston joystick bit layout (classic):
# bit0 RIGHT, bit1 LEFT, bit2 DOWN, bit3 UP, bit4 FIRE


def _btn_by_name(pyxel_mod: object, name: str) -> bool:
    """Safely read a Pyxel button constant by attribute name."""
    key = getattr(pyxel_mod, name, None)
    if key is None:
        return False
    return bool(pyxel_mod.btn(key))


def joy_kempston() -> int:
    """Return a Kempston-like joystick state from gamepad and WASD+Space."""
    import pyxel

    v = 0
    if _btn_by_name(pyxel, "GAMEPAD1_BUTTON_DPAD_RIGHT") or _btn_by_name(pyxel, "KEY_D"):
        v |= 0x01
    if _btn_by_name(pyxel, "GAMEPAD1_BUTTON_DPAD_LEFT") or _btn_by_name(pyxel, "KEY_A"):
        v |= 0x02
    if _btn_by_name(pyxel, "GAMEPAD1_BUTTON_DPAD_DOWN") or _btn_by_name(pyxel, "KEY_S"):
        v |= 0x04
    if _btn_by_name(pyxel, "GAMEPAD1_BUTTON_DPAD_UP") or _btn_by_name(pyxel, "KEY_W"):
        v |= 0x08
    if _btn_by_name(pyxel, "GAMEPAD1_BUTTON_A") or _btn_by_name(pyxel, "KEY_SPACE"):
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

    # Mirror gamepad movement/action into the classic WASD+Space matrix layout.
    # This keeps keyboard-scanned code paths (menus/define-keys/etc.) compatible.
    for btn_name, key_char in (
        ("GAMEPAD1_BUTTON_DPAD_UP", "w"),
        ("GAMEPAD1_BUTTON_DPAD_LEFT", "a"),
        ("GAMEPAD1_BUTTON_DPAD_DOWN", "s"),
        ("GAMEPAD1_BUTTON_DPAD_RIGHT", "d"),
        ("GAMEPAD1_BUTTON_A", " "),
    ):
        if not _btn_by_name(pyxel, btn_name):
            continue
        mapped = KEY_CHAR_TO_ZX_KEYBOARD_SCAN.get(key_char)
        if mapped is None:
            continue
        row_idx = ZX_KEYBOARD_ROW_INDEX_BY_PORT.get(mapped[0])
        if row_idx is None:
            continue
        rows[row_idx] &= ~(1 << mapped[1])

    # Virtual gamepad-B trigger: physical GAMEPAD B or host key E.
    # Route it to SYMBOL SHIFT bit used by kempston slot6 preset.
    if _btn_by_name(pyxel, "GAMEPAD1_BUTTON_B") or _btn_by_name(pyxel, "KEY_E"):
        row_idx = ZX_KEYBOARD_ROW_INDEX_BY_PORT.get(0x7FFE)
        if row_idx is not None:
            rows[row_idx] &= ~(1 << 1)

    return tuple(v & 0xFF for v in rows)


def read_frame_input() -> FrameInput:
    """Collect current Pyxel input state in frame-step API form."""
    return FrameInput(
        joy_kempston=joy_kempston(),
        keyboard_rows=keyboard_rows(),
    )
