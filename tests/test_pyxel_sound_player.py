from __future__ import annotations

import unittest

from alien_evolution.alienevolution.logic import AlienEvolutionPort, ForcedInterpreterAbort
from alien_evolution.pyxel.sound import PyxelAudioPlayer, _note_from_hz
from alien_evolution.zx.pointers import BlockPtr
from alien_evolution.zx.runtime import AudioCommand


def _queue_ticks(player: PyxelAudioPlayer, channel: int) -> list[int]:
    return [queued.ticks for queued in player._queues[channel]]


class PyxelSoundPlayerTests(unittest.TestCase):
    def test_note_from_hz_uses_pyxel_octave_base(self) -> None:
        self.assertEqual(_note_from_hz(429.89), "A2")
        self.assertEqual(_note_from_hz(440.0), "A2")
        self.assertEqual(_note_from_hz(340.187), "F2")
        self.assertEqual(_note_from_hz(1760.0), "A4")

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

    def test_stream_presets_b_and_c_have_delayed_stream_music_commands(self) -> None:
        runtime = AlienEvolutionPort()
        presets = (
            (runtime.const_scenario_preset_b_stream_1, runtime.const_scenario_preset_b_stream_2),
            (runtime.const_scenario_preset_c_stream_1, runtime.const_scenario_preset_c_stream_2),
        )

        for stream_a, stream_b in presets:
            runtime._audio_commands.clear()
            runtime._stream_ptr_a = BlockPtr(stream_a, 0x0000)
            runtime._stream_ptr_c = BlockPtr(stream_b, 0x0000)
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


if __name__ == "__main__":
    unittest.main()
