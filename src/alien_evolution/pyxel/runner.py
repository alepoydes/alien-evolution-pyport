from __future__ import annotations

import sys
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Deque, Sequence

from ..fileio.stateio import load_state_json, save_state_json
from ..zx.runtime import FrameInput, FrameStepRuntime, StepOutput, ZXSpectrumServiceLayer
from ..zx.screen import ZX_ATTR_BYTES, ZX_BITMAP_BYTES, ZX_SCREEN_H, ZX_SCREEN_W
from ..zx.state import StatefulRuntime, ensure_stateful_runtime
from .input import read_frame_input
from .screen import apply_zx_palette, blit_zx_screen_to_pyxel
from .sound import PyxelAudioPlayer

DEFAULT_HISTORY_INTERVAL_HOST_FRAMES = 500
DEFAULT_HISTORY_MAX_CHECKPOINTS = 120
DEFAULT_QUICKSAVE_FILENAME = "pyxel_quicksave.state.json"
DEFAULT_SCREEN_MESSAGE_TTL_SECONDS = 1.0


def _save_autosave_state(runtime: StatefulRuntime) -> dict[str, object]:
    save_autosave = getattr(runtime, "save_autosave_state", None)
    if callable(save_autosave):
        state = save_autosave()
        if isinstance(state, dict):
            return state
    return runtime.save_state()


@dataclass(frozen=True)
class RuntimeCheckpoint:
    host_frame_index: int
    state: dict[str, object]


@dataclass(frozen=True)
class _ScreenMessage:
    text: str
    expires_at_host_frame: int


class ScreenMessageQueue:
    def __init__(self, *, ttl_host_frames: int) -> None:
        self.ttl_host_frames = max(1, int(ttl_host_frames))
        self._messages: Deque[_ScreenMessage] = deque()

    @property
    def messages(self) -> Sequence[str]:
        return tuple(item.text for item in self._messages)

    def push(self, text: str, *, host_frame_index: int) -> None:
        self._messages.append(
            _ScreenMessage(
                text=str(text),
                expires_at_host_frame=int(host_frame_index) + self.ttl_host_frames,
            ),
        )

    def prune(self, *, host_frame_index: int) -> None:
        frame = int(host_frame_index)
        while self._messages and self._messages[0].expires_at_host_frame <= frame:
            self._messages.popleft()


class RuntimeStateHistory:
    def __init__(self, *, interval_host_frames: int, max_checkpoints: int) -> None:
        self.interval_host_frames = max(1, int(interval_host_frames))
        self._checkpoints: Deque[RuntimeCheckpoint] = deque(maxlen=max(2, int(max_checkpoints)))
        self._last_capture_host_frame: int | None = None

    def maybe_capture(self, runtime: StatefulRuntime, *, host_frame_index: int) -> bool:
        if self._last_capture_host_frame is None:
            return self.force_capture(runtime, host_frame_index=host_frame_index)
        if (host_frame_index - self._last_capture_host_frame) < self.interval_host_frames:
            return False
        return self.force_capture(runtime, host_frame_index=host_frame_index)

    def force_capture(self, runtime: StatefulRuntime, *, host_frame_index: int) -> bool:
        state = _save_autosave_state(runtime)
        self._checkpoints.append(
            RuntimeCheckpoint(
                host_frame_index=int(host_frame_index),
                state=state,
            ),
        )
        self._last_capture_host_frame = int(host_frame_index)
        return True

    def rollback(self, runtime: StatefulRuntime, *, steps: int = 1) -> bool:
        if len(self._checkpoints) < 2:
            return False
        pop_count = max(1, int(steps))
        for _ in range(pop_count):
            if len(self._checkpoints) <= 1:
                break
            self._checkpoints.pop()
        if not self._checkpoints:
            return False
        checkpoint = self._checkpoints[-1]
        runtime.load_state(checkpoint.state)
        self._last_capture_host_frame = checkpoint.host_frame_index
        return True


