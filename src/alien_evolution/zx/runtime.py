from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final, Protocol, TypeAlias

from .state import StatefulRuntime as _StatefulRuntime

from .screen import ZX_ATTR_BYTES, ZX_BITMAP_BYTES

_AUDIO_TONES: Final[frozenset[str]] = frozenset({"S", "T", "P", "N"})
_DEFAULT_KEYBOARD_ROWS: Final[tuple[int, ...]] = (0xFF,) * 8


def _default_audio_priority(source: str) -> int:
    source_s = str(source or "generic")
    if source_s == "stream_music":
        return 10
    if source_s == "stream_special":
        return 20
    if source_s == "generic":
        return 25
    if source_s == "rom_beeper":
        return 30
    return 25


@dataclass(frozen=True, slots=True)
class AudioClockSnapshot:
    current_epoch_id: int = 0
    current_tick: int = 0

    def __post_init__(self) -> None:
        epoch = max(0, int(self.current_epoch_id))
        if epoch != self.current_epoch_id:
            object.__setattr__(self, "current_epoch_id", epoch)
        tick = max(0, int(self.current_tick))
        if tick != self.current_tick:
            object.__setattr__(self, "current_tick", tick)


@dataclass(frozen=True, slots=True)
class FrameInput:
    """Buttons/joystick snapshot sampled for one frame."""

    joy_kempston: int = 0
    keyboard_rows: tuple[int, ...] = _DEFAULT_KEYBOARD_ROWS
    audio_clock: AudioClockSnapshot = field(default_factory=AudioClockSnapshot)


@dataclass(frozen=True, slots=True)
class AudioNoteEvent:
    """Semantic note event scheduled inside one local audio epoch."""

    epoch_id: int
    start_tick: int
    duration_ticks: int
    lane: int
    tone: str
    freq_hz: float
    volume: int = 7
    source: str = "generic"
    priority: int = 25

    def __post_init__(self) -> None:
        epoch = max(0, int(self.epoch_id))
        if epoch != self.epoch_id:
            object.__setattr__(self, "epoch_id", epoch)
        start_tick = max(0, int(self.start_tick))
        if start_tick != self.start_tick:
            object.__setattr__(self, "start_tick", start_tick)
        duration_ticks = max(1, int(self.duration_ticks))
        if duration_ticks != self.duration_ticks:
            object.__setattr__(self, "duration_ticks", duration_ticks)
        lane = max(0, int(self.lane))
        if lane != self.lane:
            object.__setattr__(self, "lane", lane)
        tone_u = (self.tone or "S").upper()
        if tone_u not in _AUDIO_TONES:
            tone_u = "S"
        if tone_u != self.tone:
            object.__setattr__(self, "tone", tone_u)
        source_s = str(self.source or "generic")
        if source_s != self.source:
            object.__setattr__(self, "source", source_s)
        volume = max(0, min(7, int(self.volume)))
        if volume != self.volume:
            object.__setattr__(self, "volume", volume)
        priority = int(self.priority)
        if priority != self.priority:
            object.__setattr__(self, "priority", priority)


@dataclass(frozen=True, slots=True)
class AudioResetEvent:
    """Cut current epoch at `cut_tick` and activate `next_epoch_id`."""

    epoch_id: int
    cut_tick: int
    next_epoch_id: int

    def __post_init__(self) -> None:
        epoch = max(0, int(self.epoch_id))
        if epoch != self.epoch_id:
            object.__setattr__(self, "epoch_id", epoch)
        cut_tick = max(0, int(self.cut_tick))
        if cut_tick != self.cut_tick:
            object.__setattr__(self, "cut_tick", cut_tick)
        next_epoch = max(epoch + 1, int(self.next_epoch_id))
        if next_epoch != self.next_epoch_id:
            object.__setattr__(self, "next_epoch_id", next_epoch)


AudioEvent: TypeAlias = AudioNoteEvent | AudioResetEvent


@dataclass(frozen=True, slots=True)
class StepTiming:
    """Timing metadata attached to one `step()` result."""

    delay_after_step_frames: int = 0


