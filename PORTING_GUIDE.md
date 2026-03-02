# ZX Spectrum → Python Porting Guide

This document describes a reproducible workflow for porting a ZX Spectrum game (Z80, typically 48K) into a maintainable, deterministic Python runtime in the style used in this repository.

A key premise: we are not building a CPU emulator. We are transferring *game semantics* (rules, timing, rendering, audio behavior, and input handling) as precisely as the evidence allows, while implementing those semantics in an architecture that is debuggable, testable, and backend-agnostic.

This guide is organized as a pipeline with explicit deliverables and quality gates. The intended outcome is that two people, working independently on the same binary and the same evidence, converge to compatible ports.

---

## 1. Terminology and invariants

**ZX address**  
A 16‑bit address in the Spectrum address space (`0x0000..0xFFFF`). When we say “routine at `0x7C10`”, we mean the entry point in the snapshot’s address space.

**Frame (port frame)**  
One simulation quantum produced by a single `step(frame_input)` call.

**Host frame**  
A physical backend frame tick (50 Hz in this project’s default backends). Host frames are a rendering/presentation clock, not a gameplay logic clock.

**Frame boundary**  
The exact point where the port must stop computation for the current port frame, assemble a complete `StepOutput`, and return control to the backend. Frame boundaries are explicit in the port (FSM states), not implicit in the Python call stack.

**Synchronization point**  
A place in original code where the game aligns itself to the 50 Hz interrupt cadence. On Spectrum this is often an `EI; HALT` pattern (or a loop that includes `HALT`). In the port, synchronization points typically become frame boundaries.

**Routine**  
A function-like block of code with an entry label and a contract (inputs, side effects, outputs, and control-flow behavior). Not every label is a routine entry: many labels are internal jump targets.

**SkoolKit map**  
A `.ctl` + `.skool` pair that correctly separates code/data/text and provides meaningful names and routine contracts. In this project, the SkoolKit output is treated as a primary knowledge base: Python code should remain traceable back to skool labels and address ranges.

---

## 2. Repository constraints (summary)

Porting decisions should be compatible with the normative architecture. The shortest useful summary is:

- Deterministic behavior is the primary correctness criterion: identical inputs must yield identical outputs and state.
- Game logic is backend-agnostic; backends provide inputs and consume outputs, but do not reach into game internals.
- Runtime execution uses an explicit FSM with persisted state identifiers; frame boundaries are explicit FSM states.
- After initialization, gameplay/runtime code must not read from or write to a raw ROM/snapshot buffer; it operates on named blocks and typed fields.
- Pointer-like values in runtime code are represented as block-bound pointers (`BlockPtr`) or typed pointers (`StructFieldPtr`), not as raw global ZX addresses.
- Screen output is returned as full buffers (bitmap + attributes), not deltas.
- Audio is emitted as semantic commands, not as reconstructed `OUT (0xFE)` waveforms.

The architecture document contains the precise requirements and edge-case policies.

---

## 3. What “done” looks like (deliverables)

A porting effort is structurally “ready” when you have the following artifacts:

1. **Reference start state**
   - A snapshot (or equivalent RAM image) that represents the baseline start state for the runtime.
   - A short description of how it was obtained (loader/depacker details, required emulator options, machine model).

2. **Evidence package**
   - A dynamic execution trace (PC stream + I/O events is usually enough; memory writes are a bonus).
   - Notes on interrupt model and synchronization behavior (IM1 vs IM2, where the handler lives, whether the game relies on `HALT`, what the music driver does).

3. **Fully annotated SkoolKit listing**
   - `.ctl` and `.skool` with correct code/data/text partitioning.
   - Named blocks for major data structures and screen buffers.
   - For each port-relevant routine: a one-line summary + `Args/Returns/def` pythonized annotation.
   - A call graph stable enough that “routine identity” is not changing on every edit.

4. **Python runtime skeleton**
   - A deterministic `reset/step` implementation with explicit frame boundaries (FSM).
   - Screen, input, and audio outputs represented semantically (backend-agnostic).
   - Pointer and data-block infrastructure in place (no raw-buffer reads after initialization).

