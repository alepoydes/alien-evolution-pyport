# ZX -> Python/Pyxel Porting Guide

This document describes reusable infrastructure for porting ZX Spectrum games to Python + Pyxel in this repository.

For game rules and player-facing behavior, see [GAME_INFO.md](GAME_INFO.md).  
For bot-facing usage patterns, see [AI.md](AI.md).  
For game-specific deep internals, see [RESEARCH.md](RESEARCH.md).

## Goals of the Porting Layer

- Keep game logic isolated from frontend and file I/O.
- Run the same runtime both interactively (Pyxel window) and headlessly (CLI).
- Preserve deterministic frame-step behavior for testing and automation.
- Support reproducible experiments via JSONL telemetry, FMF recordings, RZX replay input, and runtime state snapshots.

## Core Runtime Contracts

Shared frame-step contracts are defined in `src/alien_evolution/zx/runtime.py`:

- `FrameInput`: per-step controls (`joy_kempston`, `keyboard_rows`).
- `StepOutput`: per-step rendered frame + audio + timing metadata.
- `StepTiming`: includes `delay_after_step_frames`.
- `FrameStepRuntime`: protocol (`reset()`, `step(frame_input)`).
- `ZXSpectrumServiceLayer`: ZX-like helpers (screen buffers, input sampling, IN/OUT semantics, audio command emission).

These contracts are the main compatibility surface for new game ports.

## Reusable Module Layout

- `src/alien_evolution/zx/`: ZX-style abstractions and state/runtime contracts.
- `src/alien_evolution/fileio/`: headless runner, JSONL I/O, FMF writing, RZX decoding, state load/save.
- `src/alien_evolution/pyxel/`: interactive frontend, screen/audio glue, FMF player.
- `src/alien_evolution/alienevolution/`: game-specific runtime implementation.
- `src/alien_evolution/demoline/`: minimal demo runtime using the same contracts.

## CLI Entry Points

Defined in `pyproject.toml`:

- `uv run alienevolution`: interactive game.
- `uv run alienevolution-cli`: headless frame-step runner.
- `uv run fmf-player --input <file.fmf>`: FMF playback.
- `uv run demoline`, `uv run demoline-cli`: contract-level demo runners.

## JSONL Telemetry and Logging

Headless loop is implemented in `src/alien_evolution/fileio/runner.py` and `src/alien_evolution/fileio/cli_core.py`.

Input:
- `--input <file.jsonl|->` accepts one JSON object per line.
- Each frame record uses:
  - `joy_kempston` (int, lower 5 bits used),
  - `keyboard_rows` (array of 8 ints).

Output:
- `--output <file.jsonl|->` writes telemetry:
  - first record: `meta`,
  - then one `frame` record per simulation step.
- Includes:
  - rendered screen (`screen_bitmap_hex`, `screen_attrs_hex`),
  - `audio_commands`,
  - timing (`delay_after_step_frames`),
  - `host_frame_index` for host-frame pacing traceability.

Frame-length rules:
- JSONL mode: without `--frames`, runs until EOF.
- If `--frames` is set and input ends early, neutral input is used for remaining frames.

## FMF Recording and Playback

FMF support is implemented in:

- writer: `src/alien_evolution/fileio/fmf.py` (`FMFScreenWriter`),
- player: `src/alien_evolution/pyxel/fmfplayer.py`.

Usage:

```bash
uv run alienevolution-cli --frames 300 --output-fmf out/run.fmf --output out/run.jsonl
uv run fmf-player --input out/run.fmf
```

FMF can be generated in parallel with JSONL telemetry.

## RZX Input Replay

RZX decoder and iterator:
- `src/alien_evolution/fileio/rzx.py` (`RZXFrameInputIterator`).

CLI usage:

```bash
uv run alienevolution-cli --input-rzx path/to/recording.rzx --output out/run.jsonl
```

Run-length behavior:
- without `--frames`: run exactly recording length,
- with `--frames`: run `len(rzx) + frames`.

Notes:
- `--input` no longer accepts `.rzx`; use `--input-rzx`.
- RZX stores IN results (not port IDs), so keyboard reconstruction is heuristic by design.

## State Snapshot I/O

State envelope I/O lives in `src/alien_evolution/fileio/stateio.py`.

- `--save-state <file.json>` saves runtime snapshot.
- `--load-state <file.json>` restores runtime snapshot before stepping.

This is useful for deterministic branching and regression scenarios.

## Porting Support Scripts

Current helper script:

- `tools/check_runtime_global_ptr_usage.py`: guardrail for pointer-helper usage growth in `AlienEvolutionPort`.
- `tools/runtime_global_ptr_usage_baseline.json`: baseline for the same check.

## Practical Porting Flow

1. Implement game runtime behind `FrameStepRuntime`.
2. Route ZX-like machine interactions through `ZXSpectrumServiceLayer`.
3. Expose both Pyxel runner and file I/O runner over the same runtime.
4. Validate determinism/pacing with JSONL logs and snapshot roundtrips.
5. Use FMF for visual debugging and RZX for replay-based comparison.
