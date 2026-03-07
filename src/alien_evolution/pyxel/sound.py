from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import Final

from ..zx.runtime import AudioClockSnapshot, AudioEvent, AudioNoteEvent, AudioResetEvent

_AUDIO_TONES = ("S", "T", "P", "N")
_A2_REFERENCE_HZ = 429.89
_PYXEL_SOUND_SPEED_MAX = 255
_SCHEDULE_HORIZON_TICKS: Final[int] = 96


@dataclass(frozen=True, slots=True)
class _ChannelSegment:
    is_rest: bool
    ticks: int
    lane: int | None
    tone: str
    freq_hz: float
    volume: int
    source: str
    priority: int


@dataclass(slots=True)
class _ChannelPlan:
    epoch_id: int = 0
    anchor_tick: int = 0
    segments: tuple[_ChannelSegment, ...] = ()


def _note_from_hz(freq: float) -> str:
    if freq <= 0:
        return "R"

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
    if freq <= 0:
        return "C0"

    src_hz = max(120.0, float(freq))
    src_lo = 120.0
    src_hi = 20_000.0
    t = (math.log(src_hz) - math.log(src_lo)) / (math.log(src_hi) - math.log(src_lo))
    if t < 0.0:
        t = 0.0
    if t > 1.0:
        t = 1.0
    color_hz = 1400.0 + (600.0 * (t**0.6))
    return _note_from_hz(color_hz)


def _stream_special_noise_note_from_hz(freq: float) -> str:
    if freq <= 0:
        return "F4"

    src_lo = 2500.0
    src_hi = 18_000.0
    src_hz = max(src_lo, min(src_hi, float(freq)))
    t = (math.log(src_hz) - math.log(src_lo)) / (math.log(src_hi) - math.log(src_lo))
    if t < 0.0:
        t = 0.0
    if t > 1.0:
        t = 1.0

    bins = ("F4", "F#4", "G4", "G#4", "A4", "A#4", "B4")
    idx = int(round((len(bins) - 1) * (t**0.7)))
    return bins[idx]


def _normalized_note_event(event: AudioNoteEvent) -> AudioNoteEvent:
    tone = (event.tone or "S").upper()
    if tone not in _AUDIO_TONES:
        tone = "S"

    freq = float(event.freq_hz)
    if freq < 20.0:
        freq = 20.0
    freq_max = 20_000.0 if tone == "N" else 5000.0
    if freq > freq_max:
        freq = freq_max

    return AudioNoteEvent(
        epoch_id=event.epoch_id,
        start_tick=event.start_tick,
        duration_ticks=event.duration_ticks,
        lane=event.lane,
        tone=tone,
        freq_hz=freq,
        volume=max(0, min(7, int(event.volume))),
        source=str(event.source or "generic"),
        priority=int(event.priority),
    )


def _sound_set_from_segment(slot: int, segment: _ChannelSegment) -> None:
    import pyxel

    ticks = max(1, min(_PYXEL_SOUND_SPEED_MAX, int(segment.ticks)))
    if segment.is_rest:
        notes = "R"
        tones = "N"
        volumes = "0"
        effects = "N"
    else:
        is_stream_special_noise = segment.tone == "N" and segment.source == "stream_special"
        if segment.tone == "N":
            note = (
                _stream_special_noise_note_from_hz(segment.freq_hz)
                if is_stream_special_noise
                else _noise_note_from_hz(segment.freq_hz)
            )
        else:
            note = _note_from_hz(segment.freq_hz)
        notes = note
        tones = segment.tone
        volumes = str(segment.volume)
        effects = "N" if is_stream_special_noise else ("F" if (ticks <= 2 or segment.tone == "N") else "N")

    pyxel.sounds[slot].set(
        notes=notes,
        tones=tones,
        volumes=volumes,
        effects=effects,
        speed=ticks,
    )


