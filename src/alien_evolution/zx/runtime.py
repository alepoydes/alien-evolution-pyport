from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final, Protocol

from .state import StatefulRuntime as _StatefulRuntime

from .screen import ZX_ATTR_BYTES, ZX_BITMAP_BYTES

_AUDIO_TONES: Final[frozenset[str]] = frozenset({"S", "T", "P", "N"})
_DEFAULT_KEYBOARD_ROWS: Final[tuple[int, ...]] = (0xFF,) * 8


@dataclass(frozen=True, slots=True)
class FrameInput:
    """Buttons/joystick snapshot sampled for one frame."""

    joy_kempston: int = 0
    keyboard_rows: tuple[int, ...] = _DEFAULT_KEYBOARD_ROWS


@dataclass(frozen=True, slots=True)
class AudioCommand:
    """High-level audio command emitted by game logic."""

    tone: str
    freq_hz: float
    duration_s: float
    volume: int = 7
    channel: int = 0
    source: str = "generic"
    start_delay_ticks: int = 0

    def __post_init__(self) -> None:
        tone_u = (self.tone or "S").upper()
        if tone_u not in _AUDIO_TONES:
            tone_u = "S"
        if tone_u != self.tone:
            object.__setattr__(self, "tone", tone_u)
        source_s = str(self.source or "generic")
        if source_s != self.source:
            object.__setattr__(self, "source", source_s)
        start_delay = max(0, int(self.start_delay_ticks))
        if start_delay != self.start_delay_ticks:
            object.__setattr__(self, "start_delay_ticks", start_delay)


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
    audio_commands: tuple[AudioCommand, ...]
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
    """Narrow ZX-facing service layer for frame-based game runtimes.

    This is intentionally not a full machine emulator. It provides only helpers
    that the game logic needs:
    - screen buffers in ZX layout,
    - frame-scoped input snapshot,
    - minimal IN/OUT port abstraction for gameplay-visible effects,
    - semantic audio helpers for effects/music.
    """

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
        self._audio_commands: list[AudioCommand] = []
        self._pending_delay_after_step_frames: int = 0

    def reset_zx_output(self) -> None:
        self.border_color = 0
        self.flash_phase = 0
        self._pending_delay_after_step_frames = 0
        self._audio_commands.clear()
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

    def sample_inputs(
        self,
        joy_kempston: int,
        keyboard_rows: tuple[int, ...] | list[int] | None = None,
    ) -> None:
        self._frame_input = FrameInput(
            joy_kempston=(joy_kempston & 0x1F),
            keyboard_rows=self._normalize_keyboard_rows(keyboard_rows),
        )

    def begin_frame(self, frame_input: FrameInput) -> None:
        self._audio_commands.clear()
        self._pending_delay_after_step_frames = 0
        self.advance_host_frame()
        self.sample_inputs(
            joy_kempston=frame_input.joy_kempston,
            keyboard_rows=frame_input.keyboard_rows,
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
        emitted = tuple(self._audio_commands)
        self._audio_commands.clear()
        timing = StepTiming(delay_after_step_frames=self._pending_delay_after_step_frames)
        self._pending_delay_after_step_frames = 0
        return StepOutput(
            screen_bitmap=bytes(self.screen_bitmap),
            screen_attrs=bytes(self.screen_attrs),
            flash_phase=self.flash_phase & 0x01,
            audio_commands=emitted,
            border_color=self.border_color & 0x07,
            timing=timing,
        )

    def snapshot_output(self) -> StepOutput:
        return StepOutput(
            screen_bitmap=bytes(self.screen_bitmap),
            screen_attrs=bytes(self.screen_attrs),
            flash_phase=self.flash_phase & 0x01,
            audio_commands=(),
            border_color=self.border_color & 0x07,
            timing=StepTiming(delay_after_step_frames=0),
        )

    @property
    def joy_kempston(self) -> int:
        return self._frame_input.joy_kempston

    @property
    def keyboard_rows(self) -> tuple[int, ...]:
        return self._frame_input.keyboard_rows

    def in_port(self, bc_port: int) -> int:
        """Read a ZX-like I/O port.

        Supported semantics:
        - 0x001F low byte: Kempston joystick state (active-high bits).
        - everything else: returns 0xFF for now (unknown/unconnected input bus).
        """
        if (bc_port & 0x00FF) == 0x1F:
            return self.joy_kempston
        return 0xFF

    def out_port(self, bc_port: int, value: int) -> None:
        """Write a ZX-like I/O port.

        Supported semantics:
        - 0x00FE low byte:
          - bits 0..2: border color.
        """
        value &= 0xFF
        if (bc_port & 0x00FF) != 0xFE:
            return

        self.border_color = value & 0x07

    def emit_rom_beeper(
        self,
        period: int,
        ticks: int,
        tone: str = "S",
        *,
        volume: int = 5,
        channel: int = 0,
        source: str = "generic",
        start_delay_ticks: int = 0,
    ) -> None:
        """Emit semantic audio command for ROM 0x03B5 beeper call.

        Model:
        - DE is the wave-count term (f * t in the ROM contract),
        - HL is the beeper loop-delay term.
        We derive frequency/duration directly from that contract rather than
        from subjective post-processing.
        """
        p = max(1, int(period) & 0xFFFF)
        waves = max(1, int(ticks) & 0xFFFF)
        # 48K ROM beeper timing model: half-period clock units ~= 4 * (HL + 30.125).
        half_period_t = 4.0 * (float(p) + 30.125)
        full_period_t = 2.0 * half_period_t
        freq = 3_500_000.0 / full_period_t
        duration = float(waves) / freq
        tone_u = (tone or "S").upper()
        self.emit_audio(
            tone=tone_u,
            freq_hz=freq,
            duration_s=duration,
            volume=volume,
            channel=channel,
            source=source,
            start_delay_ticks=start_delay_ticks,
        )

    def emit_audio(
        self,
        *,
        tone: str,
        freq_hz: float,
        duration_s: float,
        volume: int,
        channel: int = 0,
        source: str = "generic",
        start_delay_ticks: int = 0,
    ) -> None:
        tone_u = (tone or "S").upper()
        if tone_u not in ("S", "T", "P", "N"):
            tone_u = "S"
        freq = float(freq_hz)
        duration = float(duration_s)
        vol = max(0, min(7, int(volume)))
        ch_i = max(0, min(3, int(channel)))
        source_s = str(source or "generic")
        delay_ticks = max(0, int(start_delay_ticks))

        if self._audio_commands and delay_ticks == 0:
            last = self._audio_commands[-1]
            if (
                last.tone == tone_u
                and last.volume == vol
                and last.channel == ch_i
                and last.source == source_s
                and abs(last.freq_hz - freq) < 1e-6
            ):
                self._audio_commands[-1] = AudioCommand(
                    tone=tone_u,
                    freq_hz=freq,
                    duration_s=last.duration_s + duration,
                    volume=vol,
                    channel=ch_i,
                    source=source_s,
                    start_delay_ticks=last.start_delay_ticks,
                )
                return

        self._audio_commands.append(
            AudioCommand(
                tone=tone_u,
                freq_hz=freq,
                duration_s=duration,
                volume=vol,
                channel=ch_i,
                source=source_s,
                start_delay_ticks=delay_ticks,
            )
        )
