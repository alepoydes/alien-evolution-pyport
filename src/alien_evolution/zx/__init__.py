"""ZX Spectrum emulation-facing helpers for the port.

This subpackage contains:
- ZX screen buffer layouts and address mapping,
- frame-step runtime contracts and service helpers.
"""

from .screen import (
    ZX_SCREEN_W,
    ZX_SCREEN_H,
    ZX_BITMAP_BYTES,
    ZX_ATTR_BYTES,
    new_zx_screen_buffers,
    zx_bitmap_index,
    zx_attr_index,
    ZX_PALETTE_16,
)
from .runtime import (
    FrameInput,
    AudioClockSnapshot,
    AudioEvent,
    AudioNoteEvent,
    AudioResetEvent,
    AudioWaveform,
    StepTiming,
    StepOutput,
    FrameStepRuntime,
    StatefulRuntime,
    ZXSpectrumServiceLayer,
)
from .pointers import BlockPtr, StructFieldPtr
from .state import StatefulManifestRuntime

__all__ = [
    "ZX_SCREEN_W",
    "ZX_SCREEN_H",
    "ZX_BITMAP_BYTES",
    "ZX_ATTR_BYTES",
    "new_zx_screen_buffers",
    "zx_bitmap_index",
    "zx_attr_index",
    "ZX_PALETTE_16",
    "FrameInput",
    "AudioClockSnapshot",
    "AudioEvent",
    "AudioNoteEvent",
    "AudioResetEvent",
    "AudioWaveform",
    "StepTiming",
    "StepOutput",
    "FrameStepRuntime",
    "StatefulRuntime",
    "StatefulManifestRuntime",
    "ZXSpectrumServiceLayer",
    "BlockPtr",
    "StructFieldPtr",
]
