from __future__ import annotations

import math
from dataclasses import dataclass
from collections import deque
from collections.abc import Sequence

from ..zx.runtime import AudioCommand

_AUDIO_TONES = ("S", "T", "P", "N")
_A2_REFERENCE_HZ = 429.89
# Pyxel Sound.speed is documented as 1..255.
_PYXEL_SOUND_SPEED_MAX = 255


@dataclass(slots=True)
class _QueuedAudioCommand:
    cmd: AudioCommand
    ticks: int
    is_rest: bool = False


def _note_from_hz(freq: float) -> str:
    if freq <= 0:
        return "R"

    # Pyxel note numbers are 0..59 => C0..B4, anchored to project-tuned A2.
    note_idx = int(round(33 + 12.0 * math.log2(freq / _A2_REFERENCE_HZ)))
    if note_idx < 0:
        note_idx = 0
    if note_idx > 59:
        note_idx = 59
    names = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
    name = names[note_idx % 12]
    octv = note_idx // 12
    return f"{name}{octv}"


def _noise_note_from_hz(freq: float) -> str:
    """Map wide-band/noise rates into a bright Pyxel noise color range."""
    if freq <= 0:
        return "C0"

    # Stream bit-noise in the original engine is mostly high-rate, cymbal-like
    # texture. Keep noise mapping in a bright register and use a logarithmic
    # compression to preserve pattern differences without collapsing everything
    # to one top bin.
    src_hz = max(120.0, float(freq))
    src_lo = 120.0
    src_hi = 20_000.0
    t = (math.log(src_hz) - math.log(src_lo)) / (math.log(src_hi) - math.log(src_lo))
    if t < 0.0:
        t = 0.0
    if t > 1.0:
        t = 1.0
    # Keep stream-special noise in the upper register: on real Spectrum this
    # path toggles the beeper latch at ~2.5..18 kHz (preset-A uses D=01/29/FF),
    # which is perceived as bright cymbal-like hash rather than low rumble.
    color_hz = 1400.0 + (600.0 * (t**0.6))
    return _note_from_hz(color_hz)


def _stream_special_noise_note_from_hz(freq: float) -> str:
    """Bright bins for FD0E stream-special beeper hash."""
    f = max(0.0, float(freq))
    return "A#4" if f < 5000.0 else "B4"


def _normalized_command(cmd: AudioCommand) -> AudioCommand | None:
    tone = (cmd.tone or "S").upper()
    if tone not in _AUDIO_TONES:
        tone = "S"

    duration = float(cmd.duration_s)
    if duration <= 0.0:
        return None
    if duration > 1.2:
        duration = 1.2

    freq = float(cmd.freq_hz)
    if freq < 20.0:
        freq = 20.0
    # For noise tone ("N"), keep a wider control-rate range so distinct
    # bitstream patterns don't collapse into one identical color.
    freq_max = 20_000.0 if tone == "N" else 5000.0
    if freq > freq_max:
        freq = freq_max

    volume = max(0, min(7, int(cmd.volume)))
    channel = max(0, min(3, int(cmd.channel)))
    source = str(cmd.source or "generic")
    start_delay_ticks = max(0, int(cmd.start_delay_ticks))

    return AudioCommand(
        tone=tone,
        freq_hz=freq,
        duration_s=duration,
        volume=volume,
        channel=channel,
        source=source,
        start_delay_ticks=start_delay_ticks,
    )


def _sound_set_from_command(
    slot: int,
    cmd: AudioCommand,
    *,
    speed_ticks: int | None = None,
    rest: bool = False,
) -> None:
    import pyxel

    ticks = max(1, int(speed_ticks) if speed_ticks is not None else int(round(cmd.duration_s * 120.0)))
    if ticks > _PYXEL_SOUND_SPEED_MAX:
        ticks = _PYXEL_SOUND_SPEED_MAX
    speed = ticks

    if rest:
        notes = "R"
        tones = "N"
        volumes = "0"
        effects = "N"
    else:
        is_stream_special_noise = cmd.tone == "N" and cmd.source == "stream_special"
        if cmd.tone == "N":
            note = (
                _stream_special_noise_note_from_hz(cmd.freq_hz)
                if is_stream_special_noise
                else _noise_note_from_hz(cmd.freq_hz)
            )
        else:
            note = _note_from_hz(cmd.freq_hz)
        notes = note
        tones = cmd.tone
        volumes = str(cmd.volume)
        # For very short one-tick blips, a tiny fade helps avoid hard clicks and also
        # subjectively matches the "pip" character of Spectrum beeper output.
        #
        # For noise, keep a fade too: raw Pyxel noise is fuller than Spectrum
        # beeper hash and otherwise masks pitched cues.
        if is_stream_special_noise:
            effects = "N"
        else:
            effects = "F" if (ticks <= 2 or cmd.tone == "N") else "N"

    pyxel.sounds[slot].set(
        notes=notes,
        tones=tones,
        volumes=volumes,
        effects=effects,
        speed=speed,
    )


