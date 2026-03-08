from __future__ import annotations

import sys
import unittest
from unittest.mock import patch

from alien_evolution.pyxel.sound import AudioDebugStats
from alien_evolution.pyxel.runner import (
    CheatCommandBuffer,
    DEFAULT_QUICKSAVE_FILENAME,
    DEFAULT_HISTORY_INTERVAL_HOST_FRAMES,
    RuntimeStateHistory,
    ScreenMessageQueue,
    _format_audio_debug_overlay_lines,
    _maybe_apply_runtime_cheat,
    run_pyxel_game,
)
from alien_evolution.zx.runtime import FrameInput, StepOutput, StepTiming


class _DummyStatefulRuntime:
    def __init__(self) -> None:
        self.value = 0

    def save_state(self) -> dict[str, object]:
        return {"value": self.value}

    def load_state(self, state: dict[str, object]) -> None:
        self.value = int(state["value"])


class _DummyAutosaveRuntime(_DummyStatefulRuntime):
    def save_autosave_state(self) -> dict[str, object]:
        return {"value": self.value, "compact": True}


class _DummyCheatRuntime:
    def __init__(self) -> None:
        self.calls: list[tuple[str, ...]] = []

    def apply_cheat_sequence(self, symbols) -> bool:
        typed = tuple(str(symbol) for symbol in symbols)
        self.calls.append(typed)
        return "".join(typed) == "lvl1"


class _DummyFrameRuntime:
    def __init__(self) -> None:
        self.step_calls = 0
        self.advance_host_frame_calls = 0
        self._last_output = StepOutput(
            screen_bitmap=b"idle",
            screen_attrs=b"attrs",
            flash_phase=0,
            audio_events=(),
            border_color=0,
            timing=StepTiming(delay_after_step_frames=0),
        )

    def reset(self) -> None:
        self.step_calls = 0
        self.advance_host_frame_calls = 0
        self._last_output = StepOutput(
            screen_bitmap=b"idle",
            screen_attrs=b"attrs",
            flash_phase=0,
            audio_events=(),
            border_color=0,
            timing=StepTiming(delay_after_step_frames=0),
        )

    def step(self, frame_input: FrameInput) -> StepOutput:
        self.step_calls += 1
        self._last_output = StepOutput(
            screen_bitmap=f"frame-{self.step_calls}".encode("ascii"),
            screen_attrs=b"attrs",
            flash_phase=0,
            audio_events=(),
            border_color=0,
            timing=StepTiming(delay_after_step_frames=2),
        )
        return self._last_output

    def advance_host_frame(self) -> None:
        self.advance_host_frame_calls += 1

    def snapshot_output(self) -> StepOutput:
        return self._last_output