5. **Ported gameplay paths**
   - Menu and gameplay loops mapped to explicit FSM states.
   - Non-trivial subsystems (render, input polling, audio generation, object updates) represented as Python functions that preserve semantics.
   - A regression mechanism (recorded input replay) that is used continuously while refactoring.

The remainder of this guide follows that order: evidence → skool map → synchronization analysis → Python FSM → refactor into functions → verification.

---

## 4. Stage A. Acquire a stable snapshot

### 4.1. Identify the “analysis snapshot” (baseline)

For many Spectrum games, the distribution image (TAP/TZX/TRD/etc.) is not a useful disassembly target: it contains a loader, and the actual game is often packed and relocated.

For porting, you typically want a RAM snapshot taken at one of these points:

- **Immediately after decompression / relocation**, before gameplay begins.
- **At a stable menu screen**, after initialization has completed.
- **At the start of a new game session**, right after the “start game” transition.

The baseline must be reproducible. If the game seeds RNG from timing noise, capture (and later control) whatever state provides that seed. If the game depends on “time since boot” counters, you need to decide whether to preserve those counters and how they advance in the port.

### 4.2. Collect machine model constraints

Before trusting any trace:

- Confirm whether the game is 48K or 128K and whether it uses bank switching.
- Confirm interrupt mode (IM 1 is common; IM 2 exists and matters).
- Check whether the game relies on contention timing or raster tricks. If it does, the port may need an explicit high-level model of those effects (rare, but not impossible).

Even if the target port is “semantics, not cycles”, you still need a correct understanding of which events the original code uses as timing anchors (interrupts, `HALT`, busy-waits, counters).

### 4.3. Decide what counts as the baseline “start state” in Python

A ported runtime needs a deterministic baseline start state. In practice that means:

- A fixed RAM image (split into named blocks during initialization).
- Fixed initial values for runtime-only Python fields (FSM state, transient pointer bindings, audio pending state).
- A defined initial mode: menu vs gameplay vs intro.

This definition becomes the reference point for `reset()` and for save-state compatibility.

Quality gate: you can restart the game from the baseline snapshot in an emulator multiple times and observe identical early behavior given identical inputs (at least for the parts you intend to preserve).

---

## 5. Stage B. Dynamic tracing in an emulator

Static disassembly alone is rarely sufficient, because Spectrum games blur code and data, use jump tables, and may include self-modifying code. A trace provides ground truth about what is executed and what is touched.

### 5.1. Minimal trace fields that are actually useful

At minimum, collect:

- PC stream (instruction addresses executed).
- Control-flow events: `CALL`, `RET`, conditional/unconditional `JP/JR`, `RST`.
- `HALT` occurrences and interrupt entry points.
- Port I/O: `IN` and `OUT` events (port number + value; include the row-select mask for keyboard scans when possible).

If possible, also collect:

- Memory writes (address + value), at least for writes into code regions and screen regions.
- A per-host-frame marker aligned to the 50 Hz interrupt cadence so you can correlate trace segments with frames.

### 5.2. Use the trace to build an evidence map

From trace data you can build summaries that directly accelerate porting:

- **Executed address coverage**: which ranges are definitely code.
- **Write heatmap**: which memory regions are mutated frequently (state variables, buffers, self-modifying sites).
- **I/O usage profile**:
  - keyboard matrix scan patterns (usually port `0xFE`),
  - Kempston reads (often `0x1F`),
  - beeper/border writes (`OUT (0xFE)`),
  - any “unexpected” ports that imply additional hardware assumptions.

This evidence map is what prevents speculative reverse engineering. When you are unsure whether a block is code or data, the trace usually resolves it.

### 5.3. Identify interrupt behavior early

Determine:

- Where the interrupt handler lives.
- Whether it is used only for timing (`HALT` wake-up), or also performs game logic (music driver, counters, screen effects).
- Whether interrupts are enabled/disabled in long stretches (`DI` / `EI` patterns), and whether `HALT` is always preceded by `EI`.

In a port, interrupt logic typically becomes “per-frame update” work executed inside `step()`. But treat that as a conclusion, not an assumption: confirm what the handler does and when it is expected to run.

Quality gate: you can explain, with evidence, what the original program uses as its timing source(s), and you can point to the addresses involved.

---

## 6. Stage C. SkoolKit: draft `.ctl`, then converge to a correct memory map

