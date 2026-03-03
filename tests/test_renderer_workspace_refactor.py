from __future__ import annotations

import unittest

from alien_evolution.alienevolution.blocks import (
    RENDERER_WORKSPACE_LEN_CELL_BLIT_WORK_BUFFER,
    RENDERER_WORKSPACE_LEN_LINEAR_VIEWPORT_WORK_BUFFER,
    RENDERER_WORKSPACE_LEN_RENDER_WORK_AREA_TAIL,
    RENDERER_WORKSPACE_LEN_TOTAL,
    RENDERER_WORKSPACE_LEN_VISIBLE_CELL_STAGING_LATTICE,
    RENDERER_WORKSPACE_LEN_VISIBLE_CELL_STAGING_MID_WINDOW,
    RENDERER_WORKSPACE_LEN_VISIBLE_CELL_STAGING_PRELUDE,
    RENDERER_WORKSPACE_LEN_VISIBLE_CELL_STAGING_TAIL_WINDOW,
    RENDERER_WORKSPACE_OFF_CELL_BLIT_WORK_BUFFER,
    RENDERER_WORKSPACE_OFF_LINEAR_VIEWPORT_WORK_BUFFER,
    RENDERER_WORKSPACE_OFF_RENDER_WORK_AREA_TAIL,
    RENDERER_WORKSPACE_OFF_VISIBLE_CELL_STAGING_LATTICE,
    RENDERER_WORKSPACE_OFF_VISIBLE_CELL_STAGING_MID_WINDOW,
    RENDERER_WORKSPACE_OFF_VISIBLE_CELL_STAGING_PRELUDE,
    RENDERER_WORKSPACE_OFF_VISIBLE_CELL_STAGING_TAIL_WINDOW,
)
from alien_evolution.alienevolution.logic import (
    _VISIBLE_CELL_STAGING_PRESET_ROW_OFFSETS,
    AlienEvolutionPort,
)
from alien_evolution.zx.pointers import BlockPtr


class RendererWorkspaceRefactorTests(unittest.TestCase):
    def test_renderer_workspace_layout_is_contiguous(self) -> None:
        segments = (
            (
                RENDERER_WORKSPACE_OFF_VISIBLE_CELL_STAGING_PRELUDE,
                RENDERER_WORKSPACE_LEN_VISIBLE_CELL_STAGING_PRELUDE,
            ),
            (
                RENDERER_WORKSPACE_OFF_VISIBLE_CELL_STAGING_LATTICE,
                RENDERER_WORKSPACE_LEN_VISIBLE_CELL_STAGING_LATTICE,
            ),
            (
                RENDERER_WORKSPACE_OFF_VISIBLE_CELL_STAGING_MID_WINDOW,
                RENDERER_WORKSPACE_LEN_VISIBLE_CELL_STAGING_MID_WINDOW,
            ),
            (
                RENDERER_WORKSPACE_OFF_VISIBLE_CELL_STAGING_TAIL_WINDOW,
                RENDERER_WORKSPACE_LEN_VISIBLE_CELL_STAGING_TAIL_WINDOW,
            ),
            (
                RENDERER_WORKSPACE_OFF_RENDER_WORK_AREA_TAIL,
                RENDERER_WORKSPACE_LEN_RENDER_WORK_AREA_TAIL,
            ),
            (
                RENDERER_WORKSPACE_OFF_CELL_BLIT_WORK_BUFFER,
                RENDERER_WORKSPACE_LEN_CELL_BLIT_WORK_BUFFER,
            ),
            (
                RENDERER_WORKSPACE_OFF_LINEAR_VIEWPORT_WORK_BUFFER,
                RENDERER_WORKSPACE_LEN_LINEAR_VIEWPORT_WORK_BUFFER,
            ),
        )
        cursor = 0
        for offset, length in segments:
            self.assertEqual(offset, cursor)
            cursor += length
        self.assertEqual(cursor, RENDERER_WORKSPACE_LEN_TOTAL)

        runtime = AlienEvolutionPort()
        self.assertEqual(len(runtime.var_renderer_workspace), RENDERER_WORKSPACE_LEN_TOTAL)

    def test_renderer_entrypoints_use_unified_workspace(self) -> None:
        runtime = AlienEvolutionPort()

        sp = runtime._linear_viewport_stack_fill_top_ptr()
        self.assertIs(sp.array, runtime.var_renderer_workspace)
        self.assertEqual(
            sp.index,
            RENDERER_WORKSPACE_OFF_LINEAR_VIEWPORT_WORK_BUFFER + 0x0F00,
        )

        row_ptr = runtime._visible_cell_staging_preset_row_ptr(2)
        self.assertIs(row_ptr.array, runtime.var_renderer_workspace)
        self.assertEqual(
            row_ptr.index,
            RENDERER_WORKSPACE_OFF_VISIBLE_CELL_STAGING_LATTICE + _VISIBLE_CELL_STAGING_PRESET_ROW_OFFSETS[2],
        )

    def test_map_normalization_is_applied_only_for_map_buffers(self) -> None:
        runtime = AlienEvolutionPort()

        wrapped = runtime._read_u8_ptr(BlockPtr(runtime.var_level_map_mode_0, -1))
        self.assertEqual(wrapped, runtime.var_level_map_mode_0[-1])

        with self.assertRaises(IndexError):
            runtime._read_u8_ptr(BlockPtr(runtime.var_renderer_workspace, -1))

    def test_transient_queue_insert_normalizes_map_pointer(self) -> None:
        runtime = AlienEvolutionPort()
        queue = runtime.var_transient_queue_a
        for entry in queue.entries:
            entry.state = 0x00
            entry.cell_ptr = None
        queue.free_slots = len(queue.entries) & 0xFF

        runtime._queue_insert_state_with_cell_ptr(
            queue_state=queue,
            A_state=0x80,
            HL_cell=BlockPtr(runtime.var_level_map_mode_0, -1),
        )

        inserted = queue.entries[0]
        self.assertEqual(inserted.state & 0xFF, 0x80)
        self.assertIsNotNone(inserted.cell_ptr)
        assert inserted.cell_ptr is not None
        self.assertIs(inserted.cell_ptr.array, runtime.var_level_map_mode_0)
        self.assertEqual(inserted.cell_ptr.index, len(runtime.var_level_map_mode_0) - 1)


if __name__ == "__main__":
    unittest.main()
