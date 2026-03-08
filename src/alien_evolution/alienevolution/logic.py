from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Callable, Literal, Sequence, cast

from .blocks import (
    AlienEvolutionData,
    DefineKeySlot,
    HudBarCache,
    MapCoords,
    MapRestoreEntry,
    MarkerCounters,
    OverlayTriplet,
    RendererFillCounters,
    RuntimeObjectQueueBuffer,
    RuntimeObjectQueueEntry,
    RENDERER_WORKSPACE_OFF_CELL_BLIT_WORK_BUFFER,
    RENDERER_WORKSPACE_OFF_LINEAR_VIEWPORT_WORK_BUFFER,
    RENDERER_WORKSPACE_OFF_VISIBLE_CELL_STAGING_LATTICE,
    TransientQueueBuffer,
    TransientQueueEntry,
    UIFrameParams,
)
from ..zx.pointers import BlockPtr, StructFieldPtr
from ..zx.inputmap import KEY_CHAR_TO_ZX_KEYBOARD_SCAN, ZX_KEYBOARD_ROW_INDEX_BY_PORT
from ..zx.runtime import (
    FrameInput,
    StepOutput,
    ZXSpectrumServiceLayer,
)
from ..zx.state import (
    compute_schema_hash,
    StatefulManifestRuntime,
)

StreamSlot = Literal["stream_ptr_a", "stream_ptr_b", "stream_ptr_c", "stream_ptr_d"]

_DEFAULT_CUBE_FAST_MASK_PAIRS: tuple[tuple[int, int], ...] = (
    (0xF8, 0x01), (0x1F, 0x80), (0x00, 0x9F), (0x00, 0xF9),
    (0xE0, 0x07), (0x07, 0xE0), (0x00, 0x7F), (0x00, 0xFE),
    (0x80, 0x1F), (0x01, 0xF8), (0x00, 0x7F), (0x00, 0xFF),
    (0x00, 0x7F), (0x00, 0xFE), (0x00, 0x7F), (0x00, 0xFF),
    (0x00, 0xFF), (0x00, 0xFF), (0x00, 0x7E), (0x00, 0x7F),
    (0x00, 0x7F), (0x00, 0xFE), (0x01, 0x78), (0x80, 0x1F),
    (0x00, 0x9F), (0x00, 0xF9), (0x07, 0x60), (0xE0, 0x07),
    (0x00, 0xE7), (0x00, 0xE7), (0x1F, 0x00), (0xF8, 0x01),
)

# Keep Pyxel at 50 FPS, but run gameplay simulation/render cadence slower to
# better match observed original pacing without touching menu/UI frame timing.
GAMEPLAY_FRAME_DIVIDER: int = 5
_AUDIO_TICKS_PER_SECOND: int = 120
_HOST_FRAMES_PER_SECOND: int = 50

# Stream interpreter throughput budget per host frame. This keeps menu/intro
# stream progression close to original pacing without tying gameplay loop speed
# to CPU-cycle emulation.
STREAM_ENGINE_FRAME_BUDGET: int = 69_888

# Level-complete score-roll pacing:
# keep total score animation steps from ZX loop (0x01F4), but distribute them
# over a fixed host-frame window for visible frame-synced roll-up.
LEVEL_COMPLETE_ROLL_TOTAL_STEPS: int = 0x01F4
LEVEL_COMPLETE_ROLL_TARGET_FRAMES: int = 125

FSM_STATE_BOOT_ENTRY = "BOOT_ENTRY"
FSM_STATE_MENU_INIT = "MENU_INIT"
FSM_STATE_MENU_IDLE_POLL_FRAME = "MENU_IDLE_POLL_FRAME"
FSM_STATE_MENU_POST_ACTION_FRAME = "MENU_POST_ACTION_FRAME"
FSM_STATE_DEFINE_KEYS_WAIT_FRAME = "DEFINE_KEYS_WAIT_FRAME"
FSM_STATE_WAIT_KEYBOARD_RELEASE_FRAME = "WAIT_KEYBOARD_RELEASE_FRAME"
FSM_STATE_STREAM_INTERMISSION_FRAME = "STREAM_INTERMISSION_FRAME"
FSM_STATE_GAMEPLAY_SETUP = "GAMEPLAY_SETUP"
FSM_STATE_GAMEPLAY_MAIN_FRAME = "GAMEPLAY_MAIN_FRAME"
FSM_STATE_GAMEPLAY_MAIN_AFTER_DIRECTIONAL = "GAMEPLAY_MAIN_AFTER_DIRECTIONAL"
FSM_STATE_GAMEPLAY_MAIN_AFTER_CALLBACK = "GAMEPLAY_MAIN_AFTER_CALLBACK"
FSM_STATE_GAMEPLAY_MAIN_POST_TICK = "GAMEPLAY_MAIN_POST_TICK"
FSM_STATE_SCHEDULER_AUTONOMOUS_FRAME = "SCHEDULER_AUTONOMOUS_FRAME"
FSM_STATE_GAMEPLAY_BRANCH = "GAMEPLAY_BRANCH"
FSM_STATE_TRANSITION_DISPATCH = "TRANSITION_DISPATCH"
FSM_STATE_LEVEL_ROLL_FRAME = "LEVEL_ROLL_FRAME"
FSM_STATE_FRAME_DELAY_0X50_FRAME = "FRAME_DELAY_0x50_FRAME"
FSM_STATE_FAILURE_TIMER_DRAIN_FRAME = "FAILURE_TIMER_DRAIN_FRAME"
FSM_STATE_HIGHSCORE_WAIT_KEY_FRAME = "HIGHSCORE_WAIT_KEY_FRAME"
FSM_STATE_HIGHSCORE_FILTER_KEY_FRAME = "HIGHSCORE_FILTER_KEY_FRAME"
FSM_STATE_HIGHSCORE_BACKSPACE_FRAME = "HIGHSCORE_BACKSPACE_FRAME"
FSM_STATE_HIGHSCORE_CHAR_FRAME = "HIGHSCORE_CHAR_FRAME"
FSM_STATE_GAMEPLAY_TICK_STAGE_0_FRAME = "GAMEPLAY_TICK_STAGE_0_FRAME"
FSM_STATE_GAMEPLAY_TICK_STAGE_1_FRAME = "GAMEPLAY_TICK_STAGE_1_FRAME"
FSM_STATE_GAMEPLAY_TICK_STAGE_2_FRAME = "GAMEPLAY_TICK_STAGE_2_FRAME"
FSM_STATE_GAMEPLAY_TICK_STAGE_3_FRAME = "GAMEPLAY_TICK_STAGE_3_FRAME"
FSM_STATE_OVERLAY_PRE_FILL_FRAME = "OVERLAY_PRE_FILL_FRAME"
FSM_STATE_OVERLAY_POST_FILL_FRAME = "OVERLAY_POST_FILL_FRAME"
FSM_STATE_CALLBACK_TIMING_FRAME = "CALLBACK_TIMING_FRAME"
FSM_STATE_CALLBACK_HALT_65_FRAME = "CALLBACK_HALT_65_FRAME"
FSM_STATE_RUNTIME_FALLBACK_IDLE_FRAME = "RUNTIME_FALLBACK_IDLE_FRAME"


def _build_rowbit_key_scan_order() -> tuple[tuple[int, int, str], ...]:
    seen: set[tuple[int, int]] = set()
    ordered: list[tuple[int, int, str]] = []
    for key_char, (port_word, bit_index) in KEY_CHAR_TO_ZX_KEYBOARD_SCAN.items():
        row_index = ZX_KEYBOARD_ROW_INDEX_BY_PORT.get(port_word)
        if row_index is None:
            continue
        token = (row_index, bit_index)
        if token in seen:
            continue
        seen.add(token)
        ordered.append((row_index, bit_index, key_char))
    return tuple(ordered)


_ROWBIT_KEY_SCAN_ORDER: tuple[tuple[int, int, str], ...] = _build_rowbit_key_scan_order()
_VISIBLE_CELL_STAGING_PRESET_ROW_OFFSETS: tuple[int, ...] = (
    0x0181,
    0x0192,
    0x01A2,
    0x01B3,
    0x01C3,
)


class ForcedInterpreterAbort(Exception):
    """Non-local unwind used by forced_interpreter_abort_path (0xFC0B)."""


@dataclass
class RenderStripState:
    hl_stage: BlockPtr
    de_dst: BlockPtr
    c_lane: int
    b_rows: int
    row_base: BlockPtr
    alt_phase: int


ObjectCallback = Callable[[int, BlockPtr], int | tuple[int, BlockPtr]]

_STATE_DATACLASS_TYPES: dict[str, type] = {
    DefineKeySlot.__name__: DefineKeySlot,
    FrameInput.__name__: FrameInput,
    HudBarCache.__name__: HudBarCache,
    MapCoords.__name__: MapCoords,
    MapRestoreEntry.__name__: MapRestoreEntry,
    MarkerCounters.__name__: MarkerCounters,
    OverlayTriplet.__name__: OverlayTriplet,
    RendererFillCounters.__name__: RendererFillCounters,
    RuntimeObjectQueueBuffer.__name__: RuntimeObjectQueueBuffer,
    RuntimeObjectQueueEntry.__name__: RuntimeObjectQueueEntry,
    TransientQueueBuffer.__name__: TransientQueueBuffer,
    TransientQueueEntry.__name__: TransientQueueEntry,
    UIFrameParams.__name__: UIFrameParams,
}