Your first SkoolKit output is a scaffold. The real work is turning it into a truthful map: correct partitioning + meaningful names + routine contracts.

### 6.1. Generate a draft `.ctl` (bootstrapping)

Start with an automatically generated `.ctl` based on the snapshot. The goal is to get:

- initial segmentation into code/data/text guesses,
- crude labels,
- initial disassembly that you can navigate.

Do not optimize the draft. Expect large changes once you begin applying trace evidence.

### 6.2. Partition the snapshot into code, data, and text

This is the highest-leverage step. Treat it as a classification problem with evidence.

#### Code

Classify as code when at least one of these is true:

- It appears in the executed PC stream.
- It is reachable from known entry points via plausible control flow (and does not look like structured data).
- It is the target of a confirmed call/jump table.

#### Data

Classify as data when:

- It is read via pointer arithmetic (tables, sprites, maps, masks, font bitmaps).
- It is written by logic routines as structured state.
- It is never executed, and disassembly looks nonsensical.

#### Text / streams

Classify as text/streams when:

- It contains printable character ranges in a known encoding *and* is referenced by printing routines.
- It is consumed by a stream interpreter (menus, overlays, cutscenes).
- It has clear terminators or length fields.

Practical rule: if you are uncertain, bias toward “data” first. Misclassifying data as code is usually more destructive than misclassifying code as data, because it poisons control-flow graphs and creates phantom routines.

### 6.3. Identify anchors: screen memory, large buffers, pointer tables

Before you fully understand gameplay, establish the structural regions:

- **Screen bitmap** (`0x4000..0x57FF` in standard 48K layout) and **attributes** (`0x5800..0x5AFF`).
- Level/map buffers, sprite buffers, object queues.
- Pointer tables (address lists, callback vectors, jump tables).
- “Hot” writable regions from the trace (these are almost always state).

Anchors make later reasoning cheaper: once you know “this is the entity queue” and “this is the level map”, many memory accesses become self-explanatory.

### 6.4. Identify functional subsystems in the listing

Use the trace and the map to label:

- main menu loop,
- gameplay loop,
- render pipeline,
- keyboard/joystick input polling,
- audio driver (beeper/music),
- level loading / decompression,
- random number generation,
- collision / physics / AI queues.

This step is not about perfect names; it is about carving the codebase into units you can reason about and port independently.

### 6.5. Track control flow: direct calls, tail jumps, and dispatch tables

In Z80 code, three patterns matter:

- **`CALL`/`RET`**: function-like, usually ports naturally to Python functions.
- **`JP/JR`**: control transfer without implicit return; often corresponds to state transitions or tail calls.
- **Indirect jumps/calls** (`JP (HL)`, computed targets, table-driven dispatch): interpreters and callback systems.

In the skool map, mark dispatch points explicitly and name the tables if possible. Dispatch points are later turned into Python tables of handlers.

### 6.6. Bring routine blocks to “pythonized” annotation quality

For the routines you will port (not necessarily every helper), add annotation blocks following the project conventions:

- One-line summary in `D <addr> ...`.
- A structured block at routine entry in `N <addr> ...`:
  - `Args: ...` (semantic types/shapes, not register trivia),
  - `Returns: ...` (meaningful outputs and pointer advancements),
  - `def fn_name(...):` plus a compact Python-like body.

See `PYTHONIZER.md` for formatting and indentation rules (`↳` marker), naming conventions, and the fact-first policy regarding uncertainty.

A good annotation is not a transliteration of Z80 instructions. It is a compact, checkable description of semantics and side effects.

### 6.7. Hygiene: keep the listing usable as a knowledge base

Two repo-specific practices that improve long-term maintainability:

- When a routine has a complete pythonized `def` annotation, remove redundant auto-generated per-instruction comments inside that routine (keep only comments that add information not captured by the function block).
- Track pythonization progress in the call-graph lists (`analysis/skool/graphs/..._bottom_up_calls.md`) by marking completed routines as strikethrough, immediately after rebuilding the HTML manual.

Quality gate: for each routine that matters to gameplay, you can answer these questions *from the skool map*:
- What are the inputs (including pointers and implied global state)?
- What state does it mutate?
- What is the output (register/pointer/memory effect)?
- Does it return, or does it transfer control elsewhere?

