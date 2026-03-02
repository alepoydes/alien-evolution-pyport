# Command-line utilities, headless runner, and data exchange formats

This repository provides two ways to run the port:

- Interactive mode: a Pyxel window with real-time input, rendering, and audio.
- Headless/offline mode: deterministic frame stepping driven by recorded inputs, with machine-readable outputs.

This document is a reference for:

- all runnable entry points shipped with the repo,
- their command-line flags (when applicable),
- offline/headless execution workflows,
- the JSONL telemetry format (input + output),
- the Fuse-oriented interchange formats supported by the project (RZX and FMF).

The intent is reproducibility. When the same runtime version is driven by the same input frames, the outputs are expected to be deterministic.


## 1. Inventory: runnable entry points

### Console scripts (preferred)

These names are defined as `project.scripts` entry points (see `pyproject.toml`). If you use `uv`, run them as:

```bash
uv run <command> [args...]
```

If the package is installed, they are available directly on `PATH` as `<command>`.

- `alienevolution`  
  Interactive Pyxel runner for the full game port.

- `demoline`  
  Interactive Pyxel runner for a minimal “demo line” runtime (useful for verifying the rendering + stepping pipeline in isolation).

- `alienevolution-cli`  
  Headless/offline runner for the full game port (JSONL/RZX input; JSONL and/or FMF output; optional state load/save).

- `demoline-cli`  
  Headless/offline runner for the demo runtime.

- `fmf-player`  
  Pyxel viewer for FMF recordings produced by the headless runner (and, in many cases, by Fuse).


### Python module entry points (equivalent)

These are useful when running from source without installing scripts:

- `python -m alien_evolution`  
  Equivalent to `alienevolution`.

- `python -m alien_evolution.alienevolution.cli`  
  Equivalent to `alienevolution-cli`.

- `python -m alien_evolution.demoline.cli`  
  Equivalent to `demoline-cli`.

- `python -m alien_evolution.pyxel.fmfplayer --input <file.fmf> ...`  
  Equivalent to `fmf-player`.


### Repo-local tools

These are not installed as console scripts; they are executed directly from the repo checkout:

- `tools/check_runtime_global_ptr_usage.py`  
  A guardrail tool for the porting process (static analysis of `AlienEvolutionPort`), ensuring that the number of remaining “global-address helper” call sites does not increase.


## 2. Interactive mode (Pyxel)

Interactive mode runs a Pyxel window at a fixed host refresh rate (default: 50 Hz). The backend samples host input every host frame and drives the runtime using the frame-step contract:

- input: one `FrameInput` snapshot per step,
- output: one `StepOutput` with screen, border/flash, audio commands, plus timing metadata.

The interactive backend also supports rollback-like workflows if the runtime implements state save/load.


### 2.1 `alienevolution`

Run:

```bash
uv run alienevolution
```

Controls (default “modern layout”):

- Movement: `W` / `A` / `S` / `D`
- Action / fire: `Space`
- Secondary / overlay action: `Enter`

Quality-of-life hotkeys (interactive runner, not game logic):

- `F10`: reset runtime to baseline start state
- `F5`: quick-save state to `pyxel_quicksave.state.json` in the current working directory
- `F9`: quick-load from that quick-save file
- `F8`: rollback to the previous checkpoint (if available)
- `F7`: force a checkpoint immediately

Notes on rollback/checkpointing:

- Checkpoints are stored in host-frame units.
- By default the runner captures one automatic checkpoint every 500 host frames (10 seconds at 50 Hz) and keeps up to 120 checkpoints.
- Checkpoints store full runtime state envelopes (see “State JSON format”).


### 2.2 `demoline`

Run:

```bash
uv run demoline
```

This is a small runtime used to validate the stepping/rendering pipeline without the full game.


### 2.3 Timing: step frames vs host frames

The runtime may request “post-step delay” using `StepOutput.timing.delay_after_step_frames`.

Interpretation:

