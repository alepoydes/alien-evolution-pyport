from __future__ import annotations

import unittest

from alien_evolution.alienevolution.logic import AlienEvolutionPort


class KempstonPortSemanticsTests(unittest.TestCase):
    def test_port_df_exposes_kempston_active_high_bits(self) -> None:
        runtime = AlienEvolutionPort()

        runtime.sample_inputs(joy_kempston=0x00, keyboard_rows=(0xFF,) * 8)
        self.assertEqual(runtime.in_port(0x00DF) & 0x1F, 0x00)

        runtime.sample_inputs(joy_kempston=0x01, keyboard_rows=(0xFF,) * 8)
        self.assertEqual(runtime.in_port(0x00DF) & 0x1F, 0x01)

        runtime.sample_inputs(joy_kempston=0x12, keyboard_rows=(0xFF,) * 8)
        self.assertEqual(runtime.in_port(0x00DF) & 0x1F, 0x12)

    def test_port_1f_keeps_raw_kempston_bits(self) -> None:
        runtime = AlienEvolutionPort()
        runtime.sample_inputs(joy_kempston=0x1B, keyboard_rows=(0xFF,) * 8)
        self.assertEqual(runtime.in_port(0x001F), 0x1B)


if __name__ == "__main__":
    unittest.main()
