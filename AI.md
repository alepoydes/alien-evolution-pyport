# AI Integration Guide

This document describes how to run `Alien Evolution` in non-interactive mode and integrate bots through the CLI.

For reusable ZX -> Python/Pyxel porting infrastructure details (module layout, RZX/FMF pipeline, telemetry logging contracts), see [PORTING_GUIDE.md](PORTING_GUIDE.md).

## CLI Entry Points

- Interactive game window: `uv run alienevolution`
- Headless file/stdin/stdout runner: `uv run alienevolution-cli`
- FMF playback utility: `uv run fmf-player --input <file.fmf>`

For gameplay rules and controls, see [GAME_INFO.md](GAME_INFO.md).

## Core Headless Workflow

Install dependencies once:

```bash
uv sync
```

Run a fixed number of frames with neutral input:

```bash
uv run alienevolution-cli --frames 300 --output out/run.jsonl
```

Run from JSONL input stream and save both telemetry and FMF:

```bash
uv run alienevolution-cli \
  --input data/input.jsonl \
  --output out/run.jsonl \
  --output-fmf out/run.fmf
```

Stream input through stdin and output to stdout:

```bash
cat data/input.jsonl | uv run alienevolution-cli --input - --output - --frames 300
```

## Input Interface

Input records are JSONL objects, one record per line.

Required fields per frame:
- `joy_kempston` (integer; lower 5 bits are used)
- `keyboard_rows` (array of 8 integers)

Example:

```json
{"joy_kempston": 16, "keyboard_rows": [255,255,255,255,255,255,255,255]}
{"joy_kempston": 0, "keyboard_rows": [255,255,255,255,255,254,255,255]}
```

Rules:
- Blank lines are ignored.
- Lines starting with `#` are ignored.
- JSON arrays are not accepted; only JSON objects per line.

### Kempston Bit Layout

`joy_kempston` uses this bit layout:
- bit 0: right
- bit 1: left
- bit 2: down
- bit 3: up
- bit 4: fire

### Keyboard Matrix Layout

`keyboard_rows` is an 8-row active-low matrix:
- A pressed key is represented by a cleared bit (`0`).
- Not pressed is `1`.

Row order:
1. `CAPS SHIFT, Z, X, C, V`
2. `A, S, D, F, G`
3. `Q, W, E, R, T`
4. `1, 2, 3, 4, 5`
5. `0, 9, 8, 7, 6`
6. `P, O, I, U, Y`
7. `ENTER, L, K, J, H`
8. `SPACE, SYMBOL SHIFT, M, N, B`

## Run-Length Semantics

`--frames` behaves differently depending on input mode:

- JSONL input mode:
- if `--frames` is omitted: run until input EOF;
- if input ends early and `--frames` is set: remaining frames use neutral input.

- RZX input mode (`--input-rzx`):
- if `--frames` is omitted: run exactly recording length;
- if `--frames` is set: run `recording_length + frames`.

## Output Interface

At least one output target is required:
- `--output <jsonl|->`
- and/or `--output-fmf <file.fmf>`
- and/or state I/O (`--load-state`, `--save-state`)

JSONL output begins with a `meta` record, then one `frame` record per step.

Example shape:

```json
{"type":"meta","format":"alien-evolution-fileio-v2","frames":300,"input_source":"data/input.jsonl"}
{"type":"frame","index":0,"host_frame_index":0,"input":{"joy_kempston":0,"keyboard_rows":[255,255,255,255,255,255,255,255]},"output":{"border_color":0,"flash_phase":0,"screen_bitmap_hex":"...","screen_attrs_hex":"...","audio_commands":[],"timing":{"delay_after_step_frames":0}}}
```

`output.timing.delay_after_step_frames` is important:
- it tells you how many host frames passed after this step before the next step.
- `host_frame_index` accumulates those delays.

For visual replay, write FMF and play it:

```bash
uv run fmf-player --input out/run.fmf
```

## State Load/Save

You can checkpoint full runtime state as JSON:

```bash
uv run alienevolution-cli --frames 600 --output out/run.jsonl --save-state out/state.json
uv run alienevolution-cli --load-state out/state.json --frames 300 --output out/resume.jsonl
```

This is useful for:
- curriculum training from mid-game states;
- reproducible scenario resets;
- branching evaluation from identical starting points.

## Bot Design Recommendations

Start simple:
1. Use joystick bits for movement/fire.
2. Use a small keyboard policy only for front-end actions.
3. Record JSONL outputs and compute rewards from visible progress/survival.

Then scale up:
1. Parse `screen_bitmap_hex` + `screen_attrs_hex` into tensors.
2. Track `host_frame_index` and delay timing explicitly.
3. Use saved states for deterministic rollouts and A/B policy testing.

## Determinism Notes

For a fixed build and identical input/state sequence, behavior is designed to be deterministic.
To keep experiments reproducible:
- keep exact input logs;
- include state snapshots;
- store the produced JSONL telemetry together with model metadata.