- One `step()` call always produces exactly one “step frame” of gameplay logic.
- After the step, the backend may advance additional host frames without calling `step()`. That number is `delay_after_step_frames`.
- During those delay-only host frames, the backend may still update its own clocks (e.g., flash phase) via `advance_host_frame()`.

This matters for telemetry and offline replay: a run with delays is not a strict 1:1 mapping between “step index” and “host frame index”.


## 3. Headless/offline mode (file I/O runner)

Headless mode executes the same `reset()/step()` runtime contract but replaces interactive I/O with file/stdin/stdout streams.

Primary use cases:

- deterministic replay from recorded inputs,
- dataset generation (screen + audio + timing telemetry),
- regression tests (“same inputs → same outputs”),
- running without a window (servers/CI).

There are two headless runners that share one CLI contract:

- `alienevolution-cli`
- `demoline-cli`

Only the runtime differs.


### 3.1 CLI synopsis

```bash
uv run alienevolution-cli [--frames N] [--input PATH|- | --input-rzx PATH]
                         [--output PATH|-] [--output-fmf PATH]
                         [--load-state PATH] [--save-state PATH]
```

Arguments:

- `--frames N`  
  Non-negative integer.

  Semantics depend on input mode:

  - With `--input-rzx`: `N` is the number of *additional* frames after the RZX recording length.
  - With `--input` (JSONL):
    - If omitted: run until input EOF.
    - If provided: run exactly `N` frames; if input ends early, missing frames are filled with neutral input.
  - With no input source: `--frames` is required.

- `--input PATH` or `--input -`  
  JSONL input stream (one input object per line). `-` means stdin.

- `--input-rzx PATH`  
  RZX input recording (file only). `--input` and `--input-rzx` are mutually exclusive.

- `--output PATH` or `--output -`  
  JSONL output stream. `-` means stdout.

- `--output-fmf PATH`  
  FMF video output (file only). This records the reconstructed Spectrum screen for each emitted step frame.

- `--load-state PATH`  
  Load runtime state JSON before executing the frame loop.

- `--save-state PATH`  
  Save runtime state JSON after the frame loop.

Hard constraints enforced by the CLI:

- At least one of `--output`, `--output-fmf`, `--load-state`, `--save-state` must be provided.
- `--input-rzx -` is invalid (RZX is file-only).
- `--output-fmf -` is invalid (FMF is file-only).
- `--input` does not accept `.rzx` paths; use `--input-rzx`.
- `--output` is JSONL-only; it does not accept `.fmf` paths.

Exit behavior:

- A short run summary is printed to stderr (runtime name, executed frame count, output targets).


### 3.2 Offline recipes

Run for a fixed number of frames with neutral input:

```bash
uv run alienevolution-cli --frames 300 --output out.jsonl
```

Replay inputs from a JSONL file and write JSONL telemetry:

```bash
uv run alienevolution-cli --input in.jsonl --output out.jsonl
```

Stream: stdin → stdout (useful for piping generators/filters):

```bash
cat in.jsonl | uv run alienevolution-cli --input - --output - > out.jsonl
```

Replay from an RZX recording (Fuse-style) and write JSONL telemetry:

```bash
uv run alienevolution-cli --input-rzx run.rzx --output out.jsonl
```

Replay from RZX and extend the run by 500 neutral-input frames after the recording:

```bash
uv run alienevolution-cli --input-rzx run.rzx --frames 500 --output out.jsonl
```

Record FMF video in parallel with JSONL telemetry:

```bash
uv run alienevolution-cli --frames 2000 --output out.jsonl --output-fmf out.fmf
```

State-only mode (no outputs, only convert or validate state envelopes):

```bash
uv run alienevolution-cli --load-state in.state.json --save-state out.state.json
```


## 4. JSONL exchange format (inputs + telemetry outputs)

JSONL here means “one JSON object per line”. The headless runner supports:

