from __future__ import annotations

import sys
import unittest
from unittest.mock import patch

from alien_evolution.pyxel import input as pyxel_input
from alien_evolution.zx.inputmap import ZX_KEYBOARD_ROW_INDEX_BY_PORT


class _FakePyxel:
    KEY_RIGHT = 1
    KEY_LEFT = 2
    KEY_DOWN = 3
    KEY_UP = 4
    KEY_SPACE = 5
    KEY_E = 6
    KEY_W = 7
    KEY_A = 8
    KEY_S = 9
    KEY_D = 10

    GAMEPAD1_BUTTON_DPAD_RIGHT = 21
    GAMEPAD1_BUTTON_DPAD_LEFT = 22
    GAMEPAD1_BUTTON_DPAD_DOWN = 23
    GAMEPAD1_BUTTON_DPAD_UP = 24
    GAMEPAD1_BUTTON_A = 25
    GAMEPAD1_BUTTON_B = 26

    def __init__(self, pressed: set[int]) -> None:
        self._pressed = pressed

    def btn(self, key: int) -> bool:
        return key in self._pressed


class PyxelInputGamepadTests(unittest.TestCase):
    def _with_pyxel(self, fake: _FakePyxel, fn):
        with patch.dict(sys.modules, {"pyxel": fake}):
            pyxel_input._host_key_table = None
            return fn()

    def test_gamepad_a_sets_kempston_fire(self) -> None:
        fake = _FakePyxel(pressed={_FakePyxel.GAMEPAD1_BUTTON_A})
        value = self._with_pyxel(fake, pyxel_input.joy_kempston)
        self.assertEqual(value & 0x10, 0x10)

    def test_arrow_keys_do_not_drive_kempston(self) -> None:
        fake = _FakePyxel(
            pressed={_FakePyxel.KEY_RIGHT, _FakePyxel.KEY_LEFT, _FakePyxel.KEY_DOWN, _FakePyxel.KEY_UP}
        )
        value = self._with_pyxel(fake, pyxel_input.joy_kempston)
        self.assertEqual(value & 0x1F, 0x00)

    def test_wasd_space_drive_kempston(self) -> None:
        fake = _FakePyxel(
            pressed={_FakePyxel.KEY_W, _FakePyxel.KEY_A, _FakePyxel.KEY_S, _FakePyxel.KEY_D, _FakePyxel.KEY_SPACE}
        )
        value = self._with_pyxel(fake, pyxel_input.joy_kempston)
        self.assertEqual(value & 0x1F, 0x1F)

    def test_gamepad_b_does_not_set_kempston_fire(self) -> None:
        fake = _FakePyxel(pressed={_FakePyxel.GAMEPAD1_BUTTON_B})
        value = self._with_pyxel(fake, pyxel_input.joy_kempston)
        self.assertEqual(value & 0x10, 0x00)

    def test_gamepad_dpad_and_a_mirror_to_wasd_space_rows(self) -> None:
        fake = _FakePyxel(
            pressed={
                _FakePyxel.GAMEPAD1_BUTTON_DPAD_UP,
                _FakePyxel.GAMEPAD1_BUTTON_DPAD_LEFT,
                _FakePyxel.GAMEPAD1_BUTTON_DPAD_DOWN,
                _FakePyxel.GAMEPAD1_BUTTON_DPAD_RIGHT,
                _FakePyxel.GAMEPAD1_BUTTON_A,
            }
        )
        rows = self._with_pyxel(fake, pyxel_input.keyboard_rows)

        row_fbfe = ZX_KEYBOARD_ROW_INDEX_BY_PORT[0xFBFE]  # Q W E R T
        row_fdfe = ZX_KEYBOARD_ROW_INDEX_BY_PORT[0xFDFE]  # A S D F G
        row_7ffe = ZX_KEYBOARD_ROW_INDEX_BY_PORT[0x7FFE]  # SPACE SYMBOL M N B

        self.assertEqual((rows[row_fbfe] >> 1) & 0x01, 0x00)  # W
        self.assertEqual((rows[row_fdfe] >> 0) & 0x01, 0x00)  # A
        self.assertEqual((rows[row_fdfe] >> 1) & 0x01, 0x00)  # S
        self.assertEqual((rows[row_fdfe] >> 2) & 0x01, 0x00)  # D
        self.assertEqual((rows[row_7ffe] >> 0) & 0x01, 0x00)  # SPACE

    def test_gamepad_b_maps_to_symbol_shift_in_keyboard_rows(self) -> None:
        fake = _FakePyxel(pressed={_FakePyxel.GAMEPAD1_BUTTON_B})
        rows = self._with_pyxel(fake, pyxel_input.keyboard_rows)

        row_7ffe = ZX_KEYBOARD_ROW_INDEX_BY_PORT[0x7FFE]
        self.assertEqual((rows[row_7ffe] >> 1) & 0x01, 0x00)  # SYMBOL SHIFT pressed

        row_fbfe = ZX_KEYBOARD_ROW_INDEX_BY_PORT[0xFBFE]
        self.assertEqual((rows[row_fbfe] >> 2) & 0x01, 0x01)  # E not pressed by B itself

    def test_host_e_triggers_virtual_gamepad_b_symbol_shift(self) -> None:
        fake = _FakePyxel(pressed={_FakePyxel.KEY_E})
        rows = self._with_pyxel(fake, pyxel_input.keyboard_rows)

        row_7ffe = ZX_KEYBOARD_ROW_INDEX_BY_PORT[0x7FFE]
        self.assertEqual((rows[row_7ffe] >> 1) & 0x01, 0x00)  # SYMBOL SHIFT via virtual B


if __name__ == "__main__":
    unittest.main()
