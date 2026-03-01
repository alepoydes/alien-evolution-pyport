# Alien Evolution (ZX Spectrum) -> Modern Python Port

`Alien Evolution` is an isometric action game released in 1987 for the Sinclair ZX Spectrum.
You play as CYBORG G4, sent to contain an alien outbreak after a nuclear disaster.
The key mechanic is simple and tense: if you leave aliens alive for too long, they evolve into more dangerous forms and can eventually lay eggs.
So this is not just a shooting game, it is about target priority and crowd control.

This repository contains a Python/Pyxel port focused on fidelity to the original game while making it easier to run and inspect on modern machines.
It includes headless stepping, deterministic replay, and runtime state save/load for testing and automation.

<table>
  <tr>
    <td><img src="https://worldofspectrum.org//scr2gif?file=pub/sinclair/screens/load/a/scr/AlienEvolution.scr" alt="Alien Evolution loading screen" width="420"></td>
    <td><img src="figs/alien_evolution_gameplay_screenshot.png" alt="Alien Evolution gameplay screenshot" width="420"></td>
  </tr>
</table>

## About The Original Game

`Alien Evolution` was published by Gremlin Graphics Software Ltd in 1987.
It was created by Marco Paulo Carrasco and Rui Manuel Tito, two young developers from Portugal.
The game was well received at the time and got coverage in magazines such as Crash, Your Sinclair, ASM, and MicroHobby.

Why it still matters:
- The design is compact but interesting: a few rules interact to create pressure.
- The original program is small enough to reverse engineer in detail.
- It is a good candidate for software archaeology and for preserving 8-bit design techniques.

Historical references:
- World of Spectrum entry (release data, credits, archive): https://worldofspectrum.org/archive/software/games/alien-evolution-gremlin-graphics-software-ltd
- Nelson Zagalo (2015), Video Games Around the World (Portugal): https://www.researchgate.net/figure/Paradise-Cafe-1985-top-left-Alien-Evolution-1987-top-right-Portugal-1111_fig1_323255356
- Review aggregation with source magazines/issues: https://www.uvlist.net/game-11914-Alien%2BEvolution

## Project Goals

- Preserve a historically interesting game in a form that runs well on modern hardware.
- Reconstruct the original behavior with evidence-based reverse engineering.
- Document runtime logic and data flow so the project is maintainable.
- Provide practical tooling for automation, bots, and machine learning experiments.

## Why It Is Useful For ML

8-bit games are a good middle ground: fast and deterministic, but still non-trivial.
`Alien Evolution` is especially useful because delayed consequences are built into the core loop.
If an agent ignores threats now, difficulty spikes later due to evolution and reproduction.

This makes the game useful for:
- delayed credit assignment experiments,
- policy testing under controllable difficulty,
- deterministic rollouts and regression checks from saved inputs/states,
- comparing pixel-only policies with structured observations.

## Quick Start (Interactive)

```bash
uv sync
uv run alienevolution
```

Default controls:
- `W/A/S/D`: move
- `Space`: action/fire
- `Enter`: cycle weapon mode

Quality-of-life hotkeys:
- `F5`: quick-save
- `F9`: quick-load
- `F8`: rollback
- `F7`: manual checkpoint

## CLI And Automation Docs

- Headless CLI usage, JSONL telemetry, FMF recording/playback, RZX input, and state I/O: [PORTING_GUIDE.md](PORTING_GUIDE.md)
- Bot and ML workflows: [AI.md](AI.md)

## Documentation Guide

- [GAME_INFO.md](GAME_INFO.md) explains the game as a player-facing system: goals, controls, enemy evolution, weapon roles, and level flow.
- [RESEARCH.md](RESEARCH.md) captures research on the original ZX game: runtime behavior, data models, decoded code families, and Skool-based reverse-engineering materials.
- [PORTING_GUIDE.md](PORTING_GUIDE.md) contains implementation infrastructure: shared runtime contracts, module layout, CLI/file I/O tools, FMF/RZX pipelines, and reproducible execution workflow.
- [AI.md](AI.md) focuses on bot and ML integration: control interfaces, telemetry semantics, and practical automation strategy.
- [OPEN_ISSUES.md](OPEN_ISSUES.md) tracks open fidelity gaps and unresolved technical discrepancies.