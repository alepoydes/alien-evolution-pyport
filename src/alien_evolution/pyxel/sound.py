from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import Final

from ..zx.runtime import AudioClockSnapshot, AudioEvent, AudioNoteEvent, AudioResetEvent

_AUDIO_WAVEFORMS = ("S", "T", "P", "N")
_A2_REFERENCE_HZ = 429.89
_PYXEL_SOUND_SPEED_MAX = 255
_SCHEDULE_HORIZON_TICKS: Final[int] = 96


@dataclass(frozen=True, slots=True)
class AudioDebugStats:
    late_head_ticks_lost: int = 0
    late_partially_played_events: int = 0
    fully_missed_events: int = 0
    fully_missed_ticks: int = 0
    saturation_dropped_events: int = 0
    saturation_dropped_ticks: int = 0
    active_epoch_id: int = 0
    current_playhead_tick: int = 0


@dataclass(frozen=True, slots=True)
class _ChannelSegment:
    is_rest: bool
    ticks: int
    waveform: str
    effect: str
    freq_hz: float
    volume: int
    source: str
    priority: int


@dataclass(slots=True)
class _ChannelPlan:
    epoch_id: int = 0
    anchor_tick: int = 0
    segments: tuple[_ChannelSegment, ...] = ()


@dataclass(slots=True)
class _QueuedNote:
    order: int
    event: AudioNoteEvent
    available_from_tick: int
    saturation_recorded: bool = False


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
    waveform = str(event.waveform or "S").upper()
    if waveform not in _AUDIO_WAVEFORMS:
        waveform = "S"

    freq = float(event.freq_hz)
    if freq < 20.0:
        freq = 20.0
    freq_max = 20_000.0 if waveform == "N" else 5000.0
    if freq > freq_max:
        freq = freq_max

    return AudioNoteEvent(
        epoch_id=event.epoch_id,
        start_tick=event.start_tick,
        duration_ticks=event.duration_ticks,
        waveform=waveform,
        effect=str(event.effect or "N").upper(),
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
        if segment.waveform == "N":
            note = _noise_note_from_hz(segment.freq_hz)
        else:
            note = _note_from_hz(segment.freq_hz)
        notes = note
        tones = segment.waveform if segment.waveform in _AUDIO_WAVEFORMS else "S"
        volumes = str(segment.volume)
        effects = str(segment.effect or "N").upper()

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
    waveform: str = "S",
    channel: int = 0,
    volume: int = 7,
) -> None:
    import pyxel

    ticks = max(1, int(round(float(duration_s) * 120.0)))
    segment = _ChannelSegment(
        is_rest=False,
        ticks=ticks,
        waveform=str(waveform or "S").upper(),
        effect="N",
        freq_hz=float(freq_hz),
        volume=volume,
        source="generic",
        priority=25,
    )
    _sound_set_from_segment(0, segment)
    pyxel.play(channel, 0)


