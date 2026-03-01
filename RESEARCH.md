# Research Notes

This document is dedicated to the original ZX Spectrum game and to the reverse-engineering evidence used to understand it.
Its goal is to explain how the original system behaves, how we decode its data, and how we verify hypotheses with stable artifacts.

Execution tooling (CLI runners, FMF/RZX pipelines, telemetry I/O, and state checkpoints) is documented in [PORTING_GUIDE.md](PORTING_GUIDE.md).

## Primary Sources and Research Artifacts

- This directory does not ship original game source code, ROMs, tape images, or other proprietary binaries.
- Reverse engineering is documented from derived, reproducible artifacts prepared for study.
- For independent binary-level work (including self-run disassembly from original archives), use the World of Spectrum archive: [https://worldofspectrum.org/](https://worldofspectrum.org/).
- Reverse-engineering outputs are tracked as reproducible artifacts:
  - decoded map renders in `figs/`,
  - sprite atlases in `figs/`,
  - skool and ctl files in `skool/`.

## Skool Files and SkoolKit Workflow

### What SkoolKit Is Used For

[SkoolKit](https://skoolkit.ca/) is a toolkit for producing readable Z80 disassembly listings and hyperlinked HTML views from Spectrum snapshots and control metadata.
In this project, it is the main bridge between raw binary evidence and human-readable program structure.

### Core Skool Files in This Project

- `skool/AlienEvolution.ctl`: control/annotation file that marks code/data/text boundaries and labels.
- `skool/AlienEvolution.skool`: generated/maintained skool listing with comments and structure.
- `skool/html/`: generated HTML listing output (when built locally).

### Building HTML Listing

Run from inside `alien-evolution-pyport/`:

```bash
UV_CACHE_DIR=.uv-cache uv run --with skoolkit skool2html.py \
  -d skool/html \
  skool/AlienEvolution.skool
```

Typical output index:

```text
skool/html/AlienEvolution/index.html
```

## Main Loop Inventory

The runtime uses a state-driven control model with multiple loop families:

1. Boot / menu init loop:
- draw title UI, run menu stream, enter menu input poll.

2. Menu polling loop:
- handle preset selection, define-keys flow, and start action.

3. Stream intermission loop:
- advance scripted audio stream with a timing budget and optional key-abort.

4. Gameplay setup loop:
- build level runtime state, initialize queues/counters, start pre-game stream.

5. Gameplay main loop:
- object queue update;
- transient effects update;
- player movement/action step;
- directional interaction pass;
- callback/timing gates;
- scheduler tick;
- render;
- branch to continue, level complete, or failure.

6. Scheduler autonomous subloop:
- expansion and queue rebalance path when scheduler mask triggers autonomous step.

7. Transition loops:
- level-complete score roll loop;
- failure drain/delay loop;
- ending flow loop.

8. High-score name entry loop:
- key wait/filter/backspace/char states until confirm.

## Frame Synchronization and Pacing

### Host Frame vs Simulation Step

A single `step()` may request extra host-frame delay via:
- `StepOutput.timing.delay_after_step_frames`

The wrappers then advance host frames without running a new simulation step.
This is how the runtime preserves original pacing patterns while staying frame-step friendly.

### Key Timing Constants

- Gameplay frame divider: `5` host frames per gameplay cycle target.
- Stream interpreter frame budget: `69888` timing units.
- Level-complete roll: `0x01F4` score increments distributed across `125` frames.

### Pacing Behavior by Mode

- Menu and text intermissions are paced with frame delays derived from stream timing debt.
- Gameplay is intentionally slower than host refresh to match observed legacy cadence.
- Transition sequences (level complete / failure) use dedicated loop pacing rather than the normal gameplay cadence.

## Map Data Model

Each level map is a mutable `50x50` byte table.

Byte split:
- low 6 bits: gameplay/object/state code;
- high 2 bits: render profile bits.

Conceptually:

```text
cell = profile_bits | low6_code
profile_bits in {0x00, 0x40, 0x80, 0xC0}
```

Special wall-profile full-byte family:
- `0x17`, `0x57`, `0x97`, `0xD7`

## Hex Map Code Decoding (Practical Table)

The table below summarizes the most useful gameplay codes seen in runtime logic.

| Hex code(s) | Meaning |
| --- | --- |
| `0x00` | Empty traversable cell |
| `0x01..0x0C` | Advanced chasing enemy family |
| `0x0D..0x10` | Mid enemy family |
| `0x11..0x14` | Early mobile enemy family |
| `0x17` | Wall/base solid block code |
| `0x18` | Pushable block |
| `0x19..0x1A` | Static/toggling enemy phase markers |
| `0x1B..0x1C` | Interactive toggle pair used in directional interaction logic |
| `0x21..0x24` | Player-facing markers after movement commit |
| `0x25..0x26` | Mine state pair (idle animation/toggle) |
| `0x2A` | Shared impact marker |
| `0x2B..0x2D` | Transient effect sequence markers |
| `0x33` | Forward transient projectile seed |
| `0x34..0x35` | TNT armed-phase markers |
| `0x36..0x37` | Bomb armed-phase markers |
| `0x38` | Shared kill/impact tag marker |
| `0x39` | Queue-3 spawned transient attack marker |

## Reference Visual Artifacts

Level map renders:
- [Level 1 map](figs/alien_evolution_level1_map.png)
- [Level 2 map](figs/alien_evolution_level2_map.png)
- [Level 3 map](figs/alien_evolution_level3_map.png)

Sprite atlases:
- [Level 1 sprites](figs/alien_evolution_level1_sprites.png)
- [Level 2 sprites](figs/alien_evolution_level2_sprites.png)
- [Level 3 sprites](figs/alien_evolution_level3_sprites.png)

Skool source:
- [AlienEvolution.skool](skool/AlienEvolution.skool)
- [AlienEvolution.ctl](skool/AlienEvolution.ctl)

## Reproducibility Boundary

Research conclusions in this file are derived from stable artifacts (snapshots, map dumps, sprite atlases, and skool listings).
Operational execution interfaces and run tooling are intentionally documented in [PORTING_GUIDE.md](PORTING_GUIDE.md), so this document can remain focused on evidence and interpretation of the original game.

Known unresolved fidelity topics are tracked in [OPEN_ISSUES.md](OPEN_ISSUES.md).
