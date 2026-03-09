from __future__ import annotations

import io
import json
import unittest

from alien_evolution.fileio.runner import iter_jsonl_frame_inputs_from_stream, run_frame_loop
from alien_evolution.zx.runtime import AudioClockSnapshot, AudioNoteEvent, AudioResetEvent, FrameInput, StepOutput


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
            audio_events=(
                AudioNoteEvent(
                    epoch_id=0,
                    start_tick=7,
                    duration_ticks=12,
                    note="A2",
                    waveform="S",
                    effect="N",
                    volume=5,
                    priority=10,
                ),
            ),
            border_color=0,
        )


class _AudioClockCaptureRuntime:
    def __init__(self) -> None:
        self.audio_clocks: list[AudioClockSnapshot] = []
        self._step_calls = 0

    def reset(self) -> None:
        self.audio_clocks.clear()
        self._step_calls = 0

    def step(self, frame_input: FrameInput) -> StepOutput:
        assert frame_input.audio_clock is not None
        self.audio_clocks.append(frame_input.audio_clock)
        self._step_calls += 1
        audio_events = ()
        if self._step_calls == 1:
            audio_events = (AudioResetEvent(epoch_id=0, cut_tick=5, next_epoch_id=1),)
        return StepOutput(
            screen_bitmap=b"",
            screen_attrs=b"",
            flash_phase=0,
            audio_events=audio_events,
            border_color=0,
        )


class FileIORunnerTests(unittest.TestCase):
    def test_run_frame_loop_jsonl_includes_audio_event_ticks(self) -> None:
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
            frame_record["output"]["audio_events"][0]["start_tick"],
            7,
        )
        self.assertEqual(
            frame_record["output"]["audio_events"][0]["waveform"],
            "S",
        )
        self.assertEqual(
            frame_record["output"]["audio_events"][0]["note"],
            "A2",
        )
        self.assertEqual(
            frame_record["output"]["audio_events"][0]["effect"],
            "N",
        )

    def test_run_frame_loop_jsonl_includes_effective_audio_clock(self) -> None:
        runtime = _SingleFrameRuntime()
        sink = io.StringIO()

        run_frame_loop(
            runtime,
            frames=1,
            input_frames=None,
            input_source=None,
            jsonl_output=sink,
            flush_jsonl=False,
            screen_output=None,
            reset_runtime=True,
        )

        lines = [line for line in sink.getvalue().splitlines() if line.strip()]
        frame_record = json.loads(lines[1])
        self.assertEqual(frame_record["input"]["audio_clock"]["current_epoch_id"], 0)
        self.assertEqual(frame_record["input"]["audio_clock"]["safe_start_tick"], 3)
        self.assertEqual(frame_record["input"]["audio_clock"]["fill_until_tick"], 96)

    def test_run_frame_loop_synthesizes_audio_clock_and_applies_reset_cutover(self) -> None:
        runtime = _AudioClockCaptureRuntime()

        executed = run_frame_loop(
            runtime,
            frames=4,
            input_frames=None,
            input_source=None,
            jsonl_output=None,
            flush_jsonl=False,
            screen_output=None,
            reset_runtime=True,
        )

        self.assertEqual(executed, 4)
        self.assertEqual([clock.current_epoch_id for clock in runtime.audio_clocks], [0, 0, 0, 1])
        self.assertEqual([clock.safe_start_tick for clock in runtime.audio_clocks], [3, 5, 7, 5])

    def test_jsonl_parser_accepts_explicit_audio_clock_override(self) -> None:
        stream = io.StringIO(
            json.dumps(
                {
                    "joy_kempston": 0,
                    "keyboard_rows": [255] * 8,
                    "audio_clock": {
                        "current_epoch_id": 3,
                        "safe_start_tick": 17,
                        "fill_until_tick": 42,
                    },
                }
            )
            + "\n"
        )

        frame_input = next(iter_jsonl_frame_inputs_from_stream(stream, source="test"))

        assert frame_input.audio_clock is not None
        self.assertEqual(frame_input.audio_clock.current_epoch_id, 3)
        self.assertEqual(frame_input.audio_clock.safe_start_tick, 17)
        self.assertEqual(frame_input.audio_clock.fill_until_tick, 42)

    def test_run_frame_loop_passes_explicit_audio_clock_override_through(self) -> None:
        runtime = _AudioClockCaptureRuntime()
        explicit_clock = AudioClockSnapshot(current_epoch_id=2, safe_start_tick=11, fill_until_tick=40)

        run_frame_loop(
            runtime,
            frames=1,
            input_frames=iter((FrameInput(audio_clock=explicit_clock),)),
            input_source="test",
            jsonl_output=None,
            flush_jsonl=False,
            screen_output=None,
            reset_runtime=True,
        )

        self.assertEqual(runtime.audio_clocks, [explicit_clock])


if __name__ == "__main__":
    unittest.main()
