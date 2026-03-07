from __future__ import annotations

import sys
import unittest
from unittest.mock import patch

from alien_evolution.alienevolution.logic import AlienEvolutionPort, ForcedInterpreterAbort
from alien_evolution.pyxel.sound import (
    PyxelAudioPlayer,
    _noise_note_from_hz,
    _normalized_command,
    _note_from_hz,
    _sound_set_from_command,
    _stream_special_noise_note_from_hz,
)
from alien_evolution.zx.pointers import BlockPtr
from alien_evolution.zx.runtime import AudioCommand


def _queue_ticks(player: PyxelAudioPlayer, channel: int) -> list[int]:
    return [queued.ticks for queued in player._queues[channel]]


def _stream_command_timings(commands: tuple[AudioCommand, ...] | list[AudioCommand]) -> list[tuple[int, int, int]]:
    channel_time = [0, 0, 0, 0]
    timings: list[tuple[int, int, int]] = []
    for cmd in commands:
        start = channel_time[cmd.channel] + cmd.start_delay_ticks
        duration_ticks = int(round(cmd.duration_s * 120.0))
        end = start + duration_ticks
        timings.append((cmd.channel, start, end))
        channel_time[cmd.channel] = end
    return timings


class PyxelSoundPlayerTests(unittest.TestCase):
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
        self.assertEqual(_stream_special_noise_note_from_hz(2502.0), "A#4")
        self.assertEqual(_stream_special_noise_note_from_hz(7299.0), "B4")
        self.assertEqual(_stream_special_noise_note_from_hz(18199.0), "B4")

    def test_normalized_noise_command_keeps_wider_control_rate(self) -> None:
        noise_cmd = _normalized_command(
            AudioCommand(
                tone="N",
                freq_hz=18000.0,
                duration_s=0.1,
                volume=5,
                channel=0,
                source="generic",
            )
        )
        self.assertIsNotNone(noise_cmd)
        assert noise_cmd is not None
        self.assertEqual(noise_cmd.freq_hz, 18000.0)

        tonal_cmd = _normalized_command(
            AudioCommand(
                tone="S",
                freq_hz=18000.0,
                duration_s=0.1,
                volume=5,
                channel=0,
                source="generic",
            )
        )
        self.assertIsNotNone(tonal_cmd)
        assert tonal_cmd is not None
        self.assertEqual(tonal_cmd.freq_hz, 5000.0)

    def test_audio_command_normalizes_negative_start_delay_ticks(self) -> None:
        cmd = AudioCommand(
            tone="S",
            freq_hz=440.0,
            duration_s=0.1,
            volume=5,
            channel=0,
            source="stream_music",
            start_delay_ticks=-7,
        )
        self.assertEqual(cmd.start_delay_ticks, 0)

    def test_emit_audio_does_not_merge_when_new_command_has_start_delay(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._audio_commands.clear()

        runtime.emit_audio(
            tone="S",
            freq_hz=440.0,
            duration_s=0.1,
            volume=5,
            channel=0,
            source="stream_music",
        )
        runtime.emit_audio(
            tone="S",
            freq_hz=440.0,
            duration_s=0.1,
            volume=5,
            channel=0,
            source="stream_music",
            start_delay_ticks=3,
        )

        self.assertEqual(len(runtime._audio_commands), 2)
        self.assertEqual(runtime._audio_commands[1].start_delay_ticks, 3)

    def test_emit_audio_does_not_merge_stream_special_segments(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._audio_commands.clear()

        runtime.emit_audio(
            tone="N",
            freq_hz=7299.0,
            duration_s=0.026,
            volume=2,
            channel=0,
            source="stream_special",
        )
        runtime.emit_audio(
            tone="N",
            freq_hz=7299.0,
            duration_s=0.026,
            volume=2,
            channel=0,
            source="stream_special",
        )

        self.assertEqual(len(runtime._audio_commands), 2)
        self.assertAlmostEqual(runtime._audio_commands[0].duration_s, 0.026, places=6)
        self.assertAlmostEqual(runtime._audio_commands[1].duration_s, 0.026, places=6)

    def test_stream_music_uses_120hz_quantization(self) -> None:
        player = PyxelAudioPlayer()
        freqs = [220.0 * (2.0 ** (float(idx) / 12.0)) for idx in range(10)]
        commands = [
            AudioCommand(
                tone="S",
                freq_hz=freq,
                duration_s=0.126401,
                volume=5,
                channel=0,
                source="stream_music",
            )
            for freq in freqs
        ]

        player.submit(commands)
        ticks = _queue_ticks(player, 0)

        self.assertEqual(len(ticks), 10)
        self.assertEqual(sum(ticks), 152)
        self.assertTrue(all(tick in (15, 16) for tick in ticks))

    def test_generic_audio_path_unchanged_120hz(self) -> None:
        player = PyxelAudioPlayer()
        commands = [
            AudioCommand(
                tone="S",
                freq_hz=440.0 + float(idx),
                duration_s=0.126401,
                volume=5,
                channel=0,
                source="generic",
            )
            for idx in range(10)
        ]

        player.submit(commands)
        ticks = _queue_ticks(player, 0)

        self.assertEqual(len(ticks), 10)
        self.assertEqual(sum(ticks), 152)
        self.assertTrue(all(tick in (15, 16) for tick in ticks))

    def test_per_channel_tail_merge_independent_boundaries(self) -> None:
        player = PyxelAudioPlayer()
        player.submit(
            (
                AudioCommand(
                    tone="S",
                    freq_hz=440.0,
                    duration_s=0.126401,
                    volume=5,
                    channel=0,
                    source="stream_music",
                ),
                AudioCommand(
                    tone="S",
                    freq_hz=330.0,
                    duration_s=0.126401,
                    volume=5,
                    channel=1,
                    source="stream_music",
                ),
                AudioCommand(
                    tone="S",
                    freq_hz=440.0,
                    duration_s=0.126401,
                    volume=5,
                    channel=0,
                    source="stream_music",
                ),
                AudioCommand(
                    tone="S",
                    freq_hz=349.23,
                    duration_s=0.126401,
                    volume=5,
                    channel=1,
                    source="stream_music",
                ),
            )
        )

        self.assertEqual(len(player._queues[0]), 1)
        self.assertEqual(len(player._queues[1]), 2)

    def test_no_cross_source_merge(self) -> None:
        player = PyxelAudioPlayer()
        player.submit(
            (
                AudioCommand(
                    tone="S",
                    freq_hz=440.0,
                    duration_s=0.126401,
                    volume=5,
                    channel=0,
                    source="generic",
                ),
                AudioCommand(
                    tone="S",
                    freq_hz=440.0,
                    duration_s=0.126401,
                    volume=5,
                    channel=0,
                    source="stream_music",
                ),
            )
        )

        self.assertEqual(len(player._queues[0]), 2)

    def test_start_delay_inserts_rest_segment_before_note(self) -> None:
        player = PyxelAudioPlayer()
        player.submit(
            (
                AudioCommand(
                    tone="S",
                    freq_hz=440.0,
                    duration_s=0.1,
                    volume=5,
                    channel=0,
                    source="stream_music",
                    start_delay_ticks=5,
                ),
            )
        )

        self.assertEqual(len(player._queues[0]), 2)
        self.assertTrue(player._queues[0][0].is_rest)
        self.assertEqual(player._queues[0][0].ticks, 5)
        self.assertFalse(player._queues[0][1].is_rest)

    def test_stream_music_merge_does_not_cross_rest_segment(self) -> None:
        player = PyxelAudioPlayer()
        player.submit(
            (
                AudioCommand(
                    tone="S",
                    freq_hz=440.0,
                    duration_s=0.1,
                    volume=5,
                    channel=0,
                    source="stream_music",
                ),
                AudioCommand(
                    tone="S",
                    freq_hz=440.0,
                    duration_s=0.1,
                    volume=5,
                    channel=0,
                    source="stream_music",
                    start_delay_ticks=4,
                ),
            )
        )

        self.assertEqual(len(player._queues[0]), 3)
        self.assertFalse(player._queues[0][0].is_rest)
        self.assertTrue(player._queues[0][1].is_rest)
        self.assertFalse(player._queues[0][2].is_rest)

    def test_stream_music_merges_by_pyxel_note_ignoring_volume(self) -> None:
        player = PyxelAudioPlayer()
        player.submit(
            (
                AudioCommand(
                    tone="S",
                    freq_hz=440.0,
                    duration_s=0.126401,
                    volume=4,
                    channel=0,
                    source="stream_music",
                ),
                AudioCommand(
                    tone="S",
                    freq_hz=441.0,
                    duration_s=0.126401,
                    volume=6,
                    channel=0,
                    source="stream_music",
                ),
            )
        )

        self.assertEqual(len(player._queues[0]), 1)
        self.assertEqual(player._queues[0][0].cmd.volume, 6)
        self.assertEqual(player._queues[0][0].ticks, 30)

    def test_stream_music_merge_splits_when_ticks_exceed_pyxel_limit(self) -> None:
        player = PyxelAudioPlayer()
        player.submit(
            tuple(
                AudioCommand(
                    tone="S",
                    freq_hz=440.0,
                    duration_s=0.1,
                    volume=5,
                    channel=0,
                    source="stream_music",
                )
                for _ in range(30)
            )
        )

        ticks = _queue_ticks(player, 0)
        self.assertEqual(sum(ticks), 360)
        self.assertTrue(all(tick <= 255 for tick in ticks))
        self.assertGreater(len(ticks), 1)

    def test_start_delay_splits_rest_segments_at_pyxel_speed_limit(self) -> None:
        player = PyxelAudioPlayer()
        player.submit(
            (
                AudioCommand(
                    tone="S",
                    freq_hz=440.0,
                    duration_s=0.1,
                    volume=5,
                    channel=0,
                    source="stream_music",
                    start_delay_ticks=400,
                ),
            )
        )

        self.assertEqual(len(player._queues[0]), 3)
        self.assertTrue(player._queues[0][0].is_rest)
        self.assertTrue(player._queues[0][1].is_rest)
        self.assertFalse(player._queues[0][2].is_rest)

        rest_ticks = [player._queues[0][0].ticks, player._queues[0][1].ticks]
        self.assertEqual(sum(rest_ticks), 400)
        self.assertTrue(all(tick <= 255 for tick in rest_ticks))

    def test_sound_set_clamps_speed_above_pyxel_limit(self) -> None:
        class _FakeSound:
            def __init__(self) -> None:
                self.calls: list[dict[str, object]] = []

            def set(self, **kwargs) -> None:
                self.calls.append(kwargs)

        class _FakePyxel:
            def __init__(self) -> None:
                self.sounds = [_FakeSound()]

        fake_pyxel = _FakePyxel()
        cmd = AudioCommand(
            tone="S",
            freq_hz=440.0,
            duration_s=0.1,
            volume=5,
            channel=0,
            source="stream_music",
        )

        with patch.dict(sys.modules, {"pyxel": fake_pyxel}):
            _sound_set_from_command(0, cmd, speed_ticks=999)

        self.assertEqual(fake_pyxel.sounds[0].calls[-1]["speed"], 255)

    def test_sound_set_uses_noise_color_note_mapping(self) -> None:
        class _FakeSound:
            def __init__(self) -> None:
                self.calls: list[dict[str, object]] = []

            def set(self, **kwargs) -> None:
                self.calls.append(kwargs)

        class _FakePyxel:
            def __init__(self) -> None:
                self.sounds = [_FakeSound()]

        fake_pyxel = _FakePyxel()
        cmd = AudioCommand(
            tone="N",
            freq_hz=2200.0,
            duration_s=0.1,
            volume=5,
            channel=0,
            source="generic",
        )

        with patch.dict(sys.modules, {"pyxel": fake_pyxel}):
            _sound_set_from_command(0, cmd)

        self.assertEqual(fake_pyxel.sounds[0].calls[-1]["notes"], _noise_note_from_hz(2200.0))
        self.assertEqual(fake_pyxel.sounds[0].calls[-1]["effects"], "F")

    def test_sound_set_uses_bright_profile_for_stream_special_noise(self) -> None:
        class _FakeSound:
            def __init__(self) -> None:
                self.calls: list[dict[str, object]] = []

            def set(self, **kwargs) -> None:
                self.calls.append(kwargs)

        class _FakePyxel:
            def __init__(self) -> None:
                self.sounds = [_FakeSound()]

        fake_pyxel = _FakePyxel()
        cmd = AudioCommand(
            tone="N",
            freq_hz=2502.0,
            duration_s=0.1,
            volume=2,
            channel=0,
            source="stream_special",
        )

        with patch.dict(sys.modules, {"pyxel": fake_pyxel}):
            _sound_set_from_command(0, cmd)

        self.assertEqual(fake_pyxel.sounds[0].calls[-1]["notes"], "A#4")
        self.assertEqual(fake_pyxel.sounds[0].calls[-1]["effects"], "N")

    def test_runtime_marks_stream_semantic_mix_as_stream_music(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._audio_commands.clear()

        timing_cost = runtime._emit_stream_semantic_mix(
            iterations=512,
            fast_wraps=5,
            slow_wraps=3,
        )

        self.assertGreater(timing_cost, 0)
        self.assertGreaterEqual(len(runtime._audio_commands), 1)
        self.assertTrue(all(cmd.source == "stream_music" for cmd in runtime._audio_commands))

    def test_stream_semantic_mix_keeps_carrier_channel_timing_present(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._audio_commands.clear()
        runtime._stream_pending_delay_ticks = [0, 0, 0]

        runtime._emit_stream_semantic_mix(
            iterations=4608,
            fast_wraps=86,
            slow_wraps=4608,
        )

        self.assertEqual(len(runtime._audio_commands), 2)
        channel_cmds = {cmd.channel: cmd for cmd in runtime._audio_commands}
        self.assertEqual(channel_cmds[0].tone, "S")
        self.assertEqual(channel_cmds[1].tone, "T")
        self.assertEqual(channel_cmds[0].start_delay_ticks, 0)
        self.assertEqual(channel_cmds[1].start_delay_ticks, 0)
        self.assertEqual(channel_cmds[1].volume, 0)

    def test_bitstream_noise_frequency_tracks_pattern_density(self) -> None:
        runtime = AlienEvolutionPort()
        captured: list[float] = []
        orig_emit_audio = runtime.emit_audio

        def _capture_emit_audio(**kwargs) -> None:
            captured.append(float(kwargs["freq_hz"]))
            orig_emit_audio(**kwargs)

        runtime.emit_audio = _capture_emit_audio  # type: ignore[assignment]

        runtime.bitstream_pulse_generator(C_repeat=0x20, D_bits=0x01)
        runtime.bitstream_pulse_generator(C_repeat=0x20, D_bits=0x29)
        runtime.bitstream_pulse_generator(C_repeat=0x20, D_bits=0xFF)

        self.assertEqual(len(captured), 3)
        self.assertLess(captured[0], captured[1])
        self.assertLess(captured[1], captured[2])
        self.assertGreater(captured[2], 2200.0)

    def test_bitstream_noise_consumes_pending_special_delay_ticks(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._stream_pending_delay_ticks = [5, 0, 0]
        runtime._audio_commands.clear()

        runtime.bitstream_pulse_generator(C_repeat=0x20, D_bits=0x29)

        self.assertEqual(len(runtime._audio_commands), 1)
        self.assertEqual(runtime._audio_commands[0].start_delay_ticks, 5)
        self.assertEqual(runtime._audio_commands[0].source, "stream_special")
        self.assertLessEqual(runtime._audio_commands[0].volume, 3)
        self.assertEqual(runtime._stream_pending_delay_ticks[0], 0)
        self.assertGreater(runtime._stream_pending_delay_ticks[1], 0)

    def test_pre_delay_calibration_advances_both_stream_channels(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._stream_pending_delay_ticks = [0, 0, 0]

        timing = runtime.pre_delay_calibration_helper(C_wait=0x20)

        self.assertGreater(timing, 0)
        self.assertGreater(runtime._stream_pending_delay_ticks[0], 0)
        self.assertEqual(runtime._stream_pending_delay_ticks[0], runtime._stream_pending_delay_ticks[1])

    def test_special_dispatcher_noise_marks_stream_special_source(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._audio_commands.clear()
        runtime.var_stream_cmd_byte_1 = 0x29

        runtime.special_command_dispatcher(A_cmd=0xFF)

        emitted_noise = [cmd for cmd in runtime._audio_commands if cmd.tone == "N"]
        self.assertEqual(len(emitted_noise), 1)
        self.assertEqual(emitted_noise[0].source, "stream_special")

    def test_stream_semantic_mix_with_no_toggles_advances_channel_timeline(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._audio_commands.clear()
        runtime._stream_pending_delay_ticks = [0, 0, 0]

        timing = runtime._emit_stream_semantic_mix(iterations=256, fast_wraps=0, slow_wraps=0)

        self.assertGreater(timing, 0)
        self.assertEqual(len(runtime._audio_commands), 0)
        self.assertGreater(runtime._stream_pending_delay_ticks[0], 0)
        self.assertEqual(runtime._stream_pending_delay_ticks[0], runtime._stream_pending_delay_ticks[1])

    def test_stream_semantic_mix_emits_nonzero_start_delay_after_silence(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._audio_commands.clear()
        runtime._stream_ptr_a = BlockPtr(runtime.const_scenario_preset_b_stream_1, 0x0000)
        runtime._stream_ptr_c = BlockPtr(runtime.const_scenario_preset_b_stream_2, 0x0000)
        runtime._stream_ptr_b = runtime._stream_ptr_a.add(0x0001)
        runtime._stream_ptr_d = runtime._stream_ptr_c.add(0x0001)

        found_delayed = False
        for _ in range(512):
            before = len(runtime._audio_commands)
            try:
                runtime.core_command_interpreter_scenario_stream_engine()
            except ForcedInterpreterAbort:
                break
            emitted = runtime._audio_commands[before:]
            if any(cmd.source == "stream_music" and cmd.start_delay_ticks > 0 for cmd in emitted):
                found_delayed = True
                break

        self.assertTrue(found_delayed)

    def test_stream_preset_b_retains_delayed_stream_music_commands(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._audio_commands.clear()
        runtime._stream_ptr_a = BlockPtr(runtime.const_scenario_preset_b_stream_1, 0x0000)
        runtime._stream_ptr_c = BlockPtr(runtime.const_scenario_preset_b_stream_2, 0x0000)
        runtime._stream_ptr_b = runtime._stream_ptr_a.add(0x0001)
        runtime._stream_ptr_d = runtime._stream_ptr_c.add(0x0001)
        delayed_count = 0
        total_stream_commands = 0

        for _ in range(2048):
            before = len(runtime._audio_commands)
            try:
                runtime.core_command_interpreter_scenario_stream_engine()
            except ForcedInterpreterAbort:
                break
            emitted = runtime._audio_commands[before:]
            stream_emitted = [cmd for cmd in emitted if cmd.source == "stream_music"]
            total_stream_commands += len(stream_emitted)
            delayed_count += sum(1 for cmd in stream_emitted if cmd.start_delay_ticks > 0)

        self.assertGreater(total_stream_commands, 0)
        self.assertGreater(delayed_count, 0)

    def test_stream_presets_b_and_c_start_both_channels_together(self) -> None:
        runtime = AlienEvolutionPort()
        presets = (
            (runtime.const_scenario_preset_b_stream_1, runtime.const_scenario_preset_b_stream_2),
            (runtime.const_scenario_preset_c_stream_1, runtime.const_scenario_preset_c_stream_2),
        )

        for stream_a, stream_b in presets:
            runtime._audio_commands.clear()
            runtime._reset_stream_audio_timing_state()
            runtime._stream_ptr_a = BlockPtr(stream_a, 0x0000)
            runtime._stream_ptr_c = BlockPtr(stream_b, 0x0000)
            runtime._stream_ptr_b = runtime._stream_ptr_a.add(0x0001)
            runtime._stream_ptr_d = runtime._stream_ptr_c.add(0x0001)

            for _ in range(8):
                try:
                    runtime.core_command_interpreter_scenario_stream_engine()
                except ForcedInterpreterAbort:
                    break

            stream_cmds = [cmd for cmd in runtime._audio_commands if cmd.source == "stream_music"]
            timings = _stream_command_timings(stream_cmds)
            first_start_by_channel: dict[int, int] = {}
            for channel, start, _ in timings:
                if channel not in first_start_by_channel:
                    first_start_by_channel[channel] = start
                if len(first_start_by_channel) == 2:
                    break

            self.assertEqual(first_start_by_channel[0], 0)
            self.assertEqual(first_start_by_channel[1], 0)

            paired_starts = {(channel, start) for channel, start, _ in timings[:6]}
            shared_starts = {start for start in {s for _, s, _ in timings[:6]} if (0, start) in paired_starts and (1, start) in paired_starts}
            self.assertTrue(shared_starts)


if __name__ == "__main__":
    unittest.main()
