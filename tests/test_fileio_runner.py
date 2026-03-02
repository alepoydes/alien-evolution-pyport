from __future__ import annotations

import io
import json
import unittest

from alien_evolution.fileio.runner import run_frame_loop
from alien_evolution.zx.runtime import AudioCommand, FrameInput, StepOutput


class _SingleFrameRuntime:
    def __init__(self) -> None:
        self._step_calls = 0
        self._was_reset = False

    def reset(self) -> None:
        self._was_reset = True
        self._step_calls = 0

    def step(self, frame_input: FrameInput) -> StepOutput:
        self._step_calls += 1
        return StepOutput(
            screen_bitmap=b"",
            screen_attrs=b"",
            flash_phase=0,
            audio_commands=(
                AudioCommand(
                    tone="S",
                    freq_hz=440.0,
                    duration_s=0.1,
                    volume=5,
                    channel=0,
                    source="stream_music",
                    start_delay_ticks=7,
                ),
            ),
            border_color=0,
        )


class FileIORunnerTests(unittest.TestCase):
    def test_run_frame_loop_jsonl_includes_start_delay_ticks(self) -> None:
        runtime = _SingleFrameRuntime()
        sink = io.StringIO()

        executed = run_frame_loop(
            runtime,
            frames=1,
            input_frames=None,
            input_source=None,
            jsonl_output=sink,
            flush_jsonl=False,
            screen_output=None,
            reset_runtime=True,
        )

        self.assertEqual(executed, 1)
        lines = [line for line in sink.getvalue().splitlines() if line.strip()]
        self.assertEqual(len(lines), 2)
        frame_record = json.loads(lines[1])
        self.assertEqual(
            frame_record["output"]["audio_commands"][0]["start_delay_ticks"],
            7,
        )


if __name__ == "__main__":
    unittest.main()
