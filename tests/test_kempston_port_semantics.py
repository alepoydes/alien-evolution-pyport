from __future__ import annotations

import unittest

from alien_evolution.alienevolution.logic import AlienEvolutionPort


class KempstonPortSemanticsTests(unittest.TestCase):
    def test_default_keyboard_profile_slot6_uses_e_key(self) -> None:
        runtime = AlienEvolutionPort()

        self.assertEqual(runtime.patch_control_scan_slot_6_port_word, 0xFBFE)
        self.assertEqual(runtime.patch_control_scan_slot_6_prefix_opcode, 0xCB)
        self.assertEqual(runtime.patch_control_scan_slot_6_bit_opcode, 0x57)
        self.assertEqual(runtime.patch_control_scan_slot_6_branch_opcode, 0xCA)
        self.assertEqual(runtime.const_define_keys_descriptor_table[5].port_word, 0xFBFE)
        self.assertEqual(runtime.const_define_keys_descriptor_table[5].mask_byte, 0x57)

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

    def test_kempston_preset_slot6_is_symbol_shift_only(self) -> None:
        runtime = AlienEvolutionPort()
        runtime.control_preset_branch()

        self.assertEqual(runtime.patch_control_scan_slot_6_port_word, 0x7FFE)
        self.assertEqual(runtime.patch_control_scan_slot_6_prefix_opcode, 0xCB)
        self.assertEqual(runtime.patch_control_scan_slot_6_bit_opcode, 0x4F)
        self.assertEqual(runtime.patch_control_scan_slot_6_branch_opcode, 0xCA)


if __name__ == "__main__":
    unittest.main()
