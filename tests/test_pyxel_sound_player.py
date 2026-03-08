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
                audio_clock=AudioClockSnapshot(current_epoch_id=0, safe_start_tick=12, fill_until_tick=12),
            )
        )

        runtime.emit_immediate_sfx(
            waveform="S",
            freq_hz=440.0,
            duration_ticks=5,
            volume=5,
            start_tick=runtime.audio_clock.safe_start_tick,
            source="rom_beeper",
        )
        next_epoch = runtime.schedule_reset(20)
        runtime.emit_note_event(
            waveform="S",
            freq_hz=220.0,
            start_tick=0,
            duration_ticks=10,
            volume=5,
            source="stream_music",
        )
        events = runtime.end_frame().audio_events

        self.assertEqual(next_epoch, 1)
        self.assertEqual(len(events), 3)
        assert isinstance(events[0], AudioNoteEvent)
        assert isinstance(events[1], AudioResetEvent)
        assert isinstance(events[2], AudioNoteEvent)
        self.assertEqual(events[0].epoch_id, 0)
        self.assertEqual(events[0].start_tick, 12)
        self.assertEqual(events[0].waveform, "S")
        self.assertEqual(events[0].effect, "N")
        self.assertEqual(events[1].epoch_id, 0)
        self.assertEqual(events[1].cut_tick, 20)
        self.assertEqual(events[1].next_epoch_id, 1)
        self.assertEqual(events[2].epoch_id, 1)
        self.assertEqual(events[2].start_tick, 0)

    def test_emit_immediate_sfx_uses_audio_clock_snapshot(self) -> None:
        runtime = AlienEvolutionPort()
        runtime.begin_frame(
            FrameInput(
                audio_clock=AudioClockSnapshot(current_epoch_id=0, safe_start_tick=17, fill_until_tick=17),
            )
        )

        runtime.emit_immediate_sfx(
            waveform="S",
            freq_hz=440.0,
            duration_ticks=5,
            volume=5,
            start_tick=runtime.audio_clock.safe_start_tick,
            source="rom_beeper",
        )
        event = runtime.end_frame().audio_events[0]

        assert isinstance(event, AudioNoteEvent)
        self.assertEqual(event.start_tick, 17)
        self.assertEqual(event.waveform, "S")
        self.assertEqual(event.effect, "N")
        self.assertEqual(event.source, "rom_beeper")

    def test_stream_silence_advances_other_voice_cursor(self) -> None:
        runtime = AlienEvolutionPort()
        runtime.begin_frame(FrameInput())
        runtime._reset_stream_audio_timing_state()

        runtime._emit_stream_semantic_mix(iterations=256, fast_wraps=8, slow_wraps=0)
        runtime._emit_stream_semantic_mix(iterations=256, fast_wraps=0, slow_wraps=8)
        events = runtime.end_frame().audio_events

        self.assertEqual(len(events), 2)
        assert isinstance(events[0], AudioNoteEvent)
        assert isinstance(events[1], AudioNoteEvent)
        self.assertEqual(events[0].waveform, "S")
        self.assertEqual(events[1].waveform, "S")
        self.assertEqual(events[1].start_tick, events[0].duration_ticks)

    def test_emit_helpers_require_explicit_start_tick(self) -> None:
        runtime = AlienEvolutionPort()
        runtime.begin_frame(FrameInput())

        with self.assertRaises(TypeError):
            runtime.emit_audio(
                waveform="S",
                freq_hz=440.0,
                duration_s=0.1,
                volume=5,
            )
        with self.assertRaises(TypeError):
            runtime.emit_immediate_sfx(
                waveform="S",
                freq_hz=440.0,
                duration_ticks=5,
                volume=5,
            )
        with self.assertRaises(TypeError):
            runtime.emit_rom_beeper(
                period=100,
                ticks=10,
            )

    def test_fsm_start_stream_queues_mode_reset(self) -> None:
        runtime = AlienEvolutionPort()
        runtime.begin_frame(
            FrameInput(
                audio_clock=AudioClockSnapshot(current_epoch_id=0, safe_start_tick=8, fill_until_tick=24),
            )
        )
        runtime.emit_immediate_sfx(
            waveform="S",
            freq_hz=440.0,
            duration_ticks=5,
            volume=5,
            start_tick=runtime.audio_clock.safe_start_tick,
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

    def test_front_end_beeper_cadence_uses_explicit_offsets(self) -> None:
        runtime = AlienEvolutionPort()
        runtime.begin_frame(
            FrameInput(
                audio_clock=AudioClockSnapshot(current_epoch_id=0, safe_start_tick=10, fill_until_tick=10),
            )
        )

        runtime.fn_front_end_two_step_beeper_cadence()
        events = runtime.end_frame().audio_events

        self.assertEqual(len(events), 2)
        assert isinstance(events[0], AudioNoteEvent)
        assert isinstance(events[1], AudioNoteEvent)
        self.assertEqual(events[0].start_tick, 10)
        self.assertEqual(
            events[1].start_tick,
            10 + runtime._rom_beeper_duration_ticks(de_ticks=0x0032, hl_period=0x0032),
        )

    def test_stream_step_prefills_audio_until_fill_target(self) -> None:
        runtime = AlienEvolutionPort()
        output = runtime.step(
            FrameInput(
                audio_clock=AudioClockSnapshot(current_epoch_id=0, safe_start_tick=10, fill_until_tick=40),
            )
        )

        note_events = [event for event in output.audio_events if isinstance(event, AudioNoteEvent)]
        self.assertTrue(note_events)
        self.assertGreaterEqual(
            max(int(event.start_tick) + int(event.duration_ticks) for event in note_events),
            30,
        )

    def test_teleport_entry_queues_audio_for_each_host_frame(self) -> None:
        runtime = AlienEvolutionPort()
        runtime.begin_frame(
            FrameInput(
                audio_clock=AudioClockSnapshot(current_epoch_id=0, safe_start_tick=10, fill_until_tick=10),
            )
        )
        runtime.var_runtime_current_cell_ptr = BlockPtr(runtime.var_level_map_mode_0, 0x0000)
        runtime.var_level_map_mode_0[0] = 0x00
        runtime.fn_hud_strip_painter = lambda: None  # type: ignore[assignment]

        runtime.state_29_handler()
        events = runtime.end_frame().audio_events

        note_events = [event for event in events if isinstance(event, AudioNoteEvent)]
        self.assertEqual([event.start_tick for event in note_events], [10, 12, 15, 17, 20])
        self.assertTrue(all(event.waveform == "S" for event in note_events))
        self.assertTrue(all(event.effect == "N" for event in note_events))

    def test_backend_uses_effect_from_event_without_short_note_autofade(self) -> None:
        fake_pyxel = _FakePyxel()
        player = PyxelAudioPlayer()
        player._epoch_origin_time_s = 10.0
        player.submit(
            (
                AudioNoteEvent(
                    epoch_id=0,
                    start_tick=0,
                    duration_ticks=2,
                    waveform="S",
                    effect="N",
                    freq_hz=1017.0,
                    volume=5,
                    source="rom_beeper",
                    priority=30,
                ),
            ),
            now_s=10.0,
        )

        with patch.dict(sys.modules, {"pyxel": fake_pyxel}):
            player.update(now_s=10.0)

        set_calls = [call for sound in fake_pyxel.sounds for call in sound.calls if call.get("notes") != "R"]
        self.assertEqual(len(set_calls), 1)
        self.assertEqual(set_calls[0]["tones"], "S")
        self.assertEqual(set_calls[0]["effects"], "N")

    def test_clock_snapshot_follows_monotonic_time(self) -> None:
        player = PyxelAudioPlayer()
        player._epoch_origin_time_s = 10.0

        snap = player.clock_snapshot(now_s=10.5)

        self.assertEqual(snap.current_epoch_id, 0)
        self.assertEqual(snap.safe_start_tick, 63)
        self.assertEqual(snap.fill_until_tick, 156)

    def test_reset_switches_epoch_on_wall_clock_cut(self) -> None:
        fake_pyxel = _FakePyxel()
        player = PyxelAudioPlayer()
        player._epoch_origin_time_s = 10.0
        player.submit((AudioResetEvent(epoch_id=0, cut_tick=12, next_epoch_id=1),), now_s=10.0)

        with patch.dict(sys.modules, {"pyxel": fake_pyxel}):
            snap = player.clock_snapshot(now_s=10.1)

        self.assertEqual(snap.current_epoch_id, 1)
        self.assertEqual(snap.safe_start_tick, 3)
        self.assertEqual(snap.fill_until_tick, 96)
        self.assertEqual(fake_pyxel.stop_calls, [None])

    def test_reset_truncates_old_epoch_audio_but_keeps_next_epoch_audio(self) -> None:
        fake_pyxel = _FakePyxel()
        player = PyxelAudioPlayer()
        player._epoch_origin_time_s = 10.0
        player.submit(
            (
                AudioNoteEvent(
                    epoch_id=0,
                    start_tick=0,
                    duration_ticks=20,
                    waveform="S",
                    freq_hz=440.0,
                    volume=5,
                    source="stream_music",
                    priority=10,
                ),
                AudioResetEvent(epoch_id=0, cut_tick=5, next_epoch_id=1),
                AudioNoteEvent(
                    epoch_id=1,
                    start_tick=0,
                    duration_ticks=8,
                    waveform="S",
                    freq_hz=220.0,
                    volume=5,
                    source="rom_beeper",
                    priority=30,
                ),
            ),
            now_s=10.0,
        )

        with patch.dict(sys.modules, {"pyxel": fake_pyxel}):
            player.update(now_s=10.0)
            player.update(now_s=10.05)

        non_rest_calls = [call for sound in fake_pyxel.sounds for call in sound.calls if call.get("notes") != "R"]
        self.assertTrue(any(call.get("speed") == 5 for call in non_rest_calls))
        self.assertTrue(any(call.get("speed") == 7 for call in non_rest_calls))

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
                    waveform="S",
                    freq_hz=440.0,
                    volume=5,
                    source="stream_music",
                    priority=10,
                ),
                AudioNoteEvent(
                    epoch_id=0,
                    start_tick=8,
                    duration_ticks=5,
                    waveform="S",
                    freq_hz=440.0,
                    volume=5,
                    source="stream_music",
                    priority=10,
                ),
            ),
            now_s=10.0,
        )

        with patch.dict(sys.modules, {"pyxel": fake_pyxel}):
            player.update(now_s=10.0)

        set_calls = [call for sound in fake_pyxel.sounds for call in sound.calls]
        self.assertTrue(any(call.get("notes") == "R" for call in set_calls))

    def test_late_event_plays_remaining_tail_and_records_lost_head(self) -> None:
        fake_pyxel = _FakePyxel()
        player = PyxelAudioPlayer()
        player._epoch_origin_time_s = 10.0
        player.submit(
            (
                AudioNoteEvent(
                    epoch_id=0,
                    start_tick=0,
                    duration_ticks=20,
                    waveform="S",
                    freq_hz=440.0,
                    volume=5,
                    source="generic",
                    priority=25,
                ),
            ),
            now_s=10.1,
        )

        with patch.dict(sys.modules, {"pyxel": fake_pyxel}):
            player.update(now_s=10.1)

        stats = player.debug_stats()
        self.assertEqual(stats.late_head_ticks_lost, 12)
        self.assertEqual(stats.late_partially_played_events, 1)
        set_calls = [call for sound in fake_pyxel.sounds for call in sound.calls if call.get("notes") != "R"]
        self.assertTrue(any(call.get("speed") == 8 for call in set_calls))

    def test_fully_missed_event_increments_debug_counter_without_play(self) -> None:
        fake_pyxel = _FakePyxel()
        player = PyxelAudioPlayer()
        player._epoch_origin_time_s = 10.0
        player.submit(
            (
                AudioNoteEvent(
                    epoch_id=0,
                    start_tick=0,
                    duration_ticks=10,
                    waveform="S",
                    freq_hz=440.0,
                    volume=5,
                    source="generic",
                    priority=25,
                ),
            ),
            now_s=10.1,
        )

        with patch.dict(sys.modules, {"pyxel": fake_pyxel}):
            player.update(now_s=10.1)

        stats = player.debug_stats()
        self.assertEqual(stats.fully_missed_events, 1)
        self.assertEqual(stats.fully_missed_ticks, 10)
        self.assertEqual(fake_pyxel.play_calls, [])

    def test_short_event_can_play_before_future_higher_priority_sound(self) -> None:
        fake_pyxel = _FakePyxel()
        player = PyxelAudioPlayer()
        player._epoch_origin_time_s = 10.0
        player.submit(
            (
                AudioNoteEvent(
                    epoch_id=0,
                    start_tick=0,
                    duration_ticks=4,
                    waveform="S",
                    freq_hz=220.0,
                    volume=5,
                    source="generic",
                    priority=25,
                ),
                AudioNoteEvent(
                    epoch_id=0,
                    start_tick=8,
                    duration_ticks=10,
                    waveform="S",
                    freq_hz=330.0,
                    volume=5,
                    source="rom_beeper",
                    priority=30,
                ),
            ),
            now_s=10.0,
        )

        with patch.dict(sys.modules, {"pyxel": fake_pyxel}):
            player.update(now_s=10.0)

        set_calls = [call for sound in fake_pyxel.sounds for call in sound.calls if call.get("notes") != "R"]
        self.assertTrue(any(call.get("speed") == 4 for call in set_calls))

    def test_saturation_loss_counters_track_overflowed_fifth_voice(self) -> None:
        fake_pyxel = _FakePyxel()
        player = PyxelAudioPlayer()
        player._epoch_origin_time_s = 10.0
        player.submit(
            tuple(
                AudioNoteEvent(
                    epoch_id=0,
                    start_tick=0,
                    duration_ticks=10,
                    waveform="S",
                    freq_hz=220.0 + idx,
                    volume=5,
                    source="generic",
                    priority=25,
                )
                for idx in range(5)
            ),
            now_s=10.0,
        )

        with patch.dict(sys.modules, {"pyxel": fake_pyxel}):
            player.update(now_s=10.0)
            player.update(now_s=10.1)

        stats = player.debug_stats()
        self.assertEqual(stats.saturation_dropped_events, 1)
        self.assertEqual(stats.saturation_dropped_ticks, 10)

    def test_reset_debug_stats_clears_counters(self) -> None:
        player = PyxelAudioPlayer()
        player._epoch_origin_time_s = 10.0
        player.submit(
            (
                AudioNoteEvent(
                    epoch_id=0,
                    start_tick=0,
                    duration_ticks=10,
                    waveform="S",
                    freq_hz=440.0,
                    volume=5,
                    source="generic",
                    priority=25,
                ),
            ),
            now_s=10.1,
        )

        self.assertGreater(player.debug_stats().fully_missed_events, 0)
        player.reset_debug_stats()
        stats = player.debug_stats()
        self.assertEqual(stats.late_head_ticks_lost, 0)
        self.assertEqual(stats.late_partially_played_events, 0)
        self.assertEqual(stats.fully_missed_events, 0)
        self.assertEqual(stats.fully_missed_ticks, 0)
        self.assertEqual(stats.saturation_dropped_events, 0)
        self.assertEqual(stats.saturation_dropped_ticks, 0)


if __name__ == "__main__":
    unittest.main()
