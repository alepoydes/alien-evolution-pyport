; Manual game-wide CTL (editable baseline)
; Label: AlienEvolution
;
; Project-level overview (memory layout, render anchors, and main-loop flow)
; is documented in:
;   GAME_FACTS.md
;
; This CTL is intended to be snapshot-agnostic for Alien Evolution RAM layout:
; it should annotate any compatible game snapshot (raw .sna and RZX-derived runs).
@ 16384 start
@ 16384 org
@ 16384 label=var_display_bitmap_ram
b 16384 var_display_bitmap_ram
D 16384 ZX display bitmap RAM (0x4000-0x57FF, 6144 bytes), live framebuffer used by current frame.
D 16384 #SCR(2,0,0,32,24,16384,22528)(*display_runtime_frame)#FRAMES(display_runtime_frame)(display_runtime_frame|Current snapshot display frame: bitmap 0x4000-0x57FF + attrs 0x5800-0x5AFF)
D 16384 Structure: ZX bitmap framebuffer bytes in native Spectrum screen-line layout (6144 bytes total).
@ 16385 label=var_display_bitmap_copy_tail_anchor_4001
@ 16417 label=var_display_bitmap_strip_dst_anchor_4021
@ 18432 label=var_display_bitmap_lower_clear_base_4800
@ 18433 label=var_display_bitmap_lower_clear_tail_4801
@ 20480 label=var_display_bitmap_mission_panel_dst_5000
@ 22528 label=var_display_attribute_ram
b 22528 var_display_attribute_ram
D 22528 ZX display attribute RAM (0x5800-0x5AFF, 768 bytes), color attributes for the current frame.
D 22528 Structure: 24x32 attribute matrix (row-major, 1 byte per cell).
@ 22529 label=var_display_attribute_ram_anchor_5801
@ 22556 label=var_display_attribute_ram_anchor_581c
@ 22561 label=var_display_attribute_ram_anchor_5821
@ 22586 label=var_display_attribute_ram_anchor_583a
@ 22589 label=var_display_attribute_ram_anchor_583d
@ 22593 label=var_display_attribute_ram_anchor_5841
@ 22618 label=var_display_attribute_ram_anchor_585a
@ 22684 label=var_display_attribute_ram_anchor_589c
@ 22717 label=var_display_attribute_ram_anchor_58bd
@ 22721 label=var_display_attribute_ram_anchor_58c1
@ 22784 label=var_display_attribute_ram_anchor_5900
@ 22785 label=var_display_attribute_ram_anchor_5901
@ 22792 label=var_display_attribute_ram_anchor_5908
@ 22794 label=var_display_attribute_ram_anchor_590a
@ 22800 label=var_display_attribute_ram_anchor_5910
@ 22812 label=var_display_attribute_ram_anchor_591c
@ 22816 label=var_display_attribute_ram_anchor_5920
@ 22817 label=var_display_attribute_ram_anchor_5921
@ 22845 label=var_display_attribute_ram_anchor_593d
@ 22848 label=var_display_attribute_ram_anchor_5940
@ 22857 label=var_display_attribute_ram_anchor_5949
@ 22858 label=var_display_attribute_ram_anchor_594a
@ 22859 label=var_display_attribute_ram_anchor_594b
@ 22880 label=var_display_attribute_ram_anchor_5960
@ 22884 label=var_display_attribute_ram_anchor_5964
@ 22891 label=var_display_attribute_ram_anchor_596b
@ 22916 label=var_display_attribute_ram_anchor_5984
@ 22940 label=var_display_attribute_ram_anchor_599c
@ 22973 label=var_display_attribute_ram_anchor_59bd
@ 23008 label=var_display_attribute_ram_anchor_59e0
@ 23040 label=var_display_attribute_ram_anchor_5a00
@ 23089 label=var_display_attribute_ram_anchor_5a31
@ 23091 label=var_display_attribute_ram_anchor_5a33
@ 23164 label=var_display_attribute_ram_anchor_5a7c
@ 23166 label=var_display_attribute_ram_anchor_5a7e
@ 23168 label=var_display_attribute_ram_anchor_5a80
@ 23173 label=var_display_attribute_ram_anchor_5a85
@ 23196 label=var_display_attribute_ram_anchor_5a9c
@ 23198 label=var_display_attribute_ram_anchor_5a9e
@ 23237 label=var_display_attribute_ram_anchor_5ac5
@ 23238 label=var_display_attribute_ram_anchor_5ac6
@ 23253 label=var_display_attribute_ram_anchor_5ad5
@ 23254 label=var_display_attribute_ram_anchor_5ad6
@ 23264 label=var_display_attribute_ram_anchor_5ae0
@ 23265 label=var_display_attribute_ram_anchor_5ae1
@ 23269 label=var_display_attribute_ram_anchor_5ae5
@ 23270 label=var_display_attribute_ram_anchor_5ae6
@ 23285 label=var_display_attribute_ram_anchor_5af5
@ 23286 label=var_display_attribute_ram_anchor_5af6
b 23296 var_zx_system_workspace_ram
D 23296 ZX 48K system area (0x5B00-0x5DBF): printer buffer + ROM system variables/channels/workspace; values are runtime state, not game asset tables.
D 23296 Structure: ZX system snapshot image; coarse subranges are 0x5B00-0x5BFF (printer buffer), 0x5C00-0x5CB5 (ROM system vars), 0x5CB6-0x5DBF (channels/workspace).
@ 23624 label=var_rom_border_shadow_byte
@ 24000 label=const_title_bitmap_source
b 24000 const_title_bitmap_source
D 24000 Title screen source bitmap (0x5DC0-0x65BF, 2048 bytes).
D 24000 #SCR(2,0,0,32,8,24000,26048)(*title_src_bitmap)#FRAMES(title_src_bitmap)(title_source_bitmap|Title screen source bitmap preview)
D 24000 Structure: title image bitmap source as 256 cells x 8 bytes (32x8 cell grid).
@ 24582 label=const_title_bitmap_patch_anchor_6006
@ 26048 label=const_title_attr_source
b 26048 const_title_attr_source
D 26048 Title screen source attributes (0x65C0-0x66BF, 256 bytes).
D 26048 Structure: 8x32 attribute matrix for the title-source image (row-major, 256 bytes).
@ 26302 label=const_text_glyph_bias_word_66be
b 26304 const_text_glyph_source_head
D 26304 Core text-glyph source region head (code windows 0..83): 0xEAC3 addressing 0x66BE+8*(code+17) maps this part to 0x6746-0x69DD.
D 26304 #UDGARRAY16,56,2,1,0(26438-27205-8-128)(*font_glyph_table_code_order)#FRAMES(font_glyph_table_code_order)(font_glyph_table_code_order|Primary text glyph source windows in code order (0..95), 8x8)
D 26304 #HTML(<style>.font_all_table td{white-space:nowrap;vertical-align:middle;}.font_all_table img{image-rendering:pixelated;}.font_stretch{display:inline-block;width:16px;height:32px;overflow:hidden;}.font_stretch img{width:16px !important;height:32px !important;image-rendering:pixelated;}</style>)#TABLE(font_all_table){ =h Code | =h Source glyph 8x8 window (used by 0xEAC3) | =h 8x16 stretched preview }#FOR0,95,1/^%I%^{ #N(%I%,3) | #UDGARRAY1,56,2,1,0((26302+(%I%+17)*8)-(26302+(%I%+17)*8))(font_src_%I%|code %I%, source window) | #HTML(<div class="font_stretch">)#UDGARRAY1,56,2,1,0((26302+(%I%+17)*8)-(26302+(%I%+17)*8))(font_stretch_%I%|code %I%, vertically stretched 8x16 preview)#HTML(</div>) }^ ^/TABLE#
D 26304 Structure: contiguous 8-byte glyph windows used by text renderer address formula HL=0x66BE+8*(code+17).
@ 27110 label=const_control_icon_set_table
b 27110 const_control_icon_set_table
D 27110 Control-icon sets #1..#6 (192 bytes total at 0x69E6-0x6AA5), consumed by drawer 0x6CD8 via selector stubs 0x6EAA..0x6EC8.
D 27110 Storage format per icon set (32 bytes => 16x16): left half (16 bytes, 8x16) followed by right half (16 bytes, 8x16); each byte is one row (bit7 leftmost pixel, bit0 rightmost), rows ordered top->bottom.
D 27110 Equivalent 8x8-quadrant assembly order is [1 2; 4 3]: (base+0, base+16, base+8, base+24).
D 27110 Set starts: #1 0x69E6 (overlaps windows 84..87), #2 0x6A06 (88..91), #3 0x6A26 (92..95), #4 0x6A46 (96..99), #5 0x6A66, #6 0x6A86.
D 27110 In text paths, code 96 (<SYM60>) uses 0x6A46-0x6A4D from set #4 and appears in menu streams 0x6C19/0x6C25/0x6C35/0x6C41/0x6C4B/0x6C5A.
D 27110 #HTML(<style>.control_icons td{white-space:nowrap;vertical-align:middle;}.control_icons img{image-rendering:pixelated;}</style>)#TABLE(control_icons){ =h Icon | =h 16x16 preview }#FOR1,6,1/^%I%^{ #N(%I%,1) | #UDGARRAY2,56,4,1,0((27110+(%I%-1)*32+0)-(27110+(%I%-1)*32+0);(27110+(%I%-1)*32+16)-(27110+(%I%-1)*32+16);(27110+(%I%-1)*32+8)-(27110+(%I%-1)*32+8);(27110+(%I%-1)*32+24)-(27110+(%I%-1)*32+24))(control_icon_%I%|Control icon #%I% assembled as [1 2;4 3]) }^ ^/TABLE#
D 27110 Structure: 6 icon records x 32 bytes; each record is [left_half_8x16 (16 bytes), right_half_8x16 (16 bytes)].
@ 27142 label=const_control_icon_set_2
@ 27174 label=const_control_icon_set_3
@ 27206 label=const_control_icon_set_4
@ 27238 label=const_control_icon_set_5
@ 27270 label=const_control_icon_set_6
b 27302 const_unresolved_pattern_candidate_16b
D 27302 Unresolved 16-byte pattern candidate block (not directly seeded by current absolute DE loaders).
D 27302 Structure: opaque 16-byte blob; no stable field boundaries proven yet.
b 27318 const_unresolved_pre_highscore_tail
D 27318 Unresolved trailing bytes before high-score row templates.
D 27318 Structure: opaque 7-byte tail before high-score templates; no stable field boundaries proven yet.
@ 27325 label=str_highscore_row_template_1
t 27325 str_highscore_row_template_1
D 27325 High-score row template #1 for 0xEAE2 stream printer.
D 27325 Decoded text stream: "1-MARCO & TITO...-000000".
@ 27343 label=str_highscore_row_template_1_score_field
@ 27350 label=str_highscore_row_template_2
t 27350 str_highscore_row_template_2
D 27350 High-score row template #2 for 0xEAE2 stream printer.
D 27350 Decoded text stream: "2-ALIEN EVOLUTION-000000".
@ 27368 label=str_highscore_row_template_2_score_field
@ 27375 label=str_highscore_row_template_3
t 27375 str_highscore_row_template_3
D 27375 High-score row template #3 for 0xEAE2 stream printer.
D 27375 Decoded text stream: "3-GREMLIN........-000000".
@ 27393 label=str_highscore_row_template_3_score_field
@ 27400 label=str_highscore_row_template_4
t 27400 str_highscore_row_template_4
D 27400 High-score row template #4 for 0xEAE2 stream printer.
D 27400 Decoded text stream: "4-ALGARVE........-000000".
@ 27418 label=str_highscore_row_template_4_score_field
@ 27425 label=str_highscore_row_template_5
t 27425 str_highscore_row_template_5
D 27425 High-score row template #5 for 0xEAE2 stream printer.
D 27425 Decoded text stream: "5-THE END........-000000".
@ 27443 label=str_highscore_row_template_5_score_field
@ 27450 label=fn_title_top_screen_setup
c 27450 fn_title_top_screen_setup
D 27450 Title/top-screen setup: copy static title image source into display memory and clear remaining screen bands.
N 27450 Args: none.
N 27450 Returns: none.
N 27450 def fn_title_top_screen_setup():
N 27450 ↳var_display_bitmap_ram[0x0000:0x0800] = const_title_bitmap_source[0x0000:0x0800]
N 27450 ↳var_display_attribute_ram[0x0000:0x0100] = const_title_attr_source[0x0000:0x0100]
N 27450 ↳var_display_attribute_ram[0x0100:0x0300] = 0x00
N 27450 ↳OUT_0xFE = 0x00
N 27450 ↳var_rom_border_shadow_byte = 0x00
N 27450 ↳var_display_bitmap_ram[0x0800:0x1800] = 0x00
@ 27503 label=fn_title_screen_text_compositor
c 27503 fn_title_screen_text_compositor
D 27503 Title-screen text compositor: prints six 8x16 lines via 0xEAE2, then draws byline via 0x6B9D (8x8 path).
N 27503 Args: none.
N 27503 Returns: none.
N 27503 def fn_title_screen_text_compositor():
N 27503 ↳fn_title_top_screen_setup()
N 27503 ↳fn_stretched_text_symbol_stream_printer(HL_stream=str_frontend_option_stream_1, B_row=0x0A, C_col=0x09)
N 27503 ↳fn_stretched_text_symbol_stream_printer(HL_stream=str_frontend_option_stream_2, B_row=0x0C, C_col=0x09)
N 27503 ↳fn_stretched_text_symbol_stream_printer(HL_stream=str_frontend_option_stream_3, B_row=0x0E, C_col=0x09)
N 27503 ↳fn_stretched_text_symbol_stream_printer(HL_stream=str_frontend_option_stream_4, B_row=0x10, C_col=0x09)
N 27503 ↳fn_stretched_text_symbol_stream_printer(HL_stream=str_frontend_option_stream_5, B_row=0x12, C_col=0x09)
N 27503 ↳fn_stretched_text_symbol_stream_printer(HL_stream=str_frontend_option_stream_6, B_row=0x14, C_col=0x09)
N 27503 ↳fn_compact_8x8_text_renderer()
N 27503 ↳front_end_highlight_initializer()
@ 27565 label=fn_compact_8x8_text_renderer
c 27565 fn_compact_8x8_text_renderer
D 27565 Compact 8x8 text renderer: read byte codes at HL until 0xFF, map code C to glyph window 0x66BE+8*(C+1), and blit one 8-row cell via 0xEAA6.
N 27565 Args: none (uses fixed source stream str_byline_stream and fixed cursor row/column 0x17/0x01).
N 27565 Returns: none.
N 27565 def fn_compact_8x8_text_renderer():
N 27565 ↳HL_stream = str_byline_stream
N 27565 ↳const_highscore_header_tail_word = HL_stream
N 27565 ↳B_row, C_col = 0x17, 0x01
N 27565 ↳while True:
N 27565 ↳↳A_code = HL_stream[0x00]
N 27565 ↳↳if A_code == 0xFF:
N 27565 ↳↳↳break
N 27565 ↳↳DE_glyph = 0x66BE + ((A_code + 0x01) << 0x03)
N 27565 ↳↳fn_routine_8_byte_screen_blit_primitive(DE_src=DE_glyph, B_row=B_row, C_col=C_col)
N 27565 ↳↳C_col += 0x01
N 27565 ↳↳HL_stream = const_highscore_header_tail_word + 0x0001
N 27565 ↳↳const_highscore_header_tail_word = HL_stream
N 27565 ↳mem[0x5AE0:0x5B00] = 0x04
@ 27620 label=front_end_highlight_initializer
c 27620 front_end_highlight_initializer
D 27620 Front-end highlight initializer: paint 12 selector cells and branch into shared marker redraw at 0x6BE1.
N 27620 Args: none.
N 27620 Returns: none.
N 27620 def front_end_highlight_initializer():
N 27620 ↳HL_cell = 0x5949
N 27620 ↳for _ in range(0x0C):
N 27620 ↳↳HL_cell[0x00] = 0x0F
N 27620 ↳↳HL_cell += 0x20
N 27620 ↳fn_front_end_selection_bars_redraw()
@ 27633 label=fn_front_end_selection_bars_redraw
c 27633 fn_front_end_selection_bars_redraw
D 27633 Secondary front-end selection-bars redraw entry: repaints two interlaced 24-byte bars for active menu row.
N 27633 Args: none.
N 27633 Returns: none.
N 27633 def fn_front_end_selection_bars_redraw():
N 27633 ↳fn_attribute_span_fill_helper(HL_dst=0x594B, A_fill=0x05)
N 27633 ↳fn_attribute_span_fill_helper(HL_dst=0x596B, A_fill=0x07)
@ 27650 label=fn_attribute_span_fill_helper
c 27650 fn_attribute_span_fill_helper
D 27650 Attribute-span fill helper: write A over 6 rows of 24 bytes with 0x40 stride (menu/high-score frames).
N 27650 Args: HL_dst is ptr_u8 to the first attribute cell of the row-group; A_fill is u8 attribute value.
N 27650 Returns: none.
N 27650 def fn_attribute_span_fill_helper(HL_dst, A_fill):
N 27650 ↳for _ in range(0x06):
N 27650 ↳↳HL_dst[0x00:0x18] = A_fill
N 27650 ↳↳HL_dst += 0x40
@ 27673 label=str_frontend_option_stream_1
t 27673 str_frontend_option_stream_1
D 27673 Front-end option stream #1 for 0xEAE2 (code 96 = <SYM60> control icon glyph).
D 27673 Decoded text stream: "1<SYM60>-KEYBOARD".
@ 27685 label=str_frontend_option_stream_2
t 27685 str_frontend_option_stream_2
D 27685 Front-end option stream #2 for 0xEAE2.
D 27685 Decoded text stream: "2<SYM60>-INTERFACE II".
@ 27701 label=str_frontend_option_stream_3
t 27701 str_frontend_option_stream_3
D 27701 Front-end option stream #3 for 0xEAE2.
D 27701 Decoded text stream: "3<SYM60>-KEMPSTON".
@ 27713 label=str_frontend_option_stream_4
t 27713 str_frontend_option_stream_4
D 27713 Front-end option stream #4 for 0xEAE2.
D 27713 Decoded text stream: "4<SYM60>-CURSOR".
@ 27723 label=str_frontend_option_stream_5
t 27723 str_frontend_option_stream_5
D 27723 Front-end option stream #5 for 0xEAE2.
D 27723 Decoded text stream: "5<SYM60>-DEFINE KEYS".
@ 27738 label=str_frontend_option_stream_6
t 27738 str_frontend_option_stream_6
D 27738 Front-end option stream #6 for 0xEAE2.
D 27738 Decoded text stream: "6<SYM60>-START".
@ 27747 label=str_byline_stream
t 27747 str_byline_stream
D 27747 0x6B9D byline stream (compact 8x8 renderer).
D 27747 Decoded text stream: "BY MARCO CARRASCO AND RUI TITO".
@ 27778 label=top_level_pre_game_control_loop
c 27778 top_level_pre_game_control_loop
D 27778 Top-level pre-game control loop: draws front-end/status panel, polls input, and enters gameplay on start command.
D 27778 Snapshot handoff note: AlienEvolution.Z80 resumes at RAM stub PC=0x8EB9 (inside 0x8E94 block), then branches here via JP NZ/Z,0x6C82 after short setup checks.
N 27778 Args: none.
N 27778 Returns: none.
N 27778 def top_level_pre_game_control_loop():
N 27778 ↳fn_title_screen_text_compositor()
N 27778 ↳fn_scenario_preset_b_beeper_stream_engine()
N 27778 ↳while True:
N 27778 ↳↳A_sel = var_menu_selection_index
N 27778 ↳↳HL_row = 0x590A + (A_sel + 0x01) * 0x40
N 27778 ↳↳HL_row[0x00] = 0x06
N 27778 ↳↳HL_row[0x20] = 0x06
N 27778 ↳↳HL_row[0x22:0x33] = [0x06] * 0x11
N 27778 ↳↳fn_front_end_two_step_beeper_cadence()
N 27778 ↳↳A_keys = in_port(0xF7FE)
N 27778 ↳↳if (A_keys & 0x01) == 0x00:
N 27778 ↳↳↳define_keys_apply_routine()
N 27778 ↳↳↳continue
N 27778 ↳↳if (A_keys & 0x02) == 0x00:
N 27778 ↳↳↳control_preset_branch_3()
N 27778 ↳↳↳continue
N 27778 ↳↳if (A_keys & 0x04) == 0x00:
N 27778 ↳↳↳control_preset_branch()
N 27778 ↳↳↳continue
N 27778 ↳↳if (A_keys & 0x08) == 0x00:
N 27778 ↳↳↳control_preset_branch_2()
N 27778 ↳↳↳continue
N 27778 ↳↳if (A_keys & 0x10) == 0x00:
N 27778 ↳↳↳define_keys_setup_flow()
N 27778 ↳↳↳continue
N 27778 ↳↳A_start = in_port(0xEFFE)
N 27778 ↳↳if (A_start & 0x10) == 0x00:
N 27778 ↳↳↳gameplay_session_controller()
N 27778 ↳↳↳return
@ 27864 label=control_icon_drawer
c 27864 control_icon_drawer
D 27864 Control-icon drawer: consume one 32-byte icon set at DE (16-byte left half + 16-byte right half), decode bits to 0/148 attribute writes, and stamp resulting 16x16 icon into attribute area at 0x5908/0x5910.
N 27864 Args: DE_icon is ptr_u8 icon payload (32 bytes = two 16-byte halves).
N 27864 Returns: DE_icon advanced by 32 bytes.
N 27864 def control_icon_drawer(DE_icon):
N 27864 ↳fn_control_icon_row_draw_loop(HL_dst=0x5908, DE_src=DE_icon[0x00:0x10])
N 27864 ↳fn_control_icon_row_draw_loop(HL_dst=0x5910, DE_src=DE_icon[0x10:0x20])
@ 27873 label=fn_control_icon_row_draw_loop
c 27873 fn_control_icon_row_draw_loop
D 27873 Control-icon drawer row-loop entry: processes 16 rows x 8 bits and writes 0/0x94 attribute pixels.
N 27873 Args: HL_dst is ptr_u8 to top-left destination of one 8x16 icon half in attribute RAM; DE_src is ptr_u8 to 16 source row bytes (bit7 is leftmost pixel).
N 27873 Returns: none.
N 27873 def fn_control_icon_row_draw_loop(HL_dst, DE_src):
N 27873 ↳for _ in range(0x10):
N 27873 ↳↳A_bits = DE_src[0x00]
N 27873 ↳↳for _ in range(0x08):
N 27873 ↳↳↳HL_dst[0x00] = 0x94 if (A_bits & 0x80) else 0x00
N 27873 ↳↳↳A_bits = ((A_bits << 1) & 0xFF) | (A_bits >> 7)
N 27873 ↳↳↳HL_dst += 1
N 27873 ↳↳DE_src += 1
N 27873 ↳↳HL_dst += 0x18
@ 27902 label=const_define_keys_descriptor_table
b 27902 const_define_keys_descriptor_table
D 27902 Define-keys descriptor table at 0x6CFE-0x6D0F (6 slots): per-slot keyboard port pair + mask bytes captured in 0x6E48 setup.
D 27902 Slot writes in 0x6E4C flow: (0x6CFE,0x6D06), (0x6D00,0x6D07), (0x6D04,0x6D09), (0x6D02,0x6D08), (0x6D0A,0x6D0C), (0x6D0D,0x6D0F).
D 27902 Structure: six control descriptors encoded as interleaved (port_lo,port_hi,mask) fields across 0x6CFE-0x6D0F; consumed by copier/patcher at 0x6D10.
@ 27904 label=const_define_key_slot_2_port_word
@ 27906 label=const_define_key_slot_4_port_word
@ 27908 label=const_define_key_slot_3_port_word
@ 27910 label=const_define_key_slot_1_mask_byte
@ 27911 label=const_define_key_slot_2_mask_byte
@ 27912 label=const_define_key_slot_4_mask_byte
@ 27913 label=const_define_key_slot_3_mask_byte
@ 27914 label=const_define_key_slot_5_port_word
@ 27916 label=const_define_key_slot_5_mask_byte
@ 27917 label=const_define_key_slot_6_port_word
@ 27919 label=const_define_key_slot_6_mask_byte
@ 27920 label=define_keys_apply_routine
c 27920 define_keys_apply_routine
D 27920 Define-keys apply routine: copy descriptors from 0x6CFE..0x6D0F into runtime key-check tables (self-modified operands), refresh key logic via 0x713F, then clear A and fall through.
N 27920 Args: none.
N 27920 Returns: none.
N 27920 def define_keys_apply_routine():
N 27920 ↳patch_control_scan_slot_1_port_word = read_u16(0x6CFE)
N 27920 ↳patch_control_scan_slot_1_bit_opcode = read_u8(0x6D06)
N 27920 ↳patch_control_scan_slot_2_port_word = read_u16(0x6D00)
N 27920 ↳patch_control_scan_slot_2_bit_opcode = read_u8(0x6D07)
N 27920 ↳patch_control_scan_slot_3_port_word = read_u16(0x6D04)
N 27920 ↳patch_control_scan_slot_3_bit_opcode = read_u8(0x6D09)
N 27920 ↳patch_control_scan_slot_4_port_word = read_u16(0x6D02)
N 27920 ↳patch_control_scan_slot_4_bit_opcode = read_u8(0x6D08)
N 27920 ↳patch_control_scan_slot_5_port_word = read_u16(0x6D0A)
N 27920 ↳patch_control_scan_slot_5_bit_opcode = read_u8(0x6D0C)
N 27920 ↳patch_control_scan_slot_6_port_word = read_u16(0x6D0D)
N 27920 ↳patch_control_scan_slot_6_bit_opcode = read_u8(0x6D0F)
N 27920 ↳patch_control_scan_slot_6_prefix_opcode = 0xCB
N 27920 ↳patch_control_scan_slot_6_branch_opcode = 0xCA
N 27920 ↳fn_input_patch_preset_2()
N 27920 ↳front_end_selection_commit(A_sel=0x00)
@ 28018 label=front_end_selection_commit
c 28018 front_end_selection_commit
D 28018 Front-end selection commit: store menu index at 0xA8E8, clear highlight stripe, redraw markers, and return to poll loop.
N 28018 Args: A_sel is u8 front-end option index (0..5).
N 28018 Returns: none.
N 28018 def front_end_selection_commit(A_sel):
N 28018 ↳var_menu_selection_index = A_sel
N 28018 ↳HL_col = 0x594A
N 28018 ↳for _ in range(0x0C):
N 28018 ↳↳HL_col[0x00] = 0x00
N 28018 ↳↳HL_col += 0x20
N 28018 ↳fn_front_end_selection_bars_redraw()
N 28018 ↳jump(0x6C88)
@ 28040 label=control_preset_branch
c 28040 control_preset_branch
D 28040 Control preset branch (option key #3): patch key-read operands, then commit selection index 2 via 0x6D72.
N 28040 Args: none.
N 28040 Returns: none.
N 28040 def control_preset_branch():
N 28040 ↳for HL_slot in [0xE0D4, 0xE0DE, 0xE0CA, 0xE0C0, 0xE0E8]:
N 28040 ↳↳write_u16(HL_slot, 0x00DF)
N 28040 ↳patch_control_scan_slot_4_bit_opcode = 0x47
N 28040 ↳patch_control_scan_slot_3_bit_opcode = 0x4F
N 28040 ↳patch_control_scan_slot_2_bit_opcode = 0x57
N 28040 ↳patch_control_scan_slot_1_bit_opcode = 0x5F
N 28040 ↳patch_control_scan_slot_5_bit_opcode = 0x67
N 28040 ↳fn_input_patch_preset()
N 28040 ↳front_end_selection_commit(A_sel=0x02)
@ 28096 label=control_preset_branch_2
c 28096 control_preset_branch_2
D 28096 Control preset branch (option key #4): patch key-read operands and joystick opcode tail, then commit selection index 3.
N 28096 Args: none.
N 28096 Returns: none.
N 28096 def control_preset_branch_2():
N 28096 ↳patch_control_scan_slot_3_port_word = 0xF7FE
N 28096 ↳patch_control_scan_slot_3_bit_opcode = 0x67
N 28096 ↳patch_control_scan_slot_5_port_word = 0xEFFE
N 28096 ↳patch_control_scan_slot_4_port_word = 0xEFFE
N 28096 ↳patch_control_scan_slot_2_port_word = 0xEFFE
N 28096 ↳patch_control_scan_slot_1_port_word = 0xEFFE
N 28096 ↳patch_control_scan_slot_5_bit_opcode = 0x47
N 28096 ↳patch_control_scan_slot_2_bit_opcode = 0x67
N 28096 ↳patch_control_scan_slot_1_bit_opcode = 0x5F
N 28096 ↳patch_control_scan_slot_4_bit_opcode = 0x57
N 28096 ↳fn_input_opcode_patch_tail()
N 28096 ↳front_end_selection_commit(A_sel=0x03)
@ 28155 label=control_preset_branch_3
c 28155 control_preset_branch_3
D 28155 Control preset branch (option key #2): patch keyboard/cursor key map, then commit selection index 1.
N 28155 Args: none.
N 28155 Returns: none.
N 28155 def control_preset_branch_3():
N 28155 ↳patch_control_scan_slot_3_port_word = 0xF7FE
N 28155 ↳patch_control_scan_slot_4_port_word = 0xF7FE
N 28155 ↳patch_control_scan_slot_1_port_word = 0xF7FE
N 28155 ↳patch_control_scan_slot_2_port_word = 0xF7FE
N 28155 ↳patch_control_scan_slot_5_port_word = 0xF7FE
N 28155 ↳patch_control_scan_slot_3_bit_opcode = 0x47
N 28155 ↳patch_control_scan_slot_4_bit_opcode = 0x4F
N 28155 ↳patch_control_scan_slot_2_bit_opcode = 0x57
N 28155 ↳patch_control_scan_slot_1_bit_opcode = 0x5F
N 28155 ↳patch_control_scan_slot_5_bit_opcode = 0x67
N 28155 ↳fn_input_opcode_patch_tail()
N 28155 ↳front_end_selection_commit(A_sel=0x01)
@ 28211 label=fn_input_opcode_patch_tail
c 28211 fn_input_opcode_patch_tail
D 28211 Shared input-opcode patch tail: call 0x714F and rewrite key-check opcodes at 0xE144..0xE146.
N 28211 Args: none.
N 28211 Returns: none.
N 28211 def fn_input_opcode_patch_tail():
N 28211 ↳fn_input_patch_preset_2()
N 28211 ↳mem[0xE13E:0xE140] = u16le(0x7FFE)  # slot6 keyboard port word
N 28211 ↳mem[0xE144] = 0xFE
N 28211 ↳mem[0xE145] = 0xFF
N 28211 ↳mem[0xE146] = 0xC2
@ 28236 label=define_keys_setup_flow
c 28236 define_keys_setup_flow
D 28236 Define-keys setup flow: iterates six icon selectors (0x6EB6/0x6EBC/0x6EAA/0x6EB0/0x6EC2/0x6EC8) that feed 32-byte icon sets to drawer 0x6CD8 while collecting key assignments.
N 28236 Args: none.
N 28236 Returns: none.
N 28236 def define_keys_setup_flow():
N 28236 ↳fn_title_top_screen_setup()
N 28236 ↳fn_blink_delay_two_phase_wait()
N 28236 ↳for fn_icon, HL_port, HL_bit in [
N 28236 ↳↳(fn_icon_selector_2, 0x6CFE, 0x6D06),
N 28236 ↳↳(fn_icon_selector_1, 0x6D00, 0x6D07),
N 28236 ↳↳(fn_icon_selector_3, 0x6D04, 0x6D09),
N 28236 ↳↳(fn_icon_selector_4, 0x6D02, 0x6D08),
N 28236 ↳↳(fn_icon_selector_5, 0x6D0A, 0x6D0C),
N 28236 ↳↳(fn_icon_selector_6, 0x6D0D, 0x6D0F),
N 28236 ↳]:
N 28236 ↳↳fn_icon()
N 28236 ↳↳A_bit, BC_port = fn_define_keys_wait_loop()
N 28236 ↳↳write_u16(HL_port, BC_port)
N 28236 ↳↳mem[HL_bit] = A_bit
N 28236 ↳var_menu_selection_index = 0x00
N 28236 ↳fn_title_screen_text_compositor()
N 28236 ↳define_keys_apply_routine()
@ 28330 label=fn_icon_selector_3
c 28330 fn_icon_selector_3
D 28330 Icon selector #3: DE <- 0x6A26, then JP 0x6CD8.
N 28330 Args: none.
N 28330 Returns: DE_icon advanced by 0x20 bytes by control_icon_drawer.
N 28330 def fn_icon_selector_3():
N 28330 ↳control_icon_drawer(DE_icon=const_control_icon_set_3)
@ 28336 label=fn_icon_selector_4
c 28336 fn_icon_selector_4
D 28336 Icon selector #4: DE <- 0x6A46, then JP 0x6CD8.
N 28336 Args: none.
N 28336 Returns: DE_icon advanced by 0x20 bytes by control_icon_drawer.
N 28336 def fn_icon_selector_4():
N 28336 ↳control_icon_drawer(DE_icon=const_control_icon_set_4)
@ 28342 label=fn_icon_selector_1
c 28342 fn_icon_selector_1
D 28342 Icon selector #1: DE <- 0x69E6, then JP 0x6CD8.
N 28342 Args: none.
N 28342 Returns: DE_icon advanced by 0x20 bytes by control_icon_drawer.
N 28342 def fn_icon_selector_1():
N 28342 ↳control_icon_drawer(DE_icon=const_control_icon_set_table)
@ 28348 label=fn_icon_selector_2
c 28348 fn_icon_selector_2
D 28348 Icon selector #2: DE <- 0x6A06, then JP 0x6CD8.
N 28348 Args: none.
N 28348 Returns: DE_icon advanced by 0x20 bytes by control_icon_drawer.
N 28348 def fn_icon_selector_2():
N 28348 ↳control_icon_drawer(DE_icon=const_control_icon_set_2)
@ 28354 label=fn_icon_selector_5
c 28354 fn_icon_selector_5
D 28354 Icon selector #5: DE <- 0x6A66, then JP 0x6CD8.
N 28354 Args: none.
N 28354 Returns: DE_icon advanced by 0x20 bytes by control_icon_drawer.
N 28354 def fn_icon_selector_5():
N 28354 ↳control_icon_drawer(DE_icon=const_control_icon_set_5)
@ 28360 label=fn_icon_selector_6
c 28360 fn_icon_selector_6
D 28360 Icon selector #6: DE <- 0x6A86, then JP 0x6CD8.
N 28360 Args: none.
N 28360 Returns: DE_icon advanced by 0x20 bytes by control_icon_drawer.
N 28360 def fn_icon_selector_6():
N 28360 ↳control_icon_drawer(DE_icon=const_control_icon_set_6)
@ 28366 label=fn_define_keys_wait_loop
c 28366 fn_define_keys_wait_loop
D 28366 Define-keys wait loop: scan input ports/masks until any key line changes, otherwise continue polling.
N 28366 Args: none.
N 28366 Returns: A_glyph is u8 prompt glyph code; BC_port is u16 row-port descriptor where key press was detected.
N 28366 def fn_define_keys_wait_loop():
N 28366 ↳while True:
N 28366 ↳↳for BC_port in [0xFEFE, 0xFDFE, 0xFBFE, 0xF7FE, 0xEFFE, 0xDFFE, 0xBFFE, 0x7FFE]:
N 28366 ↳↳↳A_row = fn_input_probe_primitive(BC_port=BC_port)
N 28366 ↳↳↳if A_row != 0xFF:
N 28366 ↳↳↳↳A_glyph = pressed_key_decoder(A_row=A_row)
N 28366 ↳↳↳↳return A_glyph, BC_port
@ 28441 label=fn_input_probe_primitive
c 28441 fn_input_probe_primitive
D 28441 Input probe primitive: IN A,(C); return Z when no active key after OR 0xE0/CP 0xFF.
N 28441 Args: BC_port is u16 keyboard row port descriptor for IN A,(C).
N 28441 Returns: A_row is u8 normalized row sample; Z flag is set iff A_row == 0xFF (no pressed key on this row).
N 28441 def fn_input_probe_primitive(BC_port):
N 28441 ↳A_row = IN_port_u8(BC_port) | 0xE0
N 28441 ↳return A_row
@ 28448 label=pressed_key_decoder
c 28448 pressed_key_decoder
D 28448 Pressed-key decoder: map first active bit to glyph code and run prompt blink delay helper at 0x6F1F.
N 28448 Args: A_row is u8 normalized keyboard-row sample from fn_input_probe_primitive.
N 28448 Returns: A_glyph is u8 symbol code for key prompt rendering.
N 28448 def pressed_key_decoder(A_row):
N 28448 ↳D_bits = A_row
N 28448 ↳A_glyph = 0x47
N 28448 ↳if D_bits & 0x01:
N 28448 ↳↳while D_bits & 0x01:
N 28448 ↳↳↳D_bits = rr8(D_bits)
N 28448 ↳↳↳A_glyph = (A_glyph + 0x08) & 0xFF
N 28448 ↳fn_blink_delay_two_phase_wait()
N 28448 ↳return A_glyph
@ 28463 label=fn_blink_delay_two_phase_wait
c 28463 fn_blink_delay_two_phase_wait
D 28463 Blink-delay helper entry: runs two timed waits (DE/HL presets) while preserving AF/BC.
N 28463 Args: none (AF and BC are preserved by the helper wrapper).
N 28463 Returns: none.
N 28463 def fn_blink_delay_two_phase_wait():
N 28463 ↳rom_beeper(DE_ticks=0x0050, HL_period=0x01F4)
N 28463 ↳rom_beeper(DE_ticks=0x005A, HL_period=0x02BB)
@ 28486 label=fn_high_score_table_draw_routine
c 28486 fn_high_score_table_draw_routine
D 28486 High-score table draw routine: call 0x6B9D for byline, then print 8x16 text streams from 0x6ABD/0x6AD6/0x6AEF/0x6B08/0x6B21 and header 0x6FAD.
N 28486 Args: none.
N 28486 Returns: none.
N 28486 def fn_high_score_table_draw_routine():
N 28486 ↳fn_title_top_screen_setup()
N 28486 ↳fn_compact_8x8_text_renderer()
N 28486 ↳fn_stretched_text_symbol_stream_printer(HL_stream=str_highscore_row_template_1, B_row=0x0C, C_col=0x04)
N 28486 ↳fn_stretched_text_symbol_stream_printer(HL_stream=str_highscore_row_template_2, B_row=0x0E, C_col=0x04)
N 28486 ↳fn_stretched_text_symbol_stream_printer(HL_stream=str_highscore_row_template_3, B_row=0x10, C_col=0x04)
N 28486 ↳fn_stretched_text_symbol_stream_printer(HL_stream=str_highscore_row_template_4, B_row=0x12, C_col=0x04)
N 28486 ↳fn_stretched_text_symbol_stream_printer(HL_stream=str_highscore_row_template_5, B_row=0x14, C_col=0x04)
N 28486 ↳fn_stretched_text_symbol_stream_printer(HL_stream=str_highscore_header_stream, B_row=0x09, C_col=0x0A)
N 28486 ↳fn_attribute_span_fill_helper(HL_dst=var_display_attribute_ram_anchor_5964, A_fill=0x07)
N 28486 ↳fn_attribute_span_fill_helper(HL_dst=var_display_attribute_ram_anchor_5984, A_fill=0x05)
N 28486 ↳var_display_attribute_ram_anchor_5920[0x00:0x40] = [0x44] * 0x40
N 28486 ↳HL_attr = var_display_attribute_ram_anchor_5984
N 28486 ↳for _ in range(0x0A):
N 28486 ↳↳HL_attr[0x00] = 0x0F
N 28486 ↳↳HL_attr += 0x20
@ 28589 label=str_highscore_header_stream
t 28589 str_highscore_header_stream
D 28589 High-score header stream for 0xEAE2.
D 28589 Decoded text stream: "HALL OF FAME".
@ 28602 label=const_highscore_header_tail_word
b 28602 const_highscore_header_tail_word
D 28602 Non-text trailing word after 0x6FAD header stream (bytes 0x81,0x6C).
D 28602 Structure: 16-bit word; initialized as non-text tail bytes and reused at runtime as compact-text stream pointer scratch by 0x6B9D.
@ 28604 label=high_score_editor_init
c 28604 high_score_editor_init
D 28604 High-score editor init: select one row template, store its pointer at 0x7110, clear editable name field, then reprint prompt+row via 0xEAE2.
N 28604 Args: none.
N 28604 Returns: none.
N 28604 def high_score_editor_init():
N 28604 ↳if fn_score_compare_helper(HL_row=0x6ACF):
N 28604 ↳↳high_score_row_shift_helper_4()
N 28604 ↳↳fn_high_score_row_shift_helper_3()
N 28604 ↳↳fn_high_score_row_shift_helper_2()
N 28604 ↳↳fn_high_score_row_shift_helper_1()
N 28604 ↳↳HL_row = str_highscore_row_template_1
N 28604 ↳elif fn_score_compare_helper(HL_row=0x6AE8):
N 28604 ↳↳high_score_row_shift_helper_4()
N 28604 ↳↳fn_high_score_row_shift_helper_3()
N 28604 ↳↳fn_high_score_row_shift_helper_2()
N 28604 ↳↳HL_row = str_highscore_row_template_2
N 28604 ↳elif fn_score_compare_helper(HL_row=0x6B01):
N 28604 ↳↳high_score_row_shift_helper_4()
N 28604 ↳↳fn_high_score_row_shift_helper_3()
N 28604 ↳↳HL_row = str_highscore_row_template_3
N 28604 ↳elif fn_score_compare_helper(HL_row=0x6B1A):
N 28604 ↳↳high_score_row_shift_helper_4()
N 28604 ↳↳HL_row = str_highscore_row_template_4
N 28604 ↳elif fn_score_compare_helper(HL_row=0x6B33):
N 28604 ↳↳HL_row = str_highscore_row_template_5
N 28604 ↳else:
N 28604 ↳↳return
N 28604 ↳var_highscore_edit_row_ptr = HL_row
N 28604 ↳IX_name = HL_row + 0x0002
N 28604 ↳var_highscore_name_edit_state = 0x00
N 28604 ↳for _ in range(0x0F):
N 28604 ↳↳IX_name[0x00] = 0x0E
N 28604 ↳↳IX_name += 0x0001
N 28604 ↳IX_score = IX_name + 0x0001
N 28604 ↳DE_score = 0xA8C8
N 28604 ↳for _ in range(0x05):
N 28604 ↳↳IX_score[0x00] = (DE_score[0x00] + 0x10) & 0xFF
N 28604 ↳↳IX_score += 0x0001
N 28604 ↳↳DE_score += 0x0001
N 28604 ↳fn_title_top_screen_setup()
N 28604 ↳fn_stretched_text_symbol_stream_printer(HL_stream=str_name_entry_prompt_stream, B_row=0x0A, C_col=0x08)
N 28604 ↳fn_routine_31_byte_row_fill_helper(HL_dst=var_display_attribute_ram_anchor_5940, A_fill=0x45)
N 28604 ↳fn_routine_31_byte_row_fill_helper(HL_dst=var_display_attribute_ram_anchor_5960, A_fill=0x05)
N 28604 ↳fn_routine_31_byte_row_fill_helper(HL_dst=var_display_attribute_ram_anchor_59e0, A_fill=0x05)
N 28604 ↳fn_routine_31_byte_row_fill_helper(HL_dst=var_display_attribute_ram_anchor_5a00, A_fill=0x07)
N 28604 ↳fn_compact_8x8_text_renderer()
N 28604 ↳IX_name = var_highscore_edit_row_ptr + 0x0002 + var_highscore_name_edit_state
N 28604 ↳while True:
N 28604 ↳↳fn_stretched_text_symbol_stream_printer(HL_stream=var_highscore_edit_row_ptr, B_row=0x0F, C_col=0x04)
N 28604 ↳↳A_key = rom_get_key_0x02bf()
N 28604 ↳↳if A_key == 0xFF:
N 28604 ↳↳↳continue
N 28604 ↳↳if A_key == 0x0D:
N 28604 ↳↳↳return
N 28604 ↳↳if A_key == 0x0C:
N 28604 ↳↳↳if var_highscore_name_edit_state != 0x00:
N 28604 ↳↳↳↳var_highscore_name_edit_state -= 0x01
N 28604 ↳↳↳↳IX_name -= 0x0001
N 28604 ↳↳↳↳IX_name[0x00] = 0x0E
N 28604 ↳↳↳rom_beeper(DE_ticks=0x0096, HL_period=0x0190)
N 28604 ↳↳↳continue
N 28604 ↳↳if A_key != 0x20 and A_key < 0x2F:
N 28604 ↳↳↳continue
N 28604 ↳↳IX_name[0x00] = ((A_key & 0x7F) - 0x20) & 0xFF
N 28604 ↳↳IX_name += 0x0001
N 28604 ↳↳var_highscore_name_edit_state += 0x01
N 28604 ↳↳if var_highscore_name_edit_state == 0x0F:
N 28604 ↳↳↳return
N 28604 ↳↳rom_beeper(DE_ticks=0x0096, HL_period=0x0190)
@ 28864 label=fn_routine_31_byte_row_fill_helper
c 28864 fn_routine_31_byte_row_fill_helper
D 28864 31-byte row fill helper: write A at HL and LDIR across one 0x20-wide attribute row segment.
N 28864 Args: HL_dst is ptr_u8 to row-segment start; A_fill is u8 fill value.
N 28864 Returns: none.
N 28864 def fn_routine_31_byte_row_fill_helper(HL_dst, A_fill):
N 28864 ↳HL_dst[0x00:0x1F] = A_fill
@ 28875 label=high_score_row_shift_helper_4
c 28875 high_score_row_shift_helper_4
D 28875 High-score row shift helper #4->#5 (copy 23-byte payload windows after 2-byte row headers).
N 28875 Args: none.
N 28875 Returns: none.
N 28875 def high_score_row_shift_helper_4():
N 28875 ↳HL_src = str_highscore_row_template_4
N 28875 ↳DE_dst = str_highscore_row_template_5
N 28875 ↳DE_dst[0x02:0x19] = HL_src[0x02:0x19]
@ 28891 label=fn_high_score_row_shift_helper_3
c 28891 fn_high_score_row_shift_helper_3
D 28891 High-score row shift helper #3->#4 (source 0x6AEF, destination 0x6B08).
N 28891 Args: none.
N 28891 Returns: none.
N 28891 def fn_high_score_row_shift_helper_3():
N 28891 ↳HL_src = str_highscore_row_template_3
N 28891 ↳DE_dst = str_highscore_row_template_4
N 28891 ↳DE_dst[0x02:0x19] = HL_src[0x02:0x19]
@ 28899 label=fn_high_score_row_shift_helper_2
c 28899 fn_high_score_row_shift_helper_2
D 28899 High-score row shift helper #2->#3 (source 0x6AD6, destination 0x6AEF).
N 28899 Args: none.
N 28899 Returns: none.
N 28899 def fn_high_score_row_shift_helper_2():
N 28899 ↳HL_src = str_highscore_row_template_2
N 28899 ↳DE_dst = str_highscore_row_template_3
N 28899 ↳DE_dst[0x02:0x19] = HL_src[0x02:0x19]
@ 28907 label=fn_high_score_row_shift_helper_1
c 28907 fn_high_score_row_shift_helper_1
D 28907 High-score row shift helper #1->#2 (source 0x6ABD, destination 0x6AD6).
N 28907 Args: none.
N 28907 Returns: none.
N 28907 def fn_high_score_row_shift_helper_1():
N 28907 ↳HL_src = str_highscore_row_template_1
N 28907 ↳DE_dst = str_highscore_row_template_2
N 28907 ↳DE_dst[0x02:0x19] = HL_src[0x02:0x19]
@ 28915 label=fn_score_compare_helper
c 28915 fn_score_compare_helper
D 28915 Score compare helper: compare current 5-digit score (0xA8C8..) against row threshold at HL; returns A=1 on promote.
N 28915 Args: HL_row is ptr_u8 to 5 encoded row-score digits; var_runtime_control_core[0x16:0x1B] (0xA8C8..0xA8CC) stores current score digits.
N 28915 Returns: A_promote is u8 bool (1 when current score outranks row score, else 0); Z flag mirrors (A_promote == 1).
N 28915 def fn_score_compare_helper(HL_row):
N 28915 ↳for i in range(0x05):
N 28915 ↳↳A_cur = var_runtime_control_core[0x16 + i] + 0x10
N 28915 ↳↳A_row = HL_row[i]
N 28915 ↳↳if A_row < A_cur:
N 28915 ↳↳↳return 1
N 28915 ↳↳if A_row > A_cur:
N 28915 ↳↳↳return 0
N 28915 ↳return 0
@ 28944 label=var_highscore_edit_row_ptr
b 28944 var_highscore_edit_row_ptr
D 28944 Pointer to current editable high-score row stream, consumed by LD HL,(0x7110) before CALL 0xEAE2 at 0x7070.
D 28944 Structure: 16-bit little-endian pointer field [ptr_lo, ptr_hi].
@ 28946 label=var_highscore_name_edit_state
b 28946 var_highscore_name_edit_state
D 28946 Name-entry redraw scratch byte adjacent to pointer 0x7110.
D 28946 Structure: 1-byte high-score name-entry scratch/state value.
@ 28947 label=str_name_entry_prompt_stream
t 28947 str_name_entry_prompt_stream
D 28947 Name-entry prompt stream for 0xEAE2.
D 28947 Decoded text stream: "ENTER YOUR NAME".
@ 28963 label=fn_front_end_two_step_beeper_cadence
c 28963 fn_front_end_two_step_beeper_cadence
D 28963 Front-end two-step beeper cadence helper (two ROM 0x03B5 calls used for menu pacing).
N 28963 Args: none.
N 28963 Returns: none.
N 28963 def fn_front_end_two_step_beeper_cadence():
N 28963 ↳rom_beeper(DE_ticks=0x0032, HL_period=0x0032)
N 28963 ↳rom_beeper(DE_ticks=0x0064, HL_period=0x0064)
@ 28981 label=fn_input_patch_preset
c 28981 fn_input_patch_preset
D 28981 Input patch preset (D=0xC4, A=0xC2): apply joystick/keyboard opcode bytes then jump to shared tail 0x6E36.
N 28981 Args: none.
N 28981 Returns: none.
N 28981 def fn_input_patch_preset():
N 28981 ↳fn_input_patch_writer_apply(A_op=0xC2, D_tail=0xC4)
N 28981 ↳fn_input_opcode_patch_tail()
@ 28991 label=fn_input_patch_preset_2
c 28991 fn_input_patch_preset_2
D 28991 Input patch preset (D=0xCC, A=0xCA): patch key-read opcode bytes at 0xE0D0..0xE0F8.
N 28991 Args: none.
N 28991 Returns: none.
N 28991 def fn_input_patch_preset_2():
N 28991 ↳fn_input_patch_writer_apply(A_op=0xCA, D_tail=0xCC)
@ 28995 label=fn_input_patch_writer_apply
c 28995 fn_input_patch_writer_apply
D 28995 Input-patch writer entry: stores opcode bytes to 0xE0C6/0xE0D0/0xE0DA/0xE0E4 and tail byte to 0xE0EE.
N 28995 Args: A_op is u8 opcode byte for four branch sites in key-scan template; D_tail is u8 opcode byte for call-condition site.
N 28995 Returns: none.
N 28995 def fn_input_patch_writer_apply(A_op, D_tail):
N 28995 ↳patch_control_scan_slot_3_branch_opcode = A_op
N 28995 ↳patch_control_scan_slot_4_branch_opcode = A_op
N 28995 ↳patch_control_scan_slot_1_branch_opcode = A_op
N 28995 ↳patch_control_scan_slot_2_branch_opcode = A_op
N 28995 ↳patch_control_scan_slot_5_action_opcode = D_tail
b 29012 const_panel_source_padding_byte
D 29012 Single padding byte between control-patch routine block and panel bitmap at 0x7155.
D 29012 Structure: single padding byte separating code tail and panel bitmap source.
@ 29013 label=const_mission_panel_bitmap_source
b 29013 const_mission_panel_bitmap_source
D 29013 Mission lower-panel source bitmap (0x7155-0x7954, 2048 bytes).
D 29013 #SCR(2,0,0,32,8,29013,31061)(*mission_panel_src_bitmap)#FRAMES(mission_panel_src_bitmap)(mission_lower_source_bitmap|Mission lower-panel source bitmap preview)
D 29013 Structure: mission-panel bitmap as 256 cells x 8 bytes (32x8 cell grid).
@ 31061 label=const_mission_panel_attr_source
b 31061 const_mission_panel_attr_source
D 31061 Mission lower-panel source attributes (0x7955-0x7A54, 256 bytes).
D 31061 Structure: 8x32 attribute matrix for mission-panel source image (row-major, 256 bytes).
@ 31189 label=const_status_string_template_28b
@ 31317 label=const_mission_panel_tile_strip
b 31317 const_mission_panel_tile_strip
D 31317 Mission/status panel tile strip source used by 0xF4C0 blit loop (copied to screen rows B=6..9).
D 31317 Structure: 4x26 cells x 8 bytes/cell bitmap strip (832 bytes, 0x7A55-0x7D94).
@ 32149 label=const_mission_frame_pattern_source
b 32149 const_mission_frame_pattern_source
D 32149 Mission/frame pattern source block consumed by 0xF5B0 (0x7D95-0x7E14, 128 bytes).
D 32149 Consumed by 0xF5B0 (62896): DE starts at 0x7D95; four calls draw 4x(4*8-byte) pattern chunks (total 128 bytes) into gameplay frame/UI positions.
D 32149 Structure: 4 pattern records x 32 bytes (each record emitted via four 8-byte blits in 0xF618 helper path).
@ 32277 label=const_scenario_preset_a_stream_1
b 32277 const_scenario_preset_a_stream_1
D 32277 Scenario preset-A stream #1 source (seeded by 0xF149 into 0xFBCC driver).
D 32277 Structure: preset-A beeper command stream #1 for 0xFBCC engine (music/effect script bytes); 0x40 terminator at 0x7E55.
@ 32342 label=const_scenario_preset_a_stream_2
b 32342 const_scenario_preset_a_stream_2
D 32342 Scenario preset-A stream #2 source (paired with 0xF15B for 0xFBCC driver).
D 32342 Structure: preset-A beeper command stream #2 for 0xFBCC engine (paired music/effect bytes); 0x40 terminator at 0x7E96.
b 32407 const_preset_a_padding_tail
D 32407 Zero/padding tail after preset-A streams up to map base.
D 32407 Structure: zero-filled padding reservoir (0x7E97-0x7FFF) in all current snapshots; no direct static consumers.
@ 32768 label=var_level_map_mode_0
b 32768 var_level_map_mode_0
D 32768 Level map table mode0 (0x8000-0x89C3, 50x50=2500 bytes; low6=runtime cell/state code, high2=render-profile bits).
D 32768 #HTML(<style>.map_hex_rows_wrap{overflow-x:auto;max-width:100%;}.map_hex_rows td{white-space:pre !important;overflow-wrap:normal !important;word-break:normal !important;font-family:monospace;}</style><div class="map_hex_rows_wrap">)#TABLE(map_hex_rows)#FOR0,49,1/^%R%^{ #FOR0,49,1/|%C%|#N(#PEEK(32768+%R%*50+%C%),2,,,1)| |/ }^ ^/TABLE##HTML(</div>)
D 32768 Structure: 50x50 map matrix, 1 byte per cell (low6 runtime code, high2 render-profile bits).
@ 32769 label=var_level_map_mode_0_lidir_tail_8001
b 35268 var_visible_cell_staging_prelude
D 35268 2-byte prelude/padding immediately before visible-cell staging stream base 0x89C6.
D 35268 Structure: 2-byte prelude/padding immediately ahead of visible-cell staging workspace.
@ 35270 label=var_visible_cell_staging_lattice
b 35270 var_visible_cell_staging_lattice
D 35270 Visible-cell staging lattice base: built in 0xA38E from active map (out-of-bounds -> 0), consumed by dispatcher at 0xA41A.
D 35270 0xA38E writes a sparse 37x14 staged-cell lattice from base 0x89C6; write footprint spans up to 0x8E1D (not only the 0x89C6-0x8C0F preset-clear region).
D 35270 Structure: staged-cell workspace with preset clear window 0x89C6-0x8C0F (0xEF83 path) plus sparse runtime writes beyond it.
@ 35271 label=var_visible_cell_staging_clear_tail_89c7
@ 35655 label=var_visible_cell_staging_preset_row_0
@ 35672 label=var_visible_cell_staging_preset_row_1
@ 35688 label=var_visible_cell_staging_preset_row_2
@ 35705 label=var_visible_cell_staging_preset_row_3
@ 35721 label=var_visible_cell_staging_preset_row_4
b 35856 var_visible_cell_staging_mid_window
D 35856 Mid-window of staged-cell lattice inside former unresolved tail (0x8C10-0x8C25).
D 35856 0xA38E lattice writes hit 8 addresses in this 22-byte slice (sparse pattern, not contiguous buffer fill).
D 35856 Structure: sparse continuation of staged-cell lattice inside 0x8C10..0x8C25.
b 35878 var_visible_cell_staging_tail_window
D 35878 Staged-cell lattice continuation plus volatile gaps (0x8C26-0x8D5F).
D 35878 0xA38E lattice writes hit 147 addresses in this window; non-hit bytes are volatile and include stack-residue effects near 0x8D51..0x8D5F.
D 35878 Structure: mixed sparse staging lattice + volatile tail bytes.
b 36192 var_render_work_area_tail
D 36192 Non-text bytes in render/work-data area.
D 36192 The same 0xA38E lattice continues here through 0x8E1D (91 touched addresses in 0x8D60-0x8E1D); upper tail to 0x8F7F is mostly volatile/runtime scratch.
D 36192 Consolidated volatile region up to 0x8F7F; in baseline snapshot 0x00_boot_attract.sna the inherited main SP is 0x8D71 (SNA header), so this area also contains normal-call-stack residue.
D 36192 No fixed mainline stack init (LD SP,nn) is used by gameplay code outside the dedicated render-stack switch at 0xA5BE/0xA653.
D 36192 AlienEvolution.Z80 (v3) stores effective snapshot PC=0x8EB9 in the extended header; this entry is inside RAM stub bytes in 0x8E94..0x8EBF.
D 36192 The RAM stub path performs stack/setup (`LD SP,0x8D77`) and on normal branch conditions hands off to top_level_pre_game_control_loop (0x6C82).
D 36192 Structure: volatile workspace/state region (mixed scratch bytes and inherited stack residue).
@ 36500 label=snapshot_resume_stub_base_8e94
@ 36537 label=snapshot_resume_pc_8eb9
@ 36736 label=var_cell_blit_work_buffer
b 36736 var_cell_blit_work_buffer
D 36736 Pseudo-3D cell-blit destination work buffer base (set at 0xA416): intermediate AND/OR composition target before final viewport strip copy.
D 36736 Structure: linear pseudo-3D composition scratch buffer at 0x8F80-0x90FF (384 bytes), byte-addressed by render blit paths.
@ 37120 label=var_linear_viewport_work_buffer
b 37120 var_linear_viewport_work_buffer
D 37120 Linear viewport buffer base (source for final strip copy to ZX bitmap at 0xA588; rows in linear order).
D 37120 #UDGARRAY26,56,2,26,0(37120-40057-1-208)(*pseudo3d_viewport_linear)#FRAMES(pseudo3d_viewport_linear)(pseudo3d_viewport_linear|Pseudo-3D linear viewport work buffer, 26x15 UDG)
D 37120 Stack-backed render fill window: 0xA5C2 sets SP=0xA000 and performs 15*(128 PUSH HL)=3840-byte burst fill, covering 0x9100-0x9FFF before SP is restored.
D 37120 Structure: linear viewport buffer arranged as 15 rows x 26 bytes (row-major).
@ 40960 label=var_linear_viewport_stack_fill_top_a000
@ 41870 label=fn_main_pseudo_3d_map_render_pipeline
c 41870 fn_main_pseudo_3d_map_render_pipeline
D 41870 Main pseudo-3D map render pipeline: build visible-cell staging stream, dispatch cell draw paths, then blit viewport strips to ZX bitmap.
N 41870 Args: none.
N 41870 Returns: none.
N 41870 def fn_main_pseudo_3d_map_render_pipeline():
N 41870 ↳disable_interrupts()
N 41870 ↳var_renderer_fill_counters = 0x250E
N 41870 ↳HL_map = read_u16(var_runtime_current_cell_ptr_lo)
N 41870 ↳BC_row_col = var_current_map_coords
N 41870 ↳build_visible_cell_staging_lattice(HL_map=HL_map, BC_row_col=BC_row_col, DE_dst=var_visible_cell_staging_lattice)
N 41870 ↳var_renderer_staging_cursor_ptr = var_visible_cell_staging_lattice
N 41870 ↳render_staging_to_cell_buffer(HL_stage=var_visible_cell_staging_lattice, DE_dst=var_cell_blit_work_buffer)
N 41870 ↳viewport_strip_blit_core(HL_src=var_linear_viewport_work_buffer, DE_dst=0x4021, A_passes=0x02)
N 41870 ↳# Dispatch order per staged cell is fixed: 23/87/215/151 -> bit6 -> bit7 -> generic sprite.
@ 42389 label=viewport_strip_blit_core
@ 42440 label=patch_viewport_fill_word_1
@ 42459 label=patch_viewport_fill_word_2
@ 42478 label=patch_viewport_fill_word_3
@ 42497 label=patch_viewport_fill_word_4
@ 42516 label=patch_viewport_fill_word_5
@ 42535 label=patch_viewport_fill_word_6
@ 42554 label=patch_viewport_fill_word_7
@ 42573 label=patch_viewport_fill_word_8
c 42389 viewport_strip_blit_core
D 42389 Viewport strip blit core: copies rendered strips to ZX bitmap window with ZX row-layout stepping.
N 42389 Self-mod patch points inside this code block: 0xA5C8/0xA5DB/0xA5EE/0xA601/0xA614/0xA627/0xA63A/0xA64D are immediate words in LD HL,nn; they are written by 0xA818..0xA849.
N 42389 Args: HL_src is ptr_u8 linear viewport source row (normally var_linear_viewport_work_buffer); DE_dst is ptr_u8 ZX bitmap destination base (normally 0x4021); A_passes is u8 outer pass count (normally 2).
N 42389 Returns: none.
N 42389 def viewport_strip_blit_core(HL_src, DE_dst, A_passes):
N 42389 ↳for _ in range(A_passes):
N 42389 ↳↳copy_26_byte_strips_into_zx_layout(HL_src=HL_src, DE_dst=DE_dst)
N 42389 ↳fill_linear_viewport_stack_window_via_sp_switch()
@ 42601 label=var_render_stack_saved_sp
b 42601 var_render_stack_saved_sp
D 42601 Saved caller SP (2 bytes, 0xA669..0xA66A) for temporary render-stack switch 0xA5BE..0xA653.
D 42601 Structure: 16-bit saved stack pointer word [sp_lo, sp_hi].
@ 42603 label=var_renderer_staging_cursor_ptr
b 42603 var_renderer_staging_cursor_ptr
D 42603 Renderer staging cursor pointer (2 bytes, 0xA66B..0xA66C), updated by draw pass and used as cell-strip source cursor.
D 42603 Structure: 16-bit renderer cursor pointer [ptr_lo, ptr_hi].
@ 42605 label=var_renderer_fill_counters
b 42605 var_renderer_fill_counters
D 42605 Renderer zig-zag/fill counters (2 bytes, 0xA66D..0xA66E) used by strip traversal logic.
D 42605 Structure: two 1-byte renderer counters/flags [counter0, counter1].
@ 42606 label=var_renderer_fill_counter_1
@ 42607 label=fn_frequent_cube_blit_fast_path
c 42607 fn_frequent_cube_blit_fast_path
D 42607 Frequent cube blit fast-path (self-modifying target; patched by routine 0xA88D).
N 42607 Args: DE_dst is ptr_u8 to destination cell area in pseudo-3D work buffer; immediate AND/OR mask bytes inside this routine are runtime-patched by fn_patches_immediate_operands_routine_xa66f_sprite.
N 42607 Returns: none.
N 42607 def fn_frequent_cube_blit_fast_path(DE_dst):
N 42607 ↳HL_dst = DE_dst
N 42607 ↳for mask_step in const_cube_fast_path_patched_mask_program:
N 42607 ↳↳apply_patched_mask_step(HL_dst, mask_step)
N 42607 ↳↳HL_dst -= 0x00E0
N 42607 Note: exact per-step pixel geometry is still being refined; confirmed facts are runtime mask patching and fixed row stride progression.
@ 42842 label=special_code_23_path
c 42842 special_code_23_path
D 42842 Special code 23 path: one fast cube blit via 0xA66F.
N 42842 Args: DE_dst is ptr_u8 current cell write position in var_cell_blit_work_buffer.
N 42842 Returns: none.
N 42842 def special_code_23_path(DE_dst):
N 42842 ↳fn_frequent_cube_blit_fast_path(DE_dst=DE_dst)
N 42842 ↳advance_to_next_cell_in_strip()
@ 42848 label=bit6_path
c 42848 bit6_path
D 42848 bit6 path: optional base sprite (A with bit6 cleared) then one fast cube blit at D-1.
N 42848 Args: A_code is u8 staged cell code with bit6 set; DE_dst is ptr_u8 current cell write position in var_cell_blit_work_buffer.
N 42848 Returns: none.
N 42848 def bit6_path(A_code, DE_dst):
N 42848 ↳if A_code != 0x40:
N 42848 ↳↳fn_generic_sprite_blitter(A_idx=(A_code & 0xBF), DE_dst=DE_dst)
N 42848 ↳DE_dst_hi = high_byte(DE_dst) - 0x01
N 42848 ↳fn_frequent_cube_blit_fast_path(DE_dst=(DE_dst_hi << 0x08) | low_byte(DE_dst))
N 42848 ↳advance_to_next_cell_in_strip()
@ 42867 label=bit7_path
c 42867 bit7_path
D 42867 bit7 path: optional base sprite (A with bit7 cleared) then one fast cube blit at D-2.
N 42867 Args: A_code is u8 staged cell code with bit7 set; DE_dst is ptr_u8 current cell write position in var_cell_blit_work_buffer.
N 42867 Returns: none.
N 42867 def bit7_path(A_code, DE_dst):
N 42867 ↳if A_code != 0x80:
N 42867 ↳↳fn_generic_sprite_blitter(A_idx=(A_code & 0x7F), DE_dst=DE_dst)
N 42867 ↳DE_dst_hi = high_byte(DE_dst) - 0x02
N 42867 ↳fn_frequent_cube_blit_fast_path(DE_dst=(DE_dst_hi << 0x08) | low_byte(DE_dst))
N 42867 ↳advance_to_next_cell_in_strip()
@ 42887 label=special_code_87_path
c 42887 special_code_87_path
D 42887 Special code 87 path: two fast cube blits (levels D and D-1).
N 42887 Args: DE_dst is ptr_u8 current cell write position in var_cell_blit_work_buffer.
N 42887 Returns: none.
N 42887 def special_code_87_path(DE_dst):
N 42887 ↳fn_frequent_cube_blit_fast_path(DE_dst=DE_dst)
N 42887 ↳DE_lvl1 = DE_dst - 0x0100
N 42887 ↳fn_frequent_cube_blit_fast_path(DE_dst=DE_lvl1)
N 42887 ↳advance_to_next_cell_in_strip()
@ 42899 label=special_code_151_path
c 42899 special_code_151_path
D 42899 Special code 151 path: three fast cube blits (levels D, D-1, D-2).
N 42899 Args: DE_dst is ptr_u8 current cell write position in var_cell_blit_work_buffer.
N 42899 Returns: none.
N 42899 def special_code_151_path(DE_dst):
N 42899 ↳fn_frequent_cube_blit_fast_path(DE_dst=DE_dst)
N 42899 ↳DE_lvl1 = DE_dst - 0x0100
N 42899 ↳fn_frequent_cube_blit_fast_path(DE_dst=DE_lvl1)
N 42899 ↳DE_lvl2 = DE_dst - 0x0200
N 42899 ↳fn_frequent_cube_blit_fast_path(DE_dst=DE_lvl2)
N 42899 ↳advance_to_next_cell_in_strip()
@ 42917 label=special_code_215_path
c 42917 special_code_215_path
D 42917 Special code 215 path: explicit sprite pair (codes 21 and 22) on two levels.
N 42917 Args: DE_dst is ptr_u8 current cell write position in var_cell_blit_work_buffer.
N 42917 Returns: none.
N 42917 def special_code_215_path(DE_dst):
N 42917 ↳fn_generic_sprite_blitter(A_idx=0x15, DE_dst=DE_dst)
N 42917 ↳DE_lvl1 = DE_dst - 0x0100
N 42917 ↳fn_generic_sprite_blitter(A_idx=0x16, DE_dst=DE_lvl1)
N 42917 ↳advance_to_next_cell_in_strip()
@ 42933 label=fn_generic_sprite_blitter
c 42933 fn_generic_sprite_blitter
D 42933 Generic 16x16 masked sprite blitter from 64-byte sprite-table entries.
N 42933 Args: A_idx is u8 sprite index into 64-byte entries at var_runtime_control_core (0xA8B2 base); DE_dst is ptr_u8 destination anchor in ZX bitmap layout.
N 42933 Returns: none.
N 42933 def fn_generic_sprite_blitter(A_idx, DE_dst):
N 42933 ↳HL_src = var_runtime_control_core + (A_idx << 0x06)
N 42933 ↳for _ in range(0x08):
N 42933 ↳↳for off in [0x0000, 0x0001, 0x0101, 0x0100]:
N 42933 ↳↳↳DE_dst[off] = (DE_dst[off] & HL_src[0x00]) | HL_src[0x01]
N 42933 ↳↳↳HL_src += 0x02
N 42933 ↳↳DE_dst += 0x20
@ 43006 label=fn_floor_texture_selector_pattern_setup_active
c 43006 fn_floor_texture_selector_pattern_setup_active
D 43006 Floor texture selector/pattern setup by active map mode byte at 0xA8DB.
N 43006 Args: none.
N 43006 Returns: none.
N 43006 def fn_floor_texture_selector_pattern_setup_active():
N 43006 ↳if var_active_map_mode == 0x00:
N 43006 ↳↳HL_tbl = const_floor_pattern_mode_0_table
N 43006 ↳elif var_active_map_mode == 0x01:
N 43006 ↳↳HL_tbl = const_floor_pattern_mode_1_table
N 43006 ↳else:
N 43006 ↳↳HL_tbl = const_floor_pattern_mode_2_table
N 43006 ↳BC_lane = u16le(HL_tbl[0x00], HL_tbl[0x01])  # C low byte, B high byte
N 43006 ↳patch_viewport_fill_word_1 = BC_lane
N 43006 ↳HL_tbl, B_lane, C_lane = fn_helper_xa7fe(HL_tbl=HL_tbl)
N 43006 ↳patch_viewport_fill_word_2 = (B_lane << 0x08) | C_lane
N 43006 ↳HL_tbl, B_lane, C_lane = fn_helper_xa7fe(HL_tbl=HL_tbl)
N 43006 ↳patch_viewport_fill_word_3 = (B_lane << 0x08) | C_lane
N 43006 ↳HL_tbl, B_lane, C_lane = fn_helper_xa7fe(HL_tbl=HL_tbl)
N 43006 ↳patch_viewport_fill_word_4 = (B_lane << 0x08) | C_lane
N 43006 ↳HL_tbl, B_lane, C_lane = fn_helper_xa7fe(HL_tbl=HL_tbl)
N 43006 ↳patch_viewport_fill_word_5 = (B_lane << 0x08) | C_lane
N 43006 ↳HL_tbl, B_lane, C_lane = fn_helper_xa7fe(HL_tbl=HL_tbl)
N 43006 ↳patch_viewport_fill_word_6 = (B_lane << 0x08) | C_lane
N 43006 ↳HL_tbl, B_lane, C_lane = fn_helper_xa7fe(HL_tbl=HL_tbl)
N 43006 ↳patch_viewport_fill_word_7 = (B_lane << 0x08) | C_lane
N 43006 ↳HL_tbl, B_lane, C_lane = fn_helper_xa7fe(HL_tbl=HL_tbl)
N 43006 ↳patch_viewport_fill_word_8 = (B_lane << 0x08) | C_lane
N 43006 ↳fn_patches_immediate_operands_routine_xa66f_sprite()
N 43006 ↳disable_interrupts()
N 43006 ↳jump(0xA5BE)
@ 43092 label=fn_helper_xa7fe
c 43092 fn_helper_xa7fe
D 43092 Helper for 0xA7FE: advance floor-pattern pointer HL and load next pattern word into BC (C low byte, B high).
N 43092 Args: HL_tbl is ptr_u8 floor-pattern cursor positioned on the current B-byte in a lane table.
N 43092 Returns: HL_tbl advanced by 2 bytes; BC_lane is the next lane word (C low byte, B high byte).
N 43092 def fn_helper_xa7fe(HL_tbl):
N 43092 ↳HL_tbl += 0x01
N 43092 ↳C_lane = HL_tbl[0x00]
N 43092 ↳HL_tbl += 0x01
N 43092 ↳B_lane = HL_tbl[0x00]
N 43092 ↳return HL_tbl, B_lane, C_lane
@ 43097 label=const_floor_pattern_mode_1_table
b 43097 const_floor_pattern_mode_1_table
D 43097 Floor-pattern table for mode1 selector (0xA859).
D 43097 #UDGARRAY2,56,4,2,0(43097-43098)(*floor_pattern_mode1_lanes)#FRAMES(floor_pattern_mode1_lanes)(floor_pattern_mode1_lanes|Floor-pattern mode1: BC-word byte lanes (C then B), 8 rows)
D 43097 Structure: 16-byte floor pattern lane table (8 records x 2 bytes -> C then B).
@ 43113 label=const_floor_pattern_mode_0_table
b 43113 const_floor_pattern_mode_0_table
D 43113 Floor-pattern table for mode0 selector (0xA869).
D 43113 #UDGARRAY2,56,4,2,0(43113-43114)(*floor_pattern_mode0_lanes)#FRAMES(floor_pattern_mode0_lanes)(floor_pattern_mode0_lanes|Floor-pattern mode0: BC-word byte lanes (C then B), 8 rows)
D 43113 Structure: 16-byte floor pattern lane table (8 records x 2 bytes -> C then B).
@ 43129 label=const_floor_pattern_mode_2_table
b 43129 const_floor_pattern_mode_2_table
D 43129 Floor-pattern table for mode2 selector (0xA879).
D 43129 #UDGARRAY2,56,4,2,0(43129-43130)(*floor_pattern_mode2_lanes)#FRAMES(floor_pattern_mode2_lanes)(floor_pattern_mode2_lanes|Floor-pattern mode2: BC-word byte lanes (C then B), 8 rows)
D 43129 Structure: 16-byte floor pattern lane table (8 records x 2 bytes -> C then B).
@ 43145 label=fn_render_pass_re_entry_stub
c 43145 fn_render_pass_re_entry_stub
D 43145 Render-pass re-entry stub: DI and JP 0xA40B (draw pass over staged visible-cell buffer).
N 43145 Args: none.
N 43145 Returns: none.
N 43145 def fn_render_pass_re_entry_stub():
N 43145 ↳disable_interrupts()
N 43145 ↳jump(0xA40B)
@ 43149 label=fn_patches_immediate_operands_routine_xa66f_sprite
c 43149 fn_patches_immediate_operands_routine_xa66f_sprite
D 43149 Patches immediate operands in routine 0xA66F from sprite-table data bytes.
N 43149 Args: none.
N 43149 Returns: none.
N 43149 def fn_patches_immediate_operands_routine_xa66f_sprite():
N 43149 ↳DE_src = var_active_sprite_patch_source_ae72
N 43149 ↳HL_scan = fn_frequent_cube_blit_fast_path
N 43149 ↳for _ in range(0x20):
N 43149 ↳↳while not (HL_scan[0x00] == 0xE6 and HL_scan[0x02] == 0xF6):
N 43149 ↳↳↳HL_scan += 0x01
N 43149 ↳↳HL_scan[0x01] = DE_src[0x00]
N 43149 ↳↳HL_scan[0x03] = DE_src[0x01]
N 43149 ↳↳DE_src += 0x02
N 43149 ↳↳HL_scan += 0x03
b 43184 var_runtime_control_prelude
D 43184 Runtime-control prelude bytes at 0xA8B0..0xA8B1.
D 43184 Structure: 2-byte runtime prelude directly before core state struct at 0xA8B2.
@ 43186 label=var_runtime_control_core
b 43186 var_runtime_control_core
D 43186 Runtime control/state core at 0xA8B2..0xA8DA; this area is also the code-0 window at sprite-table base 0xA8B2 used by generic blitter addressing.
D 43186 Key runtime fields: queue heads 0xA8B6/0xA8B8/0xA8BA/0xA8BC/0xA8BE; phase byte 0xA8C0; current cell pointer 0xA8C1; move-state 0xA8C3; counters 0xA8C4/0xA8C5; move delta 0xA8C6; frame timer pair 0xA8CD/0xA8CE; directional pointers 0xA8CF..0xA8D6; mask 0xA8D7; progress bytes 0xA8D8..0xA8DA.
D 43186 Structure: packed runtime state struct at 0xA8B2..0xA8DA (pointers, counters, masks, mode bytes).
@ 43190 label=var_runtime_queue_head_0_lo
@ 43191 label=var_runtime_queue_head_0_hi
@ 43192 label=var_runtime_queue_head_1_ptr
@ 43194 label=var_runtime_queue_head_2_ptr
@ 43196 label=var_runtime_queue_head_3_ptr
@ 43198 label=var_runtime_queue_head_4_ptr
@ 43200 label=var_runtime_phase_index
@ 43201 label=var_runtime_current_cell_ptr_lo
@ 43202 label=var_runtime_current_cell_ptr_hi
@ 43203 label=var_runtime_move_state_code
@ 43204 label=var_runtime_progress_counter
@ 43205 label=var_runtime_objective_counter
@ 43206 label=var_runtime_move_delta
@ 43208 label=var_runtime_aux_c8_lo
@ 43209 label=var_runtime_aux_c8_hi
@ 43210 label=var_runtime_aux_ca
@ 43211 label=var_runtime_aux_cb
@ 43212 label=var_runtime_aux_cc
@ 43213 label=var_runtime_scheduler_timer_lo
@ 43214 label=var_runtime_scheduler_timer_hi
@ 43215 label=var_runtime_dir_ptr_up
@ 43217 label=var_runtime_dir_ptr_down
@ 43219 label=var_runtime_dir_ptr_right
@ 43221 label=var_runtime_dir_ptr_left
@ 43223 label=var_runtime_direction_mask
@ 43224 label=var_runtime_progress_byte_0
@ 43225 label=var_runtime_progress_byte_1
@ 43226 label=var_runtime_progress_byte_2
@ 43227 label=var_active_map_mode
b 43227 var_active_map_mode
D 43227 Active map mode selector byte (0xA8DB): 0->mode0, 1->mode1, 2+->mode2.
D 43227 Structure: enum byte map_mode where 0=mode0, 1=mode1, 2=mode2+.
@ 43228 label=var_action_effect_flags
b 43228 var_action_effect_flags
D 43228 Action/effect flags byte (0xA8DC) consumed by dispatcher 0xE3E9.
D 43228 Structure: 1-byte runtime bitfield with action/effect flags.
@ 43229 label=var_strip_fill_value
b 43229 var_strip_fill_value
D 43229 Strip-fill byte (0xA8DD) used by fill helper 0xEDBA.
D 43229 Structure: 1-byte fill value for strip/area fill helpers.
@ 43230 label=var_current_map_coords
b 43230 var_current_map_coords
D 43230 Current map coordinates mirror (0xA8DE..0xA8DF).
D 43230 Structure: 2-byte [row_B, col_C] pair (BC-ordered coordinate cache).
@ 43231 label=var_current_map_col
@ 43232 label=var_marker_event_ptr
b 43232 var_marker_event_ptr
D 43232 Marker/event pointer slot (0xA8E0..0xA8E1).
D 43232 Structure: 16-bit little-endian pointer used by marker/event paths.
@ 43234 label=var_marker_index_state
b 43234 var_marker_index_state
D 43234 Marker index/state byte (0xA8E2).
D 43234 Structure: 1-byte marker index/state value.
@ 43235 label=var_marker_counters
b 43235 var_marker_counters
D 43235 Marker counters array (0xA8E3..0xA8E7).
D 43235 Structure: 5-byte counter array for marker/objective progress.
@ 43236 label=var_marker_counter_1
@ 43237 label=var_marker_counter_2
@ 43238 label=var_marker_counter_3
@ 43239 label=var_marker_counter_4
@ 43240 label=var_menu_selection_index
b 43240 var_menu_selection_index
D 43240 Menu selection index byte (0xA8E8, range 0..5).
D 43240 Structure: 1-byte enum for front-end control/icon selection.
b 43241 var_runtime_reserve_tail
D 43241 Unreferenced runtime reserve tail (0xA8E9..0xA8F1).
D 43241 No direct static references to 0xA8E9..0xA8F1 found in current code paths; bytes are zero in all captured gameplay snapshots.
D 43241 Structure: 9-byte reserved/unassigned runtime tail adjacent to control block.
@ 43250 label=var_active_sprite_subset_bank
b 43250 var_active_sprite_subset_bank
D 43250 Mode-swapped sprite subset, active bank (0xA8F2-0xAF71, codes 1..26).
D 43250 #HTML(<style>.sprite16_pairs td{white-space:nowrap;vertical-align:middle;}.sprite16_pairs img{image-rendering:pixelated;}</style>)#TABLE(sprite16_pairs){ =h Code | =h AND 16x16 | =h OR 16x16 }#FOR1,26,1/^%I%^{ #N(%I%,2) | #UDGARRAY2,56,4,8,0((43250+(%I%-1)*64)-(43250+(%I%-1)*64);(43250+(%I%-1)*64+2)-(43250+(%I%-1)*64+2);(43250+(%I%-1)*64+6)-(43250+(%I%-1)*64+6);(43250+(%I%-1)*64+4)-(43250+(%I%-1)*64+4))(sprite_active_and_%I%|code %I% AND, layout [1 2;4 3]) | #UDGARRAY2,56,4,8,0((43250+(%I%-1)*64+1)-(43250+(%I%-1)*64+1);(43250+(%I%-1)*64+3)-(43250+(%I%-1)*64+3);(43250+(%I%-1)*64+7)-(43250+(%I%-1)*64+7);(43250+(%I%-1)*64+5)-(43250+(%I%-1)*64+5))(sprite_active_or_%I%|code %I% OR, layout [1 2;4 3]) }^ ^/TABLE#
D 43250 Structure: sprite bank of 26 records x 64 bytes; each record stores paired AND/OR 16x16 data.
@ 44658 label=var_active_sprite_patch_source_ae72
b 44914 const_sprite_table_continuation
D 44914 Sprite-table continuation for codes 27..57 plus first two bytes of code 58 (0xAF72-0xB733).
D 44914 Mapping from base 0xA8B2 with 64-byte records: this region is the unswapped continuation after code 26.
D 44914 Structure: sprite records compatible with 16x16 AND/OR format for codes 27..57, then head bytes of code 58.
@ 46900 label=var_saved_map_triplet_buffer
b 46900 var_saved_map_triplet_buffer
D 46900 Saved-map-object triplet list buffer at 0xB734 (overlays sprite records 58..63 area at runtime).
D 46900 Produced by 0xF2BB and consumed by 0xF25F: repeating triplets [full_cell_byte, ptr_lo, ptr_hi], scan terminates on 0xFF sentinel.
D 46900 Structure: variable-length triplet list workspace in 0xB734.. (runtime-mutated; overlaps would-be sprite-table tail).
b 47280 var_runtime_sprite_tail
D 47280 Runtime tail bytes before bank-A sprite subset.
D 47280 Structure: 2-byte tail/padding slice at 0xB8B0-0xB8B1 preceding bank-A block at 0xB8B2.
@ 47282 label=const_sprite_subset_bank_a
b 47282 const_sprite_subset_bank_a
D 47282 Mode-swapped sprite subset bank A (0xB8B2-0xBF31, codes 1..26).
D 47282 #HTML(<style>.sprite16_pairs td{white-space:nowrap;vertical-align:middle;}.sprite16_pairs img{image-rendering:pixelated;}</style>)#TABLE(sprite16_pairs){ =h Code | =h AND 16x16 | =h OR 16x16 }#FOR1,26,1/^%I%^{ #N(%I%,2) | #UDGARRAY2,56,4,8,0((47282+(%I%-1)*64)-(47282+(%I%-1)*64);(47282+(%I%-1)*64+2)-(47282+(%I%-1)*64+2);(47282+(%I%-1)*64+6)-(47282+(%I%-1)*64+6);(47282+(%I%-1)*64+4)-(47282+(%I%-1)*64+4))(sprite_bank_a_and_%I%|code %I% AND, layout [1 2;4 3]) | #UDGARRAY2,56,4,8,0((47282+(%I%-1)*64+1)-(47282+(%I%-1)*64+1);(47282+(%I%-1)*64+3)-(47282+(%I%-1)*64+3);(47282+(%I%-1)*64+7)-(47282+(%I%-1)*64+7);(47282+(%I%-1)*64+5)-(47282+(%I%-1)*64+5))(sprite_bank_a_or_%I%|code %I% OR, layout [1 2;4 3]) }^ ^/TABLE#
D 47282 Structure: sprite bank of 26 records x 64 bytes; each record stores paired AND/OR 16x16 data.
@ 48946 label=const_sprite_subset_bank_b
b 48946 const_sprite_subset_bank_b
D 48946 Mode-swapped sprite subset bank B (0xBF32-0xC5B1, codes 1..26).
D 48946 #HTML(<style>.sprite16_pairs td{white-space:nowrap;vertical-align:middle;}.sprite16_pairs img{image-rendering:pixelated;}</style>)#TABLE(sprite16_pairs){ =h Code | =h AND 16x16 | =h OR 16x16 }#FOR1,26,1/^%I%^{ #N(%I%,2) | #UDGARRAY2,56,4,8,0((48946+(%I%-1)*64)-(48946+(%I%-1)*64);(48946+(%I%-1)*64+2)-(48946+(%I%-1)*64+2);(48946+(%I%-1)*64+6)-(48946+(%I%-1)*64+6);(48946+(%I%-1)*64+4)-(48946+(%I%-1)*64+4))(sprite_bank_b_and_%I%|code %I% AND, layout [1 2;4 3]) | #UDGARRAY2,56,4,8,0((48946+(%I%-1)*64+1)-(48946+(%I%-1)*64+1);(48946+(%I%-1)*64+3)-(48946+(%I%-1)*64+3);(48946+(%I%-1)*64+7)-(48946+(%I%-1)*64+7);(48946+(%I%-1)*64+5)-(48946+(%I%-1)*64+5))(sprite_bank_b_or_%I%|code %I% OR, layout [1 2;4 3]) }^ ^/TABLE#
D 48946 Structure: sprite bank of 26 records x 64 bytes; each record stores paired AND/OR 16x16 data.
@ 50610 label=var_runtime_object_queue_0
b 50610 var_runtime_object_queue_0
D 50610 Runtime object queue #0 (0xC5B2-0xC72D, 380 bytes).
D 50610 Queue format for 0xC5B2/0xC72E/0xC8AA/0xCA26/0xCBA2 heads: repeating triplets [state_or_code, ptr_lo, ptr_hi], 0xFF terminator.
D 50610 Seeded from first map cell with code 25 in 0xF2F4 setup; callback 0xEA0C (59916) flips low bits (25<->26 visual phase).
D 50610 Structure: queue storage of repeating 3-byte entries [state_or_code, ptr_lo, ptr_hi] with 0xFF terminator in unused slots.
@ 50611 label=var_runtime_object_queue_0_entries
@ 50990 label=var_runtime_object_queue_1
b 50990 var_runtime_object_queue_1
D 50990 Runtime object queue #1 (0xC72E-0xC8A9, 380 bytes).
D 50990 Seeded from first map cell with code 17; processed by directional callback 0xE704 (59140), using map codes 17..20.
D 50990 Structure: queue of repeating triplets [state_or_code, ptr_lo, ptr_hi] with 0xFF terminator semantics (same layout as queue #0 at 0xC5B2).
@ 50991 label=var_runtime_object_queue_1_entries
@ 51370 label=var_runtime_object_queue_2
b 51370 var_runtime_object_queue_2
D 51370 Runtime object queue #2 (0xC8AA-0xCA25, 380 bytes).
D 51370 Seeded from first map cell with code 13; processed by directional callback 0xE76F (59247), using map codes 13..16.
D 51370 Structure: queue of repeating triplets [state_or_code, ptr_lo, ptr_hi] with 0xFF terminator semantics (same layout as queue #0 at 0xC5B2).
@ 51371 label=var_runtime_object_queue_2_entries
@ 51750 label=var_runtime_object_queue_3
b 51750 var_runtime_object_queue_3
D 51750 Runtime object queue #3 (0xCA26-0xCBA1, 380 bytes).
D 51750 Seeded from first map cell with code 1; processed by animated/chase callback 0xE848 (59464), using map codes 1..12.
D 51750 Structure: queue of repeating triplets [state_or_code, ptr_lo, ptr_hi] with 0xFF terminator semantics (same layout as queue #0 at 0xC5B2).
@ 51751 label=var_runtime_object_queue_3_entries
@ 52130 label=var_runtime_object_queue_4
b 52130 var_runtime_object_queue_4
D 52130 Runtime object queue #4 (0xCBA2-0xCD1D, 380 bytes).
D 52130 Staging queue for expansion pass 0xEC0A (60426); rotated into active heads by 0xECCA (60602).
D 52130 Structure: queue of repeating triplets [state_or_code, ptr_lo, ptr_hi] with 0xFF terminator semantics (staging queue variant).
@ 52510 label=var_level_map_mode_1
b 52510 var_level_map_mode_1
D 52510 Level map table mode1 (0xCD1E-0xD6E1, 50x50=2500 bytes; low6=runtime cell/state code, high2=render-profile bits).
D 52510 #HTML(<style>.map_hex_rows_wrap{overflow-x:auto;max-width:100%;}.map_hex_rows td{white-space:pre !important;overflow-wrap:normal !important;word-break:normal !important;font-family:monospace;}</style><div class="map_hex_rows_wrap">)#TABLE(map_hex_rows)#FOR0,49,1/^%R%^{ #FOR0,49,1/|%C%|#N(#PEEK(52510+%R%*50+%C%),2,,,1)| |/ }^ ^/TABLE##HTML(</div>)
D 52510 Structure: 50x50 map matrix, 1 byte per cell (low6 runtime code, high2 render-profile bits).
@ 55010 label=var_level_map_mode_2
b 55010 var_level_map_mode_2
D 55010 Level map table mode2 (0xD6E2-0xE0A5, 50x50=2500 bytes; low6=runtime cell/state code, high2=render-profile bits).
D 55010 #HTML(<style>.map_hex_rows_wrap{overflow-x:auto;max-width:100%;}.map_hex_rows td{white-space:pre !important;overflow-wrap:normal !important;word-break:normal !important;font-family:monospace;}</style><div class="map_hex_rows_wrap">)#TABLE(map_hex_rows)#FOR0,49,1/^%R%^{ #FOR0,49,1/|%C%|#N(#PEEK(55010+%R%*50+%C%),2,,,1)| |/ }^ ^/TABLE##HTML(</div>)
D 55010 Structure: 50x50 map matrix, 1 byte per cell (low6 runtime code, high2 render-profile bits).
@ 57510 label=fn_gameplay_movement_control_step
@ 57536 label=patch_control_scan_slot_4_port_word
@ 57541 label=patch_control_scan_slot_4_bit_opcode
@ 57542 label=patch_control_scan_slot_4_branch_opcode
@ 57546 label=patch_control_scan_slot_3_port_word
@ 57551 label=patch_control_scan_slot_3_bit_opcode
@ 57552 label=patch_control_scan_slot_3_branch_opcode
@ 57556 label=patch_control_scan_slot_1_port_word
@ 57561 label=patch_control_scan_slot_1_bit_opcode
@ 57562 label=patch_control_scan_slot_1_branch_opcode
@ 57566 label=patch_control_scan_slot_2_port_word
@ 57571 label=patch_control_scan_slot_2_bit_opcode
@ 57572 label=patch_control_scan_slot_2_branch_opcode
@ 57576 label=patch_control_scan_slot_5_port_word
@ 57581 label=patch_control_scan_slot_5_bit_opcode
@ 57582 label=patch_control_scan_slot_5_action_opcode
@ 57662 label=patch_control_scan_slot_6_port_word
@ 57668 label=patch_control_scan_slot_6_prefix_opcode
@ 57669 label=patch_control_scan_slot_6_bit_opcode
@ 57670 label=patch_control_scan_slot_6_branch_opcode
c 57510 fn_gameplay_movement_control_step
D 57510 Gameplay movement/control step: poll directional/action keys, update current map cell state, and route to move handlers.
N 57510 Key-scan template bytes at 0xE0C0..0xE146 are code operands/opcodes patched by define-keys/control-preset routines (0x6D10, 0x6D88, 0x6DC0, 0x6DFB, 0x6E33, 0x7143), not separate data.
N 57510 Args: none.
N 57510 Returns: none.
N 57510 def fn_gameplay_movement_control_step():
N 57510 ↳if var_runtime_move_state_code != 0x1C:
N 57510 ↳↳move_commit_branch_special_cell_codes()
N 57510 ↳↳return
N 57510 ↳HL_cell = var_runtime_current_cell_ptr_lo
N 57510 ↳A_cell = HL_cell[0x00] & 0x3F
N 57510 ↳if A_cell == 0x38 or (0x01 <= A_cell <= 0x14):
N 57510 ↳↳state_29_handler()
N 57510 ↳↳return
N 57510 ↳if scan_control_slot_4_pressed():
N 57510 ↳↳movement_attempt_map_offset_1_enters()
N 57510 ↳↳return
N 57510 ↳if scan_control_slot_3_pressed():
N 57510 ↳↳movement_attempt_map_offset_1_enters_2()
N 57510 ↳↳return
N 57510 ↳if scan_control_slot_1_pressed():
N 57510 ↳↳movement_attempt_map_offset_50_move()
N 57510 ↳↳return
N 57510 ↳if scan_control_slot_2_pressed():
N 57510 ↳↳movement_attempt_map_offset_50_enters()
N 57510 ↳↳return
N 57510 ↳if scan_control_slot_5_pressed():
N 57510 ↳↳action_effect_dispatcher_keyed_xa8dc_bits()
N 57510 ↳A_delta = var_runtime_move_delta
N 57510 ↳if A_delta != var_movement_hud_shared_state:
N 57510 ↳↳mem[0x5A7C:0x5A80] = [0x00] * 0x04
N 57510 ↳↳mem[0x5A9C:0x5AA0] = [0x00] * 0x04
N 57510 ↳↳if A_delta == 0x01:
N 57510 ↳↳↳HL_mark = 0x5A9E
N 57510 ↳↳elif A_delta == 0xFF:
N 57510 ↳↳↳HL_mark = 0x5A7C
N 57510 ↳↳elif A_delta == 0xCE:
N 57510 ↳↳↳HL_mark = 0x5A7E
N 57510 ↳↳else:
N 57510 ↳↳↳HL_mark = 0x5A9C
N 57510 ↳↳HL_mark[0x00] = 0x06
N 57510 ↳↳HL_mark[0x01] = 0x06
N 57510 ↳↳var_movement_hud_shared_state = A_delta
N 57510 ↳if scan_control_slot_6_pressed():
N 57510 ↳↳A_flags = var_action_effect_flags
N 57510 ↳↳if A_flags & 0x10:
N 57510 ↳↳↳HL_dst, HL_src = 0x591C, 0x599C
N 57510 ↳↳elif A_flags & 0x01:
N 57510 ↳↳↳HL_dst, HL_src = 0x581C, 0x589C
N 57510 ↳↳elif A_flags & 0x04:
N 57510 ↳↳↳HL_dst, HL_src = 0x589C, 0x591C
N 57510 ↳↳else:
N 57510 ↳↳↳HL_dst, HL_src = 0x599C, 0x581C
N 57510 ↳↳paint_4x4_attr_marker(HL_dst=HL_dst, A_fill=0x20)
N 57510 ↳↳paint_4x4_attr_marker(HL_dst=HL_src, A_fill=0x38)
N 57510 ↳↳var_action_effect_flags = rol8(rol8(var_action_effect_flags))
N 57510 ↳fn_gameplay_movement_step_core()
@ 57798 label=fn_gameplay_movement_step_core
c 57798 fn_gameplay_movement_step_core
D 57798 Gameplay movement/control core entry (0xE1C6): executes the main movement step branch used by directional handlers.
N 57798 Args: none.
N 57798 Returns: none.
N 57798 def fn_gameplay_movement_step_core():
N 57798 ↳A_now = var_runtime_progress_counter
N 57798 ↳A_now = fn_hud_bar_updater(HL_bar=0x5AC5, A_new=A_now, C_old=var_hud_prev_cache_pair_0, B_fill=0x0F)
N 57798 ↳var_hud_prev_cache_pair_0 = A_now
N 57798 ↳A_flags = var_action_effect_flags
N 57798 ↳if A_flags & 0x40:
N 57798 ↳↳A_now = fn_hud_bar_updater(HL_bar=0x5AF5, A_new=var_transient_queue_c, C_old=var_hud_prev_cache_pair_1_hi, B_fill=0x07)
N 57798 ↳↳var_hud_prev_cache_pair_1_hi = A_now
N 57798 ↳↳return
N 57798 ↳if A_flags & 0x10:
N 57798 ↳↳A_now = fn_hud_bar_updater(HL_bar=0x5AD5, A_new=var_transient_queue_b, C_old=var_hud_prev_cache_pair_0_hi, B_fill=0x06)
N 57798 ↳↳var_hud_prev_cache_pair_0_hi = A_now
N 57798 ↳↳return
N 57798 ↳if A_flags & 0x04:
N 57798 ↳↳A_now = fn_hud_bar_updater(HL_bar=0x5AE5, A_new=var_transient_queue_a, C_old=var_hud_prev_cache_pair_1, B_fill=0x05)
N 57798 ↳↳var_hud_prev_cache_pair_1 = A_now
@ 57892 label=fn_hud_bar_updater
c 57892 fn_hud_bar_updater
D 57892 HUD bar updater: adjust one vertical meter row at HL using current value A and previous value C.
N 57892 Args: HL_bar is ptr_u8 meter-row base; A_new is u8 new value; C_old is u8 previous value; B_fill is u8 marker byte.
N 57892 Returns: none.
N 57892 def fn_hud_bar_updater(HL_bar, A_new, C_old, B_fill):
N 57892 ↳if A_new == C_old:
N 57892 ↳↳return
N 57892 ↳if A_new >= C_old:
N 57892 ↳↳HL_bar[A_new] = B_fill
N 57892 ↳↳return
N 57892 ↳if A_new != 0x00:
N 57892 ↳↳HL_bar[A_new] = B_fill
N 57892 ↳HL_bar[A_new + 0x01] = 0x00
@ 57913 label=fn_rebuild_hud_meter_bars_counters_xa8c4
c 57913 fn_rebuild_hud_meter_bars_counters_xa8c4
D 57913 Rebuild HUD meter bars for counters at 0xA8C4/0xE4ED/0xE4CD/0xE50D into screen buffer rows 0x5AC6+.
N 57913 Args: none.
N 57913 Returns: none.
N 57913 def fn_rebuild_hud_meter_bars_counters_xa8c4():
N 57913 ↳fn_rebuild_hud_meter_bars_core(HL_bar=0x5AC6, A_len=var_runtime_progress_counter, E_fill=0x0F)
N 57913 ↳fn_rebuild_hud_meter_bars_core(HL_bar=0x5AD6, A_len=var_transient_queue_b, E_fill=0x06)
N 57913 ↳fn_rebuild_hud_meter_bars_core(HL_bar=0x5AE6, A_len=var_transient_queue_a, E_fill=0x05)
N 57913 ↳fn_rebuild_hud_meter_bars_core(HL_bar=0x5AF6, A_len=var_transient_queue_c, E_fill=0x07)
@ 57954 label=fn_rebuild_hud_meter_bars_core
c 57954 fn_rebuild_hud_meter_bars_core
D 57954 HUD meter-bars rebuild core: clear 10-byte row, fill A-byte prefix with E, then play short beeper cue.
N 57954 Args: HL_bar is ptr_u8 10-byte HUD row; A_len is u8 fill length (caller keeps it within row width); E_fill is u8 marker byte.
N 57954 Returns: none.
N 57954 def fn_rebuild_hud_meter_bars_core(HL_bar, A_len, E_fill):
N 57954 ↳HL_bar[0x00:0x0A] = 0x00
N 57954 ↳if A_len == 0x00:
N 57954 ↳↳return
N 57954 ↳HL_bar[0x00:A_len] = E_fill
N 57954 ↳rom_beeper(DE_ticks=0x0032, HL_period=0x0032)
@ 57979 label=movement_attempt_map_offset_1_enters
c 57979 movement_attempt_map_offset_1_enters
D 57979 Movement attempt with map offset +1 (neighbor step); enters shared move resolver 0xE298.
N 57979 Args: none.
N 57979 Returns: none.
N 57979 def movement_attempt_map_offset_1_enters():
N 57979 ↳movement_attempt_map_offset_50_move(DE_step=0x0001, B_mark=0x22)
@ 57987 label=movement_attempt_map_offset_50_enters
c 57987 movement_attempt_map_offset_50_enters
D 57987 Movement attempt with map offset +50; enters shared move resolver 0xE298.
N 57987 Args: none.
N 57987 Returns: none.
N 57987 def movement_attempt_map_offset_50_enters():
N 57987 ↳movement_attempt_map_offset_50_move(DE_step=0x0032, B_mark=0x23)
@ 57995 label=movement_attempt_map_offset_1_enters_2
c 57995 movement_attempt_map_offset_1_enters_2
D 57995 Movement attempt with map offset -1; enters shared move resolver 0xE298.
N 57995 Args: none.
N 57995 Returns: none.
N 57995 def movement_attempt_map_offset_1_enters_2():
N 57995 ↳movement_attempt_map_offset_50_move(DE_step=0xFFFF, B_mark=0x21)
@ 58003 label=movement_attempt_map_offset_50_move
c 58003 movement_attempt_map_offset_50_move
D 58003 Movement attempt with map offset -50 and shared move resolver (writes marker code B and updates 0xA8C1/0xA8DE/0xA8DF).
N 58003 Args: DE_step is i16 signed map offset (default 0xFFCE at this entry); B_mark is u8 destination marker code (default 0x24 at this entry).
N 58003 Returns: none.
N 58003 def movement_attempt_map_offset_50_move(DE_step=0xFFCE, B_mark=0x24):
N 58003 ↳HL_dst = var_runtime_current_cell_ptr_lo
N 58003 ↳var_move_marker_code_scratch = B_mark
N 58003 ↳var_runtime_move_delta = DE_step
N 58003 ↳HL_dst += DE_step
N 58003 ↳A_code = HL_dst[0x00] & 0x3F
N 58003 ↳if A_code == 0x00:
N 58003 ↳↳HL_cell = HL_dst
N 58003 ↳elif A_code < 0x15:
N 58003 ↳↳alternate_movement_commit_path_low_cell(HL_cell=HL_dst, DE_delta=DE_step, B_marker=B_mark)
N 58003 ↳↳return
N 58003 ↳elif A_code == 0x18:
N 58003 ↳↳HL_probe = HL_dst + DE_step
N 58003 ↳↳if (HL_probe[0x00] & 0x3F) != 0x00:
N 58003 ↳↳↳jump(0xE0E7)
N 58003 ↳↳HL_probe[0x00] = (HL_probe[0x00] & 0xC0) | 0x18
N 58003 ↳↳HL_cell = HL_probe - DE_step
N 58003 ↳elif A_code < 0x1B:
N 58003 ↳↳jump(0xE0E7)
N 58003 ↳elif A_code < 0x1D:
N 58003 ↳↳HL_cell = HL_dst
N 58003 ↳elif A_code == 0x25:
N 58003 ↳↳special_move_branch(HL_cell=HL_dst, DE_step=DE_step, B_mark=B_mark)
N 58003 ↳↳return
N 58003 ↳elif A_code < 0x2A or A_code == 0x38:
N 58003 ↳↳jump(0xE0E7)
N 58003 ↳else:
N 58003 ↳↳HL_cell = HL_dst
N 58003 ↳var_runtime_current_cell_ptr_lo = HL_cell
N 58003 ↳HL_cell[0x00] = (HL_cell[0x00] & 0xC0) | B_mark
N 58003 ↳HL_prev = HL_cell - DE_step
N 58003 ↳HL_prev[0x00] &= 0xC0
N 58003 ↳E_step = low_byte(DE_step)
N 58003 ↳if E_step == 0x01:
N 58003 ↳↳var_current_map_coords += 0x01
N 58003 ↳elif E_step == 0xCE:
N 58003 ↳↳var_current_map_col -= 0x01
N 58003 ↳elif E_step == 0xFF:
N 58003 ↳↳var_current_map_coords -= 0x01
N 58003 ↳else:
N 58003 ↳↳var_current_map_col += 0x01
N 58003 ↳jump(0xE0E7)
@ 58139 label=countdown_driven_marker_updater_one_cell
c 58139 countdown_driven_marker_updater_one_cell
D 58139 Countdown-driven marker updater one cell behind current pointer (uses 0xA8C4).
N 58139 Args: none.
N 58139 Returns: none.
N 58139 def countdown_driven_marker_updater_one_cell():
N 58139 ↳if var_runtime_progress_counter == 0x00:
N 58139 ↳↳return
N 58139 ↳HL_prev = read_u16(0xA8C1) - read_u16(0xA8C6)
N 58139 ↳if (HL_prev[0x00] & 0x3F) != 0x00:
N 58139 ↳↳return
N 58139 ↳HL_prev[0x00] = (HL_prev[0x00] & 0xC0) | 0x25
N 58139 ↳var_runtime_progress_counter -= 0x01
N 58139 ↳rom_beeper(DE_ticks=0x0005, HL_period=0x0005)
@ 58177 label=special_move_branch
c 58177 special_move_branch
D 58177 Special move branch: increment 0xA8C4, short delay, then commit through shared path 0xE2AD.
N 58177 Args: HL_cell is ptr_u8 pending destination cell; DE_step is i16 movement delta; B_mark is u8 marker code in caller BC context.
N 58177 Returns: none.
N 58177 def special_move_branch(HL_cell, DE_step, B_mark):
N 58177 ↳var_runtime_progress_counter += 0x01
N 58177 ↳rom_beeper(DE_ticks=0x0007, HL_period=0x000A)
N 58177 ↳jump(0xE2CD)
@ 58202 label=state_29_handler
c 58202 state_29_handler
D 58202 State-29 handler: mark current cell as code 29, delay, decrement phase counter 0xA8C5, and refresh via 0xF108.
N 58202 Args: none.
N 58202 Returns: none.
N 58202 def state_29_handler():
N 58202 ↳var_runtime_move_state_code = 0x1D
N 58202 ↳HL_cell = var_runtime_current_cell_ptr_lo
N 58202 ↳HL_cell[0x00] = (HL_cell[0x00] & 0xC0) | 0x1D
N 58202 ↳rom_beeper(DE_ticks=0x0014, HL_period=0x01F4)
N 58202 ↳var_runtime_objective_counter -= 0x01
N 58202 ↳jump(0xF108)
@ 58232 label=move_commit_branch_special_cell_codes
c 58232 move_commit_branch_special_cell_codes
D 58232 Move-commit branch for special cell codes: write current cell, update state at 0xA8C3, and route into state-29/marker logic.
N 58232 Args: A_code is u8 candidate low6 cell code from movement resolver.
N 58232 Returns: none.
N 58232 def move_commit_branch_special_cell_codes(A_code):
N 58232 ↳if A_code != 0x21:
N 58232 ↳↳HL_cell = var_runtime_current_cell_ptr_lo
N 58232 ↳↳HL_cell[0x00] = (HL_cell[0x00] & 0xC0) | A_code
N 58232 ↳↳var_runtime_move_state_code += 0x01
N 58232 ↳↳rom_beeper(DE_ticks=0x000F, HL_period=0x0190)
N 58232 ↳↳return
N 58232 ↳var_runtime_move_state_code = 0x1C
N 58232 ↳HL_cell = var_runtime_current_cell_ptr_lo
N 58232 ↳if (HL_cell[0x00] & 0x3F) < 0x15:
N 58232 ↳↳state_29_handler()
N 58232 ↳↳return
N 58232 ↳HL_cell[0x00] = (HL_cell[0x00] & 0xC0) | var_move_marker_code_scratch
@ 58285 label=var_move_marker_code_scratch
b 58285 var_move_marker_code_scratch
D 58285 Scratch byte: last movement marker code B for shared move path 0xE2AD/0xE343.
D 58285 Structure: 1-byte scratch field movement_marker_code written before shared commit path.
@ 58286 label=alternate_movement_commit_path_low_cell
c 58286 alternate_movement_commit_path_low_cell
D 58286 Alternate movement commit path used for low cell codes; then enters state-29 handler 0xE35A.
N 58286 Args: HL_cell is ptr_u8 destination cell; DE_delta is u16 signed move delta used by resolver; B_marker is u8 marker code written into destination low6 bits.
N 58286 Returns: none.
N 58286 def alternate_movement_commit_path_low_cell(HL_cell, DE_delta, B_marker):
N 58286 ↳var_runtime_current_cell_ptr_lo = HL_cell
N 58286 ↳HL_cell[0x00] = (HL_cell[0x00] & 0xC0) | B_marker
N 58286 ↳HL_prev = HL_cell - DE_delta
N 58286 ↳HL_prev[0x00] &= 0xC0
N 58286 ↳E_step = low_byte(DE_delta)
N 58286 ↳if E_step == 0x01:
N 58286 ↳↳var_current_map_coords += 0x01
N 58286 ↳elif E_step == 0xCE:
N 58286 ↳↳var_current_map_col -= 0x01
N 58286 ↳elif E_step == 0xFF:
N 58286 ↳↳var_current_map_coords -= 0x01
N 58286 ↳else:
N 58286 ↳↳var_current_map_col += 0x01
N 58286 ↳state_29_handler()
@ 58345 label=action_effect_dispatcher_keyed_xa8dc_bits
c 58345 action_effect_dispatcher_keyed_xa8dc_bits
D 58345 Action/effect dispatcher keyed by 0xA8DC bits; consumes counters at 0xE4CD/0xE4ED/0xE50D and writes transient map codes.
N 58345 Args: none.
N 58345 Returns: none.
N 58345 def action_effect_dispatcher_keyed_xa8dc_bits():
N 58345 ↳A_flags = var_action_effect_flags
N 58345 ↳if A_flags & 0x40:
N 58345 ↳↳if var_transient_queue_c == 0x00:
N 58345 ↳↳↳return
N 58345 ↳↳HL_cell = read_u16(var_runtime_current_cell_ptr_lo) + read_u16(var_runtime_move_delta)
N 58345 ↳↳if (HL_cell[0x00] & 0x3F) != 0x00:
N 58345 ↳↳↳return
N 58345 ↳↳HL_cell[0x00] = (HL_cell[0x00] & 0xC0) | 0x33
N 58345 ↳↳A_state = 0x34 if low_byte(var_runtime_move_delta) == 0x01 else (0x32 if low_byte(var_runtime_move_delta) == 0xFF else (0x01 if low_byte(var_runtime_move_delta) == 0xCE else 0x65))
N 58345 ↳↳queue_insert_state_with_cell_ptr(var_queue=var_transient_queue_c, A_state=A_state, HL_cell=HL_cell)
N 58345 ↳↳return
N 58345 ↳if A_flags & 0x10:
N 58345 ↳↳if var_transient_queue_b == 0x00:
N 58345 ↳↳↳return
N 58345 ↳↳HL_cell = read_u16(var_runtime_current_cell_ptr_lo) - read_u16(var_runtime_move_delta)
N 58345 ↳↳if (HL_cell[0x00] & 0x3F) != 0x00:
N 58345 ↳↳↳return
N 58345 ↳↳HL_cell[0x00] = (HL_cell[0x00] & 0xC0) | 0x36
N 58345 ↳↳queue_insert_state_with_cell_ptr(var_queue=var_transient_queue_b, A_state=0x80, HL_cell=HL_cell)
N 58345 ↳↳return
N 58345 ↳if A_flags & 0x01:
N 58345 ↳↳jump_0xE31B()
N 58345 ↳if var_transient_queue_a == 0x00:
N 58345 ↳↳return
N 58345 ↳HL_cell = read_u16(var_runtime_current_cell_ptr_lo) - read_u16(var_runtime_move_delta)
N 58345 ↳if (HL_cell[0x00] & 0x3F) != 0x00:
N 58345 ↳↳return
N 58345 ↳HL_cell[0x00] = (HL_cell[0x00] & 0xC0) | 0x34
N 58345 ↳queue_insert_state_with_cell_ptr(var_queue=var_transient_queue_a, A_state=0x80, HL_cell=HL_cell)
@ 58516 label=fn_process_transient_effect_queues_handlers_xe530
c 58516 fn_process_transient_effect_queues_handlers_xe530
D 58516 Process transient-effect queues (three 10-slot lists at 0xE4CE/0xE4EE/0xE50E) via handlers 0xE530/0xE5CA/0xE698.
N 58516 Args: none.
N 58516 Returns: none.
N 58516 def fn_process_transient_effect_queues_handlers_xe530():
N 58516 ↳fn_process_transient_effect_queues_core(HL_queue=var_transient_queue_a_entries, DE_handler=fn_transient_queue_handler_core)
N 58516 ↳fn_process_transient_effect_queues_core(HL_queue=var_transient_queue_b_entries, DE_handler=callback_queue_b_state_classifier)
N 58516 ↳fn_process_transient_effect_queues_core(HL_queue=var_transient_queue_c_entries, DE_handler=fn_repeat_wrapper_xe600)
N 58513 Queue-insert tail uses JP 0x03B5 for a short transient-effect cue.
@ 58540 label=fn_process_transient_effect_queues_core
@ 58558 label=patch_transient_queue_handler_call_target
c 58540 fn_process_transient_effect_queues_core
D 58540 Transient-effect queue processor core entry: scans three 10-slot queues and dispatches per-queue handlers.
N 58540 Args: HL_queue is ptr_u8 queue entries base (10 triplets [state,ptr_lo,ptr_hi]); DE_handler is ptr_fn callback(A_state:u8, HL_cell:ptr_u8)->A_state_next:u8.
N 58540 Returns: none.
N 58540 def fn_process_transient_effect_queues_core(HL_queue, DE_handler):
N 58540 ↳patch_transient_queue_handler_call_target = DE_handler
N 58540 ↳for _ in range(0x0A):
N 58540 ↳↳A_state = HL_queue[0x00]
N 58540 ↳↳if A_state != 0x00:
N 58540 ↳↳↳HL_cell = ptr_u16(HL_queue[0x01], HL_queue[0x02])
N 58540 ↳↳↳A_state = callback(DE_handler, A_state=A_state, HL_cell=HL_cell)
N 58540 ↳↳↳HL_queue[0x00] = A_state
N 58540 ↳↳↳HL_queue[0x01], HL_queue[0x02] = split_u16(HL_cell)
N 58540 ↳↳HL_queue += 0x03
N 58540 0xE4BE is the CALL target word inside this routine (CALL nn at 0xE4BD), runtime-written from DE at 0xE4AC.
@ 58573 label=var_transient_queue_a
b 58573 var_transient_queue_a
D 58573 Transient queue A at 0xE4CD..0xE4EC: counter byte + 10 triplets [state,ptr_lo,ptr_hi].
D 58573 Structure: counter at +0, then 10 entries x 3 bytes [state, ptr_lo, ptr_hi] over +1..+30, with one trailing byte at +31.
@ 58574 label=var_transient_queue_a_entries
@ 58605 label=var_transient_queue_b
b 58605 var_transient_queue_b
D 58605 Transient queue B at 0xE4ED..0xE50C: counter byte + 10 triplets [state,ptr_lo,ptr_hi].
D 58605 Structure: counter at +0, then 10 entries x 3 bytes [state, ptr_lo, ptr_hi] over +1..+30, with one trailing byte at +31.
@ 58606 label=var_transient_queue_b_entries
@ 58637 label=var_transient_queue_c
b 58637 var_transient_queue_c
D 58637 Transient queue C at 0xE50D..0xE52C: counter byte + 10 triplets [state,ptr_lo,ptr_hi].
D 58637 Structure: counter at +0, then 10 entries x 3 bytes [state, ptr_lo, ptr_hi] over +1..+30, with one trailing byte at +31.
@ 58638 label=var_transient_queue_c_entries
@ 58669 label=var_transient_effect_state
b 58669 var_transient_effect_state
D 58669 Transient effect state at 0xE52D..0xE52F: active byte + pointer pair consumed by 0xE6B3/0xE6D3 flow.
D 58669 Structure: transient-effect state triple [active_state, ptr_lo, ptr_hi].
@ 58670 label=var_transient_effect_ptr_lo
@ 58672 label=fn_transient_queue_handler_core
c 58672 fn_transient_queue_handler_core
D 58672 Transient queue-A handler core (0xE530): classify target cell and emit state/result for queue slot update.
N 58672 Args: A_state is u8 queue-slot state byte; HL_cell is ptr_u8 target map cell from queue entry.
N 58672 Returns: A_state_next is u8 queue-slot state result written back by queue dispatcher.
N 58672 def fn_transient_queue_handler_core(A_state, HL_cell):
N 58672 ↳A_state &= 0x7F
N 58672 ↳if (A_state & 0xFE) != 0x00:
N 58672 ↳↳return countdown_phase_helper(HL_cell=HL_cell, stack_A_state=A_state)
N 58672 ↳A_code = HL_cell[0x00] & 0x3F
N 58672 ↳if A_code == 0x34 or A_code == 0x35:
N 58672 ↳↳return state_toggle_helper(HL_cell=HL_cell, D_base=0x34, stack_A_state=A_state)
N 58672 ↳if A_code == 0x38 or A_code == 0x00:
N 58672 ↳↳return immediate_mark_helper(HL_cell=HL_cell, stack_A_state=A_state)
N 58672 ↳if A_code < 0x0D:
N 58672 ↳↳return return_helper(stack_A_state=A_state)
N 58672 ↳HL_cell[0x00] = (HL_cell[0x00] & 0xC0) | 0x38
N 58672 ↳fn_neighbor_tag_helper_queue_b_handlers(HL_cell=HL_cell)
N 58672 ↳return 0x00
@ 58714 label=fn_neighbor_tag_helper_queue_b_handlers
c 58714 fn_neighbor_tag_helper_queue_b_handlers
D 58714 Neighbor-tag helper for queue A/B handlers: inspect adjacent cells and stamp code 56 where allowed.
N 58714 Args: HL_cell is ptr_u8 center map cell.
N 58714 Returns: none.
N 58714 def fn_neighbor_tag_helper_queue_b_handlers(HL_cell):
N 58714 ↳fn_neighbor_tag_helper_core(HL_cell=HL_cell + 0x0001)
N 58714 ↳fn_neighbor_tag_helper_core(HL_cell=HL_cell - 0x0001)
N 58714 ↳fn_neighbor_tag_helper_core(HL_cell=HL_cell - 0x0032)
N 58714 ↳fn_neighbor_tag_helper_core(HL_cell=HL_cell + 0x0032)
@ 58735 label=fn_neighbor_tag_helper_core
c 58735 fn_neighbor_tag_helper_core
D 58735 Neighbor-tag helper core entry used by queue handlers to update adjacent map-cell tags.
N 58735 Args: HL_cell is ptr_u8 target map cell.
N 58735 Returns: none.
N 58735 def fn_neighbor_tag_helper_core(HL_cell):
N 58735 ↳A_code = HL_cell[0x00] & 0x3F
N 58735 ↳if not ((0x0D <= A_code < 0x17) or (0x21 <= A_code < 0x25) or (0x33 <= A_code < 0x39)):
N 58735 ↳↳return
N 58735 ↳HL_cell[0x00] = (HL_cell[0x00] & 0xC0) | 0x38
@ 58765 label=state_toggle_helper
c 58765 state_toggle_helper
D 58765 State-toggle helper: flip low bit and rewrite map cell with D/D+1 variant, returning state with bit7 set.
N 58765 Args: HL_cell is ptr_u8 target map cell; D_base is u8 base code (0x34 or 0x36); stack_A_state is the saved state byte popped from stack.
N 58765 Returns: A_state is updated state byte with bit7 set.
N 58765 def state_toggle_helper(HL_cell, D_base, stack_A_state):
N 58765 ↳A_state = stack_A_state ^ 0x01
N 58765 ↳D_code = D_base + A_state
N 58765 ↳HL_cell[0x00] = (HL_cell[0x00] & 0xC0) | D_code
N 58765 ↳return A_state | 0x80
@ 58780 label=delay_entry_helper_transient_handlers
c 58780 delay_entry_helper_transient_handlers
D 58780 Delay-entry helper for transient handlers: set bit7 and jump to pause routine 0xE6A3.
N 58780 Args: A_state is u8 transient handler state.
N 58780 Returns: none.
N 58780 def delay_entry_helper_transient_handlers(A_state):
N 58780 ↳A_state |= 0x80
N 58780 ↳routine_30_to_30_rom_beeper_pause()
@ 58785 label=countdown_phase_helper
c 58785 countdown_phase_helper
D 58785 Countdown/phase helper: map state into 0x29..0x2E sequence and clear cell when sequence completes.
N 58785 Args: HL_cell is ptr_u8 target map cell; stack_A_state is u8 state byte popped from stack.
N 58785 Returns: A_state is 0x00 when phase completes, otherwise returns via delay_entry_helper_transient_handlers with bit7 set.
N 58785 def countdown_phase_helper(HL_cell, stack_A_state):
N 58785 ↳A_state = stack_A_state
N 58785 ↳HL_cell[0x00] = (HL_cell[0x00] & 0xC0) | (A_state + 0x29)
N 58785 ↳A_state += 0x01
N 58785 ↳if A_state != 0x06:
N 58785 ↳↳return delay_entry_helper_transient_handlers(A_state=A_state)
N 58785 ↳HL_cell[0x00] &= 0xC0
N 58785 ↳return 0x00
@ 58807 label=immediate_mark_helper
c 58807 immediate_mark_helper
D 58807 Immediate mark helper (queue A): write code 42, propagate via 0xE55A, and return state 0x82.
N 58807 Args: HL_cell is ptr_u8 center map cell; stack_A_state is u8 state byte popped from stack and ignored.
N 58807 Returns: A_state is 0x82.
N 58807 def immediate_mark_helper(HL_cell, stack_A_state):
N 58807 ↳HL_cell[0x00] = (HL_cell[0x00] & 0xC0) | 0x2A
N 58807 ↳fn_neighbor_tag_helper_queue_b_handlers(HL_cell=HL_cell)
N 58807 ↳return 0x82
@ 58823 label=return_helper
c 58823 return_helper
D 58823 Shared return helper: pop AF and force bit7 in state byte.
N 58823 Args: stack_A_state is u8 state byte popped from stack.
N 58823 Returns: A_state is stack_A_state with bit7 set.
N 58823 def return_helper(stack_A_state):
N 58823 ↳A_state = stack_A_state | 0x80
N 58823 ↳return A_state
@ 58826 label=callback_queue_b_state_classifier
c 58826 callback_queue_b_state_classifier
D 58826 Transient queue-B handler core (0xE5CA): variant classifier for code family around 54/55/56.
N 58826 Args: A_state is u8 queue-slot state byte; HL_cell is ptr_u8 target map cell from queue entry.
N 58826 Returns: A_state_next is u8 queue-slot state result written back by queue dispatcher.
N 58826 def callback_queue_b_state_classifier(A_state, HL_cell):
N 58826 ↳A_state &= 0x7F
N 58826 ↳if (A_state & 0xFE) != 0x00:
N 58826 ↳↳return countdown_phase_helper(HL_cell=HL_cell, stack_A_state=A_state)
N 58826 ↳A_code = HL_cell[0x00] & 0x3F
N 58826 ↳if A_code == 0x36 or A_code == 0x37:
N 58826 ↳↳return state_toggle_helper(HL_cell=HL_cell, D_base=0x36, stack_A_state=A_state)
N 58826 ↳if A_code == 0x38 or A_code == 0x00:
N 58826 ↳↳HL_cell[0x00] = (HL_cell[0x00] & 0xC0) | 0x2A
N 58826 ↳↳return immediate_mark_helper(HL_cell=HL_cell, stack_A_state=A_state)
N 58826 ↳if A_code < 0x0D:
N 58826 ↳↳return return_helper(stack_A_state=A_state)
N 58826 ↳if A_code < 0x21:
N 58826 ↳↳return return_helper(stack_A_state=A_state)
N 58826 ↳return fallback_clear_helper_queue_b_path(HL_cell=HL_cell, stack_A_state=A_state)
N 58826 Entry is indirect: no direct CALL/JP to 0xE5CA; dispatcher at 0xE4A0 loads DE <- 0xE5CA and invokes handler via shared queue callback path.
N 58826 Internal stack-balance branch (POP DE) used by queue-C classifier path in 0xE600.
@ 58871 label=fallback_clear_helper_queue_b_path
c 58871 fallback_clear_helper_queue_b_path
D 58871 Fallback clear helper for queue-B path: force cell code 56 and return zero state.
N 58871 Args: HL_cell is ptr_u8 target map cell; stack_A_state is the saved state byte popped from stack and discarded.
N 58871 Returns: A_state is 0x00.
N 58871 def fallback_clear_helper_queue_b_path(HL_cell, stack_A_state):
N 58871 ↳HL_cell[0x00] = (HL_cell[0x00] & 0xC0) | 0x38
N 58871 ↳return 0x00
@ 58880 label=transient_queue_c_state_machine_core
@ 58889 label=patch_queue_c_root_eq_code
@ 58896 label=patch_queue_c_root_low_code_limit
@ 58938 label=patch_queue_c_scan_low_code_limit
@ 58942 label=patch_queue_c_scan_mid_code_limit
@ 58943 label=patch_queue_c_scan_branch_opcode
@ 59002 label=patch_queue_c_mark_code
c 58880 transient_queue_c_state_machine_core
D 58880 Transient queue-C state-machine core (0xE600): evaluates nearby cells and advances effect state/cell codes.
N 58880 Args: A_state is u8 queue-slot state byte; HL_cell is ptr_u8 target map cell.
N 58880 Returns: A_state_next is u8 next queue-slot state (0x00 clear, 0x80 latched mark, or phase-progress value).
N 58880 def transient_queue_c_state_machine_core(A_state, HL_cell):
N 58880 ↳if A_state & 0x80:
N 58880 ↳↳A_phase = A_state & 0x7F
N 58880 ↳↳if A_phase == 0x03:
N 58880 ↳↳↳HL_cell[0x00] &= 0xC0
N 58880 ↳↳↳return 0x00
N 58880 ↳↳HL_cell[0x00] = (HL_cell[0x00] & 0xC0) | (A_phase + 0x2B)
N 58880 ↳↳routine_30_to_30_rom_beeper_pause()
N 58880 ↳↳return A_phase + 0x01
N 58880 ↳A_code = HL_cell[0x00] & 0x3F
N 58880 ↳if A_code == patch_queue_c_root_eq_code:
N 58880 ↳↳A_saved = A_state
N 58880 ↳↳HL_root = HL_cell
N 58880 ↳↳HL_scan = HL_cell - 0x0032 + (A_code - 0x01)
N 58880 ↳↳A_scan = HL_scan[0x00] & 0x3F
N 58880 ↳↳if A_scan == 0x00:
N 58880 ↳↳↳HL_scan[0x00] = (HL_scan[0x00] & 0xC0) | patch_queue_c_mark_code
N 58880 ↳↳↳return A_saved
N 58880 ↳↳if A_scan < patch_queue_c_scan_low_code_limit:
N 58880 ↳↳↳HL_write = HL_root
N 58880 ↳↳elif A_scan < patch_queue_c_scan_mid_code_limit:
N 58880 ↳↳↳if patch_queue_c_scan_branch_opcode == 0x38:  # JR C
N 58880 ↳↳↳↳return fallback_clear_helper_queue_b_path(HL_cell=HL_scan, stack_A_state=A_saved)
N 58880 ↳↳↳HL_write = HL_root
N 58880 ↳↳elif A_scan == 0x38:
N 58880 ↳↳↳return fallback_clear_helper_queue_b_path(HL_cell=HL_scan, stack_A_state=A_saved)
N 58880 ↳↳elif A_scan < 0x21:
N 58880 ↳↳↳HL_write = HL_root
N 58880 ↳↳elif A_scan < 0x25:
N 58880 ↳↳↳return fallback_clear_helper_queue_b_path(HL_cell=HL_scan, stack_A_state=A_saved)
N 58880 ↳↳elif A_scan < 0x2A:
N 58880 ↳↳↳HL_write = HL_root
N 58880 ↳↳elif A_scan < 0x2E:
N 58880 ↳↳↳HL_write = HL_scan
N 58880 ↳↳elif A_scan < 0x33:
N 58880 ↳↳↳HL_write = HL_root
N 58880 ↳↳elif A_scan < 0x38:
N 58880 ↳↳↳return fallback_clear_helper_queue_b_path(HL_cell=HL_scan, stack_A_state=A_saved)
N 58880 ↳↳else:
N 58880 ↳↳↳HL_write = HL_root
N 58880 ↳↳HL_write[0x00] = (HL_write[0x00] & 0xC0) | 0x2A
N 58880 ↳↳return 0x80
N 58880 ↳if A_code == 0x00 or A_code == 0x38:
N 58880 ↳↳HL_cell[0x00] = (HL_cell[0x00] & 0xC0) | 0x2A
N 58880 ↳↳return 0x80
N 58880 ↳if A_code < patch_queue_c_root_low_code_limit:
N 58880 ↳↳return A_state
N 58880 ↳HL_cell[0x00] = (HL_cell[0x00] & 0xC0) | 0x38
N 58880 ↳return 0x00
N 58880 Patch points 0xE609/0xE610/0xE63A/0xE63E/0xE63F/0xE67A are immediates/opcode bytes in this code and are rewritten by 0xE6B3/0xE6D3 before/after active transient-effect execution.
@ 59032 label=fn_repeat_wrapper_xe600
c 59032 fn_repeat_wrapper_xe600
D 59032 Repeat wrapper for 0xE600: rerun while nonzero, non-bit7 state is returned.
N 59032 Args: A_state is u8 queue-slot state byte; HL_cell is ptr_u8 target map cell.
N 59032 Returns: A_state_next is u8 next queue-slot state after repeated E600 passes.
N 59032 def fn_repeat_wrapper_xe600(A_state, HL_cell):
N 59032 ↳A_state = transient_queue_c_state_machine_core(A_state=A_state, HL_cell=HL_cell)
N 59032 ↳while A_state != 0x00 and (A_state & 0x80) == 0x00:
N 59032 ↳↳A_state = transient_queue_c_state_machine_core(A_state=A_state, HL_cell=HL_cell)
N 59032 ↳return A_state
@ 59043 label=routine_30_to_30_rom_beeper_pause
c 59043 routine_30_to_30_rom_beeper_pause
D 59043 30/30 ROM-beeper pause helper used by transient effect state transitions.
N 59043 Args: none.
N 59043 Returns: none.
N 59043 def routine_30_to_30_rom_beeper_pause():
N 59043 ↳HL_saved, BC_saved, AF_saved = HL, BC, AF
N 59043 ↳rom_beeper(DE_ticks=0x001E, HL_period=0x001E)
N 59043 ↳HL, BC, AF = HL_saved, BC_saved, AF_saved
@ 59059 label=fn_active_transient_effect_executor
c 59059 fn_active_transient_effect_executor
D 59059 Active transient-effect executor: process pointer/state at 0xE52D..0xE52F via 0xE678 and restore thresholds.
N 59059 Args: none.
N 59059 Returns: none.
N 59059 def fn_active_transient_effect_executor():
N 59059 ↳if var_transient_effect_state == 0x00:
N 59059 ↳↳return
N 59059 ↳patch_queue_c_root_low_code_limit = 0x17
N 59059 ↳patch_queue_c_scan_low_code_limit = 0x17
N 59059 ↳patch_queue_c_scan_mid_code_limit = 0x39
N 59059 ↳patch_queue_c_root_eq_code = 0x39
N 59059 ↳patch_queue_c_mark_code = 0x39
N 59059 ↳patch_queue_c_scan_branch_opcode = 0x28
N 59059 ↳A_state = var_transient_effect_state
N 59059 ↳HL_cell = var_transient_effect_ptr_lo
N 59059 ↳A_state = fn_repeat_wrapper_xe600(A_state=A_state, HL_cell=HL_cell)
N 59059 ↳var_transient_effect_state = A_state
N 59059 ↳var_transient_effect_ptr_lo = HL_cell
N 59059 ↳patch_queue_c_root_low_code_limit = 0x0D
N 59059 ↳patch_queue_c_scan_low_code_limit = 0x0D
N 59059 ↳patch_queue_c_scan_mid_code_limit = 0x17
N 59059 ↳patch_queue_c_scan_branch_opcode = 0x38
N 59059 ↳patch_queue_c_root_eq_code = 0x33
N 59059 ↳patch_queue_c_mark_code = 0x33
@ 59130 label=var_hud_prev_cache_pair_0
b 59130 var_hud_prev_cache_pair_0
D 59130 HUD previous-value cache pair #0 at 0xE6FA..0xE6FB (loaded as BC by 0xE1C6 path).
D 59130 Structure: 16-bit cache pair [prev_low, prev_high] (loaded/stored as BC).
@ 59131 label=var_hud_prev_cache_pair_0_hi
@ 59132 label=var_hud_prev_cache_pair_1
b 59132 var_hud_prev_cache_pair_1
D 59132 HUD previous-value cache pair #1 at 0xE6FC..0xE6FD (loaded as BC by 0xE1FA path).
D 59132 Structure: 16-bit cache pair [prev_low, prev_high] (loaded/stored as BC).
@ 59133 label=var_hud_prev_cache_pair_1_hi
@ 59134 label=var_movement_hud_shared_state
b 59134 var_movement_hud_shared_state
D 59134 Movement/HUD shared state byte at 0xE6FE (updated in 0xE0A6 path, read by incremental redraw logic).
D 59134 Structure: single shared state byte.
b 59135 var_aux_padding_bytes
D 59135 Padding/aux bytes at 0xE6FF..0xE703 (no stable direct references yet).
D 59135 Structure: 5-byte auxiliary/padding slice; fields unresolved.
@ 59140 label=fn_queue_1_ai_step
@ 59207 label=patch_queue_1_block_threshold_code
c 59140 fn_queue_1_ai_step
D 59140 Queue-1 AI step (code-17 family): decode direction from state bits 0..2, probe target cells, move if allowed, and write facing codes 17..20.
N 59140 Args: A_state is u8 queue-state byte; BC_cell is ptr_u8 current map cell.
N 59140 Returns: A_state_next is u8 next queue state; BC_cell may advance to moved destination.
N 59140 def fn_queue_1_ai_step(A_state, BC_cell):
N 59140 ↳D_state = A_state
N 59140 ↳if A_state & 0xF0:
N 59140 ↳↳jump(0xE803)
N 59140 ↳if (BC_cell[0x00] & 0x3F) == 0x38:
N 59140 ↳↳BC_cell[0x00] = (BC_cell[0x00] & 0xC0) | 0x2A
N 59140 ↳↳return 0x10
N 59140 ↳if D_state & 0x01:
N 59140 ↳↳HL_step, E_face = 0xFFFF, 0x11
N 59140 ↳elif D_state & 0x02:
N 59140 ↳↳HL_step, E_face = 0x0001, 0x12
N 59140 ↳elif D_state & 0x04:
N 59140 ↳↳HL_step, E_face = 0x0032, 0x13
N 59140 ↳else:
N 59140 ↳↳HL_step, E_face = 0xFFCE, 0x14
N 59140 ↳HL_probe_2 = BC_cell + (HL_step << 0x01)
N 59140 ↳if (HL_probe_2[0x00] & 0x3F) == patch_queue_1_block_threshold_code:
N 59140 ↳↳return jump(0xE7F3)
N 59140 ↳HL_dst = BC_cell + HL_step
N 59140 ↳A_dst = HL_dst[0x00] & 0x3F
N 59140 ↳if A_dst == 0x00:
N 59140 ↳↳HL_dst[0x00] = (HL_dst[0x00] & 0xC0) | E_face
N 59140 ↳↳BC_cell[0x00] &= 0xC0
N 59140 ↳↳BC_cell = HL_dst
N 59140 ↳↳return D_state
N 59140 ↳if A_dst < 0x1D or A_dst == 0x38:
N 59140 ↳↳return jump(0xE7F3)
N 59140 ↳if A_dst == 0x25:
N 59140 ↳↳var_runtime_progress_counter += 0x01
N 59140 ↳↳fn_gameplay_movement_step_core()
N 59140 ↳↳HL_dst[0x00] = (HL_dst[0x00] & 0xC0) | 0x2A
N 59140 ↳↳BC_cell[0x00] &= 0xC0
N 59140 ↳↳BC_cell = HL_dst
N 59140 ↳↳return 0x10
N 59140 ↳HL_dst[0x00] = (HL_dst[0x00] & 0xC0) | E_face
N 59140 ↳BC_cell[0x00] &= 0xC0
N 59140 ↳BC_cell = HL_dst
N 59140 ↳return D_state
@ 59247 label=callback_queue_2_directional_ai_step
@ 59314 label=patch_queue_2_block_threshold_code
c 59247 callback_queue_2_directional_ai_step
D 59247 Queue-2 AI step (code-13 family): same directional policy as 0xE704, with facing codes 13..16.
N 59247 Args: A_state is u8 queue-state byte; BC_cell is ptr_u8 current map cell.
N 59247 Returns: A_state_next is u8 next queue state; BC_cell may advance to moved destination.
N 59247 def callback_queue_2_directional_ai_step(A_state, BC_cell):
N 59247 ↳D_state = A_state
N 59247 ↳if A_state & 0xF0:
N 59247 ↳↳jump(0xE803)
N 59247 ↳if (BC_cell[0x00] & 0x3F) == 0x38:
N 59247 ↳↳BC_cell[0x00] = (BC_cell[0x00] & 0xC0) | 0x2A
N 59247 ↳↳return 0x10
N 59247 ↳if D_state & 0x01:
N 59247 ↳↳HL_step, E_face = 0xFFFF, 0x0D
N 59247 ↳elif D_state & 0x02:
N 59247 ↳↳HL_step, E_face = 0x0001, 0x0E
N 59247 ↳elif D_state & 0x04:
N 59247 ↳↳HL_step, E_face = 0x0032, 0x0F
N 59247 ↳else:
N 59247 ↳↳HL_step, E_face = 0xFFCE, 0x10
N 59247 ↳HL_probe_2 = BC_cell + (HL_step << 0x01)
N 59247 ↳if (HL_probe_2[0x00] & 0x3F) == patch_queue_2_block_threshold_code:
N 59247 ↳↳return jump(0xE7F3)
N 59247 ↳HL_dst = BC_cell + HL_step
N 59247 ↳A_dst = HL_dst[0x00] & 0x3F
N 59247 ↳if A_dst == 0x00:
N 59247 ↳↳HL_dst[0x00] = (HL_dst[0x00] & 0xC0) | E_face
N 59247 ↳↳BC_cell[0x00] &= 0xC0
N 59247 ↳↳BC_cell = HL_dst
N 59247 ↳↳return D_state
N 59247 ↳if A_dst < 0x1D or A_dst == 0x38:
N 59247 ↳↳return jump(0xE7F3)
N 59247 ↳if A_dst == 0x25:
N 59247 ↳↳var_runtime_progress_counter += 0x01
N 59247 ↳↳fn_gameplay_movement_step_core()
N 59247 ↳↳HL_dst[0x00] = (HL_dst[0x00] & 0xC0) | 0x2A
N 59247 ↳↳BC_cell[0x00] &= 0xC0
N 59247 ↳↳BC_cell = HL_dst
N 59247 ↳↳return 0x10
N 59247 ↳HL_dst[0x00] = (HL_dst[0x00] & 0xC0) | E_face
N 59247 ↳BC_cell[0x00] &= 0xC0
N 59247 ↳BC_cell = HL_dst
N 59247 ↳return D_state
N 59247 Entry is indirect: no direct CALL/JP to 0xE76F; queue router at 0xE9D1 loads DE <- 0xE76F and dispatches through shared callback executor.
@ 59464 label=callback_queue_3_chase_ai_step
@ 59531 label=patch_queue_3_block_threshold_code
@ 59580 label=patch_queue_3_contact_branch_opcode
@ 59758 label=patch_queue_3_fallback_threshold_code
c 59464 callback_queue_3_chase_ai_step
D 59464 Queue-3 AI step (code-1 family): directional movement + phase animation, with player-relative branch that can arm transient effect source at 0xE52D.
N 59464 Args: A_state is u8 queue-state byte; BC_cell is ptr_u8 current map cell.
N 59464 Returns: A_state_next is u8 next queue state; BC_cell may advance to moved destination.
N 59464 def callback_queue_3_chase_ai_step(A_state, BC_cell):
N 59464 ↳D_state = A_state
N 59464 ↳if A_state & 0xF0:
N 59464 ↳↳return jump(0xE803)
N 59464 ↳if (BC_cell[0x00] & 0x3F) == 0x38:
N 59464 ↳↳return jump(0xE7EA)
N 59464 ↳if D_state & 0x01:
N 59464 ↳↳HL_step, E_base = 0xFFFF, 0x01
N 59464 ↳elif D_state & 0x02:
N 59464 ↳↳HL_step, E_base = 0x0001, 0x04
N 59464 ↳elif D_state & 0x04:
N 59464 ↳↳HL_step, E_base = 0x0032, 0x07
N 59464 ↳else:
N 59464 ↳↳HL_step, E_base = 0xFFCE, 0x0A
N 59464 ↳HL_probe_2 = BC_cell + (HL_step << 0x01)
N 59464 ↳if (HL_probe_2[0x00] & 0x3F) == patch_queue_3_block_threshold_code:
N 59464 ↳↳return fallback_direction_from_player_delta()
N 59464 ↳HL_dst = BC_cell + HL_step
N 59464 ↳A_dst = HL_dst[0x00] & 0x3F
N 59464 ↳if A_dst == 0x00:
N 59464 ↳↳pass
N 59464 ↳elif A_dst < 0x1D or A_dst == 0x38 or A_dst == 0x39:
N 59464 ↳↳return fallback_direction_from_player_delta()
N 59464 ↳elif A_dst == 0x25:
N 59464 ↳↳special_contact_event_branch_xe848()
N 59464 ↳HL_dst[0x00] &= 0xC0
N 59464 ↳HL_dst[0x00] |= E_base + var_runtime_phase_index
N 59464 ↳BC_cell[0x00] &= 0xC0
N 59464 ↳BC_cell = HL_dst
N 59464 ↳if patch_queue_3_contact_branch_opcode != 0xC5:
N 59464 ↳↳return D_state
N 59464 ↳if var_transient_effect_state != 0x00:
N 59464 ↳↳return D_state
N 59464 ↳HL_player = var_current_map_coords
N 59464 ↳fn_convert_map_pointer_hl_row_column(HL_map=BC_cell)
N 59464 ↳BC_enemy = var_current_map_coords
N 59464 ↳var_current_map_coords = HL_player
N 59464 ↳if HL_player[0x00] >= BC_enemy[0x00] and HL_player[0x01] == BC_enemy[0x01]:
N 59464 ↳↳if D_state & 0x04:
N 59464 ↳↳↳HL_spawn = BC_cell + 0x0032
N 59464 ↳↳↳A_seed = 0x65
N 59464 ↳↳else:
N 59464 ↳↳↳return D_state
N 59464 ↳elif HL_player[0x00] < BC_enemy[0x00] and HL_player[0x01] == BC_enemy[0x01]:
N 59464 ↳↳if D_state & 0x08:
N 59464 ↳↳↳HL_spawn = BC_cell + 0xFFCE
N 59464 ↳↳↳A_seed = 0x01
N 59464 ↳↳else:
N 59464 ↳↳↳return D_state
N 59464 ↳elif HL_player[0x01] < BC_enemy[0x01] and HL_player[0x00] == BC_enemy[0x00]:
N 59464 ↳↳if D_state & 0x01:
N 59464 ↳↳↳HL_spawn = BC_cell - 0x0001
N 59464 ↳↳↳A_seed = 0x32
N 59464 ↳↳else:
N 59464 ↳↳↳return D_state
N 59464 ↳elif HL_player[0x01] >= BC_enemy[0x01] and HL_player[0x00] == BC_enemy[0x00]:
N 59464 ↳↳if D_state & 0x02:
N 59464 ↳↳↳HL_spawn = BC_cell + 0x0001
N 59464 ↳↳↳A_seed = 0x34
N 59464 ↳↳else:
N 59464 ↳↳↳return D_state
N 59464 ↳else:
N 59464 ↳↳return D_state
N 59464 ↳if (HL_spawn[0x00] & 0x3F) != 0x00:
N 59464 ↳↳return D_state
N 59464 ↳var_transient_effect_state = A_seed
N 59464 ↳var_transient_effect_ptr_lo = HL_spawn
N 59464 ↳HL_spawn[0x00] = (HL_spawn[0x00] & 0xC0) | 0x39
N 59464 ↳return D_state
N 59464 Entry is indirect: no direct CALL/JP to 0xE848; queue router at 0xE9DD loads DE <- 0xE848 and dispatches through shared callback executor.
N 59464 0xE88B/0xE96E are CP-immediate thresholds; 0xE8BC is a patchable branch-gate opcode byte (0xC5 PUSH BC or 0xC9 RET) rewritten by 0xF1C0/0xF231.
N 59464 Fallback direction chooser at 0xE963/0xE989 uses var_runtime_move_delta (1/255/50/other -> return 2/1/4/8) and rechecks cell-code guards.
s 59815 Reserved 5-byte gap (currently unused).
@ 59820 label=special_contact_event_branch_xe848
c 59820 special_contact_event_branch_xe848
D 59820 Special contact/event branch used by 0xE848: increment 0xA8C4 and refresh HUD counters via 0xE1C6.
N 59820 Args: none.
N 59820 Returns: none.
N 59820 def special_contact_event_branch_xe848():
N 59820 ↳var_runtime_progress_counter += 0x01
N 59820 ↳swap_register_bank_exx()
N 59820 ↳fn_hud_decimal_counter_animator()
N 59820 ↳fn_gameplay_movement_step_core()
N 59820 ↳swap_register_bank_exx()
@ 59836 label=per_frame_object_state_update_pass
c 59836 per_frame_object_state_update_pass
D 59836 Per-frame object/state update pass: cycles phase byte at 0xA8C0, iterates active object queues, and applies callback-driven transforms.
N 59836 Args: none.
N 59836 Returns: none.
N 59836 def per_frame_object_state_update_pass():
N 59836 ↳A_phase = var_runtime_phase_index + 0x01
N 59836 ↳if A_phase == 0x03:
N 59836 ↳↳A_phase = 0x00
N 59836 ↳var_runtime_phase_index = A_phase
N 59836 ↳fn_object_state_update_pass_core(DE_cb=fn_queue_1_ai_step, HL_queue=var_runtime_queue_head_1_ptr)
N 59836 ↳fn_object_state_update_pass_core(DE_cb=callback_queue_2_directional_ai_step, HL_queue=var_runtime_queue_head_2_ptr)
N 59836 ↳fn_active_transient_effect_executor()
N 59836 ↳fn_object_state_update_pass_core(DE_cb=callback_queue_3_chase_ai_step, HL_queue=var_runtime_queue_head_3_ptr)
N 59836 ↳fn_object_state_update_pass_core(DE_cb=callback_queue_0_low_bits_toggle, HL_queue=var_runtime_queue_head_0_lo)
N 59836 Queue callback routing is fixed: 0xA8B8->0xE704, 0xA8BA->0xE76F, 0xA8BC->0xE848, 0xA8B6->0xEA0C.
@ 59884 label=fn_object_state_update_pass_core
@ 59902 label=patch_object_callback_call_target
c 59884 fn_object_state_update_pass_core
D 59884 Per-frame object/state update core entry: runs slot pass used by gameplay tick and transition paths.
N 59884 Args: DE_cb is ptr_code callback entry with contract (A_state:u8, BC_cell:ptr_u8)->(A_state:u8, BC_cell:ptr_u8); HL_queue is ptr_u8 queue stream of 3-byte records [state, cell_lo, cell_hi], terminated by state 0xFF.
N 59884 Returns: none.
N 59884 def fn_object_state_update_pass_core(DE_cb, HL_queue):
N 59884 ↳patch_object_callback_call_target = DE_cb
N 59884 ↳while True:
N 59884 ↳↳A_state = HL_queue[0x00]
N 59884 ↳↳if A_state == 0xFF:
N 59884 ↳↳↳return
N 59884 ↳↳if A_state != 0x00:
N 59884 ↳↳↳BC_cell = (HL_queue[0x02] << 0x08) | HL_queue[0x01]
N 59884 ↳↳↳A_state, BC_cell = call_dynamic_object_callback(A_state=A_state, BC_cell=BC_cell)
N 59884 ↳↳↳HL_queue[0x01] = BC_cell & 0xFF
N 59884 ↳↳↳HL_queue[0x02] = BC_cell >> 0x08
N 59884 ↳↳↳HL_queue[0x00] = A_state
N 59884 ↳↳HL_queue += 0x03
@ 59916 label=callback_queue_0_low_bits_toggle
c 59916 callback_queue_0_low_bits_toggle
D 59916 Queue-0 callback: toggle low two bits in target map cell (XOR 3), keeping animation in-place.
N 59916 Args: A_state is u8 queue state; BC_cell is ptr_u8 target map cell.
N 59916 Returns: A_state unchanged.
N 59916 def callback_queue_0_low_bits_toggle(A_state, BC_cell):
N 59916 ↳BC_cell[0x00] ^= 0x03
N 59916 ↳return A_state
N 59916 Entry is indirect: no direct CALL/JP to 0xEA0C; queue router at 0xE9E6 loads DE <- 0xEA0C and dispatches through shared callback executor.
@ 59923 label=var_queue_write_ptr_scratch
b 59923 var_queue_write_ptr_scratch
D 59923 Scratch queue-write pointer (0xEA13..0xEA14) for object-queue expansion helper 0xEC0A/0xEC34.
D 59923 Structure: 16-bit scratch pointer [ptr_lo, ptr_hi] used during queue insertion.
@ 59925 label=var_queue_state_scratch
b 59925 var_queue_state_scratch
D 59925 Scratch state byte (0xEA15) paired with pointer above during queue insertion.
D 59925 Structure: 1-byte scratch state paired with pointer at 0xEA13.
N 59926 Internal phase-wrap branch in 0xE9BC: reset frame phase byte 0xA8C0 to 0 every 3 ticks.
@ 59930 label=fn_hud_decimal_counter_animator
c 59930 fn_hud_decimal_counter_animator
D 59930 HUD decimal counter animator: increment 0xA8C8..0xA8CC modulo 10 and redraw digits via 0xEAC3.
N 59930 Args: none.
N 59930 Returns: none.
N 59930 def fn_hud_decimal_counter_animator():
N 59930 ↳A_d4 = var_runtime_aux_cc + 0x01
N 59930 ↳if A_d4 != 0x0A:
N 59930 ↳↳var_runtime_aux_cc = A_d4
N 59930 ↳↳jump(0xEA88)
N 59930 ↳var_runtime_aux_cc = 0x00
N 59930 ↳fn_hud_decimal_animator_stage_1(A_digit=0x00)
N 59930 ↳fn_hud_decimal_counter_animator_core()
@ 59952 label=fn_hud_decimal_counter_animator_core
c 59952 fn_hud_decimal_counter_animator_core
D 59952 HUD decimal-counter animator core entry: shared increment/decrement and carry handling path.
N 59952 Args: none.
N 59952 Returns: none.
N 59952 def fn_hud_decimal_counter_animator_core():
N 59952 ↳A_d3 = var_runtime_aux_cb + 0x01
N 59952 ↳if A_d3 != 0x0A:
N 59952 ↳↳var_runtime_aux_cb = A_d3
N 59952 ↳↳fn_hud_decimal_animator_stage_2(A_digit=A_d3)
N 59952 ↳↳return
N 59952 ↳var_runtime_aux_cb = 0x00
N 59952 ↳fn_hud_decimal_animator_stage_2(A_digit=0x00)
N 59952 ↳A_d2 = var_runtime_aux_ca + 0x01
N 59952 ↳if A_d2 != 0x0A:
N 59952 ↳↳var_runtime_aux_ca = A_d2
N 59952 ↳↳fn_hud_decimal_animator_stage_3(A_digit=A_d2)
N 59952 ↳↳return
N 59952 ↳var_runtime_aux_ca = 0x00
N 59952 ↳fn_hud_decimal_animator_stage_3(A_digit=0x00)
N 59952 ↳A_d1 = var_runtime_aux_c8_hi + 0x01
N 59952 ↳if A_d1 != 0x0A:
N 59952 ↳↳var_runtime_aux_c8_hi = A_d1
N 59952 ↳↳fn_hud_decimal_animator_stage_dispatch(A_digit=A_d1)
N 59952 ↳↳return
N 59952 ↳var_runtime_aux_c8_hi = 0x00
N 59952 ↳fn_hud_decimal_animator_stage_dispatch(A_digit=0x00)
N 59952 ↳A_d0 = var_runtime_aux_c8_lo + 0x01
N 59952 ↳if A_d0 != 0x0A:
N 59952 ↳↳var_runtime_aux_c8_lo = A_d0
N 59952 ↳↳jump(0xEAA0)
N 59952 ↳var_runtime_aux_c8_lo = 0x00
N 59952 ↳jump(0xEAA0)
@ 60040 label=fn_hud_decimal_animator_stage_1
c 60040 fn_hud_decimal_animator_stage_1
D 60040 HUD decimal animator stage #1 entry (offset +0x6E in 0xEA1A).
N 60040 Args: A_digit is u8 decimal digit value.
N 60040 Returns: none.
N 60040 def fn_hud_decimal_animator_stage_1(A_digit):
N 60040 ↳glyph_plot_helper(A_glyph=A_digit, B_row=0x11, C_col=0x0A)
@ 60046 label=fn_hud_decimal_animator_stage_2
c 60046 fn_hud_decimal_animator_stage_2
D 60046 HUD decimal animator stage #2 entry (offset +0x74 in 0xEA1A).
N 60046 Args: A_digit is u8 decimal digit value.
N 60046 Returns: none.
N 60046 def fn_hud_decimal_animator_stage_2(A_digit):
N 60046 ↳glyph_plot_helper(A_glyph=A_digit, B_row=0x11, C_col=0x09)
@ 60052 label=fn_hud_decimal_animator_stage_3
c 60052 fn_hud_decimal_animator_stage_3
D 60052 HUD decimal animator stage #3 entry (offset +0x7A in 0xEA1A).
N 60052 Args: A_digit is u8 decimal digit value.
N 60052 Returns: none.
N 60052 def fn_hud_decimal_animator_stage_3(A_digit):
N 60052 ↳glyph_plot_helper(A_glyph=A_digit, B_row=0x11, C_col=0x08)
@ 60058 label=fn_hud_decimal_animator_stage_dispatch
c 60058 fn_hud_decimal_animator_stage_dispatch
D 60058 HUD decimal animator stage-dispatch entry (offset +0x80 in 0xEA1A).
N 60058 Args: A_digit is u8 decimal digit value.
N 60058 Returns: none.
N 60058 def fn_hud_decimal_animator_stage_dispatch(A_digit):
N 60058 ↳glyph_plot_helper(A_glyph=A_digit, B_row=0x11, C_col=0x07)
@ 60070 label=fn_routine_8_byte_screen_blit_primitive
c 60070 fn_routine_8_byte_screen_blit_primitive
D 60070 8-byte screen blit primitive: copy bytes from DE into ZX bitmap using B=character row (8-pixel steps) and C=byte column.
N 60070 Args: DE_src is ptr_u8 source byte stream (8 bytes); B_row is u8 character-row index; C_col is u8 byte-column index.
N 60070 Returns: DE_src advanced by 8 bytes.
N 60070 def fn_routine_8_byte_screen_blit_primitive(DE_src, B_row, C_col):
N 60070 ↳HL_dst = zx_bitmap_addr_from_row_col(B_row, C_col)
N 60070 ↳for i in range(0x08):
N 60070 ↳↳HL_dst[i * 0x0100] = DE_src[i]
s 60098 Reserved 1-byte gap before stretched glyph plot helper at 0xEAC3 (unused).
@ 60099 label=glyph_plot_helper
c 60099 glyph_plot_helper
D 60099 Glyph plot helper: compute glyph address via biased base 0x66BE (HL=0x66BE+8*(A+17); storage table starts at 0x66C0), build a 16-byte temporary strip, and draw symbol footprint 8x16 via two calls to 0xEAA6.
N 60099 Args: A_glyph is u8 glyph code; B_row is u8 character-row index; C_col is u8 byte-column index.
N 60099 Returns: B_row is preserved; C_col is incremented by 1.
N 60099 def glyph_plot_helper(A_glyph, B_row, C_col):
N 60099 ↳A_glyph = (A_glyph + 0x10) & 0xFF
N 60099 ↳B_row, C_col = fn_glyph_plot_helper_entry(A_glyph=A_glyph, B_row=B_row, C_col=C_col)
N 60099 ↳return B_row, C_col
@ 60101 label=fn_glyph_plot_helper_entry
c 60101 fn_glyph_plot_helper_entry
D 60101 Glyph-plot helper callable entry (+0x2): blits one glyph byte-row to ZX bitmap via mapped address math.
N 60101 Args: A_glyph is u8 glyph code from stream; B_row is u8 character-row index; C_col is u8 byte-column index.
N 60101 Returns: B_row is preserved; C_col is incremented by 1.
N 60101 def fn_glyph_plot_helper_entry(A_glyph, B_row, C_col):
N 60101 ↳DE_src = 0x66BE + 0x08 * (A_glyph + 0x11)
N 60101 ↳for i in range(0x08):
N 60101 ↳↳var_glyph_scratch_template[0x01 + i * 0x02] = DE_src[i]
N 60101 ↳↳var_glyph_scratch_template[0x02 + i * 0x02] = DE_src[i]
N 60101 ↳fn_routine_8_byte_screen_blit_primitive(DE_src=var_glyph_scratch_template, B_row=B_row, C_col=C_col)
N 60101 ↳fn_routine_8_byte_screen_blit_primitive(DE_src=var_glyph_scratch_template + 0x08, B_row=B_row + 0x01, C_col=C_col)
N 60101 ↳C_col += 0x01
N 60101 ↳return B_row, C_col
@ 60145 label=var_glyph_scratch_template
b 60145 var_glyph_scratch_template
D 60145 Glyph scratch-template buffer at 0xEAF1..0xEB01 (17 bytes) used by 0xEAC3 to build doubled-row 8x16 glyph strips.
D 60145 Structure: 17-byte glyph scratch template; bytes +1..+16 hold doubled 8-row glyph data used as two 8-byte blit slices.
@ 60146 label=var_glyph_scratch_template_row_1
@ 60153 label=var_glyph_scratch_template_row_2
@ 60162 label=fn_stretched_text_symbol_stream_printer
c 60162 fn_stretched_text_symbol_stream_printer
D 60162 Stretched text/symbol stream printer: read bytes at HL until 255 terminator and draw each code via 0xEAC5 (8x16 output path).
N 60162 Static stream sources seen in CALL sites: 0x6C19/0x6C25/0x6C35/0x6C41/0x6C4B/0x6C5A (front-end options), 0x6ABD/0x6AD6/0x6AEF/0x6B08/0x6B21 (high-score rows), 0x6FAD ("HALL OF FAME"), 0x7113 ("ENTER YOUR NAME"), 0xF816/0xF829/0xF839/0xF84A (ending lines).
N 60162 One dynamic source is also used: HL <- (0x7110) at 0x7070 during name-entry redraw.
N 60162 Args: HL_stream is ptr_u8 to 0xFF-terminated glyph stream; B_row is u8 character-row index; C_col is u8 byte-column index.
N 60162 Returns: B_row is preserved; C_col is advanced by number of emitted glyphs.
N 60162 def fn_stretched_text_symbol_stream_printer(HL_stream, B_row, C_col):
N 60162 ↳var_stream_walk_ptr_scratch = HL_stream
N 60162 ↳while True:
N 60162 ↳↳A_glyph = var_stream_walk_ptr_scratch[0x00]
N 60162 ↳↳if A_glyph == 0xFF:
N 60162 ↳↳↳return B_row, C_col
N 60162 ↳↳B_row, C_col = fn_glyph_plot_helper_entry(A_glyph=A_glyph, B_row=B_row, C_col=C_col)
N 60162 ↳↳var_stream_walk_ptr_scratch += 0x0001
@ 60182 label=var_stream_walk_ptr_scratch
b 60182 var_stream_walk_ptr_scratch
D 60182 Stream-walk scratch pointer for 0xEAE2 printer (saved/restored HL while consuming 0xFF-terminated text stream).
D 60182 Structure: 16-bit stream walker pointer [ptr_lo, ptr_hi].
@ 60184 label=fn_directional_interaction_dispatcher_using_pointer_table
c 60184 fn_directional_interaction_dispatcher_using_pointer_table
D 60184 Directional interaction dispatcher using pointer table at 0xA8CF and bitmask at 0xA8D7.
N 60184 Args: none.
N 60184 Returns: none (updates var_runtime_direction_mask in place).
N 60184 def fn_directional_interaction_dispatcher_using_pointer_table():
N 60184 ↳IX_dir = var_runtime_dir_ptr_up
N 60184 ↳C_flags = var_runtime_direction_mask
N 60184 ↳if C_flags & 0x01:
N 60184 ↳↳direction_bit_0_blocked_path_handler()
N 60184 ↳else:
N 60184 ↳↳fn_directional_action_core(IX_dir=IX_dir, B_mask=0x02, C_flags=C_flags)
N 60184 ↳IX_dir += 0x0002
N 60184 ↳if C_flags & 0x02:
N 60184 ↳↳direction_bit_1_blocked_path_handler()
N 60184 ↳else:
N 60184 ↳↳fn_directional_action_core(IX_dir=IX_dir, B_mask=0x04, C_flags=C_flags)
N 60184 ↳IX_dir += 0x0002
N 60184 ↳if C_flags & 0x04:
N 60184 ↳↳direction_bit_2_blocked_path_handler()
N 60184 ↳else:
N 60184 ↳↳fn_directional_action_core(IX_dir=IX_dir, B_mask=0x08, C_flags=C_flags)
N 60184 ↳IX_dir += 0x0002
N 60184 ↳if C_flags & 0x08:
N 60184 ↳↳direction_bit_3_blocked_path_handler()
N 60184 ↳else:
N 60184 ↳↳HL_probe = read_u16_ix(IX_dir + 0x00)
N 60184 ↳↳IX_dir = var_runtime_scheduler_timer_lo  # IX+2/3 points to first directional slot at 0xA8CF
N 60184 ↳↳fn_directional_action_validate_target(HL_probe=HL_probe, IX_dir=IX_dir, B_mask=0x01, C_flags=C_flags)
N 60184 ↳var_runtime_direction_mask = C_flags
@ 60259 label=fn_directional_action_core
c 60259 fn_directional_action_core
D 60259 Directional action core: validate target cell, perform map edit, and wrap it with pre/post render calls.
N 60259 Args: IX_dir points to directional descriptor where [+0,+1] is probe cell pointer and [+2,+3] is paired map-cell pointer; B_mask is u8 directional bit mask; C_flags is u8 directional flags.
N 60259 Returns: none (C_flags is updated in-place by fn_directional_action_validate_target on commit path).
N 60259 def fn_directional_action_core(IX_dir, B_mask, C_flags):
N 60259 ↳HL_probe = read_u16_ix(IX_dir + 0x00)
N 60259 ↳fn_directional_action_validate_target(HL_probe=HL_probe, IX_dir=IX_dir, B_mask=B_mask, C_flags=C_flags)
@ 60265 label=fn_directional_action_validate_target
@ 60305 label=patch_directional_action_mark_code
c 60265 fn_directional_action_validate_target
D 60265 Directional-action sub-entry (+0x6): validate/normalize target cell and continue action pipeline.
N 60265 0xEB91 is the immediate byte of OR nn in this routine; it is runtime-set from A at 0xEB8A.
N 60265 Args: HL_probe is ptr_u8 candidate map cell from direction table; IX_dir points to direction descriptor where [+2,+3] is paired map-cell pointer; B_mask is u8 directional bit mask; C_flags is u8 directional flags.
N 60265 Returns: none (C_flags is updated in-place by OR with B_mask on commit path).
N 60265 def fn_directional_action_validate_target(HL_probe, IX_dir, B_mask, C_flags):
N 60265 ↳A_code = HL_probe[0x00] & 0x3F
N 60265 ↳if A_code in [0x1B, 0x1C]:
N 60265 ↳↳HL_probe[0x00] ^= 0x07
N 60265 ↳↳return
N 60265 ↳saved_code = A_code
N 60265 ↳render_ctx_save()
N 60265 ↳fn_main_pseudo_3d_map_render_pipeline()
N 60265 ↳fn_pre_action_overlay_painter_ui_area()
N 60265 ↳render_ctx_restore()
N 60265 ↳HL_pair = read_u16_ix(IX_dir + 0x02)
N 60265 ↳patch_directional_action_mark_code = saved_code
N 60265 ↳HL_pair[0x00] = (HL_pair[0x00] & 0xC0) | patch_directional_action_mark_code
N 60265 ↳fn_convert_map_pointer_hl_row_column(HL_cell=HL_pair)
N 60265 ↳HL_probe[0x00] = (HL_probe[0x00] & 0xC0) | 0x1B
N 60265 ↳var_runtime_current_cell_ptr_lo = HL_probe
N 60265 ↳C_flags |= B_mask
N 60265 ↳render_ctx_save()
N 60265 ↳fn_main_pseudo_3d_map_render_pipeline()
N 60265 ↳fn_post_action_overlay_painter_ui_area()
N 60265 ↳render_ctx_restore()
@ 60342 label=direction_bit_0_blocked_path_handler
c 60342 direction_bit_0_blocked_path_handler
D 60342 Direction bit-0 blocked-path handler (mask with 254) then continue dispatcher.
N 60342 Args: none (uses IX_dir and C_flags from fn_directional_interaction_dispatcher_using_pointer_table context).
N 60342 Returns: none.
N 60342 def direction_bit_0_blocked_path_handler():
N 60342 ↳fn_if_probed_cell_is_empty_mark(IX_ptr_slot=IX_dir, B_bit_clear_mask=0xFE, C_blocked_bits=C_flags)
N 60342 ↳jump(0xEB2A)
@ 60350 label=direction_bit_1_blocked_path_handler
c 60350 direction_bit_1_blocked_path_handler
D 60350 Direction bit-1 blocked-path handler (mask with 253) then continue dispatcher.
N 60350 Args: none (uses IX_dir and C_flags from fn_directional_interaction_dispatcher_using_pointer_table context).
N 60350 Returns: none.
N 60350 def direction_bit_1_blocked_path_handler():
N 60350 ↳fn_if_probed_cell_is_empty_mark(IX_ptr_slot=IX_dir, B_bit_clear_mask=0xFD, C_blocked_bits=C_flags)
N 60350 ↳jump(0xEB38)
@ 60358 label=direction_bit_2_blocked_path_handler
c 60358 direction_bit_2_blocked_path_handler
D 60358 Direction bit-2 blocked-path handler (mask with 251) then continue dispatcher.
N 60358 Args: none (uses IX_dir and C_flags from fn_directional_interaction_dispatcher_using_pointer_table context).
N 60358 Returns: none.
N 60358 def direction_bit_2_blocked_path_handler():
N 60358 ↳fn_if_probed_cell_is_empty_mark(IX_ptr_slot=IX_dir, B_bit_clear_mask=0xFB, C_blocked_bits=C_flags)
N 60358 ↳jump(0xEB46)
@ 60366 label=direction_bit_3_blocked_path_handler
c 60366 direction_bit_3_blocked_path_handler
D 60366 Direction bit-3 blocked-path handler (mask with 247) then continue dispatcher.
N 60366 Args: none (uses IX_dir and C_flags from fn_directional_interaction_dispatcher_using_pointer_table context).
N 60366 Returns: none.
N 60366 def direction_bit_3_blocked_path_handler():
N 60366 ↳fn_if_probed_cell_is_empty_mark(IX_ptr_slot=IX_dir, B_bit_clear_mask=0xF7, C_blocked_bits=C_flags)
N 60366 ↳jump(0xEB5E)
@ 60374 label=fn_if_probed_cell_is_empty_mark
c 60374 fn_if_probed_cell_is_empty_mark
D 60374 If probed cell is empty, mark it as code 27 and clear corresponding blocked bit in C.
N 60374 Args: IX_ptr_slot points to two-byte pointer [lo,hi] of probed map cell; B_bit_clear_mask is u8 mask; C_blocked_bits is u8 blocked-bit set.
N 60374 Returns: C_blocked_bits updated only when probed cell low6 code is 0x00.
N 60374 def fn_if_probed_cell_is_empty_mark(IX_ptr_slot, B_bit_clear_mask, C_blocked_bits):
N 60374 ↳HL_cell = read_u16_ix(IX_ptr_slot)
N 60374 ↳if (HL_cell[0x00] & 0x3F) != 0x00:
N 60374 ↳↳return C_blocked_bits
N 60374 ↳C_blocked_bits &= B_bit_clear_mask
N 60374 ↳HL_cell[0x00] = (HL_cell[0x00] & 0xC0) | 0x1B
N 60374 ↳return C_blocked_bits
@ 60395 label=fn_convert_map_pointer_hl_row_column
@ 60399 label=patch_pointer_to_rowcol_map_base
c 60395 fn_convert_map_pointer_hl_row_column
D 60395 Convert map pointer HL to row/column BC relative to map base 0x8000 and store into 0xA8DE.
N 60395 0xEBEF is the immediate word of LD DE,nn in this routine, patched by gameplay mode setup (0xF1BA/0xF1F1/0xF22B).
N 60395 Args: HL_cell is ptr_u8 map cell pointer.
N 60395 Returns: none.
N 60395 def fn_convert_map_pointer_hl_row_column(HL_cell):
N 60395 ↳HL_off = HL_cell - patch_pointer_to_rowcol_map_base
N 60395 ↳B_row = 0x00
N 60395 ↳while HL_off >= 0x0032:
N 60395 ↳↳HL_off -= 0x0032
N 60395 ↳↳B_row += 0x01
N 60395 ↳C_col = low_byte(HL_off)
N 60395 ↳var_current_map_coords = pack_u16(B_row, C_col)
@ 60426 label=autonomous_expansion_pass
c 60426 autonomous_expansion_pass
D 60426 Autonomous expansion pass: consume queue at 0xA8BC and append generated triplets into staging queue at 0xA8BE.
N 60426 Args: none.
N 60426 Returns: none.
N 60426 def autonomous_expansion_pass():
N 60426 ↳fn_main_gameplay_tick_updater()
N 60426 ↳DE_src = var_runtime_queue_head_3_ptr
N 60426 ↳HL_dst = var_runtime_queue_head_4_ptr
N 60426 ↳while True:
N 60426 ↳↳A_state = DE_src[0x00]
N 60426 ↳↳if A_state == 0xFF:
N 60426 ↳↳↳jump(0xECBA)
N 60426 ↳↳if A_state == 0x00:
N 60426 ↳↳↳DE_src += 0x03
N 60426 ↳↳↳continue
N 60426 ↳↳var_queue_state_scratch = A_state
N 60426 ↳↳HL_dst[0x00] = A_state
N 60426 ↳↳HL_dst[0x01] = DE_src[0x01]
N 60426 ↳↳HL_dst[0x02] = DE_src[0x02]
N 60426 ↳↳BC_cell = read_u16(HL_dst + 0x01)
N 60426 ↳↳A_spawn = fn_spawn_state_selector_xec0a(BC_cell=BC_cell, HL_out=HL_dst)
N 60426 ↳↳var_queue_source_ptr_scratch = DE_src
N 60426 ↳↳var_queue_write_ptr_scratch = HL_dst
N 60426 ↳↳HL_cell = BC_cell
N 60426 ↳↳HL_cell[0x00] = (HL_cell[0x00] & 0xC0) | A_spawn
N 60426 ↳↳fn_queue_insert_helper_xec0a(HL_cell=HL_cell + 0x0001)
N 60426 ↳↳fn_queue_insert_helper_xec0a(HL_cell=HL_cell - 0x0001)
N 60426 ↳↳fn_queue_insert_helper_xec0a(HL_cell=HL_cell - 0x0032)
N 60426 ↳↳fn_queue_insert_helper_xec0a(HL_cell=HL_cell + 0x0032)
N 60426 ↳↳HL_dst = var_queue_write_ptr_scratch + 0x0001
N 60426 ↳↳DE_src = var_queue_source_ptr_scratch + 0x0003
@ 60516 label=fn_queue_insert_helper_xec0a
c 60516 fn_queue_insert_helper_xec0a
D 60516 Queue insert helper for 0xEC0A: if candidate cell is empty, append [state,ptr] to staging queue and tag cell as code 25.
N 60516 Args: HL_cell is ptr_u8 candidate map cell; var_queue_write_ptr_scratch is current output cursor; var_queue_state_scratch is current entry state byte.
N 60516 Returns: none.
N 60516 def fn_queue_insert_helper_xec0a(HL_cell):
N 60516 ↳if (HL_cell[0x00] & 0x3F) != 0x00:
N 60516 ↳↳return
N 60516 ↳BC_cell = HL_cell
N 60516 ↳HL_out = var_queue_write_ptr_scratch
N 60516 ↳HL_out += 0x0001
N 60516 ↳HL_out[0x00] = var_queue_state_scratch
N 60516 ↳HL_out += 0x0001
N 60516 ↳HL_out[0x00] = low_byte(BC_cell)
N 60516 ↳HL_out += 0x0001
N 60516 ↳HL_out[0x00] = high_byte(BC_cell)
N 60516 ↳BC_cell[0x00] = (BC_cell[0x00] & 0xC0) | 0x19
N 60516 ↳fn_hud_triplet_increment_helper_bytes_xa8d8()
N 60516 ↳var_queue_write_ptr_scratch = HL_out
N 60516 ↳HL_cell = BC_cell
@ 60552 label=fn_spawn_state_selector_xec0a
c 60552 fn_spawn_state_selector_xec0a
D 60552 Spawn-state selector for 0xEC0A: default state 25; if candidate equals player cell, emit special states 33..36 based on player heading (0xA8C6).
N 60552 Args: BC_cell is ptr_u8 candidate cell; HL_out is ptr_u8 current output cursor in caller.
N 60552 Returns: A_spawn is u8 low6 code for candidate spawn encoding.
N 60552 def fn_spawn_state_selector_xec0a(BC_cell, HL_out):
N 60552 ↳if low_byte(var_runtime_current_cell_ptr_lo) != low_byte(BC_cell):
N 60552 ↳↳return 0x19
N 60552 ↳if high_byte(var_runtime_current_cell_ptr_lo) != high_byte(BC_cell):
N 60552 ↳↳return 0x19
N 60552 ↳HL_out -= 0x0003
N 60552 ↳fn_hud_triplet_decrement_helper_bytes_xa8d8()
N 60552 ↳A_step = low_byte(var_runtime_move_delta)
N 60552 ↳if A_step == 0xFF:
N 60552 ↳↳return 0x24
N 60552 ↳if A_step == 0x32:
N 60552 ↳↳return 0x21
N 60552 ↳if A_step == 0x01:
N 60552 ↳↳return 0x23
N 60552 ↳return 0x22
@ 60602 label=expansion_commit
c 60602 expansion_commit
D 60602 Expansion commit: rotate queue heads (0xA8B6..0xA8BE), run one gameplay tick, then retag queued cells by family codes (25/17/13/1).
N 60602 Args: HL_dst is ptr_u8 current staging tail slot; A_term is u8 record terminator (expected 0xFF) from autonomous_expansion_pass.
N 60602 Returns: none.
N 60602 def expansion_commit(HL_dst, A_term):
N 60602 ↳HL_dst[0x00] = A_term
N 60602 ↳HL_q4 = var_runtime_queue_head_4_ptr
N 60602 ↳DE_q0 = var_runtime_queue_head_0_lo
N 60602 ↳var_runtime_queue_head_0_lo = HL_q4
N 60602 ↳HL_q1 = var_runtime_queue_head_1_ptr
N 60602 ↳var_runtime_queue_head_1_ptr = DE_q0
N 60602 ↳DE_q2 = var_runtime_queue_head_2_ptr
N 60602 ↳var_runtime_queue_head_2_ptr = HL_q1
N 60602 ↳HL_q3 = var_runtime_queue_head_3_ptr
N 60602 ↳var_runtime_queue_head_3_ptr = DE_q2
N 60602 ↳var_runtime_queue_head_4_ptr = HL_q3
N 60602 ↳fn_main_gameplay_tick_updater()
N 60602 ↳fn_queue_retag_helper_one_list(HL_queue=var_runtime_queue_head_0_lo, E_code=0x19, D_xor=0x03)
N 60602 ↳fn_queue_retag_helper_one_list(HL_queue=var_runtime_queue_head_1_ptr, E_code=0x11, D_xor=0x00)
N 60602 ↳fn_queue_retag_helper_one_list(HL_queue=var_runtime_queue_head_2_ptr, E_code=0x0D, D_xor=0x00)
N 60602 ↳fn_queue_retag_helper_one_list(HL_queue=var_runtime_queue_head_3_ptr, E_code=0x01, D_xor=0x00)
@ 60673 label=fn_queue_retag_helper_one_list
c 60673 fn_queue_retag_helper_one_list
D 60673 Queue-retag helper over one list: rewrites low 6 bits of each queued cell code with optional E^D alternation.
N 60673 Args: HL_queue is ptr_u8 queue triplet stream [state, ptr_lo, ptr_hi] terminated by 0xFF in state; E_code is initial low6 code; D_xor is xor-mask for alternating codes.
N 60673 Returns: none.
N 60673 def fn_queue_retag_helper_one_list(HL_queue, E_code, D_xor):
N 60673 ↳while True:
N 60673 ↳↳A_state = HL_queue[0x00]
N 60673 ↳↳if A_state == 0xFF:
N 60673 ↳↳↳return
N 60673 ↳↳if A_state == 0x00:
N 60673 ↳↳↳HL_queue += 0x03
N 60673 ↳↳↳continue
N 60673 ↳↳BC_cell = read_u16(HL_queue + 0x01)
N 60673 ↳↳BC_cell[0x00] = (BC_cell[0x00] & 0xC0) | E_code
N 60673 ↳↳E_code ^= D_xor
N 60673 ↳↳HL_queue += 0x03
@ 60700 label=fn_main_gameplay_tick_updater
c 60700 fn_main_gameplay_tick_updater
D 60700 Main gameplay-tick updater: process entities/effects/UI then call map renderer 0xA38E.
N 60700 Args: none.
N 60700 Returns: none.
N 60700 def fn_main_gameplay_tick_updater():
N 60700 ↳for E_code in [0x26, 0x27, 0x28, 0x29]:
N 60700 ↳↳fn_main_gameplay_tick_update_core(E_code=E_code, D_xor=0x00)
@ 60719 label=fn_main_gameplay_tick_update_core
c 60719 fn_main_gameplay_tick_update_core
D 60719 Main gameplay-tick updater core entry (+0x13): shared phase used by level loop and transition branches.
N 60719 Args: E_code is u8 retag low6 code for this phase; D_xor is u8 xor-mask for retag helper (0 in normal calls).
N 60719 Returns: none.
N 60719 def fn_main_gameplay_tick_update_core(E_code, D_xor):
N 60719 ↳fn_queue_retag_helper_one_list(HL_queue=var_runtime_queue_head_0_lo, E_code=E_code, D_xor=D_xor)
N 60719 ↳fn_queue_retag_helper_one_list(HL_queue=var_runtime_queue_head_1_ptr, E_code=E_code, D_xor=D_xor)
N 60719 ↳fn_queue_retag_helper_one_list(HL_queue=var_runtime_queue_head_2_ptr, E_code=E_code, D_xor=D_xor)
N 60719 ↳fn_queue_retag_helper_one_list(HL_queue=var_runtime_queue_head_3_ptr, E_code=E_code, D_xor=D_xor)
N 60719 ↳rom_beeper(DE_ticks=0x001E, HL_period=0x00E6)
N 60719 ↳if var_runtime_objective_counter != 0x00:
N 60719 ↳↳fn_gameplay_movement_control_step()
N 60719 ↳fn_process_transient_effect_queues_handlers_xe530()
N 60719 ↳fn_patchable_callback_hook_frame_loop()
N 60719 ↳fn_directional_interaction_dispatcher_using_pointer_table()
N 60719 ↳fn_active_transient_effect_executor()
N 60719 ↳fn_main_pseudo_3d_map_render_pipeline()
N 60719 ↳rom_beeper(DE_ticks=0x0003, HL_period=0x00C8)
@ 60792 label=var_queue_source_ptr_scratch
b 60792 var_queue_source_ptr_scratch
D 60792 Scratch source-pointer pair used by object-queue walker at 0xEC0A.
D 60792 Structure: 16-bit scratch pointer [ptr_lo, ptr_hi] for queue walker.
@ 60794 label=fn_pre_action_overlay_painter_ui_area
c 60794 fn_pre_action_overlay_painter_ui_area
D 60794 Pre-action overlay painter on UI area (fills slanted strips using fill byte 18).
N 60794 Args: none.
N 60794 Returns: none.
N 60794 def fn_pre_action_overlay_painter_ui_area():
N 60794 ↳var_strip_fill_value = 0x12
N 60794 ↳HL_left = 0x5821
N 60794 ↳DE_right = 0x585A
N 60794 ↳for _ in range(0x1A):
N 60794 ↳↳fn_strip_fill_helper_xed7a_xed9a(HL_dst=HL_left, B_count=0x08)
N 60794 ↳↳fn_strip_fill_helper_xed7a_xed9a(HL_dst=DE_right, B_count=0x07)
N 60794 ↳↳HL_left += 0x01
N 60794 ↳↳DE_right -= 0x01
@ 60826 label=fn_post_action_overlay_painter_ui_area
c 60826 fn_post_action_overlay_painter_ui_area
D 60826 Post-action overlay painter on UI area (fills slanted strips using fill byte 57).
N 60826 Args: none.
N 60826 Returns: none.
N 60826 def fn_post_action_overlay_painter_ui_area():
N 60826 ↳var_strip_fill_value = 0x39
N 60826 ↳HL_left = 0x5841
N 60826 ↳DE_right = 0x583A
N 60826 ↳for _ in range(0x1A):
N 60826 ↳↳fn_strip_fill_helper_xed7a_xed9a(HL_dst=HL_left, B_count=0x07)
N 60826 ↳↳fn_strip_fill_helper_xed7a_xed9a(HL_dst=DE_right, B_count=0x08)
N 60826 ↳↳HL_left += 0x01
N 60826 ↳↳DE_right -= 0x01
@ 60858 label=fn_strip_fill_helper_xed7a_xed9a
c 60858 fn_strip_fill_helper_xed7a_xed9a
D 60858 Strip-fill helper used by 0xED7A/0xED9A (writes B bytes with current fill value 0xA8DD).
N 60858 Args: HL_dst is ptr_u8 stripe start; B_count is u8 row count; var_strip_fill_value provides fill byte.
N 60858 Returns: none.
N 60858 def fn_strip_fill_helper_xed7a_xed9a(HL_dst, B_count):
N 60858 ↳HL_row = HL_dst
N 60858 ↳A_fill = var_strip_fill_value
N 60858 ↳for _ in range(B_count):
N 60858 ↳↳HL_row[0x00] = A_fill
N 60858 ↳↳HL_row += 0x0040
N 60858 ↳HL_period = 0x0100 | low_byte(HL_row)
N 60858 ↳rom_beeper(DE_ticks=0x0006, HL_period=HL_period)
@ 60881 label=fn_patchable_callback_hook_frame_loop
c 60881 fn_patchable_callback_hook_frame_loop
D 60881 Patchable callback hook in frame loop (default RET; replaced at runtime by 0xEDD4 logic).
N 60881 Args: none.
N 60881 Returns: none.
N 60881 def fn_patchable_callback_hook_frame_loop():
N 60881 ↳return
b 60882 const_unresolved_constant_2b
D 60882 Unresolved 2-byte constant block adjacent to patchable callback routine 0xEDD1.
D 60882 Structure: unresolved 2-byte constant pair near patchable callback block.
@ 60884 label=patchable_frame_callback_body
c 60884 patchable_frame_callback_body
D 60884 Patchable frame-callback body: manages staged marker cycle, buffer scrubs, redraw trigger, and completion gate.
N 60884 Args: HL_cell is ptr_u8 marker/event cell pointer (when entered via patched hook at 0xEDD1, HL is loaded from var_marker_event_ptr).
N 60884 Returns: none.
N 60884 def patchable_frame_callback_body(HL_cell):
N 60884 ↳if ((var_marker_index_state + 0x2E) & 0xFF) == HL_cell[0x00]:
N 60884 ↳↳marker_advance_helper()
N 60884 ↳↳return
N 60884 ↳A_code = HL_cell[0x00]
N 60884 ↳if A_code < 0x21:
N 60884 ↳↳mem[0xEDD1] = 0xC9
N 60884 ↳↳return
N 60884 ↳if A_code >= 0x25:
N 60884 ↳↳mem[0xEDD1] = 0xC9
N 60884 ↳↳HL_sel = None
N 60884 ↳else:
N 60884 ↳↳A_idx = var_marker_index_state
N 60884 ↳↳if A_idx == 0x00:
N 60884 ↳↳↳HL_sel = var_marker_counters
N 60884 ↳↳elif A_idx == 0x01:
N 60884 ↳↳↳HL_sel = var_marker_counter_1
N 60884 ↳↳elif A_idx == 0x02:
N 60884 ↳↳↳HL_sel = var_marker_counter_2
N 60884 ↳↳elif A_idx == 0x03:
N 60884 ↳↳↳HL_sel = var_marker_counter_3
N 60884 ↳↳else:
N 60884 ↳↳↳HL_sel = var_marker_counter_4
N 60884 ↳↳if HL_sel[0x00] != 0x00:
N 60884 ↳↳↳mem[0xEDD1] = 0xC9
N 60884 ↳↳else:
N 60884 ↳↳↳HL_sel[0x00] = 0x01
N 60884 ↳↳↳rom_beeper(DE_ticks=0x0032, HL_period=0x0032)
N 60884 ↳↳↳rom_beeper(DE_ticks=0x0064, HL_period=0x0064)
N 60884 ↳↳↳fn_hud_decimal_counter_animator_core()
N 60884 ↳visible_cell_staging_preset_builder()
N 60884 ↳if var_marker_counters[0x00] == 0x00:
N 60884 ↳↳staging_buffer_scrub_entry_marker_value()
N 60884 ↳if var_marker_counters[0x01] == 0x00:
N 60884 ↳↳staging_buffer_scrub_entry_marker_value_2()
N 60884 ↳if var_marker_counters[0x02] == 0x00:
N 60884 ↳↳staging_buffer_scrub_entry_marker_value_3()
N 60884 ↳if var_marker_counters[0x03] == 0x00:
N 60884 ↳↳staging_buffer_scrub_entry_marker_value_4()
N 60884 ↳if var_marker_counters[0x04] == 0x00:
N 60884 ↳↳staging_buffer_scrub_entry_marker_value_5()
N 60884 ↳fn_two_pass_global_scrub_helper()
N 60884 ↳mem[0xEDD1] = 0xC9
N 60884 ↳fn_render_pass_re_entry_stub()
N 60884 ↳A_sum = sum(var_marker_counters[0x00:0x05])
N 60884 ↳if A_sum == 0x05:
N 60884 ↳↳all_markers_cleared_handler()
N 60884 ↳if A_sum != 0x00:
N 60884 ↳↳for _ in range(A_sum):
N 60884 ↳↳↳fn_hud_decimal_counter_animator_core()
N 60884 ↳↳↳rom_beeper(DE_ticks=0x0064, HL_period=0x00FA)
N 60884 ↳for _ in range(0x41):
N 60884 ↳↳halt_until_interrupt()
N 60884 Entry is patch-driven: hook at 0xEDD1 is runtime-modified to enter 0xEDD4 body; plus explicit direct call to internal entry 0xEDEE (+0x1A).
@ 61074 label=staging_buffer_scrub_entry_marker_value
c 61074 staging_buffer_scrub_entry_marker_value
D 61074 Staging-buffer scrub entry for marker value 1 (shared scanner at 0xEE8F).
N 61074 Args: none.
N 61074 Returns: A_status is 0x00 (from shared scanner return path).
N 61074 def staging_buffer_scrub_entry_marker_value():
N 61074 ↳fn_staging_buffer_scrub_marker_5_entry(A_marker=0x01)
N 61074 ↳return 0x00
@ 61079 label=staging_buffer_scrub_entry_marker_value_2
c 61079 staging_buffer_scrub_entry_marker_value_2
D 61079 Staging-buffer scrub entry for marker value 2 (shared scanner at 0xEE8F).
N 61079 Args: none.
N 61079 Returns: A_status is 0x00 (from shared scanner return path).
N 61079 def staging_buffer_scrub_entry_marker_value_2():
N 61079 ↳fn_staging_buffer_scrub_marker_5_entry(A_marker=0x02)
N 61079 ↳return 0x00
@ 61084 label=staging_buffer_scrub_entry_marker_value_3
c 61084 staging_buffer_scrub_entry_marker_value_3
D 61084 Staging-buffer scrub entry for marker value 3 (shared scanner at 0xEE8F).
N 61084 Args: none.
N 61084 Returns: A_status is 0x00 (from shared scanner return path).
N 61084 def staging_buffer_scrub_entry_marker_value_3():
N 61084 ↳fn_staging_buffer_scrub_marker_5_entry(A_marker=0x03)
N 61084 ↳return 0x00
@ 61088 label=staging_buffer_scrub_entry_marker_value_4
c 61088 staging_buffer_scrub_entry_marker_value_4
D 61088 Staging-buffer scrub entry for marker value 4 (shared scanner at 0xEE8F).
N 61088 Args: none.
N 61088 Returns: A_status is 0x00 (from fn_staging_buffer_scrub_marker_5_entry).
N 61088 def staging_buffer_scrub_entry_marker_value_4():
N 61088 ↳fn_staging_buffer_scrub_marker_5_entry(A_marker=0x04)
N 61088 ↳return 0x00
@ 61093 label=staging_buffer_scrub_entry_marker_value_5
c 61093 staging_buffer_scrub_entry_marker_value_5
D 61093 Staging-buffer scrub entry for marker value 5 (falls into shared scanner at 0xEE8F).
N 61093 Args: none.
N 61093 Returns: A_status is 0x00 (from fn_staging_buffer_scrub_marker_5_entry).
N 61093 def staging_buffer_scrub_entry_marker_value_5():
N 61093 ↳fn_staging_buffer_scrub_marker_5_entry(A_marker=0x05)
N 61093 ↳return 0x00
@ 61095 label=fn_staging_buffer_scrub_marker_5_entry
@ 61105 label=patch_scrub_scanner_call_condition_opcode
c 61095 fn_staging_buffer_scrub_marker_5_entry
D 61095 Staging-buffer scrub entry for marker value 5; falls into shared scanner loop at 0xEE8F.
N 61095 Args: A_marker is u8 marker value; patch_scrub_scanner_call_condition_opcode controls compare mode (CALL Z by default, CALL NZ in pass-1 scrub).
N 61095 Returns: A_status is 0x00; HL is restored to caller value.
N 61095 def fn_staging_buffer_scrub_marker_5_entry(A_marker):
N 61095 ↳HL_saved = HL
N 61095 ↳HL_cell = var_visible_cell_staging_lattice
N 61095 ↳BC_left = 0x021C
N 61095 ↳while BC_left != 0x0000:
N 61095 ↳↳A_cell = HL_cell[0x00]
N 61095 ↳↳if A_cell == A_marker:  # patched to != when opcode at 0xEEB1 is CALL NZ
N 61095 ↳↳↳scanner_write_helper(HL_cell=HL_cell)
N 61095 ↳↳HL_cell += 0x01
N 61095 ↳↳BC_left -= 0x0001
N 61095 ↳HL = HL_saved
N 61095 ↳return 0x00
@ 61118 label=scanner_write_helper
@ 61119 label=patch_scrub_scanner_write_value
c 61118 scanner_write_helper
D 61118 Scanner write helper: clear matched staging cell byte to 0.
N 61118 0xEEB1 (CALL condition opcode) and 0xEEBF (LD (HL),nn immediate) are runtime-patched by 0xEEC1 for two-pass scrub behavior.
N 61118 Args: HL_cell is ptr_u8 matched staging byte.
N 61118 Returns: none.
N 61118 def scanner_write_helper(HL_cell):
N 61118 ↳HL_cell[0x00] = patch_scrub_scanner_write_value
@ 61121 label=fn_two_pass_global_scrub_helper
c 61121 fn_two_pass_global_scrub_helper
D 61121 Two-pass global scrub helper: patch scanner thresholds, clear selected marks, then restore defaults.
N 61121 Args: none.
N 61121 Returns: none.
N 61121 def fn_two_pass_global_scrub_helper():
N 61121 ↳patch_scrub_scanner_write_value = 0x17
N 61121 ↳patch_scrub_scanner_call_condition_opcode = 0xC4  # CALL NZ
N 61121 ↳fn_staging_buffer_scrub_marker_5_entry(A_marker=0x00)
N 61121 ↳patch_scrub_scanner_call_condition_opcode = 0xCC  # CALL Z
N 61121 ↳patch_scrub_scanner_write_value = 0x00
@ 61145 label=marker_advance_helper
c 61145 marker_advance_helper
D 61145 Marker-advance helper: rotate active marker position in map when frame phase byte 0xA8C0 is zero.
N 61145 Args: none.
N 61145 Returns: none.
N 61145 def marker_advance_helper():
N 61145 ↳if var_runtime_phase_index != 0x00:
N 61145 ↳↳return
N 61145 ↳A_marker = var_marker_index_state + 0x01
N 61145 ↳if A_marker == 0x05:
N 61145 ↳↳A_marker = 0x00
N 61145 ↳var_marker_index_state = A_marker
N 61145 ↳HL_cell = var_marker_event_ptr
N 61145 ↳HL_cell[0x00] = A_marker + 0x2E
@ 61173 label=fn_hud_triplet_increment_helper_bytes_xa8d8
c 61173 fn_hud_triplet_increment_helper_bytes_xa8d8
D 61173 HUD triplet increment helper for bytes 0xA8D8..0xA8DA with digit redraw calls.
N 61173 Args: none.
N 61173 Returns: none.
N 61173 def fn_hud_triplet_increment_helper_bytes_xa8d8():
N 61173 ↳A_d0 = var_runtime_aux_c8_lo + 0x01
N 61173 ↳if A_d0 == 0x0A:
N 61173 ↳↳var_runtime_aux_c8_lo = 0x00
N 61173 ↳↳fn_hud_digit_blit_selector_3(A_digit=0x00)
N 61173 ↳↳A_d1 = var_runtime_aux_c8_hi + 0x01
N 61173 ↳↳if A_d1 == 0x0A:
N 61173 ↳↳↳var_runtime_aux_c8_hi = 0x00
N 61173 ↳↳↳fn_hud_digit_blit_selector_2(A_digit=0x00)
N 61173 ↳↳↳var_runtime_aux_ca += 0x01
N 61173 ↳↳↳fn_hud_digit_blit_selector(A_digit=var_runtime_aux_ca)
N 61173 ↳↳else:
N 61173 ↳↳↳var_runtime_aux_c8_hi = A_d1
N 61173 ↳↳↳fn_hud_digit_blit_selector_2(A_digit=A_d1)
N 61173 ↳else:
N 61173 ↳↳var_runtime_aux_c8_lo = A_d0
N 61173 ↳↳fn_hud_digit_blit_selector_3(A_digit=A_d0)
@ 61227 label=fn_hud_triplet_decrement_helper_bytes_xa8d8
c 61227 fn_hud_triplet_decrement_helper_bytes_xa8d8
D 61227 HUD triplet decrement helper for bytes 0xA8D8..0xA8DA with digit redraw calls.
N 61227 Args: none.
N 61227 Returns: none.
N 61227 def fn_hud_triplet_decrement_helper_bytes_xa8d8():
N 61227 ↳A_d0 = var_runtime_aux_c8_lo
N 61227 ↳if A_d0 != 0x00:
N 61227 ↳↳A_d0 -= 0x01
N 61227 ↳↳var_runtime_aux_c8_lo = A_d0
N 61227 ↳↳fn_hud_digit_blit_selector_3(A_digit=A_d0)
N 61227 ↳↳return
N 61227 ↳var_runtime_aux_c8_lo = 0x09
N 61227 ↳fn_hud_digit_blit_selector_3(A_digit=0x09)
N 61227 ↳A_d1 = var_runtime_aux_c8_hi
N 61227 ↳if A_d1 != 0x00:
N 61227 ↳↳A_d1 -= 0x01
N 61227 ↳↳var_runtime_aux_c8_hi = A_d1
N 61227 ↳↳fn_hud_digit_blit_selector_2(A_digit=A_d1)
N 61227 ↳↳return
N 61227 ↳var_runtime_aux_c8_hi = 0x09
N 61227 ↳fn_hud_digit_blit_selector_2(A_digit=0x09)
N 61227 ↳var_runtime_aux_ca = (var_runtime_aux_ca - 0x01) & 0xFF
N 61227 ↳fn_hud_digit_blit_selector(A_digit=var_runtime_aux_ca)
@ 61278 label=fn_hud_digit_blit_selector
c 61278 fn_hud_digit_blit_selector
D 61278 HUD digit blit selector: choose pattern group 0x101D and jump to shared draw path 0xEF70.
N 61278 Args: A_digit is u8 glyph/digit code.
N 61278 Returns: none.
N 61278 def fn_hud_digit_blit_selector(A_digit):
N 61278 ↳hud_digit_draw_core(A_digit=A_digit, B_row=0x10, C_col=0x1D)
@ 61284 label=fn_hud_digit_blit_selector_2
c 61284 fn_hud_digit_blit_selector_2
D 61284 HUD digit blit selector: choose pattern group 0x101E and jump to shared draw path 0xEF70.
N 61284 Args: A_digit is u8 glyph/digit code.
N 61284 Returns: none.
N 61284 def fn_hud_digit_blit_selector_2(A_digit):
N 61284 ↳hud_digit_draw_core(A_digit=A_digit, B_row=0x10, C_col=0x1E)
@ 61290 label=fn_hud_digit_blit_selector_3
c 61290 fn_hud_digit_blit_selector_3
D 61290 HUD digit blit selector: choose pattern group 0x101F and jump to shared draw path 0xEF70.
N 61290 Args: A_digit is u8 glyph/digit code.
N 61290 Returns: none.
N 61290 def fn_hud_digit_blit_selector_3(A_digit):
N 61290 ↳hud_digit_draw_core(A_digit=A_digit, B_row=0x10, C_col=0x1F)
@ 61296 label=hud_digit_draw_core
c 61296 hud_digit_draw_core
D 61296 Shared HUD digit draw core: map digit code A to glyph strip source and dispatch to blitter 0xEAA6 path.
N 61296 Args: A_digit is u8 glyph/digit code; B_row is u8 character-row index; C_col is u8 byte-column index.
N 61296 Returns: DE_src is advanced by 8 bytes by tail-call to fn_routine_8_byte_screen_blit_primitive.
N 61296 def hud_digit_draw_core(A_digit, B_row, C_col):
N 61296 ↳DE_src = 0x66BE + 0x08 * (A_digit + 0x11)
N 61296 ↳DE_src = fn_routine_8_byte_screen_blit_primitive(DE_src=DE_src, B_row=B_row, C_col=C_col)
N 61296 ↳return DE_src
@ 61315 label=visible_cell_staging_preset_builder
c 61315 visible_cell_staging_preset_builder
D 61315 Visible-cell staging preset builder: clear 0x89C6.. and stamp template patterns from table 0xEFE7.
N 61315 Args: none.
N 61315 Returns: none.
N 61315 def visible_cell_staging_preset_builder():
N 61315 ↳fn_visible_cell_staging_preset_core(IX_tpl=const_staging_template_byte_table)
@ 61319 label=fn_visible_cell_staging_preset_core
c 61319 fn_visible_cell_staging_preset_core
D 61319 Visible-cell staging preset builder core entry (+0x4): initializes staged cell pattern descriptors.
N 61319 Args: IX_tpl points to source template byte stream (array_u8[95], 5 row chunks x 19 bytes).
N 61319 Returns: none.
N 61319 def fn_visible_cell_staging_preset_core(IX_tpl):
N 61319 ↳var_visible_cell_staging_lattice[:0x024A] = [0x00] * 0x024A
N 61319 ↳A_phase = 0x10
N 61319 ↳HL_dst, IX_tpl, A_phase = fn_visible_cell_staging_emit_pair_loop(HL_dst=0x8B47, IX_tpl=IX_tpl, A_phase=A_phase)
N 61319 ↳HL_dst, IX_tpl, A_phase = fn_visible_cell_staging_emit_pair_loop(HL_dst=0x8B58, IX_tpl=IX_tpl, A_phase=A_phase)
N 61319 ↳HL_dst, IX_tpl, A_phase = fn_visible_cell_staging_emit_pair_loop(HL_dst=0x8B68, IX_tpl=IX_tpl, A_phase=A_phase)
N 61319 ↳HL_dst, IX_tpl, A_phase = fn_visible_cell_staging_emit_pair_loop(HL_dst=0x8B79, IX_tpl=IX_tpl, A_phase=A_phase)
N 61319 ↳fn_visible_cell_staging_emit_pair_loop(HL_dst=0x8B89, IX_tpl=IX_tpl, A_phase=A_phase)
@ 61362 label=fn_visible_cell_staging_emit_pair_loop
c 61362 fn_visible_cell_staging_emit_pair_loop
D 61362 Visible-cell staging emit-pair loop entry (+0x2F): writes repeated cell-pair descriptors to staging buffer.
N 61362 Args: HL_dst is ptr_u8 staging destination; IX_tpl is ptr_u8 template stream; A_phase is u8 alternating stride seed (0x10/0x0F).
N 61362 Returns: HL_dst, IX_tpl, and A_phase advanced for chained row-emitter calls.
N 61362 def fn_visible_cell_staging_emit_pair_loop(HL_dst, IX_tpl, A_phase):
N 61362 ↳for _ in range(0x13):
N 61362 ↳↳HL_dst[0x00] = IX_tpl[0x00]
N 61362 ↳↳A_phase ^= 0x1F
N 61362 ↳↳HL_dst -= A_phase
N 61362 ↳↳IX_tpl += 1
N 61362 ↳return HL_dst, IX_tpl, A_phase
@ 61383 label=all_markers_cleared_handler
c 61383 all_markers_cleared_handler
D 61383 All-markers-cleared handler: reset marker counters, increment 0xA8C5, and refresh HUD/event strip.
N 61383 Args: none.
N 61383 Returns: none.
N 61383 def all_markers_cleared_handler():
N 61383 ↳var_marker_counters[:0x05] = [0x00] * 0x05
N 61383 ↳rom_beeper(DE_ticks=0x00C8, HL_period=0x00FA)
N 61383 ↳var_runtime_objective_counter += 0x01
N 61383 ↳fn_hud_strip_painter()
@ 61415 label=const_staging_template_byte_table
b 61415 const_staging_template_byte_table
D 61415 Template byte table for visible-cell staging preset builder 0xEF83.
D 61415 Structure: template payload table of 5 groups x 19 bytes (95 bytes) consumed by 0xEF83/0xEF9B.
b 61510 const_staging_template_padding
D 61510 Template-table tail padding after active 95-byte payload.
D 61510 Structure: 10-byte zero padding tail (0xF046-0xF04F), outside current copy loop.
@ 61520 label=fn_periodic_scheduler_tick
@ 61539 label=patch_scheduler_script_base_ptr
c 61520 fn_periodic_scheduler_tick
D 61520 Periodic scheduler tick: decrements frame counter at 0xA8CD; on wrap executes scripted events (calls 0xF0C5 and optional 0xF519).
N 61520 0xF063 is the BC immediate word in this routine (scheduler script base), patched by gameplay mode presets (0xF1B0/0xF1E7/0xF20E).
N 61520 Args: none.
N 61520 Returns: none.
N 61520 def fn_periodic_scheduler_tick():
N 61520 ↳HL_timer = var_runtime_scheduler_timer_lo
N 61520 ↳HL_timer -= 0x0002
N 61520 ↳var_runtime_scheduler_timer_lo = HL_timer
N 61520 ↳if low_byte(HL_timer) != 0xFF:
N 61520 ↳↳return
N 61520 ↳A_step = high_byte(HL_timer)
N 61520 ↳HL_meter = 0x5A85 + A_step
N 61520 ↳BC_script = patch_scheduler_script_base_ptr + A_step
N 61520 ↳A_mask = BC_script[0x00]
N 61520 ↳const_periodic_scheduler_script[0x00] = A_mask
N 61520 ↳HL_meter[0x00] = 0x00
N 61520 ↳if A_mask & 0x01:
N 61520 ↳↳scheduler_triggered_autonomous_step()
N 61520 ↳if A_mask & 0x02:
N 61520 ↳↳scheduler_triggered_marker_seeding()
@ 61567 label=const_periodic_scheduler_script
b 61567 const_periodic_scheduler_script
D 61567 Periodic scheduler script bytes for 0xF050: bit0 triggers autonomous expansion tick (0xF0C5), bit1 triggers marker-seeding transition path (0xF519).
D 61567 Structure: byte-coded scheduler script table; each byte is a bitfield action mask.
@ 61568 label=const_periodic_scheduler_step_2
@ 61591 label=const_periodic_scheduler_step_3
@ 61614 label=const_periodic_scheduler_step_4
@ 61637 label=scheduler_triggered_autonomous_step
c 61637 scheduler_triggered_autonomous_step
D 61637 Scheduler-triggered autonomous step: run 0xEC0A expansion and rebalance transient queue counters before HUD refresh.
N 61637 Args: none.
N 61637 Returns: none.
N 61637 def scheduler_triggered_autonomous_step():
N 61637 ↳autonomous_expansion_pass()
N 61637 ↳if var_runtime_aux_ca != 0x00:
N 61637 ↳↳E_bias = 0x0A
N 61637 ↳else:
N 61637 ↳↳E_bias = var_runtime_aux_c8_hi
N 61637 ↳fn_counter_rebalance_helper(HL_entries=var_transient_queue_a_entries, E_bias=E_bias)
N 61637 ↳fn_counter_rebalance_helper(HL_entries=var_transient_queue_c_entries, E_bias=E_bias)
N 61637 ↳fn_counter_rebalance_helper(HL_entries=var_transient_queue_b_entries, E_bias=E_bias)
N 61637 ↳fn_rebuild_hud_meter_bars_counters_xa8c4()
@ 61677 label=fn_counter_rebalance_helper
c 61677 fn_counter_rebalance_helper
D 61677 Counter rebalance helper: count free slots in a 10-entry transient list and clamp/update its leading counter byte.
N 61677 Args: HL_entries is ptr_u8 to first state byte of a 10-entry triplet list; E_bias is u8 addend.
N 61677 Returns: none.
N 61677 def fn_counter_rebalance_helper(HL_entries, E_bias):
N 61677 ↳HL_scan = HL_entries
N 61677 ↳D_free = 0x00
N 61677 ↳for _ in range(0x0A):
N 61677 ↳↳if HL_scan[0x00] == 0x00:
N 61677 ↳↳↳D_free += 0x01
N 61677 ↳↳HL_scan += 0x03
N 61677 ↳A_target = HL_entries[-0x01] + E_bias
N 61677 ↳HL_entries[-0x01] = A_target if A_target < D_free else D_free
@ 61704 label=fn_hud_strip_painter
c 61704 fn_hud_strip_painter
D 61704 HUD strip painter: clear two 12-cell rows and draw up to six progress indicators from counter 0xA8C5.
N 61704 Args: none.
N 61704 Returns: none.
N 61704 def fn_hud_strip_painter():
N 61704 ↳HL_top = 0x5A33
N 61704 ↳for _ in range(0x0C):
N 61704 ↳↳HL_top[0x00] = 0x00
N 61704 ↳↳HL_top += 0x01
N 61704 ↳HL_bottom = HL_top + 0x001F
N 61704 ↳for _ in range(0x0C):
N 61704 ↳↳HL_bottom[0x00] = 0x00
N 61704 ↳↳HL_bottom -= 0x01
N 61704 ↳A_steps = var_runtime_objective_counter
N 61704 ↳if A_steps == 0x00:
N 61704 ↳↳return
N 61704 ↳if A_steps >= 0x07:
N 61704 ↳↳A_steps = progress_clamp_helper(A_progress=A_steps)
N 61704 ↳for A_step in range(A_steps, 0x00, -0x01):
N 61704 ↳↳fn_single_progress_step_painter(A_step=A_step)
@ 61743 label=progress_clamp_helper
c 61743 progress_clamp_helper
D 61743 Progress clamp helper: returns A=6 for values >=7 before indicator draw loop.
N 61743 Args: A_progress is u8 progress count (caller enters only when A_progress >= 0x07).
N 61743 Returns: A_progress clamped to 0x06.
N 61743 def progress_clamp_helper(A_progress):
N 61743 ↳return 0x06
@ 61746 label=fn_single_progress_step_painter
c 61746 fn_single_progress_step_painter
D 61746 Single progress-step painter: writes a 2x2 indicator pair into HUD rows using attributes 5/7.
N 61746 Args: A_step is u8 1-based indicator index from HUD loop.
N 61746 Returns: none.
N 61746 def fn_single_progress_step_painter(A_step):
N 61746 ↳HL_cell = 0x5A31 + (A_step << 0x01)
N 61746 ↳HL_cell[0x00] = 0x05
N 61746 ↳HL_cell[0x01] = 0x05
N 61746 ↳HL_cell[0x20] = 0x07
N 61746 ↳HL_cell[0x21] = 0x07
@ 61769 label=fn_scenario_preset_beeper_stream_engine
c 61769 fn_scenario_preset_beeper_stream_engine
D 61769 Scenario preset A for beeper stream engine: used by pre-level intro and ending tail, then enters common driver at 0xFBCC.
N 61769 Args: none.
N 61769 Returns: none.
N 61769 def fn_scenario_preset_beeper_stream_engine():
N 61769 ↳scenario_pointer_seeding_core(HL_stream_a=const_scenario_preset_a_stream_1, DE_stream_b=const_scenario_preset_a_stream_2)
@ 61778 label=fn_scenario_preset_b_beeper_stream_engine
c 61778 fn_scenario_preset_b_beeper_stream_engine
D 61778 Scenario preset B for beeper stream engine: front-end/menu music script preset, then enters common driver at 0xFBCC.
N 61778 Args: none.
N 61778 Returns: none.
N 61778 def fn_scenario_preset_b_beeper_stream_engine():
N 61778 ↳scenario_pointer_seeding_core(HL_stream_a=const_scenario_preset_b_stream_1, DE_stream_b=const_scenario_preset_b_stream_2)
@ 61787 label=fn_scenario_preset_c
c 61787 fn_scenario_preset_c
D 61787 Scenario preset C (used by failure/cleanup return path): seed pointer pair and enter common beeper stream driver at 0xFBCC.
N 61787 Args: none.
N 61787 Returns: none.
N 61787 def fn_scenario_preset_c():
N 61787 ↳scenario_pointer_seeding_core(HL_stream_a=const_scenario_preset_c_stream_1, DE_stream_b=const_scenario_preset_c_stream_2)
@ 61793 label=scenario_pointer_seeding_core
c 61793 scenario_pointer_seeding_core
D 61793 Shared scenario pointer-seeding core: stores HL/DE (+1) into stream-state slots and jumps to stream driver 0xFBCC.
N 61793 Args: HL_stream_a is ptr_u8 stream-A start; DE_stream_b is ptr_u8 stream-B start.
N 61793 Returns: none.
N 61793 def scenario_pointer_seeding_core(HL_stream_a, DE_stream_b):
N 61793 ↳patch_stream_player_default_stream_a_ptr = HL_stream_a
N 61793 ↳var_stream_ptr_b_lo = HL_stream_a + 0x0001
N 61793 ↳patch_stream_player_default_stream_b_ptr = DE_stream_b
N 61793 ↳var_stream_ptr_d_lo = DE_stream_b + 0x0001
N 61793 ↳scenario_intermission_beeper_stream_player_loop()
@ 61812 label=gameplay_session_controller
c 61812 gameplay_session_controller
D 61812 Gameplay session controller: performs level/session setup, then runs the per-frame main loop at 0xF23D.
N 61812 Args: none.
N 61812 Returns: none.
N 61812 def gameplay_session_controller():
N 61812 ↳gameplay_screen_setup()
N 61812 ↳fn_overlay_preset_selector()
N 61812 ↳var_runtime_scheduler_timer_lo = 0x01
N 61812 ↳var_runtime_scheduler_timer_hi = 0x16
N 61812 ↳var_runtime_progress_counter = 0x0A
N 61812 ↳var_runtime_direction_mask = 0x00
N 61812 ↳mem[fn_patchable_callback_hook_frame_loop] = 0xC9
N 61812 ↳mem[var_transient_queue_a:var_transient_effect_state] = 0x00
N 61812 ↳fn_rebuild_hud_meter_bars_counters_xa8c4()
N 61812 ↳if var_active_map_mode == 0x00:
N 61812 ↳↳patch_scheduler_script_base_ptr = const_periodic_scheduler_step_4
N 61812 ↳↳var_runtime_objective_counter = 0x06
N 61812 ↳↳patch_queue_1_block_threshold_code = 0x50
N 61812 ↳↳patch_queue_2_block_threshold_code = 0x50
N 61812 ↳↳patch_queue_3_block_threshold_code = 0x50
N 61812 ↳↳patch_queue_3_fallback_threshold_code = 0x50
N 61812 ↳↳patch_player_rowcol_map_base_offset = 0x8000
N 61812 ↳↳patch_pointer_to_rowcol_map_base = 0x8000
N 61812 ↳↳patch_queue_3_contact_branch_opcode = 0xC9
N 61812 ↳↳fn_map_mode_setup_helper(DE_map=var_level_map_mode_0)
N 61812 ↳elif var_active_map_mode == 0x01:
N 61812 ↳↳patch_scheduler_script_base_ptr = const_periodic_scheduler_step_3
N 61812 ↳↳patch_player_rowcol_map_base_offset = 0x32E2
N 61812 ↳↳patch_pointer_to_rowcol_map_base = 0x32E2
N 61812 ↳↳patch_queue_3_contact_branch_opcode = 0xC5
N 61812 ↳↳fn_map_mode_setup_helper(DE_map=var_level_map_mode_1)
N 61812 ↳↳fn_active_map_mode_switch_entry_b()
N 61812 ↳↳fn_overlay_preset_b_selector()
N 61812 ↳↳patch_queue_1_block_threshold_code = 0x50
N 61812 ↳↳patch_queue_2_block_threshold_code = 0x25
N 61812 ↳↳patch_queue_3_block_threshold_code = 0x17
N 61812 ↳↳patch_queue_3_fallback_threshold_code = 0x17
N 61812 ↳else:
N 61812 ↳↳patch_scheduler_script_base_ptr = const_periodic_scheduler_step_2
N 61812 ↳↳patch_player_rowcol_map_base_offset = 0x291E
N 61812 ↳↳patch_pointer_to_rowcol_map_base = 0x291E
N 61812 ↳↳patch_queue_3_contact_branch_opcode = 0xC5
N 61812 ↳↳fn_map_mode_setup_helper(DE_map=var_level_map_mode_2)
N 61812 ↳↳fn_active_map_mode_switch_entry_a()
N 61812 ↳↳fn_overlay_preset_c_selector()
N 61812 ↳↳patch_queue_1_block_threshold_code = 0x17
N 61812 ↳↳patch_queue_2_block_threshold_code = 0x25
N 61812 ↳↳patch_queue_3_block_threshold_code = 0x17
N 61812 ↳↳patch_queue_3_fallback_threshold_code = 0x17
N 61812 ↳fn_scenario_preset_beeper_stream_engine()
N 61812 ↳while True:
N 61812 ↳↳per_frame_object_state_update_pass()
N 61812 ↳↳fn_process_transient_effect_queues_handlers_xe530()
N 61812 ↳↳fn_gameplay_movement_control_step()
N 61812 ↳↳fn_directional_interaction_dispatcher_using_pointer_table()
N 61812 ↳↳fn_patchable_callback_hook_frame_loop()
N 61812 ↳↳fn_periodic_scheduler_tick()
N 61812 ↳↳fn_main_pseudo_3d_map_render_pipeline()
N 61812 ↳↳if var_runtime_progress_byte_0 == 0x00 and var_runtime_progress_byte_1 == 0x00 and var_runtime_progress_byte_2 == 0x00:
N 61812 ↳↳↳main_loop_level_complete_transition_path()
N 61812 ↳↳if var_runtime_scheduler_timer_hi == 0x00:
N 61812 ↳↳↳main_loop_failure_cleanup_exit_path()
N 61812 ↳↳if var_runtime_objective_counter == 0x00:
N 61812 ↳↳↳main_loop_failure_cleanup_exit_path()
@ 62069 label=fn_map_mode_setup_helper
c 62069 fn_map_mode_setup_helper
D 62069 Map-mode setup helper: save active map base pointer, build sparse object list, then initialize runtime pointers.
N 62069 Args: DE_map is ptr_u8 active map base (mode0/1/2).
N 62069 Returns: none.
N 62069 def fn_map_mode_setup_helper(DE_map):
N 62069 ↳var_active_map_base_ptr = DE_map
N 62069 ↳fn_scan_2500_byte_map_emit_selected(DE_map=DE_map)
N 62069 ↳initialize_gameplay_runtime_structures_pointers_map()  # ASM tail-jump (JP 0xF2F4)
@ 62079 label=fn_map_normalization_restore
c 62079 fn_map_normalization_restore
D 62079 Map normalization+restore: compact map bytes via 0xF292, then replay saved object triplets from 0xB734.
N 62079 Args: HL_map is ptr_u8 active 2500-byte map base.
N 62079 Returns: none.
N 62079 def fn_map_normalization_restore(HL_map):
N 62079 ↳normalize_2500_byte_map_place(HL_map=HL_map)
N 62079 ↳HL_log = var_saved_map_triplet_buffer
N 62079 ↳while True:
N 62079 ↳↳A_cell = HL_log[0x00]
N 62079 ↳↳if A_cell == 0xFF:
N 62079 ↳↳↳return
N 62079 ↳↳HL_cell = HL_log[0x01] | (HL_log[0x02] << 0x08)
N 62079 ↳↳HL_cell[0x00] = A_cell
N 62079 ↳↳HL_log += 0x03
@ 62098 label=normalize_2500_byte_map_place
c 62098 normalize_2500_byte_map_place
D 62098 Normalize 2500-byte map in-place: keep wall-profile full bytes (0x17/0x57/0x97/0xD7), otherwise collapse to high2 render-profile bits.
N 62098 Args: HL_map is ptr_u8 map base of a 2500-byte level buffer.
N 62098 Returns: none.
N 62098 def normalize_2500_byte_map_place(HL_map):
N 62098 ↳for i in range(0x09C4):
N 62098 ↳↳A_cell = HL_map[i]
N 62098 ↳↳if A_cell in [0x17, 0x57, 0x97, 0xD7]:
N 62098 ↳↳↳continue
N 62098 ↳↳A_hi = A_cell & 0xC0
N 62098 ↳↳if A_hi == 0x00:
N 62098 ↳↳↳HL_map[i] = 0x00
N 62098 ↳↳elif A_hi == 0xC0:
N 62098 ↳↳↳continue  # keep original full byte when high2==0xC0
N 62098 ↳↳else:
N 62098 ↳↳↳HL_map[i] = A_hi
@ 62139 label=fn_scan_2500_byte_map_emit_selected
c 62139 fn_scan_2500_byte_map_emit_selected
D 62139 Scan 2500-byte map and emit selected cell codes with pointers into list buffer at 0xB734.
N 62139 Args: DE_map is ptr_u8 map base of a 2500-byte level buffer.
N 62139 Returns: none.
N 62139 def fn_scan_2500_byte_map_emit_selected(DE_map):
N 62139 ↳HL_out = var_saved_map_triplet_buffer
N 62139 ↳for _ in range(0x09C4):
N 62139 ↳↳A_low6 = DE_map[0x00] & 0x3F
N 62139 ↳↳if A_low6 in [0x01, 0x0D, 0x11, 0x18, 0x19, 0x1B, 0x21]:
N 62139 ↳↳↳HL_out[0x00] = DE_map[0x00]
N 62139 ↳↳↳HL_out[0x01] = low_byte(DE_map)
N 62139 ↳↳↳HL_out[0x02] = high_byte(DE_map)
N 62139 ↳↳↳HL_out[0x03] = 0xFF  # keep live terminator after last emitted triplet
N 62139 ↳↳↳HL_out += 0x03
N 62139 ↳↳DE_map += 0x01
@ 62194 label=var_active_map_base_ptr
b 62194 var_active_map_base_ptr
D 62194 Active map-base pointer storage at 0xF2F2 (written by 0xF255, consumed by map search helpers).
D 62194 Structure: 16-bit active map base pointer [base_lo, base_hi].
@ 62196 label=initialize_gameplay_runtime_structures_pointers_map
@ 62343 label=patch_player_rowcol_map_base_offset
c 62196 initialize_gameplay_runtime_structures_pointers_map
D 62196 Initialize gameplay runtime structures/pointers from current map (object lists, counters, seed positions).
N 62196 Args: none.
N 62196 Returns: none.
N 62196 def initialize_gameplay_runtime_structures_pointers_map():
N 62196 ↳write_u16(var_runtime_queue_head_0_lo, var_runtime_object_queue_0)
N 62196 ↳write_u16(var_runtime_queue_head_1_ptr, var_runtime_object_queue_1)
N 62196 ↳write_u16(var_runtime_queue_head_2_ptr, var_runtime_object_queue_2)
N 62196 ↳write_u16(var_runtime_queue_head_3_ptr, var_runtime_object_queue_3)
N 62196 ↳write_u16(var_runtime_queue_head_4_ptr, var_runtime_object_queue_4)
N 62196 ↳var_runtime_aux_c8_lo = 0x04
N 62196 ↳var_runtime_aux_c8_hi = 0x00
N 62196 ↳var_runtime_aux_ca = 0x00
N 62196 ↳var_transient_effect_state = 0x00
N 62196 ↳fn_hud_digit_blit_selector(A_digit=0x00)
N 62196 ↳fn_hud_digit_blit_selector_2(A_digit=0x00)
N 62196 ↳fn_hud_digit_blit_selector_3(A_digit=0x04)
N 62196 ↳fn_clear_transient_object_queues_xc5b2()
N 62196 ↳HL_cell = fn_find_first_occurrence_cell_code_d(D_code=0x01)
N 62196 ↳var_runtime_object_queue_0[0x00] = 0x01
N 62196 ↳var_runtime_object_queue_1[0x00] = 0x01
N 62196 ↳var_runtime_object_queue_2[0x00] = 0x01
N 62196 ↳var_runtime_object_queue_3[0x00] = 0x01
N 62196 ↳write_u16(var_runtime_object_queue_3_entries, HL_cell)
N 62196 ↳write_u16(var_runtime_object_queue_2_entries, fn_find_first_occurrence_cell_code_d(D_code=0x0D))
N 62196 ↳write_u16(var_runtime_object_queue_1_entries, fn_find_first_occurrence_cell_code_d(D_code=0x11))
N 62196 ↳write_u16(var_runtime_object_queue_0_entries, fn_find_first_occurrence_cell_code_d(D_code=0x19))
N 62196 ↳HL_ptr = fn_find_first_occurrence_cell_code_d(D_code=0x1B)
N 62196 ↳write_u16(var_runtime_dir_ptr_up, HL_ptr)
N 62196 ↳HL_ptr = fn_find_first_cell_code_in_map_loop(HL_scan=HL_ptr + 0x01, D_code=0x1B)
N 62196 ↳write_u16(var_runtime_dir_ptr_down, HL_ptr)
N 62196 ↳HL_ptr = fn_find_first_cell_code_in_map_loop(HL_scan=HL_ptr + 0x01, D_code=0x1B)
N 62196 ↳write_u16(var_runtime_dir_ptr_right, HL_ptr)
N 62196 ↳HL_ptr = fn_find_first_cell_code_in_map_loop(HL_scan=HL_ptr + 0x01, D_code=0x1B)
N 62196 ↳write_u16(var_runtime_dir_ptr_left, HL_ptr)
N 62196 ↳var_runtime_direction_mask = 0x00
N 62196 ↳HL_cell = fn_find_first_occurrence_cell_code_d(D_code=0x21)
N 62196 ↳write_u16(var_runtime_current_cell_ptr_lo, HL_cell)
N 62196 ↳HL_idx = (HL_cell + imm16_at(patch_player_rowcol_map_base_offset)) & 0xFFFF
N 62196 ↳B_row = 0x00
N 62196 ↳while HL_idx >= 0x0032:
N 62196 ↳↳HL_idx -= 0x0032
N 62196 ↳↳B_row = (B_row + 0x01) & 0xFF
N 62196 ↳var_current_map_coords = (B_row, low_byte(HL_idx))
N 62196 ↳var_runtime_move_delta = 0x00
N 62196 ↳var_runtime_move_state_code = 0x1C
N 62196 ↳# NOTE: patch_player_rowcol_map_base_offset (0xF387) is a self-modified immediate set per active map mode.
@ 62380 label=fn_find_first_occurrence_cell_code_d
c 62380 fn_find_first_occurrence_cell_code_d
D 62380 Find first occurrence of cell code D in current 2500-byte map (base from 0xF2F2).
N 62380 Args: D_code is u8 target low6 map-cell code.
N 62380 Returns: HL_cell points to first match, else first byte after exhausted scan window.
N 62380 def fn_find_first_occurrence_cell_code_d(D_code):
N 62380 ↳HL_scan = var_active_map_base_ptr
N 62380 ↳HL_scan = fn_find_first_cell_code_in_map_loop(HL_scan=HL_scan, D_code=D_code)
N 62380 ↳return HL_scan
@ 62383 label=fn_find_first_cell_code_in_map_loop
c 62383 fn_find_first_cell_code_in_map_loop
D 62383 Map-scan loop entry (+0x3): find first occurrence of code D in active 2500-byte map.
N 62383 Args: HL_scan is ptr_u8 scan cursor; D_code is u8 target low6 cell code.
N 62383 Returns: HL_scan points to first matching cell or first byte after exhausted scan window.
N 62383 def fn_find_first_cell_code_in_map_loop(HL_scan, D_code):
N 62383 ↳for _ in range(0x09C4):
N 62383 ↳↳if (HL_scan[0x00] & 0x3F) == D_code:
N 62383 ↳↳↳return HL_scan
N 62383 ↳↳HL_scan += 0x01
N 62383 ↳return HL_scan
@ 62398 label=fn_clear_transient_object_queues_xc5b2
c 62398 fn_clear_transient_object_queues_xc5b2
D 62398 Clear transient object queues at 0xC5B2.. (1900 bytes filled with 255).
N 62398 Args: none.
N 62398 Returns: none.
N 62398 def fn_clear_transient_object_queues_xc5b2():
N 62398 ↳var_runtime_object_queue_0[0x00:0x076C] = 0xFF
@ 62413 label=fn_rectangular_panel_fill_helper
c 62413 fn_rectangular_panel_fill_helper
D 62413 Rectangular panel fill helper: paint 15x26 area at 0x5821 with value A, then run pacing routine 0xF4B5.
N 62413 Args: A_fill is u8 attribute fill value.
N 62413 Returns: none.
N 62413 def fn_rectangular_panel_fill_helper(A_fill):
N 62413 ↳HL_row = 0x5821
N 62413 ↳for _ in range(0x0F):
N 62413 ↳↳for _ in range(0x1A):
N 62413 ↳↳↳HL_row[0x00] = A_fill
N 62413 ↳↳↳HL_row += 0x01
N 62413 ↳↳HL_row += 0x06
N 62413 ↳fn_paced_beeper_helper_transitions_panel_fill()
@ 62437 label=fn_active_map_mode_switch_handler
c 62437 fn_active_map_mode_switch_handler
D 62437 Active map-mode switch handler (0xF41A): restore selected map/state and swap level-specific sprite subset banks.
N 62437 Args: none.
N 62437 Returns: none.
N 62437 def fn_active_map_mode_switch_handler():
N 62437 ↳if var_active_map_mode == 0x00:
N 62437 ↳↳fn_map_normalization_restore(HL_map=var_level_map_mode_0)
N 62437 ↳↳return
N 62437 ↳if var_active_map_mode == 0x01:
N 62437 ↳↳fn_map_normalization_restore(HL_map=var_level_map_mode_1)
N 62437 ↳↳fn_active_map_mode_switch_entry_b()
N 62437 ↳else:
N 62437 ↳↳fn_map_normalization_restore(HL_map=var_level_map_mode_2)
N 62437 ↳↳fn_active_map_mode_switch_entry_a()
@ 62472 label=fn_active_map_mode_switch_entry_a
c 62472 fn_active_map_mode_switch_entry_a
D 62472 Active map-mode switch secondary entry A (+0x23): branch used by gameplay setup path.
N 62472 Args: none.
N 62472 Returns: none.
N 62472 def fn_active_map_mode_switch_entry_a():
N 62472 ↳sprite_bank_swap_core(HL_active_bank=var_active_sprite_subset_bank, DE_selected_bank=const_sprite_subset_bank_b)
@ 62481 label=fn_active_map_mode_switch_entry_b
c 62481 fn_active_map_mode_switch_entry_b
D 62481 Active map-mode switch secondary entry B (+0x2C): branch used by alternate setup path.
N 62481 Args: none.
N 62481 Returns: none.
N 62481 def fn_active_map_mode_switch_entry_b():
N 62481 ↳sprite_bank_swap_core(HL_active_bank=var_active_sprite_subset_bank, DE_selected_bank=const_sprite_subset_bank_a)
@ 62490 label=sprite_bank_swap_core
c 62490 sprite_bank_swap_core
D 62490 Sprite-bank swap core: exchange 1664 bytes between active window 0xA8F2.. and selected level bank.
N 62490 Args: HL_active_bank is ptr_u8 active 26x64-byte sprite window; DE_selected_bank is ptr_u8 selected bank (A/B).
N 62490 Returns: none.
N 62490 def sprite_bank_swap_core(HL_active_bank, DE_selected_bank):
N 62490 ↳for i in range(0x0680):
N 62490 ↳↳tmp = HL_active_bank[i]
N 62490 ↳↳HL_active_bank[i] = DE_selected_bank[i]
N 62490 ↳↳DE_selected_bank[i] = tmp
@ 62507 label=main_loop_failure_cleanup_exit_path
c 62507 main_loop_failure_cleanup_exit_path
D 62507 Main-loop failure/cleanup exit path: drains pending ticks, restores panel/overlay state, then returns to top-level control loop 0x6C82.
N 62507 Args: none.
N 62507 Returns: none.
N 62507 def main_loop_failure_cleanup_exit_path():
N 62507 ↳mem[fn_gameplay_movement_control_step] = 0xC9
N 62507 ↳HL_cell = read_u16(var_runtime_current_cell_ptr_lo)
N 62507 ↳HL_cell[0x00] &= 0xC0
N 62507 ↳while True:
N 62507 ↳↳fn_periodic_scheduler_tick()
N 62507 ↳↳if var_runtime_scheduler_timer_hi == 0x00:
N 62507 ↳↳↳break
N 62507 ↳mem[fn_gameplay_movement_control_step] = 0x3A
N 62507 ↳fn_rectangular_panel_fill_helper(A_fill=0x00)
N 62507 ↳fn_draw_mission_status_panel_bitmap_chunk()
N 62507 ↳fn_transition_beeper_entry_a()
N 62507 ↳fn_frame_delay_loop()
N 62507 ↳fn_active_map_mode_switch_handler()
N 62507 ↳high_score_editor_init()
N 62507 ↳fn_high_score_table_draw_routine()
N 62507 ↳fn_scenario_preset_c()
N 62507 ↳top_level_pre_game_control_loop()
@ 62562 label=main_loop_level_complete_transition_path
c 62562 main_loop_level_complete_transition_path
D 62562 Main-loop level-complete transition path (0xF472): increment mode selector 0xA8DB; for values 0->1 and 1->2 re-enter gameplay setup, and when reaching 3 run ending sequence then return to front-end.
N 62562 Args: none.
N 62562 Returns: none.
N 62562 def main_loop_level_complete_transition_path():
N 62562 ↳fn_active_map_mode_switch_handler()
N 62562 ↳fn_level_transition_wait_loop()
N 62562 ↳var_active_map_mode = (var_active_map_mode + 0x01) & 0xFF
N 62562 ↳if var_active_map_mode != 0x03:
N 62562 ↳↳fn_transition_beeper_entry_a()
N 62562 ↳↳jump(0xF17A)
N 62562 ↳fn_stretched_text_symbol_stream_printer(HL_stream=str_ending_text_stream_1, B_row=0x03, C_col=0x05)
N 62562 ↳fn_stretched_text_symbol_stream_printer(HL_stream=str_ending_text_stream_2, B_row=0x06, C_col=0x07)
N 62562 ↳fn_stretched_text_symbol_stream_printer(HL_stream=str_ending_text_stream_3, B_row=0x09, C_col=0x06)
N 62562 ↳fn_stretched_text_symbol_stream_printer(HL_stream=str_ending_text_stream_4, B_row=0x0C, C_col=0x0A)
N 62562 ↳fn_scenario_preset_beeper_stream_engine()
N 62562 ↳high_score_editor_init()
N 62562 ↳fn_high_score_table_draw_routine()
N 62562 ↳fn_scenario_preset_c()
N 62562 ↳top_level_pre_game_control_loop()
@ 62628 label=fn_level_transition_wait_loop
c 62628 fn_level_transition_wait_loop
D 62628 Level-transition wait loop: run 500 iterations of HUD animation tick (0xEA1A) plus paced delay.
N 62628 Args: none.
N 62628 Returns: none.
N 62628 def fn_level_transition_wait_loop():
N 62628 ↳for _ in range(0x01F4):
N 62628 ↳↳fn_hud_decimal_counter_animator()
N 62628 ↳↳fn_paced_beeper_helper_transitions_panel_fill()
@ 62645 label=fn_paced_beeper_helper_transitions_panel_fill
c 62645 fn_paced_beeper_helper_transitions_panel_fill
D 62645 Paced beeper helper used by transitions/panel fill: 5 ROM 0x03B5 calls with fixed spacing.
N 62645 Args: none.
N 62645 Returns: none.
N 62645 def fn_paced_beeper_helper_transitions_panel_fill():
N 62645 ↳HL_period = 0x0190
N 62645 ↳for _ in range(0x05):
N 62645 ↳↳rom_beeper(DE_ticks=0x0001, HL_period=HL_period)
N 62645 ↳↳HL_period += 0x0004
@ 62672 label=fn_draw_mission_status_panel_bitmap_chunk
c 62672 fn_draw_mission_status_panel_bitmap_chunk
D 62672 Draw mission/status panel bitmap chunk rows from 0x7A55 to screen using 0xEAA6; then stamp 4 text rows.
N 62672 Args: none.
N 62672 Returns: none.
N 62672 def fn_draw_mission_status_panel_bitmap_chunk():
N 62672 ↳DE_src = 0x7A55
N 62672 ↳for B_row in range(0x06, 0x0A):
N 62672 ↳↳for C_col in range(0x01, 0x1B):
N 62672 ↳↳↳DE_src = fn_routine_8_byte_screen_blit_primitive(DE_src=DE_src, B_row=B_row, C_col=C_col)
N 62672 ↳HL_row = 0x58C1
N 62672 ↳for _ in range(0x04):
N 62672 ↳↳HL_row[:0x1A] = [0x06] * 0x1A
N 62672 ↳↳HL_row += 0x20
@ 62726 label=fn_transition_beeper_helper
c 62726 fn_transition_beeper_helper
D 62726 Transition beeper helper (entry A): run 100/300 beeper call then fall into shared 200/200 beeper call at 0xF50F.
N 62726 Args: none.
N 62726 Returns: none.
N 62726 def fn_transition_beeper_helper():
N 62726 ↳rom_beeper(DE_ticks=0x0064, HL_period=0x012C)
N 62726 ↳rom_beeper(DE_ticks=0x00C8, HL_period=0x00C8)
@ 62735 label=fn_transition_beeper_entry_a
c 62735 fn_transition_beeper_entry_a
D 62735 Transition beeper helper callable entry A (+0x9) used by level-complete transition path.
N 62735 Args: none.
N 62735 Returns: none.
N 62735 def fn_transition_beeper_entry_a():
N 62735 ↳rom_beeper(DE_ticks=0x00C8, HL_period=0x00C8)
@ 62745 label=scheduler_triggered_marker_seeding
@ 62781 label=patch_marker_seed_map_base_ptr
c 62745 scheduler_triggered_marker_seeding
D 62745 Scheduler-triggered marker seeding: choose map by mode, find empty cell, stamp marker, and enable callback 0xEDD1.
N 62745 Args: none.
N 62745 Returns: none (early RET when callback hook is already active; trigger path tail-jumps to ROM beeper).
N 62745 def scheduler_triggered_marker_seeding():
N 62745 ↳HL_hook = 0xEDD1
N 62745 ↳if HL_hook[0x00] != 0xC9:
N 62745 ↳↳return
N 62745 ↳if var_active_map_mode == 0x00:
N 62745 ↳↳HL_map = var_level_map_mode_0
N 62745 ↳elif var_active_map_mode == 0x01:
N 62745 ↳↳HL_map = var_level_map_mode_1
N 62745 ↳else:
N 62745 ↳↳HL_map = var_level_map_mode_2
N 62745 ↳patch_marker_seed_map_base_ptr = HL_map
N 62745 ↳while True:
N 62745 ↳↳HL_probe = patch_marker_seed_map_base_ptr
N 62745 ↳↳E_rand = R
N 62745 ↳↳DE_off = (((var_runtime_scheduler_timer_lo + E_rand) & 0x07) << 8) | E_rand
N 62745 ↳↳HL_probe += DE_off
N 62745 ↳↳if HL_probe[0x00] == 0x00:
N 62745 ↳↳↳break
N 62745 ↳var_marker_event_ptr = HL_probe
N 62745 ↳HL_probe[0x00] |= 0x2E
N 62745 ↳HL_hook[0x00] = 0x2A
N 62745 ↳var_marker_index_state = 0x00
N 62745 ↳rom_beeper(DE_ticks=0x001E, HL_period=0x012C)
@ 62824 label=gameplay_screen_setup
c 62824 gameplay_screen_setup
D 62824 Gameplay screen setup: clear display, then draw static lower panel from source buffers.
N 62824 Args: none.
N 62824 Returns: none.
N 62824 def gameplay_screen_setup():
N 62824 ↳var_display_bitmap_ram[0x0000:0x1000] = 0x00
N 62824 ↳var_display_attribute_ram[0x0000:0x0200] = 0x39
N 62824 ↳fn_draw_static_gameplay_frame_ui_decorations()
N 62824 ↳var_display_bitmap_mission_panel_dst_5000[0x0000:0x0800] = const_mission_panel_bitmap_source[0x0000:0x0800]
N 62824 ↳var_display_attribute_ram_anchor_5a00[0x0000:0x0100] = const_mission_panel_attr_source[0x0000:0x0100]
N 62824 ↳mem[var_runtime_queue_head_0_lo:var_menu_selection_index] = 0x00
N 62824 ↳var_action_effect_flags = 0x40
N 62824 ↳jump(0xE14C)
@ 62896 label=fn_draw_static_gameplay_frame_ui_decorations
c 62896 fn_draw_static_gameplay_frame_ui_decorations
D 62896 Draw static gameplay frame/UI decorations into screen bitmap and attributes.
N 62896 Args: none.
N 62896 Returns: none.
N 62896 def fn_draw_static_gameplay_frame_ui_decorations():
N 62896 ↳fn_draw_framed_ui_box_using_bit(A_w=0x1A, A_h=0x0F, B_row=0x00, C_col=0x00)
N 62896 ↳fn_draw_framed_ui_box_using_bit(A_w=0x02, A_h=0x02, B_row=0x00, C_col=0x1C)
N 62896 ↳fn_draw_framed_ui_box_inner(B_row=0x04, C_col=0x1C)
N 62896 ↳fn_draw_framed_ui_box_inner(B_row=0x08, C_col=0x1C)
N 62896 ↳fn_draw_framed_ui_box_inner(B_row=0x0C, C_col=0x1C)
N 62896 ↳mem[0x5800:0x581C] = 0x28
N 62896 ↳fn_draw_vertical_attribute_stripe(HL_attr=0x581B)
N 62896 ↳fn_draw_vertical_attribute_stripe(HL_attr=0x5800)
N 62896 ↳HL_attr = 0x581C
N 62896 ↳for _ in range(0x10):
N 62896 ↳↳HL_attr[0x00:0x04] = [0x20] * 0x04
N 62896 ↳↳HL_attr += 0x0021
N 62896 ↳fn_draw_2x2_attribute_block_fill_byte(HL_attr=0x583D, A_fill=0x39)
N 62896 ↳fn_draw_2x2_attribute_block_fill_byte(HL_attr=0x58BD, A_fill=0x05)
N 62896 ↳fn_draw_2x2_attribute_block_fill_byte(HL_attr=0x593D, A_fill=0x06)
N 62896 ↳fn_draw_2x2_attribute_block_fill_byte(HL_attr=0x59BD, A_fill=0x07)
N 62896 ↳DE_src = 0x7D95
N 62896 ↳DE_src = fn_draw_static_ui_frame_entry(DE_src=DE_src, B_row=0x01, C_col=0x1D)
N 62896 ↳DE_src = fn_draw_static_ui_frame_entry(DE_src=DE_src, B_row=0x05, C_col=0x1D)
N 62896 ↳DE_src = fn_draw_static_ui_frame_entry(DE_src=DE_src, B_row=0x09, C_col=0x1D)
N 62896 ↳fn_draw_static_ui_frame_entry(DE_src=DE_src, B_row=0x0D, C_col=0x1D)
@ 63032 label=fn_draw_static_ui_frame_entry
c 63032 fn_draw_static_ui_frame_entry
D 63032 Static gameplay-frame/UI decorator callable entry (+0x88): draws frame segments and panel ornaments.
N 63032 Args: DE_src is ptr_u8 fragment stream (4 fragments x 8 bytes); B_row is u8 start row; C_col is u8 start column.
N 63032 Returns: DE_src advanced by 0x20 bytes.
N 63032 def fn_draw_static_ui_frame_entry(DE_src, B_row, C_col):
N 63032 ↳DE_src = fn_secondary_8_byte_screen_blit_primitive(DE_src=DE_src, B_row=B_row, C_col=C_col)
N 63032 ↳DE_src = fn_secondary_8_byte_screen_blit_primitive(DE_src=DE_src, B_row=B_row, C_col=C_col + 0x01)
N 63032 ↳DE_src = fn_secondary_8_byte_screen_blit_primitive(DE_src=DE_src, B_row=B_row + 0x01, C_col=C_col + 0x01)
N 63032 ↳DE_src = fn_secondary_8_byte_screen_blit_primitive(DE_src=DE_src, B_row=B_row + 0x01, C_col=C_col)
N 63032 ↳return DE_src
@ 63047 label=fn_draw_vertical_attribute_stripe
c 63047 fn_draw_vertical_attribute_stripe
D 63047 Draw vertical attribute stripe (16 rows, byte value 40).
N 63047 Args: HL_attr is ptr_u8 top cell of target attribute column.
N 63047 Returns: none.
N 63047 def fn_draw_vertical_attribute_stripe(HL_attr):
N 63047 ↳for _ in range(0x10):
N 63047 ↳↳HL_attr[0x00] = 0x28
N 63047 ↳↳HL_attr += 0x0020
@ 63059 label=fn_draw_framed_ui_box_using_bit
c 63059 fn_draw_framed_ui_box_using_bit
D 63059 Draw framed UI box using bit-pattern tables at 0xF6CA.. via helpers 0xF6FA/0xF6BC.
N 63059 Args: A_w is u8 horizontal span; A_h is u8 vertical span (passed in D); B_row is u8 top row; C_col is u8 left column.
N 63059 Returns: none.
N 63059 def fn_draw_framed_ui_box_using_bit(A_w, A_h, B_row, C_col):
N 63059 ↳var_runtime_ui_frame_params[0x00] = A_w
N 63059 ↳var_runtime_ui_frame_params[0x01] = A_h
N 63059 ↳fn_draw_framed_ui_box_inner(B_row=B_row, C_col=C_col)
@ 63066 label=fn_draw_framed_ui_box_inner
c 63066 fn_draw_framed_ui_box_inner
D 63066 Framed UI box inner entry (+0x7): draws middle spans using bit-pattern tables and 0xF6FA blitter.
N 63066 Args: B_row is u8 top row; C_col is u8 left column; var_runtime_ui_frame_params[0] is u8 horizontal span; var_runtime_ui_frame_params[1] is u8 vertical span.
N 63066 Returns: none.
N 63066 def fn_draw_framed_ui_box_inner(B_row, C_col):
N 63066 ↳A_w = var_runtime_ui_frame_params[0x00]
N 63066 ↳A_h = var_runtime_ui_frame_params[0x01]
N 63066 ↳fn_secondary_8_byte_screen_blit_primitive(DE_src=const_ui_frame_bitmap_fragments, B_row=B_row, C_col=C_col)
N 63066 ↳C_col += 0x01
N 63066 ↳fn_repeat_call_helper_xf6fa_along_direction(A_span=A_w, DE_src=const_ui_frame_bitmap_fragment_2, B_row=B_row, C_col=C_col)
N 63066 ↳fn_secondary_8_byte_screen_blit_primitive(DE_src=const_ui_frame_bitmap_fragment_3, B_row=B_row, C_col=C_col + A_w)
N 63066 ↳B_row += 0x01
N 63066 ↳fn_draw_framed_ui_box_tail_entry(A_span=A_h, DE_src=const_ui_frame_bitmap_fragment_4, B_row=B_row, C_col=C_col + A_w)
N 63066 ↳fn_secondary_8_byte_screen_blit_primitive(DE_src=const_ui_frame_bitmap_fragment_5, B_row=B_row + A_h, C_col=C_col + A_w)
N 63066 ↳fn_repeat_call_helper_xf6fa_along_direction(A_span=A_w, DE_src=const_ui_frame_bitmap_fragment_2, B_row=B_row + A_h, C_col=C_col)
N 63066 ↳fn_secondary_8_byte_screen_blit_primitive(DE_src=const_ui_frame_bitmap_fragment_6, B_row=B_row + A_h, C_col=C_col - 0x01)
N 63066 ↳fn_draw_framed_ui_box_tail_entry(A_span=A_h, DE_src=const_ui_frame_bitmap_fragment_4, B_row=B_row, C_col=C_col - 0x01)
@ 63141 label=fn_draw_framed_ui_box_tail_entry
c 63141 fn_draw_framed_ui_box_tail_entry
D 63141 Framed UI box tail entry (+0x52): finalizes lower edge/corner segments of framed panel.
N 63141 Args: A_span is u8 vertical repeat count; DE_src is ptr_u8 one 8-byte fragment; B_row is u8 start row; C_col is u8 fixed column.
N 63141 Returns: none.
N 63141 def fn_draw_framed_ui_box_tail_entry(A_span, DE_src, B_row, C_col):
N 63141 ↳for _ in range(A_span):
N 63141 ↳↳fn_secondary_8_byte_screen_blit_primitive(DE_src=DE_src, B_row=B_row, C_col=C_col)
N 63141 ↳↳B_row += 0x01
@ 63153 label=fn_draw_2x2_attribute_block_fill_byte
c 63153 fn_draw_2x2_attribute_block_fill_byte
D 63153 Draw a 2x2 attribute block with fill byte A.
N 63153 Args: HL_attr is ptr_u8 top-left attribute cell; A_fill is u8 attribute byte.
N 63153 Returns: none.
N 63153 def fn_draw_2x2_attribute_block_fill_byte(HL_attr, A_fill):
N 63153 ↳HL_attr[0x00] = A_fill
N 63153 ↳HL_attr[0x01] = A_fill
N 63153 ↳HL_attr[0x20] = A_fill
N 63153 ↳HL_attr[0x21] = A_fill
@ 63164 label=fn_repeat_call_helper_xf6fa_along_direction
c 63164 fn_repeat_call_helper_xf6fa_along_direction
D 63164 Repeat-call helper for 0xF6FA along +X direction C for A steps.
N 63164 Args: A_span is u8 horizontal repeat count; DE_src is ptr_u8 one 8-byte fragment; B_row is u8 fixed row; C_col is u8 start column.
N 63164 Returns: none.
N 63164 def fn_repeat_call_helper_xf6fa_along_direction(A_span, DE_src, B_row, C_col):
N 63164 ↳for _ in range(A_span):
N 63164 ↳↳fn_secondary_8_byte_screen_blit_primitive(DE_src=DE_src, B_row=B_row, C_col=C_col)
N 63164 ↳↳C_col += 0x01
@ 63176 label=var_runtime_ui_frame_params
b 63176 var_runtime_ui_frame_params
D 63176 Runtime UI frame parameter pair consumed by box drawer 0xF63B.
D 63176 Structure: 2-byte runtime parameter pair for box dimensions/iteration counts.
@ 63177 label=var_runtime_ui_frame_param_1
@ 63178 label=const_ui_frame_bitmap_fragments
b 63178 const_ui_frame_bitmap_fragments
D 63178 UI frame static bitmap fragments consumed by box drawer 0xF63B.
D 63178 Structure: 6 fragments x 8 bytes = 48-byte static pattern table.
@ 63186 label=const_ui_frame_bitmap_fragment_2
@ 63194 label=const_ui_frame_bitmap_fragment_3
@ 63202 label=const_ui_frame_bitmap_fragment_4
@ 63210 label=const_ui_frame_bitmap_fragment_5
@ 63218 label=const_ui_frame_bitmap_fragment_6
@ 63226 label=fn_secondary_8_byte_screen_blit_primitive
c 63226 fn_secondary_8_byte_screen_blit_primitive
D 63226 Secondary 8-byte screen blit primitive (same ZX address mapping as 0xEAA6).
N 63226 Args: DE_src is ptr_u8 source byte stream (8 bytes); B_row is u8 character-row index; C_col is u8 byte-column index.
N 63226 Returns: DE_src advanced by 8 bytes.
N 63226 def fn_secondary_8_byte_screen_blit_primitive(DE_src, B_row, C_col):
N 63226 ↳HL_dst = (((B_row & 0x18) | 0x40) << 8) | (((B_row & 0x07) << 5) + C_col)
N 63226 ↳for _ in range(0x08):
N 63226 ↳↳HL_dst[0x00] = DE_src[0x00]
N 63226 ↳↳DE_src += 0x01
N 63226 ↳↳HL_dst += 0x0100
b 63254 const_unresolved_ui_helper_blob
D 63254 Unresolved binary helper blob between blit routine and overlay selectors (no direct static xrefs).
D 63254 Structure: opaque 23-byte helper blob between UI blit and overlay selectors; field boundaries unresolved.
@ 63277 label=fn_overlay_preset_selector
c 63277 fn_overlay_preset_selector
D 63277 Overlay preset-A wrapper with tail call into overlay refresh pipeline at 0xF740.
N 63277 Args: none (preset A is selected inside this wrapper).
N 63277 Returns: none.
N 63277 def fn_overlay_preset_selector():
N 63277 ↳fn_overlay_legend_refresh_pipeline(DE_src=const_overlay_preset_a_triplets)
@ 63282 label=fn_overlay_preset_b_selector
c 63282 fn_overlay_preset_b_selector
D 63282 Overlay preset-B wrapper with status-line refresh and tail call into overlay refresh pipeline.
N 63282 Args: none (preset B is selected inside this wrapper).
N 63282 Returns: none.
N 63282 def fn_overlay_preset_b_selector():
N 63282 ↳copy_28_byte_status_string_template()
N 63282 ↳fn_overlay_legend_refresh_pipeline(DE_src=const_overlay_preset_b_triplets)
@ 63290 label=fn_overlay_preset_c_selector
c 63290 fn_overlay_preset_c_selector
D 63290 Overlay preset-C wrapper with status-line refresh and tail call into overlay refresh pipeline.
N 63290 Args: none (preset C is selected inside this wrapper).
N 63290 Returns: none.
N 63290 def fn_overlay_preset_c_selector():
N 63290 ↳copy_28_byte_status_string_template()
N 63290 ↳fn_overlay_legend_refresh_pipeline(DE_src=const_overlay_preset_c_triplets)
@ 63296 label=fn_overlay_legend_refresh_pipeline
c 63296 fn_overlay_legend_refresh_pipeline
D 63296 Overlay refresh pipeline: copy preset triplets into template rows, rebuild staging payload, update floor pattern, then trigger render pass.
N 63296 Args: DE_src is ptr_u8 source triplet stream (5 records x 3 bytes).
N 63296 Returns: none.
N 63296 def fn_overlay_legend_refresh_pipeline(DE_src):
N 63296 ↳fn_copy_one_3_byte_triplet_de(HL_dst=const_overlay_template_row_0_triplet_dst, DE_src=DE_src)
N 63296 ↳fn_copy_one_3_byte_triplet_de(HL_dst=const_overlay_template_row_1_triplet_dst, DE_src=DE_src)
N 63296 ↳fn_copy_one_3_byte_triplet_de(HL_dst=const_overlay_template_row_2_triplet_dst, DE_src=DE_src)
N 63296 ↳fn_copy_one_3_byte_triplet_de(HL_dst=const_overlay_template_row_3_triplet_dst, DE_src=DE_src)
N 63296 ↳fn_copy_one_3_byte_triplet_de(HL_dst=const_overlay_template_row_4_triplet_dst, DE_src=DE_src)
N 63296 ↳fn_visible_cell_staging_preset_core(IX_tpl=const_overlay_template_payload)
N 63296 ↳fn_floor_texture_selector_pattern_setup_active()
N 63296 ↳fn_render_pass_re_entry_stub()
@ 63340 label=fn_copy_one_3_byte_triplet_de
c 63340 fn_copy_one_3_byte_triplet_de
D 63340 Copy one 3-byte triplet from DE to HL (used by 0xF740).
N 63340 Args: HL_dst is writable three-element byte array; DE_src is source three-element byte array.
N 63340 Returns: DE_src advanced by 3 bytes.
N 63340 def fn_copy_one_3_byte_triplet_de(HL_dst, DE_src):
N 63340 ↳HL_dst[:3] = DE_src[:3]
N 63340 ↳DE_src += 0x03
@ 63352 label=fn_frame_delay_loop
c 63352 fn_frame_delay_loop
D 63352 Frame delay loop (80 HALTs).
N 63352 Args: none.
N 63352 Returns: none.
N 63352 def fn_frame_delay_loop():
N 63352 ↳for _ in range(0x50):
N 63352 ↳↳halt_until_interrupt()
@ 63358 label=copy_28_byte_status_string_template
c 63358 copy_28_byte_status_string_template
D 63358 Copy 28-byte status string/template chunk 0x79D5->0x5A80.
N 63358 Args: none.
N 63358 Returns: none.
N 63358 def copy_28_byte_status_string_template():
N 63358 ↳mem[0x5A80:0x5A9C] = mem[0x79D5:0x79F1]
@ 63370 label=const_overlay_preset_a_triplets
b 63370 const_overlay_preset_a_triplets
D 63370 Overlay preset-A triplet stream consumed by 0xF740.
D 63370 Structure: 5 records x 3 bytes (15-byte triplet stream for preset A).
@ 63385 label=const_overlay_preset_b_triplets
b 63385 const_overlay_preset_b_triplets
D 63385 Overlay preset-B triplet stream consumed by 0xF740.
D 63385 Structure: 5 records x 3 bytes (15-byte triplet stream for preset B).
@ 63400 label=const_overlay_preset_c_triplets
b 63400 const_overlay_preset_c_triplets
D 63400 Overlay preset-C triplet stream consumed by 0xF740.
D 63400 Structure: 5 records x 3 bytes (15-byte triplet stream for preset C).
@ 63415 label=const_overlay_template_payload
b 63415 const_overlay_template_payload
D 63415 Overlay template payload consumed via IX by 0xF740 -> 0xEF87.
D 63415 Structure: 5 groups x 19 bytes = 95-byte template payload.
@ 63431 label=const_overlay_template_row_0_triplet_dst
@ 63450 label=const_overlay_template_row_1_triplet_dst
@ 63469 label=const_overlay_template_row_2_triplet_dst
@ 63488 label=const_overlay_template_row_3_triplet_dst
@ 63507 label=const_overlay_template_row_4_triplet_dst
@ 63510 label=str_ending_text_stream_1
t 63510 str_ending_text_stream_1
D 63510 Ending text stream #1 for 0xEAE2.
D 63510 Decoded text stream: "AN ALIEN EVOLUTION".
@ 63529 label=str_ending_text_stream_2
t 63529 str_ending_text_stream_2
D 63529 Ending text stream #2 for 0xEAE2.
D 63529 Decoded text stream: "WAS STOPPED BUT".
@ 63545 label=str_ending_text_stream_3
t 63545 str_ending_text_stream_3
D 63545 Ending text stream #3 for 0xEAE2.
D 63545 Decoded text stream: "IN SPACE WILL BE".
@ 63562 label=str_ending_text_stream_4
t 63562 str_ending_text_stream_4
D 63562 Ending text stream #4 for 0xEAE2 (includes shared 0xFF terminator at 0xF850).
D 63562 Decoded text stream: "OTHERS".
b 63569 const_ending_prelude_data
D 63569 Ending/post-loop binary script/table prelude (header/padding before scenario preset-B streams).
D 63569 Structure: ending prelude block with short header bytes followed by zero/padding reservoir before scenario stream B.
@ 63750 label=const_scenario_preset_b_stream_1
b 63750 const_scenario_preset_b_stream_1
D 63750 Scenario preset-B stream #1 source (default seed for menu/front-end beeper script via 0xF152).
D 63750 Structure: preset-B beeper command stream #1 for 0xFBCC engine (byte-coded music/effect script), terminates with 0x40 sentinel.
@ 64104 label=const_scenario_preset_b_stream_2
b 64104 const_scenario_preset_b_stream_2
D 64104 Scenario preset-B stream #2 source (paired with 0xF906 for 0xFBCC driver).
D 64104 Structure: preset-B beeper command stream #2 (paired script bytes), terminates with 0x40 sentinel.
@ 64460 label=scenario_intermission_beeper_stream_player_loop
@ 64461 label=patch_stream_player_default_stream_a_ptr
@ 64467 label=patch_stream_player_default_stream_b_ptr
c 64460 scenario_intermission_beeper_stream_player_loop
D 64460 Scenario/intermission beeper stream player loop: run command interpreter 0xFC13 until termination condition from ROM poll.
N 64460 0xFBCD and 0xFBD3 are immediate HL words (default stream pointers) patched by scenario_pointer_seeding_core at 0xF161.
N 64460 Args: none.
N 64460 Returns: none.
N 64460 def scenario_intermission_beeper_stream_player_loop():
N 64460 ↳var_stream_ptr_a_lo = patch_stream_player_default_stream_a_ptr
N 64460 ↳var_stream_ptr_c_lo = patch_stream_player_default_stream_b_ptr
N 64460 ↳disable_interrupts()
N 64460 ↳while True:
N 64460 ↳↳core_command_interpreter_scenario_stream_engine()
N 64460 ↳↳E_poll = rom_keyboard_input_poll_0x028E()
N 64460 ↳↳if ((E_poll + 0x01) & 0xFF) != 0x00:
N 64460 ↳↳↳break
N 64460 ↳enable_interrupts()
@ 64484 label=var_stream_interpreter_state
b 64484 var_stream_interpreter_state
D 64484 Mutable interpreter state block: current command bytes and stream pointer pairs for 0xFC13.
D 64484 Structure: interpreter context struct at 0xFBE4..0xFBEF: command bytes (0xFBE4-0xFBE6), stream pointers at 0xFBE7/0xFBE9/0xFBEB/0xFBED, and timing/control byte at 0xFBEF.
@ 64485 label=var_stream_cmd_byte_1
@ 64486 label=var_stream_cmd_byte_2
@ 64487 label=var_stream_ptr_a_lo
@ 64489 label=var_stream_ptr_b_lo
@ 64491 label=var_stream_ptr_c_lo
@ 64493 label=var_stream_ptr_d_lo
@ 64495 label=var_stream_timing_control_byte
@ 64496 label=fn_stream_byte_fetch_helper
c 64496 fn_stream_byte_fetch_helper
D 64496 Stream byte fetch helper: advance pointer pair, load next byte, and branch to abort on 0x40 terminator.
N 64496 Args: HL_ptr points to 16-bit little-endian stream pointer [ptr_lo, ptr_hi].
N 64496 Returns: A_byte is next stream byte; HL_ptr is updated to the incremented stream pointer.
N 64496 def fn_stream_byte_fetch_helper(HL_ptr):
N 64496 ↳DE_ptr = HL_ptr[0x00] | (HL_ptr[0x01] << 0x08)
N 64496 ↳DE_ptr += 0x0001
N 64496 ↳A_byte = mem_u8(DE_ptr)
N 64496 ↳if A_byte == 0x40:
N 64496 ↳↳forced_interpreter_abort_path()
N 64496 ↳HL_ptr[0x00] = DE_ptr & 0x00FF
N 64496 ↳HL_ptr[0x01] = (DE_ptr >> 0x08) & 0x00FF
N 64496 ↳return A_byte
@ 64509 label=fn_timing_parameter_decode_helper
c 64509 fn_timing_parameter_decode_helper
D 64509 Timing/parameter decode helper: map command byte to value from table 0xFCA0+12*n.
N 64509 Args: HL_cmd points to one command byte from var_stream_cmd_byte_1 or var_stream_cmd_byte_2.
N 64509 Returns: HL_timing is (table_hi << 8) | 0x01 where table_hi comes from const_stream_timing_profile_table[E_idx]; E_idx is (cmd + 0x0C) & 0xFF.
N 64509 def fn_timing_parameter_decode_helper(HL_cmd):
N 64509 ↳E_idx = (HL_cmd[0x00] + 0x0C) & 0xFF
N 64509 ↳table_hi = const_stream_timing_profile_table[E_idx]
N 64509 ↳HL_timing = (table_hi << 0x08) | 0x01
N 64509 ↳return HL_timing, E_idx
@ 64523 label=forced_interpreter_abort_path
c 64523 forced_interpreter_abort_path
D 64523 Forced interpreter abort path: unwind caller stack, re-enable interrupts, and return.
N 64523 Args: none.
N 64523 Returns: none (non-local unwind to caller-of-caller via stack pointer skip).
N 64523 def forced_interpreter_abort_path():
N 64523 ↳SP += 0x0004
N 64523 ↳enable_interrupts()
N 64523 ↳return
b 64527 const_unresolved_constant_4b
D 64527 Unresolved 4-byte constant block near interpreter core (no direct static xrefs).
D 64527 Structure: unresolved 4-byte constant set referenced indirectly by interpreter/tone logic.
@ 64531 label=core_command_interpreter_scenario_stream_engine
c 64531 core_command_interpreter_scenario_stream_engine
D 64531 Core command interpreter for scenario stream engine: decode commands and dispatch to effect/tone generators.
N 64531 Args: none.
N 64531 Returns: none.
N 64531 def core_command_interpreter_scenario_stream_engine():
N 64531 ↳var_stream_interpreter_state[0x00] = fn_stream_byte_fetch_helper(HL_ptr=var_stream_ptr_a_lo)
N 64531 ↳var_stream_interpreter_state[0x01] = fn_stream_byte_fetch_helper(HL_ptr=var_stream_ptr_c_lo)
N 64531 ↳HL_t1, E_cmd1 = fn_timing_parameter_decode_helper(HL_cmd=var_stream_interpreter_state + 0x00)
N 64531 ↳if E_cmd1 & 0x80:
N 64531 ↳↳special_command_dispatcher(A_cmd=var_stream_interpreter_state[0x00])
N 64531 ↳↳return
N 64531 ↳HL_t2, _ = fn_timing_parameter_decode_helper(HL_cmd=var_stream_interpreter_state + 0x01)
N 64531 ↳if high_byte(HL_t2) == 0x01 and high_byte(HL_t1) == 0x01:
N 64531 ↳↳pre_delay_calibration_helper()
N 64531 ↳↳return
N 64531 ↳C_cycles = var_stream_timing_control_byte
N 64531 ↳B_phase = 0x00
N 64531 ↳A_main = var_stream_interpreter_state[0x02]
N 64531 ↳A_alt = var_stream_interpreter_state[0x02]
N 64531 ↳E_ctr = low_byte(HL_t1)
N 64531 ↳E_reload = high_byte(HL_t1)
N 64531 ↳L_ctr = low_byte(HL_t2)
N 64531 ↳L_reload = high_byte(HL_t2)
N 64531 ↳toggle_mask = 0x10
N 64531 ↳while True:
N 64531 ↳↳# NOTE: cycle-accurate timing is implemented by the shared FC51<->FC70 loop and retained as ASM.
N 64531 ↳↳A_main, A_alt, E_ctr, L_ctr, B_phase, C_cycles = interpreter_inner_loop_branch_helper_timing(A_main=A_main, A_alt=A_alt, E_ctr=E_ctr, E_reload=E_reload, L_ctr=L_ctr, L_reload=L_reload, B_phase=B_phase, C_cycles=C_cycles, toggle_mask=toggle_mask)
N 64531 ↳↳if C_cycles == 0x00:
N 64531 ↳↳↳return
b 64620 const_stream_control_pattern_bytes
D 64620 Non-text control/pattern bytes used by 0xFC13-side effect routines.
D 64620 Structure: 4-byte control constant set used by 0xFC13 side-effect paths.
@ 64624 label=interpreter_inner_loop_branch_helper_timing
c 64624 interpreter_inner_loop_branch_helper_timing
D 64624 Interpreter inner-loop branch helper for timing/output cycle (paired with self-modifying loop at 0xFC11).
N 64624 Args: A_main is u8 current beeper latch value; A_alt is u8 alternate latch value; E_ctr/E_reload are fast-divider bytes passed through unchanged in this FC70 path; L_ctr/L_reload are slow-divider counter/reload bytes; B_phase is u8 inner-loop counter; C_cycles is u8 outer-loop counter; toggle_mask is u8 XOR mask.
N 64624 Returns: updated tuple (A_main, A_alt, E_ctr, L_ctr, B_phase, C_cycles).
N 64624 def interpreter_inner_loop_branch_helper_timing(A_main, A_alt, E_ctr, E_reload, L_ctr, L_reload, B_phase, C_cycles, toggle_mask):
N 64624 ↳# NOTE: entry byte JR Z,$FC70 is timing padding on normal FC57->FC70 path (Z is clear).
N 64624 ↳A_main, A_alt = A_alt, A_main
N 64624 ↳L_ctr = (L_ctr - 0x01) & 0xFF
N 64624 ↳if L_ctr == 0x00:
N 64624 ↳↳out_port_0xFE(A_main)
N 64624 ↳↳L_ctr = L_reload
N 64624 ↳↳A_main ^= toggle_mask
N 64624 ↳else:
N 64624 ↳↳out_port_0xFE(A_main)
N 64624 ↳B_phase = (B_phase - 0x01) & 0xFF
N 64624 ↳if B_phase != 0x00:
N 64624 ↳↳return A_main, A_alt, E_ctr, L_ctr, B_phase, C_cycles
N 64624 ↳C_cycles = (C_cycles + 0x01) & 0xFF
N 64624 ↳return A_main, A_alt, E_ctr, L_ctr, B_phase, C_cycles
@ 64642 label=pre_delay_calibration_helper
c 64642 pre_delay_calibration_helper
D 64642 Pre-delay calibration helper: derive counter from byte 0xFBEF and run shift-based wait loop.
N 64642 Args: C_wait is u8 delay count; entry 0xFC82 derives it as (~var_stream_timing_control_byte) & 0xFF, entry 0xFC87 uses caller-provided C_wait.
N 64642 Returns: none.
N 64642 def pre_delay_calibration_helper(C_wait=None):
N 64642 ↳if C_wait is None:
N 64642 ↳↳C_wait = (~var_stream_timing_control_byte) & 0xFF
N 64642 ↳for _ in range(C_wait):
N 64642 ↳↳for _ in range(0x100):
N 64642 ↳↳↳timing_spin()
@ 64672 label=const_stream_timing_profile_table
b 64672 const_stream_timing_profile_table
D 64672 Consolidated timing/pattern data region consumed by 0xFC1F/0xFCB6-side routines.
D 64672 Structure: timing/profile lookup table indexed from command-derived offset in 0xFC0D path.
@ 64726 label=special_command_dispatcher
c 64726 special_command_dispatcher
D 64726 Special-command dispatcher (carry path): decode command classes and route to pulse/table generators.
N 64726 Args: A_cmd is u8 command-class byte from core interpreter carry path (special-command class); var_stream_cmd_byte_2 is the paired command byte used as bitstream source.
N 64726 Returns: none.
N 64726 def special_command_dispatcher(A_cmd):
N 64726 ↳D_bits = var_stream_cmd_byte_2
N 64726 ↳A_cmd, B_delay, C_delay, E_wait = fn_command_parameter_normalizer(A_cmd=A_cmd)
N 64726 ↳if A_cmd == 0xFF:
N 64726 ↳↳bitstream_pulse_generator(C_repeat=C_delay, D_bits=D_bits)
N 64726 ↳↳return
N 64726 ↳if A_cmd == 0xC0:
N 64726 ↳↳lookup_driven_burst_generator(B_idx=B_delay)
N 64726 ↳↳return
N 64726 ↳C_repeat = E_wait
N 64726 ↳A_mix = rol8(rol8(rol8(rol8(A_cmd))))
N 64726 ↳for _ in range(0x04):
N 64726 ↳↳A_mix, carry = rol8(A_mix)
N 64726 ↳↳if carry:
N 64726 ↳↳↳bitstream_pulse_generator(C_repeat=C_repeat, D_bits=D_bits)
N 64726 ↳↳else:
N 64726 ↳↳↳pre_delay_calibration_helper(C_wait=C_repeat)
@ 64761 label=fn_command_parameter_normalizer
c 64761 fn_command_parameter_normalizer
D 64761 Command parameter normalizer: compute E/B/C timing values from interpreter byte 0xFBEF.
N 64761 Args: A_cmd is u8 and preserved by this routine.
N 64761 Returns: A_cmd preserved; B_delay and C_delay are (~var_stream_timing_control_byte)&0xFF; E_wait is arithmetic-right-shift-2 of (B_delay+1), clamped to minimum 1.
N 64761 def fn_command_parameter_normalizer(A_cmd):
N 64761 ↳A_inv = (~var_stream_timing_control_byte) & 0xFF
N 64761 ↳B_delay = A_inv
N 64761 ↳C_delay = A_inv
N 64761 ↳E_wait = sra8(sra8((A_inv + 0x01) & 0xFF))
N 64761 ↳if E_wait == 0x00:
N 64761 ↳↳E_wait = 0x01
N 64761 ↳return A_cmd, B_delay, C_delay, E_wait
@ 64782 label=bitstream_pulse_generator
c 64782 bitstream_pulse_generator
D 64782 Bitstream pulse generator: emit border/speaker pattern from D/C counters and command bits.
N 64782 Args: C_repeat is u8 repeat counter (from fn_command_parameter_normalizer); D_bits is u8 bitstream source.
N 64782 Returns: none.
N 64782 def bitstream_pulse_generator(C_repeat, D_bits):
N 64782 ↳A_port = var_stream_cmd_byte_2
N 64782 ↳B_phase = 0x00
N 64782 ↳HL_tap = 0x03E8
N 64782 ↳while True:
N 64782 ↳↳D_bits, carry = rrc8(D_bits)
N 64782 ↳↳if carry:
N 64782 ↳↳↳HL_tap += 0x0001
N 64782 ↳↳↳if mem[HL_tap] & 0x01:
N 64782 ↳↳↳↳A_port |= 0x10
N 64782 ↳↳↳else:
N 64782 ↳↳↳↳A_port &= 0xEF
N 64782 ↳↳↳out_port_0xFE(A_port)
N 64782 ↳↳B_phase = (B_phase - 0x01) & 0xFF
N 64782 ↳↳if B_phase != 0x00:
N 64782 ↳↳↳continue
N 64782 ↳↳C_repeat = (C_repeat - 0x01) & 0xFF
N 64782 ↳↳if C_repeat == 0x00:
N 64782 ↳↳↳break
@ 64843 label=lookup_driven_burst_generator
c 64843 lookup_driven_burst_generator
D 64843 Lookup-driven burst generator: use table 0xFD83 and call 0xFD6A repeatedly.
N 64843 Args: B_idx is u8 lookup index into const_burst_lookup_table.
N 64843 Returns: none.
N 64843 def lookup_driven_burst_generator(B_idx):
N 64843 ↳B_repeat = const_burst_lookup_table[B_idx]
N 64843 ↳HL_delay = 0x0003
N 64843 ↳for _ in range(B_repeat):
N 64843 ↳↳fn_low_level_tone_delay_primitive(HL_delay=HL_delay)
N 64843 ↳↳HL_delay = adc16(HL_delay, 0x00FF)  # carry comes from prior tone path flags
@ 64874 label=fn_low_level_tone_delay_primitive
c 64874 fn_low_level_tone_delay_primitive
D 64874 Low-level tone delay primitive: select ROM timing variant and invoke sound helper at 0x03D4.
N 64874 Args: HL_delay is u16 delay/tone code (only L byte is used for variant index).
N 64874 Returns: none (IFF is cleared by DI before RET).
N 64874 def fn_low_level_tone_delay_primitive(HL_delay):
N 64874 ↳C_variant = (~(HL_delay & 0x00FF)) & 0x03
N 64874 ↳IX_rom_tone_entry = 0x03D1 + C_variant
N 64874 ↳A_tone = var_stream_cmd_byte_2
N 64874 ↳rom_tone_03D4(IX_rom_tone_entry=IX_rom_tone_entry, A_tone=A_tone)
N 64874 ↳disable_interrupts()
@ 64899 label=const_burst_lookup_table
b 64899 const_burst_lookup_table
D 64899 Short lookup table consumed by 0xFD4B branch (index via B in 0xFD0E).
D 64899 Structure: 24-entry 1-byte lookup table (index from B in 0xFD4B branch).
@ 64923 label=const_scenario_preset_c_stream_1
b 64923 const_scenario_preset_c_stream_1
D 64923 Scenario preset-C stream #1 source (seeded by 0xF13B into 0xFBCC driver).
D 64923 Structure: preset-C beeper command stream #1 for 0xFBCC engine (byte-coded music/effect script), ends at 0x40 sentinel.
@ 65018 label=const_scenario_preset_c_stream_2
b 65018 const_scenario_preset_c_stream_2
D 65018 Scenario preset-C stream #2 source (paired with 0xFDAB for 0xFBCC driver).
D 65018 Structure: preset-C beeper command stream #2 for 0xFBCC engine (paired script bytes), ends at 0x40 sentinel.
@ 65129 label=abort_continue_gate_interpreter_loop
c 65129 abort_continue_gate_interpreter_loop
D 65129 Abort/continue gate for interpreter loop: ROM input check at 0x1F54, reset counters on abort request.
N 65129 Args: none.
N 65129 Returns: none.
N 65129 def abort_continue_gate_interpreter_loop():
N 65129 ↳disable_interrupts()
N 65129 ↳C_continue = rom_keyboard_check_break_0x1F54()
N 65129 ↳if not C_continue:
N 65129 ↳↳var_runtime_scheduler_timer_hi = 0x00
N 65129 ↳↳var_runtime_scheduler_timer_lo = 0x09
N 65129 ↳enable_interrupts()
b 65156 const_tail_zero_prelude
D 65156 Zero-filled tail prelude reservoir before unresolved control/script tail.
D 65156 Structure: 148-byte zero/padding reservoir at 0xFE84-0xFF17.
b 65304 const_tail_control_sequence
D 65304 Non-zero unresolved tail control/script sequence after zero reservoir (0xFF18-0xFF3F).
D 65304 Static across snapshots; currently no direct static xrefs from code paths.
D 65304 Structure: 40-byte control/script-like tail sequence (likely data, not executed code in current flow).
b 65344 const_tail_control_fragment
D 65344 Unresolved control fragment between 0xFF40 and 0xFF58.
D 65344 Static across snapshots; no direct static xrefs found.
D 65344 Structure: 25-byte control/data fragment preceding glyph-like rows.
b 65369 const_tail_glyph_row_table
D 65369 Uppercase-like 8x8 row table in RAM tail (0xFF59-0xFFF8).
D 65369 Byte rows decode into A..T-like 8x8 glyph patterns (20 records x 8 bytes) with no direct static xrefs in current code paths.
D 65369 Structure: glyph-like 8-byte row records.
@ 65486 label=const_tail_glyph_row_table_anchor_ffce
@ 65487 label=const_tail_glyph_row_table_anchor_ffcf
b 65529 const_tail_trailer_7b
D 65529 Final 7-byte RAM tail trailer (0xFFF9-0xFFFF).
D 65529 Structure: short tail trailer after glyph-like rows; semantics unresolved.

@ 65535 label=const_tail_trailer_last_byte_ffff
