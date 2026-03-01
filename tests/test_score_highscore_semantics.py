from __future__ import annotations

import unittest

from alien_evolution.alienevolution.logic import (
    FSM_STATE_HIGHSCORE_FILTER_KEY_FRAME,
    FSM_STATE_HIGHSCORE_WAIT_KEY_FRAME,
    FSM_STATE_TRANSITION_DISPATCH,
    AlienEvolutionPort,
)


def _set_score_value(runtime: AlienEvolutionPort, value: int) -> None:
    score = int(value) % 100_000
    runtime.var_runtime_aux_c8_lo = (score // 10_000) % 10
    runtime.var_runtime_aux_c8_hi = (score // 1_000) % 10
    runtime.var_runtime_aux_ca = (score // 100) % 10
    runtime.var_runtime_aux_cb = (score // 10) % 10
    runtime.var_runtime_aux_cc = score % 10


class ScoreHighScoreSemanticsTests(unittest.TestCase):
    def test_score_compare_promotes_when_score_above_zero_row(self) -> None:
        runtime = AlienEvolutionPort()
        _set_score_value(runtime, 1)
        self.assertEqual(runtime.fn_score_compare_helper(0), 1)

    def test_score_compare_does_not_promote_on_tie(self) -> None:
        runtime = AlienEvolutionPort()
        _set_score_value(runtime, 0)
        self.assertEqual(runtime.fn_score_compare_helper(0), 0)

    def test_high_score_editor_init_enters_name_mode_when_qualified(self) -> None:
        runtime = AlienEvolutionPort()
        _set_score_value(runtime, 1)
        runtime._rom_get_key_02bf = lambda: 0x0D
        row0_before = bytes(runtime.var_highscore_row_templates[0])

        runtime.high_score_editor_init()

        row0_after = bytes(runtime.var_highscore_row_templates[0])
        self.assertNotEqual(row0_after, row0_before)
        self.assertEqual(runtime.var_highscore_name_edit_state & 0xFF, 0x00)

    def test_high_score_editor_init_skips_when_not_qualified(self) -> None:
        runtime = AlienEvolutionPort()
        _set_score_value(runtime, 0)
        runtime._rom_get_key_02bf = lambda: 0x0D
        rows_before = tuple(bytes(row) for row in runtime.var_highscore_row_templates)

        runtime.high_score_editor_init()

        rows_after = tuple(bytes(row) for row in runtime.var_highscore_row_templates)
        self.assertEqual(rows_after, rows_before)

    def test_fsm_highscore_prepare_initializes_editor_context(self) -> None:
        runtime = AlienEvolutionPort()
        _set_score_value(runtime, 1)

        prepared = runtime._fsm_highscore_prepare()

        self.assertTrue(prepared)
        self.assertEqual(runtime.var_highscore_name_edit_state & 0xFF, 0x00)

    def test_fsm_highscore_enter_transitions_to_return_state(self) -> None:
        runtime = AlienEvolutionPort()
        _set_score_value(runtime, 1)
        self.assertTrue(runtime._fsm_highscore_prepare())
        runtime._fsm_highscore_ctx = {
            "return_state": FSM_STATE_TRANSITION_DISPATCH,
            "next_transition_kind": "failure_post_highscore",
            "pending_key": 0xFF,
        }
        runtime._rom_get_key_02bf = lambda: 0x0D

        next_state, delay = runtime._fsm_state_highscore_wait_key_frame()
        self.assertEqual(next_state, FSM_STATE_HIGHSCORE_FILTER_KEY_FRAME)
        self.assertIsNone(delay)

        next_state, delay = runtime._fsm_state_highscore_filter_key_frame()
        self.assertEqual(next_state, FSM_STATE_TRANSITION_DISPATCH)
        self.assertIsNone(delay)
        self.assertEqual(runtime._fsm_transition_kind, "failure_post_highscore")

    def test_fsm_highscore_wait_returns_frame_delay_when_no_key(self) -> None:
        runtime = AlienEvolutionPort()
        _set_score_value(runtime, 1)
        self.assertTrue(runtime._fsm_highscore_prepare())
        runtime._fsm_highscore_ctx = {
            "return_state": FSM_STATE_TRANSITION_DISPATCH,
            "next_transition_kind": "failure_post_highscore",
            "pending_key": 0xFF,
        }
        runtime._rom_get_key_02bf = lambda: 0xFF

        next_state, delay = runtime._fsm_state_highscore_wait_key_frame()
        self.assertEqual(next_state, FSM_STATE_HIGHSCORE_WAIT_KEY_FRAME)
        self.assertEqual(delay, 1)


if __name__ == "__main__":
    unittest.main()