def beep(
    freq_hz: float = 440.0,
    duration_s: float = 0.08,
    *,
    tone: str = "S",
    channel: int = 0,
    volume: int = 7,
) -> None:
    import pyxel

    ticks = max(1, int(round(float(duration_s) * 120.0)))
    segment = _ChannelSegment(
        is_rest=False,
        ticks=ticks,
        lane=channel,
        tone=(tone or "S").upper(),
        freq_hz=float(freq_hz),
        volume=volume,
        source="generic",
        priority=25,
    )
    _sound_set_from_segment(0, segment)
    pyxel.play(channel, 0)


class PyxelAudioPlayer:
    """Monotonic wall-clock audio scheduler backed by Pyxel channels."""

    def __init__(
        self,
        *,
        slots_per_channel: int = 16,
        channel_gain: float = 1.0,
        horizon_ticks: int = _SCHEDULE_HORIZON_TICKS,
    ) -> None:
        if slots_per_channel <= 0:
            raise ValueError("slots_per_channel must be > 0")
        if horizon_ticks <= 0:
            raise ValueError("horizon_ticks must be > 0")

        self._slots_per_channel = int(slots_per_channel)
        self._channel_gain = max(0.0, float(channel_gain))
        self._horizon_ticks = max(1, int(horizon_ticks))
        self._configured = False
        self._slot_cursor = [0, 0, 0, 0]
        self._epoch_note_events: dict[int, list[AudioNoteEvent]] = {0: []}
        self._epoch_reset_events: dict[int, AudioResetEvent] = {}
        self._active_epoch_id = 0
        self._epoch_origin_time_s = time.perf_counter()
        self._channel_plans = [_ChannelPlan(epoch_id=0) for _ in range(4)]

    @staticmethod
    def _split_ticks(ticks: int) -> list[int]:
        remaining = max(0, int(ticks))
        if remaining <= 0:
            return []
        out: list[int] = []
        while remaining > 0:
            chunk = remaining if remaining <= _PYXEL_SOUND_SPEED_MAX else _PYXEL_SOUND_SPEED_MAX
            out.append(chunk)
            remaining -= chunk
        return out

    def _ensure_configured(self) -> None:
        if self._configured:
            return
        import pyxel

        max_slots_per_channel = max(1, len(pyxel.sounds) // 4)
        if self._slots_per_channel > max_slots_per_channel:
            self._slots_per_channel = max_slots_per_channel
            self._slot_cursor = [c % self._slots_per_channel for c in self._slot_cursor]

        for channel in range(4):
            pyxel.channels[channel].gain = self._channel_gain
        self._configured = True

    def _note_end_tick(self, note: AudioNoteEvent) -> int:
        return int(note.start_tick) + int(note.duration_ticks)

    def _epoch_playhead_tick(self, now_s: float) -> int:
        elapsed_s = max(0.0, float(now_s) - float(self._epoch_origin_time_s))
        return max(0, int(math.floor((elapsed_s * 120.0) + 1e-9)))

    def _advance_epoch_if_needed(self, now_s: float) -> None:
        import pyxel

        while True:
            reset = self._epoch_reset_events.get(self._active_epoch_id)
            if reset is None:
                return
            cut_tick = max(0, int(reset.cut_tick))
            cut_time_s = self._epoch_origin_time_s + (float(cut_tick) / 120.0)
            if now_s + 1e-9 < cut_time_s:
                return
            pyxel.stop()
            self._active_epoch_id = int(reset.next_epoch_id)
            self._epoch_origin_time_s = cut_time_s
            self._channel_plans = [_ChannelPlan(epoch_id=self._active_epoch_id) for _ in range(4)]
            self._epoch_note_events.setdefault(self._active_epoch_id, [])

    def clock_snapshot(self, now_s: float | None = None) -> AudioClockSnapshot:
        now = time.perf_counter() if now_s is None else float(now_s)
        self._advance_epoch_if_needed(now)
        return AudioClockSnapshot(
            current_epoch_id=self._active_epoch_id,
            current_tick=self._epoch_playhead_tick(now),
        )

    def submit(self, events: tuple[AudioEvent, ...] | list[AudioEvent]) -> None:
        for raw in events:
            if isinstance(raw, AudioNoteEvent):
                event = _normalized_note_event(raw)
                notes = self._epoch_note_events.setdefault(event.epoch_id, [])
                notes.append(event)
                notes.sort(key=lambda item: (item.start_tick, -item.priority, item.lane, item.source))
                continue
            if isinstance(raw, AudioResetEvent):
                current = self._epoch_reset_events.get(raw.epoch_id)
                if current is None or int(raw.cut_tick) < int(current.cut_tick):
                    self._epoch_reset_events[raw.epoch_id] = raw
                self._epoch_note_events.setdefault(int(raw.next_epoch_id), [])

    def _build_tick_assignments(
        self,
        *,
        playhead_tick: int,
        horizon_end_tick: int,
    ) -> list[list[AudioNoteEvent | None]]:
        active_notes = [
            note
            for note in self._epoch_note_events.get(self._active_epoch_id, [])
            if note.start_tick < horizon_end_tick and self._note_end_tick(note) > playhead_tick
        ]
        reset = self._epoch_reset_events.get(self._active_epoch_id)
        if reset is not None:
            active_notes = [note for note in active_notes if note.start_tick < int(reset.cut_tick)]

        assignments = [[None] * 4 for _ in range(max(0, horizon_end_tick - playhead_tick))]
        prev: list[AudioNoteEvent | None] = [None, None, None, None]

        for offset, tick in enumerate(range(playhead_tick, horizon_end_tick)):
            selected = [
                note
                for note in active_notes
                if note.start_tick <= tick < self._note_end_tick(note)
            ]
            selected.sort(key=lambda note: (-note.priority, note.start_tick, note.lane, note.source))
            selected = selected[:4]

            row: list[AudioNoteEvent | None] = [None, None, None, None]
            remaining = list(selected)

            for channel in range(4):
                prev_note = prev[channel]
                if prev_note is not None and prev_note in remaining:
                    row[channel] = prev_note
                    remaining.remove(prev_note)

            for note in tuple(remaining):
                for channel in range(4):
                    if row[channel] is not None:
                        continue
                    prev_note = prev[channel]
                    if prev_note is not None and prev_note.lane == note.lane:
                        row[channel] = note
                        remaining.remove(note)
                        break

            for note in remaining:
                for channel in range(4):
                    if row[channel] is None:
                        row[channel] = note
                        break

            assignments[offset] = row
            prev = list(row)

        return assignments

    def _remaining_tick_limit(self, note: AudioNoteEvent) -> int:
        limit = self._note_end_tick(note)
        reset = self._epoch_reset_events.get(note.epoch_id)
        if reset is not None:
            limit = min(limit, int(reset.cut_tick))
        return limit

    def _compress_channel_segments(
        self,
        *,
        channel: int,
        playhead_tick: int,
        assignments: list[list[AudioNoteEvent | None]],
        horizon_end_tick: int,
    ) -> tuple[_ChannelSegment, ...]:
        if not assignments:
            return ()

        segments: list[_ChannelSegment] = []
        idx = 0
        total_ticks = len(assignments)
        while idx < total_ticks:
            note = assignments[idx][channel]
            run_end = idx + 1
            while run_end < total_ticks and assignments[run_end][channel] == note:
                run_end += 1
            run_ticks = run_end - idx

            if note is None:
                segments.append(
                    _ChannelSegment(
                        is_rest=True,
                        ticks=run_ticks,
                        lane=None,
                        tone="N",
                        freq_hz=20.0,
                        volume=0,
                        source="rest",
                        priority=-1,
                    )
                )
            else:
                segment_start_tick = playhead_tick + idx
                limit = self._remaining_tick_limit(note)
                if run_end == total_ticks and limit > horizon_end_tick:
                    run_ticks = max(1, limit - segment_start_tick)
                segments.append(
                    _ChannelSegment(
                        is_rest=False,
                        ticks=run_ticks,
                        lane=note.lane,
                        tone=note.tone,
                        freq_hz=note.freq_hz,
                        volume=note.volume,
                        source=note.source,
                        priority=note.priority,
                    )
                )
            idx = run_end

        return tuple(segment for segment in segments if segment.ticks > 0)

    def _trim_plan(
        self,
        *,
        plan: _ChannelPlan,
        playhead_tick: int,
    ) -> tuple[_ChannelSegment, ...]:
        if plan.epoch_id != self._active_epoch_id:
            return ()
        elapsed = max(0, int(playhead_tick) - int(plan.anchor_tick))
        if elapsed <= 0:
            return plan.segments

        remaining: list[_ChannelSegment] = []
        for segment in plan.segments:
            ticks = int(segment.ticks)
            if elapsed >= ticks:
                elapsed -= ticks
                continue
            if elapsed > 0:
                remaining.append(
                    _ChannelSegment(
                        is_rest=segment.is_rest,
                        ticks=ticks - elapsed,
                        lane=segment.lane,
                        tone=segment.tone,
                        freq_hz=segment.freq_hz,
                        volume=segment.volume,
                        source=segment.source,
                        priority=segment.priority,
                    )
                )
                elapsed = 0
                continue
            remaining.append(segment)
        return tuple(remaining)

    def _play_channel_segments(self, channel: int, segments: tuple[_ChannelSegment, ...]) -> None:
        import pyxel

        slot_base = channel * self._slots_per_channel
        slots: list[int] = []
        for segment in segments:
            for part_ticks in self._split_ticks(segment.ticks):
                if len(slots) >= self._slots_per_channel:
                    break
                slot = slot_base + self._slot_cursor[channel]
                self._slot_cursor[channel] = (self._slot_cursor[channel] + 1) % self._slots_per_channel
                _sound_set_from_segment(
                    slot,
                    _ChannelSegment(
                        is_rest=segment.is_rest,
                        ticks=part_ticks,
                        lane=segment.lane,
                        tone=segment.tone,
                        freq_hz=segment.freq_hz,
                        volume=segment.volume,
                        source=segment.source,
                        priority=segment.priority,
                    ),
                )
                slots.append(slot)
            if len(slots) >= self._slots_per_channel:
                break
        if not slots:
            return
        if len(slots) == 1:
            pyxel.play(channel, slots[0])
        else:
            pyxel.play(channel, slots)

    def update(self, now_s: float | None = None) -> None:
        import pyxel

        self._ensure_configured()
        now = time.perf_counter() if now_s is None else float(now_s)
        self._advance_epoch_if_needed(now)
        playhead_tick = self._epoch_playhead_tick(now)
        horizon_end_tick = playhead_tick + self._horizon_ticks
        assignments = self._build_tick_assignments(
            playhead_tick=playhead_tick,
            horizon_end_tick=horizon_end_tick,
        )

        for channel in range(4):
            desired = self._compress_channel_segments(
                channel=channel,
                playhead_tick=playhead_tick,
                assignments=assignments,
                horizon_end_tick=horizon_end_tick,
            )
            existing = self._trim_plan(plan=self._channel_plans[channel], playhead_tick=playhead_tick)
            if desired == existing:
                continue
            if pyxel.play_pos(channel) is not None or existing:
                pyxel.stop(channel)
            if desired:
                self._play_channel_segments(channel, desired)
            self._channel_plans[channel] = _ChannelPlan(
                epoch_id=self._active_epoch_id,
                anchor_tick=playhead_tick,
                segments=desired,
            )


def play_audio_events(events: tuple[AudioEvent, ...] | list[AudioEvent]) -> None:
    global _GLOBAL_PLAYER
    if _GLOBAL_PLAYER is None:
        _GLOBAL_PLAYER = PyxelAudioPlayer()
    _GLOBAL_PLAYER.submit(events)
    _GLOBAL_PLAYER.update()


_GLOBAL_PLAYER: PyxelAudioPlayer | None = None
