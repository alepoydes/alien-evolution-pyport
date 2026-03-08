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

## Sound: ROM beeps, stream music, and splash noise cells

Alien Evolution uses two distinct audio systems:

* the Spectrum ROM `BEEPER` routine at `0x03B5` for short cues and paced helper calls
* a custom stream engine at `0xFBCC` for menu music, gameplay splash audio, ending tail audio, and failure / cleanup audio

The stream player entry point is `scenario_intermission_beeper_stream_player_loop` at `0xFBCC`.
It is the part that matters for splash screens.

### Stream presets and where splash audio comes from

There are three preset entry points:

* preset A at `0xF149`: pre-level gameplay splash and ending post-text tail
* preset B at `0xF152`: front-end menu music
* preset C at `0xF15B`: failure / cleanup return path

Preset A is the one used by the gameplay splash screens discussed in this repository.
Its raw byte streams live at:

* `const_scenario_preset_a_stream_1` at `0x7E15`
* `const_scenario_preset_a_stream_2` at `0x7E56`

The interpreter state block is `0xFBE4..0xFBEF`:

* `0xFBE4` current command byte from stream A
* `0xFBE5` current command byte from stream B
* `0xFBE6` latched output seed used by the audio routines
* `0xFBE7..0xFBEE` stream pointers
* `0xFBEF` timing / control byte

One detail matters a lot when reading preset data: `fn_stream_byte_fetch_helper` at `0xFBF0` increments the stored pointer before reading the byte.
So the first raw byte in each preset is a seed / skipped byte, not the first audible command.

For preset A this means:

* raw bytes start with `0x16` in both streams
* the first effective command pair is `0xB4 / 0x29`, not `0x16 / 0x16`

### Ordinary music path

The core interpreter is `core_command_interpreter_scenario_stream_engine` at `0xFC13`.
For ordinary command pairs it enters the two-divider loop at `0xFC40..0xFC81`.

This loop implements the familiar "fake two-voice Spectrum beeper" trick:

* one divider lives in `E`
* one divider lives in `L`
* both toggle the same beeper latch bit via `XOR 0x10`
* the current latch value is written with `OUT (0xFE),A`

So the game does not have true polyphony. It time-division multiplexes two divider-controlled toggles fast enough that the ear hears two lines.

In preset A, the harmonic tail at the end of the splash comes from this ordinary music path.
The effective low tones are:

* `0xF7 / 0x29` -> about `87.0 Hz`
* `0xFA / 0x29` -> about `102.8 Hz`
* `0xFC / 0x29` -> about `114.7 Hz`

These are interleaved with noise words; the splash does not switch to a separate music engine.
The second divider in these tail words remains present as a very fast carrier component, so a faithful reconstruction should keep the full two-divider behavior even though the low tone is what stands out perceptually.

### Special command path and splash microcells

The more interesting splash sounds come from the special-command path at `0xFCD6..0xFCF8`.

For a command byte `A_cmd`, the dispatcher:

* takes `D_bits` from `0xFBE5`, the paired byte from stream B
* normalizes timing parameters from `0xFBEF`
* rotates `A_cmd`
* executes exactly four subcalls
* for each subcall, either:
  * calls `bitstream_pulse_generator()` at `0xFD0E`, or
  * calls `pre_delay_calibration_helper()` at `0xFC87`

Those four subcalls are the natural "microcells" of the splash-noise system.

With the preset-A timing byte `0xEE`, the normalized values are:

* `A_inv = (~0xEE) & 0xFF = 0x11`
* `C_delay = 0x11`
* `E_wait = 0x04`

That gives the following exact microcell durations:

| Symbol | Source path | `D_bits` | Duration | `OUT (0xFE)` count | Practical meaning |
| --- | --- | --- | --- | ---: | --- |
| `_` | `pre_delay_calibration_helper(C_wait=4)` | none | `27.236 ms` | 0 | timed silence |
| `1` | `bitstream_pulse_generator(C_repeat=4, D=0x29)` | `0x29` | `27.035 ms` | 384 | sparse ROM-LSB replay, heard as the type-1 chirp |
| `2` | `bitstream_pulse_generator(C_repeat=4, D=0x01)` | `0x01` | `26.594 ms` | 128 | very sparse replay, heard as the type-2 mid buzz |
| `3` | `bitstream_pulse_generator(C_repeat=4, D=0xFF)` | `0xFF` | `28.120 ms` | 1024 | dense replay, heard as the type-3 hash |

