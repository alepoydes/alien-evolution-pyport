from __future__ import annotations

import unittest

from alien_evolution.alienevolution.logic import (
    LEVEL_COMPLETE_ROLL_TARGET_FRAMES,
    AlienEvolutionPort,
)


def _read_score_value(runtime: AlienEvolutionPort) -> int:
    return (
        ((runtime.var_runtime_aux_c8_lo & 0xFF) * 10_000)
        + ((runtime.var_runtime_aux_c8_hi & 0xFF) * 1_000)
        + ((runtime.var_runtime_aux_ca & 0xFF) * 100)
        + ((runtime.var_runtime_aux_cb & 0xFF) * 10)
        + (runtime.var_runtime_aux_cc & 0xFF)
    ) % 100_000


def _write_score_value(runtime: AlienEvolutionPort, value: int) -> None:
    score = int(value) % 100_000
    runtime.var_runtime_aux_c8_lo = (score // 10_000) % 10
    runtime.var_runtime_aux_c8_hi = (score // 1_000) % 10
    runtime.var_runtime_aux_ca = (score // 100) % 10
    runtime.var_runtime_aux_cb = (score // 10) % 10
    runtime.var_runtime_aux_cc = score % 10


class TransitionWaitLoopSpy(AlienEvolutionPort):
    def __init__(self) -> None:
        super().__init__()
        self.yield_frame_calls = 0
        self.yield_gameplay_frame_calls = 0
        self.transition_beeper_calls = 0

    def _yield_frame(self) -> None:
        self.yield_frame_calls += 1

    def _yield_gameplay_frame(self) -> None:
        self.yield_gameplay_frame_calls += 1

    def fn_paced_beeper_helper_transitions_panel_fill(self) -> None:
        self.transition_beeper_calls += 1


class TransitionWaitLoopAudioSpy(AlienEvolutionPort):
    def __init__(self) -> None:
        super().__init__()
        self.per_frame_audio_counts: list[int] = []

    def _yield_frame(self) -> None:
        self.per_frame_audio_counts.append(len(self._audio_commands))
        self._audio_commands.clear()


class LevelTransitionWaitLoopTests(unittest.TestCase):
    def test_level_complete_roll_adds_exact_500_points(self) -> None:
        runtime = TransitionWaitLoopSpy()
        _write_score_value(runtime, 99_800)
        start = _read_score_value(runtime)

        runtime.fn_level_transition_wait_loop()

        end = _read_score_value(runtime)
        self.assertEqual(end, (start + 500) % 100_000)

    def test_level_complete_roll_uses_125_host_frames(self) -> None:
        runtime = TransitionWaitLoopSpy()

        runtime.fn_level_transition_wait_loop()

        self.assertEqual(runtime.yield_frame_calls, LEVEL_COMPLETE_ROLL_TARGET_FRAMES)

    def test_level_complete_roll_uses_native_frame_pacing(self) -> None:
        runtime = TransitionWaitLoopSpy()

        runtime.fn_level_transition_wait_loop()

        self.assertEqual(runtime.yield_gameplay_frame_calls, 0)

    def test_level_complete_roll_beeper_packet_once_per_frame(self) -> None:
        runtime = TransitionWaitLoopSpy()

        runtime.fn_level_transition_wait_loop()

        self.assertEqual(runtime.transition_beeper_calls, LEVEL_COMPLETE_ROLL_TARGET_FRAMES)

    def test_level_complete_roll_audio_commands_match_frame_count(self) -> None:
        runtime = TransitionWaitLoopAudioSpy()

        runtime.fn_level_transition_wait_loop()

        self.assertEqual(len(runtime.per_frame_audio_counts), LEVEL_COMPLETE_ROLL_TARGET_FRAMES)
        self.assertTrue(all(count == 1 for count in runtime.per_frame_audio_counts))


if __name__ == "__main__":
    unittest.main()