---

## 7. Stage D. Identify frame boundaries and synchronization

The port needs an explicit frame model. This is where ports become “almost correct” if the cadence model is guessed rather than inferred.

### 7.1. Find synchronization mechanisms in the original

Common Spectrum synchronization patterns:

1. **`EI; HALT`** (or `HALT` inside a loop)  
   The CPU stops until the next interrupt; this is the cleanest frame-boundary candidate.

2. **Interrupt-driven tick counters**  
   The interrupt handler increments a counter; the main loop waits until it changes.

3. **Busy-waits**  
   Loops that wait for port state changes or timing side effects (less common in typical games, more common in raster-heavy code).

The task is to locate where the original program yields to the 50 Hz interrupt cadence (or an equivalent timing source) and how often it yields in each mode.

### 7.2. Do not assume “one interrupt = one gameplay frame”

Some games:

- update the screen every interrupt,
- update gameplay every N interrupts (software divider),
- run heavy render that spans multiple interrupts,
- have different pacing for menus vs gameplay vs intermissions.

Therefore, determine cadence per mode. Use the trace to count how many interrupts occur between repeated visits to a stable point in the loop.

### 7.3. Map synchronization points to port frame boundaries

In the port runtime:

- Every frame boundary is represented by an explicit FSM state.
- `step(frame_input)` must execute logic up to the next boundary and then return one complete `StepOutput`.

A practical approach is:

- Mark every `HALT` reached in a loop as a candidate boundary.
- Validate: between two candidates, does the program perform a coherent “frame worth” of work (input, update, render, audio)?

If the block between halts is not coherent, typical explanations are:
- you are looking at a delay loop rather than a frame loop,
- the program uses multi-halt pacing (one logical update spans multiple interrupts/halts),
- interrupt handler work is substantial and must be accounted for explicitly.

### 7.4. Host-frame delays: modeling “wait N interrupts” without duplicating steps

The repository architecture supports explicit post-step delays via `StepOutput.timing.delay_after_step_frames`.

Interpretation:

- One returned `StepOutput` is always shown for the current host frame.
- `delay_after_step_frames = k` means: after returning this step output, the backend advances **k additional host frames** before calling `step()` again.
- Therefore, the total host frames consumed per `step()` result is `1 + delay_after_step_frames`.

This mechanism is appropriate for:
- original delay loops (`HALT` repeated N times),
- pacing adaptation when original gameplay updates occur slower than 50 Hz,
- long waits that are visible but do not change game state.

### 7.5. What if there is no `HALT` in a loop?

Occasionally the main progression loop does not contain `HALT`. In that case:

1. Infer the effective cadence:
   - how often does the visible screen change?
   - how many interrupts occur per loop iteration?
   - does audio update per interrupt or per iteration?

2. Decide a port policy:
   - choose an internal point as the frame boundary (typically after completing a visible screen update), and
   - apply host-frame delay to match the observed tempo if necessary.

If you must estimate an effective FPS (e.g., render spans multiple interrupts), document the evidence used for the estimate (interrupt counts, screen-change observations, trace markers). This makes later corrections straightforward.

Quality gate: you have an explicit set of boundary states per major mode (menu/gameplay/intermission), and each is justified by trace or observed behavior.

---

## 8. Stage E. First Python control model: an address-level FSM

### 8.1. Why start with a large FSM

Original Z80 programs store execution state implicitly in:

- registers,
- the machine stack,
- mutable global memory,
- and the program counter.

If you immediately rewrite everything into high-level structured Python, it is easy to change control-flow semantics without noticing. A large FSM provides a faithful intermediate model:

- state identifier ≈ routine entry label (often a ZX address),
- explicit representation of continuation,
- explicit stack when needed,
- explicit global memory blocks.

This model is not meant to be elegant. Its function is to create a correctness-preserving bridge from “address graph” to “structured Python”.

### 8.2. A practical structure for the “control” runtime

At this stage, a runtime typically has:

