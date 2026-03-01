# Alien Evolution: Game Info

This document explains the game from a player and gameplay-AI perspective.

For CLI integration details, see [AI.md](AI.md).  
For low-level internals and code-oriented analysis, see [RESEARCH.md](RESEARCH.md).

## Game Premise

The game is an isometric survival-action scenario set after a global nuclear disaster.
You control CYBORG G4, sent to clear alien life forms that keep evolving into harder strains.

## Core Objective

Your mission on each level is to survive, control alien growth, and keep progress moving until the level is cleared.

The game in this port contains three playable levels.
After the third level, the game transitions to the ending sequence and then back to the front-end flow.

## Failure Conditions

You lose a run when one of these happens:
- your mission/life reserve is depleted;
- the level timer runs out.

## Player Actions

You can:
- move in four directions;
- fire or place the currently selected weapon;
- switch weapon mode;
- push movable blocks to shape paths and traps;
- use teleporter structures to reposition.

Movement and space control are central: many situations are solved by positioning, not raw damage.

## Enemy Evolution

Enemies are not a single class. They evolve through several behavior phases:
- early static/slow phase;
- intermediate moving phases;
- advanced chasing phase.

As evolution progresses, behavior becomes less predictable and more aggressive.
This is why weapon choice and map control matter more than pure speed.

## Weapons and Tactical Roles

The weapon selector cycles through four modes:
- `Laser`: directional projectile pressure;
- `Mine`: area denial and path control;
- `TNT`: broader explosive control;
- `Bomb`: more focused explosive pressure.

Different enemy phases do not react equally to all weapon modes.
A strong strategy is to combine:
- movement pathing;
- block pushes;
- selective weapon use by situation.

## World Interactions

The map is not just static geometry. During a run it also hosts:
- enemy state changes;
- projectile/effect states;
- player-facing and interaction markers.

In practice, this means the arena is always changing. Routes that were safe a few seconds ago may become dangerous or blocked.

## Level Flow

A typical run follows this pattern:
1. Enter level and establish safe movement lanes.
2. Control enemy pressure while preserving resources.
3. Use teleports and pushes to break enemy lines.
4. Finish level objective and transition to the next level.

Resource discipline is important: reckless weapon use can leave you exposed later in the same level.

## Default Controls (Interactive Run)

- `W` / `A` / `S` / `D`: move
- `Space`: use/fire current weapon
- `Enter`: cycle weapon mode

Menu controls:
- `1..4`: select a predefined control profile
- `5`: define custom keys
- `6`: start game

Pyxel runtime quality-of-life hotkeys:
- `F5`: quick-save
- `F9`: quick-load
- `F8`: rollback to previous checkpoint
- `F7`: force checkpoint

## Notes For Bot Designers

At high level, this is a deterministic grid-action environment with:
- sparse but high-impact interaction events;
- delayed consequences from enemy evolution;
- strong dependence on tactical position;
- non-uniform weapon effectiveness across enemy phases.

A useful baseline bot usually needs:
- short-horizon survival rules;
- medium-horizon position planning;
- a weapon policy conditioned on enemy phase and local geometry.
