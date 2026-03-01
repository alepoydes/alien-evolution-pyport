from __future__ import annotations

import unittest

from alien_evolution.pyxel.runner import (
    DEFAULT_QUICKSAVE_FILENAME,
    DEFAULT_HISTORY_INTERVAL_HOST_FRAMES,
    RuntimeStateHistory,
    ScreenMessageQueue,
)


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

if __name__ == "__main__":
    unittest.main()