- `self._fsm_state`: an enum/int identifying the next routine/state to execute.
- `self._call_stack`: an explicit stack of return states (only if you need to emulate CALL/RET before refactoring).
- Data blocks (`var_*`, `const_*`, `str_*`) initialized from the snapshot.
- Screen buffers and side outputs (border/flash/audio command queue).
- Helpers for common Z80 semantics:
  - 8-bit and 16-bit wraparound arithmetic,
  - signed/unsigned conversions where needed,
  - pointer-slot read/write (little-endian words),
  - table lookups with bounds checking.

`step(frame_input)` runs a dispatcher loop:
- executes state handlers until a frame boundary is reached,
- then assembles and returns a full `StepOutput`.

### 8.3. Managing “local variables” across boundaries

When a state handler cannot complete in one frame (for example, it is a multi-frame wait or animation), store its continuation locals in an explicit context object (commonly `_fsm_*_ctx` fields). If the runtime supports save-state, those context fields must be included in the persisted dynamic state.

Avoid relying on Python call stack suspension (generators/greenlets). Persisted state must be representable as plain data.

### 8.4. Keep the intermediate model traceable

Two practices reduce drift:

1. Keep routine method names aligned with skool labels (`fn_*`, `callback_*`, etc.).
2. Add a comment above each mapped method with the ZX range, e.g. `# ZX 0xAAAA..0xBBBB`, derived from the skool/ctl label layout.

This makes review and cross-referencing mechanical rather than interpretive.

---

## 9. Stage F. Reduce FSM states to synchronization points; refactor the rest into functions

The address-level FSM can easily produce hundreds of “states”, which is usually unnecessary once boundaries are understood.

Reduction strategy:

1. **Keep only states that represent frame boundaries** (synchronization points) and mode entry/exit points.
2. **Convert everything between boundaries into conventional Python functions**, preserving contracts and side effects.

### 9.1. What remains a state

A handler should remain an FSM state if it must be able to:

- stop and return control to the backend (frame boundary),
- represent a long wait/delay whose duration is externally visible,
- represent a mode switch boundary where pacing differs (menu vs gameplay).

Everything else should be a function that executes to completion within one `step()`.

### 9.2. Refactor order that tends to stay stable

A practical order:

1. Identify boundary states for each major mode.
2. Convert leaf routines into Python functions with explicit args.
3. Convert dispatch tables into Python handler tables.
4. Convert large subsystems one by one (render, input, audio, object updates).
5. Remove explicit `_call_stack` usage where possible by turning CALL/RET into normal Python calls.

Quality gate: `_fsm_state` count is small (typically one per boundary + a small number for mode transitions), while the bulk of logic lives in functions with explicit signatures.

---

## 10. Stage G. Pythonizing routines: turning Z80 contracts into explicit functions

This stage is where the skool annotations pay off. The task is to make implicit calling conventions explicit.

### 10.1. Make arguments explicit

Most Z80 routines receive inputs through:

- registers (`A`, `HL`, `DE`, `BC`, `IX/IY`),
- stack parameters pushed before `CALL`,
- implicit global variables in RAM.

In Python, represent these inputs explicitly:

- use `int` for scalar values (`u8`/`u16`),
- use typed pointer objects (`BlockPtr`, `StructFieldPtr`) for pointer semantics,
- access global state via named runtime fields rather than raw ZX addresses.

The goal is not to preserve register mechanics; it is to preserve *dataflow semantics*.

### 10.2. Specify outputs and side effects precisely

Z80 “returns” results via:

- updated registers,
- advanced pointers (`HL` now points to the next record),
- written memory,
- flags.

In Python, choose one of these patterns:

- return a value explicitly when it is semantically a function result,
- return updated pointers explicitly when pointer advancement is part of the contract,
- keep large side effects as runtime mutations (screen buffers, global blocks),
- avoid modeling flags as a first-class concept unless a routine depends on them across a boundary.

Update the corresponding skool routine annotation to match the chosen Python contract (fact-first; if uncertain, mark uncertainty).

### 10.3. Multiple entry points into one tail

A common pattern in Z80 is:

- entry point A sets a default parameter,
- entry point B sets a different parameter,
- both fall through into the same core tail.

In SkoolKit, it is often correct to keep both entry labels (for traceability). In Python, common representations are:

1. One function with a parameter (possibly with a default).
2. Wrapper functions for each entry that call a shared core with explicit constants.

Choose based on clarity and evidence. Preserve the ability to point from a Python wrapper to the corresponding skool entry address.

