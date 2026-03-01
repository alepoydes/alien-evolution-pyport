from __future__ import annotations

import unittest

from alien_evolution.alienevolution.logic import (
    GAMEPLAY_FRAME_DIVIDER,
    FSM_STATE_CALLBACK_HALT_65_FRAME,
    FSM_STATE_CALLBACK_TIMING_FRAME,
    FSM_STATE_FAILURE_TIMER_DRAIN_FRAME,
    FSM_STATE_FRAME_DELAY_0X50_FRAME,
    FSM_STATE_GAMEPLAY_MAIN_AFTER_DIRECTIONAL,
    FSM_STATE_GAMEPLAY_MAIN_AFTER_CALLBACK,
    FSM_STATE_GAMEPLAY_MAIN_FRAME,
    FSM_STATE_GAMEPLAY_MAIN_POST_TICK,
    FSM_STATE_GAMEPLAY_BRANCH,
    FSM_STATE_LEVEL_ROLL_FRAME,
    FSM_STATE_MENU_INIT,
    FSM_STATE_OVERLAY_POST_FILL_FRAME,
    FSM_STATE_OVERLAY_PRE_FILL_FRAME,
    FSM_STATE_GAMEPLAY_TICK_STAGE_0_FRAME,
    FSM_STATE_GAMEPLAY_TICK_STAGE_1_FRAME,
    FSM_STATE_GAMEPLAY_TICK_STAGE_3_FRAME,
    FSM_STATE_GAMEPLAY_SETUP,
    FSM_STATE_SCHEDULER_AUTONOMOUS_FRAME,
    FSM_STATE_STREAM_INTERMISSION_FRAME,
    FSM_STATE_TRANSITION_DISPATCH,
    AlienEvolutionPort,
)
from alien_evolution.zx.pointers import BlockPtr, StructFieldPtr
from alien_evolution.zx.runtime import FrameInput
from alien_evolution.zx.state import StatefulManifestRuntime


_NEUTRAL_INPUT = FrameInput(joy_kempston=0, keyboard_rows=(0xFF,) * 8)


class _RebindValidationRuntime(StatefulManifestRuntime):
    STATE_SCHEMA_VERSION = 1
    _STATE_SCHEMA_HASH = "test"
    _STATE_REBIND_BLOCK_PTR_FIELDS = ("block_ptr_field",)
    _STATE_REBIND_STRUCT_PTR_FIELDS = ("struct_ptr_field",)

    def __init__(self) -> None:
        self._struct_root = [0]
        self.block_ptr_field = BlockPtr(bytearray(b"\x00"), 0)
        self.struct_ptr_field = StructFieldPtr(root=self._struct_root, path=(0,))

    def reset(self) -> None:
        return


def _output_state_signature(output: object) -> tuple[object, ...]:
    return (
        getattr(output, "screen_bitmap"),
        getattr(output, "screen_attrs"),
        getattr(output, "flash_phase"),
        getattr(output, "border_color"),
        getattr(output, "timing"),
    )


class RuntimeStatePointerCodecTests(unittest.TestCase):
    def test_block_ptr_roundtrip_uses_logical_target_attr(self) -> None:
        runtime = AlienEvolutionPort()
        ptr = BlockPtr(runtime.const_scenario_preset_b_stream_1, 5)
        encoded = runtime._state_encode_block_ptr(ptr)
        decoded = runtime._state_decode_block_ptr(encoded)

        self.assertIsInstance(decoded, BlockPtr)
        self.assertIs(decoded.array, runtime.const_scenario_preset_b_stream_1)
        self.assertEqual(decoded.index, 5)

    def test_struct_ptr_roundtrip_uses_root_attr_and_path(self) -> None:
        runtime = AlienEvolutionPort()
        ptr = runtime.const_define_key_slot_3_port_word
        encoded = runtime._state_encode_struct_ptr(ptr)
        decoded = runtime._state_decode_struct_ptr(encoded)

        self.assertIsInstance(decoded, StructFieldPtr)
        self.assertIs(decoded.root, runtime.const_define_keys_descriptor_table)
        self.assertEqual(decoded.path, ptr.path)


