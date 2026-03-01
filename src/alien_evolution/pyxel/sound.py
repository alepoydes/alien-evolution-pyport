from __future__ import annotations

import math
from collections import deque
from collections.abc import Iterable, Sequence

from ..zx.runtime import AudioCommand

_AUDIO_TONES = ("S", "T", "P", "N")


def _note_from_hz(freq: float) -> str:
    if freq <= 0:
        return "R"

    midi = int(round(69 + 12.0 * math.log2(freq / 440.0)))
    names = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
    name = names[midi % 12]

    octv = (midi // 12) - 3
    if octv < 0:
        octv = 0
    if octv > 4:
        octv = 4
    return f"{name}{octv}"


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
    if freq > 5000.0:
        freq = 5000.0

    volume = max(0, min(7, int(cmd.volume)))
    channel = max(0, min(3, int(cmd.channel)))

    return AudioCommand(
        tone=tone,
        freq_hz=freq,
        duration_s=duration,
        volume=volume,
        channel=channel,
    )


def _normalize_and_merge(commands: Iterable[AudioCommand]) -> list[AudioCommand]:
    merged: list[AudioCommand] = []
    for raw in commands:
        cmd = _normalized_command(raw)
        if cmd is None:
            continue
        if merged:
            last = merged[-1]
            if (
                last.tone == cmd.tone
                and last.volume == cmd.volume
                and last.channel == cmd.channel
                and abs(last.freq_hz - cmd.freq_hz) < 1e-6
            ):
                merged[-1] = AudioCommand(
                    tone=last.tone,
                    freq_hz=last.freq_hz,
                    duration_s=last.duration_s + cmd.duration_s,
                    volume=last.volume,
                    channel=last.channel,
                )
                continue
        merged.append(cmd)
    return merged


def _sound_set_from_command(slot: int, cmd: AudioCommand) -> None:
    import pyxel

    note = _note_from_hz(cmd.freq_hz)
    ticks = max(1, int(round(cmd.duration_s * 120.0)))
    speed = ticks

    notes = note
    tones = cmd.tone
    volumes = str(cmd.volume)
    effects = "N"

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
        slots_per_channel: int = 8,
        channel_gain: float = 1.0,
    ) -> None:
        if slots_per_channel <= 0:
            raise ValueError("slots_per_channel must be > 0")

        self._slots_per_channel = int(slots_per_channel)
        self._channel_gain = max(0.0, float(channel_gain))
        self._configured = False
        self._queues: tuple[deque[AudioCommand], ...] = (
            deque(),
            deque(),
            deque(),
            deque(),
        )
        self._slot_cursor = [0, 0, 0, 0]

    def _ensure_configured(self) -> None:
        if self._configured:
            return
        import pyxel

        for channel in range(4):
            pyxel.channels[channel].gain = self._channel_gain
        self._configured = True

    def submit(self, commands: Sequence[AudioCommand]) -> None:
        normalized = _normalize_and_merge(commands)
        for cmd in normalized:
            self._queues[cmd.channel].append(cmd)

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

                cmd = self._queues[channel].popleft()
                slot = slot_base + self._slot_cursor[channel]
                self._slot_cursor[channel] = (self._slot_cursor[channel] + 1) % self._slots_per_channel

                _sound_set_from_command(slot, cmd)
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