- JSONL input: a sequence of `FrameInput` objects.
- JSONL output: a stream that begins with a `meta` record and continues with one `frame` record per emitted `step()` result.


### 4.1 JSONL input: `FrameInput` records

Each non-empty, non-comment line must be a JSON object. Blank lines and lines starting with `#` are ignored.

Arrays are deliberately rejected; the file must be line-oriented.

Schema (per line):

```text
{
  "joy_kempston": int (optional; default 0),
  "keyboard_rows": [int, int, int, int, int, int, int, int] (required)
}
```

Semantics:

- `joy_kempston` is a classic Kempston joystick snapshot.
  - Only the low 5 bits are used.
  - Bit layout (active-high):
    - bit0 RIGHT
    - bit1 LEFT
    - bit2 DOWN
    - bit3 UP
    - bit4 FIRE

- `keyboard_rows` is the Spectrum 8-row keyboard matrix snapshot.
  - Exactly 8 integers are required.
  - Each row is stored as an active-low byte: a bit value `0` means “pressed”.
  - Row order is hardware order:

    0. `0xFEFE`: CAPS SHIFT, Z, X, C, V
    1. `0xFDFE`: A, S, D, F, G
    2. `0xFBFE`: Q, W, E, R, T
    3. `0xF7FE`: 1, 2, 3, 4, 5
    4. `0xEFFE`: 0, 9, 8, 7, 6
    5. `0xDFFE`: P, O, I, U, Y
    6. `0xBFFE`: ENTER, L, K, J, H
    7. `0x7FFE`: SPACE, SYMBOL SHIFT, M, N, B

Neutral input (what the runner uses when it needs to fill missing frames) is:

- `joy_kempston = 0`
- `keyboard_rows = [255, 255, 255, 255, 255, 255, 255, 255]`

Example input lines:

```json
{"keyboard_rows": [255,255,255,255,255,255,255,255]}
{"joy_kempston": 16, "keyboard_rows": [255,255,255,255,255,255,255,255]}
{"joy_kempston": 0, "keyboard_rows": [255,255,255,255,255,255,255,254]}
```

The third example presses SPACE (row 7, bit 0 → cleared).


### 4.2 JSONL output: stream structure

The output stream always begins with one `meta` record, followed by `frame` records.

If `--output -` is used (stdout), the runner flushes after every emitted JSONL record to support streaming pipelines.

#### 4.2.1 `meta` record

Schema:

```text
{
  "type": "meta",
  "format": "alien-evolution-fileio-v2",
  "frames": int | null,
  "input_source": string | null
}
```

Semantics:

- `frames`:
  - is an integer when the total number of `step()` results is known in advance,
  - is `null` when the runner executes until JSONL input EOF.

- `input_source` is either a path string, the literal `"stdin"`, or `null` when there is no input source.


#### 4.2.2 `frame` record

There is exactly one `frame` record per returned `step()` result.

Schema:

```text
{
  "type": "frame",
  "index": int,
  "host_frame_index": int,
  "input": {
    "joy_kempston": int,
    "keyboard_rows": [int x8]
  },
  "output": {
    "border_color": int,
    "flash_phase": int,
    "screen_bitmap_hex": string,
    "screen_attrs_hex": string,
    "audio_commands": [AudioCommand...],
    "timing": {
      "delay_after_step_frames": int
    }
  }
}
```

Semantics:

- `index` is the step counter (0-based): how many `step()` calls have produced outputs so far.

- `host_frame_index` is the physical host-frame index (0-based) at which this output was emitted.
  - This index advances by `1 + delay_after_step_frames` after each `step()`.
  - This is the primary field that lets you reconstruct the intended pacing when the runtime uses post-step delay.

- `output.border_color` is a 3-bit Spectrum border color (0..7).

- `output.flash_phase` is the current FLASH phase (0 or 1). The backend treats it as a host-frame-derived phase.

- `output.screen_bitmap_hex` is the full 6144-byte ZX bitmap RAM, serialized as a lowercase hex string (length 12288).

