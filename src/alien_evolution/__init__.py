"""Alien Evolution (ZX Spectrum) → Pyxel port scaffold.

This package intentionally focuses on:
- explicit buffers instead of a monolithic address space;
- backend-agnostic game logic API (`reset`/`step`);
- peripheral backends implemented in dedicated subpackages.

The actual game logic should live in :mod:`alien_evolution.alienevolution.logic`.
The lightweight demo implementation lives in :mod:`alien_evolution.demoline.logic`.
"""

from .zx.screen import (
    ZX_SCREEN_W,
    ZX_SCREEN_H,
    ZX_BITMAP_BYTES,
    ZX_ATTR_BYTES,
    ZX_PALETTE_16,
    new_zx_screen_buffers,
)
from .zx.runtime import FrameInput, AudioCommand, StepOutput, FrameStepRuntime, StatefulRuntime
from .zx.state import StatefulManifestRuntime

__all__ = [
    "ZX_SCREEN_W",
    "ZX_SCREEN_H",
    "ZX_BITMAP_BYTES",
    "ZX_ATTR_BYTES",
    "ZX_PALETTE_16",
    "new_zx_screen_buffers",
    "FrameInput",
    "AudioCommand",
    "StepOutput",
    "FrameStepRuntime",
    "StatefulRuntime",
    "StatefulManifestRuntime",
]