class PyxelAudioPlayer:
    """Monotonic wall-clock audio scheduler backed by four equal Pyxel channels."""

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
        self._next_note_order = 0
        self._epoch_note_events: dict[int, list[_QueuedNote]] = {0: []}
        self._epoch_reset_events: dict[int, AudioResetEvent] = {}
        self._epoch_accounted_ticks: dict[int, int] = {0: 0}
        self._active_epoch_id = 0
        self._epoch_origin_time_s = time.perf_counter()
        self._channel_plans = [_ChannelPlan(epoch_id=0) for _ in range(4)]

        self._late_head_ticks_lost = 0
        self._late_partially_played_events = 0
        self._fully_missed_events = 0
        self._fully_missed_ticks = 0
        self._saturation_dropped_events = 0
        self._saturation_dropped_ticks = 0

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

    @staticmethod
    def _queued_sort_key(note: _QueuedNote) -> tuple[int, int, int]:
        return (note.event.start_tick, -note.event.priority, note.order)

    @staticmethod
    def _selection_sort_key(note: _QueuedNote) -> tuple[int, int, int]:
        return (-note.event.priority, note.event.start_tick, note.order)

    @staticmethod
    def _note_end_tick(note: _QueuedNote) -> int:
        return int(note.event.start_tick) + int(note.event.duration_ticks)

    @staticmethod
    def _effective_note_start_tick(note: _QueuedNote) -> int:
        return max(int(note.event.start_tick), int(note.available_from_tick))

    def _epoch_playhead_tick(self, now_s: float) -> int:
        elapsed_s = max(0.0, float(now_s) - float(self._epoch_origin_time_s))
        return max(0, int(math.floor((elapsed_s * 120.0) + 1e-9)))

    def _record_submit_losses(self, note: _QueuedNote, *, current_epoch_id: int, current_tick: int) -> None:
        if note.event.epoch_id != current_epoch_id:
            return
        if note.available_from_tick <= note.event.start_tick:
            return
        note_end_tick = self._note_end_tick(note)
        if note.available_from_tick >= note_end_tick:
            self._fully_missed_events += 1
            self._fully_missed_ticks += max(0, note_end_tick - int(note.event.start_tick))
            return
        self._late_head_ticks_lost += max(0, note.available_from_tick - int(note.event.start_tick))
        self._late_partially_played_events += 1

    def _account_saturation_until(self, *, epoch_id: int, until_tick: int) -> None:
        reset = self._epoch_reset_events.get(epoch_id)
        end_tick = max(0, int(until_tick))
        if reset is not None:
            end_tick = min(end_tick, max(0, int(reset.cut_tick)))

        start_tick = max(0, int(self._epoch_accounted_ticks.get(epoch_id, 0)))
        if end_tick <= start_tick:
            self._epoch_accounted_ticks[epoch_id] = end_tick
            return

        notes = [
            note
            for note in self._epoch_note_events.get(epoch_id, [])
            if self._effective_note_start_tick(note) < end_tick and self._note_end_tick(note) > start_tick
        ]
        for tick in range(start_tick, end_tick):
            active = [
                note
                for note in notes
                if self._effective_note_start_tick(note) <= tick < self._note_end_tick(note)
            ]
            active.sort(key=self._selection_sort_key)
            if len(active) <= 4:
                continue
            dropped = active[4:]
            self._saturation_dropped_ticks += len(dropped)
            for note in dropped:
                if note.saturation_recorded:
                    continue
                note.saturation_recorded = True
                self._saturation_dropped_events += 1

        self._epoch_accounted_ticks[epoch_id] = end_tick

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
            self._account_saturation_until(epoch_id=self._active_epoch_id, until_tick=cut_tick)
            pyxel.stop()
            self._active_epoch_id = int(reset.next_epoch_id)
            self._epoch_origin_time_s = cut_time_s
            self._channel_plans = [_ChannelPlan(epoch_id=self._active_epoch_id) for _ in range(4)]
            self._epoch_note_events.setdefault(self._active_epoch_id, [])
            self._epoch_accounted_ticks.setdefault(self._active_epoch_id, 0)

    def clock_snapshot(self, now_s: float | None = None) -> AudioClockSnapshot:
        now = time.perf_counter() if now_s is None else float(now_s)
        self._advance_epoch_if_needed(now)
        return AudioClockSnapshot(
            current_epoch_id=self._active_epoch_id,
            current_tick=self._epoch_playhead_tick(now),
        )

    def submit(self, events: tuple[AudioEvent, ...] | list[AudioEvent], now_s: float | None = None) -> None:
        now = time.perf_counter() if now_s is None else float(now_s)
        current_epoch_id = self._active_epoch_id
        current_tick = self._epoch_playhead_tick(now)

        for raw in events:
            if isinstance(raw, AudioNoteEvent):
                event = _normalized_note_event(raw)
                available_from_tick = current_tick if event.epoch_id == current_epoch_id else 0
                queued = _QueuedNote(
                    order=self._next_note_order,
                    event=event,
                    available_from_tick=available_from_tick,
                )
                self._next_note_order += 1
                self._record_submit_losses(queued, current_epoch_id=current_epoch_id, current_tick=current_tick)
                notes = self._epoch_note_events.setdefault(event.epoch_id, [])
                notes.append(queued)
                notes.sort(key=self._queued_sort_key)
                self._epoch_accounted_ticks.setdefault(event.epoch_id, 0)
                continue

            if isinstance(raw, AudioResetEvent):
                current = self._epoch_reset_events.get(raw.epoch_id)
                if current is None or int(raw.cut_tick) < int(current.cut_tick):
                    self._epoch_reset_events[raw.epoch_id] = raw
                self._epoch_note_events.setdefault(int(raw.next_epoch_id), [])
                self._epoch_accounted_ticks.setdefault(int(raw.next_epoch_id), 0)

    def _active_notes_for_window(self, *, playhead_tick: int, horizon_end_tick: int) -> list[_QueuedNote]:
        reset = self._epoch_reset_events.get(self._active_epoch_id)
        cut_tick = horizon_end_tick
        if reset is not None:
            cut_tick = min(cut_tick, max(0, int(reset.cut_tick)))
        return [
            note
            for note in self._epoch_note_events.get(self._active_epoch_id, [])
            if self._effective_note_start_tick(note) < cut_tick and self._note_end_tick(note) > playhead_tick
        ]

    def _build_tick_assignments(
        self,
        *,
        playhead_tick: int,
        horizon_end_tick: int,
    ) -> list[list[_QueuedNote | None]]:
        active_notes = self._active_notes_for_window(playhead_tick=playhead_tick, horizon_end_tick=horizon_end_tick)
        assignments = [[None] * 4 for _ in range(max(0, horizon_end_tick - playhead_tick))]
        prev: list[_QueuedNote | None] = [None, None, None, None]

        for offset, tick in enumerate(range(playhead_tick, horizon_end_tick)):
            selected = [
                note
                for note in active_notes
                if self._effective_note_start_tick(note) <= tick < self._note_end_tick(note)
            ]
            selected.sort(key=self._selection_sort_key)
            selected = selected[:4]

            row: list[_QueuedNote | None] = [None, None, None, None]
            remaining = list(selected)
            for channel in range(4):
                prev_note = prev[channel]
                if prev_note is not None and prev_note in remaining:
                    row[channel] = prev_note
                    remaining.remove(prev_note)

            for note in remaining:
                for channel in range(4):
                    if row[channel] is None:
                        row[channel] = note
                        break

            assignments[offset] = row
            prev = list(row)

        return assignments

    def _remaining_tick_limit(self, note: _QueuedNote) -> int:
        limit = self._note_end_tick(note)
        reset = self._epoch_reset_events.get(note.event.epoch_id)
        if reset is not None:
            limit = min(limit, int(reset.cut_tick))
        return limit

    def _compress_channel_segments(
        self,
        *,
        channel: int,
        playhead_tick: int,
        assignments: list[list[_QueuedNote | None]],
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
                        waveform="N",
                        effect="N",
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
                        waveform=note.event.waveform,
                        effect=note.event.effect,
                        freq_hz=note.event.freq_hz,
                        volume=note.event.volume,
                        source=note.event.source,
                        priority=note.event.priority,
                    )
                )
            idx = run_end

        compact = tuple(segment for segment in segments if segment.ticks > 0)
        if compact and all(segment.is_rest for segment in compact):
            return ()
        return compact

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
                        waveform=segment.waveform,
                        effect=segment.effect,
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
                        waveform=segment.waveform,
                        effect=segment.effect,
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
        self._account_saturation_until(epoch_id=self._active_epoch_id, until_tick=playhead_tick)
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

    def debug_stats(self) -> AudioDebugStats:
        current_playhead_tick = self._epoch_playhead_tick(time.perf_counter())
        return AudioDebugStats(
            late_head_ticks_lost=self._late_head_ticks_lost,
            late_partially_played_events=self._late_partially_played_events,
            fully_missed_events=self._fully_missed_events,
            fully_missed_ticks=self._fully_missed_ticks,
            saturation_dropped_events=self._saturation_dropped_events,
            saturation_dropped_ticks=self._saturation_dropped_ticks,
            active_epoch_id=self._active_epoch_id,
            current_playhead_tick=current_playhead_tick,
        )

    def reset_debug_stats(self) -> None:
        self._late_head_ticks_lost = 0
        self._late_partially_played_events = 0
        self._fully_missed_events = 0
        self._fully_missed_ticks = 0
        self._saturation_dropped_events = 0
        self._saturation_dropped_ticks = 0
        current_tick = self._epoch_playhead_tick(time.perf_counter())
        for epoch_id in tuple(self._epoch_accounted_ticks.keys()):
            self._epoch_accounted_ticks[epoch_id] = current_tick if epoch_id == self._active_epoch_id else 0
        for notes in self._epoch_note_events.values():
            for note in notes:
                note.saturation_recorded = False


def play_audio_events(events: tuple[AudioEvent, ...] | list[AudioEvent]) -> None:
    global _GLOBAL_PLAYER
    if _GLOBAL_PLAYER is None:
        _GLOBAL_PLAYER = PyxelAudioPlayer()
    _GLOBAL_PLAYER.submit(events)
    _GLOBAL_PLAYER.update()


_GLOBAL_PLAYER: PyxelAudioPlayer | None = None