- `output.screen_attrs_hex` is the full 768-byte ZX attribute RAM, serialized as a lowercase hex string (length 1536).

- `output.timing.delay_after_step_frames` is the requested additional host-frame delay after this step output.
  - The runner does not expand delays into duplicated frame records.


#### 4.2.3 `audio_commands`

Each audio command is a semantic (backend-independent) instruction.

Schema:

```text
{
  "tone": "S" | "T" | "P" | "N",
  "freq_hz": float,
  "duration_s": float,
  "volume": int,
  "channel": int,
  "source": string,
  "start_delay_ticks": int
}
```

Semantics and constraints:

- `tone` is a Pyxel-compatible tone code:
  - `S`, `T`, `P`, or `N`.

- `freq_hz` is the tone frequency in Hz.

- `duration_s` is the duration in seconds.

- `volume` is an integer in 0..7.

- `channel` is an integer in 0..3.

- `source` is an arbitrary string tag for the subsystem that emitted the command (useful for analysis and debugging).

- `start_delay_ticks` is a non-negative integer.
  - In this project it is used as a lightweight scheduling primitive for stream-driven music: the command starts after a delay measured in “ticks” (a runtime-defined unit).


### 4.3 Output size and practical notes

JSONL output is intentionally explicit and therefore large:

- one frame record includes a full screen dump (6912 bytes) encoded as hex, plus audio + timing metadata.

For tooling that does not require the raw screen dump, it is common to post-process and strip `screen_*_hex` fields, or to record FMF video instead.


### 4.4 Telemetry interpretation (recommended conventions)

The JSONL output is designed to support two related but different “time axes”:

- Step time (`index`): counts logical `step()` results.
- Host time (`host_frame_index`): counts physical host frames (50 Hz by default).

If the runtime never requests post-step delay, then `host_frame_index == index`.

If the runtime requests delays:

- `host_frame_index` advances by `1 + output.timing.delay_after_step_frames` per record.
- A consumer that wants wall-clock timing should treat one host frame as 1/50 second, and compute durations from `host_frame_index`.

Derived metrics that are often useful in analysis:

- Total host frames consumed by a run: `last.host_frame_index + 1`.
- Effective step rate (step frames per second):
  `effective_fps = host_fps * (step_count / host_frame_count)`.


## 5. State JSON format (save/load)

Both the interactive runner and the headless runner can load/save runtime state. A state file is a single JSON object (not JSONL) with a strict envelope.

Top-level schema:

```text
{
  "format": "zx-runtime-state-v1",
  "runtime_id": string,
  "schema_version": int,
  "schema_hash": string,
  "payload": object,
  "meta": object
}
```

Compatibility rules:

- `runtime_id` must match the runtime class identity (with a small alias set if declared by the runtime).
- `schema_version` and `schema_hash` must match exactly.
- Loading resets the runtime first, then applies the dynamic payload.

`meta` includes at least:

- `frame_counter`: runtime-maintained frame clock (32-bit)
- `host_frame_index`: currently set equal to `frame_counter`
- `load_mode`: currently only `"reset_replay"` is supported

`payload` is partitioned into sections (`values`, `block_ptrs`, `struct_ptrs`, `object_refs`). Internally these sections contain typed encodings (tagged by a `"__kind__"` field) for byte arrays, tuples, dataclasses, pointers, and object references.

This is intentionally strict: state files are treated as versioned binary artifacts, not as a loose “best effort” save format.


## 6. Fuse integration and related formats (RZX, FMF)

Fuse (and several other Spectrum emulators) support two formats that are useful in a reverse-engineering + porting workflow:

- RZX: input recordings (“what inputs were observed during emulation”),
- FMF: movie captures (“what screen frames were shown”).

This repository can:

- read RZX as an input source for the headless runner,
- write FMF from the port runtime,
- play FMF in a Pyxel window.


### 6.1 RZX input (`--input-rzx`)

