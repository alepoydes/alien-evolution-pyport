"""Demo game logic with I/O-independent frame-step API."""

from __future__ import annotations

from ..zx.runtime import FrameInput, StepOutput, ZXSpectrumServiceLayer
from ..zx.screen import new_zx_screen_buffers, zx_bitmap_index


class DemoLineGame(ZXSpectrumServiceLayer):
    def __init__(self) -> None:
        screen_bitmap, screen_attrs = new_zx_screen_buffers()
        super().__init__(screen_bitmap=screen_bitmap, screen_attrs=screen_attrs)
        self._frame = 0
        self.reset()

    def reset(self) -> None:
        # Reset shared ZX-side frame outputs and clear any pending frame audio.
        self.reset_zx_output()
        # Reset sampled input snapshot to deterministic baseline.
        self.sample_inputs(joy_kempston=0)
        self.frame_counter = 0
        self._frame = 0

        # Attributes: paper=0 (black), ink=7 (white), bright=0, flash=0.
        # `reset_zx_output()` already applies this baseline.

    def step(self, frame_input: FrameInput) -> StepOutput:
        self.begin_frame(frame_input)

        self.frame_counter = (self.frame_counter + 1) & 0xFFFFFFFF
        self._frame = self.frame_counter

        # Demo: flash toggles every ~32 frames.
        self.flash_phase = (self._frame // 32) & 1

        # Demo: border cycles when Fire is pressed.
        if self.joy_kempston & 0x10:
            self.border_color = (self.border_color + 1) & 7

        # Demo: draw a moving vertical bar.
        xpix = (self._frame // 2) & 255
        xb = xpix >> 3
        bit = 0x80 >> (xpix & 7)

        # Clear previous column-ish.
        prev_x = ((self._frame - 1) // 2) & 255
        prev_xb = prev_x >> 3
        prev_bit = 0x80 >> (prev_x & 7)

        for y in range(192):
            idx_prev = zx_bitmap_index(prev_xb, y)
            self.screen_bitmap[idx_prev] &= (~prev_bit) & 0xFF

            idx = zx_bitmap_index(xb, y)
            self.screen_bitmap[idx] |= bit

        return self.end_frame()

    # Backward-compatible shim for older wrappers.
    def tick(self, joy: int) -> StepOutput:
        return self.step(FrameInput(joy_kempston=joy))
