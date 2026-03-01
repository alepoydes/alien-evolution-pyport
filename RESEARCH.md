# Research Notes: ZX Spectrum Implementation

This document is about how the original Alien Evolution program works on the ZX Spectrum: memory layout, data formats, control flow, and the implementation details that are difficult to infer from gameplay alone.

If you want the rules, controls, and strategies, start with `GAME_INFO.md`. This file intentionally talks about addresses, byte layouts, and Z80 routines.

The reference point for all names and addresses below is the annotated SkoolKit listing in `skool/AlienEvolution.skool`. Routine names are ours; the original binary has no symbols.

## How to navigate the disassembly

The repository keeps the reverse engineered knowledge in a form that is easy to browse:

* `skool/AlienEvolution.skool` is the annotated disassembly, mixing code, data, and commentary.
* `skool/AlienEvolution.ctl` is the SkoolKit control file that drives HTML generation.

[SkoolKit](https://github.com/skoolkid/skoolkit) itself is a mature Spectrum reverse engineering toolkit by SkoolKid.

If you want an HTML version locally, the shortest path is:

```bash
uvx --from skoolkit skool2html.py -c skool/AlienEvolution.ctl skool/AlienEvolution.skool
```

This produces a browsable site under the default SkoolKit output directory.
If you do not have `uv` yet, install it from the official guide: https://docs.astral.sh/uv/getting-started/installation/

## Coordinate system and address conventions

Addresses are written in hexadecimal with a `0x` prefix, for example `0xF23D`. All addresses refer to the 48K address space.

The level map is a 50 by 50 byte grid stored in row major order. A move of one cell:

* left is minus `0x0001`
* right is plus `0x0001`
* up is minus `0x0032`
* down is plus `0x0032`

Many routines work on raw map pointers rather than `(row, col)` pairs. When you see a pointer arithmetic step of `0x0032`, you are looking at a vertical move.

## Memory map overview

A Spectrum program is, unavoidably, a memory management exercise. Alien Evolution is very deliberate about where data lives.

The following map is not meant to be exhaustive, but it covers the regions that matter for understanding the game.

```text
0x0000..0x3FFF   48K ROM

0x4000..0x57FF   Screen bitmap
0x5800..0x5AFF   Screen attributes (HUD, panels)

0x8000..0x89C3   Level map buffer, mode 0 (50x50, 0x09C4 bytes)
0x89C6..0x8F7F   Visible cell staging lattice and related render staging data
0x8F80..0x90FF   Cell blit work buffer (0x0180 bytes)
0x9100..0x9FFF   Linear viewport work buffer and scratch (also used as a stack fill window)

0xA38E..0xA8A8   Pseudo 3D renderer and helpers (including the strip blitter)

0xA8B2..0xA8F1   Runtime control block stored inside the unused sprite slot 0
0xA8F2..0xAF71   Active sprite subset bank (26 entries x 64 bytes)

0xB734..         Saved map triplet buffer used by map normalization restore
0xB8B2..         Sprite subset bank A (inactive storage)
0xBF32..         Sprite subset bank B (inactive storage)

0xC5B2..0xC72D   Object queue 0
0xC72E..0xC8A9   Object queue 1
0xC8AA..0xCA25   Object queue 2
0xCA26..0xCBA1   Object queue 3
0xCBA2..0xCD1D   Object queue 4

0xCD1E..0xD6E1   Level map buffer, mode 1 (50x50)
0xD6E2..0xE0A5   Level map buffer, mode 2 (50x50)

0xE0A6..0xEFFF   Input, movement resolution, transient effects, enemy AI
0xF050..0xF5FF   Scheduler, session control, transitions
0xF778..0xF7FF   Timing helpers, overlay presets
0xFBCC..0xFCFF   Beeper stream engine (intermissions, multi voice effect)
```

A useful mental model is: maps and render buffers sit in the 0x8000..0x9FFF band, the renderer starts around 0xA38E, the main gameplay logic lives in 0xE000..0xF000, and the audio stream player is parked near the top of memory.

## The level map byte format

Each map cell is one byte. The program treats it as a compact tagged value:

* low 6 bits (`cell & 0x3F`) are the cell code used by gameplay and most logic
* high 2 bits (`cell & 0xC0`) are a render profile used by the pseudo 3D renderer

This split is explicit in almost every routine, because the first operation is often `AND 0x3F`.

There are two important complications.

First, the wall profile family uses full bytes `0x17`, `0x57`, `0x97`, `0xD7`. In other words, it is the same low 6 bit code (`0x17`), with all four high bit combinations. These are treated as distinct wall profiles by the renderer, and they are preserved as full bytes.

Second, any cell with high bits `0xC0` is also preserved as a full byte by map cleanup logic. This is a technical hook: it lets the program keep extra information in the low bits for a small set of special cells without being destroyed by normalization.

### Map normalization and restoration

The routine `normalize_2500_byte_map_place` at `0xF292` performs an in place cleanup pass over a 2500 byte map.

Its rules are strict and, in practice, define which cell types are considered structural:

* wall profile bytes `0x17`, `0x57`, `0x97`, `0xD7` are left untouched
* otherwise, if the high bits are `0x00`, the cell is rewritten to `0x00`
* if the high bits are `0x40` or `0x80`, the cell is rewritten to just that high bit pattern
* if the high bits are `0xC0`, the full byte is kept

The companion routine `fn_map_normalization_restore` at `0xF27F` calls normalization and then replays a saved triplet log from `0xB734`.

That log is built by `fn_scan_2500_byte_map_emit_selected` at `0xF2BB`, which records the full byte and pointer for a small set of dynamic cell codes:

* `0x01` (queue 3 family)
* `0x0D` (queue 2 family)
* `0x11` (queue 1 family)
* `0x18` (pushable block)
* `0x19` (queue 0 family)
* `0x1B` (directional marker)
* `0x21` (player marker)

The intention is almost certainly: wipe transient debris, keep walls and the renderer’s depth cues, then restore the meaningful movable state.

I am confident in this description because the restore list is literally hardcoded at `0xF2C4..0xF2DE`.

## Runtime state block

The game keeps a compact control block at `0xA8B2..0xA8F1`. This region doubles as sprite slot 0 in the active sprite bank, which is a clever way to reclaim space: code 0 is empty and never needs a sprite.

Some key fields you will see referenced throughout the code:

* `0xA8B6..0xA8BF` are five queue head pointers (queues 0 through 4)
* `0xA8C0` is the phase index used to animate the queue 3 enemy family
* `0xA8C1..0xA8C2` is the current player cell pointer
* `0xA8C4` is the primary counter shown as a HUD bar and used by several interactions
* `0xA8C5` is an objective counter checked as a failure condition in the main loop
* `0xA8C6` stores the last move delta as an 8 bit signed step (`0x01`, `0xFF`, `0x32`, `0xCE`). When used as a 16 bit offset it is sign extended (so `0xCE` corresponds to `0xFFCE`).
* `0xA8CD..0xA8CE` is the 16 bit scheduler timer (decremented each frame)
* `0xA8CF..0xA8D6` are four direction pointers (up, down, right, left) used by the directional interaction subsystem
* `0xA8D8..0xA8DA` are the three progress bytes, checked for the win condition
* `0xA8DB` is the active map mode selector (0, 1, or 2)
* `0xA8DC` is the action and effect bitfield consumed by the action dispatcher
* `0xA8DE..0xA8DF` caches `(row, col)` for the player or for temporary enemy computations
* `0xA8E0..0xA8E7` are marker system pointers and counters

This is the core of “what state exists” in the original program.

## Program structure at a glance

Alien Evolution is structured around a tight per frame loop, with a small number of subsystems called in a fixed order.

The entry point for a gameplay session is `gameplay_session_controller` at `0xF174`. It performs:

* screen and overlay setup
* timer and counter initialization
* map mode selection and mode specific patching
* queue seeding by scanning the active map
* a short scenario preset (audio cue)

Then it enters the per frame main loop at `0xF23D`.

### The per frame loop

The loop body is easy to spot because it is a straight line of calls, followed by three exit checks:

* `per_frame_object_state_update_pass` at `0xE9BC`
* `fn_process_transient_effect_queues_handlers_xe530` at `0xE494`
* `fn_gameplay_movement_control_step` at `0xE0A6`
* `fn_directional_interaction_dispatcher_using_pointer_table` at `0xEB18`
* `fn_patchable_callback_hook_frame_loop` at `0xEDD1`
* `fn_periodic_scheduler_tick` at `0xF050`
* `fn_main_pseudo_3d_map_render_pipeline` at `0xA38E`

After rendering, the loop checks:

* win condition: `0xA8D8..0xA8DA` all equal zero
* failure condition: scheduler timer high byte `0xA8CE` equals zero
* failure condition: objective counter `0xA8C5` equals zero

On completion it jumps to `main_loop_level_complete_transition_path` at `0xF462`. On failure it goes to `main_loop_failure_cleanup_exit_path` at `0xF42B`.

I am confident about the call order and conditions because the loop is explicitly annotated in `skool/AlienEvolution.skool` around `0xF23D`.

### State transitions

The level complete transition path `0xF462` is a compact state machine:

* it calls `fn_active_map_mode_switch_handler` at `0xF3E5` to restore the current map and swap sprite banks as needed
* it runs `fn_level_transition_wait_loop` at `0xF4A4` for a fixed delay with HUD animation
* it increments `var_active_map_mode` at `0xA8DB`
* for modes 0 and 1 it re enters gameplay setup by jumping back to `0xF17A`
* when the mode reaches 3 it runs the ending text sequence, shows the high score flow, and returns to the front end

So the three maps are played in sequence, and mode 3 is a terminal “ending and menu” branch.

## Rendering: pseudo 3D pipeline

The most distinctive engineering feature of Alien Evolution is the renderer: a pseudo 3D projection built from a 2D grid, rendered fast enough to redraw every frame on a 3.5 MHz Z80.

The renderer lives around `0xA38E`.

At a high level it has two stages.

First, it builds a visible cell staging lattice in RAM at `0x89C6`. This is a compact representation of what is currently visible from the player’s position and facing.

Second, it renders that staging lattice into a linear work buffer, then blits it into the Spectrum’s screen memory, handling the ZX bitmap’s unusual row layout.

### Render entry points

There are two entry points that matter:

* `fn_main_pseudo_3d_map_render_pipeline` at `0xA38E` builds the staging lattice and then renders it
* `fn_render_pass_re_entry_stub` at `0xA889` disables interrupts and jumps directly into the render staged lattice part at `0xA40B`

The re entry stub is used when the program updates overlays or other staged UI elements without needing to rebuild visibility from the player pointer.

### Staging lattice builder

The staging builder is the first part of `0xA38E`. In broad terms:

* it reads the current player map pointer from `0xA8C1..0xA8C2`
* it walks the map in a pattern that approximates the player’s field of view
* it writes the encountered cell bytes into the staging buffer at `0x89C6`

The scanning pattern is not a simple rectangle. You can see it in the nested loops at `0xA39F..0xA40B`, where the inner loop increments the map pointer by 1, the outer loop subtracts `0x0040` from the map pointer and also decrements the row counter. The result is a skewed sampling window, which matches the perspective look.

If you want to reproduce the exact view frustum, start by emulating the loop structure at `0xA39F` and inspect how the pointer is adjusted at the end of each row.

### From cell codes to pixels

After the staging lattice is ready, the renderer iterates over it and builds a cell blit buffer at `0x8F80`.

Cells fall into a few categories, handled by different code paths:

* empty cells (`code == 0`) are skipped
* wall profile family bytes (`0x17`, `0x57`, `0x97`, `0xD7`) take a dedicated fast path
* pure render profile bytes (`0x40` and `0x80`) take a dedicated cube blit path
* everything else is drawn via sprite mask data from the active sprite bank

The active sprite bank begins at `0xA8F2`. Each sprite is a 64 byte record containing paired AND and OR masks for a 16 by 16 pattern.

A recurring performance trick here is that the renderer does not interpret masks in a generic inner loop. Instead, it uses a patching routine.

### Self modified cube blitter

`fn_patches_immediate_operands_routine_xa66f_sprite` at `0xA88D` reads mask bytes from the sprite table and writes them into the immediate operands of `fn_frequent_cube_blit_fast_path` at `0xA66F`.

In other words, the game turns “draw sprite X” into “run a specialized blitter whose `AND n` and `OR n` constants have already been baked in”.

This saves instructions in the inner loop, at the cost of occasional self modification when the sprite changes.

I am confident this is the intention because `0xA88D` explicitly scans and rewrites immediate operands of `AND` and `OR` instructions, and it is called from the wall profile handler and other sprite selection paths.

### Strip blit into Spectrum screen memory

Once the cell blit buffer is prepared, the renderer uses `viewport_strip_blit_core` at `0xA595` to copy the linear representation into the Spectrum bitmap at `0x4021`.

Two implementation details are worth noting:

* the Spectrum screen is not linear by rows; `0xA595` contains the address arithmetic needed to hop between bitmap rows and 8 line character bands
* the code uses the stack pointer as a fast bulk fill tool: at `0xA5BE..0xA62D` it sets `SP = 0xA000` and then repeatedly `PUSH`es preloaded values to fill the background window at `0x9100..0x9FFF`

The stack fill trick is a classic Spectrum optimization: `PUSH` is fast, and it writes two bytes at once. Alien Evolution uses it aggressively.

## Sound: ROM beeps and a two stream engine

The game uses the ROM `BEEPER` routine at `0x03B5` for short cues, but it also contains a custom stream player for longer sequences.

The stream engine entry point is `scenario_intermission_beeper_stream_player_loop` at `0xFBCC`.

### Stream structure

The engine reads two byte streams in parallel, with pointers stored at `0xFBE7` and `0xFBEB`. Conceptually, this is channel A and channel B.

Each channel yields a command byte. The core interpreter is `stream_bytecode_interpreter_core` at `0xFC13`.

A byte value of `0x40` is treated as a terminator for that stream.

Other bytes are interpreted as note selectors and duration selectors through tables starting at `0xFCA0`.

### How the two voice effect works

The Spectrum beeper is one bit, so true polyphony is impossible. Alien Evolution approximates it by rapidly alternating between two tone generators.

Inside the inner loop at `0xFC51`:

* the current toggle mask is kept in `A` and mirrored in the alternate accumulator via `EX AF,AF'`
* two counters (in `E` and `L`) are decremented at different rates
* when a counter reaches zero, the output mask is flipped (`XOR`) and the counter is reloaded
* the routine writes the mask to port `0xFE` (via `OUT (0xFE),A`) to flip the beeper state

The effect is a time division multiplexed mixture: not simultaneous tones, but tones switched quickly enough that the ear perceives two lines.

This is one of those areas where the exact details are easier to see in the code than in prose, so the recommended reading path is: start at `0xFBCC`, follow into `0xFC13`, then study the loop around `0xFC51`.

## Dynamic entities: queues, callbacks, and map centric state

Alien Evolution uses a map centric state model.

Most dynamic things are represented directly in the map byte grid, and then a separate sparse structure keeps pointers to the cells that need updating.

There are two families of such structures:

* long object queues in the `0xC5B2..0xCD1D` region
* short transient effect queues embedded in the code region (`0xE4CD`, `0xE4ED`, `0xE50D`)

### Long object queues

Queues 0 through 4 share the same layout: a stream of triplets

* one byte state
* two bytes pointer (little endian) to a map cell

The stream ends when the state byte is `0xFF`.

Queue bases are:

* queue 0 at `0xC5B2`
* queue 1 at `0xC72E`
* queue 2 at `0xC8AA`
* queue 3 at `0xCA26`
* queue 4 at `0xCBA2`

Pointers to these bases are stored in the runtime control block at `0xA8B6..0xA8BF`.

The generic dispatcher is `fn_object_state_update_pass_core` at `0xE9EC`. It takes a callback pointer in `DE` and runs it for every queue entry.

The per frame orchestration is `per_frame_object_state_update_pass` at `0xE9BC`. It routes:

* queue 1 to `fn_queue_1_ai_step` at `0xE704`
* queue 2 to `callback_queue_2_directional_ai_step` at `0xE76F`
* transient executor to `fn_active_transient_effect_executor` at `0xE6B3`
* queue 3 to `callback_queue_3_chase_ai_step` at `0xE848`
* queue 0 to `callback_queue_0_low_bits_toggle` at `0xEA0C`

Queue 4 is not updated every frame. It is used as a staging queue during autonomous expansion.

This callback based queue design is one of the reasons the code is relatively compact: the traversal logic is shared, and behaviour is factored into small routines.

### Short transient effect queues

The transient queues `var_transient_queue_a`, `b`, and `c` live at `0xE4CD`, `0xE4ED`, and `0xE50D`.

Each has:

* a one byte counter at offset 0
* ten triplets `[state, ptr_lo, ptr_hi]`

They are processed by `fn_process_transient_effect_queues_handlers_xe530` at `0xE494`, which iterates each queue and calls a handler core. For queue A the handler core is `fn_transient_queue_handler_core` at `0xE530`.

The transient state bytes are small packed state machines. A very common pattern is:

* state zero means slot is inactive
* bit 7 is used as an armed or phase toggled marker
* the low bits encode a countdown that decrements each frame

The handlers rewrite the map cell codes accordingly and either return a new nonzero state, or return zero to free the slot.

In gameplay terms these are used for weapon effects and short lived hazards. The map remains the source of truth, and the queues provide “which cells should be advanced this frame”.

## Player movement and pushable blocks

Player movement is resolved in a fairly direct way: read input, choose an offset, check the destination code, then commit map updates.

`fn_gameplay_movement_control_step` at `0xE0A6` handles input scanning and dispatch.

The direction attempt entry points are:

* `movement_attempt_map_offset_1_enters` at `0xE27B` (step `+0x0001`, marker code `0x22`)
* `movement_attempt_map_offset_50_enters` at `0xE283` (step `+0x0032`, marker code `0x23`)
* `movement_attempt_map_offset_1_enters_2` at `0xE28B` (step `-0x0001`, marker code `0x21`)
* `movement_attempt_map_offset_50_move` at `0xE293` (step `-0x0032`, marker code `0x24`)

All of them converge into the shared resolver at `0xE298` inside `movement_attempt_map_offset_50_move`.

### Destination code handling

The movement resolver reads `A_code = (HL_dst[0] & 0x3F)` and then follows a sequence of comparisons.

A compact way to state the observed rules is:

* if `A_code == 0x00`, commit a normal move
* if `A_code < 0x15`, jump to `0xE3AE` (a distinct commit path used for low numbered codes)
* if `A_code == 0x18`, attempt to push the block (see below)
* if `0x15 <= A_code < 0x1B`, block the move
* if `0x1B <= A_code < 0x1D`, commit a normal move
* if `A_code == 0x25`, take `special_move_branch` at `0xE341` (it increments `0xA8C4`, beeps, then commits)
* if `0x1D <= A_code < 0x2A`, block the move
* if `A_code == 0x38`, block the move
* otherwise, commit a normal move

Normal commit happens through the shared block at `0xE2CD`:

* `0xA8C1..0xA8C2` is updated to the new cell pointer
* the destination cell is rewritten to `(profile | marker_code)`
* the previous cell is cleared to its high bit profile only
* `(row, col)` in `0xA8DE..0xA8DF` is updated based on the move delta

This commit path is a good representative sample of the program’s style: it maintains a cached pointer, and it treats map bytes as authoritative state.

### Pushable block rule

The block push is implemented as an inlined branch at `0xE308..0xE318` inside the same movement resolver.

When the destination code is `0x18`:

* the code looks one cell further in the same direction
* if that cell is not empty, the move is blocked
* if it is empty, the further cell is written as code `0x18` preserving high bit profile
* then the player move is committed into the original block cell via the shared commit path at `0xE2CD`

So the block literally moves by copying its byte forward and clearing its previous location.

## The directional interaction subsystem

`fn_directional_interaction_dispatcher_using_pointer_table` at `0xEB18` is a separate subsystem that probes cells in four directions and marks or clears them based on a bitfield.

The helper `fn_if_probed_cell_is_empty_mark` at `0xEBD6` is explicit: if a probed cell is empty, it writes code `0x1B` into it.

During gameplay setup, pointers to the `0x1B` cells are discovered and stored as direction pointers at `0xA8CF..0xA8D6`. That makes the directional subsystem a kind of pre indexed interaction feature.

The player facing semantics are explained in `GAME_INFO.md`. From an implementation viewpoint, the important point is that this subsystem is separate from normal movement and runs every frame.

## Periodic scheduler and evolution

Alien Evolution has a periodic scheduler driven by a 16 bit timer at `0xA8CD..0xA8CE`.

The tick routine is `fn_periodic_scheduler_tick` at `0xF050`. Every frame it subtracts 2 from the timer. When the low byte underflows to `0xFF`, the routine treats it as a scheduler event.

Since the low byte is stepped by 2, scheduler events occur every 128 frames, which is about 2.56 seconds on a 50 Hz Spectrum.

On each event:

* the high byte is used as a step index
* a script byte is read from a table selected by the current map mode
* bits in that script byte decide which periodic actions run

The script base pointer is patched at `0xF063` during map mode setup. In practice:

* mode 0 uses the table starting at `0xF0AE`
* mode 1 uses the table starting at `0xF097`
* mode 2 uses the table starting at `0xF080`

A script byte is treated as a bit mask:

* bit 0 triggers `scheduler_triggered_autonomous_step` at `0xF0C5`
* bit 1 triggers `scheduler_triggered_marker_seeding` at `0xF519`

This is where the game’s “things happen if you wait” behaviour comes from.

### Autonomous expansion pass

`scheduler_triggered_autonomous_step` at `0xF0C5` primarily calls `autonomous_expansion_pass` at `0xEC0A`.

This routine is the implementation of the enemy life cycle described in `GAME_INFO.md`.

The key idea is that the enemy population is represented by the long object queues, and evolution is implemented by rotating which physical queue buffer represents which life stage.

At a high level:

* queue 3 is treated as the active adult stage for expansion
* queue 4 is used as an empty staging buffer
* for each queue 3 entry, the routine tries to spawn into the four adjacent cells by calling `fn_queue_insert_helper_xec0a` at `0xEC64`
* newly inserted cells are tagged as code `0x19` in the map
* after processing all entries, `expansion_commit` at `0xECBA` rotates the queue head pointers and retags the map bytes of all queued cells

The expansion pass calls the insert helper on the four neighbourhood offsets in a slightly non obvious sequence:

* `+0x0001`
* `-0x0001`
* `-0x0032`
* `+0x0032`

You can see this explicitly in `0xEC3D..0xEC53`.

When inserting, the helper also updates the three byte progress counter at `0xA8D8..0xA8DA` via `0xEEF5`. So the progress counter is not just a display value, it is part of the expansion book keeping.

The spawn code written into the adult cell itself is selected by `fn_spawn_state_selector_xec0a` at `0xEC88`. Its default is `0x19`, but if the adult cell overlaps the player cell it emits a special player marker code (`0x21..0x24`) based on the player’s move delta. This looks like a collision accommodation mechanism.

### Queue rotation and retagging

The `expansion_commit` routine performs literal pointer swapping of the five queue head pointers at `0xA8B6..0xA8BF`, and then rewrites the cell codes of all queued cells to match their new stage.

Retagging is done by `fn_queue_retag_helper_one_list` at `0xED01`, which iterates one queue and forces each referenced map cell to `(profile | E_code)`.

The family codes used in the commit step are:

* queue 0 uses code `0x19` and toggles it with `XOR 0x03` (so it alternates `0x19` and `0x1A`)
* queue 1 uses base code `0x11`
* queue 2 uses base code `0x0D`
* queue 3 uses base code `0x01`

So after each expansion event, every surviving enemy effectively moves forward one stage, and the adult stage also spawns new stage 0 entries around it.

I am confident about this life cycle interpretation because the queue rotation and retagging logic is explicit in `0xECBA..0xED7B`.

### Marker seeding and the patchable frame hook

The second scheduler action is `scheduler_triggered_marker_seeding` at `0xF519`.

This routine chooses a pseudo random empty map cell (using the `R` register and the timer low byte as entropy) and writes a marker code into it.

It also turns on an otherwise dormant per frame subsystem by patching `fn_patchable_callback_hook_frame_loop` at `0xEDD1`.

At session start, `gameplay_session_controller` writes `0xC9` (RET) into `0xEDD1`, making that call in the per frame loop a no op.

Marker seeding overwrites the first byte with `0x2A`, which makes the routine execute the real body at `0xEDD4`.

The patchable body implements the marker cycling and the all markers collected logic. The completion handler is `all_markers_cleared_handler` at `0xEFC7`, which increments the objective counter at `0xA8C5` and refreshes the HUD.

From an implementation perspective this is a neat pattern: save cycles in the common case by turning an entire subsystem into a single byte RET.

## Enemy AI and difficulty scaling

Enemy behaviour is mostly encoded as movement policies inside the queue callbacks.

Difficulty scaling between levels is implemented in a direct way: by patching a few immediate constants and one opcode byte during map mode setup.

These patches happen in `gameplay_session_controller` around `0xF1A0..0xF232`.

### Directional AI (queues 1 and 2)

`fn_queue_1_ai_step` at `0xE704` and `callback_queue_2_directional_ai_step` at `0xE76F` share a structure:

* the queue entry state encodes a preferred direction via bit flags
* the routine probes two cells ahead in that direction
* a mode dependent block threshold code is compared against that probe
* if blocked, it falls back to a pseudo random direction chooser at `0xE7F3`
* otherwise it tries to move one cell

Movement is allowed into empty cells. Several codes cause a block or special handling. A notable special case is `0x25`, which triggers a contact event branch that increments the primary HUD counter at `0xA8C4` and replaces the destination with an impact marker code.

The block threshold code is a patched immediate constant. For mode 0 it is left as `0x50`, which can never match `(cell & 0x3F)` and therefore disables that particular block rule. For modes 1 and 2 it is patched to meaningful values.

### Chase AI (queue 3)

`callback_queue_3_chase_ai_step` at `0xE848` is the most complex movement routine.

It still starts as a directional mover, but it also:

* updates the visual phase of the enemy by adding `var_runtime_phase_index` at `0xA8C0` to a direction dependent base
* contains a conditional branch that can arm a transient projectile like effect when aligned with the player

That conditional branch is gated by a patchable opcode byte at `0xE8BC` (`patch_queue_3_contact_branch_opcode`).

* in mode 0 it is patched to `0xC9` (RET), disabling the extra behaviour
* in modes 1 and 2 it is patched to `0xC5` (PUSH BC), enabling the full check

When enabled, the routine checks whether the enemy shares a row or column with the player. It converts the enemy map pointer to row and column via `fn_convert_map_pointer_hl_row_column` at `0xEBEB`.

If aligned and facing the right direction, and if the adjacent cell is empty, it writes code `0x39` into the spawn cell and sets the transient effect state triple at `0xE52D..0xE52F`.

The transient executor that consumes `0xE52D` runs inside `fn_active_transient_effect_executor` at `0xE6B3`, which is invoked each frame by `per_frame_object_state_update_pass`.

This is a good example of how subsystems are stitched together by tiny shared state blocks.

## Reimplementing the game from these notes

If the goal is to reproduce Alien Evolution faithfully, the minimum set of moving parts to emulate is roughly:

* the map grid with the exact byte semantics described above
* the long queues and their callbacks, including the queue rotation life cycle in `0xECBA`
* the transient queues and their countdown state machines
* the scheduler tick cadence (128 frames per event) and per mode script tables
* the movement resolver including pushable block rules
* the renderer staging and strip blitting pipeline

The renderer is the hardest piece to reproduce exactly, but it is also the most self contained: it depends on the staging lattice, the sprite bank, and the map byte format.

Where this document makes interpretive claims, they are based on reading the code paths and cross checking with observed gameplay. If you find a mismatch, the `skool/AlienEvolution.skool` listing is the source of truth.