@dataclass(frozen=True, slots=True)
class StepOutput:
    """Output of one frame step."""

    screen_bitmap: bytes
    screen_attrs: bytes
    flash_phase: int
    audio_events: tuple[AudioEvent, ...]
    border_color: int
    timing: StepTiming = field(default_factory=StepTiming)


class FrameStepRuntime(Protocol):
    """Runtime contract used by GUI/CLI wrappers."""

    def reset(self) -> None:
        ...

    def step(self, frame_input: FrameInput) -> StepOutput:
        ...


StatefulRuntime = _StatefulRuntime


class ZXSpectrumServiceLayer:
    """Narrow ZX-facing service layer for frame-based game runtimes."""

    def __init__(self, screen_bitmap: bytearray, screen_attrs: bytearray) -> None:
        if len(screen_bitmap) != ZX_BITMAP_BYTES:
            raise ValueError(f"screen_bitmap must be {ZX_BITMAP_BYTES} bytes")
        if len(screen_attrs) != ZX_ATTR_BYTES:
            raise ValueError(f"screen_attrs must be {ZX_ATTR_BYTES} bytes")

        self.screen_bitmap: Final[bytearray] = screen_bitmap
        self.screen_attrs: Final[bytearray] = screen_attrs
        self.border_color: int = 0
        self.flash_phase: int = 0
        self.frame_counter: int = 0
        self._frame_input = FrameInput(
            joy_kempston=0,
            keyboard_rows=_DEFAULT_KEYBOARD_ROWS,
        )
        self._audio_clock = AudioClockSnapshot()
        self._audio_emit_epoch_id: int = 0
        self._audio_events: list[AudioEvent] = []
        self._audio_lane_tails: dict[int, dict[int, int]] = {0: {}}
        self._pending_delay_after_step_frames: int = 0

    def reset_zx_output(self) -> None:
        self.border_color = 0
        self.flash_phase = 0
        self._pending_delay_after_step_frames = 0
        self._audio_clock = AudioClockSnapshot()
        self._audio_emit_epoch_id = 0
        self._audio_events.clear()
        self._audio_lane_tails = {0: {}}
        for i in range(len(self.screen_bitmap)):
            self.screen_bitmap[i] = 0
        for i in range(len(self.screen_attrs)):
            self.screen_attrs[i] = 0x07

    @staticmethod
    def _normalize_keyboard_rows(rows: tuple[int, ...] | list[int] | None) -> tuple[int, ...]:
        if rows is None:
            return _DEFAULT_KEYBOARD_ROWS
        normalized = [0xFF] * 8
        limit = min(len(rows), 8)
        for i in range(limit):
            normalized[i] = int(rows[i]) & 0xFF
        return tuple(normalized)

    def _sync_audio_clock(self, snapshot: AudioClockSnapshot | None) -> None:
        if snapshot is None:
            self._audio_clock = AudioClockSnapshot()
            return
        normalized = AudioClockSnapshot(
            current_epoch_id=snapshot.current_epoch_id,
            current_tick=snapshot.current_tick,
        )
        self._audio_clock = normalized
        self._ensure_audio_epoch(normalized.current_epoch_id)
        if self._audio_emit_epoch_id < normalized.current_epoch_id:
            self._audio_emit_epoch_id = normalized.current_epoch_id

    def sample_inputs(
        self,
        joy_kempston: int,
        keyboard_rows: tuple[int, ...] | list[int] | None = None,
        *,
        audio_clock: AudioClockSnapshot | None = None,
    ) -> None:
        self._frame_input = FrameInput(
            joy_kempston=(joy_kempston & 0x1F),
            keyboard_rows=self._normalize_keyboard_rows(keyboard_rows),
            audio_clock=AudioClockSnapshot(
                current_epoch_id=(audio_clock.current_epoch_id if audio_clock is not None else 0),
                current_tick=(audio_clock.current_tick if audio_clock is not None else 0),
            ),
        )
        self._sync_audio_clock(audio_clock)

    def begin_frame(self, frame_input: FrameInput) -> None:
        self._audio_events.clear()
        self._pending_delay_after_step_frames = 0
        self.advance_host_frame()
        self.sample_inputs(
            joy_kempston=frame_input.joy_kempston,
            keyboard_rows=frame_input.keyboard_rows,
            audio_clock=frame_input.audio_clock,
        )

    def advance_host_frame(self) -> None:
        """Advance host-frame clock state without running gameplay logic."""
        self.frame_counter = (self.frame_counter + 1) & 0xFFFFFFFF
        self.flash_phase = (self.frame_counter // 32) & 0x01

    def _set_step_delay_after_frames(self, delay_after_step_frames: int) -> None:
        delay = int(delay_after_step_frames)
        if delay < 0:
            delay = 0
        self._pending_delay_after_step_frames = delay

    def end_frame(self) -> StepOutput:
        emitted = tuple(self._audio_events)
        self._audio_events.clear()
        timing = StepTiming(delay_after_step_frames=self._pending_delay_after_step_frames)
        self._pending_delay_after_step_frames = 0
        return StepOutput(
            screen_bitmap=bytes(self.screen_bitmap),
            screen_attrs=bytes(self.screen_attrs),
            flash_phase=self.flash_phase & 0x01,
            audio_events=emitted,
            border_color=self.border_color & 0x07,
            timing=timing,
        )

    def snapshot_output(self) -> StepOutput:
        return StepOutput(
            screen_bitmap=bytes(self.screen_bitmap),
            screen_attrs=bytes(self.screen_attrs),
            flash_phase=self.flash_phase & 0x01,
            audio_events=(),
            border_color=self.border_color & 0x07,
            timing=StepTiming(delay_after_step_frames=0),
        )

    @property
    def joy_kempston(self) -> int:
        return self._frame_input.joy_kempston

    @property
    def keyboard_rows(self) -> tuple[int, ...]:
        return self._frame_input.keyboard_rows

    @property
    def audio_clock(self) -> AudioClockSnapshot:
        return self._audio_clock

    def _ensure_audio_epoch(self, epoch_id: int) -> None:
        epoch = max(0, int(epoch_id))
        self._audio_lane_tails.setdefault(epoch, {})

    def _lane_tail(self, *, epoch_id: int, lane: int) -> int:
        self._ensure_audio_epoch(epoch_id)
        return max(0, int(self._audio_lane_tails[epoch_id].get(lane, 0)))

    def _set_lane_tail(self, *, epoch_id: int, lane: int, tail_tick: int) -> None:
        self._ensure_audio_epoch(epoch_id)
        self._audio_lane_tails[epoch_id][lane] = max(0, int(tail_tick))

    def audio_epoch_tail(self, epoch_id: int | None = None) -> int:
        epoch = self._audio_emit_epoch_id if epoch_id is None else max(0, int(epoch_id))
        self._ensure_audio_epoch(epoch)
        tails = self._audio_lane_tails.get(epoch, {})
        if not tails:
            return 0
        return max(int(tick) for tick in tails.values())

    def current_audio_tick(self, *, epoch_id: int | None = None) -> int:
        epoch = self._audio_emit_epoch_id if epoch_id is None else max(0, int(epoch_id))
        if epoch != self._audio_clock.current_epoch_id:
            return 0
        return max(0, int(self._audio_clock.current_tick))

    def in_port(self, bc_port: int) -> int:
        if (bc_port & 0x00FF) == 0x1F:
            return self.joy_kempston
        return 0xFF

    def out_port(self, bc_port: int, value: int) -> None:
        value &= 0xFF
        if (bc_port & 0x00FF) != 0xFE:
            return
        self.border_color = value & 0x07

    def emit_note_event(
        self,
        *,
        lane: int,
        tone: str,
        freq_hz: float,
        start_tick: int,
        duration_ticks: int,
        volume: int,
        source: str = "generic",
        priority: int | None = None,
        epoch_id: int | None = None,
    ) -> None:
        epoch = self._audio_emit_epoch_id if epoch_id is None else max(0, int(epoch_id))
        event = AudioNoteEvent(
            epoch_id=epoch,
            start_tick=start_tick,
            duration_ticks=duration_ticks,
            lane=lane,
            tone=tone,
            freq_hz=float(freq_hz),
            volume=volume,
            source=source,
            priority=_default_audio_priority(source) if priority is None else int(priority),
        )
        self._audio_events.append(event)
        self._set_lane_tail(
            epoch_id=event.epoch_id,
            lane=event.lane,
            tail_tick=event.start_tick + event.duration_ticks,
        )

    @staticmethod
    def _duration_ticks_from_seconds(duration_s: float) -> int:
        ticks = int(round(float(duration_s) * 120.0))
        if ticks < 1:
            return 1
        return ticks

    def emit_audio(
        self,
        *,
        tone: str,
        freq_hz: float,
        duration_s: float,
        volume: int,
        lane: int = 0,
        source: str = "generic",
        priority: int | None = None,
        start_tick: int | None = None,
        epoch_id: int | None = None,
    ) -> None:
        epoch = self._audio_emit_epoch_id if epoch_id is None else max(0, int(epoch_id))
        duration_ticks = self._duration_ticks_from_seconds(duration_s)
        if start_tick is None:
            base_tick = self.current_audio_tick(epoch_id=epoch)
            start = max(base_tick, self._lane_tail(epoch_id=epoch, lane=lane))
        else:
            start = max(0, int(start_tick))
        self.emit_note_event(
            lane=lane,
            tone=tone,
            freq_hz=freq_hz,
            start_tick=start,
            duration_ticks=duration_ticks,
            volume=volume,
            source=source,
            priority=priority,
            epoch_id=epoch,
        )

    def emit_immediate_sfx(
        self,
        *,
        lane: int,
        tone: str,
        freq_hz: float,
        duration_ticks: int,
        volume: int,
        source: str = "generic",
        priority: int | None = None,
        epoch_id: int | None = None,
    ) -> None:
        epoch = self._audio_emit_epoch_id if epoch_id is None else max(0, int(epoch_id))
        base_tick = self.current_audio_tick(epoch_id=epoch)
        start_tick = max(base_tick, self._lane_tail(epoch_id=epoch, lane=lane))
        self.emit_note_event(
            lane=lane,
            tone=tone,
            freq_hz=freq_hz,
            start_tick=start_tick,
            duration_ticks=duration_ticks,
            volume=volume,
            source=source,
            priority=priority,
            epoch_id=epoch,
        )

    def schedule_reset(self, cut_tick: int | None = None) -> int:
        epoch = max(0, int(self._audio_emit_epoch_id))
        if cut_tick is None:
            cut = self.audio_epoch_tail(epoch)
        else:
            cut = max(0, int(cut_tick))
        next_epoch = max(epoch + 1, self._audio_clock.current_epoch_id + 1)
        self._audio_events.append(
            AudioResetEvent(
                epoch_id=epoch,
                cut_tick=cut,
                next_epoch_id=next_epoch,
            )
        )
        self._audio_emit_epoch_id = next_epoch
        self._ensure_audio_epoch(next_epoch)
        return next_epoch

    def emit_rom_beeper(
        self,
        period: int,
        ticks: int,
        tone: str = "S",
        *,
        volume: int = 5,
        lane: int = 2,
        source: str = "rom_beeper",
        priority: int | None = None,
        start_tick: int | None = None,
        epoch_id: int | None = None,
    ) -> None:
        p = max(1, int(period) & 0xFFFF)
        waves = max(1, int(ticks) & 0xFFFF)
        half_period_t = 4.0 * (float(p) + 30.125)
        full_period_t = 2.0 * half_period_t
        freq = 3_500_000.0 / full_period_t
        duration = float(waves) / freq
        self.emit_audio(
            tone=tone,
            freq_hz=freq,
            duration_s=duration,
            volume=volume,
            lane=lane,
            source=source,
            priority=priority,
            start_tick=start_tick,
            epoch_id=epoch_id,
        )
