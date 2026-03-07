from __future__ import annotations

import sys
import unittest
from unittest.mock import patch

from alien_evolution.alienevolution.logic import AlienEvolutionPort
from alien_evolution.pyxel.sound import (
    PyxelAudioPlayer,
    _noise_note_from_hz,
    _note_from_hz,
    _stream_special_noise_note_from_hz,
)
from alien_evolution.zx.pointers import BlockPtr
from alien_evolution.zx.runtime import (
    AudioClockSnapshot,
    AudioNoteEvent,
    AudioResetEvent,
    FrameInput,
)


class _FakeSound:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def set(self, **kwargs) -> None:  # type: ignore[no-untyped-def]
        self.calls.append(dict(kwargs))


class _FakeChannel:
    def __init__(self) -> None:
        self.gain = 1.0


class _FakePyxel:
    def __init__(self) -> None:
        self.sounds = [_FakeSound() for _ in range(64)]
        self.channels = [_FakeChannel() for _ in range(4)]
        self.play_calls: list[tuple[int, tuple[int, ...]]] = []
        self.stop_calls: list[int | None] = []
        self._busy = [False, False, False, False]

    def play(self, channel: int, slots) -> None:  # type: ignore[no-untyped-def]
        if isinstance(slots, list):
            slot_tuple = tuple(int(slot) for slot in slots)
        else:
            slot_tuple = (int(slots),)
        self.play_calls.append((int(channel), slot_tuple))
        self._busy[int(channel)] = True

    def stop(self, channel=None) -> None:  # type: ignore[no-untyped-def]
        token = None if channel is None else int(channel)
        self.stop_calls.append(token)
        if token is None:
            self._busy = [False, False, False, False]
            return
        self._busy[token] = False

    def play_pos(self, channel: int):
        return 0 if self._busy[int(channel)] else None