def run_pyxel_game(
    runtime: FrameStepRuntime,
    *,
    title: str,
    fps: int = 50,
    display_scale: int = 2,
    margin_x: int = 32,
    margin_y: int = 24,
    history_interval_host_frames: int = DEFAULT_HISTORY_INTERVAL_HOST_FRAMES,
    history_max_checkpoints: int = DEFAULT_HISTORY_MAX_CHECKPOINTS,
    quicksave_path: Path | None = None,
    screen_message_ttl_seconds: float = DEFAULT_SCREEN_MESSAGE_TTL_SECONDS,
    dev_tools: bool = True,
) -> None:
    """Run a frame-step runtime in a Pyxel window."""
    import pyxel

    width = ZX_SCREEN_W + margin_x * 2
    height = ZX_SCREEN_H + margin_y * 2

    runtime.reset()
    audio_player = PyxelAudioPlayer()
    pending_delay_frames = 0
    host_frame_index = 0
    screen_messages: ScreenMessageQueue | None = None
    quicksave_file: Path | None = None
    if dev_tools:
        message_ttl_host_frames = max(1, int(round(float(screen_message_ttl_seconds) * fps)))
        screen_messages = ScreenMessageQueue(ttl_host_frames=message_ttl_host_frames)
        if quicksave_path is None:
            quicksave_file = Path.cwd() / DEFAULT_QUICKSAVE_FILENAME
        else:
            quicksave_file = Path(quicksave_path)
            if not quicksave_file.is_absolute():
                quicksave_file = Path.cwd() / quicksave_file

    stateful_runtime: StatefulRuntime | None = None
    if dev_tools or history_interval_host_frames > 0:
        try:
            stateful_runtime = ensure_stateful_runtime(runtime)
        except TypeError:
            stateful_runtime = None

    history: RuntimeStateHistory | None = None
    if stateful_runtime is not None and history_interval_host_frames > 0:
        history = RuntimeStateHistory(
            interval_host_frames=history_interval_host_frames,
            max_checkpoints=history_max_checkpoints,
        )
        history.force_capture(stateful_runtime, host_frame_index=0)

    if isinstance(runtime, ZXSpectrumServiceLayer):
        last_output: StepOutput = runtime.snapshot_output()
    else:
        # Fallback for external runtimes that implement only the protocol.
        # Do not pre-step here: backend must call step() exactly per frame update.
        last_output = StepOutput(
            screen_bitmap=bytes(ZX_BITMAP_BYTES),
            screen_attrs=bytes([0x07] * ZX_ATTR_BYTES),
            flash_phase=0,
            audio_commands=(),
            border_color=0,
        )
    redraw_required = True

    def _refresh_snapshot_output() -> None:
        nonlocal last_output
        snapshot = getattr(runtime, "snapshot_output", None)
        if callable(snapshot):
            last_output = snapshot()

    def _log_state_error(action: str, exc: Exception) -> None:
        print(f"{type(runtime).__name__} {action} failed: {exc}", file=sys.stderr)

    def _push_screen_message(text: str) -> None:
        nonlocal redraw_required
        if screen_messages is None:
            return
        screen_messages.push(text, host_frame_index=host_frame_index)
        redraw_required = True

    def _handle_state_hotkeys() -> None:
        nonlocal pending_delay_frames, history, redraw_required
        if not dev_tools:
            return
        if hasattr(pyxel, "KEY_F10") and pyxel.btnp(pyxel.KEY_F10):
            try:
                runtime.reset()
                pending_delay_frames = 0
                _refresh_snapshot_output()
                redraw_required = True
                if stateful_runtime is not None and history_interval_host_frames > 0:
                    history = RuntimeStateHistory(
                        interval_host_frames=history_interval_host_frames,
                        max_checkpoints=history_max_checkpoints,
                    )
                    history.force_capture(stateful_runtime, host_frame_index=host_frame_index)
                _push_screen_message("Reset done")
            except Exception as exc:  # pragma: no cover - runtime/UI error path
                _log_state_error("reset", exc)
                _push_screen_message("Reset failed")
        if stateful_runtime is None:
            return
        if hasattr(pyxel, "KEY_F5") and pyxel.btnp(pyxel.KEY_F5):
            try:
                assert quicksave_file is not None
                save_state_json(quicksave_file, _save_autosave_state(stateful_runtime))
                _push_screen_message("Quick-save done")
            except Exception as exc:  # pragma: no cover - runtime/UI error path
                _log_state_error("quick-save", exc)
                _push_screen_message("Quick-save failed")
        if hasattr(pyxel, "KEY_F9") and pyxel.btnp(pyxel.KEY_F9):
            try:
                assert quicksave_file is not None
                envelope = load_state_json(quicksave_file)
                stateful_runtime.load_state(envelope)
                pending_delay_frames = 0
                _refresh_snapshot_output()
                redraw_required = True
                if history is not None:
                    history.force_capture(stateful_runtime, host_frame_index=host_frame_index)
                _push_screen_message("Quick-load done")
            except Exception as exc:  # pragma: no cover - runtime/UI error path
                _log_state_error("quick-load", exc)
                _push_screen_message("Quick-load failed")
        if hasattr(pyxel, "KEY_F8") and pyxel.btnp(pyxel.KEY_F8):
            if history is None:
                _push_screen_message("Rollback unavailable")
                return
            try:
                if history.rollback(stateful_runtime, steps=1):
                    pending_delay_frames = 0
                    _refresh_snapshot_output()
                    redraw_required = True
                    _push_screen_message("Rollback done")
                else:
                    _push_screen_message("Rollback unavailable")
            except Exception as exc:  # pragma: no cover - runtime/UI error path
                _log_state_error("rollback", exc)
                _push_screen_message("Rollback failed")
        if hasattr(pyxel, "KEY_F7") and pyxel.btnp(pyxel.KEY_F7):
            if history is None:
                _push_screen_message("Checkpoint unavailable")
                return
            try:
                history.force_capture(stateful_runtime, host_frame_index=host_frame_index)
                _push_screen_message("Checkpoint saved")
            except Exception as exc:  # pragma: no cover - runtime/UI error path
                _log_state_error("checkpoint", exc)
                _push_screen_message("Checkpoint failed")

    def _advance_runtime_host_frame() -> None:
        if isinstance(runtime, ZXSpectrumServiceLayer):
            runtime.advance_host_frame()
            return
        advance = getattr(runtime, "advance_host_frame", None)
        if callable(advance):
            advance()
            return
        raise RuntimeError(
            "Runtime requested post-step delay but does not implement advance_host_frame()",
        )

    def _update() -> None:
        nonlocal host_frame_index, last_output, pending_delay_frames, redraw_required
        host_frame_index += 1
        if screen_messages is not None:
            messages_before = tuple(screen_messages.messages)
        else:
            messages_before = ()

        _handle_state_hotkeys()

        if screen_messages is not None:
            screen_messages.prune(host_frame_index=host_frame_index)
            if tuple(screen_messages.messages) != messages_before:
                redraw_required = True

        if pending_delay_frames > 0:
            prev_flash_phase = int(last_output.flash_phase) & 0x01
            prev_border_color = int(last_output.border_color) & 0x07
            _advance_runtime_host_frame()
            pending_delay_frames -= 1
            _refresh_snapshot_output()
            if (
                ((int(last_output.flash_phase) & 0x01) != prev_flash_phase)
                or ((int(last_output.border_color) & 0x07) != prev_border_color)
            ):
                redraw_required = True
            audio_player.update()
            if history is not None and stateful_runtime is not None:
                history.maybe_capture(stateful_runtime, host_frame_index=host_frame_index)
            return

        last_output = runtime.step(read_frame_input())
        redraw_required = True
        pending_delay_frames = max(0, int(last_output.timing.delay_after_step_frames))
        audio_player.submit(last_output.audio_commands)
        audio_player.update()
        if history is not None and stateful_runtime is not None:
            history.maybe_capture(stateful_runtime, host_frame_index=host_frame_index)

    def _draw() -> None:
        nonlocal redraw_required
        if not redraw_required:
            return
        blit_zx_screen_to_pyxel(
            last_output.screen_bitmap,
            last_output.screen_attrs,
            x=margin_x,
            y=margin_y,
            border=last_output.border_color,
            flash_phase=last_output.flash_phase,
            method="rect",
        )
        text_x = 4
        text_y = 4
        row_height = 8
        if screen_messages is not None:
            for idx, message in enumerate(screen_messages.messages):
                pyxel.text(text_x, text_y + idx * row_height, message, 10)
        redraw_required = False

    pyxel.init(width, height, title=title, fps=fps, display_scale=display_scale)
    apply_zx_palette()
    pyxel.run(_update, _draw)