class RuntimeStateRoundtripTests(unittest.TestCase):
    def test_save_load_roundtrip_is_deterministic(self) -> None:
        runtime = AlienEvolutionPort()
        for _ in range(20):
            runtime.step(_NEUTRAL_INPUT)

        saved_state = runtime.save_state()
        outputs_a = [runtime.step(_NEUTRAL_INPUT) for _ in range(30)]

        runtime.load_state(saved_state)
        outputs_b = [runtime.step(_NEUTRAL_INPUT) for _ in range(30)]

        self.assertEqual(
            [_output_state_signature(item) for item in outputs_a],
            [_output_state_signature(item) for item in outputs_b],
        )

    def test_load_restores_pointer_targets_and_queue_head_aliases(self) -> None:
        runtime = AlienEvolutionPort()
        for _ in range(30):
            runtime.step(_NEUTRAL_INPUT)
        state = runtime.save_state()

        restored = AlienEvolutionPort()
        restored.load_state(state)

        payload = state["payload"]
        self.assertIsInstance(payload, dict)
        block_ptrs = payload.get("block_ptrs", {})
        self.assertIsInstance(block_ptrs, dict)
        for field_name, ptr_payload in block_ptrs.items():
            self.assertTrue(hasattr(restored, field_name))
            ptr_value = getattr(restored, field_name)
            self.assertIsInstance(ptr_value, BlockPtr)
            self.assertIsInstance(ptr_payload, dict)
            target_attr = ptr_payload.get("target_attr")
            self.assertIsInstance(target_attr, str)
            self.assertIs(ptr_value.array, getattr(restored, target_attr))
            self.assertEqual(ptr_value.index, ptr_payload.get("index"))

        queue_targets = [
            restored.var_runtime_object_queue_0,
            restored.var_runtime_object_queue_1,
            restored.var_runtime_object_queue_2,
            restored.var_runtime_object_queue_3,
            restored.var_runtime_object_queue_4,
        ]
        self.assertIn(restored.var_runtime_queue_head_0, queue_targets)
        self.assertIn(restored.var_runtime_queue_head_1, queue_targets)
        self.assertIn(restored.var_runtime_queue_head_2, queue_targets)
        self.assertIn(restored.var_runtime_queue_head_3, queue_targets)
        self.assertIn(restored.var_runtime_queue_head_4, queue_targets)

    def test_autosave_state_omits_replay_history(self) -> None:
        runtime = AlienEvolutionPort()
        for _ in range(25):
            runtime.step(_NEUTRAL_INPUT)

        self.assertFalse(hasattr(runtime, "_state_step_input_history"))

        state_full = runtime.save_state()
        autosave = runtime.save_autosave_state()
        for envelope in (state_full, autosave):
            payload = envelope.get("payload")
            self.assertIsInstance(payload, dict)
            assert isinstance(payload, dict)
            values = payload.get("values")
            self.assertIsInstance(values, dict)
            assert isinstance(values, dict)
            self.assertNotIn("_state_step_input_history", values)
            self.assertNotIn("_fsm_return_state", values)
            meta = envelope.get("meta")
            self.assertIsInstance(meta, dict)
            assert isinstance(meta, dict)
            self.assertEqual(meta.get("load_mode"), "reset_replay")

    def test_load_from_autosave_restores_future_outputs(self) -> None:
        runtime = AlienEvolutionPort()
        for _ in range(60):
            runtime.step(_NEUTRAL_INPUT)

        autosave = runtime.save_autosave_state()
        expected = [runtime.step(_NEUTRAL_INPUT) for _ in range(20)]

        for _ in range(15):
            runtime.step(_NEUTRAL_INPUT)

        runtime.load_state(autosave)
        actual = [runtime.step(_NEUTRAL_INPUT) for _ in range(20)]
        self.assertEqual(
            [_output_state_signature(item) for item in expected],
            [_output_state_signature(item) for item in actual],
        )

    def test_load_accepts_legacy_runtime_id_alias(self) -> None:
        runtime = AlienEvolutionPort()
        state = runtime.save_state()
        state["runtime_id"] = "alien_evolution.logic.AlienEvolutionPort"

        runtime.load_state(state)
        output = runtime.step(_NEUTRAL_INPUT)

        self.assertIsNotNone(output)

    def test_save_state_fails_fast_on_manifest_runtime_mismatch(self) -> None:
        missing = "__missing_manifest_field__"
        original_fields = AlienEvolutionPort._STATE_DYNAMIC_VALUE_FIELDS
        AlienEvolutionPort._STATE_DYNAMIC_VALUE_FIELDS = original_fields + (missing,)
        try:
            runtime = AlienEvolutionPort()
            with self.assertRaisesRegex(ValueError, missing):
                runtime.save_state()
        finally:
            AlienEvolutionPort._STATE_DYNAMIC_VALUE_FIELDS = original_fields

    def test_load_gameplay_state_into_menu_runtime_does_not_hang(self) -> None:
        gameplay_runtime = AlienEvolutionPort()
        gameplay_runtime._fsm_state = FSM_STATE_GAMEPLAY_SETUP
        gameplay_runtime._fsm_gameplay_ctx["initialized"] = False
        for _ in range(5):
            gameplay_runtime.step(_NEUTRAL_INPUT)
        state = gameplay_runtime.save_state()

        menu_runtime = AlienEvolutionPort()
        menu_runtime.load_state(state)
        for _ in range(5):
            output = menu_runtime.step(_NEUTRAL_INPUT)
            self.assertIsNotNone(output)

    def test_level_complete_reentry_keeps_incremented_map_mode(self) -> None:
        runtime = AlienEvolutionPort()
        observed = {"switch_calls": 0, "screen_setup_calls": 0, "overlay_selector_calls": 0}

        def _switch_handler() -> None:
            observed["switch_calls"] += 1

        runtime.fn_active_map_mode_switch_handler = _switch_handler  # type: ignore[assignment]
        runtime._fsm_transition_kind = "level_complete"
        next_state, delay = runtime._fsm_state_transition_dispatch()
        self.assertEqual(next_state, FSM_STATE_LEVEL_ROLL_FRAME)
        self.assertIsNone(delay)
        self.assertEqual(observed["switch_calls"], 1)

        runtime.var_active_map_mode = 0x00
        runtime._fsm_transition_kind = "after_level_roll"
        runtime._fsm_gameplay_ctx["initialized"] = True
        runtime.fn_transition_beeper_entry_a = lambda: None  # type: ignore[assignment]
        next_state, delay = runtime._fsm_state_transition_dispatch()
        self.assertEqual(next_state, FSM_STATE_GAMEPLAY_SETUP)
        self.assertIsNone(delay)
        self.assertEqual(runtime.var_active_map_mode, 0x01)
        self.assertFalse(bool(runtime._fsm_gameplay_ctx["initialized"]))
        self.assertFalse(bool(runtime._fsm_gameplay_ctx.get("screen_setup_required", True)))

        def _screen_setup_spy() -> None:
            observed["screen_setup_calls"] += 1

        def _overlay_selector_spy() -> None:
            observed["overlay_selector_calls"] += 1

        runtime.gameplay_screen_setup = _screen_setup_spy  # type: ignore[assignment]
        runtime.fn_overlay_preset_selector = _overlay_selector_spy  # type: ignore[assignment]
        runtime._fsm_start_stream = lambda **_: None  # type: ignore[assignment]
        mode_before_setup = runtime.var_active_map_mode
        next_state, delay = runtime._fsm_state_gameplay_setup()
        self.assertEqual(next_state, FSM_STATE_STREAM_INTERMISSION_FRAME)
        self.assertIsNone(delay)
        self.assertEqual(runtime.var_active_map_mode, mode_before_setup)
        self.assertEqual(observed["screen_setup_calls"], 0)
        self.assertEqual(observed["overlay_selector_calls"], 0)

    def test_scheduler_tick_defers_autonomous_branch_into_fsm_state(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._fsm_step_active = True
        runtime._fsm_tick_ctx = {}
        runtime.var_runtime_scheduler_timer = 0x0101
        runtime.patch_scheduler_script_base_ptr = 0
        runtime.const_periodic_scheduler_script[0] = 0x01

        runtime.fn_periodic_scheduler_tick()

        self.assertTrue(runtime._fsm_tick_ctx.get("pending_autonomous", False))
        self.assertFalse(runtime._fsm_tick_ctx.get("pending_marker", False))

    def test_scheduler_autonomous_state_enters_tick_stage_chain(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._fsm_state = FSM_STATE_SCHEDULER_AUTONOMOUS_FRAME
        runtime._fsm_tick_ctx = {
            "pending_autonomous": True,
            "pending_marker": False,
            "scheduler_phase": "tick0",
        }

        next_state, delay = runtime._fsm_state_scheduler_autonomous_frame()

        self.assertEqual(next_state, FSM_STATE_GAMEPLAY_TICK_STAGE_0_FRAME)
        self.assertIsNone(delay)
        self.assertEqual(runtime._fsm_tick_ctx.get("scheduler_phase"), "after_tick0")
        self.assertEqual(
            runtime._fsm_tick_ctx.get("tick_stage3_next_state"),
            FSM_STATE_SCHEDULER_AUTONOMOUS_FRAME,
        )

    def test_scheduler_autonomous_state_after_tick_clears_pending_flags(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._fsm_state = FSM_STATE_SCHEDULER_AUTONOMOUS_FRAME
        runtime._fsm_tick_ctx = {
            "pending_autonomous": True,
            "pending_marker": False,
            "scheduler_phase": "after_tick0",
        }
        observed: dict[str, object] = {}

        def _scheduler_step(*, run_tick: bool = True) -> None:
            observed["run_tick"] = run_tick

        runtime.scheduler_triggered_autonomous_step = _scheduler_step  # type: ignore[assignment]
        runtime.scheduler_triggered_marker_seeding = lambda: None  # type: ignore[assignment]

        next_state, delay = runtime._fsm_state_scheduler_autonomous_frame()

        self.assertEqual(next_state, FSM_STATE_GAMEPLAY_MAIN_POST_TICK)
        self.assertIsNone(delay)
        self.assertEqual(observed.get("run_tick"), False)
        self.assertFalse(runtime._fsm_tick_ctx.get("pending_autonomous", True))
        self.assertEqual(runtime._fsm_tick_ctx.get("scheduler_phase"), "tick0")

    def test_scheduler_autonomous_state_after_tick_uses_configured_return_state(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._fsm_state = FSM_STATE_SCHEDULER_AUTONOMOUS_FRAME
        runtime._fsm_tick_ctx = {
            "pending_autonomous": True,
            "pending_marker": False,
            "scheduler_phase": "after_tick0",
            "scheduler_return_state": FSM_STATE_TRANSITION_DISPATCH,
        }

        runtime.scheduler_triggered_autonomous_step = lambda *, run_tick=True: None  # type: ignore[assignment]
        runtime.scheduler_triggered_marker_seeding = lambda: None  # type: ignore[assignment]

        next_state, delay = runtime._fsm_state_scheduler_autonomous_frame()

        self.assertEqual(next_state, FSM_STATE_TRANSITION_DISPATCH)
        self.assertIsNone(delay)
        self.assertNotIn("scheduler_return_state", runtime._fsm_tick_ctx)

    def test_scheduler_autonomous_state_fails_fast_without_phase(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._fsm_state = FSM_STATE_SCHEDULER_AUTONOMOUS_FRAME
        runtime._fsm_tick_ctx = {
            "pending_autonomous": True,
            "pending_marker": False,
        }
        with self.assertRaisesRegex(RuntimeError, "scheduler_phase"):
            runtime._fsm_state_scheduler_autonomous_frame()

    def test_scheduler_autonomous_state_fails_fast_without_pending_autonomous_key(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._fsm_state = FSM_STATE_SCHEDULER_AUTONOMOUS_FRAME
        runtime._fsm_tick_ctx = {
            "pending_marker": False,
            "scheduler_phase": "tick0",
        }
        with self.assertRaisesRegex(RuntimeError, "requires pending_autonomous in"):
            runtime._fsm_state_scheduler_autonomous_frame()

    def test_scheduler_autonomous_state_fails_fast_on_non_bool_pending_flags(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._fsm_state = FSM_STATE_SCHEDULER_AUTONOMOUS_FRAME
        runtime._fsm_tick_ctx = {
            "pending_autonomous": "yes",
            "pending_marker": False,
            "scheduler_phase": "tick0",
        }
        with self.assertRaisesRegex(RuntimeError, "bool pending_autonomous"):
            runtime._fsm_state_scheduler_autonomous_frame()

        runtime._fsm_tick_ctx = {
            "pending_autonomous": True,
            "pending_marker": "no",
            "scheduler_phase": "after_tick0",
        }
        with self.assertRaisesRegex(RuntimeError, "bool pending_marker"):
            runtime._fsm_state_scheduler_autonomous_frame()

    def test_scheduler_autonomous_state_fails_fast_without_pending_marker(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._fsm_state = FSM_STATE_SCHEDULER_AUTONOMOUS_FRAME
        runtime._fsm_tick_ctx = {
            "pending_autonomous": True,
            "scheduler_phase": "after_tick0",
        }
        with self.assertRaisesRegex(RuntimeError, "pending_marker"):
            runtime._fsm_state_scheduler_autonomous_frame()

    def test_scheduler_autonomous_state_fails_fast_on_unknown_phase(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._fsm_state = FSM_STATE_SCHEDULER_AUTONOMOUS_FRAME
        runtime._fsm_tick_ctx = {
            "pending_autonomous": True,
            "pending_marker": False,
            "scheduler_phase": "invalid-phase",
        }
        with self.assertRaisesRegex(RuntimeError, "Unknown scheduler autonomous phase"):
            runtime._fsm_state_scheduler_autonomous_frame()

    def test_scheduler_autonomous_state_fails_fast_on_non_string_phase(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._fsm_state = FSM_STATE_SCHEDULER_AUTONOMOUS_FRAME
        runtime._fsm_tick_ctx = {
            "pending_autonomous": True,
            "pending_marker": False,
            "scheduler_phase": 123,
        }
        with self.assertRaisesRegex(RuntimeError, "scheduler_phase to be string"):
            runtime._fsm_state_scheduler_autonomous_frame()

    def test_scheduler_autonomous_state_fails_fast_without_pending_flag(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._fsm_state = FSM_STATE_SCHEDULER_AUTONOMOUS_FRAME
        runtime._fsm_tick_ctx = {
            "pending_autonomous": False,
            "pending_marker": False,
            "scheduler_phase": "tick0",
        }
        with self.assertRaisesRegex(RuntimeError, "pending_autonomous=True"):
            runtime._fsm_state_scheduler_autonomous_frame()

    def test_gameplay_main_frame_routes_to_overlay_delay_state(self) -> None:
        runtime = AlienEvolutionPort()
        runtime.per_frame_object_state_update_pass = lambda: None  # type: ignore[assignment]
        runtime.fn_process_transient_effect_queues_handlers_xe530 = lambda: None  # type: ignore[assignment]
        runtime.fn_gameplay_movement_control_step = lambda: None  # type: ignore[assignment]
        runtime.fn_directional_interaction_dispatcher_using_pointer_table = (  # type: ignore[assignment]
            lambda *, defer_overlay_timing_to_fsm=False: runtime._fsm_overlay_ctx.update(
                {
                    "pre_frames_left": 2,
                    "post_frames_left": 1,
                },
            )
        )

        next_state, delay = runtime._fsm_state_gameplay_main_frame()

        self.assertEqual(next_state, FSM_STATE_OVERLAY_PRE_FILL_FRAME)
        self.assertIsNone(delay)
        self.assertEqual(
            runtime._fsm_overlay_ctx.get("return_state"),
            FSM_STATE_GAMEPLAY_MAIN_AFTER_DIRECTIONAL,
        )

    def test_overlay_states_count_down_and_return_to_directional_continuation(self) -> None:
        runtime = AlienEvolutionPort()
        pre_bitmap = bytes([0x11]) * len(runtime.screen_bitmap)
        pre_attrs = bytes([0x22]) * len(runtime.screen_attrs)
        post_bitmap = bytes([0x33]) * len(runtime.screen_bitmap)
        post_attrs = bytes([0x44]) * len(runtime.screen_attrs)
        runtime._fsm_overlay_ctx = {
            "pre_frames_left": 1,
            "post_frames_left": 1,
            "return_state": FSM_STATE_GAMEPLAY_MAIN_AFTER_DIRECTIONAL,
            "pre_frame_snapshots": [
                {
                    "screen_bitmap": pre_bitmap,
                    "screen_attrs": pre_attrs,
                    "border_color": 0x03,
                },
            ],
            "post_frame_snapshots": [
                {
                    "screen_bitmap": post_bitmap,
                    "screen_attrs": post_attrs,
                    "border_color": 0x05,
                },
            ],
            "pre_frame_cursor": 0,
            "post_frame_cursor": 0,
        }

        next_state, delay = runtime._fsm_state_overlay_pre_fill_frame()
        self.assertEqual(next_state, FSM_STATE_OVERLAY_POST_FILL_FRAME)
        self.assertEqual(delay, 1)
        self.assertEqual(bytes(runtime.screen_bitmap), pre_bitmap)
        self.assertEqual(bytes(runtime.screen_attrs), pre_attrs)
        self.assertEqual(runtime.border_color, 0x03)

        next_state, delay = runtime._fsm_state_overlay_post_fill_frame()
        self.assertEqual(next_state, FSM_STATE_GAMEPLAY_MAIN_AFTER_DIRECTIONAL)
        self.assertEqual(delay, 1)
        self.assertEqual(bytes(runtime.screen_bitmap), post_bitmap)
        self.assertEqual(bytes(runtime.screen_attrs), post_attrs)
        self.assertEqual(runtime.border_color, 0x05)
        self.assertEqual(runtime._fsm_overlay_ctx, {})

    def test_gameplay_main_after_directional_defers_callback_halt_into_fsm_state(self) -> None:
        runtime = AlienEvolutionPort()
        observed: dict[str, object] = {}

        def _callback(
            *,
            defer_halt_to_fsm: bool = False,
            defer_timing_to_fsm: bool = False,
        ) -> tuple[int, int]:
            observed["defer_halt_to_fsm"] = defer_halt_to_fsm
            observed["defer_timing_to_fsm"] = defer_timing_to_fsm
            return 0, 0x41

        runtime.fn_patchable_callback_hook_frame_loop = _callback  # type: ignore[assignment]

        next_state, delay = runtime._fsm_state_gameplay_main_after_directional()

        self.assertEqual(next_state, FSM_STATE_CALLBACK_HALT_65_FRAME)
        self.assertIsNone(delay)
        self.assertEqual(observed.get("defer_halt_to_fsm"), True)
        self.assertEqual(observed.get("defer_timing_to_fsm"), True)
        self.assertEqual(runtime._fsm_callback_ctx.get("frames_left"), 0x41)
        self.assertEqual(
            runtime._fsm_callback_ctx.get("return_state"),
            FSM_STATE_GAMEPLAY_MAIN_AFTER_CALLBACK,
        )

    def test_gameplay_main_after_directional_defers_callback_timing_into_fsm_state(self) -> None:
        runtime = AlienEvolutionPort()
        runtime.fn_patchable_callback_hook_frame_loop = (  # type: ignore[assignment]
            lambda *, defer_halt_to_fsm=False, defer_timing_to_fsm=False: (2, 0)
        )

        next_state, delay = runtime._fsm_state_gameplay_main_after_directional()

        self.assertEqual(next_state, FSM_STATE_CALLBACK_TIMING_FRAME)
        self.assertIsNone(delay)
        self.assertEqual(runtime._fsm_callback_ctx.get("timing_frames_left"), 2)
        self.assertEqual(runtime._fsm_callback_ctx.get("halt_frames_left"), 0)
        self.assertEqual(
            runtime._fsm_callback_ctx.get("return_state"),
            FSM_STATE_GAMEPLAY_MAIN_AFTER_CALLBACK,
        )

    def test_callback_timing_state_can_transition_into_halt_state(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._fsm_callback_ctx = {
            "timing_frames_left": 1,
            "halt_frames_left": 2,
            "return_state": FSM_STATE_GAMEPLAY_MAIN_AFTER_CALLBACK,
        }

        next_state, delay = runtime._fsm_state_callback_timing_frame()

        self.assertEqual(next_state, FSM_STATE_CALLBACK_HALT_65_FRAME)
        self.assertEqual(delay, 1)
        self.assertEqual(runtime._fsm_callback_ctx.get("frames_left"), 2)
        self.assertEqual(
            runtime._fsm_callback_ctx.get("return_state"),
            FSM_STATE_GAMEPLAY_MAIN_AFTER_CALLBACK,
        )

    def test_tick_stage_0_callback_timing_resume_to_next_stage(self) -> None:
        runtime = AlienEvolutionPort()
        runtime.var_runtime_move_state_code = 0x1C
        runtime._gameplay_tick_update_core_pre = lambda *, E_code, D_xor: None  # type: ignore[assignment]
        runtime._gameplay_tick_update_core_post = lambda: None  # type: ignore[assignment]
        runtime.fn_patchable_callback_hook_frame_loop = (  # type: ignore[assignment]
            lambda *, defer_halt_to_fsm=False, defer_timing_to_fsm=False: (1, 0)
        )
        runtime.fn_directional_interaction_dispatcher_using_pointer_table = (  # type: ignore[assignment]
            lambda *, defer_overlay_timing_to_fsm=False: None
        )

        next_state, delay = runtime._fsm_state_gameplay_tick_stage_0_frame()
        self.assertEqual(next_state, FSM_STATE_CALLBACK_TIMING_FRAME)
        self.assertIsNone(delay)

        next_state, delay = runtime._fsm_state_callback_timing_frame()
        self.assertEqual(next_state, FSM_STATE_GAMEPLAY_TICK_STAGE_0_FRAME)
        self.assertEqual(delay, 1)

        runtime.fn_patchable_callback_hook_frame_loop = (  # type: ignore[assignment]
            lambda *, defer_halt_to_fsm=False, defer_timing_to_fsm=False: (0, 0)
        )
        next_state, delay = runtime._fsm_state_gameplay_tick_stage_0_frame()
        self.assertEqual(next_state, FSM_STATE_GAMEPLAY_TICK_STAGE_1_FRAME)
        self.assertEqual(delay, max(1, int(GAMEPLAY_FRAME_DIVIDER)))

    def test_tick_stage_0_overlay_resume_to_next_stage(self) -> None:
        runtime = AlienEvolutionPort()
        runtime.var_runtime_move_state_code = 0x1C
        runtime._gameplay_tick_update_core_pre = lambda *, E_code, D_xor: None  # type: ignore[assignment]
        runtime._gameplay_tick_update_core_post = lambda: None  # type: ignore[assignment]
        runtime.fn_patchable_callback_hook_frame_loop = (  # type: ignore[assignment]
            lambda *, defer_halt_to_fsm=False, defer_timing_to_fsm=False: (0, 0)
        )
        runtime.fn_directional_interaction_dispatcher_using_pointer_table = (  # type: ignore[assignment]
            lambda *, defer_overlay_timing_to_fsm=False: runtime._fsm_overlay_ctx.update(
                {"pre_frames_left": 1, "post_frames_left": 0},
            )
        )

        next_state, delay = runtime._fsm_state_gameplay_tick_stage_0_frame()
        self.assertEqual(next_state, FSM_STATE_OVERLAY_PRE_FILL_FRAME)
        self.assertIsNone(delay)

        next_state, delay = runtime._fsm_state_overlay_pre_fill_frame()
        self.assertEqual(next_state, FSM_STATE_GAMEPLAY_TICK_STAGE_0_FRAME)
        self.assertEqual(delay, 1)

        runtime.fn_directional_interaction_dispatcher_using_pointer_table = (  # type: ignore[assignment]
            lambda *, defer_overlay_timing_to_fsm=False: None
        )
        next_state, delay = runtime._fsm_state_gameplay_tick_stage_0_frame()
        self.assertEqual(next_state, FSM_STATE_GAMEPLAY_TICK_STAGE_1_FRAME)
        self.assertEqual(delay, max(1, int(GAMEPLAY_FRAME_DIVIDER)))

    def test_main_post_tick_uses_default_host_frame_divider_when_move_state_is_teleport(self) -> None:
        runtime = AlienEvolutionPort()
        runtime.var_runtime_move_state_code = 0x1D
        runtime.fn_main_pseudo_3d_map_render_pipeline = lambda: None  # type: ignore[assignment]

        next_state, delay = runtime._fsm_state_gameplay_main_post_tick()

        self.assertEqual(next_state, FSM_STATE_GAMEPLAY_BRANCH)
        self.assertEqual(delay, max(1, int(GAMEPLAY_FRAME_DIVIDER)))

    def test_tick_stage_0_uses_default_host_frame_divider_when_move_state_is_teleport(self) -> None:
        runtime = AlienEvolutionPort()
        runtime.var_runtime_move_state_code = 0x1D
        runtime._gameplay_tick_update_core_pre = lambda *, E_code, D_xor: None  # type: ignore[assignment]
        runtime._gameplay_tick_update_core_post = lambda: None  # type: ignore[assignment]
        runtime.fn_patchable_callback_hook_frame_loop = (  # type: ignore[assignment]
            lambda *, defer_halt_to_fsm=False, defer_timing_to_fsm=False: (0, 0)
        )
        runtime.fn_directional_interaction_dispatcher_using_pointer_table = (  # type: ignore[assignment]
            lambda *, defer_overlay_timing_to_fsm=False: None
        )

        next_state, delay = runtime._fsm_state_gameplay_tick_stage_0_frame()

        self.assertEqual(next_state, FSM_STATE_GAMEPLAY_TICK_STAGE_1_FRAME)
        self.assertEqual(delay, max(1, int(GAMEPLAY_FRAME_DIVIDER)))

    def test_tick_stage_2_fails_fast_without_next_state_context(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._fsm_tick_ctx = {}
        with self.assertRaisesRegex(RuntimeError, "tick_stage3_next_state"):
            runtime._fsm_state_gameplay_tick_stage_2_frame()

    def test_tick_stage_2_accepts_explicit_next_state_context(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._fsm_tick_ctx = {"tick_stage3_next_state": FSM_STATE_GAMEPLAY_MAIN_FRAME}
        runtime._fsm_state_gameplay_tick_stage_frame = (  # type: ignore[assignment]
            lambda **kwargs: (kwargs["next_state"], None)
        )

        next_state, delay = runtime._fsm_state_gameplay_tick_stage_2_frame()

        self.assertEqual(next_state, FSM_STATE_GAMEPLAY_TICK_STAGE_3_FRAME)
        self.assertIsNone(delay)

    def test_tick_stage_3_fails_fast_without_next_state_context(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._fsm_tick_ctx = {}
        with self.assertRaisesRegex(RuntimeError, "tick_stage3_next_state"):
            runtime._fsm_state_gameplay_tick_stage_3_frame()

    def test_tick_stage_3_fails_fast_on_non_string_next_state_context(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._fsm_tick_ctx = {"tick_stage3_next_state": 123}
        with self.assertRaisesRegex(RuntimeError, "to be string"):
            runtime._fsm_state_gameplay_tick_stage_3_frame()

    def test_tick_stage_frame_fails_fast_without_phase_when_stage_matches(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._fsm_tick_ctx = {"tick_stage_id": "stage0"}
        with self.assertRaisesRegex(RuntimeError, "tick_stage_phase"):
            runtime._fsm_state_gameplay_tick_stage_0_frame()

    def test_tick_stage_frame_fails_fast_on_non_string_stage_id(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._fsm_tick_ctx = {
            "tick_stage_id": 123,
            "tick_stage_phase": "pre",
        }
        with self.assertRaisesRegex(RuntimeError, "tick_stage_id to be string"):
            runtime._fsm_state_gameplay_tick_stage_0_frame()

    def test_tick_stage_frame_fails_fast_on_non_string_phase(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._fsm_tick_ctx = {
            "tick_stage_id": "stage0",
            "tick_stage_phase": 123,
        }
        with self.assertRaisesRegex(RuntimeError, "tick_stage_phase to be string"):
            runtime._fsm_state_gameplay_tick_stage_0_frame()

    def test_callback_states_fail_fast_without_context(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._fsm_callback_ctx = {}
        with self.assertRaisesRegex(RuntimeError, "_fsm_callback_ctx"):
            runtime._fsm_state_callback_timing_frame()
        with self.assertRaisesRegex(RuntimeError, "_fsm_callback_ctx"):
            runtime._fsm_state_callback_halt_65_frame()

    def test_overlay_states_fail_fast_without_context(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._fsm_overlay_ctx = {}
        with self.assertRaisesRegex(RuntimeError, "_fsm_overlay_ctx"):
            runtime._fsm_state_overlay_pre_fill_frame()
        with self.assertRaisesRegex(RuntimeError, "_fsm_overlay_ctx"):
            runtime._fsm_state_overlay_post_fill_frame()

    def test_overlay_states_fail_fast_without_required_counters(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._fsm_overlay_ctx = {
            "return_state": FSM_STATE_GAMEPLAY_MAIN_AFTER_DIRECTIONAL,
        }
        with self.assertRaisesRegex(RuntimeError, "pre_frames_left"):
            runtime._fsm_state_overlay_pre_fill_frame()
        with self.assertRaisesRegex(RuntimeError, "post_frames_left"):
            runtime._fsm_state_overlay_post_fill_frame()

    def test_overlay_states_fail_fast_on_non_string_return_state(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._fsm_overlay_ctx = {
            "pre_frames_left": 0,
            "post_frames_left": 0,
            "return_state": 123,
        }
        with self.assertRaisesRegex(RuntimeError, "string return_state"):
            runtime._fsm_state_overlay_pre_fill_frame()
        with self.assertRaisesRegex(RuntimeError, "string return_state"):
            runtime._fsm_state_overlay_post_fill_frame()

    def test_directional_overlay_deferral_fails_fast_without_overlay_counters(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._fsm_step_active = True
        runtime._fsm_overlay_ctx = {}
        runtime.fn_main_pseudo_3d_map_render_pipeline = lambda: None  # type: ignore[assignment]
        runtime.fn_pre_action_overlay_painter_ui_area = (  # type: ignore[assignment]
            lambda *, defer_timing_to_fsm=False: 1
        )
        runtime.fn_post_action_overlay_painter_ui_area = (  # type: ignore[assignment]
            lambda *, defer_timing_to_fsm=False: 1
        )
        runtime.fn_convert_map_pointer_hl_row_column = lambda HL_cell: None  # type: ignore[assignment]

        probe = BlockPtr(runtime.var_level_map_mode_0, 0)
        pair = BlockPtr(runtime.var_level_map_mode_0, 1)
        runtime.var_level_map_mode_0[0] = 0x00
        runtime.var_level_map_mode_0[1] = 0x00
        with self.assertRaisesRegex(RuntimeError, "pre_frames_left"):
            runtime.fn_directional_action_validate_target(
                HL_probe=probe,
                HL_pair=pair,
                B_mask=0x01,
                C_flags=0x00,
                defer_overlay_timing_to_fsm=True,
            )

    def test_directional_overlay_deferral_captures_intermediate_snapshots(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._fsm_step_active = True
        runtime._fsm_overlay_ctx = {
            "pre_frames_left": 0,
            "post_frames_left": 0,
            "pre_frame_snapshots": [],
            "post_frame_snapshots": [],
            "pre_frame_cursor": 0,
            "post_frame_cursor": 0,
        }
        runtime.fn_convert_map_pointer_hl_row_column = lambda HL_cell: None  # type: ignore[assignment]

        probe = BlockPtr(runtime.var_level_map_mode_0, 0)
        pair = BlockPtr(runtime.var_level_map_mode_0, 1)
        runtime.var_level_map_mode_0[0] = 0x00
        runtime.var_level_map_mode_0[1] = 0x00

        out_flags = runtime.fn_directional_action_validate_target(
            HL_probe=probe,
            HL_pair=pair,
            B_mask=0x01,
            C_flags=0x00,
            defer_overlay_timing_to_fsm=True,
        )

        self.assertEqual(out_flags & 0x01, 0x01)
        pre_frames_left = int(runtime._fsm_overlay_ctx["pre_frames_left"])
        post_frames_left = int(runtime._fsm_overlay_ctx["post_frames_left"])
        pre_snapshots = runtime._fsm_overlay_ctx["pre_frame_snapshots"]
        post_snapshots = runtime._fsm_overlay_ctx["post_frame_snapshots"]
        self.assertGreater(pre_frames_left, 0)
        self.assertGreater(post_frames_left, 0)
        self.assertIsInstance(pre_snapshots, list)
        self.assertIsInstance(post_snapshots, list)
        self.assertEqual(len(pre_snapshots), pre_frames_left)
        self.assertEqual(len(post_snapshots), post_frames_left)

    def test_wait_keyboard_release_uses_explicit_return_state(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._fsm_menu_ctx["wait_release_return_state"] = FSM_STATE_TRANSITION_DISPATCH

        next_state, delay = runtime._fsm_state_wait_keyboard_release_frame()

        self.assertEqual(next_state, FSM_STATE_TRANSITION_DISPATCH)
        self.assertIsNone(delay)
        self.assertNotIn("wait_release_return_state", runtime._fsm_menu_ctx)

    def test_wait_keyboard_release_fails_without_return_state(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._fsm_menu_ctx.pop("wait_release_return_state", None)
        with self.assertRaisesRegex(RuntimeError, "wait_release_return_state"):
            runtime._fsm_state_wait_keyboard_release_frame()

    def test_wait_keyboard_release_fails_on_non_string_return_state(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._fsm_menu_ctx["wait_release_return_state"] = 123
        with self.assertRaisesRegex(RuntimeError, "string wait_release_return_state"):
            runtime._fsm_state_wait_keyboard_release_frame()

    def test_yield_host_frames_fails_fast_during_active_fsm_step(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._fsm_step_active = True
        with self.assertRaisesRegex(RuntimeError, "Legacy yield helper called"):
            runtime._yield_host_frames(1)

    def test_frame_delay_state_fails_fast_without_context(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._fsm_frame_delay_ctx = {}
        with self.assertRaisesRegex(RuntimeError, "_fsm_frame_delay_ctx"):
            runtime._fsm_state_frame_delay_0x50_frame()

    def test_frame_delay_state_fails_fast_without_frames_left(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._fsm_frame_delay_ctx = {
            "return_state": FSM_STATE_MENU_INIT,
        }
        with self.assertRaisesRegex(RuntimeError, "frames_left"):
            runtime._fsm_state_frame_delay_0x50_frame()

    def test_frame_delay_state_fails_fast_on_non_string_return_state(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._fsm_frame_delay_ctx = {
            "return_state": 123,
            "frames_left": 0,
        }
        with self.assertRaisesRegex(RuntimeError, "string return_state"):
            runtime._fsm_state_frame_delay_0x50_frame()

    def test_frame_delay_state_fails_fast_on_non_integer_frames_left(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._fsm_frame_delay_ctx = {
            "return_state": FSM_STATE_MENU_INIT,
            "frames_left": "0",
        }
        with self.assertRaisesRegex(RuntimeError, "integer frames_left"):
            runtime._fsm_state_frame_delay_0x50_frame()

    def test_level_roll_state_fails_fast_without_context(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._fsm_level_roll_ctx = {}
        with self.assertRaisesRegex(RuntimeError, "_fsm_level_roll_ctx"):
            runtime._fsm_state_level_roll_frame()

    def test_level_roll_state_fails_fast_without_steps_done(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._fsm_level_roll_ctx = {"frame_idx": 0}
        with self.assertRaisesRegex(RuntimeError, "frame_idx and steps_done"):
            runtime._fsm_state_level_roll_frame()

    def test_level_roll_state_fails_fast_on_non_integer_counters(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._fsm_level_roll_ctx = {
            "frame_idx": "0",
            "steps_done": 0,
        }
        with self.assertRaisesRegex(RuntimeError, "integer frame_idx"):
            runtime._fsm_state_level_roll_frame()

        runtime._fsm_level_roll_ctx = {
            "frame_idx": 0,
            "steps_done": "0",
        }
        with self.assertRaisesRegex(RuntimeError, "integer steps_done"):
            runtime._fsm_state_level_roll_frame()

    def test_stream_state_fails_fast_without_context(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._fsm_stream_ctx = {}
        with self.assertRaisesRegex(RuntimeError, "_fsm_stream_ctx"):
            runtime._fsm_state_stream_intermission_frame()

    def test_stream_state_fails_fast_without_timing_debt(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._fsm_stream_ctx = {
            "abort_on_keypress": True,
            "return_state": FSM_STATE_MENU_INIT,
        }
        with self.assertRaisesRegex(RuntimeError, "timing_debt"):
            runtime._fsm_state_stream_intermission_frame()

    def test_stream_state_fails_fast_without_abort_on_keypress(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._fsm_stream_ctx = {
            "timing_debt": 0,
            "return_state": FSM_STATE_MENU_INIT,
        }
        with self.assertRaisesRegex(RuntimeError, "abort_on_keypress"):
            runtime._fsm_state_stream_intermission_frame()

    def test_stream_state_fails_fast_on_non_bool_abort_on_keypress(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._fsm_stream_ctx = {
            "timing_debt": 0,
            "abort_on_keypress": "yes",
            "return_state": FSM_STATE_MENU_INIT,
        }
        with self.assertRaisesRegex(RuntimeError, "bool abort_on_keypress"):
            runtime._fsm_state_stream_intermission_frame()

    def test_menu_idle_state_fails_fast_without_prepared_flag(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._fsm_menu_ctx = {}
        with self.assertRaisesRegex(RuntimeError, "requires prepared"):
            runtime._fsm_state_menu_idle_poll_frame()

    def test_menu_idle_state_fails_fast_on_non_bool_prepared_flag(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._fsm_menu_ctx = {"prepared": 1}
        with self.assertRaisesRegex(RuntimeError, "bool prepared"):
            runtime._fsm_state_menu_idle_poll_frame()

    def test_gameplay_setup_fails_fast_without_initialized_flag(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._fsm_gameplay_ctx = {}
        with self.assertRaisesRegex(RuntimeError, "requires initialized"):
            runtime._fsm_state_gameplay_setup()

    def test_gameplay_setup_fails_fast_on_non_bool_initialized_flag(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._fsm_gameplay_ctx = {"initialized": 1}
        with self.assertRaisesRegex(RuntimeError, "bool initialized"):
            runtime._fsm_state_gameplay_setup()

    def test_stream_finish_on_key_abort_returns_configured_state(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._fsm_start_stream(
            stream_a=BlockPtr(runtime.const_scenario_preset_b_stream_1, 0x0000),
            stream_b=BlockPtr(runtime.const_scenario_preset_b_stream_2, 0x0000),
            abort_on_keypress=True,
            return_state=FSM_STATE_MENU_INIT,
        )
        runtime._rom_keyboard_input_poll_028e = lambda: 0x00  # type: ignore[assignment]

        next_state, delay = runtime._fsm_state_stream_intermission_frame()

        self.assertEqual(next_state, FSM_STATE_MENU_INIT)
        self.assertIsNone(delay)
        self.assertEqual(runtime._fsm_stream_ctx, {})
        self.assertTrue(runtime._interrupts_enabled)

    def test_stream_finish_fails_fast_on_non_string_return_state(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._fsm_stream_ctx = {
            "timing_debt": 0,
            "abort_on_keypress": True,
            "return_state": 123,
        }
        with self.assertRaisesRegex(RuntimeError, "string return_state"):
            runtime._fsm_finish_stream()

    def test_define_keys_state_fails_fast_without_context(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._fsm_define_keys_ctx = {}
        with self.assertRaisesRegex(RuntimeError, "_fsm_define_keys_ctx"):
            runtime._fsm_state_define_keys_wait_frame()

    def test_define_keys_state_fails_fast_without_phase(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._fsm_define_keys_ctx = {"slot_index": 0}
        with self.assertRaisesRegex(RuntimeError, "requires phase"):
            runtime._fsm_state_define_keys_wait_frame()

    def test_define_keys_state_fails_fast_on_non_string_phase_type(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._fsm_define_keys_ctx = {
            "phase": 123,
            "slot_index": 0,
        }
        with self.assertRaisesRegex(RuntimeError, "string phase"):
            runtime._fsm_state_define_keys_wait_frame()

    def test_define_keys_state_fails_fast_without_slot_index(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._fsm_define_keys_ctx = {"phase": "wait_release_before_slot"}
        with self.assertRaisesRegex(RuntimeError, "requires slot_index"):
            runtime._fsm_state_define_keys_wait_frame()

    def test_define_keys_state_fails_fast_on_non_integer_slot_index_type(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._fsm_define_keys_ctx = {
            "phase": "wait_release_before_slot",
            "slot_index": "0",
        }
        with self.assertRaisesRegex(RuntimeError, "integer slot_index"):
            runtime._fsm_state_define_keys_wait_frame()

    def test_define_keys_state_fails_fast_on_invalid_slot_index(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._fsm_define_keys_ctx = {
            "phase": "draw_icon",
            "slot_index": 255,
        }
        with self.assertRaisesRegex(RuntimeError, "invalid slot_index"):
            runtime._fsm_state_define_keys_wait_frame()

    def test_define_keys_state_fails_fast_on_unknown_phase(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._fsm_define_keys_ctx = {
            "phase": "unknown-phase",
            "slot_index": 0,
        }
        with self.assertRaisesRegex(RuntimeError, "Unknown define-keys phase"):
            runtime._fsm_state_define_keys_wait_frame()

    def test_highscore_states_fail_fast_without_context(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._fsm_highscore_ctx = {}
        with self.assertRaisesRegex(RuntimeError, "_fsm_highscore_ctx"):
            runtime._fsm_state_highscore_wait_key_frame()
        with self.assertRaisesRegex(RuntimeError, "_fsm_highscore_ctx"):
            runtime._fsm_state_highscore_filter_key_frame()
        with self.assertRaisesRegex(RuntimeError, "_fsm_highscore_ctx"):
            runtime._fsm_state_highscore_backspace_frame()
        with self.assertRaisesRegex(RuntimeError, "_fsm_highscore_ctx"):
            runtime._fsm_state_highscore_char_frame()

    def test_highscore_filter_and_char_fail_fast_without_pending_key(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._fsm_highscore_ctx = {
            "next_transition_kind": "failure_post_highscore",
            "return_state": FSM_STATE_TRANSITION_DISPATCH,
        }
        with self.assertRaisesRegex(RuntimeError, "pending_key"):
            runtime._fsm_state_highscore_filter_key_frame()
        with self.assertRaisesRegex(RuntimeError, "pending_key"):
            runtime._fsm_state_highscore_char_frame()

    def test_highscore_filter_and_char_fail_fast_on_non_integer_pending_key(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._fsm_highscore_ctx = {
            "next_transition_kind": "failure_post_highscore",
            "return_state": FSM_STATE_TRANSITION_DISPATCH,
            "pending_key": "x",
        }
        with self.assertRaisesRegex(RuntimeError, "integer pending_key"):
            runtime._fsm_state_highscore_filter_key_frame()

        runtime._fsm_highscore_ctx = {
            "next_transition_kind": "failure_post_highscore",
            "return_state": FSM_STATE_TRANSITION_DISPATCH,
            "pending_key": "x",
        }
        with self.assertRaisesRegex(RuntimeError, "integer pending_key"):
            runtime._fsm_state_highscore_char_frame()

    def test_highscore_finish_fails_fast_without_required_transition_keys(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._fsm_highscore_ctx = {"return_state": FSM_STATE_TRANSITION_DISPATCH}
        with self.assertRaisesRegex(RuntimeError, "next_transition_kind"):
            runtime._fsm_highscore_finish()

        runtime._fsm_highscore_ctx = {"next_transition_kind": "failure_post_highscore"}
        with self.assertRaisesRegex(RuntimeError, "return_state"):
            runtime._fsm_highscore_finish()

    def test_highscore_finish_fails_fast_on_non_string_transition_fields(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._fsm_highscore_ctx = {
            "next_transition_kind": 123,
            "return_state": FSM_STATE_TRANSITION_DISPATCH,
        }
        with self.assertRaisesRegex(RuntimeError, "string next_transition_kind"):
            runtime._fsm_highscore_finish()

        runtime._fsm_highscore_ctx = {
            "next_transition_kind": "ending_post_highscore",
            "return_state": 123,
        }
        with self.assertRaisesRegex(RuntimeError, "string return_state"):
            runtime._fsm_highscore_finish()

    def test_highscore_finish_applies_configured_transition_and_clears_context(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._fsm_transition_kind = "none"
        runtime._fsm_highscore_ctx = {
            "next_transition_kind": "ending_post_highscore",
            "return_state": FSM_STATE_TRANSITION_DISPATCH,
            "pending_key": 0x0D,
        }

        next_state, delay = runtime._fsm_highscore_finish()

        self.assertEqual(next_state, FSM_STATE_TRANSITION_DISPATCH)
        self.assertIsNone(delay)
        self.assertEqual(runtime._fsm_transition_kind, "ending_post_highscore")
        self.assertEqual(runtime._fsm_highscore_ctx, {})

    def test_transition_dispatch_failure_routes_into_timer_drain_state(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._fsm_transition_kind = "failure"
        runtime.var_runtime_current_cell_ptr = BlockPtr(runtime.var_level_map_mode_0, 0x0000)
        runtime.var_level_map_mode_0[0] = 0xAB
        runtime._fsm_tick_ctx = {
            "pending_autonomous": True,
            "pending_marker": True,
            "scheduler_phase": "after_tick0",
            "scheduler_return_state": FSM_STATE_MENU_INIT,
            "tick_stage_phase": "after_overlay",
            "tick_stage_id": "stage3",
            "tick_stage3_next_state": FSM_STATE_TRANSITION_DISPATCH,
        }

        next_state, delay = runtime._fsm_state_transition_dispatch()

        self.assertEqual(next_state, FSM_STATE_FAILURE_TIMER_DRAIN_FRAME)
        self.assertIsNone(delay)
        self.assertEqual(runtime.patch_gameplay_movement_step_opcode & 0xFF, 0xC9)
        self.assertEqual(runtime.var_level_map_mode_0[0], 0x80)
        self.assertFalse(runtime._fsm_tick_ctx["pending_autonomous"])
        self.assertFalse(runtime._fsm_tick_ctx["pending_marker"])
        self.assertNotIn("scheduler_phase", runtime._fsm_tick_ctx)
        self.assertNotIn("scheduler_return_state", runtime._fsm_tick_ctx)
        self.assertNotIn("tick_stage_phase", runtime._fsm_tick_ctx)
        self.assertNotIn("tick_stage_id", runtime._fsm_tick_ctx)
        self.assertNotIn("tick_stage3_next_state", runtime._fsm_tick_ctx)

    def test_failure_timer_drain_state_routes_pending_autonomous_into_scheduler_state(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._fsm_step_active = True
        runtime.var_runtime_scheduler_timer = 0x0101
        runtime.patch_scheduler_script_base_ptr = 0
        runtime.const_periodic_scheduler_script[0] = 0x01

        next_state, delay = runtime._fsm_state_failure_timer_drain_frame()

        self.assertEqual(next_state, FSM_STATE_SCHEDULER_AUTONOMOUS_FRAME)
        self.assertIsNone(delay)
        self.assertEqual(runtime._fsm_tick_ctx.get("scheduler_phase"), "tick0")
        self.assertEqual(
            runtime._fsm_tick_ctx.get("scheduler_return_state"),
            FSM_STATE_FAILURE_TIMER_DRAIN_FRAME,
        )

    def test_failure_timer_drain_state_finishes_cleanup_and_enters_frame_delay(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._fsm_step_active = True
        runtime.var_runtime_scheduler_timer = 0x0101
        runtime.patch_scheduler_script_base_ptr = 0
        runtime.const_periodic_scheduler_script[0] = 0x00
        runtime._fsm_gameplay_ctx["initialized"] = True
        runtime._set_patch_gameplay_movement_step_opcode(0xC9)
        calls: list[tuple[str, int | None]] = []

        runtime.fn_rectangular_panel_fill_helper = (  # type: ignore[assignment]
            lambda A_fill: calls.append(("fill", int(A_fill) & 0xFF))
        )
        runtime.fn_draw_mission_status_panel_bitmap_chunk = (  # type: ignore[assignment]
            lambda: calls.append(("panel", None))
        )
        runtime.fn_transition_beeper_helper = lambda: calls.append(("beeper", None))  # type: ignore[assignment]

        next_state, delay = runtime._fsm_state_failure_timer_drain_frame()

        self.assertEqual(next_state, FSM_STATE_FRAME_DELAY_0X50_FRAME)
        self.assertIsNone(delay)
        self.assertEqual(runtime.patch_gameplay_movement_step_opcode & 0xFF, 0x3A)
        self.assertEqual(calls, [("fill", 0x00), ("panel", None), ("beeper", None)])
        self.assertEqual(runtime._fsm_transition_kind, "failure_post_delay")
        self.assertFalse(runtime._fsm_gameplay_ctx["initialized"])
        self.assertEqual(runtime._fsm_frame_delay_ctx["frames_left"], 0x50)
        self.assertEqual(runtime._fsm_frame_delay_ctx["return_state"], FSM_STATE_TRANSITION_DISPATCH)

    def test_transition_dispatch_fails_fast_on_unknown_kind(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._fsm_transition_kind = "none"
        with self.assertRaisesRegex(RuntimeError, "Unknown FSM transition kind"):
            runtime._fsm_state_transition_dispatch()

    def test_transition_dispatch_fails_fast_on_non_string_kind(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._fsm_transition_kind = 123  # type: ignore[assignment]
        with self.assertRaisesRegex(RuntimeError, "string _fsm_transition_kind"):
            runtime._fsm_state_transition_dispatch()

    def test_legacy_callback_hook_fails_fast_during_active_fsm_step(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._fsm_step_active = True
        with self.assertRaisesRegex(RuntimeError, "Legacy callback hook path called"):
            runtime.fn_patchable_callback_hook_frame_loop()

    def test_legacy_directional_dispatcher_fails_fast_during_active_fsm_step(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._fsm_step_active = True
        with self.assertRaisesRegex(RuntimeError, "Legacy directional dispatcher path called"):
            runtime.fn_directional_interaction_dispatcher_using_pointer_table()

    def test_legacy_tick_core_fails_fast_during_active_fsm_step(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._fsm_step_active = True
        with self.assertRaisesRegex(RuntimeError, "Legacy gameplay tick core called"):
            runtime.fn_main_gameplay_tick_update_core(E_code=0x26, D_xor=0x00)

    def test_legacy_tick_updater_fails_fast_during_active_fsm_step(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._fsm_step_active = True
        with self.assertRaisesRegex(RuntimeError, "Legacy gameplay tick updater called"):
            runtime.fn_main_gameplay_tick_updater()

    def test_legacy_wait_keyboard_release_fails_fast_during_active_fsm_step(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._fsm_step_active = True
        with self.assertRaisesRegex(RuntimeError, "Legacy keyboard-release wait called"):
            runtime._wait_keyboard_release()

    def test_legacy_menu_loop_fails_fast_during_active_fsm_step(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._fsm_step_active = True
        with self.assertRaisesRegex(RuntimeError, "Legacy menu control loop called"):
            runtime.top_level_pre_game_control_loop()

    def test_legacy_define_keys_wait_loop_fails_fast_during_active_fsm_step(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._fsm_step_active = True
        with self.assertRaisesRegex(RuntimeError, "Legacy define-keys wait loop called"):
            runtime.fn_define_keys_wait_loop()

    def test_legacy_gameplay_session_controller_fails_fast_during_active_fsm_step(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._fsm_step_active = True
        with self.assertRaisesRegex(RuntimeError, "Legacy gameplay session controller called"):
            runtime.gameplay_session_controller()

    def test_legacy_frame_delay_loop_fails_fast_during_active_fsm_step(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._fsm_step_active = True
        with self.assertRaisesRegex(RuntimeError, "Legacy frame-delay loop called"):
            runtime.fn_frame_delay_loop()

    def test_legacy_stream_intermission_loop_fails_fast_during_active_fsm_step(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._fsm_step_active = True
        with self.assertRaisesRegex(RuntimeError, "Legacy stream intermission loop called"):
            runtime.scenario_intermission_beeper_stream_player_loop()

    def test_callback_states_fail_fast_without_required_counters(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._fsm_callback_ctx = {"return_state": FSM_STATE_GAMEPLAY_MAIN_AFTER_CALLBACK}
        with self.assertRaisesRegex(RuntimeError, "timing_frames_left"):
            runtime._fsm_state_callback_timing_frame()
        with self.assertRaisesRegex(RuntimeError, "frames_left"):
            runtime._fsm_state_callback_halt_65_frame()

    def test_callback_states_fail_fast_on_non_string_return_state(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._fsm_callback_ctx = {
            "return_state": 123,
            "timing_frames_left": 0,
            "halt_frames_left": 0,
        }
        with self.assertRaisesRegex(RuntimeError, "string return_state"):
            runtime._fsm_state_callback_timing_frame()

        runtime._fsm_callback_ctx = {
            "return_state": 123,
            "frames_left": 0,
        }
        with self.assertRaisesRegex(RuntimeError, "string return_state"):
            runtime._fsm_state_callback_halt_65_frame()

    def test_callback_states_fail_fast_on_non_integer_counters(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._fsm_callback_ctx = {
            "return_state": FSM_STATE_GAMEPLAY_MAIN_AFTER_CALLBACK,
            "timing_frames_left": "0",
            "halt_frames_left": 0,
        }
        with self.assertRaisesRegex(RuntimeError, "integer timing_frames_left"):
            runtime._fsm_state_callback_timing_frame()

        runtime._fsm_callback_ctx = {
            "return_state": FSM_STATE_GAMEPLAY_MAIN_AFTER_CALLBACK,
            "timing_frames_left": 0,
            "halt_frames_left": "0",
        }
        with self.assertRaisesRegex(RuntimeError, "integer halt_frames_left"):
            runtime._fsm_state_callback_timing_frame()

        runtime._fsm_callback_ctx = {
            "return_state": FSM_STATE_GAMEPLAY_MAIN_AFTER_CALLBACK,
            "frames_left": "0",
        }
        with self.assertRaisesRegex(RuntimeError, "integer frames_left"):
            runtime._fsm_state_callback_halt_65_frame()

    def test_callback_halt_state_counts_down_and_returns_to_continuation(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._fsm_callback_ctx = {
            "frames_left": 2,
            "return_state": FSM_STATE_GAMEPLAY_MAIN_AFTER_CALLBACK,
        }

        next_state, delay = runtime._fsm_state_callback_halt_65_frame()
        self.assertEqual(next_state, FSM_STATE_CALLBACK_HALT_65_FRAME)
        self.assertEqual(delay, 1)
        self.assertEqual(runtime._fsm_callback_ctx.get("frames_left"), 1)

        next_state, delay = runtime._fsm_state_callback_halt_65_frame()
        self.assertEqual(next_state, FSM_STATE_GAMEPLAY_MAIN_AFTER_CALLBACK)
        self.assertEqual(delay, 1)
        self.assertEqual(runtime._fsm_callback_ctx, {})

    def test_gameplay_main_after_callback_routes_scheduler_pending_autonomous(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._fsm_tick_ctx = {}
        runtime.fn_periodic_scheduler_tick = lambda: (  # type: ignore[assignment]
            runtime._fsm_tick_ctx.__setitem__("pending_autonomous", True),
            runtime._fsm_tick_ctx.__setitem__("pending_marker", False),
        )

        next_state, delay = runtime._fsm_state_gameplay_main_after_callback()

        self.assertEqual(next_state, FSM_STATE_SCHEDULER_AUTONOMOUS_FRAME)
        self.assertIsNone(delay)
        self.assertEqual(runtime._fsm_tick_ctx.get("scheduler_phase"), "tick0")

    def test_gameplay_main_after_callback_fails_fast_without_pending_keys(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._fsm_tick_ctx = {}
        runtime.fn_periodic_scheduler_tick = lambda: None  # type: ignore[assignment]
        with self.assertRaisesRegex(RuntimeError, "pending_autonomous"):
            runtime._fsm_state_gameplay_main_after_callback()

    def test_gameplay_main_after_callback_fails_fast_on_non_bool_pending_flags(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._fsm_tick_ctx = {
            "pending_autonomous": "yes",
            "pending_marker": False,
        }
        runtime.fn_periodic_scheduler_tick = lambda: None  # type: ignore[assignment]
        with self.assertRaisesRegex(RuntimeError, "bool pending_autonomous"):
            runtime._fsm_state_gameplay_main_after_callback()

        runtime._fsm_tick_ctx = {
            "pending_autonomous": True,
            "pending_marker": "no",
        }
        runtime.fn_periodic_scheduler_tick = lambda: None  # type: ignore[assignment]
        with self.assertRaisesRegex(RuntimeError, "bool pending_marker"):
            runtime._fsm_state_gameplay_main_after_callback()

    def test_gameplay_main_after_callback_fails_fast_on_invalid_pending_marker_invariant(self) -> None:
        runtime = AlienEvolutionPort()
        runtime._fsm_tick_ctx = {
            "pending_autonomous": False,
            "pending_marker": True,
        }
        runtime.fn_periodic_scheduler_tick = lambda: None  # type: ignore[assignment]
        with self.assertRaisesRegex(RuntimeError, "pending_marker requires pending_autonomous=True"):
            runtime._fsm_state_gameplay_main_after_callback()

    def test_scheduler_triggered_autonomous_step_keeps_rebalance_when_run_tick_false(self) -> None:
        runtime = AlienEvolutionPort()
        observed: dict[str, int | bool] = {"rebalance_calls": 0, "hud_calls": 0}

        def _autonomous(*, run_tick: bool = True) -> None:
            observed["run_tick"] = run_tick

        def _rebalance(queue_state, E_bias: int) -> None:  # type: ignore[no-untyped-def]
            observed["rebalance_calls"] = int(observed["rebalance_calls"]) + 1

        def _hud() -> None:
            observed["hud_calls"] = int(observed["hud_calls"]) + 1

        runtime.autonomous_expansion_pass = _autonomous  # type: ignore[assignment]
        runtime.fn_counter_rebalance_helper = _rebalance  # type: ignore[assignment]
        runtime.fn_rebuild_hud_meter_bars_counters_xa8c4 = _hud  # type: ignore[assignment]

        runtime.scheduler_triggered_autonomous_step(run_tick=False)

        self.assertEqual(observed.get("run_tick"), False)
        self.assertEqual(observed.get("rebalance_calls"), 3)
        self.assertEqual(observed.get("hud_calls"), 1)


class RuntimeStateBaseValidationTests(unittest.TestCase):
    def test_rebind_validation_accepts_valid_types(self) -> None:
        runtime = _RebindValidationRuntime()
        runtime._state_validate_rebind_pointer_fields()

    def test_rebind_validation_rejects_missing_pointer_field(self) -> None:
        runtime = _RebindValidationRuntime()
        delattr(runtime, "block_ptr_field")
        with self.assertRaisesRegex(ValueError, "Missing rebind BlockPtr field"):
            runtime._state_validate_rebind_pointer_fields()

    def test_rebind_validation_rejects_wrong_pointer_type(self) -> None:
        runtime = _RebindValidationRuntime()
        runtime.struct_ptr_field = "wrong-type"
        with self.assertRaisesRegex(ValueError, "is not StructFieldPtr"):
            runtime._state_validate_rebind_pointer_fields()


if __name__ == "__main__":
    unittest.main()