### 10.4. Tail calls and “far jumps” (no `RET`)

If a routine ends with `JP other_routine` (or otherwise transfers control without returning), treat it as control flow.

In Python, this typically becomes one of:

- an explicit FSM transition (`self._fsm_state = ...`),
- a direct call to the next routine (tail-call style) when it is still within the same port frame,
- a structured loop that mirrors the original dispatcher.

The key requirement is semantic equivalence: the original does not return to the caller, therefore the port must not silently return to an earlier point.

### 10.5. Indirect dispatch (jump tables, callback vectors)

Patterns like `JP (HL)` or “load address from table and jump” are typically:

- per-object behavior dispatch,
- AI callback dispatch,
- stream interpreter command handlers.

Represent them in Python as:

- a list/dict of callables,
- explicit index validation (fail fast if the table index is out of range),
- explicit argument signatures.

Avoid “compute a ZX address and then map it through a resolver” in gameplay loops. Once blocks and pointers are established, runtime logic should operate on those types directly.

### 10.6. Self-modifying code

Self-modifying code usually appears as writes into the code region, typically patching:

- immediate operands (`LD A,imm`),
- conditional jump opcodes or targets,
- table entries embedded inline.

Do not emulate byte patching in Python. Instead:

1. Identify each patch site (trace makes this straightforward).
2. Determine its semantic meaning (mode flags, selected handler, constants).
3. Replace patch bytes with explicit runtime fields (e.g., `self.patch_mode`, `self.patch_jump_index`).
4. Use these fields to control behavior in refactored code.

This preserves semantics while making state explicit, serializable, and testable.

Quality gate: no remaining writes into “code memory” exist as hidden behavior controls; each is represented as explicit state.

---

## 11. Stage H. Memory model, blocks, and pointer discipline

The port’s memory model is one of the strongest determinants of long-term maintainability.

### 11.1. Named blocks as the post-init source of truth

After initialization, runtime code should not read from an undifferentiated raw snapshot buffer. Instead:

- declare named `var_*`, `const_*`, and `str_*` blocks,
- initialize them from the snapshot (or explicit Python literals),
- perform all reads/writes through those blocks.

This enables:
- bounds checks,
- serialization discipline,
- auditability (“what can change” vs “what is immutable”),
- migration from byte tables to typed structures without losing traceability.

### 11.2. Mutable vs immutable blocks

A practical convention aligned with the repository:

- `var_*` blocks are mutable `bytearray`.
- `const_*` and `str_*` blocks are immutable `bytes`, unless explicitly documented exceptions exist.
- Stable one-byte and two-byte state values can become typed `int`/records once the semantics are stable; do not keep redundant “byte buffer + typed mirror” unless there is a concrete need.

When initializing a typed block/field from snapshot data, include a comment documenting the originating ZX address range.

### 11.3. Pointers: use `BlockPtr` / `StructFieldPtr`

Use `BlockPtr` for byte-addressable buffers (screen buffers, level maps, packed tables). Use `StructFieldPtr` (or typed equivalents) for typed structures (records, arrays of records).

Key practices:

- pass pointer-like arguments as pointer objects, not as integer ZX addresses,
- keep pointer arithmetic block-local (offset-based),
- avoid `BlockPtr → ZX addr → BlockPtr` roundtrips in gameplay paths.

If you must accept legacy integer addresses temporarily, constrain them to explicit conversion boundaries and fail fast on unknown values.

### 11.4. Pointer-slot words in memory

Many Z80 games store pointers as 16-bit little-endian words in RAM. Handle these with dedicated pointer-slot helpers that read/write pointer slots logically.

A practical rule: if a memory location semantically stores a pointer, treat it as such everywhere. Do not sometimes treat it as `u16` and sometimes as an address-like int.

### 11.5. Known out-of-bounds behavior

Original games sometimes read “past the end” of buffers, either accidentally or as a performance trick.

Python must not perform out-of-bounds reads/writes. When you identify such behavior, choose an explicit containment policy that preserves intent (e.g., modulo normalization for toroidal maps) and document it near the relevant subsystem.

---

## 12. Stage I. Screen, input, audio: expressing ZX-visible effects

### 12.1. Screen representation

