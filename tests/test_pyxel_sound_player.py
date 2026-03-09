from __future__ import annotations

import sys
import unittest
from unittest.mock import patch

from alien_evolution.alienevolution.logic import GAMEPLAY_FRAME_DIVIDER, AlienEvolutionPort, ForcedInterpreterAbort
from alien_evolution.pyxel.sound import PyxelAudioPlayer, _ChannelSegment, _sound_set_from_segment
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
    def test_sound_set_uses_note_from_segment_without_backend_conversion(self) -> None:
        fake_pyxel = _FakePyxel()
        segment = _ChannelSegment(
            is_rest=False,
            ticks=4,
            note="C#4",
            waveform="S",
            effect="N",
            volume=3,
            priority=25,
        )

        with patch.dict(sys.modules, {"pyxel": fake_pyxel}):
            _sound_set_from_segment(0, segment)

        call = fake_pyxel.sounds[0].calls[-1]
        self.assertEqual(call["notes"], "C#4")
        self.assertEqual(call["tones"], "S")
        self.assertEqual(call["effects"], "N")
        self.assertEqual(call["volumes"], "3")
        self.assertEqual(call["speed"], 4)

    def test_special_command_dispatcher_expands_t1_macrocell_into_ranked_voices(self) -> None:
        runtime = AlienEvolutionPort()
        runtime.begin_frame(FrameInput())
        runtime._reset_stream_audio_timing_state()
        runtime.var_stream_cmd_byte_1 = 0x29

        runtime.special_command_dispatcher(0xB4)
        events = runtime.end_frame().audio_events

        self.assertEqual(len(events), 8)
        self.assertEqual([event.start_tick for event in events], [0, 0, 4, 4, 8, 8, 12, 12])
        self.assertEqual([event.note for event in events], ["B4", "B3", "A4", "A3", "G4", "G3", "F4", "F3"])
        self.assertEqual([event.waveform for event in events], ["P"] * 8)
        self.assertEqual([event.priority for event in events], [20, 19, 20, 19, 20, 19, 20, 19])
        self.assertEqual(runtime._stream_lane_ticks[:2], [16, 16])

    def test_special_command_dispatcher_expands_t2_macrocell_with_trailing_silence(self) -> None:
        runtime = AlienEvolutionPort()
        runtime.begin_frame(FrameInput())
        runtime._reset_stream_audio_timing_state()
        runtime.var_stream_cmd_byte_1 = 0x01

        runtime.special_command_dispatcher(0xEC)
        events = runtime.end_frame().audio_events

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].start_tick, 0)
        self.assertEqual(events[0].duration_ticks, 4)
        self.assertEqual(events[0].note, "G4")
        self.assertEqual(events[0].waveform, "N")
        self.assertEqual(runtime._stream_lane_ticks[:2], [16, 16])

    def test_special_command_dispatcher_expands_t3late_macrocell_on_all_steps(self) -> None:
        runtime = AlienEvolutionPort()
        runtime.begin_frame(FrameInput())
        runtime._reset_stream_audio_timing_state()
        runtime.var_stream_cmd_byte_1 = 0xFF

        runtime.special_command_dispatcher(0xF3)
        events = runtime.end_frame().audio_events

        self.assertEqual(len(events), 8)
        self.assertEqual([event.start_tick for event in events], [0, 0, 4, 4, 8, 8, 12, 12])
        self.assertEqual([event.note for event in events], ["A#4", "B4", "A#4", "B4", "A#4", "B4", "A#4", "B4"])
        self.assertTrue(all(event.waveform == "N" for event in events))

    def test_special_command_dispatcher_expands_t3early_macrocell_every_other_step(self) -> None:
        runtime = AlienEvolutionPort()
        runtime.begin_frame(FrameInput())
        runtime._reset_stream_audio_timing_state()
        runtime.var_stream_cmd_byte_1 = 0xFF

        runtime.special_command_dispatcher(0xEE)
        events = runtime.end_frame().audio_events

        self.assertEqual(len(events), 4)
        self.assertEqual([event.start_tick for event in events], [0, 0, 8, 8])
        self.assertEqual([event.note for event in events], ["A#4", "B4", "A#4", "B4"])

    def test_schedule_reset_switches_default_emit_epoch(self) -> None:
        runtime = AlienEvolutionPort()
        runtime.begin_frame(
            FrameInput(
                audio_clock=AudioClockSnapshot(current_epoch_id=0, safe_start_tick=12, fill_until_tick=12),
            )
        )

        runtime.emit_immediate_sfx(
            note="A2",
            waveform="S",
            duration_ticks=5,
            volume=5,
            priority=30,
            start_tick=runtime.audio_clock.safe_start_tick,
        )
        next_epoch = runtime.schedule_reset(20)
        runtime.emit_note_event(
            note="A1",
            waveform="S",
            start_tick=0,
            duration_ticks=10,
            volume=5,
            priority=10,
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
            note="A2",
            waveform="S",
            duration_ticks=5,
            volume=5,
            priority=30,
            start_tick=runtime.audio_clock.safe_start_tick,
        )
        event = runtime.end_frame().audio_events[0]

        assert isinstance(event, AudioNoteEvent)
        self.assertEqual(event.start_tick, 17)
        self.assertEqual(event.note, "A2")
        self.assertEqual(event.waveform, "S")
        self.assertEqual(event.effect, "N")

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
                note="A2",
                waveform="S",
                duration_s=0.1,
                volume=5,
            )
        with self.assertRaises(TypeError):
            runtime.emit_immediate_sfx(
                note="A2",
                waveform="S",
                duration_ticks=5,
                volume=5,
            )

    def test_fsm_start_stream_queues_mode_reset(self) -> None:
        runtime = AlienEvolutionPort()
        runtime.begin_frame(
            FrameInput(
                audio_clock=AudioClockSnapshot(current_epoch_id=0, safe_start_tick=8, fill_until_tick=24),
            )
        )
        runtime.emit_immediate_sfx(
            note="A2",
            waveform="S",
            duration_ticks=5,
            volume=5,
            priority=30,
            start_tick=runtime.audio_clock.safe_start_tick,
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

    def test_pre_delay_calibration_helper_uses_exact_z80_loop_cost_for_default_wait(self) -> None:
        runtime = AlienEvolutionPort()
        runtime.begin_frame(FrameInput())
        runtime._reset_stream_audio_timing_state()

        timing_cost = runtime.pre_delay_calibration_helper()

        # FC82..FC86 entry = 21 t
        # FC87..FC9F setup/teardown = 59 t
        # Each outer pass = 255 * 93 + 88 + 14 = 23817 t
        # Default wait comes from (~0xEE) & 0xFF = 0x11.
        self.assertEqual(timing_cost, 404969)
        self.assertEqual(runtime._stream_lane_ticks[:2], [14, 14])

    def test_pre_delay_calibration_helper_uses_exact_z80_loop_cost_for_explicit_wait(self) -> None:
        runtime = AlienEvolutionPort()
        runtime.begin_frame(FrameInput())
        runtime._reset_stream_audio_timing_state()

        timing_cost = runtime.pre_delay_calibration_helper(C_wait=0x04)

        self.assertEqual(timing_cost, 95327)
        self.assertEqual(runtime._stream_lane_ticks[:2], [3, 3])

    def test_stream_preset_a_keeps_noise_and_tonal_tail_after_macrocell_rewrite(self) -> None:
        runtime = AlienEvolutionPort()
        runtime.begin_frame(
            FrameInput(
                audio_clock=AudioClockSnapshot(current_epoch_id=0, safe_start_tick=0, fill_until_tick=0),
            )
        )
        runtime._stream_ptr_a = BlockPtr(runtime.const_scenario_preset_a_stream_1, 0x0000)
        runtime._stream_ptr_b = runtime._stream_ptr_a.add(0x0001)
        runtime._stream_ptr_c = BlockPtr(runtime.const_scenario_preset_a_stream_2, 0x0000)
        runtime._stream_ptr_d = runtime._stream_ptr_c.add(0x0001)
        runtime._reset_stream_audio_timing_state()

        try:
            while True:
                runtime.core_command_interpreter_scenario_stream_engine()
        except ForcedInterpreterAbort:
            pass

        note_events = [event for event in runtime._audio_events if isinstance(event, AudioNoteEvent)]
        self.assertTrue(note_events)
        self.assertGreater(runtime.audio_epoch_tail(), 0)
        self.assertTrue(any(event.waveform == "N" for event in note_events))
        self.assertTrue(any(event.waveform in {"S", "P", "T"} for event in note_events))

    def test_stream_presets_b_and_c_preserve_full_duration(self) -> None:
        expected_tail_ticks = {
            "b": 5279,
            "c": 1408,
        }

        for preset_name, expected_tail in expected_tail_ticks.items():
            runtime = AlienEvolutionPort()
            runtime.begin_frame(
                FrameInput(
                    audio_clock=AudioClockSnapshot(current_epoch_id=0, safe_start_tick=0, fill_until_tick=0),
                )
            )
            runtime._stream_ptr_a = BlockPtr(getattr(runtime, f"const_scenario_preset_{preset_name}_stream_1"), 0x0000)
            runtime._stream_ptr_b = runtime._stream_ptr_a.add(0x0001)
            runtime._stream_ptr_c = BlockPtr(getattr(runtime, f"const_scenario_preset_{preset_name}_stream_2"), 0x0000)
            runtime._stream_ptr_d = runtime._stream_ptr_c.add(0x0001)
            runtime._reset_stream_audio_timing_state()

            with self.subTest(preset=preset_name):
                try:
                    while True:
                        runtime.core_command_interpreter_scenario_stream_engine()
                except ForcedInterpreterAbort:
                    pass
                self.assertEqual(runtime.audio_epoch_tail(), expected_tail)

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
        self.assertEqual(
            [event.start_tick for event in note_events],
            [10 + runtime._audio_ticks_for_host_frames(host_frame_idx) for host_frame_idx in range(GAMEPLAY_FRAME_DIVIDER)],
        )
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
                    note="B3",
                    waveform="S",
                    effect="N",
                    volume=5,
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
                    note="A2",
                    waveform="S",
                    volume=5,
                    priority=10,
                ),
                AudioResetEvent(epoch_id=0, cut_tick=5, next_epoch_id=1),
                AudioNoteEvent(
                    epoch_id=1,
                    start_tick=0,
                    duration_ticks=8,
                    note="A1",
                    waveform="S",
                    volume=5,
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
                    note="A2",
                    waveform="S",
                    volume=5,
                    priority=10,
                ),
                AudioNoteEvent(
                    epoch_id=0,
                    start_tick=8,
                    duration_ticks=5,
                    note="A2",
                    waveform="S",
                    volume=5,
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
                    note="A2",
                    waveform="S",
                    volume=5,
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
                    note="A2",
                    waveform="S",
                    volume=5,
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
                    note="A1",
                    waveform="S",
                    volume=5,
                    priority=25,
                ),
                AudioNoteEvent(
                    epoch_id=0,
                    start_tick=8,
                    duration_ticks=10,
                    note="E2",
                    waveform="S",
                    volume=5,
                    priority=30,
                ),
            ),
            now_s=10.0,
        )

        with patch.dict(sys.modules, {"pyxel": fake_pyxel}):
            player.update(now_s=10.0)

        set_calls = [call for sound in fake_pyxel.sounds for call in sound.calls if call.get("notes") != "R"]
        self.assertTrue(any(call.get("speed") == 4 for call in set_calls))

    def test_future_short_event_does_not_restart_each_frame_before_onset(self) -> None:
        fake_pyxel = _FakePyxel()
        player = PyxelAudioPlayer()
        player._epoch_origin_time_s = 10.0
        player.submit(
            (
                AudioNoteEvent(
                    epoch_id=0,
                    start_tick=3,
                    duration_ticks=2,
                    note="A2",
                    waveform="S",
                    volume=5,
                    priority=25,
                ),
            ),
            now_s=10.0,
        )

        with patch.dict(sys.modules, {"pyxel": fake_pyxel}):
            player.update(now_s=10.0)
            player.update(now_s=10.0167)
            player.update(now_s=10.0334)

        self.assertEqual(fake_pyxel.stop_calls, [])
        self.assertEqual(len(fake_pyxel.play_calls), 1)

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
                    note=("A1", "A#1", "B1", "C2", "C#2")[idx],
                    waveform="S",
                    volume=5,
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
                    note="A2",
                    waveform="S",
                    volume=5,
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