class _FakePyxelRunner:
    def __init__(self, runtime: _DummyFrameRuntime) -> None:
        self.runtime = runtime
        self.advance_calls_after_draw: list[int] = []
        self.step_calls_after_draw: list[int] = []

    def init(self, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
        return

    def run(self, update, draw) -> None:  # type: ignore[no-untyped-def]
        update()
        draw()
        self.advance_calls_after_draw.append(self.runtime.advance_host_frame_calls)
        self.step_calls_after_draw.append(self.runtime.step_calls)
        update()
        draw()
        self.advance_calls_after_draw.append(self.runtime.advance_host_frame_calls)
        self.step_calls_after_draw.append(self.runtime.step_calls)

    def text(self, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
        return


class _FakeAudioPlayer:
    def clock_snapshot(self, *, now_s: float):  # type: ignore[no-untyped-def]
        return None

    def submit(self, events, *, now_s: float) -> None:  # type: ignore[no-untyped-def]
        return

    def update(self, *, now_s: float) -> None:  # type: ignore[no-untyped-def]
        return


class PyxelStateHistoryTests(unittest.TestCase):
    def test_default_interval_is_500_host_frames(self) -> None:
        self.assertEqual(DEFAULT_HISTORY_INTERVAL_HOST_FRAMES, 500)
        self.assertEqual(DEFAULT_QUICKSAVE_FILENAME, "pyxel_quicksave.state.json")

    def test_history_capture_interval_and_rollback(self) -> None:
        runtime = _DummyStatefulRuntime()
        history = RuntimeStateHistory(interval_host_frames=5, max_checkpoints=10)

        history.force_capture(runtime, host_frame_index=0)
        runtime.value = 10
        self.assertFalse(history.maybe_capture(runtime, host_frame_index=4))
        self.assertTrue(history.maybe_capture(runtime, host_frame_index=5))
        runtime.value = 20
        history.force_capture(runtime, host_frame_index=9)

        runtime.value = 99
        self.assertTrue(history.rollback(runtime, steps=1))
        self.assertEqual(runtime.value, 10)

    def test_history_uses_compact_autosave_if_runtime_supports_it(self) -> None:
        runtime = _DummyAutosaveRuntime()
        history = RuntimeStateHistory(interval_host_frames=5, max_checkpoints=10)

        history.force_capture(runtime, host_frame_index=0)
        runtime.value = 7
        history.force_capture(runtime, host_frame_index=5)

        runtime.value = 99
        self.assertTrue(history.rollback(runtime, steps=1))
        self.assertEqual(runtime.value, 0)


class ScreenMessageQueueTests(unittest.TestCase):
    def test_queue_expires_messages_after_ttl(self) -> None:
        queue = ScreenMessageQueue(ttl_host_frames=5)

        queue.push("m1", host_frame_index=0)
        queue.prune(host_frame_index=4)
        self.assertEqual(queue.messages, ("m1",))

        queue.prune(host_frame_index=5)
        self.assertEqual(queue.messages, ())

    def test_queue_grows_top_down_and_shifts_up_after_expire(self) -> None:
        queue = ScreenMessageQueue(ttl_host_frames=3)

        queue.push("oldest", host_frame_index=0)
        queue.push("middle", host_frame_index=1)
        queue.push("newest", host_frame_index=2)
        self.assertEqual(queue.messages, ("oldest", "middle", "newest"))

        queue.prune(host_frame_index=3)
        self.assertEqual(queue.messages, ("middle", "newest"))

        queue.prune(host_frame_index=4)
        self.assertEqual(queue.messages, ("newest",))

    def test_audio_debug_overlay_line_formats_loss_breakdown(self) -> None:
        lines = _format_audio_debug_overlay_lines(
            AudioDebugStats(
                late_head_ticks_lost=5,
                late_partially_played_events=2,
                fully_missed_events=3,
                fully_missed_ticks=7,
                saturation_dropped_events=1,
                saturation_dropped_ticks=11,
                active_epoch_id=4,
                current_playhead_tick=99,
            )
        )

        self.assertEqual(lines[0], "AUD ep=4 tick=99 loss=23t")
        self.assertEqual(lines[1], "late=5t/2e miss=7t/3e sat=11t/1e")

    def test_runner_keeps_fresh_step_frame_visible_until_next_draw(self) -> None:
        runtime = _DummyFrameRuntime()
        fake_pyxel = _FakePyxelRunner(runtime)
        blit_bitmaps: list[bytes] = []

        with (
            patch.dict(sys.modules, {"pyxel": fake_pyxel}),
            patch("alien_evolution.pyxel.runner.PyxelAudioPlayer", return_value=_FakeAudioPlayer()),
            patch(
                "alien_evolution.pyxel.runner.read_frame_input",
                return_value=FrameInput(joy_kempston=0, keyboard_rows=(0xFF,) * 8),
            ),
            patch("alien_evolution.pyxel.runner.apply_zx_palette", return_value=None),
            patch(
                "alien_evolution.pyxel.runner.blit_zx_screen_to_pyxel",
                side_effect=lambda bitmap, attrs, **kwargs: blit_bitmaps.append(bytes(bitmap)),
            ),
            patch("alien_evolution.pyxel.runner.time.perf_counter", side_effect=[0.0, 0.04, 0.06]),
        ):
            run_pyxel_game(
                runtime,
                title="test",
                fps=50,
                dev_tools=False,
                history_interval_host_frames=0,
            )

        self.assertEqual(fake_pyxel.advance_calls_after_draw, [0, 1])
        self.assertEqual(fake_pyxel.step_calls_after_draw, [1, 1])
        self.assertEqual(blit_bitmaps, [b"frame-1"])


class CheatCommandBufferTests(unittest.TestCase):
    def test_buffer_dispatches_after_idle_timeout(self) -> None:
        buffer = CheatCommandBuffer(inactivity_host_frames=5)

        buffer.push(("l", "v", "l", "1"), host_frame_index=10)
        self.assertIsNone(buffer.poll_ready(host_frame_index=14))
        self.assertEqual(buffer.poll_ready(host_frame_index=15), ("l", "v", "l", "1"))

    def test_dispatch_clears_buffer(self) -> None:
        buffer = CheatCommandBuffer(inactivity_host_frames=3)

        buffer.push(("l", "v", "l", "1"), host_frame_index=0)
        self.assertEqual(buffer.poll_ready(host_frame_index=3), ("l", "v", "l", "1"))
        self.assertEqual(buffer.pending_text, "")
        self.assertIsNone(buffer.poll_ready(host_frame_index=10))

    def test_disabled_mode_never_dispatches(self) -> None:
        runtime = _DummyCheatRuntime()
        buffer = CheatCommandBuffer(inactivity_host_frames=1)

        buffer.push(("l", "v", "l", "1"), host_frame_index=0)
        result = _maybe_apply_runtime_cheat(
            runtime,
            command_buffer=buffer,
            typed_chars=(),
            host_frame_index=1,
            cheats_enabled=False,
        )

        self.assertIsNone(result)
        self.assertEqual(runtime.calls, [])

if __name__ == "__main__":
    unittest.main()