A common and effective choice is to keep the canonical screen representation in ZX-native layout:

- bitmap (6144 bytes),
- attributes (768 bytes).

Benefits:

- matches the original memory layout (blitters and printers port cleanly),
- backends can convert ZX layout to host pixels as a pure function,
- screen output is fully deterministic and easy to hash/compare.

### 12.2. Input representation: keyboard matrix semantics

Spectrum keyboard reads are matrix-based and active-low. A correct port must represent:

- all 8 keyboard rows,
- per-row bits (multiple keys simultaneously),
- active-low logic (pressed bit = 0).

In this repository, `FrameInput.keyboard_rows` is the canonical representation (8 bytes in hardware row order).

If edge-triggered behavior is needed (“on press”), derive it explicitly by comparing current vs previous snapshots.

### 12.3. Audio representation: semantic commands, not port writes

Many games use `OUT (0xFE)` for border color and beeper toggling. In a port, treating those as “hardware writes” is usually the wrong abstraction.

Prefer semantic audio commands with explicit parameters:

- frequency,
- duration,
- volume,
- waveform/tone type,
- channel.

If the original uses a music driver, port the driver’s semantic outputs rather than its bit-level toggling. For correctness work, focus on reproducing gameplay-significant audio behavior (events, durations, cadences), not on re-synthesizing an exact beeper waveform.

---

## 13. Stage J. `reset/step`, timing, and deterministic execution

The runtime API is minimal by design:

- `reset()`
- `step(frame_input) -> StepOutput`

### 13.1. `reset()`

`reset()` restores the baseline start state. It must not:

- advance gameplay,
- consume input,
- emit frame output.

It is state restoration to “frame 0”.

### 13.2. `step(frame_input)`

`step()` must:

- consume exactly one input snapshot,
- compute exactly one port frame,
- stop at the next frame boundary (explicit FSM state),
- return a complete `StepOutput`:
  - full screen buffers (bitmap + attrs),
  - per-frame side outputs (flash/border/audio),
  - timing payload (`delay_after_step_frames`).

If the current frame must be followed by a multi-host-frame wait, represent it via `delay_after_step_frames` rather than emitting duplicated step results.

Quality gate: running the runtime with the same `FrameInput` sequence yields identical `StepOutput` sequences (and identical saved states), independent of backend.

---

## 14. Library structure in this repository

This section documents the main building blocks used by the port. It intentionally does not describe CLI utilities or command-line entry points.

### 14.1. Core data types and the backend protocol

The runtime/backends interact only through a small protocol:

- **Input**: `FrameInput`
  - `keyboard_rows`: 8-row active-low matrix snapshot per port frame (supports chords).
  - optionally other inputs (Kempston, etc.) depending on runtime.

- **Output**: `StepOutput`
  - full screen output (bitmap + attrs),
  - side outputs (border/flash),
  - `audio_commands`: semantic audio commands for this frame,
  - `timing.delay_after_step_frames`: additional host frames to advance before the next `step()` call.

Backends follow a simple rule:
- if `delay_after_step_frames > 0`, advance host-frame time without calling `step()` until the delay is consumed.

Some runtimes/backends may additionally support “advance host frame without gameplay step” helpers; if present, they must not mutate gameplay state.

### 14.2. `alien_evolution.zx` - ZX service layer and shared abstractions

Common responsibilities:

- runtime protocol (`reset/step`),
- canonical input/output types (`FrameInput`, `StepOutput`, `StepTiming`, `AudioCommand`),
- ZX screen layout helpers and buffer conventions,
- pointer types (`BlockPtr`, `StructFieldPtr`) and safe memory access helpers,
- save/load state envelope and manifest-driven persistence helpers (e.g., `StatefulManifestRuntime`),
- a minimal ZX service layer (`ZXSpectrumServiceLayer`-style) that:
  - owns screen buffers and per-frame side outputs,
  - provides keyboard-matrix read semantics,
  - collects semantic audio commands.

Everything here must remain backend-agnostic.

### 14.3. Game module - blocks, routines, FSM

A game port module typically contains three layers:

1. **Data image / blocks**
   - `var_*` mutable blocks (`bytearray`),
   - `const_*` and `str_*` immutable blocks (`bytes`),
   - optional typed structures (dataclasses, typed lists) when semantics are stable.