class AlienEvolutionPort(StatefulManifestRuntime, AlienEvolutionData, ZXSpectrumServiceLayer):
    """Runtime scaffold with routine stubs auto-seeded from Skool annotations."""

    STATE_SCHEMA_VERSION: int = 4
    _STATE_CODEC_VERSION: int = 1
    STATE_RUNTIME_ID_ALIASES: tuple[str, ...] = (
        "alien_evolution.logic.AlienEvolutionPort",
    )
    _STATE_DATACLASS_TYPES = _STATE_DATACLASS_TYPES

    _STATE_DYNAMIC_VALUE_FIELDS: tuple[str, ...] = (
        "_cube_fast_mask_pairs",
        "_fsm_callback_ctx",
        "_fsm_define_keys_ctx",
        "_fsm_frame_delay_ctx",
        "_fsm_gameplay_ctx",
        "_fsm_highscore_ctx",
        "_fsm_level_roll_ctx",
        "_fsm_menu_ctx",
        "_fsm_overlay_ctx",
        "_fsm_state",
        "_fsm_stream_ctx",
        "_fsm_tick_ctx",
        "_fsm_transition_kind",
        "_interrupts_enabled",
        "_level_complete_roll_audio_frame_sync",
        "_rom_last_key_scan",
        "_stream_lane_ticks",
        "_stream_slot_tick_remainder",
        "_z80_r_register",
        "border_color",
        "const_define_keys_descriptor_table",
        "const_overlay_template_payload",
        "const_periodic_scheduler_script",
        "const_sprite_subset_bank_a",
        "const_sprite_subset_bank_b",
        "flash_phase",
        "frame_counter",
        "patch_callback_hook_opcode",
        "patch_control_scan_slot_1_bit_opcode",
        "patch_control_scan_slot_1_branch_opcode",
        "patch_control_scan_slot_1_port_word",
        "patch_control_scan_slot_2_bit_opcode",
        "patch_control_scan_slot_2_branch_opcode",
        "patch_control_scan_slot_2_port_word",
        "patch_control_scan_slot_3_bit_opcode",
        "patch_control_scan_slot_3_branch_opcode",
        "patch_control_scan_slot_3_port_word",
        "patch_control_scan_slot_4_bit_opcode",
        "patch_control_scan_slot_4_branch_opcode",
        "patch_control_scan_slot_4_port_word",
        "patch_control_scan_slot_5_action_opcode",
        "patch_control_scan_slot_5_bit_opcode",
        "patch_control_scan_slot_5_port_word",
        "patch_control_scan_slot_6_bit_opcode",
        "patch_control_scan_slot_6_branch_opcode",
        "patch_control_scan_slot_6_port_word",
        "patch_control_scan_slot_6_prefix_opcode",
        "patch_directional_action_mark_code",
        "patch_gameplay_movement_step_opcode",
        "patch_queue_1_block_threshold_code",
        "patch_queue_2_block_threshold_code",
        "patch_queue_3_block_threshold_code",
        "patch_queue_3_contact_branch_opcode",
        "patch_queue_3_fallback_threshold_code",
        "patch_queue_c_mark_code",
        "patch_queue_c_root_eq_code",
        "patch_queue_c_root_low_code_limit",
        "patch_queue_c_scan_branch_opcode",
        "patch_queue_c_scan_low_code_limit",
        "patch_queue_c_scan_mid_code_limit",
        "patch_scheduler_script_base_ptr",
        "patch_scrub_scanner_call_condition_opcode",
        "patch_scrub_scanner_write_value",
        "patch_viewport_fill_word_1",
        "patch_viewport_fill_word_2",
        "patch_viewport_fill_word_3",
        "patch_viewport_fill_word_4",
        "patch_viewport_fill_word_5",
        "patch_viewport_fill_word_6",
        "patch_viewport_fill_word_7",
        "patch_viewport_fill_word_8",
        "str_highscore_row_template_1",
        "str_highscore_row_template_2",
        "str_highscore_row_template_3",
        "str_highscore_row_template_4",
        "str_highscore_row_template_5",
        "var_action_effect_flags",
        "var_active_map_mode",
        "var_active_sprite_subset_bank",
        "var_aux_padding_bytes",
        "var_current_map_coords",
        "var_display_attribute_ram",
        "var_display_bitmap_copy_tail_anchor_4001",
        "var_display_bitmap_lower_clear_base_4800",
        "var_display_bitmap_lower_clear_tail_4801",
        "var_display_bitmap_mission_panel_dst_5000",
        "var_display_bitmap_ram",
        "var_display_bitmap_strip_dst_anchor_4021",
        "var_glyph_scratch_template",
        "var_glyph_scratch_template_row_1",
        "var_glyph_scratch_template_row_2",
        "var_highscore_edit_row_index",
        "var_highscore_name_edit_state",
        "var_highscore_row_score_offsets",
        "var_hud_bar_cache",
        "var_level_map_mode_0",
        "var_level_map_mode_1",
        "var_level_map_mode_2",
        "var_marker_counters",
        "var_marker_index_state",
        "var_menu_selection_index",
        "var_move_marker_code_scratch",
        "var_movement_hud_shared_state",
        "var_queue_source_ptr_scratch",
        "var_queue_state_scratch",
        "var_queue_write_ptr_scratch",
        "var_render_stack_saved_sp",
        "var_renderer_fill_counters",
        "var_renderer_workspace",
        "var_rom_border_shadow_byte",
        "var_runtime_aux_c8_hi",
        "var_runtime_aux_c8_lo",
        "var_runtime_aux_ca",
        "var_runtime_aux_cb",
        "var_runtime_aux_cc",
        "var_runtime_control_core",
        "var_runtime_control_prelude",
        "var_runtime_direction_mask",
        "var_runtime_move_delta",
        "var_runtime_move_state_code",
        "var_runtime_object_queue_0",
        "var_runtime_object_queue_1",
        "var_runtime_object_queue_2",
        "var_runtime_object_queue_3",
        "var_runtime_object_queue_4",
        "var_runtime_objective_counter",
        "var_runtime_phase_index",
        "var_runtime_progress_byte_0",
        "var_runtime_progress_byte_1",
        "var_runtime_progress_byte_2",
        "var_runtime_progress_counter",
        "var_runtime_reserve_tail",
        "var_runtime_scheduler_timer",
        "var_runtime_sprite_tail",
        "var_runtime_ui_frame_params",
        "var_saved_map_triplet_buffer",
        "var_stream_cmd_byte_0",
        "var_stream_cmd_byte_1",
        "var_stream_cmd_byte_2",
        "var_stream_timing_control_byte",
        "var_stream_walk_ptr_scratch",
        "var_strip_fill_value",
        "var_transient_effect_state",
        "var_transient_queue_a",
        "var_transient_queue_b",
        "var_transient_queue_c",
        "var_visible_cell_staging_prelude",
        "var_zx_system_workspace_ram",
    )
    _STATE_DYNAMIC_BLOCK_PTR_FIELDS: tuple[str, ...] = (
        "_stream_ptr_a",
        "_stream_ptr_b",
        "_stream_ptr_c",
        "_stream_ptr_d",
        "patch_highscore_header_tail_ptr",
        "patch_marker_seed_map_base_ptr",
        "patch_stream_player_default_stream_a_ptr",
        "patch_stream_player_default_stream_b_ptr",
        "var_active_map_base_ptr",
        "var_marker_event_cell_ptr",
        "var_renderer_staging_cursor_ptr",
        "var_runtime_current_cell_ptr",
        "var_runtime_dir_ptr_up_cell",
        "var_runtime_dir_ptr_down_cell",
        "var_runtime_dir_ptr_right_cell",
        "var_runtime_dir_ptr_left_cell",
        "var_transient_effect_ptr",
    )
    _STATE_DYNAMIC_STRUCT_PTR_FIELDS: tuple[str, ...] = ()
    _STATE_RUNTIME_QUEUE_TARGET_FIELDS: tuple[str, ...] = (
        "var_runtime_object_queue_0",
        "var_runtime_object_queue_1",
        "var_runtime_object_queue_2",
        "var_runtime_object_queue_3",
        "var_runtime_object_queue_4",
    )
    _STATE_DYNAMIC_OBJECT_REF_FIELDS: dict[str, tuple[str, ...]] = {
        "var_runtime_queue_head_0": _STATE_RUNTIME_QUEUE_TARGET_FIELDS,
        "var_runtime_queue_head_1": _STATE_RUNTIME_QUEUE_TARGET_FIELDS,
        "var_runtime_queue_head_2": _STATE_RUNTIME_QUEUE_TARGET_FIELDS,
        "var_runtime_queue_head_3": _STATE_RUNTIME_QUEUE_TARGET_FIELDS,
        "var_runtime_queue_head_4": _STATE_RUNTIME_QUEUE_TARGET_FIELDS,
    }
    _STATE_REBIND_BLOCK_PTR_FIELDS: tuple[str, ...] = ("_glyph_bias_ptr",)
    _STATE_REBIND_STRUCT_PTR_FIELDS: tuple[str, ...] = (
        "const_define_key_slot_1_mask_byte",
        "const_define_key_slot_1_port_word",
        "const_define_key_slot_2_mask_byte",
        "const_define_key_slot_2_port_word",
        "const_define_key_slot_3_mask_byte",
        "const_define_key_slot_3_port_word",
        "const_define_key_slot_4_mask_byte",
        "const_define_key_slot_4_port_word",
        "const_define_key_slot_5_mask_byte",
        "const_define_key_slot_5_port_word",
        "const_define_key_slot_6_mask_byte",
        "const_define_key_slot_6_port_word",
    )
    _STATE_TRANSIENT_FIELDS: tuple[str, ...] = (
        "_audio_clock",
        "_audio_emit_epoch_id",
        "_audio_events",
        "_audio_epoch_tails",
        "_fsm_step_active",
        "_frame_input",
        "_pending_delay_after_step_frames",
        "patch_object_callback_call_target",
        "patch_transient_queue_handler_call_target",
        "screen_attrs",
        "screen_bitmap",
    )
    _STATE_SCHEMA_MANIFEST: dict[str, object] = {
        "dynamic_values": list(_STATE_DYNAMIC_VALUE_FIELDS),
        "dynamic_block_ptrs": list(_STATE_DYNAMIC_BLOCK_PTR_FIELDS),
        "dynamic_struct_ptrs": list(_STATE_DYNAMIC_STRUCT_PTR_FIELDS),
        "dynamic_object_refs": {
            key: list(value)
            for key, value in _STATE_DYNAMIC_OBJECT_REF_FIELDS.items()
        },
        "rebind_block_ptrs": list(_STATE_REBIND_BLOCK_PTR_FIELDS),
        "rebind_struct_ptrs": list(_STATE_REBIND_STRUCT_PTR_FIELDS),
        "transient_fields": list(_STATE_TRANSIENT_FIELDS),
    }
    _STATE_SCHEMA_HASH: str = compute_schema_hash(
        schema_version=STATE_SCHEMA_VERSION,
        manifest=_STATE_SCHEMA_MANIFEST,
        codec_version=_STATE_CODEC_VERSION,
    )

    def __init__(self) -> None:
        AlienEvolutionData.__init__(self)
        ZXSpectrumServiceLayer.__init__(
            self,
            screen_bitmap=self.var_display_bitmap_ram,
            screen_attrs=self.var_display_attribute_ram,
        )
        self._init_runtime_state_from_loaded_image()

    def _init_runtime_state_from_loaded_image(self) -> None:
        self._cube_fast_mask_pairs = list(_DEFAULT_CUBE_FAST_MASK_PAIRS)
        self.patch_callback_hook_opcode = self.const_patch_seed_callback_hook_opcode & 0xFF
        self.patch_scrub_scanner_call_condition_opcode = (
            self.const_patch_seed_scrub_scanner_call_condition_opcode & 0xFF
        )
        self.patch_scrub_scanner_write_value = self.const_patch_seed_scrub_scanner_write_value & 0xFF
        self.patch_marker_seed_map_base_ptr = BlockPtr(self.var_level_map_mode_0, 0x0000)
        self.patch_highscore_header_tail_ptr = BlockPtr(self.str_byline_stream, 0x0000)
        self.patch_gameplay_movement_step_opcode = self.const_patch_seed_gameplay_movement_step_opcode & 0xFF
        self.patch_scheduler_script_base_ptr = self.const_periodic_scheduler_step_4
        self.patch_directional_action_mark_code = 0x00
        self.patch_queue_1_block_threshold_code = 0x50
        self.patch_queue_2_block_threshold_code = 0x50
        self.patch_queue_3_block_threshold_code = 0x50
        self.patch_queue_3_fallback_threshold_code = 0x50
        self.patch_queue_3_contact_branch_opcode = 0xC5
        self.patch_queue_c_mark_code = 0x33
        self.patch_queue_c_root_eq_code = 0x33
        self.patch_queue_c_root_low_code_limit = 0x0D
        self.patch_queue_c_scan_branch_opcode = 0x38
        self.patch_queue_c_scan_low_code_limit = 0x0D
        self.patch_queue_c_scan_mid_code_limit = 0x17
        self.patch_viewport_fill_word_1 = 0x0660
        self.patch_viewport_fill_word_2 = 0x1818
        self.patch_viewport_fill_word_3 = 0x6006
        self.patch_viewport_fill_word_4 = 0x8001
        self.patch_viewport_fill_word_5 = 0x6006
        self.patch_viewport_fill_word_6 = 0x1818
        self.patch_viewport_fill_word_7 = 0x0660
        self.patch_viewport_fill_word_8 = 0x0180
        self.patch_stream_player_default_stream_a_ptr = BlockPtr(
            self.const_scenario_preset_c_stream_1,
            0x0000,
        )
        self.patch_stream_player_default_stream_b_ptr = BlockPtr(
            self.const_scenario_preset_c_stream_1,
            0x0004,
        )
        # Default modern keyboard profile: W/A/S/D + Space + E.
        self.patch_control_scan_slot_1_port_word = 0xFBFE
        self.patch_control_scan_slot_1_bit_opcode = 0x4F
        self.patch_control_scan_slot_1_branch_opcode = 0xCA
        self.patch_control_scan_slot_2_port_word = 0xFDFE
        self.patch_control_scan_slot_2_bit_opcode = 0x4F
        self.patch_control_scan_slot_2_branch_opcode = 0xCA
        self.patch_control_scan_slot_3_port_word = 0xFDFE
        self.patch_control_scan_slot_3_bit_opcode = 0x47
        self.patch_control_scan_slot_3_branch_opcode = 0xCA
        self.patch_control_scan_slot_4_port_word = 0xFDFE
        self.patch_control_scan_slot_4_bit_opcode = 0x57
        self.patch_control_scan_slot_4_branch_opcode = 0xCA
        self.patch_control_scan_slot_5_port_word = 0x7FFE
        self.patch_control_scan_slot_5_bit_opcode = 0x47
        self.patch_control_scan_slot_5_action_opcode = 0xCC
        self.patch_control_scan_slot_6_port_word = 0xFBFE
        self.patch_control_scan_slot_6_prefix_opcode = 0xCB
        self.patch_control_scan_slot_6_bit_opcode = 0x57
        self.patch_control_scan_slot_6_branch_opcode = 0xCA
        self._glyph_bias_ptr = BlockPtr(self.const_text_glyph_source_head, -0x0002)
        self._stream_ptr_a = BlockPtr(self.const_scenario_preset_b_stream_1, 0x0000)
        self._stream_ptr_b = self._stream_ptr_a.add(0x0001)
        self._stream_ptr_c = BlockPtr(self.const_scenario_preset_b_stream_2, 0x0000)
        self._stream_ptr_d = self._stream_ptr_c.add(0x0001)
        self._z80_r_register = 0x00
        self._interrupts_enabled = True
        self._fsm_state = FSM_STATE_BOOT_ENTRY
        self._fsm_transition_kind: str = "none"
        self._fsm_define_keys_ctx: dict[str, object] = {}
        self._fsm_stream_ctx: dict[str, object] = {}
        self._fsm_menu_ctx: dict[str, object] = {"prepared": False}
        self._fsm_gameplay_ctx: dict[str, object] = {
            "initialized": False,
            "screen_setup_required": True,
        }
        self._fsm_level_roll_ctx: dict[str, object] = {}
        self._fsm_highscore_ctx: dict[str, object] = {}
        self._fsm_tick_ctx: dict[str, object] = {
            "pending_autonomous": False,
            "pending_marker": False,
        }
        self._fsm_overlay_ctx: dict[str, object] = {}
        self._fsm_callback_ctx: dict[str, object] = {}
        self._fsm_frame_delay_ctx: dict[str, object] = {}
        self._fsm_step_active = False
        self._rom_last_key_scan: tuple[int, int] | None = None
        self._level_complete_roll_audio_frame_sync = False
        self._frame_rom_beeper_cursors: dict[int, int] = {}
        self._stream_lane_ticks = [0, 0, 0]
        self._stream_slot_tick_remainder = 0.0

    def reset(self) -> None:
        # Rebuild full runtime state from a fresh baseline instance.
        baseline = type(self)()
        for attr_name in tuple(self.__dict__.keys()):
            if attr_name not in baseline.__dict__:
                del self.__dict__[attr_name]
        self.__dict__.update(baseline.__dict__)

    def apply_cheat_sequence(self, symbols: Sequence[str]) -> bool:
        command = "".join(str(symbol) for symbol in symbols).lower()
        level_index = {"lvl1": 0, "lvl2": 1, "lvl3": 2}.get(command)
        if level_index is None:
            return False
        self._cheat_start_level(level_index)
        return True

    def _cheat_start_level(self, level_index: int) -> None:
        idx = int(level_index)
        if idx < 0 or idx > 2:
            raise ValueError(f"Unsupported cheat level index: {level_index!r}")

        self.reset()
        self.gameplay_screen_setup()
        if idx == 0:
            self.fn_overlay_preset_selector()
        self.var_active_map_mode = idx & 0xFF
        self._fsm_prepare_gameplay_loop()
        self.var_runtime_objective_counter = 0x06
        self.fn_hud_strip_painter()
        self._fsm_gameplay_ctx["initialized"] = True
        self._fsm_gameplay_ctx["screen_setup_required"] = False
        self._fsm_start_stream(
            stream_a=BlockPtr(self.const_scenario_preset_a_stream_1, 0x0000),
            stream_b=BlockPtr(self.const_scenario_preset_a_stream_2, 0x0000),
            abort_on_keypress=True,
            return_state=FSM_STATE_GAMEPLAY_MAIN_FRAME,
        )
        self._fsm_state = FSM_STATE_STREAM_INTERMISSION_FRAME

    def _state_reset_transient_runtime_state(self) -> None:
        self._audio_events.clear()
        self._pending_delay_after_step_frames = 0
        self._fsm_step_active = False
        self.sample_inputs(joy_kempston=0, keyboard_rows=(0xFF,) * 8)

    def step(self, frame_input: FrameInput) -> StepOutput:
        self.begin_frame(frame_input)
        self._frame_rom_beeper_cursors = {
            int(self._audio_emit_epoch_id): self._audio_safe_start_tick_for_epoch(),
        }
        self._fsm_step_active = True
        try:
            for _ in range(4096):
                next_state, host_frames = self._fsm_dispatch_state()
                self._fsm_state = next_state
                if host_frames is None:
                    continue
                total_host_frames = max(1, int(host_frames))
                self._set_step_delay_after_frames(total_host_frames - 1)
                break
            else:
                raise RuntimeError("FSM dispatch exceeded safety iteration budget")
        finally:
            self._fsm_step_active = False
        return self.end_frame()

    # Backward-compatible shim for older wrappers.
    def tick(self, joy: int) -> StepOutput:
        return self.step(FrameInput(joy_kempston=joy))

    def _is_level_map_buffer(self, array: bytes | bytearray) -> bool:
        return (
            array is self.var_level_map_mode_0
            or array is self.var_level_map_mode_1
            or array is self.var_level_map_mode_2
        )

    @staticmethod
    def _wrap_level_index_periodic(index: int) -> int:
        # 50x50 toroidal addressing for map indices.
        row_size = 0x32
        # Use floor-based decomposition so negative indices keep row/col semantics:
        # e.g. idx=-49 corresponds to row=-1,col=1 -> wraps to row=49,col=1.
        row, col = divmod(int(index), row_size)
        row %= row_size
        return (row * row_size + col) & 0xFFFF

    def _normalize_map_ptr(self, ptr: BlockPtr) -> BlockPtr:
        if self._is_level_map_buffer(ptr.array):
            return BlockPtr(ptr.array, self._wrap_level_index_periodic(ptr.index))
        return ptr

    def _read_bytes(self, src: BlockPtr, size: int) -> bytes:
        src = self._normalize_map_ptr(src)
        array, index = src.array, src.index
        size_int = int(size)
        if index < 0:
            raise IndexError(index)
        if size_int > 0:
            # Force IndexError for out-of-range slices (including bytearray writes).
            _ = array[index + size_int - 1]
        return bytes(array[index : index + size_int])

    def _read_u8_ptr(self, ptr: BlockPtr) -> int:
        ptr = self._normalize_map_ptr(ptr)
        if ptr.index < 0:
            raise IndexError(ptr.index)
        return ptr.array[ptr.index]

    def _read_u16_ptr(self, ptr: BlockPtr) -> int:
        lo = self._read_u8_ptr(ptr)
        hi = self._read_u8_ptr(ptr.add(0x0001))
        return lo | (hi << 8)

    def _write_u16_ptr(self, ptr: BlockPtr, value: int) -> None:
        v = value & 0xFFFF
        self._write_u8_ptr(ptr, v & 0xFF)
        self._write_u8_ptr(ptr.add(0x0001), (v >> 8) & 0xFF)

    def _write_u8_ptr(self, ptr: BlockPtr, value: int) -> None:
        ptr = self._normalize_map_ptr(ptr)
        if ptr.index < 0:
            raise IndexError(ptr.index)
        cast(bytearray, ptr.array)[ptr.index] = value & 0xFF

    def _as_u8(self, value_or_ptr: int | BlockPtr) -> int:
        if isinstance(value_or_ptr, BlockPtr):
            return self._read_u8_ptr(value_or_ptr) & 0xFF
        if isinstance(value_or_ptr, int):
            return value_or_ptr & 0xFF
        raise TypeError(f"Expected int or BlockPtr, got {type(value_or_ptr)!r}")

    @staticmethod
    def _u16_to_signed(value: int) -> int:
        v = int(value) & 0xFFFF
        return v - 0x10000 if (v & 0x8000) else v

    def _write_bytes_ptr(self, dst: BlockPtr, data: bytes | bytearray) -> None:
        dst = self._normalize_map_ptr(dst)
        array, index = dst.array, dst.index
        payload = bytes(data)
        if index < 0:
            raise IndexError(index)
        if payload:
            # Force IndexError for out-of-range slices (including bytearray writes).
            _ = array[index + len(payload) - 1]
        cast(bytearray, array)[index : index + len(payload)] = payload

    def _fill_bytes_ptr(self, dst: BlockPtr, size: int, value: int) -> None:
        dst = self._normalize_map_ptr(dst)
        array, index = dst.array, dst.index
        size_int = int(size)
        if index < 0:
            raise IndexError(index)
        if size_int > 0:
            # Force IndexError for out-of-range slices (including bytearray writes).
            _ = array[index + size_int - 1]
        cast(bytearray, array)[index : index + size_int] = bytes([value & 0xFF]) * size_int

    def _ptr_add(self, ptr: BlockPtr, delta: int) -> BlockPtr:
        return ptr.add(int(delta))

    def _display_attr_ptr(self, abs_addr: int) -> BlockPtr:
        index = int(abs_addr) - 0x5800
        if index < 0 or index >= len(self.var_display_attribute_ram):
            raise ValueError(f"Display attribute address out of range: 0x{int(abs_addr) & 0xFFFF:04X}")
        return BlockPtr(self.var_display_attribute_ram, index)

    def _active_sprite_patch_source_ptr(self) -> BlockPtr:
        return BlockPtr(self.var_active_sprite_subset_bank, 0x0580)

    def _linear_viewport_stack_fill_top_ptr(self) -> BlockPtr:
        return BlockPtr(
            self.var_renderer_workspace,
            RENDERER_WORKSPACE_OFF_LINEAR_VIEWPORT_WORK_BUFFER + 0x0F00,
        )

    def _visible_cell_staging_preset_row_ptr(self, row_index: int) -> BlockPtr:
        idx = int(row_index)
        if idx < 0 or idx >= len(_VISIBLE_CELL_STAGING_PRESET_ROW_OFFSETS):
            raise ValueError(f"Preset row index out of range: {idx}")
        return BlockPtr(
            self.var_renderer_workspace,
            RENDERER_WORKSPACE_OFF_VISIBLE_CELL_STAGING_LATTICE + _VISIBLE_CELL_STAGING_PRESET_ROW_OFFSETS[idx],
        )

    def _highscore_row_ptr(self, row_index: int) -> BlockPtr:
        idx = int(row_index)
        if idx < 0 or idx >= len(self.var_highscore_row_templates):
            raise ValueError(f"High-score row index out of range: {idx}")
        return BlockPtr(self.var_highscore_row_templates[idx], 0x0000)

    def _highscore_row_score_ptr(self, row_index: int) -> BlockPtr:
        idx = int(row_index)
        if idx < 0 or idx >= len(self.var_highscore_row_score_offsets):
            raise ValueError(f"High-score score-field index out of range: {idx}")
        return self._highscore_row_ptr(idx).add(self.var_highscore_row_score_offsets[idx])

    def _resolve_object_callback(self, callback: ObjectCallback) -> ObjectCallback:
        if not callable(callback):
            raise TypeError(f"Expected callable object callback, got {type(callback)!r}")
        return callback

    def _resolve_object_queue_cursor(
        self,
        HL_queue: RuntimeObjectQueueBuffer,
    ) -> RuntimeObjectQueueBuffer:
        return HL_queue

    def _set_level_completion_gate(self, *, armed: bool) -> None:
        if armed:
            self.var_runtime_progress_byte_0 = 0x01
            self.var_runtime_progress_byte_1 = 0x00
            self.var_runtime_progress_byte_2 = 0x00
            return
        self.var_runtime_progress_byte_0 = 0x00
        self.var_runtime_progress_byte_1 = 0x00
        self.var_runtime_progress_byte_2 = 0x00

    def _rom_beeper(self, de_ticks: int, hl_period: int, *, start_tick: int | None = None) -> int:
        # Game-level approximation of ROM 0x03B5 call used by this code path.
        period = hl_period & 0xFFFF
        ticks = de_ticks & 0xFFFF
        emit_epoch = int(self._audio_emit_epoch_id)
        duration_ticks = self._rom_beeper_duration_ticks(de_ticks=ticks, hl_period=period)
        if start_tick is None:
            frame_cursor = self._frame_rom_beeper_cursors.get(emit_epoch)
            safe_start_tick = self._audio_safe_start_tick_for_epoch(emit_epoch)
            if frame_cursor is None:
                start_tick = safe_start_tick
            else:
                start_tick = max(int(frame_cursor), safe_start_tick)
        else:
            start_tick = max(0, int(start_tick))
        self.emit_rom_beeper(
            period=period,
            ticks=ticks,
            waveform="S",
            source="rom_beeper",
            start_tick=start_tick,
        )
        self._frame_rom_beeper_cursors[emit_epoch] = max(
            int(self._frame_rom_beeper_cursors.get(emit_epoch, 0)),
            int(start_tick + duration_ticks),
        )
        per_wave_clock_units = 8.0 * (float(period if period > 0 else 1) + 30.125)
        timing_cost = int(round(float(ticks if ticks > 0 else 1) * per_wave_clock_units))
        # Timing is consumed by outer control loops (gameplay/menu/intermission),
        # not by beeper itself.
        return timing_cost

    def _rom_beeper_duration_ticks(self, de_ticks: int, hl_period: int) -> int:
        return self.rom_beeper_duration_ticks(period=(hl_period & 0xFFFF), ticks=(de_ticks & 0xFFFF))

    def _rom_beeper_sequence(
        self,
        packets: Sequence[tuple[int, int]],
        *,
        start_tick: int | None = None,
    ) -> int:
        cursor_tick = self._audio_safe_start_tick_for_epoch() if start_tick is None else max(0, int(start_tick))
        total_timing_cost = 0
        for de_ticks, hl_period in packets:
            total_timing_cost += self._rom_beeper(
                de_ticks=de_ticks,
                hl_period=hl_period,
                start_tick=cursor_tick,
            )
            cursor_tick += self._rom_beeper_duration_ticks(de_ticks=de_ticks, hl_period=hl_period)
        return total_timing_cost

    @staticmethod
    def _audio_ticks_for_host_frames(host_frames: int) -> int:
        frames = max(0, int(host_frames))
        return (frames * _AUDIO_TICKS_PER_SECOND + (_HOST_FRAMES_PER_SECOND // 2)) // _HOST_FRAMES_PER_SECOND

    def _queue_teleport_audio_frame_burst(self, *, de_ticks: int, hl_period: int) -> None:
        start_tick = self._audio_safe_start_tick_for_epoch()
        frame_count = max(1, int(GAMEPLAY_FRAME_DIVIDER))
        period = hl_period & 0xFFFF
        ticks = de_ticks & 0xFFFF
        for host_frame_idx in range(frame_count):
            self.emit_rom_beeper(
                period=period,
                ticks=ticks,
                waveform="S",
                effect="N",
                priority=35,
                start_tick=start_tick + self._audio_ticks_for_host_frames(host_frame_idx),
            )

    @staticmethod
    def _rla(a: int, carry_in: int) -> tuple[int, int]:
        a &= 0xFF
        carry = 1 if (a & 0x80) else 0
        a = ((a << 1) & 0xFF) | (carry_in & 0x01)
        return a, carry

    @staticmethod
    def _rr(v: int, carry_in: int) -> tuple[int, int]:
        v &= 0xFF
        carry_out = v & 0x01
        v = ((v >> 1) | ((carry_in & 0x01) << 7)) & 0xFF
        return v, carry_out

    def _next_r_register(self) -> int:
        # Approximate Z80 R register progression used as entropy source.
        self._z80_r_register = (self._z80_r_register + 0x11) & 0xFF
        return self._z80_r_register

    def _yield_host_frames(self, total_frames: int) -> None:
        host_frames = max(1, int(total_frames))
        if not self._fsm_step_active:
            # Compatibility mode for direct routine calls in tests.
            for _ in range(host_frames):
                self.advance_host_frame()
            return
        raise RuntimeError(
            f"Legacy yield helper called during active FSM step: total_frames={host_frames}",
        )

    def _yield_frame(self) -> None:
        self._yield_host_frames(1)

    def _yield_gameplay_frame(self) -> None:
        divider = max(1, int(GAMEPLAY_FRAME_DIVIDER))
        self._yield_host_frames(divider)

    def _fsm_dispatch_state(self) -> tuple[str, int | None]:
        state = str(self._fsm_state)
        if state == FSM_STATE_BOOT_ENTRY:
            return self._fsm_state_boot_entry()
        if state == FSM_STATE_MENU_INIT:
            return self._fsm_state_menu_init()
        if state == FSM_STATE_STREAM_INTERMISSION_FRAME:
            return self._fsm_state_stream_intermission_frame()
        if state == FSM_STATE_MENU_IDLE_POLL_FRAME:
            return self._fsm_state_menu_idle_poll_frame()
        if state == FSM_STATE_MENU_POST_ACTION_FRAME:
            return self._fsm_state_menu_post_action_frame()
        if state == FSM_STATE_WAIT_KEYBOARD_RELEASE_FRAME:
            return self._fsm_state_wait_keyboard_release_frame()
        if state == FSM_STATE_DEFINE_KEYS_WAIT_FRAME:
            return self._fsm_state_define_keys_wait_frame()
        if state == FSM_STATE_GAMEPLAY_SETUP:
            return self._fsm_state_gameplay_setup()
        if state == FSM_STATE_GAMEPLAY_MAIN_FRAME:
            return self._fsm_state_gameplay_main_frame()
        if state == FSM_STATE_GAMEPLAY_MAIN_AFTER_DIRECTIONAL:
            return self._fsm_state_gameplay_main_after_directional()
        if state == FSM_STATE_GAMEPLAY_MAIN_AFTER_CALLBACK:
            return self._fsm_state_gameplay_main_after_callback()
        if state == FSM_STATE_SCHEDULER_AUTONOMOUS_FRAME:
            return self._fsm_state_scheduler_autonomous_frame()
        if state == FSM_STATE_GAMEPLAY_MAIN_POST_TICK:
            return self._fsm_state_gameplay_main_post_tick()
        if state == FSM_STATE_GAMEPLAY_BRANCH:
            return self._fsm_state_gameplay_branch()
        if state == FSM_STATE_TRANSITION_DISPATCH:
            return self._fsm_state_transition_dispatch()
        if state == FSM_STATE_LEVEL_ROLL_FRAME:
            return self._fsm_state_level_roll_frame()
        if state == FSM_STATE_FRAME_DELAY_0X50_FRAME:
            return self._fsm_state_frame_delay_0x50_frame()
        if state == FSM_STATE_FAILURE_TIMER_DRAIN_FRAME:
            return self._fsm_state_failure_timer_drain_frame()
        if state == FSM_STATE_HIGHSCORE_WAIT_KEY_FRAME:
            return self._fsm_state_highscore_wait_key_frame()
        if state == FSM_STATE_HIGHSCORE_FILTER_KEY_FRAME:
            return self._fsm_state_highscore_filter_key_frame()
        if state == FSM_STATE_HIGHSCORE_BACKSPACE_FRAME:
            return self._fsm_state_highscore_backspace_frame()
        if state == FSM_STATE_HIGHSCORE_CHAR_FRAME:
            return self._fsm_state_highscore_char_frame()
        if state == FSM_STATE_GAMEPLAY_TICK_STAGE_0_FRAME:
            return self._fsm_state_gameplay_tick_stage_0_frame()
        if state == FSM_STATE_GAMEPLAY_TICK_STAGE_1_FRAME:
            return self._fsm_state_gameplay_tick_stage_1_frame()
        if state == FSM_STATE_GAMEPLAY_TICK_STAGE_2_FRAME:
            return self._fsm_state_gameplay_tick_stage_2_frame()
        if state == FSM_STATE_GAMEPLAY_TICK_STAGE_3_FRAME:
            return self._fsm_state_gameplay_tick_stage_3_frame()
        if state == FSM_STATE_OVERLAY_PRE_FILL_FRAME:
            return self._fsm_state_overlay_pre_fill_frame()
        if state == FSM_STATE_OVERLAY_POST_FILL_FRAME:
            return self._fsm_state_overlay_post_fill_frame()
        if state == FSM_STATE_CALLBACK_TIMING_FRAME:
            return self._fsm_state_callback_timing_frame()
        if state == FSM_STATE_CALLBACK_HALT_65_FRAME:
            return self._fsm_state_callback_halt_65_frame()
        if state == FSM_STATE_RUNTIME_FALLBACK_IDLE_FRAME:
            return self._fsm_state_runtime_fallback_idle_frame()
        raise RuntimeError(f"Unknown FSM state: {state!r}")

    def _fsm_state_boot_entry(self) -> tuple[str, int | None]:
        return FSM_STATE_MENU_INIT, None

    def _reset_stream_audio_timing_state(self) -> None:
        self._ensure_stream_lane_slots()
        self._stream_lane_ticks[0] = 0
        self._stream_lane_ticks[1] = 0
        self._stream_lane_ticks[2] = 0
        self._stream_slot_tick_remainder = 0.0

    def _align_stream_audio_lanes_to_safe_start_tick(self) -> None:
        self._ensure_stream_lane_slots()
        anchor_tick = self._audio_safe_start_tick_for_epoch()
        self._stream_lane_ticks[0] = max(int(self._stream_lane_ticks[0]), anchor_tick)
        self._stream_lane_ticks[1] = max(int(self._stream_lane_ticks[1]), anchor_tick)
        self._stream_lane_ticks[2] = max(int(self._stream_lane_ticks[2]), anchor_tick)

    def _stream_audio_frontier_tick(self) -> int:
        self._ensure_stream_lane_slots()
        return max(int(self._stream_lane_ticks[0]), int(self._stream_lane_ticks[1]), int(self._stream_lane_ticks[2]))

    def _fill_stream_audio_until_target(self) -> None:
        self._align_stream_audio_lanes_to_safe_start_tick()
        target_tick = self._audio_fill_until_tick_for_epoch()
        while self._stream_audio_frontier_tick() < target_tick:
            frontier_before = self._stream_audio_frontier_tick()
            timing_cost = self.core_command_interpreter_scenario_stream_engine()
            frontier_after = self._stream_audio_frontier_tick()
            if frontier_after <= frontier_before and int(timing_cost) <= 0:
                raise RuntimeError("Stream audio fill made no progress")

    def _ensure_stream_lane_slots(self) -> None:
        value = self._stream_lane_ticks
        if not isinstance(value, list):
            self._stream_lane_ticks = [0, 0, 0]
            return
        while len(value) < 3:
            value.append(0)

    def _quantize_stream_slot_ticks(self, duration_s: float) -> int:
        raw_ticks = (float(duration_s) * 120.0) + float(self._stream_slot_tick_remainder)
        rounded = int(math.floor(raw_ticks + 0.5))
        if rounded < 1:
            rounded = 1
            self._stream_slot_tick_remainder = 0.0
            return rounded
        self._stream_slot_tick_remainder = raw_ticks - float(rounded)
        return rounded

    def _queue_mode_audio_reset(self) -> int:
        cut_tick = self.audio_epoch_tail()
        if cut_tick <= 0:
            cut_tick = self._audio_safe_start_tick_for_epoch()
        return self.schedule_reset(cut_tick)

    def _fsm_start_stream(
        self,
        *,
        stream_a: BlockPtr,
        stream_b: BlockPtr,
        abort_on_keypress: bool,
        return_state: str,
    ) -> None:
        self._queue_mode_audio_reset()
        self.patch_stream_player_default_stream_a_ptr = stream_a
        self.patch_stream_player_default_stream_b_ptr = stream_b
        self._stream_ptr_a = stream_a
        self._stream_ptr_b = stream_a.add(0x0001)
        self._stream_ptr_c = stream_b
        self._stream_ptr_d = stream_b.add(0x0001)
        self._reset_stream_audio_timing_state()
        self._fsm_stream_ctx = {
            "abort_on_keypress": bool(abort_on_keypress),
            "return_state": return_state,
        }
        self._interrupts_enabled = False

    def _fsm_finish_stream(self) -> str:
        ctx = self._fsm_stream_ctx
        if not ctx:
            raise RuntimeError("FSM stream finish requires non-empty _fsm_stream_ctx")
        if "return_state" not in ctx:
            raise RuntimeError("FSM stream finish requires return_state in context")
        if not isinstance(ctx["return_state"], str):
            raise RuntimeError("FSM stream finish requires string return_state")
        self.schedule_reset(self._audio_safe_start_tick_for_epoch())
        return_state = ctx["return_state"]
        self._reset_stream_audio_timing_state()
        self._interrupts_enabled = True
        self._fsm_stream_ctx = {}
        return return_state

    def _fsm_state_menu_init(self) -> tuple[str, int | None]:
        # ZX 0x6C82..0x6CD7 + 0xF152..0xF173 (FSM state MENU_INIT)
        self.fn_title_screen_text_compositor()
        self._fsm_menu_ctx["prepared"] = False
        self._fsm_start_stream(
            stream_a=BlockPtr(self.const_scenario_preset_b_stream_1, 0x0000),
            stream_b=BlockPtr(self.const_scenario_preset_b_stream_2, 0x0000),
            abort_on_keypress=True,
            return_state=FSM_STATE_MENU_IDLE_POLL_FRAME,
        )
        return FSM_STATE_STREAM_INTERMISSION_FRAME, None

    def _fsm_state_stream_intermission_frame(self) -> tuple[str, int | None]:
        # ZX 0xFBCC..0xFC6F (FSM state STREAM_INTERMISSION_FRAME)
        ctx = self._fsm_stream_ctx
        if not ctx:
            raise RuntimeError("FSM stream state requires non-empty _fsm_stream_ctx")
        if "return_state" not in ctx:
            raise RuntimeError("FSM stream state requires return_state in context")
        if "abort_on_keypress" not in ctx:
            raise RuntimeError("FSM stream state requires abort_on_keypress in context")
        if not isinstance(ctx["abort_on_keypress"], bool):
            raise RuntimeError("FSM stream state requires bool abort_on_keypress")

        try:
            self._fill_stream_audio_until_target()
        except ForcedInterpreterAbort:
            return self._fsm_finish_stream(), None

        key_code = self._rom_keyboard_input_poll_028e()
        if bool(ctx["abort_on_keypress"]) and ((key_code + 0x01) & 0xFF) != 0x00:
            next_state = self._fsm_finish_stream()
            # Gameplay splash-dismiss key must be consumed by splash itself; do
            # not let held key continue into gameplay movement in the same tick.
            if next_state == FSM_STATE_GAMEPLAY_MAIN_FRAME:
                self._fsm_menu_ctx["wait_release_return_state"] = next_state
                return FSM_STATE_WAIT_KEYBOARD_RELEASE_FRAME, 1
            return next_state, None

        return FSM_STATE_STREAM_INTERMISSION_FRAME, 1

    def _fsm_state_menu_idle_poll_frame(self) -> tuple[str, int | None]:
        # ZX 0x6C82..0x6CD7 (FSM state MENU_IDLE_POLL_FRAME)
        if "prepared" not in self._fsm_menu_ctx:
            raise RuntimeError("FSM menu-idle state requires prepared in _fsm_menu_ctx")
        if not isinstance(self._fsm_menu_ctx["prepared"], bool):
            raise RuntimeError("FSM menu-idle state requires bool prepared in _fsm_menu_ctx")
        prepared = self._fsm_menu_ctx["prepared"]
        if not prepared:
            a_sel = self.var_menu_selection_index & 0xFF
            row_offset = ((a_sel + 0x01) * 0x40) & 0xFFFF
            hl_row = self._ptr_add(self._display_attr_ptr(0x590a), row_offset)
            self._write_u8_ptr(hl_row, 0x06)
            self._write_u8_ptr(self._ptr_add(hl_row, 0x20), 0x06)
            self._fill_bytes_ptr(self._ptr_add(hl_row, 0x22), 0x11, 0x06)
            self.fn_front_end_two_step_beeper_cadence()
            self._fsm_menu_ctx["prepared"] = True

        a_keys = self.in_port(0xF7FE) & 0xFF
        if (a_keys & 0x01) == 0x00:
            self.define_keys_apply_routine()
            self._fsm_menu_ctx["prepared"] = False
            return FSM_STATE_MENU_POST_ACTION_FRAME, 1
        if (a_keys & 0x02) == 0x00:
            self.control_preset_branch_3()
            self._fsm_menu_ctx["prepared"] = False
            return FSM_STATE_MENU_POST_ACTION_FRAME, 1
        if (a_keys & 0x04) == 0x00:
            self.control_preset_branch()
            self._fsm_menu_ctx["prepared"] = False
            return FSM_STATE_MENU_POST_ACTION_FRAME, 1
        if (a_keys & 0x08) == 0x00:
            self.control_preset_branch_2()
            self._fsm_menu_ctx["prepared"] = False
            return FSM_STATE_MENU_POST_ACTION_FRAME, 1
        if (a_keys & 0x10) == 0x00:
            self.fn_title_top_screen_setup()
            self.fn_blink_delay_two_phase_wait()
            self._fsm_define_keys_ctx = {
                "phase": "wait_release_before_slot",
                "slot_index": 0,
            }
            self._fsm_menu_ctx["prepared"] = False
            return FSM_STATE_DEFINE_KEYS_WAIT_FRAME, None

        a_start = self.in_port(0xEFFE) & 0xFF
        if (a_start & 0x10) == 0x00:
            # Entering gameplay splash from menu with START held must not
            # immediately count as a "new" splash-exit key event.
            start_scan = KEY_CHAR_TO_ZX_KEYBOARD_SCAN.get("6")
            if start_scan is not None:
                start_row = ZX_KEYBOARD_ROW_INDEX_BY_PORT.get(start_scan[0])
                if start_row is not None:
                    self._rom_last_key_scan = (start_row, start_scan[1])
            self._fsm_gameplay_ctx["initialized"] = False
            self._fsm_gameplay_ctx["screen_setup_required"] = True
            return FSM_STATE_GAMEPLAY_SETUP, None
        return FSM_STATE_MENU_IDLE_POLL_FRAME, 1

    def _fsm_state_menu_post_action_frame(self) -> tuple[str, int | None]:
        self._fsm_menu_ctx["prepared"] = False
        return FSM_STATE_MENU_IDLE_POLL_FRAME, None

    def _fsm_state_wait_keyboard_release_frame(self) -> tuple[str, int | None]:
        if self._keyboard_any_pressed():
            return FSM_STATE_WAIT_KEYBOARD_RELEASE_FRAME, 1
        menu_ctx = self._fsm_menu_ctx
        if "wait_release_return_state" not in menu_ctx:
            raise RuntimeError("FSM wait-keyboard-release state requires wait_release_return_state")
        if not isinstance(menu_ctx["wait_release_return_state"], str):
            raise RuntimeError("FSM wait-keyboard-release state requires string wait_release_return_state")
        next_state = menu_ctx["wait_release_return_state"]
        menu_ctx.pop("wait_release_return_state", None)
        return next_state, None

    @staticmethod
    def _fsm_define_keys_slots() -> tuple[tuple[str, str, str], ...]:
        return (
            ("fn_icon_selector_2", "const_define_key_slot_1_port_word", "const_define_key_slot_1_mask_byte"),
            ("fn_icon_selector_1", "const_define_key_slot_2_port_word", "const_define_key_slot_2_mask_byte"),
            ("fn_icon_selector_3", "const_define_key_slot_3_port_word", "const_define_key_slot_3_mask_byte"),
            ("fn_icon_selector_4", "const_define_key_slot_4_port_word", "const_define_key_slot_4_mask_byte"),
            ("fn_icon_selector_5", "const_define_key_slot_5_port_word", "const_define_key_slot_5_mask_byte"),
            ("fn_icon_selector_6", "const_define_key_slot_6_port_word", "const_define_key_slot_6_mask_byte"),
        )

    def _fsm_probe_define_key(self) -> tuple[int, int] | None:
        probe_ports = (0xFEFE, 0xFDFE, 0xFBFE, 0xF7FE, 0xEFFE, 0xDFFE, 0xBFFE, 0x7FFE)
        for bc_port in probe_ports:
            a_row = self.fn_input_probe_primitive(BC_port=bc_port)
            if a_row != 0xFF:
                a_glyph = self.pressed_key_decoder(A_row=a_row)
                return a_glyph, bc_port
        return None

    def _fsm_state_define_keys_wait_frame(self) -> tuple[str, int | None]:
        # ZX 0x6E4C..0x6EA9 + 0x6ECE..0x6F18 (FSM state DEFINE_KEYS_WAIT_FRAME)
        ctx = self._fsm_define_keys_ctx
        if not ctx:
            raise RuntimeError("FSM define-keys state requires non-empty _fsm_define_keys_ctx")
        if "phase" not in ctx:
            raise RuntimeError("FSM define-keys state requires phase in context")
        if "slot_index" not in ctx:
            raise RuntimeError("FSM define-keys state requires slot_index in context")
        if not isinstance(ctx["phase"], str):
            raise RuntimeError("FSM define-keys state requires string phase")
        if not isinstance(ctx["slot_index"], int):
            raise RuntimeError("FSM define-keys state requires integer slot_index")
        phase = ctx["phase"]
        slot_index = ctx["slot_index"]
        slots = self._fsm_define_keys_slots()
        if slot_index < 0 or slot_index >= len(slots):
            raise RuntimeError(
                f"FSM define-keys state has invalid slot_index={slot_index} for {len(slots)} slots",
            )

        if phase == "wait_release_before_slot":
            if self._keyboard_any_pressed():
                return FSM_STATE_DEFINE_KEYS_WAIT_FRAME, 1
            ctx["phase"] = "draw_icon"
            return FSM_STATE_DEFINE_KEYS_WAIT_FRAME, None

        if phase == "draw_icon":
            icon_name, _, _ = slots[slot_index]
            getattr(self, icon_name)()
            ctx["phase"] = "wait_key"
            return FSM_STATE_DEFINE_KEYS_WAIT_FRAME, None

        if phase == "wait_key":
            key_probe = self._fsm_probe_define_key()
            if key_probe is None:
                return FSM_STATE_DEFINE_KEYS_WAIT_FRAME, 1
            a_bit, bc_port = key_probe
            _, port_attr, mask_attr = slots[slot_index]
            typed_port = getattr(self, port_attr)
            typed_mask = getattr(self, mask_attr)
            if not isinstance(typed_port, StructFieldPtr) or not isinstance(typed_mask, StructFieldPtr):
                raise TypeError("define-keys slots must be StructFieldPtr fields")
            typed_port.write_u16(bc_port)
            typed_mask.write_u8(a_bit)
            ctx["phase"] = "wait_release_after_slot"
            return FSM_STATE_DEFINE_KEYS_WAIT_FRAME, 1

        if phase == "wait_release_after_slot":
            if self._keyboard_any_pressed():
                return FSM_STATE_DEFINE_KEYS_WAIT_FRAME, 1
            slot_index += 1
            if slot_index >= len(slots):
                self.var_menu_selection_index = 0x00
                self.fn_title_screen_text_compositor()
                self.define_keys_apply_routine()
                self._fsm_define_keys_ctx = {}
                self._fsm_menu_ctx["prepared"] = False
                return FSM_STATE_MENU_POST_ACTION_FRAME, 1
            ctx["slot_index"] = slot_index
            ctx["phase"] = "draw_icon"
            return FSM_STATE_DEFINE_KEYS_WAIT_FRAME, None

        raise RuntimeError(f"Unknown define-keys phase: {phase!r}")

    def _fsm_highscore_prepare(self) -> bool:
        # ZX 0x6FBC..0x70BF pre-loop setup (FSM helper)
        selected_row_index: int | None = None
        if self.fn_score_compare_helper(row_index=0):
            self.high_score_row_shift_helper_4()
            self.fn_high_score_row_shift_helper_3()
            self.fn_high_score_row_shift_helper_2()
            self.fn_high_score_row_shift_helper_1()
            selected_row_index = 0
        elif self.fn_score_compare_helper(row_index=1):
            self.high_score_row_shift_helper_4()
            self.fn_high_score_row_shift_helper_3()
            self.fn_high_score_row_shift_helper_2()
            selected_row_index = 1
        elif self.fn_score_compare_helper(row_index=2):
            self.high_score_row_shift_helper_4()
            self.fn_high_score_row_shift_helper_3()
            selected_row_index = 2
        elif self.fn_score_compare_helper(row_index=3):
            self.high_score_row_shift_helper_4()
            selected_row_index = 3
        elif self.fn_score_compare_helper(row_index=4):
            selected_row_index = 4
        else:
            return False

        if selected_row_index is None:
            raise ValueError("High-score editor selected no row index")

        self.var_highscore_edit_row_index = selected_row_index
        self.var_highscore_name_edit_state = 0x00
        hl_row = self._highscore_row_ptr(selected_row_index)
        hl_ptr = hl_row.add(0x0002)
        for _ in range(0x0F):
            self._write_u8_ptr(hl_ptr, 0x0E)
            hl_ptr = hl_ptr.add(0x0001)

        ix_score = hl_ptr.add(0x0001)
        score_digits = (
            self.var_runtime_aux_c8_lo & 0xFF,
            self.var_runtime_aux_c8_hi & 0xFF,
            self.var_runtime_aux_ca & 0xFF,
            self.var_runtime_aux_cb & 0xFF,
            self.var_runtime_aux_cc & 0xFF,
        )
        for i, src_digit in enumerate(score_digits):
            self._write_u8_ptr(ix_score, (src_digit + 0x10) & 0xFF)
            if i != (len(score_digits) - 1):
                ix_score = ix_score.add(0x0001)

        self.fn_title_top_screen_setup()
        self.fn_stretched_text_symbol_stream_printer(
            HL_stream=BlockPtr(self.str_name_entry_prompt_stream, 0x0000),
            B_row=0x0A,
            C_col=0x08,
        )
        self.fn_routine_31_byte_row_fill_helper(HL_dst=self._display_attr_ptr(0x5940), A_fill=0x45)
        self.fn_routine_31_byte_row_fill_helper(HL_dst=self._display_attr_ptr(0x5960), A_fill=0x05)
        self.fn_routine_31_byte_row_fill_helper(HL_dst=self._display_attr_ptr(0x59e0), A_fill=0x05)
        self.fn_routine_31_byte_row_fill_helper(HL_dst=self._display_attr_ptr(0x5a00), A_fill=0x07)
        self.fn_compact_8x8_text_renderer()
        return True

    def _fsm_highscore_cursor_ptr(self) -> BlockPtr:
        state = self.var_highscore_name_edit_state & 0xFF
        return self._highscore_row_ptr(self.var_highscore_edit_row_index).add(0x0002 + state)

    def _fsm_highscore_finish(self) -> tuple[str, int | None]:
        ctx = self._fsm_highscore_ctx
        if not ctx:
            raise RuntimeError("FSM highscore finish requires non-empty _fsm_highscore_ctx")
        if "next_transition_kind" not in ctx:
            raise RuntimeError("FSM highscore finish requires next_transition_kind in context")
        if "return_state" not in ctx:
            raise RuntimeError("FSM highscore finish requires return_state in context")
        if not isinstance(ctx["next_transition_kind"], str):
            raise RuntimeError("FSM highscore finish requires string next_transition_kind")
        if not isinstance(ctx["return_state"], str):
            raise RuntimeError("FSM highscore finish requires string return_state")
        next_kind = ctx["next_transition_kind"]
        return_state = ctx["return_state"]
        self._fsm_highscore_ctx = {}
        self._fsm_transition_kind = next_kind
        return return_state, None

    def _fsm_prepare_gameplay_loop(self) -> None:
        # ZX 0xF174..0xF274 setup prefix (FSM state GAMEPLAY_SETUP)
        self.var_runtime_scheduler_timer = 0x1601
        self.var_runtime_progress_counter = 0x0A
        self.var_runtime_direction_mask = 0x00
        self._set_patch_callback_hook_opcode(0xC9)
        for queue in (
            self.var_transient_queue_a,
            self.var_transient_queue_b,
            self.var_transient_queue_c,
        ):
            for queue_entry in queue.entries:
                queue_entry.state = 0x00
                queue_entry.cell_ptr = None
        self.var_transient_queue_a.free_slots = 0x00
        self.var_transient_queue_b.free_slots = 0x00
        self.var_transient_queue_c.free_slots = 0x00
        self.fn_rebuild_hud_meter_bars_counters_xa8c4()
        if (self.var_active_map_mode & 0xFF) == 0x00:
            self.patch_scheduler_script_base_ptr = self.const_periodic_scheduler_step_4
            self.var_runtime_objective_counter = 0x06
            self.patch_queue_1_block_threshold_code = 0x50
            self.patch_queue_2_block_threshold_code = 0x50
            self.patch_queue_3_block_threshold_code = 0x50
            self.patch_queue_3_fallback_threshold_code = 0x50
            self.patch_queue_3_contact_branch_opcode = 0xC9
            self.fn_map_mode_setup_helper(DE_map=BlockPtr(self.var_level_map_mode_0, 0x0000))
        elif (self.var_active_map_mode & 0xFF) == 0x01:
            self.patch_scheduler_script_base_ptr = self.const_periodic_scheduler_step_3
            self.patch_queue_3_contact_branch_opcode = 0xC5
            self.fn_map_mode_setup_helper(DE_map=BlockPtr(self.var_level_map_mode_1, 0x0000))
            self.fn_active_map_mode_switch_entry_b()
            self.fn_overlay_preset_b_selector()
            self.patch_queue_1_block_threshold_code = 0x50
            self.patch_queue_2_block_threshold_code = 0x25
            self.patch_queue_3_block_threshold_code = 0x17
            self.patch_queue_3_fallback_threshold_code = 0x17
        else:
            self.patch_scheduler_script_base_ptr = self.const_periodic_scheduler_step_2
            self.patch_queue_3_contact_branch_opcode = 0xC5
            self.fn_map_mode_setup_helper(DE_map=BlockPtr(self.var_level_map_mode_2, 0x0000))
            self.fn_active_map_mode_switch_entry_a()
            self.fn_overlay_preset_c_selector()
            self.patch_queue_1_block_threshold_code = 0x17
            self.patch_queue_2_block_threshold_code = 0x25
            self.patch_queue_3_block_threshold_code = 0x17
            self.patch_queue_3_fallback_threshold_code = 0x17

    def _fsm_state_gameplay_setup(self) -> tuple[str, int | None]:
        if "initialized" not in self._fsm_gameplay_ctx:
            raise RuntimeError("FSM gameplay-setup state requires initialized in _fsm_gameplay_ctx")
        if not isinstance(self._fsm_gameplay_ctx["initialized"], bool):
            raise RuntimeError("FSM gameplay-setup state requires bool initialized in _fsm_gameplay_ctx")
        if not self._fsm_gameplay_ctx["initialized"]:
            if bool(self._fsm_gameplay_ctx.get("screen_setup_required", True)):
                self.gameplay_screen_setup()
                self.fn_overlay_preset_selector()
            self._fsm_prepare_gameplay_loop()
            self._fsm_gameplay_ctx["initialized"] = True
            self._fsm_start_stream(
                stream_a=BlockPtr(self.const_scenario_preset_a_stream_1, 0x0000),
                stream_b=BlockPtr(self.const_scenario_preset_a_stream_2, 0x0000),
                abort_on_keypress=True,
                return_state=FSM_STATE_GAMEPLAY_MAIN_FRAME,
            )
            return FSM_STATE_STREAM_INTERMISSION_FRAME, None
        return FSM_STATE_GAMEPLAY_MAIN_FRAME, None

    def _fsm_state_gameplay_main_frame(self) -> tuple[str, int | None]:
        # ZX 0xF174..0xF274 main-frame body (FSM state GAMEPLAY_MAIN_FRAME)
        self.per_frame_object_state_update_pass()
        self.fn_process_transient_effect_queues_handlers_xe530()
        self.fn_gameplay_movement_control_step()
        self._fsm_overlay_ctx = {
            "pre_frames_left": 0,
            "post_frames_left": 0,
            "pre_frame_snapshots": [],
            "post_frame_snapshots": [],
            "pre_frame_cursor": 0,
            "post_frame_cursor": 0,
        }
        self.fn_directional_interaction_dispatcher_using_pointer_table(
            defer_overlay_timing_to_fsm=True,
        )
        overlay_ctx = self._fsm_overlay_ctx
        pre_frames_left = int(overlay_ctx["pre_frames_left"])
        post_frames_left = int(overlay_ctx["post_frames_left"])
        if pre_frames_left > 0 or post_frames_left > 0:
            overlay_ctx["return_state"] = FSM_STATE_GAMEPLAY_MAIN_AFTER_DIRECTIONAL
            if pre_frames_left > 0:
                return FSM_STATE_OVERLAY_PRE_FILL_FRAME, None
            return FSM_STATE_OVERLAY_POST_FILL_FRAME, None
        return FSM_STATE_GAMEPLAY_MAIN_AFTER_DIRECTIONAL, None

    def _fsm_state_gameplay_main_after_directional(self) -> tuple[str, int | None]:
        # ZX 0xF174..0xF274 continuation after directional overlay frame-gates.
        callback_timing_frames, halt_frames = self.fn_patchable_callback_hook_frame_loop(
            defer_halt_to_fsm=True,
            defer_timing_to_fsm=True,
        )
        if callback_timing_frames > 0:
            self._fsm_callback_ctx = {
                "timing_frames_left": int(callback_timing_frames),
                "halt_frames_left": int(halt_frames),
                "return_state": FSM_STATE_GAMEPLAY_MAIN_AFTER_CALLBACK,
            }
            return FSM_STATE_CALLBACK_TIMING_FRAME, None
        if halt_frames > 0:
            self._fsm_callback_ctx = {
                "frames_left": int(halt_frames),
                "return_state": FSM_STATE_GAMEPLAY_MAIN_AFTER_CALLBACK,
            }
            return FSM_STATE_CALLBACK_HALT_65_FRAME, None
        return FSM_STATE_GAMEPLAY_MAIN_AFTER_CALLBACK, None

    def _fsm_state_gameplay_main_after_callback(self) -> tuple[str, int | None]:
        # ZX 0xF174..0xF274 continuation after callback frame-gate.
        self.fn_periodic_scheduler_tick()
        tick_ctx = self._fsm_tick_ctx
        if "pending_autonomous" not in tick_ctx:
            raise RuntimeError("FSM gameplay-main-after-callback requires pending_autonomous in _fsm_tick_ctx")
        if "pending_marker" not in tick_ctx:
            raise RuntimeError("FSM gameplay-main-after-callback requires pending_marker in _fsm_tick_ctx")
        if not isinstance(tick_ctx["pending_autonomous"], bool):
            raise RuntimeError(
                "FSM gameplay-main-after-callback requires bool pending_autonomous in _fsm_tick_ctx",
            )
        if not isinstance(tick_ctx["pending_marker"], bool):
            raise RuntimeError(
                "FSM gameplay-main-after-callback requires bool pending_marker in _fsm_tick_ctx",
            )
        pending_autonomous = tick_ctx["pending_autonomous"]
        pending_marker = tick_ctx["pending_marker"]
        if pending_marker and not pending_autonomous:
            raise RuntimeError(
                "FSM gameplay-main-after-callback has invalid tick context: "
                "pending_marker requires pending_autonomous=True",
            )
        if pending_autonomous:
            tick_ctx["scheduler_phase"] = "tick0"
            tick_ctx["scheduler_return_state"] = FSM_STATE_GAMEPLAY_MAIN_POST_TICK
            return FSM_STATE_SCHEDULER_AUTONOMOUS_FRAME, None
        return FSM_STATE_GAMEPLAY_MAIN_POST_TICK, None

    def _fsm_state_scheduler_autonomous_frame(self) -> tuple[str, int | None]:
        # ZX 0xF050..0xF0EC deferred autonomous scheduler branch
        tick_ctx = self._fsm_tick_ctx
        if "pending_autonomous" not in tick_ctx:
            raise RuntimeError("FSM scheduler-autonomous state requires pending_autonomous in _fsm_tick_ctx")
        if not isinstance(tick_ctx["pending_autonomous"], bool):
            raise RuntimeError("FSM scheduler-autonomous state requires bool pending_autonomous")
        if not tick_ctx["pending_autonomous"]:
            raise RuntimeError(
                "FSM scheduler-autonomous state requires pending_autonomous=True in _fsm_tick_ctx",
            )
        if "scheduler_phase" not in tick_ctx:
            raise RuntimeError("FSM scheduler-autonomous state requires scheduler_phase in _fsm_tick_ctx")
        if not isinstance(tick_ctx["scheduler_phase"], str):
            raise RuntimeError("FSM scheduler-autonomous state requires scheduler_phase to be string")
        scheduler_return_state = tick_ctx.get("scheduler_return_state", FSM_STATE_GAMEPLAY_MAIN_POST_TICK)
        if not isinstance(scheduler_return_state, str):
            raise RuntimeError("FSM scheduler-autonomous state requires scheduler_return_state to be string")
        phase = tick_ctx["scheduler_phase"]
        if phase == "tick0":
            tick_ctx["scheduler_phase"] = "after_tick0"
            tick_ctx["tick_stage3_next_state"] = FSM_STATE_SCHEDULER_AUTONOMOUS_FRAME
            return FSM_STATE_GAMEPLAY_TICK_STAGE_0_FRAME, None
        if phase != "after_tick0":
            raise RuntimeError(f"Unknown scheduler autonomous phase: {phase!r}")

        if "pending_marker" not in tick_ctx:
            raise RuntimeError("FSM scheduler-autonomous state requires pending_marker in _fsm_tick_ctx")
        if not isinstance(tick_ctx["pending_marker"], bool):
            raise RuntimeError("FSM scheduler-autonomous state requires bool pending_marker")
        pending_marker = tick_ctx["pending_marker"]
        tick_ctx["pending_autonomous"] = False
        tick_ctx["pending_marker"] = False
        tick_ctx["scheduler_phase"] = "tick0"
        tick_ctx.pop("scheduler_return_state", None)
        self.scheduler_triggered_autonomous_step(run_tick=False)
        if pending_marker:
            self.scheduler_triggered_marker_seeding()
        return scheduler_return_state, None

    def _fsm_state_gameplay_main_post_tick(self) -> tuple[str, int | None]:
        # Post-scheduler render for one gameplay frame.
        self.fn_main_pseudo_3d_map_render_pipeline()
        return FSM_STATE_GAMEPLAY_BRANCH, self._fsm_gameplay_delay_frames()

    def _fsm_gameplay_delay_frames(self) -> int:
        # Keep gameplay pacing aligned with legacy loop cadence for all movement
        # states, including teleport/move-commit animation phases.
        return max(1, int(GAMEPLAY_FRAME_DIVIDER))

    def _fsm_state_gameplay_branch(self) -> tuple[str, int | None]:
        if (
            (self.var_runtime_progress_byte_0 & 0xFF) == 0x00
            and (self.var_runtime_progress_byte_1 & 0xFF) == 0x00
            and (self.var_runtime_progress_byte_2 & 0xFF) == 0x00
        ):
            self._fsm_transition_kind = "level_complete"
            return FSM_STATE_TRANSITION_DISPATCH, None
        if ((self.var_runtime_scheduler_timer >> 8) & 0xFF) == 0x00:
            self._fsm_transition_kind = "failure"
            return FSM_STATE_TRANSITION_DISPATCH, None
        if (self.var_runtime_objective_counter & 0xFF) == 0x00:
            self._fsm_transition_kind = "failure"
            return FSM_STATE_TRANSITION_DISPATCH, None
        return FSM_STATE_GAMEPLAY_MAIN_FRAME, None

    def _fsm_state_transition_dispatch(self) -> tuple[str, int | None]:
        if not isinstance(self._fsm_transition_kind, str):
            raise RuntimeError("FSM transition dispatch requires string _fsm_transition_kind")
        kind = self._fsm_transition_kind
        if kind == "level_complete":
            self.fn_active_map_mode_switch_handler()
            self._fsm_level_roll_ctx = {
                "frame_idx": 0,
                "steps_done": 0,
            }
            return FSM_STATE_LEVEL_ROLL_FRAME, None
        if kind == "after_level_roll":
            next_mode = ((self.var_active_map_mode & 0xFF) + 0x01) & 0xFF
            self.var_active_map_mode = next_mode
            if next_mode != 0x03:
                self.fn_transition_beeper_entry_a()
                self._fsm_transition_kind = "none"
                self._fsm_gameplay_ctx["initialized"] = False
                self._fsm_gameplay_ctx["screen_setup_required"] = False
                return FSM_STATE_GAMEPLAY_SETUP, None
            self.fn_stretched_text_symbol_stream_printer(
                HL_stream=BlockPtr(self.str_ending_text_stream_1, 0x0000),
                B_row=0x03,
                C_col=0x05,
            )
            self.fn_stretched_text_symbol_stream_printer(
                HL_stream=BlockPtr(self.str_ending_text_stream_2, 0x0000),
                B_row=0x06,
                C_col=0x07,
            )
            self.fn_stretched_text_symbol_stream_printer(
                HL_stream=BlockPtr(self.str_ending_text_stream_3, 0x0000),
                B_row=0x09,
                C_col=0x06,
            )
            self.fn_stretched_text_symbol_stream_printer(
                HL_stream=BlockPtr(self.str_ending_text_stream_4, 0x0000),
                B_row=0x0C,
                C_col=0x0A,
            )
            self._fsm_transition_kind = "ending_post_text_stream"
            self._fsm_gameplay_ctx["initialized"] = False
            self._fsm_start_stream(
                stream_a=BlockPtr(self.const_scenario_preset_a_stream_1, 0x0000),
                stream_b=BlockPtr(self.const_scenario_preset_a_stream_2, 0x0000),
                abort_on_keypress=True,
                return_state=FSM_STATE_TRANSITION_DISPATCH,
            )
            return FSM_STATE_STREAM_INTERMISSION_FRAME, None
        if kind == "ending_post_text_stream":
            if self._fsm_highscore_prepare():
                self._fsm_highscore_ctx = {
                    "return_state": FSM_STATE_TRANSITION_DISPATCH,
                    "next_transition_kind": "ending_post_highscore",
                    "pending_key": 0xFF,
                }
                return FSM_STATE_HIGHSCORE_WAIT_KEY_FRAME, None
            self._fsm_transition_kind = "ending_post_highscore"
            return FSM_STATE_TRANSITION_DISPATCH, None
        if kind == "ending_post_highscore":
            self._queue_mode_audio_reset()
            self.fn_high_score_table_draw_routine()
            self._fsm_transition_kind = "ending_wait_release"
            self._fsm_menu_ctx["wait_release_return_state"] = FSM_STATE_TRANSITION_DISPATCH
            return FSM_STATE_WAIT_KEYBOARD_RELEASE_FRAME, None
        if kind == "ending_wait_release":
            self._fsm_transition_kind = "none"
            self._fsm_start_stream(
                stream_a=BlockPtr(self.const_scenario_preset_c_stream_1, 0x0000),
                stream_b=BlockPtr(self.const_scenario_preset_c_stream_2, 0x0000),
                abort_on_keypress=True,
                return_state=FSM_STATE_MENU_INIT,
            )
            return FSM_STATE_STREAM_INTERMISSION_FRAME, None
        if kind == "failure":
            self._set_patch_gameplay_movement_step_opcode(0xC9)
            hl_cell = self.var_runtime_current_cell_ptr
            self._write_u8_ptr(hl_cell, self._read_u8_ptr(hl_cell) & 0xC0)
            tick_ctx = self._fsm_tick_ctx
            tick_ctx["pending_autonomous"] = False
            tick_ctx["pending_marker"] = False
            tick_ctx.pop("scheduler_phase", None)
            tick_ctx.pop("scheduler_return_state", None)
            tick_ctx.pop("tick_stage_phase", None)
            tick_ctx.pop("tick_stage_id", None)
            tick_ctx.pop("tick_stage3_next_state", None)
            return FSM_STATE_FAILURE_TIMER_DRAIN_FRAME, None
        if kind == "failure_post_delay":
            self.fn_active_map_mode_switch_handler()
            if self._fsm_highscore_prepare():
                self._fsm_highscore_ctx = {
                    "return_state": FSM_STATE_TRANSITION_DISPATCH,
                    "next_transition_kind": "failure_post_highscore",
                    "pending_key": 0xFF,
                }
                return FSM_STATE_HIGHSCORE_WAIT_KEY_FRAME, None
            self._fsm_transition_kind = "failure_post_highscore"
            return FSM_STATE_TRANSITION_DISPATCH, None
        if kind == "failure_post_highscore":
            self._queue_mode_audio_reset()
            self.fn_high_score_table_draw_routine()
            self._fsm_transition_kind = "failure_wait_release"
            self._fsm_menu_ctx["wait_release_return_state"] = FSM_STATE_TRANSITION_DISPATCH
            return FSM_STATE_WAIT_KEYBOARD_RELEASE_FRAME, None
        if kind == "failure_wait_release":
            self._fsm_transition_kind = "none"
            self._fsm_start_stream(
                stream_a=BlockPtr(self.const_scenario_preset_c_stream_1, 0x0000),
                stream_b=BlockPtr(self.const_scenario_preset_c_stream_2, 0x0000),
                abort_on_keypress=True,
                return_state=FSM_STATE_MENU_INIT,
            )
            return FSM_STATE_STREAM_INTERMISSION_FRAME, None
        raise RuntimeError(f"Unknown FSM transition kind: {kind!r}")

    def _fsm_state_level_roll_frame(self) -> tuple[str, int | None]:
        # ZX 0xF4A4..0xF4B4 (FSM state LEVEL_ROLL_FRAME)
        self._level_complete_roll_audio_frame_sync = True
        ctx = self._fsm_level_roll_ctx
        if not ctx:
            raise RuntimeError("FSM level-roll state requires non-empty _fsm_level_roll_ctx")
        if "frame_idx" not in ctx or "steps_done" not in ctx:
            raise RuntimeError("FSM level-roll state requires frame_idx and steps_done in context")
        if not isinstance(ctx["frame_idx"], int):
            raise RuntimeError("FSM level-roll state requires integer frame_idx")
        if not isinstance(ctx["steps_done"], int):
            raise RuntimeError("FSM level-roll state requires integer steps_done")
        frame_idx = ctx["frame_idx"]
        steps_done = ctx["steps_done"]
        total_steps = int(LEVEL_COMPLETE_ROLL_TOTAL_STEPS)
        total_frames = int(LEVEL_COMPLETE_ROLL_TARGET_FRAMES)
        if frame_idx >= total_frames:
            self._fsm_level_roll_ctx = {}
            self._fsm_transition_kind = "after_level_roll"
            self._level_complete_roll_audio_frame_sync = False
            return FSM_STATE_TRANSITION_DISPATCH, None
        next_steps = ((frame_idx + 0x01) * total_steps) // total_frames
        steps_this_frame = next_steps - steps_done
        for _ in range(max(0, steps_this_frame)):
            self.fn_hud_decimal_counter_animator()
        self.fn_paced_beeper_helper_transitions_panel_fill()
        ctx["frame_idx"] = frame_idx + 1
        ctx["steps_done"] = next_steps
        return FSM_STATE_LEVEL_ROLL_FRAME, 1

    def _fsm_state_frame_delay_0x50_frame(self) -> tuple[str, int | None]:
        ctx = self._fsm_frame_delay_ctx
        if not ctx:
            raise RuntimeError("FSM frame-delay state requires non-empty _fsm_frame_delay_ctx")
        if "return_state" not in ctx:
            raise RuntimeError("FSM frame-delay state requires return_state in context")
        if not isinstance(ctx["return_state"], str):
            raise RuntimeError("FSM frame-delay state requires string return_state")
        if "frames_left" not in ctx:
            raise RuntimeError("FSM frame-delay state requires frames_left in context")
        if not isinstance(ctx["frames_left"], int):
            raise RuntimeError("FSM frame-delay state requires integer frames_left")
        frames_left = ctx["frames_left"]
        if frames_left <= 0:
            next_state = ctx["return_state"]
            self._fsm_frame_delay_ctx = {}
            return next_state, None
        ctx["frames_left"] = frames_left - 1
        return FSM_STATE_FRAME_DELAY_0X50_FRAME, 1

    def _fsm_state_failure_timer_drain_frame(self) -> tuple[str, int | None]:
        # ZX 0xF437..0xF43E deferred failure-cleanup timer drain loop.
        tick_ctx = self._fsm_tick_ctx
        while True:
            self.fn_periodic_scheduler_tick()

            if "pending_autonomous" not in tick_ctx:
                raise RuntimeError("FSM failure timer-drain state requires pending_autonomous in _fsm_tick_ctx")
            if "pending_marker" not in tick_ctx:
                raise RuntimeError("FSM failure timer-drain state requires pending_marker in _fsm_tick_ctx")
            if not isinstance(tick_ctx["pending_autonomous"], bool):
                raise RuntimeError(
                    "FSM failure timer-drain state requires bool pending_autonomous in _fsm_tick_ctx",
                )
            if not isinstance(tick_ctx["pending_marker"], bool):
                raise RuntimeError("FSM failure timer-drain state requires bool pending_marker in _fsm_tick_ctx")
            pending_autonomous = tick_ctx["pending_autonomous"]
            pending_marker = tick_ctx["pending_marker"]
            if pending_marker and not pending_autonomous:
                raise RuntimeError(
                    "FSM failure timer-drain state has invalid tick context: "
                    "pending_marker requires pending_autonomous=True",
                )
            if pending_autonomous:
                tick_ctx["scheduler_phase"] = "tick0"
                tick_ctx["scheduler_return_state"] = FSM_STATE_FAILURE_TIMER_DRAIN_FRAME
                return FSM_STATE_SCHEDULER_AUTONOMOUS_FRAME, None

            if ((self.var_runtime_scheduler_timer >> 8) & 0xFF) == 0x00:
                self._set_patch_gameplay_movement_step_opcode(0x3A)
                self.fn_rectangular_panel_fill_helper(A_fill=0x00)
                self.fn_draw_mission_status_panel_bitmap_chunk()
                self.fn_transition_beeper_helper()
                self._fsm_transition_kind = "failure_post_delay"
                self._fsm_gameplay_ctx["initialized"] = False
                self._fsm_frame_delay_ctx = {
                    "frames_left": 0x50,
                    "return_state": FSM_STATE_TRANSITION_DISPATCH,
                }
                return FSM_STATE_FRAME_DELAY_0X50_FRAME, None

            # Render one visible drain step per host frame (one scheduler script step).
            if (self.var_runtime_scheduler_timer & 0x00FF) == 0x00FF:
                return FSM_STATE_FAILURE_TIMER_DRAIN_FRAME, 1

    def _fsm_state_highscore_wait_key_frame(self) -> tuple[str, int | None]:
        # ZX 0x6FBC..0x70BF input wait loop (FSM state HIGHSCORE_WAIT_KEY_FRAME)
        ctx = self._fsm_highscore_ctx
        if not ctx:
            raise RuntimeError("FSM highscore wait-key state requires non-empty _fsm_highscore_ctx")
        hl_stream = self._highscore_row_ptr(self.var_highscore_edit_row_index)
        self.fn_stretched_text_symbol_stream_printer(HL_stream=hl_stream, B_row=0x0F, C_col=0x04)
        a_key = self._rom_get_key_02bf()
        if a_key == 0xFF:
            return FSM_STATE_HIGHSCORE_WAIT_KEY_FRAME, 1
        if not (a_key == 0x20 or a_key >= 0x2F or a_key == 0x0C or a_key == 0x0D):
            return FSM_STATE_HIGHSCORE_WAIT_KEY_FRAME, 1
        ctx["pending_key"] = a_key & 0xFF
        return FSM_STATE_HIGHSCORE_FILTER_KEY_FRAME, None

    def _fsm_state_highscore_filter_key_frame(self) -> tuple[str, int | None]:
        ctx = self._fsm_highscore_ctx
        if not ctx:
            raise RuntimeError("FSM highscore filter-key state requires non-empty _fsm_highscore_ctx")
        if "pending_key" not in ctx:
            raise RuntimeError("FSM highscore filter-key state requires pending_key in context")
        if not isinstance(ctx["pending_key"], int):
            raise RuntimeError("FSM highscore filter-key state requires integer pending_key")
        a_key = ctx["pending_key"] & 0xFF
        if a_key == 0x0D:
            ctx.pop("pending_key", None)
            return self._fsm_highscore_finish()
        if a_key == 0x0C:
            ctx.pop("pending_key", None)
            return FSM_STATE_HIGHSCORE_BACKSPACE_FRAME, None
        return FSM_STATE_HIGHSCORE_CHAR_FRAME, None

    def _fsm_state_highscore_backspace_frame(self) -> tuple[str, int | None]:
        if not self._fsm_highscore_ctx:
            raise RuntimeError("FSM highscore backspace state requires non-empty _fsm_highscore_ctx")
        state = self.var_highscore_name_edit_state & 0xFF
        if state != 0x00:
            state = (state - 0x01) & 0xFF
            self.var_highscore_name_edit_state = state
            self._write_u8_ptr(self._fsm_highscore_cursor_ptr(), 0x0E)
        self._rom_beeper(de_ticks=0x0096, hl_period=0x0190)
        return FSM_STATE_HIGHSCORE_WAIT_KEY_FRAME, 1

    def _fsm_state_highscore_char_frame(self) -> tuple[str, int | None]:
        ctx = self._fsm_highscore_ctx
        if not ctx:
            raise RuntimeError("FSM highscore char state requires non-empty _fsm_highscore_ctx")
        if "pending_key" not in ctx:
            raise RuntimeError("FSM highscore char state requires pending_key in context")
        pending_key = ctx.pop("pending_key")
        if not isinstance(pending_key, int):
            raise RuntimeError("FSM highscore char state requires integer pending_key")
        a_key = pending_key & 0xFF
        self._write_u8_ptr(self._fsm_highscore_cursor_ptr(), ((a_key & 0x7F) - 0x20) & 0xFF)
        state = ((self.var_highscore_name_edit_state & 0xFF) + 0x01) & 0xFF
        self.var_highscore_name_edit_state = state
        if state == 0x0F:
            return self._fsm_highscore_finish()
        self._rom_beeper(de_ticks=0x0096, hl_period=0x0190)
        return FSM_STATE_HIGHSCORE_WAIT_KEY_FRAME, 1

    def _fsm_state_gameplay_tick_stage_frame(
        self,
        *,
        stage_key: str,
        stage_state: str,
        e_code: int,
        next_state: str,
    ) -> tuple[str, int | None]:
        tick_ctx = self._fsm_tick_ctx
        if "tick_stage_id" in tick_ctx and not isinstance(tick_ctx["tick_stage_id"], str):
            raise RuntimeError("FSM gameplay tick-stage requires tick_stage_id to be string")
        current_stage_id = tick_ctx.get("tick_stage_id")
        if current_stage_id != stage_key:
            tick_ctx["tick_stage_id"] = stage_key
            tick_ctx["tick_stage_phase"] = "pre"

        if "tick_stage_phase" not in tick_ctx:
            raise RuntimeError("FSM gameplay tick-stage requires tick_stage_phase in _fsm_tick_ctx")
        if not isinstance(tick_ctx["tick_stage_phase"], str):
            raise RuntimeError("FSM gameplay tick-stage requires tick_stage_phase to be string")
        phase = tick_ctx["tick_stage_phase"]
        if phase == "pre":
            self._gameplay_tick_update_core_pre(E_code=e_code, D_xor=0x00)
            callback_timing_frames, callback_halt_frames = self.fn_patchable_callback_hook_frame_loop(
                defer_halt_to_fsm=True,
                defer_timing_to_fsm=True,
            )
            tick_ctx["tick_stage_phase"] = "after_callback"
            if callback_timing_frames > 0:
                self._fsm_callback_ctx = {
                    "timing_frames_left": int(callback_timing_frames),
                    "halt_frames_left": int(callback_halt_frames),
                    "return_state": stage_state,
                }
                return FSM_STATE_CALLBACK_TIMING_FRAME, None
            if callback_halt_frames > 0:
                self._fsm_callback_ctx = {
                    "frames_left": int(callback_halt_frames),
                    "return_state": stage_state,
                }
                return FSM_STATE_CALLBACK_HALT_65_FRAME, None
            phase = "after_callback"

        if phase == "after_callback":
            self._fsm_overlay_ctx = {
                "pre_frames_left": 0,
                "post_frames_left": 0,
                "pre_frame_snapshots": [],
                "post_frame_snapshots": [],
                "pre_frame_cursor": 0,
                "post_frame_cursor": 0,
            }
            self.fn_directional_interaction_dispatcher_using_pointer_table(
                defer_overlay_timing_to_fsm=True,
            )
            overlay_ctx = self._fsm_overlay_ctx
            pre_frames_left = int(overlay_ctx["pre_frames_left"])
            post_frames_left = int(overlay_ctx["post_frames_left"])
            tick_ctx["tick_stage_phase"] = "after_overlay"
            if pre_frames_left > 0 or post_frames_left > 0:
                overlay_ctx["return_state"] = stage_state
                if pre_frames_left > 0:
                    return FSM_STATE_OVERLAY_PRE_FILL_FRAME, None
                return FSM_STATE_OVERLAY_POST_FILL_FRAME, None
            phase = "after_overlay"

        if phase == "after_overlay":
            self._gameplay_tick_update_core_post()
            tick_ctx.pop("tick_stage_phase", None)
            tick_ctx.pop("tick_stage_id", None)
            return next_state, self._fsm_gameplay_delay_frames()

        raise RuntimeError(f"Unknown gameplay tick-stage phase: {phase!r}")

    def _fsm_state_gameplay_tick_stage_0_frame(self) -> tuple[str, int | None]:
        return self._fsm_state_gameplay_tick_stage_frame(
            stage_key="stage0",
            stage_state=FSM_STATE_GAMEPLAY_TICK_STAGE_0_FRAME,
            e_code=0x26,
            next_state=FSM_STATE_GAMEPLAY_TICK_STAGE_1_FRAME,
        )

    def _fsm_state_gameplay_tick_stage_1_frame(self) -> tuple[str, int | None]:
        return self._fsm_state_gameplay_tick_stage_frame(
            stage_key="stage1",
            stage_state=FSM_STATE_GAMEPLAY_TICK_STAGE_1_FRAME,
            e_code=0x27,
            next_state=FSM_STATE_GAMEPLAY_TICK_STAGE_2_FRAME,
        )

    def _fsm_state_gameplay_tick_stage_2_frame(self) -> tuple[str, int | None]:
        if "tick_stage3_next_state" not in self._fsm_tick_ctx:
            raise RuntimeError("FSM gameplay tick-stage2 requires tick_stage3_next_state in _fsm_tick_ctx")
        return self._fsm_state_gameplay_tick_stage_frame(
            stage_key="stage2",
            stage_state=FSM_STATE_GAMEPLAY_TICK_STAGE_2_FRAME,
            e_code=0x28,
            next_state=FSM_STATE_GAMEPLAY_TICK_STAGE_3_FRAME,
        )

    def _fsm_state_gameplay_tick_stage_3_frame(self) -> tuple[str, int | None]:
        tick_ctx = self._fsm_tick_ctx
        if "tick_stage3_next_state" not in tick_ctx:
            raise RuntimeError("FSM gameplay tick-stage3 requires tick_stage3_next_state in _fsm_tick_ctx")
        if not isinstance(tick_ctx["tick_stage3_next_state"], str):
            raise RuntimeError("FSM gameplay tick-stage3 requires tick_stage3_next_state to be string")
        next_state = tick_ctx["tick_stage3_next_state"]
        out_state, out_delay = self._fsm_state_gameplay_tick_stage_frame(
            stage_key="stage3",
            stage_state=FSM_STATE_GAMEPLAY_TICK_STAGE_3_FRAME,
            e_code=0x29,
            next_state=next_state,
        )
        if out_state == next_state and out_delay is not None:
            tick_ctx.pop("tick_stage3_next_state", None)
        return out_state, out_delay

    def _fsm_state_overlay_pre_fill_frame(self) -> tuple[str, int | None]:
        ctx = self._fsm_overlay_ctx
        if not ctx:
            raise RuntimeError("FSM overlay pre-fill state requires non-empty _fsm_overlay_ctx")
        if "pre_frames_left" not in ctx:
            raise RuntimeError("FSM overlay pre-fill state requires pre_frames_left in context")
        if "post_frames_left" not in ctx:
            raise RuntimeError("FSM overlay pre-fill state requires post_frames_left in context")
        if "return_state" not in ctx:
            raise RuntimeError("FSM overlay pre-fill state requires overlay return_state")
        if not isinstance(ctx["return_state"], str):
            raise RuntimeError("FSM overlay pre-fill state requires string return_state")
        pre_frames_left = int(ctx["pre_frames_left"])
        post_frames_left = int(ctx["post_frames_left"])
        if pre_frames_left <= 0:
            if post_frames_left > 0:
                return FSM_STATE_OVERLAY_POST_FILL_FRAME, None
            next_state = ctx["return_state"]
            self._fsm_overlay_ctx = {}
            return next_state, None
        self._fsm_overlay_apply_snapshot(
            snapshots_key="pre_frame_snapshots",
            cursor_key="pre_frame_cursor",
        )
        pre_frames_left -= 1
        ctx["pre_frames_left"] = pre_frames_left
        if pre_frames_left > 0:
            return FSM_STATE_OVERLAY_PRE_FILL_FRAME, 1
        if post_frames_left > 0:
            return FSM_STATE_OVERLAY_POST_FILL_FRAME, 1
        next_state = ctx["return_state"]
        self._fsm_overlay_ctx = {}
        return next_state, 1

    def _fsm_state_overlay_post_fill_frame(self) -> tuple[str, int | None]:
        ctx = self._fsm_overlay_ctx
        if not ctx:
            raise RuntimeError("FSM overlay post-fill state requires non-empty _fsm_overlay_ctx")
        if "return_state" not in ctx:
            raise RuntimeError("FSM overlay post-fill state requires overlay return_state")
        if not isinstance(ctx["return_state"], str):
            raise RuntimeError("FSM overlay post-fill state requires string return_state")
        if "post_frames_left" not in ctx:
            raise RuntimeError("FSM overlay post-fill state requires post_frames_left in context")
        post_frames_left = int(ctx["post_frames_left"])
        if post_frames_left <= 0:
            next_state = ctx["return_state"]
            self._fsm_overlay_ctx = {}
            return next_state, None
        self._fsm_overlay_apply_snapshot(
            snapshots_key="post_frame_snapshots",
            cursor_key="post_frame_cursor",
        )
        post_frames_left -= 1
        ctx["post_frames_left"] = post_frames_left
        if post_frames_left > 0:
            return FSM_STATE_OVERLAY_POST_FILL_FRAME, 1
        next_state = ctx["return_state"]
        self._fsm_overlay_ctx = {}
        return next_state, 1

    def _fsm_overlay_capture_snapshot(self, *, snapshots_key: str) -> None:
        ctx = self._fsm_overlay_ctx
        snapshots = ctx.get(snapshots_key)
        if snapshots is None:
            return
        if not isinstance(snapshots, list):
            raise RuntimeError(f"FSM overlay context requires list {snapshots_key}")
        snapshots.append(
            {
                "screen_bitmap": bytes(self.screen_bitmap),
                "screen_attrs": bytes(self.screen_attrs),
                "border_color": self.border_color & 0x07,
            },
        )

    def _fsm_overlay_apply_snapshot(self, *, snapshots_key: str, cursor_key: str) -> None:
        ctx = self._fsm_overlay_ctx
        snapshots = ctx.get(snapshots_key)
        if snapshots is None:
            return
        if not isinstance(snapshots, list):
            raise RuntimeError(f"FSM overlay context requires list {snapshots_key}")
        cursor = int(ctx.get(cursor_key, 0))
        if cursor < 0:
            raise RuntimeError(f"FSM overlay context has negative cursor {cursor_key}={cursor}")
        if cursor >= len(snapshots):
            return
        snapshot = snapshots[cursor]
        if not isinstance(snapshot, dict):
            raise RuntimeError(f"FSM overlay snapshot {snapshots_key}[{cursor}] must be dict")
        bitmap = snapshot.get("screen_bitmap")
        attrs = snapshot.get("screen_attrs")
        border = snapshot.get("border_color", self.border_color)
        if not isinstance(bitmap, (bytes, bytearray)):
            raise RuntimeError(f"FSM overlay snapshot {snapshots_key}[{cursor}] missing screen_bitmap bytes")
        if not isinstance(attrs, (bytes, bytearray)):
            raise RuntimeError(f"FSM overlay snapshot {snapshots_key}[{cursor}] missing screen_attrs bytes")
        if not isinstance(border, int):
            raise RuntimeError(f"FSM overlay snapshot {snapshots_key}[{cursor}] border_color must be int")
        if len(bitmap) != len(self.screen_bitmap):
            raise RuntimeError(
                f"FSM overlay snapshot {snapshots_key}[{cursor}] bitmap size mismatch: "
                f"{len(bitmap)} != {len(self.screen_bitmap)}",
            )
        if len(attrs) != len(self.screen_attrs):
            raise RuntimeError(
                f"FSM overlay snapshot {snapshots_key}[{cursor}] attr size mismatch: "
                f"{len(attrs)} != {len(self.screen_attrs)}",
            )
        self.screen_bitmap[:] = bytes(bitmap)
        self.screen_attrs[:] = bytes(attrs)
        self.border_color = border & 0x07
        ctx[cursor_key] = cursor + 1

    def _fsm_state_callback_timing_frame(self) -> tuple[str, int | None]:
        ctx = self._fsm_callback_ctx
        if not ctx:
            raise RuntimeError("FSM callback timing state requires non-empty _fsm_callback_ctx")
        if "return_state" not in ctx:
            raise RuntimeError("FSM callback timing state requires callback return_state")
        if not isinstance(ctx["return_state"], str):
            raise RuntimeError("FSM callback timing state requires string return_state")
        if "timing_frames_left" not in ctx:
            raise RuntimeError("FSM callback timing state requires timing_frames_left in context")
        if "halt_frames_left" not in ctx:
            raise RuntimeError("FSM callback timing state requires halt_frames_left in context")
        if not isinstance(ctx["timing_frames_left"], int):
            raise RuntimeError("FSM callback timing state requires integer timing_frames_left")
        if not isinstance(ctx["halt_frames_left"], int):
            raise RuntimeError("FSM callback timing state requires integer halt_frames_left")
        timing_frames_left = ctx["timing_frames_left"]
        if timing_frames_left <= 0:
            halt_frames_left = ctx["halt_frames_left"]
            if halt_frames_left > 0:
                ctx.pop("timing_frames_left", None)
                ctx.pop("halt_frames_left", None)
                ctx["frames_left"] = halt_frames_left
                return FSM_STATE_CALLBACK_HALT_65_FRAME, None
            next_state = ctx["return_state"]
            self._fsm_callback_ctx = {}
            return next_state, None

        timing_frames_left -= 1
        ctx["timing_frames_left"] = timing_frames_left
        if timing_frames_left > 0:
            return FSM_STATE_CALLBACK_TIMING_FRAME, 1

        halt_frames_left = ctx["halt_frames_left"]
        if halt_frames_left > 0:
            ctx.pop("timing_frames_left", None)
            ctx.pop("halt_frames_left", None)
            ctx["frames_left"] = halt_frames_left
            return FSM_STATE_CALLBACK_HALT_65_FRAME, 1

        next_state = ctx["return_state"]
        self._fsm_callback_ctx = {}
        return next_state, 1

    def _fsm_state_callback_halt_65_frame(self) -> tuple[str, int | None]:
        ctx = self._fsm_callback_ctx
        if not ctx:
            raise RuntimeError("FSM callback halt state requires non-empty _fsm_callback_ctx")
        if "return_state" not in ctx:
            raise RuntimeError("FSM callback halt state requires callback return_state")
        if not isinstance(ctx["return_state"], str):
            raise RuntimeError("FSM callback halt state requires string return_state")
        if "frames_left" not in ctx:
            raise RuntimeError("FSM callback halt state requires frames_left in context")
        if not isinstance(ctx["frames_left"], int):
            raise RuntimeError("FSM callback halt state requires integer frames_left")
        frames_left = ctx["frames_left"]
        if frames_left <= 0:
            next_state = ctx["return_state"]
            self._fsm_callback_ctx = {}
            return next_state, None

        frames_left -= 1
        ctx["frames_left"] = frames_left
        if frames_left > 0:
            return FSM_STATE_CALLBACK_HALT_65_FRAME, 1
        next_state = ctx["return_state"]
        self._fsm_callback_ctx = {}
        return next_state, 1

    def _fsm_state_runtime_fallback_idle_frame(self) -> tuple[str, int | None]:
        return FSM_STATE_RUNTIME_FALLBACK_IDLE_FRAME, 1

    def in_port(self, bc_port: int) -> int:
        port = bc_port & 0xFFFF
        if (port & 0x00FF) == 0x1F:
            return self.joy_kempston
        if (port & 0x00FF) == 0xDF:
            # 0x00DF control preset path (Kempston) uses BIT/JP NZ tests in
            # the original patch table, so keep pressed directions active-high.
            return (self.joy_kempston & 0x1F) | 0xE0
        if (port & 0x00FF) == 0xFE:
            value = 0xFF
            for row_index, row_value in enumerate(self.keyboard_rows):
                if (port & (1 << (8 + row_index))) == 0:
                    value &= row_value
            return value
        return super().in_port(bc_port)

    def _first_pressed_key_scan(self) -> tuple[int, int, str] | None:
        for row_index, bit_index, key_char in _ROWBIT_KEY_SCAN_ORDER:
            if (self.keyboard_rows[row_index] & (1 << bit_index)) == 0:
                return row_index, bit_index, key_char
        return None

    def _is_key_pressed_char(self, key_char: str) -> bool:
        key_norm = key_char if key_char in ("\n", "\r", " ") else key_char.lower()
        mapped = KEY_CHAR_TO_ZX_KEYBOARD_SCAN.get(key_norm)
        if mapped is None:
            return False
        row_index = ZX_KEYBOARD_ROW_INDEX_BY_PORT.get(mapped[0])
        if row_index is None:
            return False
        return (self.keyboard_rows[row_index] & (1 << mapped[1])) == 0

    def _rom_get_key_02bf(self) -> int:
        scan = self._first_pressed_key_scan()
        if scan is None:
            self._rom_last_key_scan = None
            return 0xFF
        row_index, bit_index, key = scan
        if self._rom_last_key_scan == (row_index, bit_index):
            return 0xFF
        self._rom_last_key_scan = (row_index, bit_index)
        if key in ("\r", "\n"):
            return 0x0D
        if len(key) == 1:
            return ord(key) & 0x7F
        return 0xFF

    def _rom_keyboard_input_poll_028e(self) -> int:
        # ROM 0x028E ultimately returns key code in E (0xFF when no new key).
        return self._rom_get_key_02bf()

    def _keyboard_any_pressed(self) -> bool:
        for row in self.keyboard_rows:
            if (row & 0x1F) != 0x1F:
                return True
        return False

    def _wait_keyboard_release(self) -> None:
        if self._fsm_step_active:
            raise RuntimeError(
                "Legacy keyboard-release wait called during active FSM step; "
                "use FSM wait-keyboard-release state instead",
            )
        # Frame-step runtime keeps one input snapshot per step; wait for release
        # with yields so held key from menu doesn't auto-fill define-keys slots.
        while self._keyboard_any_pressed():
            prev_frame = self.frame_counter
            self._yield_frame()
            if self.frame_counter == prev_frame:
                # Fallback for non-frame-driven direct calls.
                break

    def _rom_keyboard_check_break_1f54(self) -> bool:
        """Approximate ROM 0x1F54 break gate; True means 'continue' (carry set)."""
        if not self._keyboard_any_pressed():
            return True
        if self._is_key_pressed_char("q"):
            return False
        return True

    # ZX 0x6B3A..0x6B6E
    def fn_title_top_screen_setup(self):
        self.var_display_bitmap_ram[0x0000:0x0800] = self.const_title_bitmap_source[0x0000:0x0800]
        self.var_display_attribute_ram[0x0000:0x0100] = self.const_title_attr_source[0x0000:0x0100]
        self.var_display_attribute_ram[0x0100:0x0300] = b"\x00" * 0x0200
        self.out_port(0x00FE, 0x00)
        self.var_rom_border_shadow_byte = 0x00
        self.var_display_bitmap_ram[0x0800:0x1800] = b"\x00" * 0x1000

    # ZX 0x6B6F..0x6BAC
    def fn_title_screen_text_compositor(self) -> None:
        self.fn_title_top_screen_setup()
        self.fn_stretched_text_symbol_stream_printer(
            HL_stream=BlockPtr(self.str_frontend_option_stream_1, 0x0000),
            B_row=0x0A,
            C_col=0x09,
        )
        self.fn_stretched_text_symbol_stream_printer(
            HL_stream=BlockPtr(self.str_frontend_option_stream_2, 0x0000),
            B_row=0x0C,
            C_col=0x09,
        )
        self.fn_stretched_text_symbol_stream_printer(
            HL_stream=BlockPtr(self.str_frontend_option_stream_3, 0x0000),
            B_row=0x0E,
            C_col=0x09,
        )
        self.fn_stretched_text_symbol_stream_printer(
            HL_stream=BlockPtr(self.str_frontend_option_stream_4, 0x0000),
            B_row=0x10,
            C_col=0x09,
        )
        self.fn_stretched_text_symbol_stream_printer(
            HL_stream=BlockPtr(self.str_frontend_option_stream_5, 0x0000),
            B_row=0x12,
            C_col=0x09,
        )
        self.fn_stretched_text_symbol_stream_printer(
            HL_stream=BlockPtr(self.str_frontend_option_stream_6, 0x0000),
            B_row=0x14,
            C_col=0x09,
        )
        self.fn_compact_8x8_text_renderer()
        self.front_end_highlight_initializer()

    # ZX 0x6BAD..0x6BE3
    def fn_compact_8x8_text_renderer(self) -> None:
        self.patch_highscore_header_tail_ptr = BlockPtr(self.str_byline_stream, 0x0000)
        glyph_bias_ptr = self._glyph_bias_ptr
        B_row = 0x17
        C_col = 0x01
        while True:
            stream_ptr = self.patch_highscore_header_tail_ptr
            A_code = self._read_u8_ptr(stream_ptr)
            if A_code == 0xFF:
                break
            DE_glyph = glyph_bias_ptr.add((((A_code + 0x01) & 0xFF) << 0x03))
            self.fn_routine_8_byte_screen_blit_primitive(DE_src=DE_glyph, B_row=B_row, C_col=C_col)
            C_col = (C_col + 0x01) & 0xFF
            self.patch_highscore_header_tail_ptr = stream_ptr.add(0x0001)
        self._fill_bytes_ptr(self._display_attr_ptr(0x5ae0), 0x20, 0x04)

    # ZX 0x6BE4..0x6BF0
    def front_end_highlight_initializer(self):
        B_count = 0x0C
        DE_step = 0x0020
        HL_cell = self._display_attr_ptr(0x5949)
        while B_count != 0x00:
            self._write_u8_ptr(HL_cell, 0x0F)
            HL_cell = self._ptr_add(HL_cell, DE_step)
            B_count = (B_count - 0x01) & 0xFF
        self.fn_front_end_selection_bars_redraw()

    # ZX 0x6BF1..0x6C01
    def fn_front_end_selection_bars_redraw(self):
        self.fn_attribute_span_fill_helper(HL_dst=self._display_attr_ptr(0x594b), A_fill=0x05)
        self.fn_attribute_span_fill_helper(HL_dst=self._display_attr_ptr(0x596b), A_fill=0x07)

    # ZX 0x6C02..0x6C18
    def fn_attribute_span_fill_helper(self, HL_dst, A_fill):
        fill = A_fill & 0xFF
        for i in range(0x06):
            self._fill_bytes_ptr(HL_dst, 0x18, fill)
            if i != (0x06 - 1):
                HL_dst = self._ptr_add(HL_dst, 0x40)

    # ZX 0x6C82..0x6CD7
    def top_level_pre_game_control_loop(self) -> None:
        if self._fsm_step_active:
            raise RuntimeError(
                "Legacy menu control loop called during active FSM step; "
                "use FSM menu states instead",
            )
        self.fn_title_screen_text_compositor()
        self.fn_scenario_preset_b_beeper_stream_engine()
        while True:
            A_sel = self.var_menu_selection_index & 0xFF
            row_offset = ((A_sel + 0x01) * 0x40) & 0xFFFF
            HL_row = self._ptr_add(self._display_attr_ptr(0x590a), row_offset)
            self._write_u8_ptr(HL_row, 0x06)
            self._write_u8_ptr(self._ptr_add(HL_row, 0x20), 0x06)
            self._fill_bytes_ptr(self._ptr_add(HL_row, 0x22), 0x11, 0x06)
            self.fn_front_end_two_step_beeper_cadence()
            action_taken = False
            while True:
                A_keys = self.in_port(0xF7FE) & 0xFF
                if (A_keys & 0x01) == 0x00:
                    self.define_keys_apply_routine()
                    action_taken = True
                    break
                if (A_keys & 0x02) == 0x00:
                    self.control_preset_branch_3()
                    action_taken = True
                    break
                if (A_keys & 0x04) == 0x00:
                    self.control_preset_branch()
                    action_taken = True
                    break
                if (A_keys & 0x08) == 0x00:
                    self.control_preset_branch_2()
                    action_taken = True
                    break
                if (A_keys & 0x10) == 0x00:
                    self.define_keys_setup_flow()
                    action_taken = True
                    break
                A_start = self.in_port(0xEFFE) & 0xFF
                if (A_start & 0x10) == 0x00:
                    self.gameplay_session_controller()
                    return
                # Original code loops at 0x6CAE while idle; yield per frame to
                # preserve frame-step contract without re-running 0x6C88 block.
                self._yield_frame()
            if action_taken:
                # A pressed key can keep the poll path hot; yield once after
                # dispatch so a single step() never spins indefinitely.
                self._yield_frame()

    # ZX 0x6CD8..0x6CE0
    def control_icon_drawer(self, DE_icon: tuple[int, ...]) -> int:
        src_index = 0
        src_index = self.fn_control_icon_row_draw_loop(
            HL_dst=self._display_attr_ptr(0x5908),
            icon_bytes=DE_icon,
            src_index=src_index,
        )
        src_index = self.fn_control_icon_row_draw_loop(
            HL_dst=self._display_attr_ptr(0x5910),
            icon_bytes=DE_icon,
            src_index=src_index,
        )
        return src_index

    # ZX 0x6CE1..0x6CFD
    def fn_control_icon_row_draw_loop(
        self,
        HL_dst: BlockPtr,
        icon_bytes: tuple[int, ...],
        src_index: int,
    ) -> int:
        if src_index < 0 or (src_index + 0x10) > len(icon_bytes):
            raise ValueError(
                f"Control icon row source overrun: src_index={src_index}, len={len(icon_bytes)}",
            )
        HL_ptr = HL_dst
        idx = src_index
        for row in range(0x10):
            bits = icon_bytes[idx] & 0xFF
            idx += 0x01
            for _ in range(0x08):
                self._write_u8_ptr(HL_ptr, 0x94 if (bits & 0x80) else 0x00)
                bits = ((bits << 1) | (bits >> 7)) & 0xFF
                HL_ptr = HL_ptr.add(0x0001)
            if row != 0x0F:
                HL_ptr = HL_ptr.add(0x0018)
        return idx

    # ZX 0x6D10..0x6D71
    def define_keys_apply_routine(self):
        self.patch_control_scan_slot_1_port_word = self.const_define_key_slot_1_port_word.read_u16()
        self.patch_control_scan_slot_1_bit_opcode = self.const_define_key_slot_1_mask_byte.read_u8()
        self.patch_control_scan_slot_2_port_word = self.const_define_key_slot_2_port_word.read_u16()
        self.patch_control_scan_slot_2_bit_opcode = self.const_define_key_slot_2_mask_byte.read_u8()
        self.patch_control_scan_slot_3_port_word = self.const_define_key_slot_3_port_word.read_u16()
        self.patch_control_scan_slot_3_bit_opcode = self.const_define_key_slot_3_mask_byte.read_u8()
        self.patch_control_scan_slot_4_port_word = self.const_define_key_slot_4_port_word.read_u16()
        self.patch_control_scan_slot_4_bit_opcode = self.const_define_key_slot_4_mask_byte.read_u8()
        self.patch_control_scan_slot_5_port_word = self.const_define_key_slot_5_port_word.read_u16()
        self.patch_control_scan_slot_5_bit_opcode = self.const_define_key_slot_5_mask_byte.read_u8()
        self.patch_control_scan_slot_6_port_word = self.const_define_key_slot_6_port_word.read_u16()
        self.patch_control_scan_slot_6_bit_opcode = self.const_define_key_slot_6_mask_byte.read_u8()
        self.patch_control_scan_slot_6_prefix_opcode = 0xCB
        self.patch_control_scan_slot_6_branch_opcode = 0xCA
        self.fn_input_patch_preset_2()
        self.front_end_selection_commit(A_sel=0x00)

    # ZX 0x6D72..0x6D87
    def front_end_selection_commit(self, A_sel: int) -> None:
        self.var_menu_selection_index = A_sel & 0xFF
        HL_col = self._display_attr_ptr(0x594a)
        for i in range(0x0C):
            self._write_u8_ptr(HL_col, 0x00)
            if i != (0x0C - 1):
                HL_col = self._ptr_add(HL_col, 0x20)
        self.fn_front_end_selection_bars_redraw()

    # ZX 0x6D88..0x6DBF
    def control_preset_branch(self):
        self.patch_control_scan_slot_1_port_word = 0x00DF
        self.patch_control_scan_slot_2_port_word = 0x00DF
        self.patch_control_scan_slot_3_port_word = 0x00DF
        self.patch_control_scan_slot_4_port_word = 0x00DF
        self.patch_control_scan_slot_5_port_word = 0x00DF
        self.patch_control_scan_slot_4_bit_opcode = 0x47
        self.patch_control_scan_slot_3_bit_opcode = 0x4F
        self.patch_control_scan_slot_2_bit_opcode = 0x57
        self.patch_control_scan_slot_1_bit_opcode = 0x5F
        self.patch_control_scan_slot_5_bit_opcode = 0x67
        self.fn_input_patch_preset()
        # Kempston preset keeps secondary/use on a single ZX key-matrix bit
        # (SYMBOL SHIFT), while host/gamepad mapping feeds this virtual button.
        self.patch_control_scan_slot_6_port_word = 0x7FFE
        self.patch_control_scan_slot_6_prefix_opcode = 0xCB
        self.patch_control_scan_slot_6_bit_opcode = 0x4F
        self.patch_control_scan_slot_6_branch_opcode = 0xCA
        self.front_end_selection_commit(A_sel=0x02)

    # ZX 0x6DC0..0x6DFA
    def control_preset_branch_2(self):
        self.patch_control_scan_slot_3_port_word = 0xF7FE
        self.patch_control_scan_slot_3_bit_opcode = 0x67
        self.patch_control_scan_slot_5_port_word = 0xEFFE
        self.patch_control_scan_slot_4_port_word = 0xEFFE
        self.patch_control_scan_slot_2_port_word = 0xEFFE
        self.patch_control_scan_slot_1_port_word = 0xEFFE
        self.patch_control_scan_slot_5_bit_opcode = 0x47
        self.patch_control_scan_slot_2_bit_opcode = 0x67
        self.patch_control_scan_slot_1_bit_opcode = 0x5F
        self.patch_control_scan_slot_4_bit_opcode = 0x57
        self.fn_input_opcode_patch_tail()
        self.front_end_selection_commit(A_sel=0x03)

    # ZX 0x6DFB..0x6E32
    def control_preset_branch_3(self):
        self.patch_control_scan_slot_3_port_word = 0xF7FE
        self.patch_control_scan_slot_4_port_word = 0xF7FE
        self.patch_control_scan_slot_1_port_word = 0xF7FE
        self.patch_control_scan_slot_2_port_word = 0xF7FE
        self.patch_control_scan_slot_5_port_word = 0xF7FE
        self.patch_control_scan_slot_3_bit_opcode = 0x47
        self.patch_control_scan_slot_4_bit_opcode = 0x4F
        self.patch_control_scan_slot_2_bit_opcode = 0x57
        self.patch_control_scan_slot_1_bit_opcode = 0x5F
        self.patch_control_scan_slot_5_bit_opcode = 0x67
        self.fn_input_opcode_patch_tail()
        self.front_end_selection_commit(A_sel=0x01)

    # ZX 0x6E33..0x6E4B
    def fn_input_opcode_patch_tail(self):
        self.fn_input_patch_preset_2()
        self.fn_input_opcode_patch_tail_entry_6e36()

    # ZX 0x6E36..0x6E4B (callable fall-through entry used by 0x7135)
    def fn_input_opcode_patch_tail_entry_6e36(self):
        # Self-modifying opcode patch in original code (0xE13E/0xE144..0xE146).
        # In Python port we keep it as explicit patch state consumed by input logic.
        BC_slot_6_port = 0x7FFE
        A_prefix_opcode = 0xFE

        self.patch_control_scan_slot_6_port_word = BC_slot_6_port
        self.patch_control_scan_slot_6_prefix_opcode = A_prefix_opcode
        self.patch_control_scan_slot_6_bit_opcode = (A_prefix_opcode + 0x01) & 0xFF
        self.patch_control_scan_slot_6_branch_opcode = 0xC2

    # ZX 0x6E4C..0x6EA9
    def define_keys_setup_flow(self) -> None:
        self.fn_title_top_screen_setup()
        self.fn_blink_delay_two_phase_wait()
        self._wait_keyboard_release()
        for fn_icon, HL_port, HL_bit in [
            (self.fn_icon_selector_2, self.const_define_key_slot_1_port_word, self.const_define_key_slot_1_mask_byte),
            (self.fn_icon_selector_1, self.const_define_key_slot_2_port_word, self.const_define_key_slot_2_mask_byte),
            (self.fn_icon_selector_3, self.const_define_key_slot_3_port_word, self.const_define_key_slot_3_mask_byte),
            (self.fn_icon_selector_4, self.const_define_key_slot_4_port_word, self.const_define_key_slot_4_mask_byte),
            (self.fn_icon_selector_5, self.const_define_key_slot_5_port_word, self.const_define_key_slot_5_mask_byte),
            (self.fn_icon_selector_6, self.const_define_key_slot_6_port_word, self.const_define_key_slot_6_mask_byte),
        ]:
            fn_icon()
            A_bit, BC_port = self.fn_define_keys_wait_loop()
            typed_port = HL_port
            typed_mask = HL_bit
            if not isinstance(typed_port, StructFieldPtr) or not isinstance(typed_mask, StructFieldPtr):
                raise TypeError("define_keys_setup_flow expects StructFieldPtr fields for define-keys descriptors")
            typed_port.write_u16(BC_port)
            typed_mask.write_u8(A_bit)
            self._wait_keyboard_release()
        self.var_menu_selection_index = 0x00
        self.fn_title_screen_text_compositor()
        self.define_keys_apply_routine()

    # ZX 0x6EAA..0x6EAF
    def fn_icon_selector_3(self):
        DE_icon = self.const_control_icon_set_3
        return self.control_icon_drawer(DE_icon=DE_icon)

    # ZX 0x6EB0..0x6EB5
    def fn_icon_selector_4(self):
        DE_icon = self.const_control_icon_set_4
        return self.control_icon_drawer(DE_icon=DE_icon)

    # ZX 0x6EB6..0x6EBB
    def fn_icon_selector_1(self):
        DE_icon = self.const_control_icon_set_1
        return self.control_icon_drawer(DE_icon=DE_icon)

    # ZX 0x6EBC..0x6EC1
    def fn_icon_selector_2(self):
        DE_icon = self.const_control_icon_set_2
        return self.control_icon_drawer(DE_icon=DE_icon)

    # ZX 0x6EC2..0x6EC7
    def fn_icon_selector_5(self):
        DE_icon = self.const_control_icon_set_5
        return self.control_icon_drawer(DE_icon=DE_icon)

    # ZX 0x6EC8..0x6ECD
    def fn_icon_selector_6(self):
        DE_icon = self.const_control_icon_set_6
        return self.control_icon_drawer(DE_icon=DE_icon)

    # ZX 0x6ECE..0x6F18
    def fn_define_keys_wait_loop(self):
        if self._fsm_step_active:
            raise RuntimeError(
                "Legacy define-keys wait loop called during active FSM step; "
                "use FSM define-keys state instead",
            )
        probe_ports = (0xFEFE, 0xFDFE, 0xFBFE, 0xF7FE, 0xEFFE, 0xDFFE, 0xBFFE, 0x7FFE)
        while True:
            for BC_port in probe_ports:
                A_row = self.fn_input_probe_primitive(BC_port=BC_port)
                if A_row != 0xFF:
                    A_glyph = self.pressed_key_decoder(A_row=A_row)
                    return A_glyph, BC_port
            self._yield_frame()

    # ZX 0x6F19..0x6F1F
    def fn_input_probe_primitive(self, BC_port):
        A_row = (self.in_port(BC_port) | 0xE0) & 0xFF
        return A_row

    # ZX 0x6F20..0x6F2E
    def pressed_key_decoder(self, A_row):
        D_bits = A_row & 0xFF
        A_glyph = 0x47
        if D_bits & 0x01:
            # Entry carry comes from CP 0xFF in caller path and is set for A!=0xFF.
            carry = 0x01
            while D_bits & 0x01:
                D_bits, carry = self._rr(D_bits, carry)
                A_glyph = (A_glyph + 0x08) & 0xFF
        self.fn_blink_delay_two_phase_wait()
        return A_glyph

    # ZX 0x6F2F..0x6F45
    def fn_blink_delay_two_phase_wait(self):
        self._rom_beeper_sequence(
            (
                (0x0050, 0x01F4),
                (0x005A, 0x02BB),
            )
        )

    # ZX 0x6F46..0x6FAC
    def fn_high_score_table_draw_routine(self):
        self.fn_title_top_screen_setup()
        self.fn_compact_8x8_text_renderer()
        for row_idx in range(len(self.var_highscore_row_templates)):
            self.fn_stretched_text_symbol_stream_printer(
                HL_stream=self._highscore_row_ptr(row_idx),
                B_row=0x0C + (row_idx * 0x02),
                C_col=0x04,
            )
        self.fn_stretched_text_symbol_stream_printer(HL_stream=BlockPtr(self.str_highscore_header_stream, 0x0000), B_row=0x09, C_col=0x0A)
        self.fn_attribute_span_fill_helper(HL_dst=self._display_attr_ptr(0x5964), A_fill=0x07)
        self.fn_attribute_span_fill_helper(HL_dst=self._display_attr_ptr(0x5984), A_fill=0x05)
        self._fill_bytes_ptr(self._display_attr_ptr(0x5920), 0x40, 0x44)
        HL_attr = self._display_attr_ptr(0x5984)
        for i in range(0x0A):
            self._write_u8_ptr(HL_attr, 0x0F)
            if i != (0x0A - 1):
                HL_attr = HL_attr.add(0x20)

    # ZX 0x6FBC..0x70BF
    def high_score_editor_init(self):
        selected_row_index: int | None = None
        if self.fn_score_compare_helper(row_index=0):
            self.high_score_row_shift_helper_4()
            self.fn_high_score_row_shift_helper_3()
            self.fn_high_score_row_shift_helper_2()
            self.fn_high_score_row_shift_helper_1()
            selected_row_index = 0
        elif self.fn_score_compare_helper(row_index=1):
            self.high_score_row_shift_helper_4()
            self.fn_high_score_row_shift_helper_3()
            self.fn_high_score_row_shift_helper_2()
            selected_row_index = 1
        elif self.fn_score_compare_helper(row_index=2):
            self.high_score_row_shift_helper_4()
            self.fn_high_score_row_shift_helper_3()
            selected_row_index = 2
        elif self.fn_score_compare_helper(row_index=3):
            self.high_score_row_shift_helper_4()
            selected_row_index = 3
        elif self.fn_score_compare_helper(row_index=4):
            selected_row_index = 4
        else:
            return

        if selected_row_index is None:
            raise ValueError("High-score editor selected no row index")
        self.var_highscore_edit_row_index = selected_row_index
        hl_row = self._highscore_row_ptr(selected_row_index)
        self.var_highscore_name_edit_state = 0x00

        hl_ptr = hl_row.add(0x0002)
        for _ in range(0x0F):
            self._write_u8_ptr(hl_ptr, 0x0E)
            hl_ptr = hl_ptr.add(0x0001)

        ix_name = hl_row.add(0x0002)
        ix_score = hl_ptr.add(0x0001)
        score_digits = (
            self.var_runtime_aux_c8_lo & 0xFF,
            self.var_runtime_aux_c8_hi & 0xFF,
            self.var_runtime_aux_ca & 0xFF,
            self.var_runtime_aux_cb & 0xFF,
            self.var_runtime_aux_cc & 0xFF,
        )
        for i, src_digit in enumerate(score_digits):
            a_digit = (src_digit + 0x10) & 0xFF
            self._write_u8_ptr(ix_score, a_digit)
            if i != (len(score_digits) - 1):
                ix_score = ix_score.add(0x0001)

        self.fn_title_top_screen_setup()
        self.fn_stretched_text_symbol_stream_printer(
            HL_stream=BlockPtr(self.str_name_entry_prompt_stream, 0x0000),
            B_row=0x0A,
            C_col=0x08,
        )
        self.fn_routine_31_byte_row_fill_helper(HL_dst=self._display_attr_ptr(0x5940), A_fill=0x45)
        self.fn_routine_31_byte_row_fill_helper(HL_dst=self._display_attr_ptr(0x5960), A_fill=0x05)
        self.fn_routine_31_byte_row_fill_helper(HL_dst=self._display_attr_ptr(0x59e0), A_fill=0x05)
        self.fn_routine_31_byte_row_fill_helper(HL_dst=self._display_attr_ptr(0x5a00), A_fill=0x07)
        self.fn_compact_8x8_text_renderer()
        state = self.var_highscore_name_edit_state & 0xFF
        ix_name = ix_name.add(state)
        while True:
            hl_stream = self._highscore_row_ptr(self.var_highscore_edit_row_index)
            self.fn_stretched_text_symbol_stream_printer(HL_stream=hl_stream, B_row=0x0F, C_col=0x04)
            while True:
                A_key = self._rom_get_key_02bf()
                if A_key == 0xFF:
                    self._yield_frame()
                    continue
                if A_key == 0x20 or A_key >= 0x2F or A_key == 0x0C or A_key == 0x0D:
                    break
                self._yield_frame()
            if A_key == 0x0C:
                state = self.var_highscore_name_edit_state & 0xFF
                if state != 0x00:
                    state = (state - 0x01) & 0xFF
                    self.var_highscore_name_edit_state = state
                    ix_name = ix_name.add(-0x0001)
                    self._write_u8_ptr(ix_name, 0x0E)
                self._rom_beeper(de_ticks=0x0096, hl_period=0x0190)
                self._yield_frame()
                continue
            if A_key == 0x0D:
                return
            self._write_u8_ptr(ix_name, ((A_key & 0x7F) - 0x20) & 0xFF)
            ix_name = ix_name.add(0x0001)
            state = ((self.var_highscore_name_edit_state & 0xFF) + 0x01) & 0xFF
            self.var_highscore_name_edit_state = state
            if state == 0x0F:
                return
            self._rom_beeper(de_ticks=0x0096, hl_period=0x0190)
            self._yield_frame()

    # ZX 0x70C0..0x70CA
    def fn_routine_31_byte_row_fill_helper(self, HL_dst: BlockPtr, A_fill: int) -> None:
        self._fill_bytes_ptr(HL_dst, 0x1F, A_fill)

    # ZX 0x70CB..0x70DA
    def high_score_row_shift_helper_4(self):
        self._copy_high_score_row_payload(src_row_index=3, dst_row_index=4)

    # ZX 0x70DB..0x70E2
    def fn_high_score_row_shift_helper_3(self):
        self._copy_high_score_row_payload(src_row_index=2, dst_row_index=3)

    # ZX 0x70E3..0x70EA
    def fn_high_score_row_shift_helper_2(self):
        self._copy_high_score_row_payload(src_row_index=1, dst_row_index=2)

    # ZX 0x70EB..0x70F2
    def fn_high_score_row_shift_helper_1(self):
        self._copy_high_score_row_payload(src_row_index=0, dst_row_index=1)

    def _copy_high_score_row_payload(self, src_row_index: int, dst_row_index: int) -> None:
        payload = self._read_bytes(self._highscore_row_ptr(src_row_index).add(0x0002), 0x17)
        self._write_bytes_ptr(self._highscore_row_ptr(dst_row_index).add(0x0002), payload)

    # ZX 0x70F3..0x710F
    def fn_score_compare_helper(self, row_index: int) -> int:
        row_digits = self._read_bytes(self._highscore_row_score_ptr(row_index), 0x05)
        score_digits = (
            self.var_runtime_aux_c8_lo & 0xFF,
            self.var_runtime_aux_c8_hi & 0xFF,
            self.var_runtime_aux_ca & 0xFF,
            self.var_runtime_aux_cb & 0xFF,
            self.var_runtime_aux_cc & 0xFF,
        )
        for i in range(0x05):
            cur = (score_digits[i] + 0x10) & 0xFF
            row = row_digits[i]
            if row < cur:
                return 1
            if row > cur:
                return 0
        return 0

    # ZX 0x7123..0x7134
    def fn_front_end_two_step_beeper_cadence(self):
        self._rom_beeper_sequence(
            (
                (0x0032, 0x0032),
                (0x0064, 0x0064),
            )
        )

    # ZX 0x7135..0x713E
    def fn_input_patch_preset(self):
        self.fn_input_patch_writer_apply(A_op=0xC2, D_tail=0xC4)
        self.fn_input_opcode_patch_tail_entry_6e36()

    # ZX 0x713F..0x7142
    def fn_input_patch_preset_2(self):
        self.fn_input_patch_writer_apply(A_op=0xCA, D_tail=0xCC)

    # ZX 0x7143..0x7154
    def fn_input_patch_writer_apply(self, A_op, D_tail):
        op = A_op & 0xFF
        tail = D_tail & 0xFF
        self.patch_control_scan_slot_3_branch_opcode = op
        self.patch_control_scan_slot_4_branch_opcode = op
        self.patch_control_scan_slot_1_branch_opcode = op
        self.patch_control_scan_slot_2_branch_opcode = op
        self.patch_control_scan_slot_5_action_opcode = tail

    # ZX 0xA38E..0xA594
    def fn_main_pseudo_3d_map_render_pipeline(self) -> None:
        self._interrupts_enabled = False
        renderer_fill_counters = self.var_renderer_fill_counters
        renderer_fill_counters.counter_0 = 0x0E
        renderer_fill_counters.counter_1 = 0x25
        de_stage = BlockPtr(
            self.var_renderer_workspace,
            RENDERER_WORKSPACE_OFF_VISIBLE_CELL_STAGING_LATTICE,
        )
        hl_map = self.var_runtime_current_cell_ptr.add(-0x0040)
        c_col = self.var_current_map_coords.col & 0xFF
        b_row = self.var_current_map_coords.row & 0xFF
        b_row = (b_row - 0x01) & 0xFF
        c_col = (c_col - 0x0E) & 0xFF
        zigzag_phase = 0x00

        while True:
            b_saved = b_row
            c_saved = c_col
            hl_saved = hl_map
            de_saved = de_stage

            renderer_fill_counters.counter_0 = 0x0E
            while True:
                if b_row < 0x32 and c_col < 0x32:
                    a_cell = self._read_u8_ptr(hl_map)
                else:
                    a_cell = 0x00

                self._write_u8_ptr(de_stage, a_cell)
                de_stage = de_stage.add(0x0001)
                hl_map = hl_map.add(-0x0031)
                b_row = (b_row - 0x01) & 0xFF
                c_col = (c_col + 0x01) & 0xFF

                fill_counter_0 = ((renderer_fill_counters.counter_0 & 0xFF) - 0x01) & 0xFF
                if fill_counter_0 == 0x00:
                    break
                renderer_fill_counters.counter_0 = fill_counter_0

            b_row = b_saved
            c_col = c_saved
            hl_map = hl_saved
            de_stage = de_saved.add(0x0010)

            zigzag_phase ^= 0x01
            if zigzag_phase == 0x00:
                # The renderer consumes the staging lattice in 0x10-byte rows, with an
                # alternating 0/1 column offset (see _advance_to_next_cell_in_strip).
                # After emitting a +1 shifted row, we must shift the next row start back
                # by -1; otherwise the write cursor drifts and the renderer reads stale
                # bytes (manifesting as random/"changing" blocks and wrong sprites).
                de_stage = de_stage.add(-0x0001)
                b_row = (b_row + 0x01) & 0xFF
                hl_map = hl_map.add(0x0032)
            else:
                de_stage = de_stage.add(0x0001)
                c_col = (c_col + 0x01) & 0xFF
                hl_map = hl_map.add(0x0001)

            fill_counter_1 = ((renderer_fill_counters.counter_1 & 0xFF) - 0x01) & 0xFF
            if fill_counter_1 == 0x00:
                break
            renderer_fill_counters.counter_1 = fill_counter_1

        self._render_from_visible_cell_staging_lattice()

    def _render_from_visible_cell_staging_lattice(self) -> None:
        hl_stage = BlockPtr(
            self.var_renderer_workspace,
            RENDERER_WORKSPACE_OFF_VISIBLE_CELL_STAGING_LATTICE,
        )
        de_cell = BlockPtr(
            self.var_renderer_workspace,
            RENDERER_WORKSPACE_OFF_CELL_BLIT_WORK_BUFFER,
        )
        self.var_renderer_staging_cursor_ptr = hl_stage
        state = RenderStripState(
            hl_stage=hl_stage,
            de_dst=de_cell,
            c_lane=0x00,
            b_rows=0x25,
            row_base=de_cell,
            alt_phase=0x00,
        )

        while state.b_rows != 0x00:
            a_code = self._read_u8_ptr(state.hl_stage)
            if a_code == 0x00:
                self._advance_to_next_cell_in_strip(state)
                continue
            if a_code == 0x17:
                self.special_code_23_path(DE_dst=state.de_dst, state=state)
                continue
            if a_code == 0x57:
                self.special_code_87_path(DE_dst=state.de_dst, state=state)
                continue
            if a_code == 0xD7:
                self.special_code_215_path(DE_dst=state.de_dst, state=state)
                continue
            if a_code == 0x97:
                self.special_code_151_path(DE_dst=state.de_dst, state=state)
                continue
            if (a_code & 0x40) != 0x00:
                self.bit6_path(A_code=a_code, DE_dst=state.de_dst, state=state)
                continue
            if (a_code & 0x80) != 0x00:
                self.bit7_path(A_code=a_code, DE_dst=state.de_dst, state=state)
                continue

            self.fn_generic_sprite_blitter(A_idx=a_code, DE_dst=state.de_dst)
            self._advance_to_next_cell_in_strip(state)

        self.viewport_strip_blit_core(
            HL_src=BlockPtr(
                self.var_renderer_workspace,
                RENDERER_WORKSPACE_OFF_LINEAR_VIEWPORT_WORK_BUFFER,
            ),
            DE_dst=BlockPtr(self.var_display_bitmap_ram, self.var_display_bitmap_strip_dst_anchor_4021),
            A_passes=0x02,
        )

    # ZX 0xA595..0xA5C7
    def viewport_strip_blit_core(self, HL_src: BlockPtr, DE_dst: BlockPtr, A_passes: int) -> None:
        hl_src = HL_src
        de_dst = DE_dst
        passes = A_passes & 0xFF

        while passes != 0x00:
            while True:
                hl_src = hl_src.add(0x0001)
                for _ in range(0x1A):
                    self._write_u8_ptr(de_dst, self._read_u8_ptr(hl_src))
                    hl_src = hl_src.add(0x0001)
                    de_dst = de_dst.add(0x0001)

                hl_src = hl_src.add(0x0005)
                de_dst = de_dst.add(0x0004)

                hl_src_local = hl_src.index - RENDERER_WORKSPACE_OFF_LINEAR_VIEWPORT_WORK_BUFFER
                if (hl_src_local & 0x00E0) != 0x0000:
                    de_dst = de_dst.add(0x00E2)
                    continue

                de_dst = de_dst.add(0x0002)
                # Original ZX routine tested H bits on absolute source address in 0x9100-page.
                hl_src_zx = (hl_src_local + 0x9100) & 0xFFFF
                if ((hl_src_zx >> 8) & 0x07) == 0x00:
                    break

                # Original DE high-byte adjust also operates on ZX bitmap absolute addresses.
                de_dst_zx = (de_dst.index + 0x4000) & 0xFFFF
                de_hi = ((de_dst_zx >> 8) + 0xF9) & 0xFF
                de_dst_zx = ((de_hi << 8) | (de_dst_zx & 0x00FF)) & 0xFFFF
                de_dst = de_dst.with_index((de_dst_zx - 0x4000) & 0xFFFF)

            passes = (passes - 0x01) & 0xFF

        self._fill_linear_viewport_stack_window_via_sp_switch()

    def _fill_linear_viewport_stack_window_via_sp_switch(self) -> None:
        words = (
            getattr(self, "patch_viewport_fill_word_1", 0x0660) & 0xFFFF,
            getattr(self, "patch_viewport_fill_word_2", 0x1818) & 0xFFFF,
            getattr(self, "patch_viewport_fill_word_3", 0x6006) & 0xFFFF,
            getattr(self, "patch_viewport_fill_word_4", 0x8001) & 0xFFFF,
            getattr(self, "patch_viewport_fill_word_5", 0x6006) & 0xFFFF,
            getattr(self, "patch_viewport_fill_word_6", 0x1818) & 0xFFFF,
            getattr(self, "patch_viewport_fill_word_7", 0x0660) & 0xFFFF,
            getattr(self, "patch_viewport_fill_word_8", 0x0180) & 0xFFFF,
        )

        sp = self._linear_viewport_stack_fill_top_ptr()
        for _ in range(0x0F):
            for word in words:
                hi = (word >> 8) & 0xFF
                lo = word & 0xFF
                for _ in range(0x10):
                    sp = sp.add(-0x0001)
                    self._write_u8_ptr(sp, hi)
                    sp = sp.add(-0x0001)
                    self._write_u8_ptr(sp, lo)

    # ZX 0xA66F..0xA759
    def fn_frequent_cube_blit_fast_path(self, DE_dst: BlockPtr) -> None:
        mask_pairs = self._cube_fast_mask_pairs
        if len(mask_pairs) != 0x20:
            raise ValueError(f"Expected 32 mask pairs, got {len(mask_pairs)}")
        row_offsets = (0x0000, 0x0001, 0x0101, 0x0100)
        for step, (and_mask, or_mask) in enumerate(mask_pairs):
            row_base = DE_dst.add((step // 4) * 0x20)
            cell_ptr = row_base.add(row_offsets[step % 4])
            cur = self._read_u8_ptr(cell_ptr)
            self._write_u8_ptr(cell_ptr, (cur & and_mask) | or_mask)

    # ZX 0xA75A..0xA75F
    def special_code_23_path(self, DE_dst: BlockPtr, state: RenderStripState | None = None) -> None:
        self.fn_frequent_cube_blit_fast_path(DE_dst=DE_dst)
        if state is not None:
            self._advance_to_next_cell_in_strip(state)

    def _advance_to_next_cell_in_strip(self, state: RenderStripState) -> None:
        if state.c_lane < 0x19:
            state.c_lane = (state.c_lane + 0x02) & 0xFF
            state.de_dst = state.de_dst.add(0x0002)
            state.hl_stage = state.hl_stage.add(0x0001)
            return

        state.row_base = state.row_base.add(0x0080)
        state.alt_phase ^= 0x01
        state.c_lane = state.alt_phase

        hl_cursor = self.var_renderer_staging_cursor_ptr.add(0x0010)
        self.var_renderer_staging_cursor_ptr = hl_cursor

        state.hl_stage = hl_cursor.add(state.c_lane)
        state.de_dst = state.row_base.add(state.c_lane)
        state.b_rows = (state.b_rows - 0x01) & 0xFF

    # ZX 0xA760..0xA772
    def bit6_path(self, A_code: int, DE_dst: BlockPtr, state: RenderStripState | None = None) -> None:
        if A_code != 0x40:
            self.fn_generic_sprite_blitter(A_idx=(A_code & 0xBF), DE_dst=DE_dst)
        self.fn_frequent_cube_blit_fast_path(DE_dst=DE_dst.add(-0x0100))
        if state is not None:
            self._advance_to_next_cell_in_strip(state)

    # ZX 0xA773..0xA786
    def bit7_path(self, A_code: int, DE_dst: BlockPtr, state: RenderStripState | None = None) -> None:
        if A_code != 0x80:
            self.fn_generic_sprite_blitter(A_idx=(A_code & 0x7F), DE_dst=DE_dst)
        self.fn_frequent_cube_blit_fast_path(DE_dst=DE_dst.add(-0x0200))
        if state is not None:
            self._advance_to_next_cell_in_strip(state)

    # ZX 0xA787..0xA792
    def special_code_87_path(self, DE_dst: BlockPtr, state: RenderStripState | None = None) -> None:
        self.fn_frequent_cube_blit_fast_path(DE_dst=DE_dst)
        DE_lvl1 = DE_dst.add(-0x0100)
        self.fn_frequent_cube_blit_fast_path(DE_dst=DE_lvl1)
        if state is not None:
            self._advance_to_next_cell_in_strip(state)

    # ZX 0xA793..0xA7A4
    def special_code_151_path(self, DE_dst: BlockPtr, state: RenderStripState | None = None) -> None:
        self.fn_frequent_cube_blit_fast_path(DE_dst=DE_dst)
        DE_lvl1 = DE_dst.add(-0x0100)
        self.fn_frequent_cube_blit_fast_path(DE_dst=DE_lvl1)
        DE_lvl2 = DE_dst.add(-0x0200)
        self.fn_frequent_cube_blit_fast_path(DE_dst=DE_lvl2)
        if state is not None:
            self._advance_to_next_cell_in_strip(state)

    # ZX 0xA7A5..0xA7B4
    def special_code_215_path(self, DE_dst: BlockPtr, state: RenderStripState | None = None) -> None:
        self.fn_generic_sprite_blitter(A_idx=0x15, DE_dst=DE_dst)
        DE_lvl1 = DE_dst.add(-0x0100)
        self.fn_generic_sprite_blitter(A_idx=0x16, DE_dst=DE_lvl1)
        if state is not None:
            self._advance_to_next_cell_in_strip(state)

    # ZX 0xA7B5..0xA7FD
    def _resolve_sprite_mask_slot_ptr(self, sprite_idx: int) -> BlockPtr:
        idx = sprite_idx & 0xFF
        if idx == 0x00:
            raise ValueError("Sprite mask slot 0 is not representable as contiguous typed block")

        slot_off = (idx - 0x01) * 0x40
        bank_len = len(self.var_active_sprite_subset_bank)
        if slot_off < bank_len:
            return BlockPtr(self.var_active_sprite_subset_bank, slot_off)

        cont_off = slot_off - bank_len
        if cont_off < len(self.const_sprite_table_continuation):
            return BlockPtr(self.const_sprite_table_continuation, cont_off)
        raise ValueError(f"Sprite mask slot out of range: idx=0x{idx:02X}")

    def fn_generic_sprite_blitter(self, A_idx: int, DE_dst: BlockPtr) -> None:
        src_ptr = self._resolve_sprite_mask_slot_ptr(A_idx)
        row_offsets = (0x0000, 0x0001, 0x0101, 0x0100)
        for row in range(0x08):
            row_base = DE_dst.add(row * 0x20)
            for off in row_offsets:
                and_mask = self._read_u8_ptr(src_ptr)
                src_ptr = src_ptr.add(0x01)
                or_mask = self._read_u8_ptr(src_ptr)
                src_ptr = src_ptr.add(0x01)
                cell_ptr = row_base.add(off)
                cur = self._read_u8_ptr(cell_ptr)
                self._write_u8_ptr(cell_ptr, (cur & and_mask) | or_mask)

    # ZX 0xA7FE..0xA853
    def fn_floor_texture_selector_pattern_setup_active(self) -> None:
        A_mode = self.var_active_map_mode & 0xFF
        if A_mode <= 0x02:
            words = self.const_floor_pattern_words_by_mode[A_mode]
        else:
            words = self.const_floor_pattern_mode_2_words
        if len(words) != 0x08:
            raise ValueError(f"Decoded floor-pattern words must have len=8, got {len(words)}")

        self.patch_viewport_fill_word_1 = words[0]
        self.patch_viewport_fill_word_2 = words[1]
        self.patch_viewport_fill_word_3 = words[2]
        self.patch_viewport_fill_word_4 = words[3]
        self.patch_viewport_fill_word_5 = words[4]
        self.patch_viewport_fill_word_6 = words[5]
        self.patch_viewport_fill_word_7 = words[6]
        self.patch_viewport_fill_word_8 = words[7]
        self.fn_patches_immediate_operands_routine_xa66f_sprite()
        self._interrupts_enabled = False
        return self._fill_linear_viewport_stack_window_via_sp_switch()

    # ZX 0xA889..0xA88C
    def fn_render_pass_re_entry_stub(self):
        self._interrupts_enabled = False
        return self._render_from_visible_cell_staging_lattice()

    # ZX 0xA88D..0xA8B1
    def fn_patches_immediate_operands_routine_xa66f_sprite(self):
        src = self._read_bytes(self._active_sprite_patch_source_ptr(), 0x40)
        self._cube_fast_mask_pairs = [(src[i], src[i + 1]) for i in range(0, 0x40, 2)]

    # ZX 0xE0A6..0xE0BF
    def fn_gameplay_movement_control_step(self) -> None:
        movement_opcode = self.patch_gameplay_movement_step_opcode & 0xFF
        if movement_opcode == 0xC9:
            return
        if movement_opcode != 0x3A:
            raise ValueError(
                f"Unsupported gameplay movement step entry opcode: 0x{movement_opcode:02X}",
            )

        def _bit_index_from_opcode(opcode: int) -> int:
            table = {
                0x47: 0, 0x4F: 1, 0x57: 2, 0x5F: 3,
                0x67: 4, 0x6F: 5, 0x77: 6, 0x7F: 7,
            }
            if opcode not in table:
                raise ValueError(f"Unsupported BIT opcode byte: 0x{opcode:02X}")
            return table[opcode]

        def _branch_on_z(opcode: int, z_flag: bool) -> bool:
            if opcode in (0xCA, 0xCC):  # JP Z / CALL Z
                return z_flag
            if opcode in (0xC2, 0xC4):  # JP NZ / CALL NZ
                return not z_flag
            raise ValueError(f"Unsupported branch opcode byte: 0x{opcode:02X}")

        def _scan_bit_slot(*, port_word: int, bit_opcode: int, branch_opcode: int) -> bool:
            a_in = self.in_port(port_word & 0xFFFF) & 0xFF
            bit_index = _bit_index_from_opcode(bit_opcode & 0xFF)
            z_flag = ((a_in >> bit_index) & 0x01) == 0x00
            return _branch_on_z(branch_opcode & 0xFF, z_flag)

        move_state = self.var_runtime_move_state_code & 0xFF
        if move_state != 0x1C:
            self.move_commit_branch_special_cell_codes(A_code=move_state)
            return

        hl_cell = self.var_runtime_current_cell_ptr
        a_cell = self._read_u8_ptr(hl_cell) & 0x3F
        if a_cell == 0x38 or (0x01 <= a_cell <= 0x14):
            self.state_29_handler()
            return

        if _scan_bit_slot(
            port_word=self.patch_control_scan_slot_4_port_word,
            bit_opcode=self.patch_control_scan_slot_4_bit_opcode,
            branch_opcode=self.patch_control_scan_slot_4_branch_opcode,
        ):
            if not self.movement_attempt_map_offset_1_enters():
                return
        elif _scan_bit_slot(
            port_word=self.patch_control_scan_slot_3_port_word,
            bit_opcode=self.patch_control_scan_slot_3_bit_opcode,
            branch_opcode=self.patch_control_scan_slot_3_branch_opcode,
        ):
            if not self.movement_attempt_map_offset_1_enters_2():
                return
        elif _scan_bit_slot(
            port_word=self.patch_control_scan_slot_1_port_word,
            bit_opcode=self.patch_control_scan_slot_1_bit_opcode,
            branch_opcode=self.patch_control_scan_slot_1_branch_opcode,
        ):
            if not self.movement_attempt_map_offset_50_move():
                return
        elif _scan_bit_slot(
            port_word=self.patch_control_scan_slot_2_port_word,
            bit_opcode=self.patch_control_scan_slot_2_bit_opcode,
            branch_opcode=self.patch_control_scan_slot_2_branch_opcode,
        ):
            if not self.movement_attempt_map_offset_50_enters():
                return

        if _scan_bit_slot(
            port_word=self.patch_control_scan_slot_5_port_word,
            bit_opcode=self.patch_control_scan_slot_5_bit_opcode,
            branch_opcode=self.patch_control_scan_slot_5_action_opcode,
        ):
            self.action_effect_dispatcher_keyed_xa8dc_bits()

        a_delta = self.var_runtime_move_delta & 0xFF
        a_prev = self.var_movement_hud_shared_state & 0xFF
        if a_delta != a_prev:
            for off in range(0x04):
                self._write_u8_ptr(self._ptr_add(self._display_attr_ptr(0x5a7c), off), 0x00)
                self._write_u8_ptr(self._ptr_add(self._display_attr_ptr(0x5a9c), off), 0x00)

            if a_delta == 0x01:
                hl_mark = self._display_attr_ptr(0x5a9e)
            elif a_delta == 0xFF:
                hl_mark = self._display_attr_ptr(0x5a7c)
            elif a_delta == 0xCE:
                hl_mark = self._display_attr_ptr(0x5a7e)
            else:
                hl_mark = self._display_attr_ptr(0x5a9c)

            self._write_u8_ptr(hl_mark, 0x06)
            self._write_u8_ptr(self._ptr_add(hl_mark, 0x01), 0x06)
            self.var_movement_hud_shared_state = a_delta & 0xFF

        a6 = (self.in_port(self.patch_control_scan_slot_6_port_word & 0xFFFF) | 0xE0) & 0xFF
        slot6_prefix = self.patch_control_scan_slot_6_prefix_opcode & 0xFF
        slot6_arg = self.patch_control_scan_slot_6_bit_opcode & 0xFF
        slot6_branch = self.patch_control_scan_slot_6_branch_opcode & 0xFF
        if slot6_prefix == 0xCB:
            bit_index = _bit_index_from_opcode(slot6_arg)
            z_slot6 = ((a6 >> bit_index) & 0x01) == 0x00
        elif slot6_prefix == 0xFE:
            z_slot6 = (a6 == slot6_arg)
        else:
            raise ValueError(f"Unsupported slot6 prefix opcode byte: 0x{slot6_prefix:02X}")

        if _branch_on_z(slot6_branch, z_slot6):
            self.fn_gameplay_movement_overlay_step_entry_e14c()
            return
        self.fn_gameplay_movement_step_core()

    # ZX 0xE14C..0xE1C5 (internal entry used by 0xE146 and 0xF5AD)
    def fn_gameplay_movement_overlay_step_entry_e14c(self) -> None:
        def _paint_4x4_attr_marker(HL_dst: BlockPtr, A_fill: int) -> None:
            fill = A_fill & 0xFF
            for off in (0x00, 0x01, 0x02, 0x03, 0x20, 0x23, 0x40, 0x43, 0x60, 0x61, 0x62, 0x63):
                self._write_u8_ptr(self._ptr_add(HL_dst, off), fill)

        a_flags = self.var_action_effect_flags & 0xFF
        if a_flags & 0x10:
            hl_dst = self._display_attr_ptr(0x591c)
            hl_src = self._display_attr_ptr(0x599c)
        elif a_flags & 0x01:
            hl_dst = self._display_attr_ptr(0x581c)
            hl_src = self._display_attr_ptr(0x589c)
        elif a_flags & 0x04:
            hl_dst = self._display_attr_ptr(0x589c)
            hl_src = self._display_attr_ptr(0x591c)
        else:
            hl_dst = self._display_attr_ptr(0x599c)
            hl_src = self._display_attr_ptr(0x581c)

        _paint_4x4_attr_marker(HL_dst=hl_dst, A_fill=0x20)
        _paint_4x4_attr_marker(HL_dst=hl_src, A_fill=0x38)
        self.var_action_effect_flags = ((a_flags << 2) | (a_flags >> 6)) & 0xFF
        self.fn_gameplay_movement_step_core()

    # ZX 0xE1C6..0xE223
    def fn_gameplay_movement_step_core(self) -> None:
        hud_cache = self.var_hud_bar_cache
        queue_a = self.var_transient_queue_a
        queue_b = self.var_transient_queue_b
        queue_c = self.var_transient_queue_c

        A_now = self.var_runtime_progress_counter & 0xFF
        C_old = hud_cache.progress & 0xFF
        A_now = self.fn_hud_bar_updater(
            HL_bar=self._display_attr_ptr(0x5ac5),
            A_new=A_now,
            C_old=C_old,
            B_fill=0x0F,
        )
        hud_cache.progress = A_now & 0xFF

        A_flags = self.var_action_effect_flags & 0xFF
        if A_flags & 0x40:
            A_now = self.fn_hud_bar_updater(
                HL_bar=self._display_attr_ptr(0x5af5),
                A_new=queue_c.free_slots & 0xFF,
                C_old=hud_cache.queue_c & 0xFF,
                B_fill=0x07,
            )
            hud_cache.queue_c = A_now & 0xFF
            return
        if A_flags & 0x10:
            A_now = self.fn_hud_bar_updater(
                HL_bar=self._display_attr_ptr(0x5ad5),
                A_new=queue_b.free_slots & 0xFF,
                C_old=hud_cache.queue_b & 0xFF,
                B_fill=0x06,
            )
            hud_cache.queue_b = A_now & 0xFF
            return
        if A_flags & 0x04:
            A_now = self.fn_hud_bar_updater(
                HL_bar=self._display_attr_ptr(0x5ae5),
                A_new=queue_a.free_slots & 0xFF,
                C_old=hud_cache.queue_a & 0xFF,
                B_fill=0x05,
            )
            hud_cache.queue_a = A_now & 0xFF

    # ZX 0xE224..0xE238
    def fn_hud_bar_updater(self, HL_bar, A_new, C_old, B_fill):
        A_new = A_new & 0xFF
        C_old = C_old & 0xFF
        B_fill = B_fill & 0xFF

        if A_new == C_old:
            return A_new

        bar_ptr = self._normalize_map_ptr(HL_bar)
        dst, start = bar_ptr.array, bar_ptr.index
        if A_new >= C_old:
            cast(bytearray, dst)[start + A_new] = B_fill
            return A_new

        if A_new != 0x00:
            cast(bytearray, dst)[start + A_new] = B_fill
        cast(bytearray, dst)[start + A_new + 1] = 0x00
        return A_new

    # ZX 0xE239..0xE261
    def fn_rebuild_hud_meter_bars_counters_xa8c4(self):
        queue_b = self.var_transient_queue_b
        queue_a = self.var_transient_queue_a
        queue_c = self.var_transient_queue_c

        self.fn_rebuild_hud_meter_bars_core(
            HL_bar=self._display_attr_ptr(0x5ac6),
            A_len=(self.var_runtime_progress_counter & 0xFF),
            E_fill=0x0F,
        )
        self.fn_rebuild_hud_meter_bars_core(
            HL_bar=self._display_attr_ptr(0x5ad6),
            A_len=queue_b.free_slots & 0xFF,
            E_fill=0x06,
        )
        self.fn_rebuild_hud_meter_bars_core(
            HL_bar=self._display_attr_ptr(0x5ae6),
            A_len=queue_a.free_slots & 0xFF,
            E_fill=0x05,
        )
        self.fn_rebuild_hud_meter_bars_core(
            HL_bar=self._display_attr_ptr(0x5af6),
            A_len=queue_c.free_slots & 0xFF,
            E_fill=0x07,
        )

    # ZX 0xE262..0xE27A
    def fn_rebuild_hud_meter_bars_core(self, HL_bar, A_len, E_fill):
        A_count = A_len & 0xFF
        fill = E_fill & 0xFF

        self._fill_bytes_ptr(HL_bar, 0x0A, 0x00)
        if A_count == 0x00:
            return
        self._fill_bytes_ptr(HL_bar, A_count, fill)
        self._rom_beeper(de_ticks=0x0032, hl_period=0x0032)

    def _movement_commit_shared(self, HL_cell: BlockPtr, DE_step: int, B_mark: int) -> None:
        hl_cell = self._normalize_map_ptr(HL_cell)
        de_step = DE_step & 0xFFFF
        de_step_signed = self._u16_to_signed(de_step)
        b_mark = B_mark & 0xFF

        self.var_runtime_current_cell_ptr = hl_cell

        cell = self._read_u8_ptr(hl_cell)
        self._write_u8_ptr(hl_cell, (cell & 0xC0) | b_mark)

        hl_prev = hl_cell.add(-de_step_signed)
        prev = self._read_u8_ptr(hl_prev)
        self._write_u8_ptr(hl_prev, prev & 0xC0)

        e_step = de_step & 0xFF
        self.var_current_map_coords.apply_step_low_byte(e_step)

    # ZX 0xE27B..0xE282
    def movement_attempt_map_offset_1_enters(self) -> bool:
        return self.movement_attempt_map_offset_50_move(DE_step=0x0001, B_mark=0x22)

    # ZX 0xE283..0xE28A
    def movement_attempt_map_offset_50_enters(self) -> bool:
        return self.movement_attempt_map_offset_50_move(DE_step=0x0032, B_mark=0x23)

    # ZX 0xE28B..0xE292
    def movement_attempt_map_offset_1_enters_2(self) -> bool:
        return self.movement_attempt_map_offset_50_move(DE_step=0xFFFF, B_mark=0x21)

    # ZX 0xE293..0xE31A
    def movement_attempt_map_offset_50_move(self, DE_step: int = 0xFFCE, B_mark: int = 0x24) -> bool:
        de_step = DE_step & 0xFFFF
        de_step_signed = self._u16_to_signed(de_step)
        b_mark = B_mark & 0xFF

        hl_dst = self.var_runtime_current_cell_ptr
        self.var_move_marker_code_scratch = b_mark & 0xFF
        self.var_runtime_move_delta = de_step
        hl_dst = hl_dst.add(de_step_signed)

        a_code = self._read_u8_ptr(hl_dst) & 0x3F
        if a_code == 0x00:
            self._movement_commit_shared(HL_cell=hl_dst, DE_step=de_step, B_mark=b_mark)
            return True

        if a_code < 0x15:
            self.alternate_movement_commit_path_low_cell(
                HL_cell=hl_dst,
                DE_delta=de_step,
                B_marker=b_mark,
            )
            # ASM path jumps to state_29_handler and exits movement-control step.
            return False

        if a_code == 0x18:
            hl_probe = hl_dst.add(de_step_signed)
            if (self._read_u8_ptr(hl_probe) & 0x3F) != 0x00:
                return True
            probe = self._read_u8_ptr(hl_probe)
            self._write_u8_ptr(hl_probe, (probe & 0xC0) | 0x18)
            hl_cell = hl_probe.add(-de_step_signed)
            self._movement_commit_shared(HL_cell=hl_cell, DE_step=de_step, B_mark=b_mark)
            return True

        if a_code < 0x1B:
            return True

        if a_code < 0x1D:
            self._movement_commit_shared(HL_cell=hl_dst, DE_step=de_step, B_mark=b_mark)
            return True

        if a_code == 0x25:
            self.special_move_branch(HL_cell=hl_dst, DE_step=de_step, B_mark=b_mark)
            return True

        if a_code < 0x2A or a_code == 0x38:
            return True

        self._movement_commit_shared(HL_cell=hl_dst, DE_step=de_step, B_mark=b_mark)
        return True

    # ZX 0xE31B..0xE340
    def countdown_driven_marker_updater_one_cell(self) -> None:
        progress = self.var_runtime_progress_counter & 0xFF
        if progress == 0x00:
            return

        HL_cur = self.var_runtime_current_cell_ptr
        DE_step = self.var_runtime_move_delta & 0xFFFF
        DE_step_signed = self._u16_to_signed(DE_step)
        HL_prev = HL_cur.add(-DE_step_signed)

        cell = self._read_u8_ptr(HL_prev)
        if (cell & 0x3F) != 0x00:
            return

        self._write_u8_ptr(HL_prev, (cell & 0xC0) | 0x25)
        self.var_runtime_progress_counter = (progress - 0x01) & 0xFF
        self._rom_beeper(de_ticks=0x0005, hl_period=0x0005)

    # ZX 0xE341..0xE359
    def special_move_branch(self, HL_cell: BlockPtr, DE_step: int, B_mark: int) -> None:
        progress = self.var_runtime_progress_counter & 0xFF
        self.var_runtime_progress_counter = (progress + 0x01) & 0xFF
        self._rom_beeper(de_ticks=0x0007, hl_period=0x000A)
        self._movement_commit_shared(HL_cell=HL_cell, DE_step=DE_step, B_mark=B_mark)

    # ZX 0xE35A..0xE377
    def state_29_handler(self):
        self.var_runtime_move_state_code = 0x1D
        HL_cell = self.var_runtime_current_cell_ptr
        A_cell = self._read_u8_ptr(HL_cell)
        self._write_u8_ptr(HL_cell, (A_cell & 0xC0) | 0x1D)
        self._queue_teleport_audio_frame_burst(de_ticks=0x0014, hl_period=0x01F4)
        self.var_runtime_objective_counter = ((self.var_runtime_objective_counter & 0xFF) - 0x01) & 0xFF
        return self.fn_hud_strip_painter()

    # ZX 0xE378..0xE3AC
    def move_commit_branch_special_cell_codes(self, A_code: int) -> None:
        a_code = A_code & 0xFF
        hl_cell = self.var_runtime_current_cell_ptr
        if a_code != 0x21:
            cell = self._read_u8_ptr(hl_cell)
            self._write_u8_ptr(hl_cell, (cell & 0xC0) | a_code)
            state = self.var_runtime_move_state_code & 0xFF
            self.var_runtime_move_state_code = (state + 0x01) & 0xFF
            self._queue_teleport_audio_frame_burst(de_ticks=0x000F, hl_period=0x0190)
            return

        self.var_runtime_move_state_code = 0x1C
        cell = self._read_u8_ptr(hl_cell)
        if (cell & 0x3F) < 0x15:
            self.state_29_handler()
            return

        marker = self.var_move_marker_code_scratch & 0xFF
        self._write_u8_ptr(hl_cell, (cell & 0xC0) | marker)

    # ZX 0xE3AE..0xE3E8
    def alternate_movement_commit_path_low_cell(self, HL_cell: BlockPtr, DE_delta: int, B_marker: int) -> None:
        hl_cell = self._normalize_map_ptr(HL_cell)
        de_delta = DE_delta & 0xFFFF
        de_delta_signed = self._u16_to_signed(de_delta)
        b_marker = B_marker & 0xFF

        self.var_runtime_current_cell_ptr = hl_cell

        cell = self._read_u8_ptr(hl_cell)
        self._write_u8_ptr(hl_cell, (cell & 0xC0) | b_marker)

        hl_prev = hl_cell.add(-de_delta_signed)
        prev = self._read_u8_ptr(hl_prev)
        self._write_u8_ptr(hl_prev, prev & 0xC0)

        e_step = de_delta & 0xFF
        self.var_current_map_coords.apply_step_low_byte(e_step)

        self.state_29_handler()

    def _queue_insert_state_with_cell_ptr(
        self,
        queue_state: TransientQueueBuffer,
        A_state: int,
        HL_cell: BlockPtr,
    ) -> None:
        queue = queue_state
        hl_cell_ptr = self._normalize_map_ptr(HL_cell)
        queue_entries = queue.entries
        queue.free_slots = ((queue.free_slots & 0xFF) - 0x01) & 0xFF

        for queue_entry in queue_entries:
            if (queue_entry.state & 0xFF) != 0x00:
                continue
            queue_entry.state = A_state & 0xFF
            queue_entry.cell_ptr = hl_cell_ptr
            break
        else:
            raise ValueError("Transient queue is full: no empty typed entry")

        self._rom_beeper(de_ticks=0x0001, hl_period=0x0004)

    # ZX 0xE3E9..0xE493
    def action_effect_dispatcher_keyed_xa8dc_bits(self) -> None:
        A_flags = self.var_action_effect_flags & 0xFF
        DE_step = self.var_runtime_move_delta & 0xFFFF
        DE_step_signed = self._u16_to_signed(DE_step)
        HL_cur = self.var_runtime_current_cell_ptr
        E_step = DE_step & 0xFF

        if A_flags & 0x40:
            if (self.var_transient_queue_c.free_slots & 0xFF) == 0x00:
                return
            HL_cell = HL_cur.add(DE_step_signed)
            if (self._read_u8_ptr(HL_cell) & 0x3F) != 0x00:
                return
            cell = self._read_u8_ptr(HL_cell)
            self._write_u8_ptr(HL_cell, (cell & 0xC0) | 0x33)
            if E_step == 0x01:
                A_state = 0x34
            elif E_step == 0xFF:
                A_state = 0x32
            elif E_step == 0xCE:
                A_state = 0x01
            else:
                A_state = 0x65
            self._queue_insert_state_with_cell_ptr(
                queue_state=self.var_transient_queue_c,
                A_state=A_state,
                HL_cell=HL_cell,
            )
            return

        if A_flags & 0x10:
            if (self.var_transient_queue_b.free_slots & 0xFF) == 0x00:
                return
            HL_cell = HL_cur.add(-DE_step_signed)
            if (self._read_u8_ptr(HL_cell) & 0x3F) != 0x00:
                return
            cell = self._read_u8_ptr(HL_cell)
            self._write_u8_ptr(HL_cell, (cell & 0xC0) | 0x36)
            self._queue_insert_state_with_cell_ptr(
                queue_state=self.var_transient_queue_b,
                A_state=0x80,
                HL_cell=HL_cell,
            )
            return

        if A_flags & 0x01:
            self.countdown_driven_marker_updater_one_cell()
            return

        if (self.var_transient_queue_a.free_slots & 0xFF) == 0x00:
            return
        HL_cell = HL_cur.add(-DE_step_signed)
        if (self._read_u8_ptr(HL_cell) & 0x3F) != 0x00:
            return
        cell = self._read_u8_ptr(HL_cell)
        self._write_u8_ptr(HL_cell, (cell & 0xC0) | 0x34)
        self._queue_insert_state_with_cell_ptr(
            queue_state=self.var_transient_queue_a,
            A_state=0x80,
            HL_cell=HL_cell,
        )

    # ZX 0xE494..0xE4AB
    def fn_process_transient_effect_queues_handlers_xe530(self):
        self.fn_process_transient_effect_queues_core(queue_state=self.var_transient_queue_a, DE_handler=0xE530)
        self.fn_process_transient_effect_queues_core(queue_state=self.var_transient_queue_b, DE_handler=0xE5CA)
        self.fn_process_transient_effect_queues_core(queue_state=self.var_transient_queue_c, DE_handler=0xE698)

    # ZX 0xE4AC..0xE4BD
    def fn_process_transient_effect_queues_core(
        self,
        queue_state: TransientQueueBuffer,
        DE_handler: object,
    ) -> None:
        if callable(DE_handler):
            handler = DE_handler
            self.patch_transient_queue_handler_call_target = DE_handler
        elif isinstance(DE_handler, int):
            handler_map = {
                0xE530: self.fn_transient_queue_handler_core,
                0xE5CA: self.callback_queue_b_state_classifier,
                0xE698: self.fn_repeat_wrapper_xe600,
            }
            de_target = DE_handler & 0xFFFF
            if de_target not in handler_map:
                raise ValueError(f"Unsupported transient queue handler target: 0x{de_target:04X}")
            handler = handler_map[de_target]
            self.patch_transient_queue_handler_call_target = de_target
        else:
            raise TypeError(f"Unsupported DE_handler type: {type(DE_handler)!r}")

        for queue_entry in queue_state.entries:
            a_state = queue_entry.state & 0xFF
            if a_state != 0x00:
                hl_cell = queue_entry.cell_ptr
                if hl_cell is None:
                    raise ValueError("Transient queue entry has non-zero state but null cell pointer")
                result = handler(A_state=a_state, HL_cell=hl_cell)
                if isinstance(result, tuple):
                    if len(result) != 2:
                        raise ValueError("Queue handler tuple result must be (A_state, HL_cell)")
                    a_state_next, hl_cell_next = result
                else:
                    a_state_next = result
                    hl_cell_next = hl_cell

                queue_entry.state = a_state_next & 0xFF
                if not isinstance(hl_cell_next, BlockPtr):
                    raise TypeError(
                        "Transient queue handler must return BlockPtr as HL_cell in tuple form",
                    )
                queue_entry.cell_ptr = self._normalize_map_ptr(hl_cell_next)

    # ZX 0xE530..0xE559
    def fn_transient_queue_handler_core(self, A_state: int, HL_cell: BlockPtr) -> int:
        a_state = A_state & 0x7F
        if (a_state & 0xFE) != 0x00:
            return self.countdown_phase_helper(HL_cell=HL_cell, stack_A_state=a_state)

        a_code = self._read_u8_ptr(HL_cell) & 0x3F
        if a_code == 0x34 or a_code == 0x35:
            return self.state_toggle_helper(HL_cell=HL_cell, D_base=0x34, stack_A_state=a_state)
        if a_code == 0x38 or a_code == 0x00:
            return self.immediate_mark_helper(HL_cell=HL_cell, stack_A_state=a_state)
        if a_code < 0x0D:
            return self.return_helper(stack_A_state=a_state)

        cell = self._read_u8_ptr(HL_cell)
        self._write_u8_ptr(HL_cell, (cell & 0xC0) | 0x38)
        self.fn_neighbor_tag_helper_queue_b_handlers(HL_cell=HL_cell)
        return 0x00

    # ZX 0xE55A..0xE56E
    def fn_neighbor_tag_helper_queue_b_handlers(self, HL_cell: BlockPtr) -> None:
        hl = HL_cell
        self.fn_neighbor_tag_helper_core(HL_cell=hl.add(0x0001))
        self.fn_neighbor_tag_helper_core(HL_cell=hl.add(-0x0001))
        self.fn_neighbor_tag_helper_core(HL_cell=hl.add(-0x0032))
        self.fn_neighbor_tag_helper_core(HL_cell=hl.add(0x0032))

    # ZX 0xE56F..0xE58C
    def fn_neighbor_tag_helper_core(self, HL_cell: BlockPtr) -> int:
        cell = self._read_u8_ptr(HL_cell)
        A_code = cell & 0x3F
        if not ((0x0D <= A_code < 0x17) or (0x21 <= A_code < 0x25) or (0x33 <= A_code < 0x39)):
            return
        self._write_u8_ptr(HL_cell, (cell & 0xC0) | 0x38)

    # ZX 0xE58D..0xE59B
    def state_toggle_helper(self, HL_cell: BlockPtr, D_base: int, stack_A_state: int) -> int:
        A_state = (stack_A_state ^ 0x01) & 0xFF
        D_code = (D_base + A_state) & 0xFF
        cell = self._read_u8_ptr(HL_cell)
        self._write_u8_ptr(HL_cell, (cell & 0xC0) | D_code)
        return A_state | 0x80

    # ZX 0xE59C..0xE5A0
    def delay_entry_helper_transient_handlers(self, A_state):
        A_state = (A_state | 0x80) & 0xFF
        self.routine_30_to_30_rom_beeper_pause()
        return A_state

    # ZX 0xE5A1..0xE5B6
    def countdown_phase_helper(self, HL_cell: BlockPtr, stack_A_state: int) -> int:
        HL_cell_ref = HL_cell
        A_state = stack_A_state & 0xFF
        A_cell = self._read_u8_ptr(HL_cell_ref)
        self._write_u8_ptr(HL_cell_ref, (A_cell & 0xC0) | ((A_state + 0x29) & 0xFF))
        A_state = (A_state + 0x01) & 0xFF
        if A_state != 0x06:
            return self.delay_entry_helper_transient_handlers(A_state=A_state)
        A_cell = self._read_u8_ptr(HL_cell_ref)
        self._write_u8_ptr(HL_cell_ref, A_cell & 0xC0)
        return 0x00

    # ZX 0xE5B7..0xE5C6
    def immediate_mark_helper(self, HL_cell: BlockPtr, stack_A_state: int) -> int:
        A_cell = self._read_u8_ptr(HL_cell)
        self._write_u8_ptr(HL_cell, (A_cell & 0xC0) | 0x2A)
        self.fn_neighbor_tag_helper_queue_b_handlers(HL_cell=HL_cell)
        return 0x82

    # ZX 0xE5C7..0xE5C9
    def return_helper(self, stack_A_state):
        A_state = (stack_A_state | 0x80) & 0xFF
        return A_state

    # ZX 0xE5CA..0xE5F6
    def callback_queue_b_state_classifier(self, A_state: int, HL_cell: BlockPtr) -> int:
        a_state = A_state & 0x7F
        if (a_state & 0xFE) != 0x00:
            return self.countdown_phase_helper(HL_cell=HL_cell, stack_A_state=a_state)

        a_code = self._read_u8_ptr(HL_cell) & 0x3F
        if a_code == 0x36 or a_code == 0x37:
            return self.state_toggle_helper(HL_cell=HL_cell, D_base=0x36, stack_A_state=a_state)

        if a_code == 0x38 or a_code == 0x00:
            cell = self._read_u8_ptr(HL_cell)
            self._write_u8_ptr(HL_cell, (cell & 0xC0) | 0x2A)
            return 0x82

        if a_code < 0x0D:
            return self.fallback_clear_helper_queue_b_path(HL_cell=HL_cell, stack_A_state=a_state)
        if a_code < 0x21:
            return self.return_helper(stack_A_state=a_state)
        return self.fallback_clear_helper_queue_b_path(HL_cell=HL_cell, stack_A_state=a_state)

    # ZX 0xE5F7..0xE5FF
    def fallback_clear_helper_queue_b_path(self, HL_cell: BlockPtr, stack_A_state: int) -> int:
        cell = self._read_u8_ptr(HL_cell)
        self._write_u8_ptr(HL_cell, (cell & 0xC0) | 0x38)
        return 0x00

    # ZX 0xE600..0xE608
    def transient_queue_c_state_machine_core(self, A_state: int, HL_cell: BlockPtr) -> tuple[int, BlockPtr]:
        def _write_low6(ptr: BlockPtr, code: int) -> None:
            cell = self._read_u8_ptr(ptr)
            self._write_u8_ptr(ptr, (cell & 0xC0) | (code & 0x3F))

        a_state = A_state & 0xFF
        hl_cell = HL_cell

        root_eq_code = getattr(self, "patch_queue_c_root_eq_code", 0x33) & 0xFF
        root_low_limit = getattr(self, "patch_queue_c_root_low_code_limit", 0x0D) & 0xFF
        scan_low_limit = getattr(self, "patch_queue_c_scan_low_code_limit", 0x0D) & 0xFF
        scan_mid_limit = getattr(self, "patch_queue_c_scan_mid_code_limit", 0x17) & 0xFF
        scan_branch_opcode = getattr(self, "patch_queue_c_scan_branch_opcode", 0x38) & 0xFF
        mark_code = getattr(self, "patch_queue_c_mark_code", 0x33) & 0xFF

        if a_state & 0x80:
            a_phase = a_state & 0x7F
            if a_phase == 0x03:
                cell = self._read_u8_ptr(hl_cell)
                self._write_u8_ptr(hl_cell, cell & 0xC0)
                return 0x00, hl_cell

            _write_low6(hl_cell, (a_phase + 0x2B) & 0xFF)
            self.routine_30_to_30_rom_beeper_pause()
            return (a_state + 0x01) & 0xFF, hl_cell

        a_code = self._read_u8_ptr(hl_cell) & 0x3F
        if a_code == root_eq_code:
            hl_root = hl_cell
            _write_low6(hl_root, 0x00)
            e_off = (a_state - 0x01) & 0xFF
            hl_scan = hl_root.add(-0x0032 + e_off)
            a_scan = self._read_u8_ptr(hl_scan) & 0x3F

            if a_scan == 0x00:
                _write_low6(hl_scan, mark_code)
                return a_state, hl_scan

            if a_scan < scan_low_limit:
                hl_write = hl_root
            else:
                if scan_branch_opcode == 0x38:  # JR C after CP scan_mid_limit
                    branch_taken = a_scan < scan_mid_limit
                elif scan_branch_opcode == 0x28:  # JR Z after CP scan_mid_limit
                    branch_taken = a_scan == scan_mid_limit
                else:
                    raise ValueError(f"Unsupported queue-C scan branch opcode: 0x{scan_branch_opcode:02X}")

                if branch_taken:
                    _write_low6(hl_scan, 0x38)
                    return 0x00, hl_scan
                if a_scan == 0x38:
                    _write_low6(hl_scan, 0x38)
                    return 0x00, hl_scan
                if a_scan < 0x21:
                    hl_write = hl_root
                elif a_scan < 0x25:
                    _write_low6(hl_scan, 0x38)
                    return 0x00, hl_scan
                elif a_scan < 0x2A:
                    hl_write = hl_root
                elif a_scan < 0x2E:
                    hl_write = hl_scan
                elif a_scan < 0x33:
                    hl_write = hl_root
                elif a_scan < 0x38:
                    _write_low6(hl_scan, 0x38)
                    return 0x00, hl_scan
                else:
                    hl_write = hl_root

            _write_low6(hl_write, 0x2A)
            return 0x80, hl_write

        if a_code == 0x00 or a_code == 0x38:
            _write_low6(hl_cell, 0x2A)
            return 0x80, hl_cell

        if a_code < root_low_limit:
            return a_state, hl_cell

        _write_low6(hl_cell, 0x38)
        return 0x00, hl_cell

    # ZX 0xE698..0xE6A2
    def fn_repeat_wrapper_xe600(self, A_state: int, HL_cell: BlockPtr) -> tuple[int, BlockPtr]:
        a_state = A_state & 0xFF
        hl_cell = HL_cell
        a_state, hl_cell = self.transient_queue_c_state_machine_core(A_state=a_state, HL_cell=hl_cell)
        while a_state != 0x00 and (a_state & 0x80) == 0x00:
            a_state, hl_cell = self.transient_queue_c_state_machine_core(
                A_state=a_state,
                HL_cell=hl_cell,
            )
        return a_state & 0xFF, hl_cell

    # ZX 0xE6A3..0xE6B2
    def routine_30_to_30_rom_beeper_pause(self):
        self._rom_beeper(de_ticks=0x001E, hl_period=0x001E)

    # ZX 0xE6B3..0xE6F9
    def fn_active_transient_effect_executor(self) -> None:
        if (self.var_transient_effect_state & 0xFF) == 0x00:
            return
        self.patch_queue_c_root_low_code_limit = 0x17
        self.patch_queue_c_scan_low_code_limit = 0x17
        self.patch_queue_c_scan_mid_code_limit = 0x39
        self.patch_queue_c_root_eq_code = 0x39
        self.patch_queue_c_mark_code = 0x39
        self.patch_queue_c_scan_branch_opcode = 0x28
        try:
            a_state = self.var_transient_effect_state & 0xFF
            hl_cell = self.var_transient_effect_ptr
            a_state, hl_cell = self.fn_repeat_wrapper_xe600(A_state=a_state, HL_cell=hl_cell)
            self.var_transient_effect_state = a_state & 0xFF
            self.var_transient_effect_ptr = self._normalize_map_ptr(hl_cell)
        finally:
            self.patch_queue_c_root_low_code_limit = 0x0D
            self.patch_queue_c_scan_low_code_limit = 0x0D
            self.patch_queue_c_scan_mid_code_limit = 0x17
            self.patch_queue_c_scan_branch_opcode = 0x38
            self.patch_queue_c_root_eq_code = 0x33
            self.patch_queue_c_mark_code = 0x33

    def _queue_ai_mark_cell_2a_return_10(self, BC_cell: BlockPtr) -> tuple[int, BlockPtr]:
        bc_cell = BC_cell
        cell = self._read_u8_ptr(bc_cell)
        self._write_u8_ptr(bc_cell, (cell & 0xC0) | 0x2A)
        return 0x10, bc_cell

    def _queue_ai_random_fallback_state(self, A_state: int, BC_cell: BlockPtr) -> tuple[int, BlockPtr]:
        bc_cell = BC_cell
        # ZX 0xE7F4 uses `LD A,R`, not a frame counter. Multiple fallback calls
        # can happen inside one gameplay frame, so a per-use entropy source is
        # closer to the original semantics than a shared per-frame value.
        b = self._next_r_register() & 0xFF
        a = 0x11
        carry = 0
        # E7F3 uses DJNZ; when B starts at 0, it runs 256 iterations.
        loop_count = b if b != 0x00 else 0x100
        for _ in range(loop_count):
            new_carry = a & 0x01
            a = ((carry << 7) | (a >> 1)) & 0xFF
            carry = new_carry
        a &= 0x0F
        if a == 0x00:
            a = 0x01
        return a, bc_cell

    def _queue_ai_high_nibble_state(self, A_state: int, BC_cell: BlockPtr) -> tuple[int, BlockPtr]:
        a_state = A_state & 0xFF
        bc_cell = BC_cell
        e_state = a_state

        if e_state & 0x10:
            d_mark = 0x2B
        elif e_state & 0x20:
            d_mark = 0x2C
        elif e_state & 0x40:
            d_mark = 0x2D
        else:
            cell = self._read_u8_ptr(bc_cell)
            self._write_u8_ptr(bc_cell, cell & 0xC0)
            self._rom_beeper(de_ticks=0x0014, hl_period=0x003C)
            self.fn_hud_decimal_counter_animator_core()
            self.fn_hud_triplet_decrement_helper_bytes_xa8d8()
            return 0x00, bc_cell

        cell = self._read_u8_ptr(bc_cell)
        self._write_u8_ptr(bc_cell, (cell & 0xC0) | d_mark)
        a_out = ((e_state << 1) | (e_state >> 7)) & 0xFF
        self._rom_beeper(de_ticks=0x0032, hl_period=0x000A)
        return a_out, bc_cell

    def _queue_ai_directional_step(
        self,
        A_state: int,
        BC_cell: BlockPtr,
        *,
        threshold_code: int,
        face_up: int,
        face_right: int,
        face_down: int,
        face_left: int,
    ) -> tuple[int, BlockPtr]:
        d_state = A_state & 0xFF
        bc_cell = BC_cell

        if d_state & 0xF0:
            return self._queue_ai_high_nibble_state(A_state=d_state, BC_cell=bc_cell)

        if (self._read_u8_ptr(bc_cell) & 0x3F) == 0x38:
            return self._queue_ai_mark_cell_2a_return_10(BC_cell=bc_cell)

        if d_state & 0x01:
            hl_step, e_face = -0x0001, face_up & 0xFF
        elif d_state & 0x02:
            hl_step, e_face = 0x0001, face_right & 0xFF
        elif d_state & 0x04:
            hl_step, e_face = 0x0032, face_down & 0xFF
        else:
            hl_step, e_face = -0x0032, face_left & 0xFF

        hl_probe_2 = bc_cell.add(hl_step + hl_step)
        if (self._read_u8_ptr(hl_probe_2) & 0x3F) == (threshold_code & 0xFF):
            return self._queue_ai_random_fallback_state(A_state=d_state, BC_cell=bc_cell)

        hl_dst = bc_cell.add(hl_step)
        dst_raw = self._read_u8_ptr(hl_dst)
        a_dst = dst_raw & 0x3F
        if a_dst == 0x00:
            src = self._read_u8_ptr(bc_cell)
            self._write_u8_ptr(hl_dst, (dst_raw & 0xC0) | e_face)
            self._write_u8_ptr(bc_cell, src & 0xC0)
            return d_state, hl_dst

        if a_dst < 0x1D or a_dst == 0x38:
            return self._queue_ai_random_fallback_state(A_state=d_state, BC_cell=bc_cell)

        if a_dst == 0x25:
            progress = ((self.var_runtime_progress_counter & 0xFF) + 0x01) & 0xFF
            self.var_runtime_progress_counter = progress
            self.fn_gameplay_movement_step_core()
            dst = self._read_u8_ptr(hl_dst)
            src = self._read_u8_ptr(bc_cell)
            self._write_u8_ptr(hl_dst, (dst & 0xC0) | 0x2A)
            self._write_u8_ptr(bc_cell, src & 0xC0)
            return 0x10, hl_dst

        dst = self._read_u8_ptr(hl_dst)
        src = self._read_u8_ptr(bc_cell)
        self._write_u8_ptr(hl_dst, (dst & 0xC0) | e_face)
        self._write_u8_ptr(bc_cell, src & 0xC0)
        return d_state, hl_dst

    # ZX 0xE704..0xE746
    def fn_queue_1_ai_step(self, A_state: int, BC_cell: BlockPtr) -> tuple[int, BlockPtr]:
        return self._queue_ai_directional_step(
            A_state=A_state,
            BC_cell=BC_cell,
            threshold_code=getattr(self, "patch_queue_1_block_threshold_code", 0x50),
            face_up=0x11,
            face_right=0x12,
            face_down=0x13,
            face_left=0x14,
        )

    # ZX 0xE76F..0xE7B1
    def callback_queue_2_directional_ai_step(self, A_state: int, BC_cell: BlockPtr) -> tuple[int, BlockPtr]:
        return self._queue_ai_directional_step(
            A_state=A_state,
            BC_cell=BC_cell,
            threshold_code=getattr(self, "patch_queue_2_block_threshold_code", 0x50),
            face_up=0x0D,
            face_right=0x0E,
            face_down=0x0F,
            face_left=0x10,
        )

    def _queue_3_fallback_direction_from_player_delta(self, BC_cell: BlockPtr) -> int:
        bc_cell = BC_cell
        hl_step = self._u16_to_signed(self.var_runtime_move_delta)

        threshold_code = getattr(self, "patch_queue_3_fallback_threshold_code", 0x50) & 0xFF
        hl_probe_2 = bc_cell.add(hl_step + hl_step)
        if (self._read_u8_ptr(hl_probe_2) & 0x3F) == threshold_code:
            a_random, _ = self._queue_ai_random_fallback_state(A_state=0x00, BC_cell=bc_cell)
            return a_random & 0xFF

        hl_probe_1 = bc_cell.add(hl_step)
        a_probe = self._read_u8_ptr(hl_probe_1) & 0x3F
        if a_probe != 0x00 and (a_probe < 0x1D or a_probe == 0x38 or a_probe == 0x39):
            a_random, _ = self._queue_ai_random_fallback_state(A_state=0x00, BC_cell=bc_cell)
            return a_random & 0xFF

        a_step = self.var_runtime_move_delta & 0xFF
        if a_step == 0x01:
            return 0x02
        if a_step == 0xFF:
            return 0x01
        if a_step == 0x32:
            return 0x04
        return 0x08

    # ZX 0xE848..0xE88A
    def callback_queue_3_chase_ai_step(self, A_state: int, BC_cell: BlockPtr) -> tuple[int, BlockPtr]:
        d_state = A_state & 0xFF
        bc_cell = BC_cell

        if d_state & 0xF0:
            a_next, _ = self._queue_ai_high_nibble_state(A_state=d_state, BC_cell=bc_cell)
            return a_next, bc_cell
        if (self._read_u8_ptr(bc_cell) & 0x3F) == 0x38:
            a_next, _ = self._queue_ai_mark_cell_2a_return_10(BC_cell=bc_cell)
            return a_next, bc_cell

        if d_state & 0x01:
            hl_step, e_base = -0x0001, 0x01
        elif d_state & 0x02:
            hl_step, e_base = 0x0001, 0x04
        elif d_state & 0x04:
            hl_step, e_base = 0x0032, 0x07
        else:
            hl_step, e_base = -0x0032, 0x0A

        threshold_code = getattr(self, "patch_queue_3_block_threshold_code", 0x50) & 0xFF
        hl_probe_2 = bc_cell.add(hl_step + hl_step)
        if (self._read_u8_ptr(hl_probe_2) & 0x3F) == threshold_code:
            return self._queue_3_fallback_direction_from_player_delta(BC_cell=bc_cell), bc_cell

        hl_dst = bc_cell.add(hl_step)
        a_dst = self._read_u8_ptr(hl_dst) & 0x3F
        if a_dst != 0x00:
            if a_dst < 0x1D or a_dst == 0x38 or a_dst == 0x39:
                return self._queue_3_fallback_direction_from_player_delta(BC_cell=bc_cell), bc_cell
            if a_dst == 0x25:
                self.special_contact_event_branch_xe848()

        phase = self.var_runtime_phase_index & 0xFF
        dst_cell = self._read_u8_ptr(hl_dst)
        self._write_u8_ptr(hl_dst, (dst_cell & 0xC0) | ((e_base + phase) & 0xFF))
        src_cell = self._read_u8_ptr(bc_cell)
        self._write_u8_ptr(bc_cell, src_cell & 0xC0)
        bc_cell = hl_dst

        if (getattr(self, "patch_queue_3_contact_branch_opcode", 0xC5) & 0xFF) != 0xC5:
            return d_state, bc_cell
        if (self.var_transient_effect_state & 0xFF) != 0x00:
            return d_state, bc_cell

        map_coords = self.var_current_map_coords
        player_col, player_row = map_coords.snapshot()
        self.fn_convert_map_pointer_hl_row_column(HL_cell=bc_cell)
        enemy_col, enemy_row = map_coords.snapshot()
        map_coords.set(player_col, player_row)

        hl_spawn: BlockPtr
        a_seed: int
        if player_row >= enemy_row and player_col == enemy_col:
            if (d_state & 0x04) == 0x00:
                return d_state, bc_cell
            hl_spawn = bc_cell.add(0x0032)
            a_seed = 0x65
        elif player_row < enemy_row and player_col == enemy_col:
            if (d_state & 0x08) == 0x00:
                return d_state, bc_cell
            hl_spawn = bc_cell.add(-0x0032)
            a_seed = 0x01
        elif player_col < enemy_col and player_row == enemy_row:
            if (d_state & 0x01) == 0x00:
                return d_state, bc_cell
            hl_spawn = bc_cell.add(-0x0001)
            a_seed = 0x32
        elif player_col >= enemy_col and player_row == enemy_row:
            if (d_state & 0x02) == 0x00:
                return d_state, bc_cell
            hl_spawn = bc_cell.add(0x0001)
            a_seed = 0x34
        else:
            return d_state, bc_cell

        if (self._read_u8_ptr(hl_spawn) & 0x3F) != 0x00:
            return d_state, bc_cell

        self.var_transient_effect_state = a_seed & 0xFF
        self.var_transient_effect_ptr = self._normalize_map_ptr(hl_spawn)
        spawn_cell = self._read_u8_ptr(hl_spawn)
        self._write_u8_ptr(hl_spawn, (spawn_cell & 0xC0) | 0x39)
        return d_state, bc_cell

    # ZX 0xE9AC..0xE9BB
    def special_contact_event_branch_xe848(self):
        progress = ((self.var_runtime_progress_counter & 0xFF) + 0x01) & 0xFF
        self.var_runtime_progress_counter = progress
        self.fn_hud_decimal_counter_animator()
        self.fn_gameplay_movement_step_core()

    # ZX 0xE9BC..0xE9EB
    def per_frame_object_state_update_pass(self):
        a_phase = ((self.var_runtime_phase_index & 0xFF) + 0x01) & 0xFF
        if a_phase == 0x03:
            a_phase = 0x00
        self.var_runtime_phase_index = a_phase

        self.fn_object_state_update_pass_core(
            DE_cb=self.fn_queue_1_ai_step,
            HL_queue=self.var_runtime_queue_head_1,
        )
        self.fn_object_state_update_pass_core(
            DE_cb=self.callback_queue_2_directional_ai_step,
            HL_queue=self.var_runtime_queue_head_2,
        )
        self.fn_active_transient_effect_executor()
        self.fn_object_state_update_pass_core(
            DE_cb=self.callback_queue_3_chase_ai_step,
            HL_queue=self.var_runtime_queue_head_3,
        )
        self.fn_object_state_update_pass_core(
            DE_cb=self.callback_queue_0_low_bits_toggle,
            HL_queue=self.var_runtime_queue_head_0,
        )

    # ZX 0xE9EC..0xE9FD
    def fn_object_state_update_pass_core(
        self,
        DE_cb: ObjectCallback,
        HL_queue: RuntimeObjectQueueBuffer,
    ) -> None:
        callback = self._resolve_object_callback(DE_cb)
        self.patch_object_callback_call_target = callback
        queue = self._resolve_object_queue_cursor(HL_queue)
        for queue_entry in queue.entries:
            a_state = queue_entry.state & 0xFF
            if a_state == 0xFF:
                return
            if a_state != 0x00:
                bc_cell = queue_entry.cell_ptr
                if bc_cell is None:
                    raise ValueError("Runtime object queue entry has non-zero state and null cell pointer")
                callback_result = callback(A_state=a_state, BC_cell=bc_cell)
                if isinstance(callback_result, tuple):
                    if len(callback_result) != 2:
                        raise ValueError("Callback tuple result must contain exactly two items")
                    a_next = callback_result[0] & 0xFF
                    bc_next_ptr = callback_result[1]
                else:
                    if callback_result is None:
                        raise TypeError("Callback returned None; expected int or (int, ptr)")
                    a_next = callback_result & 0xFF
                    bc_next_ptr = bc_cell
                queue_entry.cell_ptr = self._normalize_map_ptr(bc_next_ptr)
                queue_entry.state = a_next

    # ZX 0xEA0C..0xEA12
    def callback_queue_0_low_bits_toggle(self, A_state: int, BC_cell: BlockPtr) -> int:
        cell = self._read_u8_ptr(BC_cell)
        self._write_u8_ptr(BC_cell, cell ^ 0x03)
        return A_state & 0xFF

    # ZX 0xEA1A..0xEA2F
    def fn_hud_decimal_counter_animator(self):
        a_d4 = ((self.var_runtime_aux_cc & 0xFF) + 0x01) & 0xFF
        if a_d4 != 0x0A:
            self.var_runtime_aux_cc = a_d4
            self.fn_hud_decimal_animator_stage_1(A_digit=a_d4)
            return
        self.var_runtime_aux_cc = 0x00
        self.fn_hud_decimal_animator_stage_1(A_digit=0x00)
        self.fn_hud_decimal_counter_animator_core()

    # ZX 0xEA30..0xEA87
    def fn_hud_decimal_counter_animator_core(self):
        a_d3 = ((self.var_runtime_aux_cb & 0xFF) + 0x01) & 0xFF
        if a_d3 != 0x0A:
            self.var_runtime_aux_cb = a_d3
            self.fn_hud_decimal_animator_stage_2(A_digit=a_d3)
            return

        self.var_runtime_aux_cb = 0x00
        self.fn_hud_decimal_animator_stage_2(A_digit=0x00)

        a_d2 = ((self.var_runtime_aux_ca & 0xFF) + 0x01) & 0xFF
        if a_d2 != 0x0A:
            self.var_runtime_aux_ca = a_d2
            self.fn_hud_decimal_animator_stage_3(A_digit=a_d2)
            return

        self.var_runtime_aux_ca = 0x00
        self.fn_hud_decimal_animator_stage_3(A_digit=0x00)

        a_d1 = ((self.var_runtime_aux_c8_hi & 0xFF) + 0x01) & 0xFF
        if a_d1 != 0x0A:
            self.var_runtime_aux_c8_hi = a_d1
            self.fn_hud_decimal_animator_stage_dispatch(A_digit=a_d1)
            return

        self.var_runtime_aux_c8_hi = 0x00
        self.fn_hud_decimal_animator_stage_dispatch(A_digit=0x00)

        a_d0 = ((self.var_runtime_aux_c8_lo & 0xFF) + 0x01) & 0xFF
        if a_d0 != 0x0A:
            self.var_runtime_aux_c8_lo = a_d0
        else:
            self.var_runtime_aux_c8_lo = 0x00

        self.glyph_plot_helper(A_glyph=(self.var_runtime_aux_c8_lo & 0xFF), B_row=0x11, C_col=0x06)

    # ZX 0xEA88..0xEA8D
    def fn_hud_decimal_animator_stage_1(self, A_digit):
        self.glyph_plot_helper(A_glyph=(A_digit & 0xFF), B_row=0x11, C_col=0x0A)

    # ZX 0xEA8E..0xEA93
    def fn_hud_decimal_animator_stage_2(self, A_digit):
        self.glyph_plot_helper(A_glyph=(A_digit & 0xFF), B_row=0x11, C_col=0x09)

    # ZX 0xEA94..0xEA99
    def fn_hud_decimal_animator_stage_3(self, A_digit):
        self.glyph_plot_helper(A_glyph=(A_digit & 0xFF), B_row=0x11, C_col=0x08)

    # ZX 0xEA9A..0xEAA5
    def fn_hud_decimal_animator_stage_dispatch(self, A_digit):
        self.glyph_plot_helper(A_glyph=(A_digit & 0xFF), B_row=0x11, C_col=0x07)

    # ZX 0xEAA6..0xEAC2
    def fn_routine_8_byte_screen_blit_primitive(
        self,
        DE_src: BlockPtr,
        B_row: int,
        C_col: int,
    ) -> BlockPtr:
        B = B_row & 0xFF
        C = C_col & 0xFF

        src8 = self._read_bytes(DE_src, 0x08)

        H = ((B & 0x18) | 0x40) & 0xFF
        L = (((B & 0x07) << 5) + C) & 0xFF
        dst_index = (((H << 8) | L) & 0xFFFF) - 0x4000
        HL_dst = BlockPtr(
            self.var_display_bitmap_ram,
            dst_index,
        )

        for i in range(0x08):
            self._write_u8_ptr(HL_dst, src8[i])
            HL_dst = HL_dst.add(0x0100)

        return DE_src.add(0x0008)

    # ZX 0xEAC3..0xEAC4
    def glyph_plot_helper(self, A_glyph, B_row, C_col):
        A_glyph = (A_glyph + 0x10) & 0xFF
        B_row, C_col = self.fn_glyph_plot_helper_entry(A_glyph=A_glyph, B_row=B_row, C_col=C_col)
        return B_row, C_col

    # ZX 0xEAC5..0xEAF0
    def fn_glyph_plot_helper_entry(self, A_glyph, B_row, C_col):
        glyph_bias_ptr = self._glyph_bias_ptr
        DE_src = glyph_bias_ptr.add(0x08 * ((A_glyph + 0x01) & 0xFF))
        src8 = self._read_bytes(DE_src, 0x08)
        scratch_base = BlockPtr(self.var_glyph_scratch_template, 0x0000)
        for i in range(0x08):
            self._write_u8_ptr(scratch_base.add(0x01 + i * 0x02), src8[i])
            self._write_u8_ptr(scratch_base.add(0x02 + i * 0x02), src8[i])
        self.fn_routine_8_byte_screen_blit_primitive(
            DE_src=scratch_base,
            B_row=B_row,
            C_col=C_col,
        )
        self.fn_routine_8_byte_screen_blit_primitive(
            DE_src=BlockPtr(self.var_glyph_scratch_template, self.var_glyph_scratch_template_row_2),
            B_row=(B_row + 0x01) & 0xFF,
            C_col=C_col,
        )
        C_col = (C_col + 0x01) & 0xFF
        return B_row, C_col

    # ZX 0xEB02..0xEB15
    def fn_stretched_text_symbol_stream_printer(
        self,
        HL_stream: BlockPtr,
        B_row: int,
        C_col: int,
    ) -> tuple[int, int]:
        stream_ptr = HL_stream
        B = B_row & 0xFF
        C = C_col & 0xFF
        while True:
            A_glyph = self._read_u8_ptr(stream_ptr)
            if A_glyph == 0xFF:
                return B, C
            B, C = self.fn_glyph_plot_helper_entry(A_glyph=A_glyph, B_row=B, C_col=C)
            stream_ptr = stream_ptr.add(0x0001)

    # ZX 0xEB18..0xEB62
    def fn_directional_interaction_dispatcher_using_pointer_table(
        self,
        *,
        defer_overlay_timing_to_fsm: bool = False,
    ):
        if self._fsm_step_active and not defer_overlay_timing_to_fsm:
            raise RuntimeError(
                "Legacy directional dispatcher path called during active FSM step; "
                "expected defer_overlay_timing_to_fsm=True",
            )
        probes = (
            self.var_runtime_dir_ptr_up_cell,
            self.var_runtime_dir_ptr_down_cell,
            self.var_runtime_dir_ptr_right_cell,
            self.var_runtime_dir_ptr_left_cell,
        )
        pairs = (
            self.var_runtime_dir_ptr_down_cell,
            self.var_runtime_dir_ptr_right_cell,
            self.var_runtime_dir_ptr_left_cell,
            self.var_runtime_dir_ptr_up_cell,
        )
        clear_masks = (0xFE, 0xFD, 0xFB, 0xF7)
        action_masks = (0x02, 0x04, 0x08, 0x01)
        c_flags = self.var_runtime_direction_mask & 0xFF

        for i in range(4):
            bit = 1 << i
            if c_flags & bit:
                c_flags = self.fn_if_probed_cell_is_empty_mark(
                    HL_cell=probes[i],
                    B_bit_clear_mask=clear_masks[i],
                    C_blocked_bits=c_flags,
                )
            else:
                c_flags = self.fn_directional_action_core(
                    HL_probe=probes[i],
                    HL_pair=pairs[i],
                    B_mask=action_masks[i],
                    C_flags=c_flags,
                    defer_overlay_timing_to_fsm=defer_overlay_timing_to_fsm,
                )

        self.var_runtime_direction_mask = c_flags & 0xFF

    # ZX 0xEB63..0xEB68
    def fn_directional_action_core(
        self,
        HL_probe: BlockPtr,
        HL_pair: BlockPtr,
        B_mask: int,
        C_flags: int,
        *,
        defer_overlay_timing_to_fsm: bool = False,
    ) -> int:
        return self.fn_directional_action_validate_target(
            HL_probe=HL_probe,
            HL_pair=HL_pair,
            B_mask=(B_mask & 0xFF),
            C_flags=(C_flags & 0xFF),
            defer_overlay_timing_to_fsm=defer_overlay_timing_to_fsm,
        )

    # ZX 0xEB69..0xEB90
    def fn_directional_action_validate_target(
        self,
        HL_probe: BlockPtr,
        HL_pair: BlockPtr,
        B_mask: int,
        C_flags: int,
        *,
        defer_overlay_timing_to_fsm: bool = False,
    ) -> int:
        probe_ptr = HL_probe

        A_code = self._read_u8_ptr(probe_ptr) & 0x3F
        if A_code in (0x1B, 0x1C):
            self._write_u8_ptr(probe_ptr, self._read_u8_ptr(probe_ptr) ^ 0x07)
            return C_flags & 0xFF

        if defer_overlay_timing_to_fsm and self._fsm_step_active:
            overlay_ctx = self._fsm_overlay_ctx
            if "pre_frames_left" not in overlay_ctx:
                raise RuntimeError(
                    "FSM directional overlay deferral requires pre_frames_left in _fsm_overlay_ctx",
                )
            if "post_frames_left" not in overlay_ctx:
                raise RuntimeError(
                    "FSM directional overlay deferral requires post_frames_left in _fsm_overlay_ctx",
                )
            if "pre_frame_snapshots" not in overlay_ctx:
                overlay_ctx["pre_frame_snapshots"] = []
            if "post_frame_snapshots" not in overlay_ctx:
                overlay_ctx["post_frame_snapshots"] = []
            if "pre_frame_cursor" not in overlay_ctx:
                overlay_ctx["pre_frame_cursor"] = 0
            if "post_frame_cursor" not in overlay_ctx:
                overlay_ctx["post_frame_cursor"] = 0
            if not isinstance(overlay_ctx["pre_frame_snapshots"], list):
                raise RuntimeError("FSM directional overlay deferral requires list pre_frame_snapshots")
            if not isinstance(overlay_ctx["post_frame_snapshots"], list):
                raise RuntimeError("FSM directional overlay deferral requires list post_frame_snapshots")
            if not isinstance(overlay_ctx["pre_frame_cursor"], int):
                raise RuntimeError("FSM directional overlay deferral requires integer pre_frame_cursor")
            if not isinstance(overlay_ctx["post_frame_cursor"], int):
                raise RuntimeError("FSM directional overlay deferral requires integer post_frame_cursor")

        self.fn_main_pseudo_3d_map_render_pipeline()
        pre_frames = self.fn_pre_action_overlay_painter_ui_area(
            defer_timing_to_fsm=defer_overlay_timing_to_fsm,
        )

        self.patch_directional_action_mark_code = A_code
        pair_cell = self._read_u8_ptr(HL_pair)
        self._write_u8_ptr(HL_pair, (pair_cell & 0xC0) | (A_code & 0x3F))
        self.fn_convert_map_pointer_hl_row_column(HL_cell=HL_pair)

        probe_cell = self._read_u8_ptr(probe_ptr)
        self._write_u8_ptr(probe_ptr, (probe_cell & 0xC0) | 0x1B)
        self.var_runtime_current_cell_ptr = self._normalize_map_ptr(HL_pair)

        C_out = (C_flags | (B_mask & 0xFF)) & 0xFF

        self.fn_main_pseudo_3d_map_render_pipeline()
        post_frames = self.fn_post_action_overlay_painter_ui_area(
            defer_timing_to_fsm=defer_overlay_timing_to_fsm,
        )
        if defer_overlay_timing_to_fsm and self._fsm_step_active:
            overlay_ctx = self._fsm_overlay_ctx
            overlay_ctx["pre_frames_left"] = int(overlay_ctx["pre_frames_left"]) + int(pre_frames)
            overlay_ctx["post_frames_left"] = int(overlay_ctx["post_frames_left"]) + int(post_frames)
        return C_out

    # ZX 0xEBB6..0xEBBD
    def direction_bit_0_blocked_path_handler(self, HL_probe: BlockPtr, C_flags: int) -> int:
        return self.fn_if_probed_cell_is_empty_mark(
            HL_cell=HL_probe,
            B_bit_clear_mask=0xFE,
            C_blocked_bits=C_flags,
        )

    # ZX 0xEBBE..0xEBC5
    def direction_bit_1_blocked_path_handler(self, HL_probe: BlockPtr, C_flags: int) -> int:
        return self.fn_if_probed_cell_is_empty_mark(
            HL_cell=HL_probe,
            B_bit_clear_mask=0xFD,
            C_blocked_bits=C_flags,
        )

    # ZX 0xEBC6..0xEBCD
    def direction_bit_2_blocked_path_handler(self, HL_probe: BlockPtr, C_flags: int) -> int:
        return self.fn_if_probed_cell_is_empty_mark(
            HL_cell=HL_probe,
            B_bit_clear_mask=0xFB,
            C_blocked_bits=C_flags,
        )

    # ZX 0xEBCE..0xEBD5
    def direction_bit_3_blocked_path_handler(self, HL_probe: BlockPtr, C_flags: int) -> int:
        return self.fn_if_probed_cell_is_empty_mark(
            HL_cell=HL_probe,
            B_bit_clear_mask=0xF7,
            C_blocked_bits=C_flags,
        )

    # ZX 0xEBD6..0xEBEA
    def fn_if_probed_cell_is_empty_mark(
        self,
        HL_cell: BlockPtr,
        B_bit_clear_mask: int,
        C_blocked_bits: int,
    ) -> int:
        cell = self._read_u8_ptr(HL_cell)
        if (cell & 0x3F) != 0x00:
            return C_blocked_bits & 0xFF
        C_out = (C_blocked_bits & B_bit_clear_mask) & 0xFF
        self._write_u8_ptr(HL_cell, (cell & 0xC0) | 0x1B)
        return C_out

    # ZX 0xEBEB..0xEBEE
    def fn_convert_map_pointer_hl_row_column(self, HL_cell: BlockPtr) -> None:
        # Original routine used patched global-address base offsets (0xEBEF immediate).
        # Port keeps map pointers typed and derives row/col directly from map-local index.
        ptr = self._normalize_map_ptr(HL_cell)
        active_map = self.var_active_map_base_ptr.array
        if ptr.array is not active_map:
            raise ValueError("Map row/col conversion expects pointer into active map buffer")
        HL_off = ptr.index & 0xFFFF
        B_row = 0x00
        while HL_off >= 0x0032:
            HL_off -= 0x0032
            B_row = (B_row + 0x01) & 0xFF
        C_col = HL_off & 0xFF
        self.var_current_map_coords.set(C_col, B_row)

    # ZX 0xEC0A..0xEC63
    def autonomous_expansion_pass(self, *, run_tick: bool = True):
        if run_tick:
            self.fn_main_gameplay_tick_updater()
        queue_src = self.var_runtime_queue_head_3
        queue_dst = self.var_runtime_queue_head_4
        src_index = 0x00
        dst_index = 0x00

        while True:
            if src_index >= len(queue_src.entries):
                raise ValueError("Runtime object queue source exhausted before sentinel")
            a_state = queue_src.entries[src_index].state & 0xFF
            if a_state == 0xFF:
                self.expansion_commit(
                    queue_dst=queue_dst,
                    write_index=dst_index,
                    A_term=a_state,
                    run_tick=run_tick,
                )
                return
            if a_state == 0x00:
                src_index += 0x01
                continue

            if dst_index >= len(queue_dst.entries):
                raise ValueError("Runtime object queue destination overflow")
            src_entry = queue_src.entries[src_index]
            bc_cell = src_entry.cell_ptr
            if bc_cell is None:
                raise ValueError("Runtime object queue entry has non-zero state and null cell pointer")
            bc_cell = self._normalize_map_ptr(bc_cell)

            dst_entry = queue_dst.entries[dst_index]
            dst_entry.state = a_state
            dst_entry.cell_ptr = self._normalize_map_ptr(bc_cell)
            dst_index += 0x01
            a_spawn, dst_index = self.fn_spawn_state_selector_xec0a(
                BC_cell=bc_cell,
                queue_write_index=dst_index,
            )

            cell = self._read_u8_ptr(bc_cell)
            self._write_u8_ptr(bc_cell, (cell & 0xC0) | (a_spawn & 0x3F))

            dst_index = self.fn_queue_insert_helper_xec0a(
                HL_cell=bc_cell.add(0x0001),
                queue_dst=queue_dst,
                queue_write_index=dst_index,
                A_state=a_state,
            )
            dst_index = self.fn_queue_insert_helper_xec0a(
                HL_cell=bc_cell.add(-0x0001),
                queue_dst=queue_dst,
                queue_write_index=dst_index,
                A_state=a_state,
            )
            dst_index = self.fn_queue_insert_helper_xec0a(
                HL_cell=bc_cell.add(-0x0032),
                queue_dst=queue_dst,
                queue_write_index=dst_index,
                A_state=a_state,
            )
            dst_index = self.fn_queue_insert_helper_xec0a(
                HL_cell=bc_cell.add(0x0032),
                queue_dst=queue_dst,
                queue_write_index=dst_index,
                A_state=a_state,
            )
            src_index += 0x01

    # ZX 0xEC64..0xEC87
    def fn_queue_insert_helper_xec0a(
        self,
        HL_cell: BlockPtr,
        queue_dst: RuntimeObjectQueueBuffer,
        queue_write_index: int,
        A_state: int,
    ) -> int:
        hl_cell = self._normalize_map_ptr(HL_cell)
        write_index = int(queue_write_index)
        a_state = A_state & 0xFF

        cell = self._read_u8_ptr(hl_cell)
        if (cell & 0x3F) != 0x00:
            return write_index

        if write_index >= len(queue_dst.entries):
            raise ValueError("Runtime object queue destination overflow")
        dst_entry = queue_dst.entries[write_index]
        dst_entry.state = a_state
        dst_entry.cell_ptr = self._normalize_map_ptr(hl_cell)
        write_index += 0x01

        self._write_u8_ptr(hl_cell, (cell & 0xC0) | 0x19)
        self.fn_hud_triplet_increment_helper_bytes_xa8d8()
        return write_index

    # ZX 0xEC88..0xECB9
    def fn_spawn_state_selector_xec0a(
        self,
        BC_cell: BlockPtr,
        queue_write_index: int,
    ) -> tuple[int, int]:
        bc_cell_ptr = BC_cell
        write_index = int(queue_write_index)
        current_ptr = self.var_runtime_current_cell_ptr
        if not (
            bc_cell_ptr.array is current_ptr.array
            and bc_cell_ptr.index == current_ptr.index
        ):
            return 0x19, write_index

        write_index = max(0x00, write_index - 0x01)
        self.fn_hud_triplet_decrement_helper_bytes_xa8d8()

        a_step = self.var_runtime_move_delta & 0xFF
        if a_step == 0xFF:
            return 0x24, write_index
        if a_step == 0x32:
            return 0x21, write_index
        if a_step == 0x01:
            return 0x23, write_index
        return 0x22, write_index

    # ZX 0xECBA..0xED00
    def expansion_commit(
        self,
        queue_dst: RuntimeObjectQueueBuffer,
        write_index: int,
        A_term: int,
        *,
        run_tick: bool = True,
    ) -> None:
        if not (0 <= write_index < len(queue_dst.entries)):
            raise ValueError(f"Runtime queue write index out of range: {write_index}")
        term_entry = queue_dst.entries[write_index]
        term_entry.state = A_term & 0xFF
        term_entry.cell_ptr = None

        hl_q4 = self.var_runtime_queue_head_4
        de_q0 = self.var_runtime_queue_head_0
        self.var_runtime_queue_head_0 = hl_q4

        hl_q1 = self.var_runtime_queue_head_1
        self.var_runtime_queue_head_1 = de_q0

        de_q2 = self.var_runtime_queue_head_2
        self.var_runtime_queue_head_2 = hl_q1

        hl_q3 = self.var_runtime_queue_head_3
        self.var_runtime_queue_head_3 = de_q2
        self.var_runtime_queue_head_4 = hl_q3

        if run_tick:
            self.fn_main_gameplay_tick_updater()

        self.fn_queue_retag_helper_one_list(
            HL_queue=self.var_runtime_queue_head_0,
            E_code=0x19,
            D_xor=0x03,
        )
        self.fn_queue_retag_helper_one_list(
            HL_queue=self.var_runtime_queue_head_1,
            E_code=0x11,
            D_xor=0x00,
        )
        self.fn_queue_retag_helper_one_list(
            HL_queue=self.var_runtime_queue_head_2,
            E_code=0x0D,
            D_xor=0x00,
        )
        self.fn_queue_retag_helper_one_list(
            HL_queue=self.var_runtime_queue_head_3,
            E_code=0x01,
            D_xor=0x00,
        )

    # ZX 0xED01..0xED1B
    def fn_queue_retag_helper_one_list(
        self,
        HL_queue: RuntimeObjectQueueBuffer,
        E_code: int,
        D_xor: int,
    ) -> int:
        queue = HL_queue

        e_code = E_code & 0xFF
        d_xor = D_xor & 0xFF

        for queue_entry in queue.entries:
            A_state = queue_entry.state & 0xFF
            if A_state == 0xFF:
                return e_code & 0xFF
            if A_state != 0x00:
                BC_cell = queue_entry.cell_ptr
                if BC_cell is None:
                    raise ValueError("Runtime object queue entry has non-zero state and null cell pointer")
                A_cell = self._read_u8_ptr(BC_cell)
                self._write_u8_ptr(BC_cell, (A_cell & 0xC0) | (e_code & 0x3F))
                e_code ^= d_xor
        return e_code & 0xFF

    # ZX 0xED1C..0xED2E
    def fn_main_gameplay_tick_updater(self):
        if self._fsm_step_active:
            raise RuntimeError(
                "Legacy gameplay tick updater called during active FSM step; "
                "use FSM tick-stage states instead",
            )
        self.fn_main_gameplay_tick_update_core(E_code=0x26, D_xor=0x00)
        self._yield_gameplay_frame()
        self.fn_main_gameplay_tick_update_core(E_code=0x27, D_xor=0x00)
        self._yield_gameplay_frame()
        self.fn_main_gameplay_tick_update_core(E_code=0x28, D_xor=0x00)
        self._yield_gameplay_frame()
        self.fn_main_gameplay_tick_update_core(E_code=0x29, D_xor=0x00)
        self._yield_gameplay_frame()

    def _gameplay_tick_update_core_pre(self, *, E_code: int, D_xor: int) -> None:
        e_code = E_code & 0xFF
        d_xor = D_xor & 0xFF

        e_code = self.fn_queue_retag_helper_one_list(
            HL_queue=self.var_runtime_queue_head_0,
            E_code=e_code,
            D_xor=d_xor,
        )
        e_code = self.fn_queue_retag_helper_one_list(
            HL_queue=self.var_runtime_queue_head_1,
            E_code=e_code,
            D_xor=d_xor,
        )
        e_code = self.fn_queue_retag_helper_one_list(
            HL_queue=self.var_runtime_queue_head_2,
            E_code=e_code,
            D_xor=d_xor,
        )
        self.fn_queue_retag_helper_one_list(
            HL_queue=self.var_runtime_queue_head_3,
            E_code=e_code,
            D_xor=d_xor,
        )

        self._rom_beeper(de_ticks=0x001E, hl_period=0x00E6)
        if (self.var_runtime_objective_counter & 0xFF) != 0x00:
            self.fn_gameplay_movement_control_step()
        self.fn_process_transient_effect_queues_handlers_xe530()

    def _gameplay_tick_update_core_post(self) -> None:
        self.fn_active_transient_effect_executor()
        self.fn_main_pseudo_3d_map_render_pipeline()
        self._rom_beeper(de_ticks=0x0003, hl_period=0x00C8)

    # ZX 0xED2F..0xED77
    def fn_main_gameplay_tick_update_core(self, E_code, D_xor):
        if self._fsm_step_active:
            raise RuntimeError(
                "Legacy gameplay tick core called during active FSM step; "
                "use FSM tick-stage states instead",
            )
        self._gameplay_tick_update_core_pre(E_code=E_code, D_xor=D_xor)
        self.fn_patchable_callback_hook_frame_loop()
        self.fn_directional_interaction_dispatcher_using_pointer_table()
        self._gameplay_tick_update_core_post()

    # ZX 0xED7A..0xED99
    def fn_pre_action_overlay_painter_ui_area(self, *, defer_timing_to_fsm: bool = False) -> int:
        if self._fsm_step_active and not defer_timing_to_fsm:
            raise RuntimeError(
                "Legacy pre-overlay painter path called during active FSM step; "
                "expected defer_timing_to_fsm=True",
            )
        self.var_strip_fill_value = 0x12
        HL_left = self._display_attr_ptr(0x5821)
        DE_right = self._display_attr_ptr(0x585a)
        timing_debt = 0
        timing_frames = 0
        for _ in range(0x1A):
            timing_debt += self.fn_strip_fill_helper_xed7a_xed9a(HL_dst=HL_left, B_count=0x08)
            timing_debt += self.fn_strip_fill_helper_xed7a_xed9a(HL_dst=DE_right, B_count=0x07)
            while timing_debt >= STREAM_ENGINE_FRAME_BUDGET:
                timing_debt -= STREAM_ENGINE_FRAME_BUDGET
                if defer_timing_to_fsm and self._fsm_step_active:
                    timing_frames += 1
                    self._fsm_overlay_capture_snapshot(snapshots_key="pre_frame_snapshots")
                else:
                    self._yield_frame()
            HL_left = self._ptr_add(HL_left, 0x0001)
            DE_right = self._ptr_add(DE_right, -0x0001)
        return timing_frames

    # ZX 0xED9A..0xEDB9
    def fn_post_action_overlay_painter_ui_area(self, *, defer_timing_to_fsm: bool = False) -> int:
        if self._fsm_step_active and not defer_timing_to_fsm:
            raise RuntimeError(
                "Legacy post-overlay painter path called during active FSM step; "
                "expected defer_timing_to_fsm=True",
            )
        self.var_strip_fill_value = 0x39
        HL_left = self._display_attr_ptr(0x5841)
        DE_right = self._display_attr_ptr(0x583a)
        timing_debt = 0
        timing_frames = 0
        for _ in range(0x1A):
            timing_debt += self.fn_strip_fill_helper_xed7a_xed9a(HL_dst=HL_left, B_count=0x07)
            timing_debt += self.fn_strip_fill_helper_xed7a_xed9a(HL_dst=DE_right, B_count=0x08)
            while timing_debt >= STREAM_ENGINE_FRAME_BUDGET:
                timing_debt -= STREAM_ENGINE_FRAME_BUDGET
                if defer_timing_to_fsm and self._fsm_step_active:
                    timing_frames += 1
                    self._fsm_overlay_capture_snapshot(snapshots_key="post_frame_snapshots")
                else:
                    self._yield_frame()
            HL_left = self._ptr_add(HL_left, 0x0001)
            DE_right = self._ptr_add(DE_right, -0x0001)
        return timing_frames

    # ZX 0xEDBA..0xEDD0
    def fn_strip_fill_helper_xed7a_xed9a(self, HL_dst: BlockPtr, B_count: int) -> int:
        HL_row = HL_dst
        A_fill = self.var_strip_fill_value & 0xFF
        for _ in range(B_count & 0xFF):
            self._write_u8_ptr(HL_row, A_fill)
            HL_row = HL_row.add(0x0040)
        HL_period = 0x0100 | (HL_row.index & 0x00FF)
        return self._rom_beeper(de_ticks=0x0006, hl_period=HL_period)

    # ZX 0xEDD1..0xEDD3
    def fn_patchable_callback_hook_frame_loop(
        self,
        *,
        defer_halt_to_fsm: bool = False,
        defer_timing_to_fsm: bool = False,
    ) -> tuple[int, int]:
        if self._fsm_step_active and not (defer_halt_to_fsm or defer_timing_to_fsm):
            raise RuntimeError(
                "Legacy callback hook path called during active FSM step; "
                "expected defer_halt_to_fsm/defer_timing_to_fsm",
            )
        opcode = self.patch_callback_hook_opcode & 0xFF
        if opcode == 0xC9:
            return 0, 0
        if opcode == 0x2A:
            HL_cell = self.var_marker_event_cell_ptr
            return self.patchable_frame_callback_body(
                HL_cell=HL_cell,
                defer_halt_to_fsm=defer_halt_to_fsm,
                defer_timing_to_fsm=defer_timing_to_fsm,
            )
        raise ValueError(f"Unsupported callback hook opcode: 0x{opcode:02X}")

    def _set_patch_callback_hook_opcode(self, opcode: int) -> None:
        self.patch_callback_hook_opcode = opcode & 0xFF

    def _set_patch_gameplay_movement_step_opcode(self, opcode: int) -> None:
        self.patch_gameplay_movement_step_opcode = opcode & 0xFF

    # ZX 0xEDD4..0xEE91
    def patchable_frame_callback_body(
        self,
        HL_cell: BlockPtr,
        *,
        defer_halt_to_fsm: bool = False,
        defer_timing_to_fsm: bool = False,
    ) -> tuple[int, int]:
        timing_debt = 0
        timing_frames = 0

        def _consume_timing(cost: int) -> None:
            nonlocal timing_debt, timing_frames
            timing_debt += max(0, int(cost))
            if defer_timing_to_fsm and self._fsm_step_active:
                while timing_debt >= STREAM_ENGINE_FRAME_BUDGET:
                    timing_debt -= STREAM_ENGINE_FRAME_BUDGET
                    timing_frames += 1
                return
            while timing_debt >= STREAM_ENGINE_FRAME_BUDGET:
                timing_debt -= STREAM_ENGINE_FRAME_BUDGET
                self._yield_frame()

        hl_cell = HL_cell
        marker_idx = self.var_marker_index_state & 0xFF
        cell_code = self._read_u8_ptr(hl_cell)

        if ((marker_idx + 0x2E) & 0xFF) == cell_code:
            self.marker_advance_helper()
            return timing_frames, 0

        if cell_code < 0x21:
            self._set_patch_callback_hook_opcode(0xC9)
            return timing_frames, 0

        if cell_code >= 0x25:
            self._set_patch_callback_hook_opcode(0xC9)
        else:
            marker_slot = marker_idx if marker_idx <= 0x04 else 0x04
            marker_value = self.var_marker_counters.get(marker_slot)
            if marker_value != 0x00:
                self._set_patch_callback_hook_opcode(0xC9)
            else:
                self.var_marker_counters.set(marker_slot, 0x01)
                _consume_timing(
                    self._rom_beeper_sequence(
                        (
                            (0x0032, 0x0032),
                            (0x0064, 0x0064),
                        )
                    )
                )
                self.fn_hud_decimal_counter_animator_core()

        self.visible_cell_staging_preset_builder()

        marker_base = self.var_marker_counters
        if marker_base.is_clear(0x00):
            self.staging_buffer_scrub_entry_marker_value()
        if marker_base.is_clear(0x01):
            self.staging_buffer_scrub_entry_marker_value_2()
        if marker_base.is_clear(0x02):
            self.staging_buffer_scrub_entry_marker_value_3()
        if marker_base.is_clear(0x03):
            self.staging_buffer_scrub_entry_marker_value_4()
        if marker_base.is_clear(0x04):
            self.staging_buffer_scrub_entry_marker_value_5()

        self.fn_two_pass_global_scrub_helper()
        self._set_patch_callback_hook_opcode(0xC9)
        self.fn_render_pass_re_entry_stub()

        active_count = marker_base.active_count()
        if marker_base.all_active():
            self.all_markers_cleared_handler()

        if marker_base.any_active():
            for _ in range(active_count):
                self.fn_hud_decimal_counter_animator_core()
                _consume_timing(self._rom_beeper(de_ticks=0x0064, hl_period=0x00FA))

        # ZX 0xEE77: 65x HALT -> wait for 65 interrupt frames.
        if defer_halt_to_fsm and self._fsm_step_active:
            return timing_frames, 0x41
        self._yield_host_frames(0x41)
        return timing_frames, 0

    # ZX 0xEE92..0xEE96
    def staging_buffer_scrub_entry_marker_value(self):
        self.fn_staging_buffer_scrub_marker_5_entry(A_marker=0x01)
        return 0x00

    # ZX 0xEE97..0xEE9B
    def staging_buffer_scrub_entry_marker_value_2(self):
        self.fn_staging_buffer_scrub_marker_5_entry(A_marker=0x02)
        return 0x00

    # ZX 0xEE9C..0xEE9F
    def staging_buffer_scrub_entry_marker_value_3(self):
        return self.fn_staging_buffer_scrub_marker_5_entry(A_marker=0x03)

    # ZX 0xEEA0..0xEEA4
    def staging_buffer_scrub_entry_marker_value_4(self):
        return self.fn_staging_buffer_scrub_marker_5_entry(A_marker=0x04)

    # ZX 0xEEA5..0xEEA6
    def staging_buffer_scrub_entry_marker_value_5(self):
        return self.fn_staging_buffer_scrub_marker_5_entry(A_marker=0x05)

    # ZX 0xEEA7..0xEEB0
    def fn_staging_buffer_scrub_marker_5_entry(self, A_marker):
        marker = self._as_u8(A_marker)
        hl_cell = BlockPtr(
            self.var_renderer_workspace,
            RENDERER_WORKSPACE_OFF_VISIBLE_CELL_STAGING_LATTICE,
        )
        bc_left = 0x021C
        cond_opcode = self.patch_scrub_scanner_call_condition_opcode & 0xFF

        while bc_left != 0x0000:
            a_cell = self._read_u8_ptr(hl_cell)
            if cond_opcode == 0xCC:  # CALL Z
                do_call = (a_cell == marker)
            elif cond_opcode == 0xC4:  # CALL NZ
                do_call = (a_cell != marker)
            else:
                raise ValueError(
                    f"Unsupported scrub call-condition opcode: 0x{cond_opcode:02X}",
                )

            if do_call:
                self.scanner_write_helper(HL_cell=hl_cell)

            bc_left = (bc_left - 0x0001) & 0xFFFF
            if bc_left != 0x0000:
                hl_cell = hl_cell.add(0x0001)

        return 0x00

    # ZX 0xEEBE..0xEEBE
    def scanner_write_helper(self, HL_cell: BlockPtr) -> None:
        A_write = self.patch_scrub_scanner_write_value & 0xFF
        self._write_u8_ptr(HL_cell, A_write)

    # ZX 0xEEC1..0xEED8
    def fn_two_pass_global_scrub_helper(self):
        self.patch_scrub_scanner_write_value = 0x17
        self.patch_scrub_scanner_call_condition_opcode = 0xC4  # CALL NZ
        self.fn_staging_buffer_scrub_marker_5_entry(A_marker=0x00)
        self.patch_scrub_scanner_call_condition_opcode = 0xCC  # CALL Z
        self.patch_scrub_scanner_write_value = 0x00

    # ZX 0xEED9..0xEEF4
    def marker_advance_helper(self) -> None:
        if (self.var_runtime_phase_index & 0xFF) != 0x00:
            return
        A_marker = ((self.var_marker_index_state & 0xFF) + 0x01) & 0xFF
        if A_marker == 0x05:
            A_marker = 0x00
        self.var_marker_index_state = A_marker
        HL_cell = self.var_marker_event_cell_ptr
        self._write_u8_ptr(HL_cell, (A_marker + 0x2E) & 0xFF)

    # ZX 0xEEF5..0xEF2A
    def fn_hud_triplet_increment_helper_bytes_xa8d8(self):
        a_d0 = ((self.var_runtime_progress_byte_0 & 0xFF) + 0x01) & 0xFF
        if a_d0 != 0x0A:
            self.var_runtime_progress_byte_0 = a_d0
            self.fn_hud_digit_blit_selector_3(A_digit=a_d0)
            return

        self.var_runtime_progress_byte_0 = 0x00
        self.fn_hud_digit_blit_selector_3(A_digit=0x00)

        a_d1 = ((self.var_runtime_progress_byte_1 & 0xFF) + 0x01) & 0xFF
        if a_d1 != 0x0A:
            self.var_runtime_progress_byte_1 = a_d1
            self.fn_hud_digit_blit_selector_2(A_digit=a_d1)
            return

        self.var_runtime_progress_byte_1 = 0x00
        self.fn_hud_digit_blit_selector_2(A_digit=0x00)
        a_d2 = ((self.var_runtime_progress_byte_2 & 0xFF) + 0x01) & 0xFF
        self.var_runtime_progress_byte_2 = a_d2
        self.fn_hud_digit_blit_selector(A_digit=a_d2)

    # ZX 0xEF2B..0xEF5D
    def fn_hud_triplet_decrement_helper_bytes_xa8d8(self):
        a_d0 = self.var_runtime_progress_byte_0 & 0xFF
        if a_d0 != 0x00:
            a_d0 = (a_d0 - 0x01) & 0xFF
            self.var_runtime_progress_byte_0 = a_d0
            self.fn_hud_digit_blit_selector_3(A_digit=a_d0)
            return

        self.var_runtime_progress_byte_0 = 0x09
        self.fn_hud_digit_blit_selector_3(A_digit=0x09)

        a_d1 = self.var_runtime_progress_byte_1 & 0xFF
        if a_d1 != 0x00:
            a_d1 = (a_d1 - 0x01) & 0xFF
            self.var_runtime_progress_byte_1 = a_d1
            self.fn_hud_digit_blit_selector_2(A_digit=a_d1)
            return

        self.var_runtime_progress_byte_1 = 0x09
        self.fn_hud_digit_blit_selector_2(A_digit=0x09)
        a_d2 = ((self.var_runtime_progress_byte_2 & 0xFF) - 0x01) & 0xFF
        self.var_runtime_progress_byte_2 = a_d2
        self.fn_hud_digit_blit_selector(A_digit=a_d2)

    # ZX 0xEF5E..0xEF63
    def fn_hud_digit_blit_selector(self, A_digit):
        self.hud_digit_draw_core(A_digit=self._as_u8(A_digit), B_row=0x10, C_col=0x1D)

    # ZX 0xEF64..0xEF69
    def fn_hud_digit_blit_selector_2(self, A_digit):
        self.hud_digit_draw_core(A_digit=self._as_u8(A_digit), B_row=0x10, C_col=0x1E)

    # ZX 0xEF6A..0xEF6F
    def fn_hud_digit_blit_selector_3(self, A_digit):
        self.hud_digit_draw_core(A_digit=self._as_u8(A_digit), B_row=0x10, C_col=0x1F)

    # ZX 0xEF70..0xEF82
    def hud_digit_draw_core(self, A_digit: int | BlockPtr, B_row: int, C_col: int) -> BlockPtr:
        a = (self._as_u8(A_digit) + 0x11) & 0xFF
        glyph_bias_ptr = self._glyph_bias_ptr
        DE_src = glyph_bias_ptr.add(0x08 * a)
        DE_src = self.fn_routine_8_byte_screen_blit_primitive(DE_src=DE_src, B_row=B_row, C_col=C_col)
        return DE_src

    # ZX 0xEF83..0xEF86
    def visible_cell_staging_preset_builder(self) -> None:
        self.fn_visible_cell_staging_preset_core(
            IX_tpl=BlockPtr(self.const_staging_template_byte_table, 0x0000),
        )

    # ZX 0xEF87..0xEFB1
    def fn_visible_cell_staging_preset_core(self, IX_tpl: BlockPtr) -> None:
        self._fill_bytes_ptr(
            BlockPtr(
                self.var_renderer_workspace,
                RENDERER_WORKSPACE_OFF_VISIBLE_CELL_STAGING_LATTICE,
            ),
            0x024A,
            0x00,
        )
        A_phase = 0x10
        HL_dst, IX_tpl, A_phase = self.fn_visible_cell_staging_emit_pair_loop(
            HL_dst=self._visible_cell_staging_preset_row_ptr(0),
            IX_tpl=IX_tpl,
            A_phase=A_phase,
        )
        HL_dst, IX_tpl, A_phase = self.fn_visible_cell_staging_emit_pair_loop(
            HL_dst=self._visible_cell_staging_preset_row_ptr(1),
            IX_tpl=IX_tpl,
            A_phase=A_phase,
        )
        HL_dst, IX_tpl, A_phase = self.fn_visible_cell_staging_emit_pair_loop(
            HL_dst=self._visible_cell_staging_preset_row_ptr(2),
            IX_tpl=IX_tpl,
            A_phase=A_phase,
        )
        HL_dst, IX_tpl, A_phase = self.fn_visible_cell_staging_emit_pair_loop(
            HL_dst=self._visible_cell_staging_preset_row_ptr(3),
            IX_tpl=IX_tpl,
            A_phase=A_phase,
        )
        self.fn_visible_cell_staging_emit_pair_loop(
            HL_dst=self._visible_cell_staging_preset_row_ptr(4),
            IX_tpl=IX_tpl,
            A_phase=A_phase,
        )

    # ZX 0xEFB2..0xEFC6
    def fn_visible_cell_staging_emit_pair_loop(
        self,
        HL_dst: BlockPtr,
        IX_tpl: BlockPtr,
        A_phase: int,
    ) -> tuple[BlockPtr, BlockPtr, int]:
        dst_ptr = HL_dst
        src_ptr = IX_tpl
        A_phase = A_phase & 0xFF
        for _ in range(0x13):
            self._write_u8_ptr(dst_ptr, self._read_u8_ptr(src_ptr))
            A_phase ^= 0x1F
            dst_ptr = dst_ptr.add(-(A_phase & 0xFF))
            src_ptr = src_ptr.add(0x01)
        return dst_ptr, src_ptr, A_phase

    # ZX 0xEFC7..0xEFE6
    def all_markers_cleared_handler(self) -> None:
        self.var_marker_counters.clear()
        self._rom_beeper(de_ticks=0x00C8, hl_period=0x00FA)
        a_counter = self.var_runtime_objective_counter & 0xFF
        self.var_runtime_objective_counter = (a_counter + 0x01) & 0xFF
        self.fn_hud_strip_painter()

    # ZX 0xF050..0xF062
    def fn_periodic_scheduler_tick(self):
        HL_timer = (self.var_runtime_scheduler_timer - 0x0002) & 0xFFFF
        self.var_runtime_scheduler_timer = HL_timer
        if (HL_timer & 0x00FF) != 0x00FF:
            return
        A_step = (HL_timer >> 8) & 0xFF
        HL_meter = self._ptr_add(self._display_attr_ptr(0x5a85), A_step)
        script_base_off = int(self.patch_scheduler_script_base_ptr) & 0xFFFF
        script_idx = script_base_off + A_step
        if script_idx >= len(self.const_periodic_scheduler_script):
            raise ValueError(f"Scheduler script index out of range: {script_idx}")
        A_mask = self.const_periodic_scheduler_script[script_idx] & 0xFF
        self.const_periodic_scheduler_script[0x0000] = A_mask
        self._write_u8_ptr(HL_meter, 0x00)
        if A_mask & 0x01:
            if self._fsm_step_active:
                self._fsm_tick_ctx["pending_autonomous"] = True
                self._fsm_tick_ctx["pending_marker"] = bool(A_mask & 0x02)
                return
            self.scheduler_triggered_autonomous_step()
        if A_mask & 0x02:
            self.scheduler_triggered_marker_seeding()

    # ZX 0xF0C5..0xF0EC
    def scheduler_triggered_autonomous_step(self, *, run_tick: bool = True):
        self.autonomous_expansion_pass(run_tick=run_tick)
        if (self.var_runtime_progress_byte_2 & 0xFF) != 0x00:
            E_bias = 0x0A
        else:
            E_bias = self.var_runtime_progress_byte_1 & 0xFF
        self.fn_counter_rebalance_helper(queue_state=self.var_transient_queue_a, E_bias=E_bias)
        self.fn_counter_rebalance_helper(queue_state=self.var_transient_queue_c, E_bias=E_bias)
        self.fn_counter_rebalance_helper(queue_state=self.var_transient_queue_b, E_bias=E_bias)
        self.fn_rebuild_hud_meter_bars_counters_xa8c4()

    # ZX 0xF0ED..0xF107
    def fn_counter_rebalance_helper(self, queue_state: TransientQueueBuffer, E_bias: int) -> None:
        queue = queue_state
        queue_entries = queue.entries
        D_free = 0x00
        for queue_entry in queue_entries:
            if (queue_entry.state & 0xFF) == 0x00:
                D_free += 0x01

        A_target = ((queue.free_slots & 0xFF) + (E_bias & 0xFF)) & 0xFF
        queue.free_slots = A_target if A_target < D_free else D_free

    # ZX 0xF108..0xF12E
    def fn_hud_strip_painter(self):
        HL_top = self._display_attr_ptr(0x5a33)
        for _ in range(0x0C):
            self._write_u8_ptr(HL_top, 0x00)
            HL_top = self._ptr_add(HL_top, 0x0001)
        HL_bottom = self._ptr_add(HL_top, 0x001F)
        for _ in range(0x0C):
            self._write_u8_ptr(HL_bottom, 0x00)
            HL_bottom = self._ptr_add(HL_bottom, -0x0001)
        A_steps = self.var_runtime_objective_counter & 0xFF
        if A_steps == 0x00:
            return
        if A_steps >= 0x07:
            A_steps = self.progress_clamp_helper(A_progress=A_steps)
        for A_step in range(A_steps, 0x00, -0x01):
            self.fn_single_progress_step_painter(A_step=A_step)

    # ZX 0xF12F..0xF131
    def progress_clamp_helper(self, A_progress):
        return 0x06

    # ZX 0xF132..0xF148
    def fn_single_progress_step_painter(self, A_step):
        A_step = A_step & 0xFF
        A_step = ((A_step << 1) | (A_step >> 7)) & 0xFF
        HL_cell = self._ptr_add(self._display_attr_ptr(0x5a31), A_step)
        self._write_u8_ptr(HL_cell, 0x05)
        self._write_u8_ptr(self._ptr_add(HL_cell, 0x01), 0x05)
        self._write_u8_ptr(self._ptr_add(HL_cell, 0x20), 0x07)
        self._write_u8_ptr(self._ptr_add(HL_cell, 0x21), 0x07)

    # ZX 0xF149..0xF151
    def fn_scenario_preset_beeper_stream_engine(self):
        self.scenario_pointer_seeding_core(
            HL_stream_a=BlockPtr(self.const_scenario_preset_a_stream_1, 0x0000),
            DE_stream_b=BlockPtr(self.const_scenario_preset_a_stream_2, 0x0000),
            abort_on_keypress=True,
        )

    # ZX 0xF152..0xF15A
    def fn_scenario_preset_b_beeper_stream_engine(self):
        self.scenario_pointer_seeding_core(
            HL_stream_a=BlockPtr(self.const_scenario_preset_b_stream_1, 0x0000),
            DE_stream_b=BlockPtr(self.const_scenario_preset_b_stream_2, 0x0000),
            abort_on_keypress=True,
        )

    # ZX 0xF15B..0xF160
    def fn_scenario_preset_c(self):
        self.scenario_pointer_seeding_core(
            HL_stream_a=BlockPtr(self.const_scenario_preset_c_stream_1, 0x0000),
            DE_stream_b=BlockPtr(self.const_scenario_preset_c_stream_2, 0x0000),
            abort_on_keypress=True,
        )

    # ZX 0xF161..0xF173
    def scenario_pointer_seeding_core(
        self,
        HL_stream_a: BlockPtr,
        DE_stream_b: BlockPtr,
        *,
        abort_on_keypress: bool = True,
    ) -> None:
        self.patch_stream_player_default_stream_a_ptr = HL_stream_a
        self.patch_stream_player_default_stream_b_ptr = DE_stream_b
        self._stream_ptr_a = HL_stream_a
        self._stream_ptr_b = HL_stream_a.add(0x0001)
        self._stream_ptr_c = DE_stream_b
        self._stream_ptr_d = DE_stream_b.add(0x0001)
        self.scenario_intermission_beeper_stream_player_loop(
            abort_on_keypress=abort_on_keypress,
        )

    # ZX 0xF174..0xF274
    def gameplay_session_controller(self):
        if self._fsm_step_active:
            raise RuntimeError(
                "Legacy gameplay session controller called during active FSM step; "
                "use FSM gameplay states instead",
            )
        self.gameplay_screen_setup()
        self.fn_overlay_preset_selector()
        self._gameplay_session_loop_entry_f17a()

    def _gameplay_session_loop_entry_f17a(self) -> None:
        self.var_runtime_scheduler_timer = 0x1601
        self.var_runtime_progress_counter = 0x0A
        self.var_runtime_direction_mask = 0x00
        self._set_patch_callback_hook_opcode(0xC9)
        for queue in (
            self.var_transient_queue_a,
            self.var_transient_queue_b,
            self.var_transient_queue_c,
        ):
            for queue_entry in queue.entries:
                queue_entry.state = 0x00
                queue_entry.cell_ptr = None
        self.var_transient_queue_a.free_slots = 0x00
        self.var_transient_queue_b.free_slots = 0x00
        self.var_transient_queue_c.free_slots = 0x00
        self.fn_rebuild_hud_meter_bars_counters_xa8c4()
        if (self.var_active_map_mode & 0xFF) == 0x00:
            self.patch_scheduler_script_base_ptr = self.const_periodic_scheduler_step_4
            self.var_runtime_objective_counter = 0x06
            self.patch_queue_1_block_threshold_code = 0x50
            self.patch_queue_2_block_threshold_code = 0x50
            self.patch_queue_3_block_threshold_code = 0x50
            self.patch_queue_3_fallback_threshold_code = 0x50
            self.patch_queue_3_contact_branch_opcode = 0xC9
            self.fn_map_mode_setup_helper(DE_map=BlockPtr(self.var_level_map_mode_0, 0x0000))
        elif (self.var_active_map_mode & 0xFF) == 0x01:
            self.patch_scheduler_script_base_ptr = self.const_periodic_scheduler_step_3
            self.patch_queue_3_contact_branch_opcode = 0xC5
            self.fn_map_mode_setup_helper(DE_map=BlockPtr(self.var_level_map_mode_1, 0x0000))
            self.fn_active_map_mode_switch_entry_b()
            self.fn_overlay_preset_b_selector()
            self.patch_queue_1_block_threshold_code = 0x50
            self.patch_queue_2_block_threshold_code = 0x25
            self.patch_queue_3_block_threshold_code = 0x17
            self.patch_queue_3_fallback_threshold_code = 0x17
        else:
            self.patch_scheduler_script_base_ptr = self.const_periodic_scheduler_step_2
            self.patch_queue_3_contact_branch_opcode = 0xC5
            self.fn_map_mode_setup_helper(DE_map=BlockPtr(self.var_level_map_mode_2, 0x0000))
            self.fn_active_map_mode_switch_entry_a()
            self.fn_overlay_preset_c_selector()
            self.patch_queue_1_block_threshold_code = 0x17
            self.patch_queue_2_block_threshold_code = 0x25
            self.patch_queue_3_block_threshold_code = 0x17
            self.patch_queue_3_fallback_threshold_code = 0x17
        self.fn_scenario_preset_beeper_stream_engine()
        while True:
            self.per_frame_object_state_update_pass()
            self.fn_process_transient_effect_queues_handlers_xe530()
            self.fn_gameplay_movement_control_step()
            self.fn_directional_interaction_dispatcher_using_pointer_table()
            self.fn_patchable_callback_hook_frame_loop()
            self.fn_periodic_scheduler_tick()
            self.fn_main_pseudo_3d_map_render_pipeline()
            self._yield_gameplay_frame()
            if (
                (self.var_runtime_progress_byte_0 & 0xFF) == 0x00
                and (self.var_runtime_progress_byte_1 & 0xFF) == 0x00
                and (self.var_runtime_progress_byte_2 & 0xFF) == 0x00
            ):
                self.main_loop_level_complete_transition_path()
                return
            if ((self.var_runtime_scheduler_timer >> 8) & 0xFF) == 0x00:
                self.main_loop_failure_cleanup_exit_path()
                return
            if (self.var_runtime_objective_counter & 0xFF) == 0x00:
                self.main_loop_failure_cleanup_exit_path()
                return

    # ZX 0xF275..0xF27E
    def fn_map_mode_setup_helper(self, DE_map: BlockPtr) -> None:
        self.var_active_map_base_ptr = DE_map
        self.fn_scan_2500_byte_map_emit_selected(DE_map=DE_map)
        self.initialize_gameplay_runtime_structures_pointers_map()  # ASM tail-jump (JP 0xF2F4)

    # ZX 0xF27F..0xF291
    def fn_map_normalization_restore(self, HL_map: BlockPtr) -> None:
        self.normalize_2500_byte_map_place(HL_map=HL_map)
        for entry in self.var_saved_map_triplet_buffer:
            self._write_u8_ptr(HL_map.add(entry.cell_index), entry.cell_value)

    # ZX 0xF292..0xF2BA
    def normalize_2500_byte_map_place(self, HL_map: BlockPtr) -> None:
        HL_ptr = HL_map
        for i in range(0x09C4):
            A_cell = self._read_u8_ptr(HL_ptr)
            if A_cell in [0x17, 0x57, 0x97, 0xD7]:
                if i != (0x09C4 - 1):
                    HL_ptr = HL_ptr.add(0x01)
                continue
            A_cell = A_cell & 0xC0
            if A_cell == 0x00:
                self._write_u8_ptr(HL_ptr, 0x00)
            elif A_cell != 0xC0:
                self._write_u8_ptr(HL_ptr, A_cell)
            if i != (0x09C4 - 1):
                HL_ptr = HL_ptr.add(0x01)

    # ZX 0xF2BB..0xF2F1
    def fn_scan_2500_byte_map_emit_selected(self, DE_map: BlockPtr) -> None:
        max_restore_entries = 126  # derived from ZX 0xB734..0xB8AF triplet+sentinel capacity
        restore_log = self.var_saved_map_triplet_buffer
        restore_log.clear()
        DE_ptr = DE_map

        for i in range(0x09C4):
            A_cell = self._read_u8_ptr(DE_ptr)
            A_low6 = A_cell & 0x3F
            if A_low6 in [0x01, 0x0D, 0x11, 0x18, 0x19, 0x1B, 0x21]:
                if len(restore_log) >= max_restore_entries:
                    raise ValueError("Map restore log overflow (typed buffer capacity exceeded)")
                restore_log.append(
                    MapRestoreEntry(
                        cell_value=A_cell & 0xFF,
                        cell_index=DE_ptr.index,
                    ),
                )
            if i != (0x09C4 - 1):
                DE_ptr = DE_ptr.add(0x01)

    # ZX 0xF2F4..0xF386
    def initialize_gameplay_runtime_structures_pointers_map(self) -> None:
        self.var_runtime_queue_head_0 = self.var_runtime_object_queue_0
        self.var_runtime_queue_head_1 = self.var_runtime_object_queue_1
        self.var_runtime_queue_head_2 = self.var_runtime_object_queue_2
        self.var_runtime_queue_head_3 = self.var_runtime_object_queue_3
        self.var_runtime_queue_head_4 = self.var_runtime_object_queue_4
        self.var_transient_effect_ptr = self.var_active_map_base_ptr
        self.var_marker_event_cell_ptr = self.var_active_map_base_ptr

        self.var_runtime_progress_byte_0 = 0x04
        self.var_runtime_progress_byte_1 = 0x00
        self.var_runtime_progress_byte_2 = 0x00
        self.var_transient_effect_state = 0x00

        self.fn_hud_digit_blit_selector(A_digit=0x00)
        self.fn_hud_digit_blit_selector_2(A_digit=0x00)
        self.fn_hud_digit_blit_selector_3(A_digit=0x04)
        self.fn_clear_transient_object_queues_xc5b2()

        HL_cell = self.fn_find_first_occurrence_cell_code_d(D_code=0x01)
        self.var_runtime_object_queue_0.entries[0x00].state = 0x01
        self.var_runtime_object_queue_1.entries[0x00].state = 0x01
        self.var_runtime_object_queue_2.entries[0x00].state = 0x01
        self.var_runtime_object_queue_3.entries[0x00].state = 0x01
        self.var_runtime_queue_head_3.entries[0x00].cell_ptr = HL_cell
        self.var_runtime_queue_head_2.entries[0x00].cell_ptr = self.fn_find_first_occurrence_cell_code_d(
            D_code=0x0D,
        )
        self.var_runtime_queue_head_1.entries[0x00].cell_ptr = self.fn_find_first_occurrence_cell_code_d(
            D_code=0x11,
        )
        self.var_runtime_queue_head_0.entries[0x00].cell_ptr = self.fn_find_first_occurrence_cell_code_d(
            D_code=0x19,
        )

        HL_ptr = self.fn_find_first_occurrence_cell_code_d(D_code=0x1B)
        self.var_runtime_dir_ptr_up_cell = HL_ptr
        HL_ptr = self.fn_find_first_cell_code_in_map_loop(HL_scan=HL_ptr.add(0x0001), D_code=0x1B)
        self.var_runtime_dir_ptr_down_cell = HL_ptr
        HL_ptr = self.fn_find_first_cell_code_in_map_loop(HL_scan=HL_ptr.add(0x0001), D_code=0x1B)
        self.var_runtime_dir_ptr_right_cell = HL_ptr
        HL_ptr = self.fn_find_first_cell_code_in_map_loop(HL_scan=HL_ptr.add(0x0001), D_code=0x1B)
        self.var_runtime_dir_ptr_left_cell = HL_ptr
        self.var_runtime_direction_mask = 0x00

        HL_cell = self.fn_find_first_occurrence_cell_code_d(D_code=0x21)
        self.var_runtime_current_cell_ptr = HL_cell
        HL_idx = HL_cell.index
        B_row = 0x00
        while HL_idx >= 0x0032:
            HL_idx = (HL_idx - 0x0032) & 0xFFFF
            B_row = (B_row + 0x01) & 0xFF
        self.var_current_map_coords.set(HL_idx, B_row)

        # ZX 0xF3A3 stores A after the row/column conversion loop. At that
        # point A is zero, so gameplay starts with "no prior move" until the
        # player actually commits a movement step.
        self.var_runtime_move_delta = 0x0000
        self.var_runtime_move_state_code = 0x1C
        # NOTE: original 0xF387 map-base immediate is represented semantically by typed active-map pointers.

    # ZX 0xF3AC..0xF3AE
    def fn_find_first_occurrence_cell_code_d(self, D_code) -> BlockPtr:
        HL_scan = self.var_active_map_base_ptr
        return self.fn_find_first_cell_code_in_map_loop(HL_scan=HL_scan, D_code=D_code)

    # ZX 0xF3AF..0xF3BD
    def fn_find_first_cell_code_in_map_loop(self, HL_scan: BlockPtr, D_code) -> BlockPtr:
        HL_ptr = HL_scan

        D_match = D_code & 0xFF
        for i in range(0x09C4):
            if (self._read_u8_ptr(HL_ptr) & 0x3F) == D_match:
                return HL_ptr
            if i != (0x09C4 - 1):
                HL_ptr = HL_ptr.add(0x01)
        return HL_ptr.add(0x01)

    # ZX 0xF3BE..0xF3CC
    def fn_clear_transient_object_queues_xc5b2(self):
        queue: RuntimeObjectQueueBuffer
        for queue in (
            self.var_runtime_object_queue_0,
            self.var_runtime_object_queue_1,
            self.var_runtime_object_queue_2,
            self.var_runtime_object_queue_3,
            self.var_runtime_object_queue_4,
        ):
            for queue_entry in queue.entries:
                queue_entry.state = 0xFF
                queue_entry.cell_ptr = None

    # ZX 0xF3CD..0xF3E4
    def fn_rectangular_panel_fill_helper(self, A_fill):
        HL_row = self._display_attr_ptr(0x5821)
        fill = self._as_u8(A_fill)
        for _ in range(0x0F):
            self._fill_bytes_ptr(HL_row, 0x1A, fill)
            HL_row = self._ptr_add(HL_row, 0x20)
        self.fn_paced_beeper_helper_transitions_panel_fill()

    # ZX 0xF3E5..0xF407
    def fn_active_map_mode_switch_handler(self) -> None:
        a_mode = self.var_active_map_mode & 0xFF
        if a_mode == 0x00:
            self.fn_map_normalization_restore(HL_map=BlockPtr(self.var_level_map_mode_0, 0x0000))
            return
        if a_mode == 0x01:
            self.fn_map_normalization_restore(HL_map=BlockPtr(self.var_level_map_mode_1, 0x0000))
            self.fn_active_map_mode_switch_entry_b()
        else:
            self.fn_map_normalization_restore(HL_map=BlockPtr(self.var_level_map_mode_2, 0x0000))
            self.fn_active_map_mode_switch_entry_a()

    # ZX 0xF408..0xF410
    def fn_active_map_mode_switch_entry_a(self):
        return self.sprite_bank_swap_core(
            HL_active_bank=BlockPtr(self.var_active_sprite_subset_bank, 0x0000),
            DE_selected_bank=BlockPtr(self.const_sprite_subset_bank_b, 0x0000),
        )

    # ZX 0xF411..0xF419
    def fn_active_map_mode_switch_entry_b(self):
        return self.sprite_bank_swap_core(
            HL_active_bank=BlockPtr(self.var_active_sprite_subset_bank, 0x0000),
            DE_selected_bank=BlockPtr(self.const_sprite_subset_bank_a, 0x0000),
        )

    # ZX 0xF41A..0xF42A
    def sprite_bank_swap_core(self, HL_active_bank: BlockPtr, DE_selected_bank: BlockPtr) -> None:
        HL_ptr = HL_active_bank
        DE_ptr = DE_selected_bank

        for i in range(0x0680):
            A_hl = self._read_u8_ptr(HL_ptr)
            A_de = self._read_u8_ptr(DE_ptr)
            self._write_u8_ptr(HL_ptr, A_de)
            self._write_u8_ptr(DE_ptr, A_hl)
            if i != (0x0680 - 1):
                HL_ptr = HL_ptr.add(0x01)
                DE_ptr = DE_ptr.add(0x01)

    # ZX 0xF42B..0xF461
    def main_loop_failure_cleanup_exit_path(self) -> None:
        self._set_patch_gameplay_movement_step_opcode(0xC9)
        HL_cell = self.var_runtime_current_cell_ptr
        self._write_u8_ptr(HL_cell, self._read_u8_ptr(HL_cell) & 0xC0)
        while True:
            self.fn_periodic_scheduler_tick()
            if ((self.var_runtime_scheduler_timer >> 8) & 0xFF) == 0x00:
                break
        self._set_patch_gameplay_movement_step_opcode(0x3A)
        self.fn_rectangular_panel_fill_helper(A_fill=0x00)
        self.fn_draw_mission_status_panel_bitmap_chunk()
        self.fn_transition_beeper_helper()
        self.fn_frame_delay_loop()
        self.fn_active_map_mode_switch_handler()
        self.high_score_editor_init()
        self.fn_high_score_table_draw_routine()
        # Prevent immediate skip of high-score intermission when a gameplay key
        # is still held across the transition.
        self._wait_keyboard_release()
        self.fn_scenario_preset_c()
        self.top_level_pre_game_control_loop()

    # ZX 0xF462..0xF4A3
    def main_loop_level_complete_transition_path(self) -> None:
        self.fn_active_map_mode_switch_handler()
        self.fn_level_transition_wait_loop()
        next_mode = ((self.var_active_map_mode & 0xFF) + 0x01) & 0xFF
        self.var_active_map_mode = next_mode
        if next_mode != 0x03:
            self.fn_transition_beeper_entry_a()
            self._gameplay_session_loop_entry_f17a()
            return
        self.fn_stretched_text_symbol_stream_printer(HL_stream=BlockPtr(self.str_ending_text_stream_1, 0x0000), B_row=0x03, C_col=0x05)
        self.fn_stretched_text_symbol_stream_printer(HL_stream=BlockPtr(self.str_ending_text_stream_2, 0x0000), B_row=0x06, C_col=0x07)
        self.fn_stretched_text_symbol_stream_printer(HL_stream=BlockPtr(self.str_ending_text_stream_3, 0x0000), B_row=0x09, C_col=0x06)
        self.fn_stretched_text_symbol_stream_printer(HL_stream=BlockPtr(self.str_ending_text_stream_4, 0x0000), B_row=0x0C, C_col=0x0A)
        self.fn_scenario_preset_beeper_stream_engine()
        self.high_score_editor_init()
        self.fn_high_score_table_draw_routine()
        # Prevent immediate skip of high-score intermission when a gameplay key
        # is still held across the transition.
        self._wait_keyboard_release()
        self.fn_scenario_preset_c()
        self.top_level_pre_game_control_loop()

    # ZX 0xF4A4..0xF4B4
    def fn_level_transition_wait_loop(self):
        self._level_complete_roll_audio_frame_sync = True
        try:
            steps_done = 0
            total_steps = LEVEL_COMPLETE_ROLL_TOTAL_STEPS
            total_frames = LEVEL_COMPLETE_ROLL_TARGET_FRAMES
            for frame_idx in range(total_frames):
                next_steps = ((frame_idx + 0x01) * total_steps) // total_frames
                steps_this_frame = next_steps - steps_done
                for _ in range(steps_this_frame):
                    self.fn_hud_decimal_counter_animator()
                self.fn_paced_beeper_helper_transitions_panel_fill()
                self._yield_frame()
                steps_done = next_steps
        finally:
            self._level_complete_roll_audio_frame_sync = False

    # ZX 0xF4B5..0xF4CF
    def fn_paced_beeper_helper_transitions_panel_fill(self):
        if self._level_complete_roll_audio_frame_sync:
            # Frame-synced roll-up uses one audible packet per frame to avoid
            # backend quantization stretching transition audio beyond visuals.
            self._rom_beeper(de_ticks=0x0005, hl_period=0x0198)
            return
        packets: list[tuple[int, int]] = []
        hl_period = 0x0190
        for _ in range(0x05):
            packets.append((0x0001, hl_period))
            hl_period = (hl_period + 0x0004) & 0xFFFF
        self._rom_beeper_sequence(tuple(packets))

    # ZX 0xF4D0..0xF505
    def fn_draw_mission_status_panel_bitmap_chunk(self) -> None:
        DE_src = BlockPtr(self.const_mission_panel_tile_strip, 0x0000)
        for B_row in range(0x06, 0x0A):
            for C_col in range(0x01, 0x1B):
                DE_src = self.fn_routine_8_byte_screen_blit_primitive(
                    DE_src=DE_src,
                    B_row=B_row,
                    C_col=C_col,
                )
        HL_row = self._display_attr_ptr(0x58c1)
        for _ in range(0x04):
            self._fill_bytes_ptr(HL_row, 0x1A, 0x06)
            HL_row = self._ptr_add(HL_row, 0x20)

    # ZX 0xF506..0xF50E
    def fn_transition_beeper_helper(self):
        self._rom_beeper_sequence(
            (
                (0x0064, 0x012C),
                (0x00C8, 0x00C8),
            )
        )

    # ZX 0xF50F..0xF518
    def fn_transition_beeper_entry_a(self):
        self._rom_beeper(de_ticks=0x00C8, hl_period=0x00C8)

    # ZX 0xF519..0xF53C
    def scheduler_triggered_marker_seeding(self) -> None:
        hook_opcode = self.patch_callback_hook_opcode & 0xFF
        if hook_opcode != 0xC9:
            return

        A_mode = self.var_active_map_mode & 0xFF
        if A_mode == 0x00:
            HL_map_base = BlockPtr(self.var_level_map_mode_0, 0x0000)
        elif A_mode == 0x01:
            HL_map_base = BlockPtr(self.var_level_map_mode_1, 0x0000)
        else:
            HL_map_base = BlockPtr(self.var_level_map_mode_2, 0x0000)
        self.patch_marker_seed_map_base_ptr = HL_map_base

        timer_lo = self.var_runtime_scheduler_timer & 0xFF
        HL_probe = self.patch_marker_seed_map_base_ptr
        for _ in range(0x10000):
            E_rand = self._next_r_register()
            DE_off = ((((timer_lo + E_rand) & 0x07) << 8) | E_rand) & 0xFFFF
            HL_probe = self.patch_marker_seed_map_base_ptr.add(DE_off)
            if self._read_u8_ptr(HL_probe) == 0x00:
                break
        else:
            raise RuntimeError("scheduler_triggered_marker_seeding: no empty map cell found")

        self.var_marker_event_cell_ptr = self._normalize_map_ptr(HL_probe)
        self._write_u8_ptr(HL_probe, self._read_u8_ptr(HL_probe) | 0x2E)
        self._set_patch_callback_hook_opcode(0x2A)
        self.var_marker_index_state = 0x00
        self._rom_beeper(de_ticks=0x001E, hl_period=0x012C)

    # ZX 0xF568..0xF5AF
    def gameplay_screen_setup(self) -> None:
        self._fill_bytes_ptr(BlockPtr(self.var_display_bitmap_ram, 0x0000), 0x1000, 0x00)
        self._fill_bytes_ptr(BlockPtr(self.var_display_attribute_ram, 0x0000), 0x0200, 0x39)
        self.fn_draw_static_gameplay_frame_ui_decorations()
        self._write_bytes_ptr(
            BlockPtr(self.var_display_bitmap_ram, self.var_display_bitmap_mission_panel_dst_5000),
            self._read_bytes(BlockPtr(self.const_mission_panel_bitmap_source, 0x0000), 0x0800),
        )
        self._write_bytes_ptr(
            self._display_attr_ptr(0x5a00),
            self._read_bytes(BlockPtr(self.const_mission_panel_attr_source, 0x0000), 0x0100),
        )
        # ROM range clear at 0xA8B6..0xA8E8, expressed as explicit block writes
        # to preserve block-boundary safety rules.
        self._fill_bytes_ptr(BlockPtr(self.var_runtime_control_core, 0x0004), 0x25, 0x00)
        self.var_runtime_progress_byte_0 = 0x00
        self.var_runtime_progress_byte_1 = 0x00
        self.var_runtime_progress_byte_2 = 0x00
        self.var_active_map_mode = 0x00
        self.var_action_effect_flags = 0x00
        self.var_strip_fill_value = 0x00
        self.var_current_map_coords.set(0x00, 0x00)
        self.var_marker_event_cell_ptr = self.var_active_map_base_ptr
        self.var_marker_index_state = 0x00
        self.var_marker_counters.clear()
        self.var_menu_selection_index = 0x00
        # Pre-game overlay render (F72D -> A889) expects a valid current map cell.
        # Seed it from mode-0 map before F17A performs full map-mode setup.
        self.var_active_map_base_ptr = BlockPtr(self.var_level_map_mode_0, 0x0000)
        HL_seed = self.fn_find_first_cell_code_in_map_loop(
            HL_scan=self.var_active_map_base_ptr,
            D_code=0x21,
        )
        if 0 <= HL_seed.index < 0x09C4:
            self.var_runtime_current_cell_ptr = HL_seed
            HL_idx = HL_seed.index
            B_row = 0x00
            while HL_idx >= 0x0032:
                HL_idx = (HL_idx - 0x0032) & 0xFFFF
                B_row = (B_row + 0x01) & 0xFF
            self.var_current_map_coords.set(HL_idx, B_row)
        self.var_action_effect_flags = 0x40
        self.fn_gameplay_movement_overlay_step_entry_e14c()

    # ZX 0xF5B0..0xF637
    def fn_draw_static_gameplay_frame_ui_decorations(self):
        self.fn_draw_framed_ui_box_using_bit(A_w=0x1A, A_h=0x0F, B_row=0x00, C_col=0x00)
        self.fn_draw_framed_ui_box_using_bit(A_w=0x02, A_h=0x02, B_row=0x00, C_col=0x1C)
        self.fn_draw_framed_ui_box_inner(B_row=0x04, C_col=0x1C)
        self.fn_draw_framed_ui_box_inner(B_row=0x08, C_col=0x1C)
        self.fn_draw_framed_ui_box_inner(B_row=0x0C, C_col=0x1C)

        self._fill_bytes_ptr(BlockPtr(self.var_display_attribute_ram, 0x0000), 0x001C, 0x28)
        self.fn_draw_vertical_attribute_stripe(
            HL_attr=self._ptr_add(self._display_attr_ptr(0x581c), -0x0001),
        )
        self.fn_draw_vertical_attribute_stripe(HL_attr=BlockPtr(self.var_display_attribute_ram, 0x0000))

        HL_attr = self._display_attr_ptr(0x581c)
        for _ in range(0x10):
            self._fill_bytes_ptr(HL_attr, 0x04, 0x20)
            # Advance to next attribute row, same column.
            HL_attr = self._ptr_add(HL_attr, 0x0020)

        self.fn_draw_2x2_attribute_block_fill_byte(HL_attr=self._display_attr_ptr(0x583d), A_fill=0x39)
        self.fn_draw_2x2_attribute_block_fill_byte(HL_attr=self._display_attr_ptr(0x58bd), A_fill=0x05)
        self.fn_draw_2x2_attribute_block_fill_byte(HL_attr=self._display_attr_ptr(0x593d), A_fill=0x06)
        self.fn_draw_2x2_attribute_block_fill_byte(HL_attr=self._display_attr_ptr(0x59bd), A_fill=0x07)

        DE_src = BlockPtr(self.const_mission_frame_pattern_source, 0x0000)
        DE_src = self.fn_draw_static_ui_frame_entry(DE_src=DE_src, B_row=0x01, C_col=0x1D)
        DE_src = self.fn_draw_static_ui_frame_entry(DE_src=DE_src, B_row=0x05, C_col=0x1D)
        DE_src = self.fn_draw_static_ui_frame_entry(DE_src=DE_src, B_row=0x09, C_col=0x1D)
        self.fn_draw_static_ui_frame_entry(DE_src=DE_src, B_row=0x0D, C_col=0x1D)

    # ZX 0xF638..0xF646
    def fn_draw_static_ui_frame_entry(self, DE_src: BlockPtr, B_row: int, C_col: int) -> BlockPtr:
        B = self._as_u8(B_row)
        C = self._as_u8(C_col)
        DE_src = self.fn_secondary_8_byte_screen_blit_primitive(DE_src=DE_src, B_row=B, C_col=C)
        C = (C + 0x01) & 0xFF
        DE_src = self.fn_secondary_8_byte_screen_blit_primitive(DE_src=DE_src, B_row=B, C_col=C)
        B = (B + 0x01) & 0xFF
        DE_src = self.fn_secondary_8_byte_screen_blit_primitive(DE_src=DE_src, B_row=B, C_col=C)
        C = (C - 0x01) & 0xFF
        DE_src = self.fn_secondary_8_byte_screen_blit_primitive(DE_src=DE_src, B_row=B, C_col=C)
        return DE_src

    # ZX 0xF647..0xF652
    def fn_draw_vertical_attribute_stripe(self, HL_attr: BlockPtr) -> None:
        HL_ptr = HL_attr
        for i in range(0x10):
            self._write_u8_ptr(HL_ptr, 0x28)
            if i != (0x10 - 1):
                HL_ptr = HL_ptr.add(0x0020)

    # ZX 0xF653..0xF659
    def fn_draw_framed_ui_box_using_bit(self, A_w: int, A_h: int, B_row: int, C_col: int) -> None:
        self.var_runtime_ui_frame_params.width = A_w & 0xFF
        self.var_runtime_ui_frame_params.height = A_h & 0xFF
        self.fn_draw_framed_ui_box_inner(B_row=(B_row & 0xFF), C_col=(C_col & 0xFF))

    # ZX 0xF65A..0xF6A4
    def fn_draw_framed_ui_box_inner(self, B_row: int, C_col: int) -> None:
        A_w = self.var_runtime_ui_frame_params.width & 0xFF
        A_h = self.var_runtime_ui_frame_params.height & 0xFF
        ui_frag_base = self.const_ui_frame_bitmap_fragments
        self.fn_secondary_8_byte_screen_blit_primitive(
            DE_src=BlockPtr(ui_frag_base, 0x0000),
            B_row=B_row,
            C_col=C_col,
        )
        C_col += 0x01
        self.fn_repeat_call_helper_xf6fa_along_direction(
            A_span=A_w,
            DE_src=BlockPtr(ui_frag_base, self.const_ui_frame_bitmap_fragment_2),
            B_row=B_row,
            C_col=C_col,
        )
        self.fn_secondary_8_byte_screen_blit_primitive(
            DE_src=BlockPtr(ui_frag_base, self.const_ui_frame_bitmap_fragment_3),
            B_row=B_row,
            C_col=C_col + A_w,
        )
        B_row += 0x01
        self.fn_draw_framed_ui_box_tail_entry(
            A_span=A_h,
            DE_src=BlockPtr(ui_frag_base, self.const_ui_frame_bitmap_fragment_4),
            B_row=B_row,
            C_col=C_col + A_w,
        )
        self.fn_secondary_8_byte_screen_blit_primitive(
            DE_src=BlockPtr(ui_frag_base, self.const_ui_frame_bitmap_fragment_5),
            B_row=B_row + A_h,
            C_col=C_col + A_w,
        )
        self.fn_repeat_call_helper_xf6fa_along_direction(
            A_span=A_w,
            DE_src=BlockPtr(ui_frag_base, self.const_ui_frame_bitmap_fragment_2),
            B_row=B_row + A_h,
            C_col=C_col,
        )
        self.fn_secondary_8_byte_screen_blit_primitive(
            DE_src=BlockPtr(ui_frag_base, self.const_ui_frame_bitmap_fragment_6),
            B_row=B_row + A_h,
            C_col=C_col - 0x01,
        )
        self.fn_draw_framed_ui_box_tail_entry(
            A_span=A_h,
            DE_src=BlockPtr(ui_frag_base, self.const_ui_frame_bitmap_fragment_4),
            B_row=B_row,
            C_col=C_col - 0x01,
        )

    # ZX 0xF6A5..0xF6B0
    def fn_draw_framed_ui_box_tail_entry(self, A_span: int | BlockPtr, DE_src: BlockPtr, B_row: int, C_col: int) -> None:
        A = self._as_u8(A_span)
        B = self._as_u8(B_row)
        C = self._as_u8(C_col)
        while True:
            self.fn_secondary_8_byte_screen_blit_primitive(DE_src=DE_src, B_row=B, C_col=C)
            B = (B + 0x01) & 0xFF
            A = (A - 0x01) & 0xFF
            if A == 0x00:
                return

    # ZX 0xF6B1..0xF6BB
    def fn_draw_2x2_attribute_block_fill_byte(self, HL_attr: BlockPtr, A_fill: int) -> None:
        HL_ptr = HL_attr
        A_byte = A_fill & 0xFF
        self._write_u8_ptr(HL_ptr, A_byte)
        self._write_u8_ptr(HL_ptr.add(0x01), A_byte)
        self._write_u8_ptr(HL_ptr.add(0x20), A_byte)
        self._write_u8_ptr(HL_ptr.add(0x21), A_byte)

    # ZX 0xF6BC..0xF6C7
    def fn_repeat_call_helper_xf6fa_along_direction(
        self,
        A_span: int | BlockPtr,
        DE_src: BlockPtr,
        B_row: int,
        C_col: int,
    ) -> None:
        A = self._as_u8(A_span)
        B = self._as_u8(B_row)
        C = self._as_u8(C_col)
        while True:
            self.fn_secondary_8_byte_screen_blit_primitive(DE_src=DE_src, B_row=B, C_col=C)
            C = (C + 0x01) & 0xFF
            A = (A - 0x01) & 0xFF
            if A == 0x00:
                return

    # ZX 0xF6FA..0xF72C
    def fn_secondary_8_byte_screen_blit_primitive(self, DE_src: BlockPtr, B_row: int, C_col: int) -> BlockPtr:
        return self.fn_routine_8_byte_screen_blit_primitive(
            DE_src=DE_src,
            B_row=B_row,
            C_col=C_col,
        )

    # ZX 0xF72D..0xF731
    def fn_overlay_preset_selector(self) -> None:
        self.fn_overlay_legend_refresh_pipeline(triplets=self.const_overlay_preset_a_triplets)

    # ZX 0xF732..0xF739
    def fn_overlay_preset_b_selector(self) -> None:
        self.copy_28_byte_status_string_template()
        self.fn_overlay_legend_refresh_pipeline(triplets=self.const_overlay_preset_b_triplets)

    # ZX 0xF73A..0xF73F
    def fn_overlay_preset_c_selector(self) -> None:
        self.copy_28_byte_status_string_template()
        self.fn_overlay_legend_refresh_pipeline(triplets=self.const_overlay_preset_c_triplets)

    # ZX 0xF740..0xF76B
    def fn_overlay_legend_refresh_pipeline(self, triplets: tuple[OverlayTriplet, ...]) -> None:
        if len(triplets) != 0x05:
            raise ValueError(f"Expected 5 overlay triplets, got {len(triplets)}")

        dst_offsets = (
            self.const_overlay_template_row_0_triplet_dst,
            self.const_overlay_template_row_1_triplet_dst,
            self.const_overlay_template_row_2_triplet_dst,
            self.const_overlay_template_row_3_triplet_dst,
            self.const_overlay_template_row_4_triplet_dst,
        )
        triplet_stream = bytearray(0x0F)
        for i, triplet in enumerate(triplets):
            base = i * 0x03
            triplet_stream[base + 0x00] = triplet.byte_0 & 0xFF
            triplet_stream[base + 0x01] = triplet.byte_1 & 0xFF
            triplet_stream[base + 0x02] = triplet.byte_2 & 0xFF

        DE_src = BlockPtr(triplet_stream, 0x0000)
        for dst_off in dst_offsets:
            DE_src = self.fn_copy_one_3_byte_triplet_de(
                HL_dst=BlockPtr(self.const_overlay_template_payload, dst_off),
                DE_src=DE_src,
            )

        self.fn_visible_cell_staging_preset_core(IX_tpl=BlockPtr(self.const_overlay_template_payload, 0x0000))
        self.fn_floor_texture_selector_pattern_setup_active()
        self.fn_render_pass_re_entry_stub()

    # ZX 0xF76C..0xF777
    def fn_copy_one_3_byte_triplet_de(self, HL_dst: BlockPtr, DE_src: BlockPtr) -> BlockPtr:
        self._write_u8_ptr(HL_dst, self._read_u8_ptr(DE_src))
        self._write_u8_ptr(HL_dst.add(0x01), self._read_u8_ptr(DE_src.add(0x01)))
        self._write_u8_ptr(HL_dst.add(0x02), self._read_u8_ptr(DE_src.add(0x02)))
        return DE_src.add(0x0003)

    # ZX 0xF778..0xF77D
    def fn_frame_delay_loop(self):
        if self._fsm_step_active:
            raise RuntimeError(
                "Legacy frame-delay loop called during active FSM step; "
                "use FSM frame-delay state instead",
            )
        self._yield_host_frames(0x50)

    # ZX 0xF77E..0xF789
    def copy_28_byte_status_string_template(self):
        base = self.const_status_string_template_28b
        src = bytes(self.const_mission_panel_attr_source[base : base + 0x1C])
        self._write_bytes_ptr(self._display_attr_ptr(0x5a80), src)

    # ZX 0xFBCC..0xFBCC
    def scenario_intermission_beeper_stream_player_loop(self, *, abort_on_keypress: bool = True):
        if self._fsm_step_active:
            raise RuntimeError(
                "Legacy stream intermission loop called during active FSM step; "
                "use FSM stream-intermission state instead",
            )
        # FBCC ROM defaults are immediate pointers 0xFD9B and 0xFD9F.
        # They are normally patched by scenario_pointer_seeding_core before entry.
        ptr_a = getattr(
            self,
            "patch_stream_player_default_stream_a_ptr",
            BlockPtr(self.const_scenario_preset_c_stream_1, 0x0000),
        )
        ptr_b = getattr(
            self,
            "patch_stream_player_default_stream_b_ptr",
            BlockPtr(self.const_scenario_preset_c_stream_1, 0x0004),
        )
        self._stream_ptr_a = ptr_a
        self._stream_ptr_b = ptr_a.add(0x0001)
        self._stream_ptr_c = ptr_b
        self._stream_ptr_d = ptr_b.add(0x0001)
        self._reset_stream_audio_timing_state()

        self._interrupts_enabled = False
        try:
            while True:
                try:
                    self._fill_stream_audio_until_target()
                except ForcedInterpreterAbort:
                    self.schedule_reset(self._audio_safe_start_tick_for_epoch())
                    return

                key_code = self._rom_keyboard_input_poll_028e()
                if abort_on_keypress and ((key_code + 0x01) & 0xFF) != 0x00:
                    self.schedule_reset(self._audio_safe_start_tick_for_epoch())
                    return

                self._yield_frame()
        finally:
            self._reset_stream_audio_timing_state()
            self._interrupts_enabled = True

    def fn_stream_byte_fetch_helper(self, stream_slot: StreamSlot) -> int:
        DE_ptr = getattr(self, f"_{stream_slot}").add(0x0001)
        A_byte = self._read_u8_ptr(DE_ptr)
        if A_byte == 0x40:
            self.forced_interpreter_abort_path()
        setattr(self, f"_{stream_slot}", DE_ptr)
        return A_byte

    # ZX 0xFBFD..0xFC0A
    def fn_timing_parameter_decode_helper(self, A_cmd_byte: int) -> tuple[int, int]:
        cmd = A_cmd_byte & 0xFF

        E_idx = (cmd + 0x0C) & 0xFF
        if E_idx >= len(self.const_stream_timing_profile_table):
            raise ValueError(f"Timing profile index out of range: {E_idx}")
        table_hi = self.const_stream_timing_profile_table[E_idx] & 0xFF
        HL_timing = ((table_hi << 0x08) | 0x01) & 0xFFFF
        return HL_timing, E_idx

    # ZX 0xFC0B..0xFC12
    def forced_interpreter_abort_path(self):
        raise ForcedInterpreterAbort()

    @staticmethod
    def _divider_toggle_count(iterations: int, *, initial: int, reload: int) -> int:
        """Count how many times an 8-bit DEC/JP Z style divider toggles.

        The inner stream engine uses two nested dividers (E and L counters).
        The original port simulated the Z80 loop literally, but for gameplay we
        only need the *toggle counts* (to derive the semantic audio commands).

        This helper reproduces the exact behaviour of:

        - counter = (counter - 1) & 0xFF
        - if counter == 0: toggle; counter = reload

        without iterating per-cycle.
        """

        n = int(iterations)
        if n <= 0:
            return 0

        ctr0 = int(initial) & 0xFF
        reload_u8 = int(reload) & 0xFF

        # How many iterations until the *first* toggle?
        # If ctr0 is 0, DEC wraps to 255 and it takes a full 256 steps.
        first_period = ctr0 if ctr0 != 0 else 0x100
        if n < first_period:
            return 0

        # After the first toggle the counter is reloaded.
        period = reload_u8 if reload_u8 != 0 else 0x100
        return 1 + ((n - first_period) // period)

    # ZX 0xFC13..0xFC6F
    def core_command_interpreter_scenario_stream_engine(self) -> int:
        self._align_stream_audio_lanes_to_safe_start_tick()
        cmd1 = self.fn_stream_byte_fetch_helper(stream_slot="stream_ptr_a")
        self.var_stream_cmd_byte_0 = cmd1 & 0xFF

        cmd2 = self.fn_stream_byte_fetch_helper(stream_slot="stream_ptr_c")
        self.var_stream_cmd_byte_1 = cmd2 & 0xFF

        hl_t1, e_cmd1 = self.fn_timing_parameter_decode_helper(
            A_cmd_byte=cmd1,
        )
        if e_cmd1 & 0x80:
            return self.special_command_dispatcher(A_cmd=cmd1)

        hl_t2, _ = self.fn_timing_parameter_decode_helper(
            A_cmd_byte=cmd2,
        )
        if (((hl_t2 >> 8) & 0xFF) == 0x01) and (((hl_t1 >> 8) & 0xFF) == 0x01):
            return self.pre_delay_calibration_helper()

        # ------------------------------------------------------------------
        # Performance note
        #
        # The original Python port translated the Z80 stream engine very
        # literally and iterated the inner timing loop step-by-step.
        #
        # That is great for debugging, but in the browser the per-iteration
        # Python overhead becomes a major FPS limiter.
        #
        # For gameplay we only need:
        #   - the number of loop iterations (to compute duration)
        #   - how many times the fast/slow dividers toggled
        #
        # Those can be computed analytically.
        # ------------------------------------------------------------------

        c_cycles = self.var_stream_timing_control_byte & 0xFF
        if c_cycles == 0x00:
            # Matches the behaviour of the existing implementation: with C==0
            # the loop executes exactly one body iteration.
            iterations = 1
        else:
            # C increments once per B-wrap (B is an 8-bit down-counter), and the
            # loop ends when INC C wraps back to 0.
            iterations = (0x100 - c_cycles) * 0x100

        e_ctr = hl_t1 & 0xFF
        e_reload = (hl_t1 >> 8) & 0xFF
        l_ctr = hl_t2 & 0xFF
        l_reload = (hl_t2 >> 8) & 0xFF

        fast_wraps = self._divider_toggle_count(iterations, initial=e_ctr, reload=e_reload)
        slow_wraps = self._divider_toggle_count(iterations, initial=l_ctr, reload=l_reload)

        return self._emit_stream_semantic_mix(
            iterations=iterations,
            fast_wraps=fast_wraps,
            slow_wraps=slow_wraps,
        )

    # ZX 0xFC70..0xFC81
    def interpreter_inner_loop_branch_helper_timing(self, A_main, A_alt, E_ctr, E_reload, L_ctr, L_reload, B_phase, C_cycles, toggle_mask):
        a_main = A_main & 0xFF
        a_alt = A_alt & 0xFF
        e_ctr = E_ctr & 0xFF
        e_reload = E_reload & 0xFF
        l_ctr = L_ctr & 0xFF
        l_reload = L_reload & 0xFF
        b_phase = B_phase & 0xFF
        c_cycles = C_cycles & 0xFF
        xor_mask = toggle_mask & 0xFF
        fast_toggled = False
        slow_toggled = False

        # FC53: EX AF,AF'
        a_main, a_alt = a_alt, a_main

        # FC54..FC57
        e_ctr = (e_ctr - 0x01) & 0xFF

        if e_ctr == 0x00:
            # FC59..FC5C path
            e_ctr = e_reload
            a_main ^= xor_mask
            a_main, a_alt = a_alt, a_main
            fast_toggled = True
        else:
            # FC70..FC72 path includes timing padding and EX AF,AF'
            a_main, a_alt = a_alt, a_main

        # Shared FC73/FC5D slow divider path.
        l_ctr = (l_ctr - 0x01) & 0xFF
        if l_ctr == 0x00:
            l_ctr = l_reload
            a_main ^= xor_mask
            slow_toggled = True

        # FC7B / FC65
        b_phase = (b_phase - 0x01) & 0xFF
        if b_phase == 0x00:
            # FC7D / FC67
            c_cycles = (c_cycles + 0x01) & 0xFF

        return a_main, a_alt, e_ctr, l_ctr, b_phase, c_cycles, fast_toggled, slow_toggled, 1

    def _emit_stream_semantic_mix(self, *, iterations: int, fast_wraps: int, slow_wraps: int) -> int:
        if iterations <= 0:
            return 0
        # Even when both dividers end up as DC (no audible toggles), the stream
        # engine still consumes real time. Keep channel timelines aligned.

        # FC51<->FC70 inner loop is cycle-shaped in ASM; use Z80 clock units directly
        # instead of treating loop iterations as arbitrary 22.05kHz samples.
        #
        # IMPORTANT DETAIL (root cause of the "music is too high / tempo drifts" bug):
        #
        # The Python port counts `iterations` as the number of times we execute the
        # FC53..FC7B / FC53..FC65 body (the part that includes the DJNZ). In the real
        # Z80 code, the *common* path after DJNZ is a jump back to FC51, and FC51/FC52
        # are two NOPs used purely as timing padding before execution continues at FC53.
        #
        # In other words: the steady-state cost between successive FC53 bodies is not
        # 88 t-states, but 88 + 8 = 96 t-states for most iterations. The exception is
        # the iteration immediately following a B-wrap, because the code goes through
        # INC C / JP NZ,FC53 and deliberately *skips* FC51/FC52.
        #
        # If we forget those two NOPs, we underestimate the duration by ~9% for the
        # menu streams (4608 iterations), which makes every note ~9% sharper and the
        # whole piece ~9% faster.
        iter_count = int(iterations)
        b_wraps = iter_count // 0x100

        # Count how many times the loop actually passes through FC51/FC52.
        #
        # After each B-wrap, the next iteration starts at FC53 (JP NZ,FC53), so those
        # two NOPs are skipped once per wrap — except for the final wrap that exits the
        # loop (no next iteration).
        starts_via_fc53 = b_wraps
        if b_wraps > 0 and (iter_count & 0xFF) == 0:
            starts_via_fc53 -= 1
        fc51_starts = max(0, iter_count - starts_via_fc53)

        total_clock_units = (88 * iter_count) + (8 * fc51_starts) + (9 * b_wraps) + 10
        total_duration_s = float(total_clock_units) / 3_500_000.0
        if total_duration_s <= 0.0:
            return 0
        slot_ticks = self._quantize_stream_slot_ticks(total_duration_s)
        slot_duration_s = float(slot_ticks) / 120.0

        # Stream dividers toggle the beeper latch bit; one tone period needs two toggles.
        #
        # Porting nuance: the original engine mixes both dividers by toggling the *same*
        # 1-bit latch (port 0xFE bit 4). When one divider is configured with an extremely
        # small reload value (the common "1" case), it becomes an ultrasonic carrier.
        # On real hardware that carrier is heavily attenuated by the speaker and ends up
        # acting as a modulation source for the other divider rather than as a dominant
        # bright lead.
        #
        # We still need to keep that carrier in the semantic timeline: dropping it
        # entirely makes the affected voice "enter late" in the Pyxel reconstruction,
        # which shifts note onsets between channels relative to the original.
        freq_fast = float(fast_wraps) / (2.0 * total_duration_s) if fast_wraps > 0 else 0.0
        freq_slow = float(slow_wraps) / (2.0 * total_duration_s) if slow_wraps > 0 else 0.0

        # Treat very high divider rates as a carrier/hiss component. Keep them present as
        # timed zero-volume placeholders so they preserve segment boundaries without being
        # audible at all.
        carrier_cutoff_hz = 3800.0
        fast_is_carrier = fast_wraps > 0 and freq_fast > carrier_cutoff_hz
        slow_is_carrier = slow_wraps > 0 and freq_slow > carrier_cutoff_hz
        fast_present = fast_wraps > 0
        slow_present = slow_wraps > 0

        if fast_present:
            if fast_is_carrier:
                waveform = "T"
                volume = 0
            else:
                waveform = "S"
                volume = 4 if slow_present and not slow_is_carrier else 5
            self.emit_note_event(
                waveform=waveform,
                freq_hz=freq_fast,
                start_tick=self._stream_lane_ticks[0],
                duration_ticks=slot_ticks,
                volume=volume,
                source="stream_music",
            )
        self._stream_lane_ticks[0] += slot_ticks
        if slow_present:
            if slow_is_carrier:
                waveform = "T"
                volume = 0
            else:
                waveform = "S"
                volume = 4 if fast_present and not fast_is_carrier else 5
            self.emit_note_event(
                waveform=waveform,
                freq_hz=freq_slow,
                start_tick=self._stream_lane_ticks[1],
                duration_ticks=slot_ticks,
                volume=volume,
                source="stream_music",
            )
        self._stream_lane_ticks[1] += slot_ticks
        return int(total_clock_units)

    # ZX 0xFC82..0xFC9F
    def pre_delay_calibration_helper(self, C_wait=None) -> int:
        if C_wait is None:
            timing_ctl = self.var_stream_timing_control_byte & 0xFF
            C_wait = (~timing_ctl) & 0xFF
        C_wait &= 0xFF
        outer = C_wait if C_wait != 0x00 else 0x100
        # FC82..FC96 delay loop approximation (8-bit nested counters with NOP pad).
        #
        # IMPORTANT: The old implementation executed a Python busy-wait loop
        # (nested `for ...: pass`) to mimic the Z80 delay.
        #
        # For the port we only need the *timing cost* as a number consumed by
        # the outer pacing logic; burning real CPU time is counter-productive
        # (especially in Pyodide).
        total_clock_units = int(outer * 0x100 * 13)

        # This path is a timed silent segment in the original stream interpreter.
        # Advance both semantic mixer channels to preserve relative timing.
        duration_s = float(total_clock_units) / 3_500_000.0
        if duration_s > 0.0:
            slot_ticks = self._quantize_stream_slot_ticks(duration_s)
            self._stream_lane_ticks[0] += slot_ticks
            self._stream_lane_ticks[1] += slot_ticks

        return total_clock_units

    # ZX 0xFCD6..0xFCF8
    def special_command_dispatcher(self, A_cmd) -> int:
        d_bits = self.var_stream_cmd_byte_1 & 0xFF
        a_cmd, b_delay, c_delay, e_wait = self.fn_command_parameter_normalizer(A_cmd=self._as_u8(A_cmd))
        if a_cmd == 0xFF:
            return self.bitstream_pulse_generator(C_repeat=c_delay, D_bits=d_bits)
        if a_cmd == 0xC0:
            return self.lookup_driven_burst_generator(B_idx=b_delay)

        c_repeat = e_wait
        carry = 1 if a_cmd < 0xC0 else 0
        a_mix = a_cmd
        total_timing_cost = 0
        for _ in range(0x04):
            a_mix, carry = self._rla(a_mix, carry)
        for _ in range(0x04):
            a_mix, carry = self._rla(a_mix, carry)
            if carry:
                total_timing_cost += self.bitstream_pulse_generator(C_repeat=c_repeat, D_bits=d_bits)
            else:
                total_timing_cost += self.pre_delay_calibration_helper(C_wait=c_repeat)
        return total_timing_cost

    # ZX 0xFCF9..0xFD0D
    def fn_command_parameter_normalizer(self, A_cmd):
        timing_ctl = self.var_stream_timing_control_byte & 0xFF
        A_inv = (~timing_ctl) & 0xFF
        B_delay = A_inv
        C_delay = A_inv
        A_wait = (A_inv + 0x01) & 0xFF
        A_wait = ((A_wait & 0x80) | (A_wait >> 1)) & 0xFF
        A_wait = ((A_wait & 0x80) | (A_wait >> 1)) & 0xFF
        E_wait = A_wait
        if E_wait == 0x00:
            E_wait = 0x01
        return A_cmd & 0xFF, B_delay, C_delay, E_wait

    # ZX 0xFD0E..0xFD4A
    def bitstream_pulse_generator(self, C_repeat, D_bits) -> int:
        C_repeat &= 0xFF
        D_bits &= 0xFF
        self._ensure_stream_lane_slots()
        density = float(D_bits.bit_count()) / 8.0

        # FD0E path timing model (cycle-checked against the Z80 routine at 0xFD0E):
        #
        # Per-iteration cost (excluding prologue/epilogue and B-wrap DEC C/JP):
        # - carry clear branch: 90 t-states
        # - carry set branch:  95..97 t-states depending on BIT 0,(HL) path
        #   (use 96 as an unbiased mean).
        #
        # Therefore, average step cost is ~90 + 6*density.
        c_outer = C_repeat if C_repeat != 0x00 else 0x100
        iter_count = c_outer * 0x100
        avg_iter_clock_units = 90.0 + (6.0 * density)
        total_clock_units = 63.0 + (float(iter_count) * avg_iter_clock_units) + (14.0 * float(c_outer)) + 40.0
        duration_s = total_clock_units / 3_500_000.0

        slot_ticks = self._quantize_stream_slot_ticks(max(duration_s, 0.0))

        # If D contains no set bits, the original routine never reaches OUT (0xFE),A:
        # it is a timed silent segment. Preserve timing without emitting noise.
        if density <= 0.0:
            self._stream_lane_ticks[0] += slot_ticks
            self._stream_lane_ticks[1] += slot_ticks
            return int(total_clock_units)

        # Model perceived latch "edge rate" as half of update rate.
        active_updates = density * float(iter_count)
        freq_hz = active_updates / (2.0 * max(duration_s, 1e-6))
        if freq_hz < 120.0:
            freq_hz = 120.0

        # Keep noise conservative; raw Pyxel noise is perceptually denser than
        # Spectrum beeper hash through a small speaker.
        volume = 1 + int(round(2.0 * density))
        if volume < 1:
            volume = 1
        if volume > 3:
            volume = 3

        self.emit_note_event(
            waveform="N",
            freq_hz=freq_hz,
            start_tick=self._stream_lane_ticks[0],
            duration_ticks=slot_ticks,
            volume=volume,
            source="stream_special",
        )
        self._stream_lane_ticks[0] += slot_ticks
        self._stream_lane_ticks[1] += slot_ticks
        return int(total_clock_units)

    # ZX 0xFD4B..0xFD69
    def lookup_driven_burst_generator(self, B_idx) -> int:
        E_idx = self._as_u8(B_idx)
        if E_idx >= len(self.const_burst_lookup_table):
            raise ValueError(f"Burst lookup index out of range: {E_idx}")
        B_repeat = self.const_burst_lookup_table[E_idx] & 0xFF
        HL_delay = 0x0003
        total_timing_cost = 0
        while True:
            carry_out, timing_cost = self.fn_low_level_tone_delay_primitive(HL_delay=HL_delay)
            total_timing_cost += timing_cost
            HL_delay = (HL_delay + 0x00FF + carry_out) & 0xFFFF
            B_repeat = (B_repeat - 0x01) & 0xFF
            if B_repeat == 0x00:
                return total_timing_cost

    # ZX 0xFD6A..0xFD82
    def fn_low_level_tone_delay_primitive(self, HL_delay) -> tuple[int, int]:
        HL_delay = HL_delay & 0xFFFF
        self._ensure_stream_lane_slots()
        # ASM computes C from the original L byte:
        # LD A,L ; SRL L ; SRL L ; CPL ; AND 03 ; LD C,A.
        # So variant index comes from ~orig_L low 2 bits (not from shifted L).
        orig_l = HL_delay & 0x00FF
        C_variant = (~orig_l) & 0x03
        A_tone = self.var_stream_cmd_byte_2 & 0xFF
        period = (0x00D1 + C_variant + (A_tone & 0x0F)) & 0xFFFF
        ticks = ((HL_delay >> 8) & 0xFF) | 0x01
        p = max(1, int(period) & 0xFFFF)
        waves = max(1, int(ticks) & 0xFFFF)
        half_period_t = 4.0 * (float(p) + 30.125)
        full_period_t = 2.0 * half_period_t
        freq = 3_500_000.0 / full_period_t
        duration_s = float(waves) / freq
        duration_ticks = self._duration_ticks_from_seconds(duration_s)
        self.emit_note_event(
            waveform="S",
            freq_hz=freq,
            start_tick=self._stream_lane_ticks[0],
            duration_ticks=duration_ticks,
            volume=5,
            source="stream_special",
        )
        self._stream_lane_ticks[0] += duration_ticks
        self._interrupts_enabled = False
        # Carry from ROM tone path (03D4) is not modeled in service layer yet.
        # Timing estimate uses the same ROM 0x03B5 model as runtime emit_rom_beeper.
        per_wave_clock_units = 8.0 * (float(period) + 30.125)
        timing_cost = int(round(float(ticks) * per_wave_clock_units))
        if duration_s > 0.0:
            slot_ticks = self._quantize_stream_slot_ticks(duration_s)
            self._stream_lane_ticks[1] += slot_ticks
        return 0, timing_cost

    # ZX 0xFE69..0xFFCD
    def abort_continue_gate_interpreter_loop(self):
        self._interrupts_enabled = False
        try:
            C_continue = self._rom_keyboard_check_break_1f54()
            if not C_continue:
                self.var_runtime_scheduler_timer = 0x0009
        finally:
            self._interrupts_enabled = True