These microcells are source-level facts. They come directly from the Z80 routines, not from listening to a WAV capture.

### What `bitstream_pulse_generator` actually does

The key routine is `bitstream_pulse_generator` at `0xFD0E`.
Its behavior is exact and important:

* `A_port` starts from `0xFBE6`
* `B` starts at `0x00`
* `HL` starts at `0x03E8`
* every inner iteration performs `RRC D`
* if carry is clear, no audio output happens; the routine only burns time
* if carry is set:
  * `HL` is incremented
  * `BIT 0,(HL)` reads the least significant bit of the ROM byte at that address
  * bit 4 of `A_port` is set or reset from that ROM bit
  * `OUT (0xFE),A` writes the value to the beeper / border port

So `1`, `2`, and `3` are not three unrelated noise colors.
They are the same ROM-derived bit phrase replayed at different densities.

All active microcells restart from the same ROM tap address `0x03E8`.
The beginning of the ROM-LSB phrase is therefore the same every time:

```text
ROM[0x03E9] bit0, ROM[0x03EA] bit0, ROM[0x03EB] bit0, ...
0, 1, 0, 1, 1, 1, 1, 1, 1, 1, 0, 1, ...
```

The difference between `1`, `2`, and `3` is only how often the routine reaches the `carry set` branch:

* `1` (`D=0x29`) uses the repeating carry mask `1 0 0 1 0 1 0 0`
* `2` (`D=0x01`) uses the repeating carry mask `1 0 0 0 0 0 0 0`
* `3` (`D=0xFF`) uses the repeating carry mask `1 1 1 1 1 1 1 1`

This changes the density of `OUT (0xFE)` events:

* `1` replays the ROM-LSB phrase at about `14.2 kHz`
* `2` replays it at about `4.8 kHz`
* `3` replays it at about `36.4 kHz`

That is the source-level explanation for the three splash noise timbres.

There is no explicit envelope or pitch sweep variable in these routines.
The quasi-tonal or falling impression of the audible type-1 chunk comes from replaying the same short, finite ROM-LSB phrase from the same start address every time `HL` is reset to `0x03E8`.

### Four-cell command words

For preset A, the special command bytes collapse to four fixed four-cell words:

| Command pair | Four-cell word | Audible role |
| --- | --- | --- |
| `0xB4 / 0x29` | `_1__` | one type-1 burst inside a 4-cell frame |
| `0xEC / 0x01` | `22__` | one type-2 burst inside a 4-cell frame |
| `0xF3 / 0xFF` | `__33` | late type-3 burst |
| `0xEE / 0xFF` | `333_` | early type-3 burst |

Two important consequences follow directly from the source:

* type 1 is never `11` or longer in preset A; it is always a single `1` inside `_1__`
* type 2 is always `22`; it never appears as a single `2`
* only type 3 can form longer active runs across command boundaries

The last point is crucial for understanding the splash recording.
Adjacent words can merge like this:

```text
__33 333_  ->  __33333_
```

So the source can produce type-3 runs of:

* `33`
* `333`
* `33333`

That exactly explains why the dense noise region sounds like one family with variable lengths, while type 1 and type 2 behave like much more stable motifs.

### From microcells to real audible macrocells

To talk about the recording, it is useful to introduce a second layer of terminology.
These "macrocells" are not a second hidden source format. They are perceptual phrases heard in the captured splash audio.

The repository keeps representative captured examples in:

* `resources/1.wav` for the type-1 macrocell
* `resources/2.wav` for the type-2 macrocell
* `resources/3.wav` for the type-3 macrocell

The safest mapping is:

* type-1 macrocell: one `_1__` command word, perceived as a chirp-like phrase
* type-2 macrocell: one `22__` command word, perceived as a short mid-band buzz
* type-3 macrocell: one `__33` or `333_` word, or a merger of neighboring type-3 words, perceived as dense hash
* harmonic macrocell: one ordinary music word (`87.0 Hz`, `102.8 Hz`, `114.7 Hz`)

This is where source and audio finally line up:

* the stream engine concatenates microcells literally
* the beeper, speaker, capture chain, and listening window make each 4-cell word sound like one audible phrase
* type-3 phrases vary in length because type-3 active runs can cross word boundaries
* type-1 and type-2 phrases stay much more stable because their active microcells do not merge the same way

