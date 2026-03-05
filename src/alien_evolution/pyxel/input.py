from __future__ import annotations

import sys

from ..zx.inputmap import KEY_CHAR_TO_ZX_KEYBOARD_SCAN, ZX_KEYBOARD_ROW_INDEX_BY_PORT
from ..zx.runtime import FrameInput

# Kempston joystick bit layout (classic):
# bit0 RIGHT, bit1 LEFT, bit2 DOWN, bit3 UP, bit4 FIRE

_WEB_KEYFIX_READY: bool | None = None


def _btn_by_name(pyxel_mod: object, name: str) -> bool:
    """Safely read a Pyxel button constant by attribute name."""
    key = getattr(pyxel_mod, name, None)
    if key is None:
        return False
    return bool(pyxel_mod.btn(key))


def _install_web_keyfix() -> bool:
    """Install best-effort keyboard state tracker for Pyxel WASM runtime."""
    global _WEB_KEYFIX_READY
    if _WEB_KEYFIX_READY is not None:
        return _WEB_KEYFIX_READY

    if sys.platform != "emscripten":
        _WEB_KEYFIX_READY = False
        return False

    try:
        import js  # type: ignore
    except Exception:
        _WEB_KEYFIX_READY = False
        return False

    try:
        if bool(getattr(js.window, "__ae_keyfix_installed", False)):
            _WEB_KEYFIX_READY = True
            return True
    except Exception:
        pass

    try:
        js.eval(
            """
(function () {
  if (window.__ae_keyfix_installed) return;
  window.__ae_keyfix_installed = true;

  const state = Object.create(null);

  function keyId(e) {
    if (e && typeof e.code === "string" && e.code.length) return e.code;
    if (e && typeof e.key === "string" && e.key.length) return e.key;
    return "";
  }

  function shouldPrevent(id) {
    if (!id) return false;
    if (id === " " || id === "Space") return true;
    if (id === "Backspace" || id === "Enter") return true;
    if (id === "KeyW" || id === "KeyA" || id === "KeyS" || id === "KeyD") return true;
    if (id === "ShiftLeft" || id === "ShiftRight") return true;
    if (id.startsWith("Arrow")) return true;
    return false;
  }

  function onDown(e) {
    const id = keyId(e);
    if (id) state[id] = true;
    if (shouldPrevent(id)) {
      try { e.preventDefault(); } catch (_) {}
    }
  }

  function onUp(e) {
    const id = keyId(e);
    if (id) state[id] = false;
    if (shouldPrevent(id)) {
      try { e.preventDefault(); } catch (_) {}
    }
  }

  function clear() {
    for (const k in state) {
      if (Object.prototype.hasOwnProperty.call(state, k)) state[k] = false;
    }
  }

  window.__aeKeyDown = function (id) { return !!state[id]; };
  window.__aeKeyClear = clear;

  window.addEventListener("keydown", onDown, { capture: true });
  window.addEventListener("keyup", onUp, { capture: true });
  window.addEventListener("blur", clear, { capture: true });
  window.addEventListener("pagehide", clear, { capture: true });
  document.addEventListener(
    "visibilitychange",
    function () { if (document.hidden) clear(); },
    { capture: true },
  );
})();
            """
        )
    except Exception:
        _WEB_KEYFIX_READY = False
        return False

    _WEB_KEYFIX_READY = True
    return True


def _web_key_down(*key_ids: str) -> bool:
    """Return whether any key id is currently held in web key-tracker."""
    if not key_ids or not _install_web_keyfix():
        return False

    try:
        import js  # type: ignore
    except Exception:
        return False

    try:
        has_focus = getattr(js.document, "hasFocus", None)
        if callable(has_focus) and not bool(has_focus()):
            clear = getattr(js.window, "__aeKeyClear", None)
            if callable(clear):
                clear()
            return False
    except Exception:
        pass

    key_down_fn = getattr(js.window, "__aeKeyDown", None)
    if not callable(key_down_fn):
        return False

    for key_id in key_ids:
        try:
            if bool(key_down_fn(key_id)):
                return True
        except Exception:
            continue
    return False


def _host_key_down(pyxel_mod: object, key_name: str, *web_ids: str) -> bool:
    """Read a keyboard key from web-tracker in WASM, else from pyxel.btn."""
    if _install_web_keyfix():
        return _web_key_down(*web_ids)
    return _btn_by_name(pyxel_mod, key_name)


def _host_char_web_ids(ch: str) -> tuple[str, ...]:
    if len(ch) == 1 and "a" <= ch <= "z":
        upper = ch.upper()
        return (f"Key{upper}", ch, upper)
    if len(ch) == 1 and "A" <= ch <= "Z":
        return (f"Key{ch}", ch.lower(), ch)
    if len(ch) == 1 and "0" <= ch <= "9":
        return (f"Digit{ch}", ch)
    if ch == " ":
        return ("Space", " ")
    if ch in ("\n", "\r"):
        return ("Enter",)
    if ch == "\b":
        return ("Backspace",)
    if ch == "\x1b":
        return ("Escape",)
    return ()


def _host_char_down(pyxel_mod: object, pyxel_key: int, ch: str) -> bool:
    if _install_web_keyfix():
        return _web_key_down(*_host_char_web_ids(ch))
    return bool(pyxel_mod.btn(pyxel_key))


def joy_kempston() -> int:
    """Return a Kempston-like joystick state from gamepad and WASD+Space."""
    import pyxel

    v = 0
    if _btn_by_name(pyxel, "GAMEPAD1_BUTTON_DPAD_RIGHT") or _host_key_down(pyxel, "KEY_D", "KeyD", "d", "D"):
        v |= 0x01
    if _btn_by_name(pyxel, "GAMEPAD1_BUTTON_DPAD_LEFT") or _host_key_down(pyxel, "KEY_A", "KeyA", "a", "A"):
        v |= 0x02
    if _btn_by_name(pyxel, "GAMEPAD1_BUTTON_DPAD_DOWN") or _host_key_down(pyxel, "KEY_S", "KeyS", "s", "S"):
        v |= 0x04
    if _btn_by_name(pyxel, "GAMEPAD1_BUTTON_DPAD_UP") or _host_key_down(pyxel, "KEY_W", "KeyW", "w", "W"):
        v |= 0x08
    if _btn_by_name(pyxel, "GAMEPAD1_BUTTON_A") or _host_key_down(pyxel, "KEY_SPACE", "Space", " "):
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
    shift_pressed = _host_key_down(pyxel, "KEY_LSHIFT", "ShiftLeft") or _host_key_down(
        pyxel,
        "KEY_RSHIFT",
        "ShiftRight",
    )
    if shift_pressed:
        # Map host shift to ZX CAPS SHIFT.
        rows[0] &= ~(1 << 0)

    for key, ch in _host_key_table.items():
        if not _host_char_down(pyxel, key, ch):
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
    if _btn_by_name(pyxel, "GAMEPAD1_BUTTON_B") or _host_key_down(pyxel, "KEY_E", "KeyE", "e", "E"):
        row_idx = ZX_KEYBOARD_ROW_INDEX_BY_PORT.get(0x7FFE)
        if row_idx is not None:
            rows[row_idx] &= ~(1 << 1)

    return tuple(v & 0xFF for v in rows)


def read_frame_input() -> FrameInput:
    """Collect current Pyxel input state in frame-step API form."""
    _install_web_keyfix()
    return FrameInput(
        joy_kempston=joy_kempston(),
        keyboard_rows=keyboard_rows(),
    )