class PyxelSoundTimelineTests(unittest.TestCase):
    def test_note_from_hz_uses_pyxel_octave_base(self) -> None:
        self.assertEqual(_note_from_hz(429.89), "A2")
        self.assertEqual(_note_from_hz(440.0), "A2")
        self.assertEqual(_note_from_hz(340.187), "F2")
        self.assertEqual(_note_from_hz(1760.0), "A4")

    def test_noise_note_from_hz_compresses_ultrasonic_range(self) -> None:
        self.assertEqual(_noise_note_from_hz(2200.0), "A#4")
        self.assertEqual(_noise_note_from_hz(10000.0), "B4")
        self.assertEqual(_noise_note_from_hz(120.0), "F4")

    def test_stream_special_noise_note_stays_in_bright_bins(self) -> None:
        self.assertEqual(_stream_special_noise_note_from_hz(2502.0), "F4")
        self.assertEqual(_stream_special_noise_note_from_hz(7299.0), "A4")
        self.assertEqual(_stream_special_noise_note_from_hz(18199.0), "B4")

    def test_schedule_reset_switches_default_emit_epoch(self) -> None:
        runtime = AlienEvolutionPort()
        runtime.begin_frame(
            FrameInput(
                audio_clock=AudioClockSnapshot(current_epoch_id=0, current_tick=12),
            )
        )

        runtime.emit_immediate_sfx(
            lane=2,
            tone="S",
            freq_hz=440.0,
            duration_ticks=5,
            volume=5,
            source="rom_beeper",
        )
        next_epoch = runtime.schedule_reset(20)
        runtime.emit_note_event(
            lane=0,
            tone="S",
            freq_hz=220.0,
            start_tick=0,
            duration_ticks=10,
            volume=5,
            source="stream_music",
        )
        events = runtime.end_frame().audio_events

        self.assertEqual(next_epoch, 1)
        self.assertEqual(len(events), 3)
        self.assertIsInstance(events[0], AudioNoteEvent)
        self.assertIsInstance(events[1], AudioResetEvent)
        self.assertIsInstance(events[2], AudioNoteEvent)
        assert isinstance(events[0], AudioNoteEvent)
        assert isinstance(events[1], AudioResetEvent)
        assert isinstance(events[2], AudioNoteEvent)
        self.assertEqual(events[0].epoch_id, 0)
        self.assertEqual(events[0].start_tick, 12)
        self.assertEqual(events[1].epoch_id, 0)
        self.assertEqual(events[1].cut_tick, 20)
        self.assertEqual(events[1].next_epoch_id, 1)
        self.assertEqual(events[2].epoch_id, 1)
        self.assertEqual(events[2].start_tick, 0)

    def test_emit_immediate_sfx_uses_audio_clock_snapshot(self) -> None:
        runtime = AlienEvolutionPort()
        runtime.begin_frame(
            FrameInput(
                audio_clock=AudioClockSnapshot(current_epoch_id=0, current_tick=17),
            )
        )

        runtime.emit_immediate_sfx(
            lane=2,
            tone="S",
            freq_hz=440.0,
            duration_ticks=5,
            volume=5,
            source="rom_beeper",
        )
        event = runtime.end_frame().audio_events[0]

        assert isinstance(event, AudioNoteEvent)
        self.assertEqual(event.start_tick, 17)
        self.assertEqual(event.lane, 2)
        self.assertEqual(event.source, "rom_beeper")

    def test_stream_silence_advances_other_lane_cursor(self) -> None:
        runtime = AlienEvolutionPort()
        runtime.begin_frame(FrameInput())
        runtime._reset_stream_audio_timing_state()

        runtime._emit_stream_semantic_mix(iterations=256, fast_wraps=8, slow_wraps=0)
        runtime._emit_stream_semantic_mix(iterations=256, fast_wraps=0, slow_wraps=8)
        events = runtime.end_frame().audio_events

        self.assertEqual(len(events), 2)
        assert isinstance(events[0], AudioNoteEvent)
        assert isinstance(events[1], AudioNoteEvent)
        self.assertEqual(events[0].lane, 0)
        self.assertEqual(events[1].lane, 1)
        self.assertEqual(events[1].start_tick, events[0].duration_ticks)

    def test_fsm_start_stream_queues_mode_reset(self) -> None:
        runtime = AlienEvolutionPort()
        runtime.begin_frame(
            FrameInput(
                audio_clock=AudioClockSnapshot(current_epoch_id=0, current_tick=8),
            )
        )
        runtime.emit_immediate_sfx(
            lane=2,
            tone="S",
            freq_hz=440.0,
            duration_ticks=5,
            volume=5,
            source="rom_beeper",
        )

        runtime._fsm_start_stream(
            stream_a=BlockPtr(runtime.const_scenario_preset_b_stream_1, 0x0000),
            stream_b=BlockPtr(runtime.const_scenario_preset_b_stream_2, 0x0000),
            abort_on_keypress=True,
            return_state="MENU_IDLE_POLL_FRAME",
        )

        reset_events = [event for event in runtime._audio_events if isinstance(event, AudioResetEvent)]
        self.assertEqual(len(reset_events), 1)
        self.assertEqual(reset_events[0].epoch_id, 0)
        self.assertEqual(reset_events[0].next_epoch_id, 1)

    def test_clock_snapshot_follows_monotonic_time(self) -> None:
        player = PyxelAudioPlayer()
        player._epoch_origin_time_s = 10.0

        snap = player.clock_snapshot(now_s=10.5)

        self.assertEqual(snap.current_epoch_id, 0)
        self.assertEqual(snap.current_tick, 60)

    def test_reset_switches_epoch_on_wall_clock_cut(self) -> None:
        fake_pyxel = _FakePyxel()
        player = PyxelAudioPlayer()
        player._epoch_origin_time_s = 10.0
        player.submit((AudioResetEvent(epoch_id=0, cut_tick=12, next_epoch_id=1),))

        with patch.dict(sys.modules, {"pyxel": fake_pyxel}):
            snap = player.clock_snapshot(now_s=10.1)

        self.assertEqual(snap.current_epoch_id, 1)
        self.assertEqual(snap.current_tick, 0)
        self.assertEqual(fake_pyxel.stop_calls, [None])

    def test_scheduler_keeps_explicit_rest_between_equal_notes(self) -> None:
        fake_pyxel = _FakePyxel()
        player = PyxelAudioPlayer()
        player._epoch_origin_time_s = 10.0
        player.submit(
            (
                AudioNoteEvent(
                    epoch_id=0,
                    start_tick=0,
                    duration_ticks=5,
                    lane=0,
                    tone="S",
                    freq_hz=440.0,
                    volume=5,
                    source="stream_music",
                    priority=10,
                ),
                AudioNoteEvent(
                    epoch_id=0,
                    start_tick=8,
                    duration_ticks=5,
                    lane=0,
                    tone="S",
                    freq_hz=440.0,
                    volume=5,
                    source="stream_music",
                    priority=10,
                ),
            )
        )

        with patch.dict(sys.modules, {"pyxel": fake_pyxel}):
            player.update(now_s=10.0)

        segments = player._channel_plans[0].segments
        self.assertGreaterEqual(len(segments), 3)
        self.assertFalse(segments[0].is_rest)
        self.assertTrue(segments[1].is_rest)
        self.assertFalse(segments[2].is_rest)
        self.assertEqual(segments[1].ticks, 3)

    def test_long_note_splits_only_for_pyxel_limit(self) -> None:
        fake_pyxel = _FakePyxel()
        player = PyxelAudioPlayer()
        player._epoch_origin_time_s = 10.0
        player.submit(
            (
                AudioNoteEvent(
                    epoch_id=0,
                    start_tick=0,
                    duration_ticks=400,
                    lane=0,
                    tone="S",
                    freq_hz=440.0,
                    volume=5,
                    source="stream_music",
                    priority=10,
                ),
            )
        )

        with patch.dict(sys.modules, {"pyxel": fake_pyxel}):
            player.update(now_s=10.0)

        speeds = [call["speed"] for sound in fake_pyxel.sounds for call in sound.calls]
        self.assertIn(255, speeds)
        self.assertIn(145, speeds)
        self.assertTrue(all(int(speed) <= 255 for speed in speeds))

    def test_priority_based_scheduler_steals_low_priority_voice(self) -> None:
        fake_pyxel = _FakePyxel()
        player = PyxelAudioPlayer()
        player._epoch_origin_time_s = 10.0
        player.submit(
            tuple(
                AudioNoteEvent(
                    epoch_id=0,
                    start_tick=0,
                    duration_ticks=30,
                    lane=lane,
                    tone="S",
                    freq_hz=220.0 + lane,
                    volume=5,
                    source="stream_music",
                    priority=10,
                )
                for lane in range(4)
            )
        )

        with patch.dict(sys.modules, {"pyxel": fake_pyxel}):
            player.update(now_s=10.0)
            initial_stop_count = len(fake_pyxel.stop_calls)
            player.submit(
                (
                    AudioNoteEvent(
                        epoch_id=0,
                        start_tick=5,
                        duration_ticks=5,
                        lane=9,
                        tone="S",
                        freq_hz=880.0,
                        volume=5,
                        source="rom_beeper",
                        priority=30,
                    ),
                )
            )
            player.update(now_s=10.0)

        self.assertGreater(len(fake_pyxel.stop_calls), initial_stop_count)
        self.assertTrue(
            any(
                any(segment.priority == 30 for segment in plan.segments if not segment.is_rest)
                for plan in player._channel_plans
            )
        )

    def test_late_update_does_not_change_wall_clock_tick_rate(self) -> None:
        fake_pyxel = _FakePyxel()
        player = PyxelAudioPlayer()
        player._epoch_origin_time_s = 10.0
        player.submit(
            (
                AudioNoteEvent(
                    epoch_id=0,
                    start_tick=0,
                    duration_ticks=60,
                    lane=0,
                    tone="S",
                    freq_hz=440.0,
                    volume=5,
                    source="stream_music",
                    priority=10,
                ),
            )
        )

        with patch.dict(sys.modules, {"pyxel": fake_pyxel}):
            player.update(now_s=10.0)
            snap = player.clock_snapshot(now_s=10.6)

        self.assertEqual(snap.current_tick, 72)
        self.assertTrue(fake_pyxel.play_calls)


if __name__ == "__main__":
    unittest.main()
