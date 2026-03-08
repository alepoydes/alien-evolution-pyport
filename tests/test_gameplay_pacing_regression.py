from __future__ import annotations

import unittest
from dataclasses import dataclass

from alien_evolution.alienevolution.logic import (
    FSM_STATE_GAMEPLAY_BRANCH,
    FSM_STATE_GAMEPLAY_TICK_STAGE_1_FRAME,
    FSM_STATE_GAMEPLAY_TICK_STAGE_2_FRAME,
    FSM_STATE_GAMEPLAY_TICK_STAGE_3_FRAME,
    GAMEPLAY_FRAME_DIVIDER,
    FSM_STATE_MENU_IDLE_POLL_FRAME,
    FSM_STATE_MENU_POST_ACTION_FRAME,
    FSM_STATE_SCHEDULER_AUTONOMOUS_FRAME,
    FSM_STATE_STREAM_INTERMISSION_FRAME,
    FSM_STATE_WAIT_KEYBOARD_RELEASE_FRAME,
    AlienEvolutionPort,
)
from alien_evolution.zx.inputmap import KEY_CHAR_TO_ZX_KEYBOARD_SCAN, ZX_KEYBOARD_ROW_INDEX_BY_PORT
from alien_evolution.zx.runtime import FrameInput, StepOutput


_NEUTRAL_INPUT = FrameInput(joy_kempston=0, keyboard_rows=(0xFF,) * 8)
_GAMEPLAY_DELAY_AFTER_STEP = max(1, int(GAMEPLAY_FRAME_DIVIDER)) - 1


@dataclass
class _HostFrameHarness:
    runtime: AlienEvolutionPort
    host_frame_index: int = 0
    step_counter: int = 0
    pending_delay_frames: int = 0

    def run_host_frame(self, frame_input: FrameInput) -> tuple[bool, StepOutput]:
        self.host_frame_index += 1
        if self.pending_delay_frames > 0:
            self.runtime.advance_host_frame()
            self.pending_delay_frames -= 1
            return False, self.runtime.snapshot_output()

        output = self.runtime.step(frame_input)
        self.pending_delay_frames = max(0, int(output.timing.delay_after_step_frames))
        self.step_counter += 1
        return True, output

    def run_until_step(self, frame_input: FrameInput, *, max_host_frames: int = 32) -> StepOutput:
        for _ in range(max_host_frames):
            stepped, output = self.run_host_frame(frame_input)
            if stepped:
                return output
        raise AssertionError("Timed out while waiting for runtime.step()")

    def run_until_step_with_states(
        self,
        frame_input: FrameInput,
        *,
        max_host_frames: int = 32,
    ) -> tuple[str, str, StepOutput]:
        for _ in range(max_host_frames):
            pre_state = self.runtime._fsm_state
            stepped, output = self.run_host_frame(frame_input)
            if not stepped:
                continue
            post_state = self.runtime._fsm_state
            return pre_state, post_state, output
        raise AssertionError("Timed out while waiting for runtime.step()")


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


