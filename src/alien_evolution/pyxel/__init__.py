"""Pyxel backend for Alien Evolution frame-step runtimes."""

from typing import Any

from .input import joy_kempston, keyboard_rows, read_frame_input
from .screen import apply_zx_palette, blit_zx_screen_to_pyxel
from .sound import AudioDebugStats, PyxelAudioPlayer, beep, play_audio_events
from .runner import run_pyxel_game


def run_fmf_player(*args: Any, **kwargs: Any) -> None:
    from .fmfplayer import run_fmf_player as _run_fmf_player

    _run_fmf_player(*args, **kwargs)


__all__ = [
    "run_fmf_player",
    "joy_kempston",
    "keyboard_rows",
    "read_frame_input",
    "apply_zx_palette",
    "blit_zx_screen_to_pyxel",
    "PyxelAudioPlayer",
    "AudioDebugStats",
    "beep",
    "play_audio_events",
    "run_pyxel_game",
]
