from __future__ import annotations

import unittest

from alien_evolution.alienevolution.logic import AlienEvolutionPort
from alien_evolution.zx.pointers import BlockPtr


class EnemyAISemanticsTests(unittest.TestCase):
    def test_random_fallback_uses_progressive_r_register_sequence(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._z80_r_register = 0x00

        ptr = BlockPtr(bytearray(1), 0x00)
        samples = [runtime._queue_ai_random_fallback_state(A_state=0x00, BC_cell=ptr)[0] for _ in range(4)]

        # The port approximates ZX `LD A,R` with a shared R-register helper,
        # so repeated fallback calls inside one frame still observe different
        # chooser states.
        self.assertEqual(samples, [0x02, 0x04, 0x08, 0x01])

    def test_level_init_clears_last_move_delta_before_player_moves(self) -> None:
        for cheat in ("lvl1", "lvl2", "lvl3"):
            with self.subTest(cheat=cheat):
                runtime = AlienEvolutionPort()

                self.assertTrue(runtime.apply_cheat_sequence(cheat))
                self.assertEqual(runtime.var_runtime_move_delta & 0xFFFF, 0x0000)

    def test_queue_3_fallback_with_no_prior_move_drops_to_random_chooser(self) -> None:
        runtime = AlienEvolutionPort()

        self.assertTrue(runtime.apply_cheat_sequence("lvl1"))
        runtime._z80_r_register = 0x00

        adult_ptr = runtime.var_runtime_queue_head_3.entries[0x00].cell_ptr
        self.assertIsNotNone(adult_ptr)

        a_next = runtime._queue_3_fallback_direction_from_player_delta(BC_cell=adult_ptr)

        self.assertEqual(a_next, 0x02)


if __name__ == "__main__":
    unittest.main()