class GameplayPacingRegressionTests(unittest.TestCase):
    _EXPECTED_POST_TICK1_TO_BRANCH: tuple[str, ...] = (
        FSM_STATE_GAMEPLAY_TICK_STAGE_2_FRAME,
        FSM_STATE_GAMEPLAY_TICK_STAGE_3_FRAME,
        FSM_STATE_SCHEDULER_AUTONOMOUS_FRAME,
        FSM_STATE_GAMEPLAY_TICK_STAGE_1_FRAME,
        FSM_STATE_GAMEPLAY_TICK_STAGE_2_FRAME,
        FSM_STATE_GAMEPLAY_TICK_STAGE_3_FRAME,
        FSM_STATE_SCHEDULER_AUTONOMOUS_FRAME,
        FSM_STATE_GAMEPLAY_BRANCH,
    )
    _EXPECTED_POST_TICK1_TO_BRANCH_DELAYS: tuple[int, ...] = (
        _GAMEPLAY_DELAY_AFTER_STEP,
    ) * len(_EXPECTED_POST_TICK1_TO_BRANCH)

    def _build_menu_harness_from_reset(self) -> _HostFrameHarness:
        runtime = AlienEvolutionPort()
        runtime.reset()
        harness = _HostFrameHarness(runtime=runtime)
        for _ in range(128):
            harness.run_until_step(_NEUTRAL_INPUT, max_host_frames=64)
            if runtime._fsm_state == FSM_STATE_STREAM_INTERMISSION_FRAME:
                break
        else:
            raise AssertionError("Timed out while waiting for STREAM_INTERMISSION_FRAME after reset")

        _ = harness.run_until_step(_frame_input_for_keys("q"), max_host_frames=64)
        for _ in range(128):
            harness.run_until_step(_NEUTRAL_INPUT, max_host_frames=64)
            if runtime._fsm_state == FSM_STATE_MENU_IDLE_POLL_FRAME:
                harness.host_frame_index = 0
                harness.step_counter = 0
                return harness
        raise AssertionError("Timed out while waiting for MENU_IDLE_POLL_FRAME after intro stream abort")

    def _mode0_source_start_cell_and_coords(self, runtime: AlienEvolutionPort) -> tuple[int, tuple[int, int]]:
        for idx, cell in enumerate(runtime.var_level_map_mode_0):
            if (int(cell) & 0x3F) == 0x21:
                col = idx % 0x32
                row = idx // 0x32
                return idx, (col, row)
        raise AssertionError("Mode-0 source map has no start cell code 0x21")

    def _assert_transition_chain(
        self,
        harness: _HostFrameHarness,
        *,
        start_state: str,
        expected_post_states: tuple[str, ...],
        expected_delays: tuple[int, ...],
        frame_input: FrameInput = _NEUTRAL_INPUT,
    ) -> list[tuple[str, str, int]]:
        if len(expected_post_states) != len(expected_delays):
            raise AssertionError("expected_post_states and expected_delays must have same length")

        transitions: list[tuple[str, str, int]] = []
        expected_pre = start_state
        for idx, (expected_post, expected_delay) in enumerate(zip(expected_post_states, expected_delays)):
            pre_state, post_state, output = harness.run_until_step_with_states(frame_input)
            delay = int(output.timing.delay_after_step_frames)
            transitions.append((pre_state, post_state, delay))
            self.assertEqual(
                pre_state,
                expected_pre,
                f"Transition #{idx + 1}: unexpected pre-state",
            )
            self.assertEqual(
                post_state,
                expected_post,
                f"Transition #{idx + 1}: unexpected post-state",
            )
            self.assertEqual(
                delay,
                expected_delay,
                f"Transition #{idx + 1}: unexpected delay",
            )
            expected_pre = expected_post

        return transitions

    def test_menu_cadence_is_50fps_in_menu_idle_after_reset(self) -> None:
        harness = self._build_menu_harness_from_reset()
        runtime = harness.runtime
        runtime.var_menu_selection_index = 0x03
        delays: list[int] = []

        for _ in range(8):
            out = harness.run_until_step(_NEUTRAL_INPUT)
            delays.append(int(out.timing.delay_after_step_frames))
            self.assertEqual(runtime._fsm_state, FSM_STATE_MENU_IDLE_POLL_FRAME)

        out_1 = harness.run_until_step(_frame_input_for_keys("1"))
        delays.append(int(out_1.timing.delay_after_step_frames))
        self.assertEqual(
            runtime._fsm_state,
            FSM_STATE_MENU_POST_ACTION_FRAME,
            "Pressing key '1' in menu must transition to MENU_POST_ACTION_FRAME",
        )
        self.assertEqual(
            runtime.var_menu_selection_index & 0xFF,
            0x00,
            "Pressing key '1' must move menu selection pointer to slot 0",
        )

        for _ in range(8):
            out = harness.run_until_step(_NEUTRAL_INPUT)
            delays.append(int(out.timing.delay_after_step_frames))
            self.assertEqual(runtime._fsm_state, FSM_STATE_MENU_IDLE_POLL_FRAME)

        out_2 = harness.run_until_step(_frame_input_for_keys("2"))
        delays.append(int(out_2.timing.delay_after_step_frames))
        self.assertEqual(
            runtime._fsm_state,
            FSM_STATE_MENU_POST_ACTION_FRAME,
            "Pressing key '2' in menu must transition to MENU_POST_ACTION_FRAME",
        )
        self.assertEqual(
            runtime.var_menu_selection_index & 0xFF,
            0x01,
            "Pressing key '2' must move menu selection pointer to slot 1",
        )

        for _ in range(8):
            out = harness.run_until_step(_NEUTRAL_INPUT)
            delays.append(int(out.timing.delay_after_step_frames))
            self.assertEqual(runtime._fsm_state, FSM_STATE_MENU_IDLE_POLL_FRAME)

        self.assertTrue(
            all(delay == 0 for delay in delays),
            f"Menu cadence changed while pressing 1/2: delays={sorted(set(delays))}",
        )
        self.assertLessEqual(harness.step_counter, 100)

    @unittest.skip("Disabled: replaced by source-grounded splash regression tests")
    def test_start_then_down_on_splash_must_not_teleport_after_reset(self) -> None:
        harness = self._build_menu_harness_from_reset()
        runtime = harness.runtime

        pre_start, post_start, start_out = harness.run_until_step_with_states(_frame_input_for_keys("6"))
        self.assertEqual(pre_start, FSM_STATE_MENU_IDLE_POLL_FRAME)
        self.assertEqual(
            post_start,
            FSM_STATE_STREAM_INTERMISSION_FRAME,
            "After first start key we must enter splash/stream state",
        )
        self.assertEqual(
            int(start_out.timing.delay_after_step_frames),
            0,
            "Transition menu->splash must keep splash cadence (delay=0)",
        )

        pre_held_start, post_held_start, held_start_out = harness.run_until_step_with_states(_frame_input_for_keys("6"))
        self.assertEqual(pre_held_start, FSM_STATE_STREAM_INTERMISSION_FRAME)
        self.assertEqual(
            post_held_start,
            FSM_STATE_STREAM_INTERMISSION_FRAME,
            "Holding START must not exit splash; splash requires a new key edge",
        )
        self.assertEqual(int(held_start_out.timing.delay_after_step_frames), 0)

        start_cell = runtime.var_runtime_current_cell_ptr.index
        start_coords = runtime.var_current_map_coords.snapshot()

        pre_down, post_down, out_down = harness.run_until_step_with_states(_frame_input_for_keys("s"))
        self.assertEqual(pre_down, FSM_STATE_STREAM_INTERMISSION_FRAME)
        self.assertEqual(
            post_down,
            FSM_STATE_WAIT_KEYBOARD_RELEASE_FRAME,
            "Down on splash must only dismiss splash and wait key release",
        )
        self.assertEqual(int(out_down.timing.delay_after_step_frames), 0)
        self.assertEqual(runtime.var_runtime_current_cell_ptr.index, start_cell)
        self.assertEqual(runtime.var_current_map_coords.snapshot(), start_coords)

        pre_hold_down, post_hold_down, hold_down_out = harness.run_until_step_with_states(_frame_input_for_keys("s"))
        self.assertEqual(pre_hold_down, FSM_STATE_WAIT_KEYBOARD_RELEASE_FRAME)
        self.assertEqual(post_hold_down, FSM_STATE_WAIT_KEYBOARD_RELEASE_FRAME)
        self.assertEqual(int(hold_down_out.timing.delay_after_step_frames), 0)
        self.assertEqual(runtime.var_runtime_current_cell_ptr.index, start_cell)
        self.assertEqual(runtime.var_current_map_coords.snapshot(), start_coords)

        pre_release, post_release, release_out = harness.run_until_step_with_states(_NEUTRAL_INPUT)
        self.assertEqual(pre_release, FSM_STATE_WAIT_KEYBOARD_RELEASE_FRAME)
        self.assertEqual(post_release, FSM_STATE_GAMEPLAY_TICK_STAGE_1_FRAME)
        self.assertEqual(int(release_out.timing.delay_after_step_frames), _GAMEPLAY_DELAY_AFTER_STEP)

        _ = self._assert_transition_chain(
            harness,
            start_state=FSM_STATE_GAMEPLAY_TICK_STAGE_1_FRAME,
            expected_post_states=self._EXPECTED_POST_TICK1_TO_BRANCH,
            expected_delays=self._EXPECTED_POST_TICK1_TO_BRANCH_DELAYS,
        )
        self.assertEqual(runtime._fsm_state, FSM_STATE_GAMEPLAY_BRANCH)
        self.assertEqual(
            runtime.var_runtime_current_cell_ptr.index,
            start_cell,
            "Down pressed on splash must not move player/teleport",
        )
        self.assertEqual(
            runtime.var_current_map_coords.snapshot(),
            start_coords,
            "Down pressed on splash must preserve player coordinates",
        )
        self.assertLessEqual(harness.step_counter, 100)

    @unittest.skip("Disabled: replaced by source-grounded splash regression tests")
    def test_start_then_start_exit_splash_then_down_is_single_step_after_reset(self) -> None:
        harness = self._build_menu_harness_from_reset()
        runtime = harness.runtime

        pre_start, post_start, start_out = harness.run_until_step_with_states(_frame_input_for_keys("6"))
        self.assertEqual(pre_start, FSM_STATE_MENU_IDLE_POLL_FRAME)
        self.assertEqual(post_start, FSM_STATE_STREAM_INTERMISSION_FRAME)
        self.assertEqual(int(start_out.timing.delay_after_step_frames), 0)

        pre_splash, post_splash, splash_out = harness.run_until_step_with_states(_NEUTRAL_INPUT)
        self.assertEqual(pre_splash, FSM_STATE_STREAM_INTERMISSION_FRAME)
        self.assertEqual(post_splash, FSM_STATE_STREAM_INTERMISSION_FRAME)
        self.assertEqual(int(splash_out.timing.delay_after_step_frames), 0)

        pre_exit, post_exit, out_exit = harness.run_until_step_with_states(_frame_input_for_keys("6"))
        self.assertEqual(pre_exit, FSM_STATE_STREAM_INTERMISSION_FRAME)
        self.assertEqual(post_exit, FSM_STATE_WAIT_KEYBOARD_RELEASE_FRAME)
        self.assertEqual(int(out_exit.timing.delay_after_step_frames), 0)

        pre_release, post_release, release_out = harness.run_until_step_with_states(_NEUTRAL_INPUT)
        self.assertEqual(pre_release, FSM_STATE_WAIT_KEYBOARD_RELEASE_FRAME)
        self.assertEqual(post_release, FSM_STATE_GAMEPLAY_TICK_STAGE_1_FRAME)
        self.assertEqual(int(release_out.timing.delay_after_step_frames), _GAMEPLAY_DELAY_AFTER_STEP)
        start_cell = runtime.var_runtime_current_cell_ptr.index
        start_coords = runtime.var_current_map_coords.snapshot()

        _ = self._assert_transition_chain(
            harness,
            start_state=FSM_STATE_GAMEPLAY_TICK_STAGE_1_FRAME,
            expected_post_states=self._EXPECTED_POST_TICK1_TO_BRANCH,
            expected_delays=self._EXPECTED_POST_TICK1_TO_BRANCH_DELAYS,
        )
        self.assertEqual(runtime._fsm_state, FSM_STATE_GAMEPLAY_BRANCH)
        self.assertEqual(runtime.var_runtime_current_cell_ptr.index, start_cell)
        self.assertEqual(runtime.var_current_map_coords.snapshot(), start_coords)

        cell_before_down = runtime.var_runtime_current_cell_ptr.index
        coords_before_down = runtime.var_current_map_coords.snapshot()

        pre_down, post_down, out_down = harness.run_until_step_with_states(_frame_input_for_keys("s"))
        self.assertEqual(pre_down, FSM_STATE_GAMEPLAY_BRANCH)
        self.assertEqual(post_down, FSM_STATE_GAMEPLAY_BRANCH)
        transitions_after_down = self._assert_transition_chain(
            harness,
            start_state=FSM_STATE_GAMEPLAY_BRANCH,
            expected_post_states=(FSM_STATE_GAMEPLAY_BRANCH,),
            expected_delays=(_GAMEPLAY_DELAY_AFTER_STEP,),
        )
        cell_after_down = runtime.var_runtime_current_cell_ptr.index
        coords_after_down = runtime.var_current_map_coords.snapshot()

        self.assertEqual(
            cell_after_down - cell_before_down,
            0x32,
            "Down in gameplay must move exactly one cell (no teleport)",
        )
        self.assertEqual(len(transitions_after_down), 1)
        self.assertEqual(coords_after_down, (coords_before_down[0], coords_before_down[1] + 1))
        self.assertEqual(int(out_down.timing.delay_after_step_frames), _GAMEPLAY_DELAY_AFTER_STEP)
        self.assertLessEqual(harness.step_counter, 100)

    def test_splash_down_requires_release_and_preserves_source_start_position(self) -> None:
        harness = self._build_menu_harness_from_reset()
        runtime = harness.runtime
        expected_start_cell, expected_start_coords = self._mode0_source_start_cell_and_coords(runtime)

        pre_start, post_start, start_out = harness.run_until_step_with_states(_frame_input_for_keys("6"))
        self.assertEqual(pre_start, FSM_STATE_MENU_IDLE_POLL_FRAME)
        self.assertEqual(post_start, FSM_STATE_STREAM_INTERMISSION_FRAME)
        self.assertEqual(int(start_out.timing.delay_after_step_frames), 0)

        pre_held_start, post_held_start, held_start_out = harness.run_until_step_with_states(_frame_input_for_keys("6"))
        self.assertEqual(pre_held_start, FSM_STATE_STREAM_INTERMISSION_FRAME)
        self.assertEqual(post_held_start, FSM_STATE_STREAM_INTERMISSION_FRAME)
        self.assertEqual(int(held_start_out.timing.delay_after_step_frames), 0)

        pre_down, post_down, out_down = harness.run_until_step_with_states(_frame_input_for_keys("s"))
        self.assertEqual(pre_down, FSM_STATE_STREAM_INTERMISSION_FRAME)
        self.assertEqual(post_down, FSM_STATE_WAIT_KEYBOARD_RELEASE_FRAME)
        self.assertEqual(int(out_down.timing.delay_after_step_frames), 0)
        self.assertEqual(runtime.var_runtime_current_cell_ptr.index, expected_start_cell)
        self.assertEqual(runtime.var_current_map_coords.snapshot(), expected_start_coords)

        pre_hold_down, post_hold_down, hold_down_out = harness.run_until_step_with_states(_frame_input_for_keys("s"))
        self.assertEqual(pre_hold_down, FSM_STATE_WAIT_KEYBOARD_RELEASE_FRAME)
        self.assertEqual(post_hold_down, FSM_STATE_WAIT_KEYBOARD_RELEASE_FRAME)
        self.assertEqual(int(hold_down_out.timing.delay_after_step_frames), 0)
        self.assertEqual(runtime.var_runtime_current_cell_ptr.index, expected_start_cell)
        self.assertEqual(runtime.var_current_map_coords.snapshot(), expected_start_coords)

        pre_release, post_release, release_out = harness.run_until_step_with_states(_NEUTRAL_INPUT)
        self.assertEqual(pre_release, FSM_STATE_WAIT_KEYBOARD_RELEASE_FRAME)
        self.assertEqual(post_release, FSM_STATE_GAMEPLAY_TICK_STAGE_1_FRAME)
        self.assertEqual(int(release_out.timing.delay_after_step_frames), _GAMEPLAY_DELAY_AFTER_STEP)

        _ = self._assert_transition_chain(
            harness,
            start_state=FSM_STATE_GAMEPLAY_TICK_STAGE_1_FRAME,
            expected_post_states=self._EXPECTED_POST_TICK1_TO_BRANCH,
            expected_delays=self._EXPECTED_POST_TICK1_TO_BRANCH_DELAYS,
        )
        self.assertEqual(runtime._fsm_state, FSM_STATE_GAMEPLAY_BRANCH)
        self.assertEqual(runtime.var_runtime_current_cell_ptr.index, expected_start_cell)
        self.assertEqual(runtime.var_current_map_coords.snapshot(), expected_start_coords)

    def test_splash_second_start_requires_release_before_gameplay(self) -> None:
        harness = self._build_menu_harness_from_reset()
        runtime = harness.runtime
        expected_start_cell, expected_start_coords = self._mode0_source_start_cell_and_coords(runtime)

        pre_start, post_start, start_out = harness.run_until_step_with_states(_frame_input_for_keys("6"))
        self.assertEqual(pre_start, FSM_STATE_MENU_IDLE_POLL_FRAME)
        self.assertEqual(post_start, FSM_STATE_STREAM_INTERMISSION_FRAME)
        self.assertEqual(int(start_out.timing.delay_after_step_frames), 0)

        pre_splash, post_splash, splash_out = harness.run_until_step_with_states(_NEUTRAL_INPUT)
        self.assertEqual(pre_splash, FSM_STATE_STREAM_INTERMISSION_FRAME)
        self.assertEqual(post_splash, FSM_STATE_STREAM_INTERMISSION_FRAME)
        self.assertEqual(int(splash_out.timing.delay_after_step_frames), 0)

        pre_exit, post_exit, out_exit = harness.run_until_step_with_states(_frame_input_for_keys("6"))
        self.assertEqual(pre_exit, FSM_STATE_STREAM_INTERMISSION_FRAME)
        self.assertEqual(post_exit, FSM_STATE_WAIT_KEYBOARD_RELEASE_FRAME)
        self.assertEqual(int(out_exit.timing.delay_after_step_frames), 0)
        self.assertEqual(runtime.var_runtime_current_cell_ptr.index, expected_start_cell)
        self.assertEqual(runtime.var_current_map_coords.snapshot(), expected_start_coords)

        pre_release, post_release, release_out = harness.run_until_step_with_states(_NEUTRAL_INPUT)
        self.assertEqual(pre_release, FSM_STATE_WAIT_KEYBOARD_RELEASE_FRAME)
        self.assertEqual(post_release, FSM_STATE_GAMEPLAY_TICK_STAGE_1_FRAME)
        self.assertEqual(int(release_out.timing.delay_after_step_frames), _GAMEPLAY_DELAY_AFTER_STEP)

        _ = self._assert_transition_chain(
            harness,
            start_state=FSM_STATE_GAMEPLAY_TICK_STAGE_1_FRAME,
            expected_post_states=self._EXPECTED_POST_TICK1_TO_BRANCH,
            expected_delays=self._EXPECTED_POST_TICK1_TO_BRANCH_DELAYS,
        )
        self.assertEqual(runtime._fsm_state, FSM_STATE_GAMEPLAY_BRANCH)
        self.assertEqual(runtime.var_runtime_current_cell_ptr.index, expected_start_cell)
        self.assertEqual(runtime.var_current_map_coords.snapshot(), expected_start_coords)


if __name__ == "__main__":
    unittest.main()