2. **Logic / routines**
   - methods corresponding to skool routines (`fn_*`, `callback_*`), with traceable names,
   - helper functions replacing common Z80 idioms (copy/fill, pointer-slot ops, table decoders),
   - explicit, testable contracts for each ported routine.

3. **FSM and mode loops**
   - `_fsm_state` identifies the current boundary state,
   - each boundary handler performs “one port frame in this mode” and transitions deterministically,
   - multi-frame waits are represented via timing delays or explicit wait states with persisted context.

### 14.4. `alien_evolution.pyxel` - interactive backend

Responsibilities:

- sample host input and build `FrameInput`,
- run the host frame loop at a stable rate (50 Hz by default),
- call `runtime.step(...)` only when no post-step delay is pending,
- apply post-step delay by advancing host frames without stepping gameplay,
- render `StepOutput` screen buffers and play audio commands,
- optionally maintain rollback history via periodic checkpoints (host-frame based).

### 14.5. `alien_evolution.fileio` - headless backend

Responsibilities:

- read scripted `FrameInput` streams (e.g., JSONL or recording formats),
- execute deterministic stepping and emit outputs (JSONL traces, frame dumps),
- apply post-step delays correctly (advance host time without extra gameplay steps),
- support loading/saving runtime state envelopes when the runtime implements it.

The file I/O backend exists primarily for regression testing and reproducible experiments.

---

## 15. Verification: keeping refactors honest

Porting is experimental work. The practical objective is to make errors detectable and localized.

### 15.1. Determinism checks

Checks that should always pass:

- identical input stream ⇒ identical `StepOutput` stream,
- `save_state → load_state → replay` does not change outputs for the same future inputs.

When these fail, treat it as a correctness bug. Non-determinism makes debugging and validation significantly harder.

### 15.2. Differential comparison against the original

Useful comparisons include:

- screen hashes at frame boundaries,
- key state variables at known points (counters, mode flags),
- audio command sequences for simple effects,
- trace-aligned events (“this routine is called once per gameplay frame”).

Avoid “feels better” heuristics as a correctness criterion. If you deliberately diverge (e.g., to contain an out-of-bounds bug), document the policy explicitly.

### 15.3. Instrumentation that pays off

Low-effort instrumentation with high payoff:

- per-frame “mode + boundary state” logs,
- counters for calls to legacy global-address helpers (to ensure they decrease),
- assertions on pointer bounds and block identities,
- a set of “known frame markers” (game start, death sequence start, level transition).

---

## 16. Practical milestone checklist

### Skool map milestones

- [ ] Baseline snapshot defined and reproducible.
- [ ] Trace collected; executed code coverage is understood.
- [ ] Code/data/text partition is stable (no major reclassification churn).
- [ ] Major data blocks identified and named (`var_*`, `const_*`, `str_*`).
- [ ] Main mode loops identified (menu/gameplay/intermission).
- [ ] Render/input/audio routines identified.
- [ ] Port-relevant routines have `Args/Returns/def` annotations per `PYTHONIZER.md`.
- [ ] Pythonization progress tracked in the bottom-up call graph lists.

### Python runtime milestones

- [ ] `reset()` restores baseline state deterministically.
- [ ] `step()` consumes one input snapshot and returns one full `StepOutput`.
- [ ] Frame boundaries are explicit FSM states.
- [ ] Synchronization policy is implemented (HALT-derived boundaries and/or explicit delays).
- [ ] Screen buffers are produced in a stable canonical format each step.
- [ ] Input is modeled as keyboard matrix (and joystick if applicable).
- [ ] Audio is emitted as semantic commands.
- [ ] Raw snapshot buffer is not accessed after initialization.
- [ ] Pointer discipline is in place (`BlockPtr`/typed pointers), with minimal global-address arithmetic.
- [ ] Regression replay exists and is used continuously during refactors.

---

## 17. Evidence discipline (why the process is structured this way)

The workflow above is designed to keep decisions grounded:

- trace data answers “what actually executes and when”,
- skool annotations capture routine contracts and uncertainty explicitly,
- Python refactors proceed under deterministic regression.

That discipline keeps large ports tractable: behavior changes remain observable, reviewable, and reversible.