RZX is used as a compact way to import recorded play sessions from emulator runs.

Usage:

```bash
uv run alienevolution-cli --input-rzx session.rzx --output out.jsonl
```

Technical note (important for interpreting results):

- RZX stores the *values returned by IN instructions*, but it does not store the probed port numbers.
- Therefore, converting RZX port-read byte streams into a full keyboard matrix snapshot is unavoidably heuristic.

Current decoding model in this project:

- Each frame contains `port_readings` bytes.
- Bytes with `(value & 0xE0) == 0x00` are treated as Kempston joystick samples (`value & 0x1F`). The last such sample in a frame is used.
- Bytes with `(value & 0xE0) == 0xE0` are treated as keyboard-row reads.
  - The first 8 such values are mapped to the 8 keyboard rows in standard row order.

Consequences:

- If the original game (or emulator) probes rows in a different order, or does not probe all rows every frame, the reconstructed `keyboard_rows` may differ from the true hardware state.
- For highest-fidelity deterministic datasets, prefer JSONL input produced by the port itself.


### 6.2 FMF output (`--output-fmf`) and playback (`fmf-player`)

FMF in this project is the Fuse Movie Format variant `FMF_V1e`.

#### 6.2.1 Producing FMF

Usage:

```bash
uv run alienevolution-cli --frames 2000 --output-fmf out.fmf
```

Properties of the FMF file written by the headless runner:

- Format: `FMF_V1e` (little-endian header).
- Screen type: standard Spectrum `$` frame slices only.
- Each emitted step frame is recorded as:
  - one full `$` slice for the active area (x=4, y=24, w=32, h=192),
  - followed by one `N` “new frame” marker.
- Sound blocks are not emitted (video-only recording in the current revision).
- Post-step delay frames are not expanded; FMF contains one frame per `step()` output.

Timing implication:

- If the runtime uses `delay_after_step_frames` for pacing, an FMF played back at 50 FPS will *compress* those delays (because the delay-only host frames are not represented as duplicated video frames).
- For wall-clock-accurate playback, use JSONL (`host_frame_index` + `delay_after_step_frames`) as the timing authority, and expand frames in a post-processing step before encoding a movie.

#### 6.2.2 Playing FMF

Usage:

```bash
uv run fmf-player --input out.fmf
```

Flags:

- `--input PATH` (required): FMF file.
- `--fps N` (default: 50): playback FPS.
- `--display-scale N` (default: 2): Pyxel scaling factor.
- `--margin-x N` (default: 32): horizontal border margin in pixels.
- `--margin-y N` (default: 24): vertical border margin in pixels.
- `--loop`: loop playback.
- `--title TEXT`: window title override.

Playback controls:

- `Space`: pause/unpause
- `Right Arrow`: single-step one frame (forces pause)


## 7. Guardrail tool: `check_runtime_global_ptr_usage.py`

This is a porting-process tool rather than a runtime runner. It statically analyzes `AlienEvolutionPort` and checks:

- how many call sites still use selected “global address” compatibility helpers,
- the cardinality of the `_pointer_enum_domains` tuple.

It supports a baseline file so the project can enforce a “ratchet”: counts may go down over time, but should not go up.

Run:

```bash
python tools/check_runtime_global_ptr_usage.py
```

Flags:

- `--logic PATH`  
  Path to `logic.py` (default: `src/alien_evolution/alienevolution/logic.py`).

- `--baseline PATH`  
  Baseline JSON file (default: `tools/runtime_global_ptr_usage_baseline.json`).

- `--write-baseline`  
  Write the current counts into the baseline file and exit successfully.

- `--pointer-enum-limit N`  
  Maximum allowed cardinality for `_pointer_enum_domains` (default: 32).

Typical workflow:

- First run in a new checkout:

  ```bash
  python tools/check_runtime_global_ptr_usage.py --write-baseline
  ```

- Later runs (CI / pre-commit) fail if usage grows.

