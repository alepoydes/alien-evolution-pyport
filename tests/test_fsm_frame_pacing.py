from __future__ import annotations

import unittest

from alien_evolution.alienevolution.logic import (
    GAMEPLAY_FRAME_DIVIDER,
    FSM_STATE_CALLBACK_HALT_65_FRAME,
    FSM_STATE_FAILURE_TIMER_DRAIN_FRAME,
    FSM_STATE_FRAME_DELAY_0X50_FRAME,
    FSM_STATE_GAMEPLAY_BRANCH,
    FSM_STATE_GAMEPLAY_MAIN_FRAME,
    FSM_STATE_GAMEPLAY_MAIN_POST_TICK,
    FSM_STATE_GAMEPLAY_MAIN_AFTER_CALLBACK,
    FSM_STATE_GAMEPLAY_TICK_STAGE_1_FRAME,
    FSM_STATE_LEVEL_ROLL_FRAME,
    FSM_STATE_MENU_IDLE_POLL_FRAME,
    FSM_STATE_STREAM_INTERMISSION_FRAME,
    FSM_STATE_TRANSITION_DISPATCH,
    AlienEvolutionPort,
)
from alien_evolution.zx.runtime import FrameInput


class RuntimeFramePacingTests(unittest.TestCase):
    _NEUTRAL_INPUT = FrameInput(joy_kempston=0, keyboard_rows=(0xFF,) * 8)

    def _seed_runtime_in_gameplay(self) -> AlienEvolutionPort:
        runtime = AlienEvolutionPort()
        runtime.gameplay_screen_setup()
        runtime.fn_overlay_preset_selector()
        runtime._fsm_prepare_gameplay_loop()
        runtime._fsm_gameplay_ctx["initialized"] = True
        runtime._fsm_state = FSM_STATE_GAMEPLAY_MAIN_POST_TICK
        runtime.var_runtime_scheduler_timer = 0x1601
        runtime.var_runtime_objective_counter = 0x06
        runtime.var_runtime_progress_byte_0 = 0x01
        runtime.var_runtime_progress_byte_1 = 0x01
        runtime.var_runtime_progress_byte_2 = 0x01
        return runtime

    def _build_tick_stage_runtime(self, *, move_state_code: int) -> AlienEvolutionPort:
        runtime = AlienEvolutionPort()
        runtime.var_runtime_move_state_code = move_state_code & 0xFF
        runtime._gameplay_tick_update_core_pre = lambda *, E_code, D_xor: None  # type: ignore[assignment]
        runtime._gameplay_tick_update_core_post = lambda: None  # type: ignore[assignment]
        runtime.fn_patchable_callback_hook_frame_loop = (  # type: ignore[assignment]
            lambda *, defer_halt_to_fsm=False, defer_timing_to_fsm=False: (0, 0)
        )
        runtime.fn_directional_interaction_dispatcher_using_pointer_table = (  # type: ignore[assignment]
            lambda *, defer_overlay_timing_to_fsm=False: None
        )
        return runtime

    def test_menu_idle_poll_waits_one_host_frame(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._fsm_menu_ctx = {"prepared": True}

        next_state, delay = runtime._fsm_state_menu_idle_poll_frame()

        self.assertEqual(next_state, FSM_STATE_MENU_IDLE_POLL_FRAME)
        self.assertEqual(delay, 1)

    def test_stream_intermission_waits_one_host_frame(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._fsm_stream_ctx = {
            "abort_on_keypress": False,
            "timing_debt": 1,
            "return_state": FSM_STATE_MENU_IDLE_POLL_FRAME,
        }

        next_state, delay = runtime._fsm_state_stream_intermission_frame()

        self.assertEqual(next_state, FSM_STATE_STREAM_INTERMISSION_FRAME)
        self.assertEqual(delay, 1)

    def test_gameplay_main_post_tick_uses_default_divider(self) -> None:
        runtime = AlienEvolutionPort()
        runtime.var_runtime_move_state_code = 0x1C
        runtime.fn_main_pseudo_3d_map_render_pipeline = lambda: None  # type: ignore[assignment]

        next_state, delay = runtime._fsm_state_gameplay_main_post_tick()

        self.assertEqual(next_state, FSM_STATE_GAMEPLAY_BRANCH)
        self.assertEqual(delay, max(1, int(GAMEPLAY_FRAME_DIVIDER)))

    def test_gameplay_main_post_tick_uses_default_divider_for_teleport_move_state(self) -> None:
        runtime = AlienEvolutionPort()
        runtime.var_runtime_move_state_code = 0x1D
        runtime.fn_main_pseudo_3d_map_render_pipeline = lambda: None  # type: ignore[assignment]

        next_state, delay = runtime._fsm_state_gameplay_main_post_tick()

        self.assertEqual(next_state, FSM_STATE_GAMEPLAY_BRANCH)
        self.assertEqual(delay, max(1, int(GAMEPLAY_FRAME_DIVIDER)))

    def test_gameplay_tick_stage_uses_default_divider(self) -> None:
        runtime = self._build_tick_stage_runtime(move_state_code=0x1C)

        next_state, delay = runtime._fsm_state_gameplay_tick_stage_0_frame()

        self.assertEqual(next_state, FSM_STATE_GAMEPLAY_TICK_STAGE_1_FRAME)
        self.assertEqual(delay, max(1, int(GAMEPLAY_FRAME_DIVIDER)))

    def test_gameplay_tick_stage_uses_default_divider_for_teleport_move_state(self) -> None:
        runtime = self._build_tick_stage_runtime(move_state_code=0x1D)

        next_state, delay = runtime._fsm_state_gameplay_tick_stage_0_frame()

        self.assertEqual(next_state, FSM_STATE_GAMEPLAY_TICK_STAGE_1_FRAME)
        self.assertEqual(delay, max(1, int(GAMEPLAY_FRAME_DIVIDER)))

    def test_scheduler_autonomous_branch_keeps_nine_gameplay_delays(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._fsm_state = FSM_STATE_GAMEPLAY_MAIN_FRAME
        runtime._fsm_gameplay_ctx["initialized"] = True
        runtime._fsm_tick_ctx = {
            "pending_autonomous": False,
            "pending_marker": False,
        }
        runtime.var_runtime_scheduler_timer = 0x0101
        runtime.patch_scheduler_script_base_ptr = 0
        runtime.const_periodic_scheduler_script[0] = 0x01
        runtime.var_runtime_objective_counter = 0x06
        runtime.var_runtime_progress_byte_0 = 0x01
        runtime.var_runtime_progress_byte_1 = 0x01
        runtime.var_runtime_progress_byte_2 = 0x01
        runtime.per_frame_object_state_update_pass = lambda: None  # type: ignore[assignment]
        runtime.fn_process_transient_effect_queues_handlers_xe530 = lambda: None  # type: ignore[assignment]
        runtime.fn_gameplay_movement_control_step = lambda: None  # type: ignore[assignment]
        runtime.fn_directional_interaction_dispatcher_using_pointer_table = (  # type: ignore[assignment]
            lambda *, defer_overlay_timing_to_fsm=False: None
        )
        runtime.fn_patchable_callback_hook_frame_loop = (  # type: ignore[assignment]
            lambda *, defer_halt_to_fsm=False, defer_timing_to_fsm=False: (0, 0)
        )
        runtime.scheduler_triggered_autonomous_step = lambda *, run_tick=True: None  # type: ignore[assignment]
        runtime.scheduler_triggered_marker_seeding = lambda: None  # type: ignore[assignment]
        runtime.fn_main_pseudo_3d_map_render_pipeline = lambda: None  # type: ignore[assignment]

        delays: list[int] = []
        for _ in range(9):
            output = runtime.step(self._NEUTRAL_INPUT)
            delays.append(int(output.timing.delay_after_step_frames))

        self.assertEqual(runtime._fsm_state, FSM_STATE_GAMEPLAY_BRANCH)
        self.assertEqual(
            delays,
            [max(1, int(GAMEPLAY_FRAME_DIVIDER)) - 1] * 9,
        )

    def test_callback_halt_state_ticks_once_per_host_frame(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._fsm_callback_ctx = {
            "frames_left": 2,
            "return_state": FSM_STATE_GAMEPLAY_MAIN_AFTER_CALLBACK,
        }

        next_state_1, delay_1 = runtime._fsm_state_callback_halt_65_frame()
        next_state_2, delay_2 = runtime._fsm_state_callback_halt_65_frame()

        self.assertEqual(next_state_1, FSM_STATE_CALLBACK_HALT_65_FRAME)
        self.assertEqual(delay_1, 1)
        self.assertEqual(next_state_2, FSM_STATE_GAMEPLAY_MAIN_AFTER_CALLBACK)
        self.assertEqual(delay_2, 1)

    def test_level_roll_state_ticks_once_per_host_frame(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._fsm_level_roll_ctx = {
            "frame_idx": 0,
            "steps_done": 0,
        }

        next_state, delay = runtime._fsm_state_level_roll_frame()

        self.assertEqual(next_state, FSM_STATE_LEVEL_ROLL_FRAME)
        self.assertEqual(delay, 1)

    def test_frame_delay_state_ticks_once_per_host_frame(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._fsm_frame_delay_ctx = {
            "frames_left": 2,
            "return_state": FSM_STATE_TRANSITION_DISPATCH,
        }

        next_state, delay = runtime._fsm_state_frame_delay_0x50_frame()

        self.assertEqual(next_state, FSM_STATE_FRAME_DELAY_0X50_FRAME)
        self.assertEqual(delay, 1)

    def test_failure_timer_drain_state_ticks_once_per_host_frame(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._fsm_step_active = True
        runtime.patch_scheduler_script_base_ptr = 0
        runtime.const_periodic_scheduler_script[0] = 0x00
        runtime.var_runtime_scheduler_timer = 0x0201

        next_state, delay = runtime._fsm_state_failure_timer_drain_frame()

        self.assertEqual(next_state, FSM_STATE_FAILURE_TIMER_DRAIN_FRAME)
        self.assertEqual(delay, 1)

    def test_step_based_gameplay_pacing_uses_default_divider_without_teleport_state(self) -> None:
        runtime = self._seed_runtime_in_gameplay()
        runtime.var_runtime_move_state_code = 0x1C

        delays: list[int] = []
        for _ in range(12):
            output = runtime.step(self._NEUTRAL_INPUT)
            delays.append(int(output.timing.delay_after_step_frames))

        self.assertTrue(all(delay == max(1, int(GAMEPLAY_FRAME_DIVIDER)) - 1 for delay in delays))

    def test_step_based_gameplay_pacing_keeps_default_divider_during_teleport_state(self) -> None:
        runtime = self._seed_runtime_in_gameplay()
        runtime.var_runtime_move_state_code = 0x1D
        runtime.var_move_marker_code_scratch = 0x22

        delays: list[int] = []
        for _ in range(10):
            output = runtime.step(self._NEUTRAL_INPUT)
            delays.append(int(output.timing.delay_after_step_frames))

        self.assertTrue(all(delay == max(1, int(GAMEPLAY_FRAME_DIVIDER)) - 1 for delay in delays))


if __name__ == "__main__":
    unittest.main()