def beep(
    freq_hz: float = 440.0,
    duration_s: float = 0.08,
    *,
    tone: str = "S",
    channel: int = 0,
    volume: int = 7,
) -> None:
    """Play one immediate beep using the new semantic audio command schema."""
    import pyxel

    cmd = _normalized_command(
        AudioCommand(
            tone=tone,
            freq_hz=freq_hz,
            duration_s=duration_s,
            volume=volume,
            channel=channel,
        )
    )
    if cmd is None:
        return

    slot = 0
    _sound_set_from_command(slot, cmd)
    pyxel.play(cmd.channel, slot)


class PyxelAudioPlayer:
    """Stateful frame-audio player backed by per-channel command queues."""

    def __init__(
        self,
        *,
        slots_per_channel: int = 16,
        channel_gain: float = 1.0,
    ) -> None:
        if slots_per_channel <= 0:
            raise ValueError("slots_per_channel must be > 0")

        self._slots_per_channel = int(slots_per_channel)
        self._channel_gain = max(0.0, float(channel_gain))
        self._configured = False
        self._queues: tuple[deque[_QueuedAudioCommand], ...] = (
            deque(),
            deque(),
            deque(),
            deque(),
        )
        self._slot_cursor = [0, 0, 0, 0]
        self._tick_remainder = [0.0, 0.0, 0.0, 0.0]

    @staticmethod
    def _split_ticks(ticks: int) -> list[int]:
        """Split a duration in 120Hz ticks into Pyxel-supported chunks."""
        remaining = max(0, int(ticks))
        if remaining <= 0:
            return []
        out: list[int] = []
        while remaining > 0:
            chunk = remaining if remaining <= _PYXEL_SOUND_SPEED_MAX else _PYXEL_SOUND_SPEED_MAX
            out.append(chunk)
            remaining -= chunk
        return out

    def _append_queued(
        self,
        queue: deque[_QueuedAudioCommand],
        *,
        cmd: AudioCommand,
        ticks: int,
        is_rest: bool,
        allow_merge: bool,
    ) -> None:
        """Append a queued command, splitting long segments and respecting merge rules."""
        parts = self._split_ticks(ticks)
        if not parts:
            return

        for part_ticks in parts:
            if (
                allow_merge
                and queue
                and (not queue[-1].is_rest)
                and (not is_rest)
                and self._commands_match_for_merge(queue[-1].cmd, cmd)
            ):
                merged = queue[-1]
                if merged.ticks + part_ticks <= _PYXEL_SOUND_SPEED_MAX:
                    merged.ticks += part_ticks
                    if merged.cmd.source == "stream_music" and cmd.source == "stream_music":
                        merged.cmd = AudioCommand(
                            tone=merged.cmd.tone,
                            freq_hz=merged.cmd.freq_hz,
                            duration_s=merged.cmd.duration_s + cmd.duration_s,
                            volume=max(merged.cmd.volume, cmd.volume),
                            channel=merged.cmd.channel,
                            source=merged.cmd.source,
                            start_delay_ticks=merged.cmd.start_delay_ticks,
                        )
                    continue

            queue.append(_QueuedAudioCommand(cmd=cmd, ticks=part_ticks, is_rest=is_rest))

    @staticmethod
    def _round_positive_with_remainder(raw_value: float) -> tuple[int, float]:
        rounded = int(math.floor(raw_value + 0.5))
        if rounded < 1:
            return 1, 0.0
        return rounded, raw_value - float(rounded)

    @staticmethod
    def _commands_match_for_merge(left: AudioCommand, right: AudioCommand) -> bool:
        if left.start_delay_ticks != 0 or right.start_delay_ticks != 0:
            return False
        if left.source == "stream_music" and right.source == "stream_music":
            return (
                left.tone == right.tone
                and left.channel == right.channel
                and _note_from_hz(left.freq_hz) == _note_from_hz(right.freq_hz)
            )
        return (
            left.tone == right.tone
            and left.volume == right.volume
            and left.channel == right.channel
            and left.source == right.source
            and abs(left.freq_hz - right.freq_hz) < 1e-6
        )

    def _quantize_duration_to_ticks(self, cmd: AudioCommand) -> int:
        channel = cmd.channel
        raw_ticks = (cmd.duration_s * 120.0) + self._tick_remainder[channel]
        ticks, tick_remainder = self._round_positive_with_remainder(raw_ticks)
        self._tick_remainder[channel] = tick_remainder
        return ticks

    def _ensure_configured(self) -> None:
        if self._configured:
            return
        import pyxel

        # Pyxel exposes a global pool of sound slots; keep our per-channel ring
        # inside that pool even if the host runtime uses a smaller configuration.
        max_slots_per_channel = max(1, len(pyxel.sounds) // 4)
        if self._slots_per_channel > max_slots_per_channel:
            self._slots_per_channel = max_slots_per_channel
            self._slot_cursor = [c % self._slots_per_channel for c in self._slot_cursor]

        for channel in range(4):
            pyxel.channels[channel].gain = self._channel_gain
        self._configured = True

    def submit(self, commands: Sequence[AudioCommand]) -> None:
        for raw in commands:
            cmd = _normalized_command(raw)
            if cmd is None:
                continue
            ticks = self._quantize_duration_to_ticks(cmd)
            delay_ticks = max(0, int(cmd.start_delay_ticks))
            queue = self._queues[cmd.channel]
            if delay_ticks > 0:
                rest_cmd = AudioCommand(
                    tone="N",
                    freq_hz=20.0,
                    duration_s=float(delay_ticks) / 120.0,
                    volume=0,
                    channel=cmd.channel,
                    source=cmd.source,
                )

                if queue and queue[-1].is_rest and (queue[-1].ticks < _PYXEL_SOUND_SPEED_MAX):
                    take = min(delay_ticks, _PYXEL_SOUND_SPEED_MAX - queue[-1].ticks)
                    queue[-1].ticks += take
                    delay_ticks -= take
                if delay_ticks > 0:
                    for part_ticks in self._split_ticks(delay_ticks):
                        queue.append(_QueuedAudioCommand(cmd=rest_cmd, ticks=part_ticks, is_rest=True))
                cmd = AudioCommand(
                    tone=cmd.tone,
                    freq_hz=cmd.freq_hz,
                    duration_s=cmd.duration_s,
                    volume=cmd.volume,
                    channel=cmd.channel,
                    source=cmd.source,
                    start_delay_ticks=0,
                )
            self._append_queued(queue, cmd=cmd, ticks=ticks, is_rest=False, allow_merge=True)

    def update(self) -> None:
        import pyxel
        self._ensure_configured()

        for channel in range(4):
            if not self._queues[channel]:
                continue
            if pyxel.play_pos(channel) is not None:
                continue

            slot_base = channel * self._slots_per_channel
            slots: list[int] = []

            while self._queues[channel]:
                if len(slots) >= self._slots_per_channel:
                    break

                queued = self._queues[channel].popleft()
                cmd = queued.cmd
                ticks = queued.ticks

                slot = slot_base + self._slot_cursor[channel]
                self._slot_cursor[channel] = (self._slot_cursor[channel] + 1) % self._slots_per_channel

                _sound_set_from_command(slot, cmd, speed_ticks=ticks, rest=queued.is_rest)
                slots.append(slot)

            if not slots:
                continue
            if len(slots) == 1:
                pyxel.play(channel, slots[0])
            else:
                pyxel.play(channel, slots)


def play_audio_commands(commands: Sequence[AudioCommand]) -> None:
    """Backward-friendly stateless wrapper around a global queue player."""
    global _GLOBAL_PLAYER
    if _GLOBAL_PLAYER is None:
        _GLOBAL_PLAYER = PyxelAudioPlayer()
    _GLOBAL_PLAYER.submit(commands)
    _GLOBAL_PLAYER.update()


_GLOBAL_PLAYER: PyxelAudioPlayer | None = None