There is no hidden source-side transformation from `_1__22__` into `11112___`.
The command stream is still `_1__22__`.
What changes is only how that literal 1-bit sequence is perceived and measured after hardware and acoustic filtering.

### Preset-A splash scenario in byte pairs

The effective preset-A command sequence is:

```text
B4/29 EC/01 B4/29 B4/29 EC/01 B4/29 B4/29 B4/29
EC/01 EC/01 F3/FF B4/29 B4/29 B4/29 B4/29 EC/01
EC/01 EC/01 F3/FF F3/FF EE/FF B4/29 EE/FF EE/FF
F3/FF EC/01 F3/FF EC/01 F3/FF EE/FF EE/FF B4/29
EC/01 F3/FF EC/01 F3/FF EE/FF EE/FF F3/FF B4/29
EC/01 F3/FF B4/29 EC/01 F3/FF B4/29 EC/01 F3/FF
EE/FF EE/FF F3/FF EC/01 F3/FF F7/29 F3/FF F7/29
F3/FF FA/29 F3/FF FA/29 EE/FF FC/29 EE/FF
```

The final five harmonic entries are ordinary music words:

* `F7/29`
* `F7/29`
* `FA/29`
* `FA/29`
* `FC/29`

### Preset-A splash scenario in microcells

Expanding every special word gives:

```text
_1__ 22__ _1__ _1__ 22__ _1__ _1__ _1__
22__ 22__ __33 _1__ _1__ _1__ _1__ 22__
22__ 22__ __33 __33 333_ _1__ 333_ 333_
__33 22__ __33 22__ __33 333_ 333_ _1__
22__ __33 22__ __33 333_ 333_ __33 _1__
22__ __33 _1__ 22__ __33 _1__ 22__ __33
333_ 333_ __33 22__ __33 87Hz __33 87Hz
__33 102.8Hz __33 102.8Hz 333_ 114.7Hz 333_
```

This form is the most useful one if you want to synthesize the splash from game data without guessing.

### Preset-A splash scenario in macrocells

If you prefer the perceptual names instead of source symbols, the same scenario can be read as:

```text
T1 T2 T1 T1 T2 T1 T1 T1
T2 T2 T3late T1 T1 T1 T1 T2
T2 T2 T3late T3late T3early T1 T3early T3early
T3late T2 T3late T2 T3late T3early T3early T1
T2 T3late T2 T3late T3early T3early T3late T1
T2 T3late T1 T2 T3late T1 T2 T3late
T3early T3early T3late T2 T3late 87Hz T3late 87Hz
T3late 102.8Hz T3late 102.8Hz T3early 114.7Hz T3early
```

Here:

* `T1` means the `_1__` word
* `T2` means the `22__` word
* `T3late` means the `__33` word
* `T3early` means the `333_` word

The distinction between `T3late` and `T3early` matters, because it controls whether the dense hash begins in the last two cells of the frame or the first three.
When neighboring type-3 words touch, this phase difference determines whether the audible run is `33`, `333`, or `33333`.

### How to reconstruct the real splash sounds from game data

If the goal is to rebuild the original splash sounds from the game data, the reliable procedure is:

1. Start from the preset stream pointers (`0x7E15` and `0x7E56` for preset A).
2. Apply the fetch-helper convention: increment each pointer before reading, so the first effective word is `0xB4 / 0x29`.
3. For each word:
   * if it is an ordinary music word, run the divider-based `0xFC40..0xFC81` path
   * if it is a special word, expand it into four microcells via `special_command_dispatcher`
4. For each `_` microcell, emit silence for `27.236 ms`.
5. For each active microcell `1`, `2`, or `3`, run the exact `0xFD0E` bitstream routine:
   * `HL = 0x03E8`
   * `B = 0x00`
   * `C = 0x04`
   * `D = 0x29`, `0x01`, or `0xFF`
   * replay the ROM LSB stream through bit 4 of `OUT (0xFE),A`
6. Concatenate the resulting 1-bit waveform exactly in source order.
7. Only after that, if desired, apply speaker / acoustic smoothing or backend-specific rendering.

The important part is step 5.
If you skip the actual `0xFD0E` logic and replace it with a generic noise source, you lose the mechanism that makes the splash sound recognizable.

For splash audio, the original game is not playing abstract "noise notes".
It is replaying a specific ROM-LSB phrase at different densities, framed into four-cell words, and then concatenating those words into the scenario script above.

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
