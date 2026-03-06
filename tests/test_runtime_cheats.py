from __future__ import annotations

import unittest

from alien_evolution.alienevolution.logic import (
    FSM_STATE_GAMEPLAY_TICK_STAGE_2_FRAME,
    FSM_STATE_GAMEPLAY_TICK_STAGE_1_FRAME,
    FSM_STATE_STREAM_INTERMISSION_FRAME,
    FSM_STATE_WAIT_KEYBOARD_RELEASE_FRAME,
    AlienEvolutionPort,
)
from alien_evolution.zx.inputmap import KEY_CHAR_TO_ZX_KEYBOARD_SCAN, ZX_KEYBOARD_ROW_INDEX_BY_PORT
from alien_evolution.zx.runtime import FrameInput

_NEUTRAL_INPUT = FrameInput(joy_kempston=0, keyboard_rows=(0xFF,) * 8)


def _frame_input_for_keys(*keys: str) -> FrameInput:
    rows = [0xFF] * 8
    for key in keys:
        scan = KEY_CHAR_TO_ZX_KEYBOARD_SCAN.get(key)
        if scan is None:
            raise ValueError(f"Unknown key for ZX scan map: {key!r}")
        port_word, bit_index = scan
        row_index = ZX_KEYBOARD_ROW_INDEX_BY_PORT.get(port_word)
        if row_index is None:
            raise ValueError(f"Unknown ZX keyboard row port: 0x{port_word:04X}")
        rows[row_index] &= (~(1 << bit_index)) & 0xFF
    return FrameInput(joy_kempston=0, keyboard_rows=tuple(rows))


class RuntimeCheatTests(unittest.TestCase):
    def test_level_cheats_enter_requested_gameplay_splash(self) -> None:
        for level_index, command in enumerate(("lvl1", "lvl2", "lvl3")):
            with self.subTest(command=command):
                runtime = AlienEvolutionPort()

                self.assertTrue(runtime.apply_cheat_sequence(command))
                self.assertEqual(runtime.var_active_map_mode & 0xFF, level_index)
                self.assertEqual(runtime._fsm_state, FSM_STATE_STREAM_INTERMISSION_FRAME)
                self.assertTrue(bool(runtime._fsm_gameplay_ctx["initialized"]))
                self.assertFalse(bool(runtime._fsm_gameplay_ctx["screen_setup_required"]))
                self.assertEqual(runtime.var_runtime_objective_counter & 0xFF, 0x06)

    def test_level_cheat_splash_release_enters_normal_gameplay_timing(self) -> None:
        runtime = AlienEvolutionPort()

        self.assertTrue(runtime.apply_cheat_sequence("lvl2"))

        splash_out = runtime.step(_frame_input_for_keys("s"))
        self.assertEqual(runtime._fsm_state, FSM_STATE_WAIT_KEYBOARD_RELEASE_FRAME)
        self.assertEqual(int(splash_out.timing.delay_after_step_frames), 0)
        self.assertEqual(runtime.var_active_map_mode & 0xFF, 0x01)

        gameplay_out = runtime.step(_NEUTRAL_INPUT)
        self.assertEqual(runtime._fsm_state, FSM_STATE_GAMEPLAY_TICK_STAGE_1_FRAME)
        self.assertEqual(int(gameplay_out.timing.delay_after_step_frames), 4)
        self.assertEqual(runtime.var_active_map_mode & 0xFF, 0x01)
        self.assertEqual(runtime.var_runtime_objective_counter & 0xFF, 0x06)

    def test_higher_level_cheats_do_not_immediately_enter_failure_path(self) -> None:
        for command, expected_mode in (("lvl2", 0x01), ("lvl3", 0x02)):
            with self.subTest(command=command):
                runtime = AlienEvolutionPort()

                self.assertTrue(runtime.apply_cheat_sequence(command))
                runtime.step(_NEUTRAL_INPUT)
                runtime.step(_frame_input_for_keys("s"))
                gameplay_out = runtime.step(_NEUTRAL_INPUT)

                self.assertEqual(runtime._fsm_state, FSM_STATE_GAMEPLAY_TICK_STAGE_1_FRAME)
                self.assertEqual(int(gameplay_out.timing.delay_after_step_frames), 4)
                self.assertEqual(runtime.var_active_map_mode & 0xFF, expected_mode)
                self.assertEqual(runtime.var_runtime_objective_counter & 0xFF, 0x06)

                runtime.advance_host_frame()
                runtime.advance_host_frame()
                runtime.advance_host_frame()
                runtime.advance_host_frame()
                next_out = runtime.step(_NEUTRAL_INPUT)

                self.assertEqual(runtime._fsm_state, FSM_STATE_GAMEPLAY_TICK_STAGE_2_FRAME)
                self.assertEqual(int(next_out.timing.delay_after_step_frames), 4)
                self.assertEqual(runtime._fsm_transition_kind, "none")

    def test_unknown_cheat_is_ignored(self) -> None:
        runtime = AlienEvolutionPort()
        before = runtime.save_state()

        self.assertFalse(runtime.apply_cheat_sequence("lvl4"))
        self.assertEqual(runtime.save_state(), before)


if __name__ == "__main__":
    unittest.main()
