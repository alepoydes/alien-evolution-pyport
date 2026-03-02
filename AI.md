# Alien Evolution as an ML / RL Environment

This document describes how to use the Alien Evolution Python port as a reproducible, scriptable environment for machine-learning research.

It focuses on two practical workflows:

1) Running the game headlessly as a black-box simulator (CLI or in-process), exchanging actions and observations via a stable JSONL contract.

2) Using full state snapshots for rollback and branching rollouts, enabling tree-search methods (MCTS, beam search, best-first search) and model-based evaluation.

For gameplay semantics (what “progress” means, what counts as success/failure, controls, and HUD meaning), read GAME_INFO.md first.

For the runtime contract (reset/step semantics, timing, and state envelope format), see PYPORT_ARCHITECTURE.md.

For CLI details (flags, stdin/stdout streaming, JSONL formats, FMF/RZX workflows), see CLI_UTILITIES.md.

For reverse-engineering context and internal variable meaning beyond what is needed for ML integration, see RESEARCH.md.

---

## 1. The problem we are studying

In Alien Evolution, the agent must choose a sequence of actions in a dynamical system where:

- Rewards are delayed and often sparse. The most important “good action” can be to prevent a future failure mode, not to gain an immediate point.
- Consequences compound over time. Letting an alien live is not neutral: the alien evolves, then may reproduce, increasing future difficulty nonlinearly.
- There is no closed-form action algorithm. What to do depends on the current configuration of the map, the population phase distribution, and the time remaining.

This is a standard setting for sequential decision making under delayed reward. Formally, we can treat it as an episodic Markov decision process (MDP) or, if we restrict the agent to pixel observations, as a partially observable MDP (POMDP).

What makes it hard is not only reactivity. It is credit assignment across time. If the agent fails 300 frames later because the population exploded, the root cause may be a missed kill or a poor positioning decision made much earlier.

Humans cope with this class of problems by building internal abstractions:

- Hierarchical decomposition (subgoals such as “stabilize population”, “clear a corridor”, “trap a chaser”),
- Learned dynamics models (“if I leave phase-3 alive in open space, it will create eggs”),
- Risk-sensitive exploration (testing a tactic in a safe region before committing),
- Memory and predictive control (planning in terms of trajectories, not single actions).

These are exactly the capabilities we want to probe with ML methods.

---

## 2. Why reinforcement learning, and what “integration” means here

Reinforcement learning (RL) provides a formal language for “learn a policy without a hand-written algorithm”. The environment exposes a controlled interface:

- Observation \(o_t\): what the agent receives (pixels, screen buffers, optional telemetry).
- Action \(a_t\): what the agent can do (joystick bits, keyboard matrix).
- Reward \(r_t\): a scalar feedback signal (score change, population reduction, survival time, shaped objectives).
- Transition: how the world changes after an action.

An RL agent does not require a symbolic description of the game, only a stable step API. However, RL algorithms are sensitive to details that are often informal in game ports:

- Exact reset semantics (does reset advance time?),
- Determinism guarantees (can we reproduce runs bit-for-bit?),
- Time base (is the step duration constant?),
- The definition of “done” (terminal conditions, episode truncation).

This repository treats those as explicit contracts: deterministic stepping, explicit timing metadata, and (optionally) full state snapshots.

---

## 3. Why this port is a good benchmark

From an ML perspective, Alien Evolution sits in a useful middle ground:

- It is “rich enough” to stress long-horizon planning, perception from pixels, and exploration under risk.
- It is deterministic and fast enough for large-scale experimentation.

This particular port adds properties that are rare in ad-hoc game wrappers:

- A narrow, explicit step contract: one input snapshot in, one observation out, plus timing metadata.
- Headless execution with streaming JSONL I/O, suitable for dataset generation and integration with non-Python tooling.
- State save/load with a validated schema hash, enabling reproducible resets and rollback-based search.
- Optional compatibility with emulator recordings (RZX) for replay and demonstration data.

---

## 4. Environment interface

At the core is a “frame-step runtime” interface:

- `reset()` initializes to a baseline state.
- `step(frame_input)` advances the simulation by one environment step and returns a `StepOutput` containing:
  - ZX screen bitmap (6144 bytes) and attribute RAM (768 bytes),
  - border color and flash phase,
  - emitted audio commands (optional, semantic),
  - timing metadata.

The key timing field is:

- `delay_after_step_frames`: additional host frames that must elapse before the next `step()` call.

In other words, one `step()` result corresponds to:

- `host_frames = 1 + delay_after_step_frames` host frames,

and wrappers must advance the host-frame clock accordingly (without applying new inputs) before the next step.

If you want the formal contract and the motivation for this design, see PYPORT_ARCHITECTURE.md.

---

## 5. Workflow A: headless simulator via JSONL (CLI and/or subprocess integration)

This is the most portable workflow: actions in, observations out, as line-delimited JSON.

The full CLI reference is in CLI_UTILITIES.md. The essentials are summarized here because they matter for ML.

### 5.1 Running headless

Typical offline run (generate 300 steps with neutral input, write telemetry JSONL):

```bash
uv sync
uv run alienevolution-cli --frames 300 --output out/run.jsonl
```

Run from an input JSONL file and save output:

```bash
uv run alienevolution-cli --input data/inputs.jsonl --output out/trace.jsonl
```

Stream inputs over stdin and stream outputs over stdout (useful for process-to-process integration):

```bash
cat data/inputs.jsonl | uv run alienevolution-cli --input - --output - --frames 1000
```

If you need visual debugging, write FMF alongside JSONL and replay it:

```bash
uv run alienevolution-cli --frames 600 --output out/trace.jsonl --output-fmf out/trace.fmf
uv run fmf-player --input out/trace.fmf
```

### 5.2 Input JSONL schema

The input stream is one JSON object per line (JSONL). Blank lines and lines starting with `#` are ignored.

Each record corresponds to one environment step. Fields:

- `joy_kempston`: integer; only lower 5 bits are used (optional; defaults to 0).
- `keyboard_rows`: array of 8 integers (required). Each integer is a row byte in the Spectrum keyboard matrix.

Example:

```json
{"joy_kempston": 16, "keyboard_rows": [255,255,255,255,255,255,255,255]}
{"joy_kempston": 0,  "keyboard_rows": [255,255,255,255,255,254,255,255]}
```

Kempston bit layout (`joy_kempston`):

- bit 0: right
- bit 1: left
- bit 2: down
- bit 3: up
- bit 4: fire/action

Keyboard matrix (`keyboard_rows`) is active-low:

- Not pressed: bit = 1
- Pressed: bit = 0

Row order (8 rows):

1. `CAPS SHIFT, Z, X, C, V`
2. `A, S, D, F, G`
3. `Q, W, E, R, T`
4. `1, 2, 3, 4, 5`
5. `0, 9, 8, 7, 6`
6. `P, O, I, U, Y`
7. `ENTER, L, K, J, H`
8. `SPACE, SYMBOL SHIFT, M, N, B`

In many ML setups you can use only the joystick bits for gameplay and reserve keyboard rows for menu / front-end actions.

### 5.3 Output JSONL schema

The output stream is JSONL with:

- one `meta` record first,
- then one `frame` record per executed step.

Example (shape only; screen hex omitted):

```json
{"type":"meta","format":"alien-evolution-fileio-v2","frames":300,"input_source":"data/inputs.jsonl"}
{"type":"frame","index":0,"host_frame_index":0,
 "input":{"joy_kempston":0,"keyboard_rows":[255,255,255,255,255,255,255,255]},
 "output":{"border_color":0,"flash_phase":0,
           "screen_bitmap_hex":"...","screen_attrs_hex":"...",
           "audio_commands":[],
           "timing":{"delay_after_step_frames":4}}}
```

Fields worth treating as telemetry (they are essential for correct time accounting and reproducibility):

- `host_frame_index`: index in host-frame time (50 Hz base). It accumulates post-step delays.
- `output.timing.delay_after_step_frames`: how many additional host frames elapse after this step.

A practical implication: the JSONL stream is in “step time”, not necessarily in “50 Hz host-frame time”. If you want a host-frame-aligned dataset, you must expand frames by repeating the last observation `delay_after_step_frames` times (and advancing flash phase accordingly). For most RL agents it is simpler to treat each step record as one environment step and keep `host_frame_index` as an auxiliary time variable.

### 5.4 Observations: decoding the ZX screen buffers

The observation is the pair:

- `screen_bitmap_hex`: 6144 bytes (Spectrum bitmap layout, same as 0x4000..0x57FF),
- `screen_attrs_hex`: 768 bytes (attribute layout, same as 0x5800..0x5AFF).

This is not a linear `H×W` framebuffer. Use the ZX mapping helpers in `alien_evolution.zx.screen` if you want pixels.

A minimal conversion to a `256×192` array of 0..15 palette indices (no external dependencies) looks like this:

```python
from alien_evolution.zx.screen import ZX_SCREEN_H, ZX_SCREEN_W, zx_bitmap_index


def _zx_col(c0_7: int, bright: int) -> int:
    c = c0_7 & 7
    return 0 if c == 0 else c + (8 if (bright & 1) else 0)


def zx_to_palette_indices(bitmap: bytes, attrs: bytes, *, flash_phase: int) -> list[list[int]]:
    assert len(bitmap) == 6144
    assert len(attrs) == 768

    flash_phase &= 1
    img: list[list[int]] = [[0] * ZX_SCREEN_W for _ in range(ZX_SCREEN_H)]

    for y in range(ZX_SCREEN_H):
        attr_row = (y >> 3) * 32
        for xb in range(32):
            b = bitmap[zx_bitmap_index(xb, y)]
            a = attrs[attr_row + xb]

            ink = a & 0x07
            paper = (a >> 3) & 0x07
            bright = (a >> 6) & 0x01
            flash = (a >> 7) & 0x01
            if flash and flash_phase:
                ink, paper = paper, ink

            ink_c = _zx_col(ink, bright)
            pap_c = _zx_col(paper, bright)

            x0 = xb * 8
            img[y][x0 + 0] = ink_c if (b & 0x80) else pap_c
            img[y][x0 + 1] = ink_c if (b & 0x40) else pap_c
            img[y][x0 + 2] = ink_c if (b & 0x20) else pap_c
            img[y][x0 + 3] = ink_c if (b & 0x10) else pap_c
            img[y][x0 + 4] = ink_c if (b & 0x08) else pap_c
            img[y][x0 + 5] = ink_c if (b & 0x04) else pap_c
            img[y][x0 + 6] = ink_c if (b & 0x02) else pap_c
            img[y][x0 + 7] = ink_c if (b & 0x01) else pap_c

    return img
```

If you want RGB, map indices through `alien_evolution.zx.screen.ZX_PALETTE_16`.

### 5.5 Rewards and “how to count points” in black-box mode

The JSONL output is intentionally low-level: it is faithful to the Spectrum-facing presentation layer (screen + attrs + border + flash + audio).

It does not directly output semantic variables such as “score” or “alien population counter”. In black-box mode you therefore have three realistic options:

1) Define reward from pixels (for example, parse the HUD digits or train directly from pixels without explicit score).

2) Define reward from time and survival only (dense but weak signal).

3) Use the in-process workflow (next section) when you want semantic reward signals such as score change, population reduction, time remaining, etc.

If your research question explicitly involves delayed reward and planning, option (3) is usually the most informative because it avoids “reward through OCR” and lets you measure the relevant quantities exactly.

---

## 6. Workflow B: in-process stepping (Python API)

When you run the runtime in-process, you can:

- step without process overhead,
- compute rewards from internal counters precisely,
- use state snapshots for rollback.

### 6.1 Minimal step loop

```python
from alien_evolution.alienevolution.logic import AlienEvolutionPort
from alien_evolution.zx.runtime import FrameInput

rt = AlienEvolutionPort()
rt.reset()

# One neutral step.
out = rt.step(FrameInput())

# Respect post-step delay (required for fidelity).
for _ in range(out.timing.delay_after_step_frames):
    rt.advance_host_frame()
```

A useful pattern is to wrap this into a helper that returns both the output and the total host-frame duration:

```python
from alien_evolution.alienevolution.logic import AlienEvolutionPort
from alien_evolution.zx.runtime import FrameInput, StepOutput


def step_with_timing(rt: AlienEvolutionPort, inp: FrameInput) -> tuple[StepOutput, int]:
    out = rt.step(inp)
    delay = int(out.timing.delay_after_step_frames)
    for _ in range(max(0, delay)):
        rt.advance_host_frame()
    return out, 1 + max(0, delay)
```

### 6.2 Action mapping (a compact discrete action space)

For many RL algorithms it is convenient to reduce the raw bitfields to a small discrete action space.

Example: 9 actions (no-op, 4 directions, 4 directions with fire):

```python
from alien_evolution.zx.runtime import FrameInput

JOY_RIGHT = 1 << 0
JOY_LEFT  = 1 << 1
JOY_DOWN  = 1 << 2
JOY_UP    = 1 << 3
JOY_FIRE  = 1 << 4

ACTIONS = [
    0,
    JOY_UP,
    JOY_DOWN,
    JOY_LEFT,
    JOY_RIGHT,
    JOY_UP | JOY_FIRE,
    JOY_DOWN | JOY_FIRE,
    JOY_LEFT | JOY_FIRE,
    JOY_RIGHT | JOY_FIRE,
]


def frame_input_from_action(action_id: int) -> FrameInput:
    joy = ACTIONS[action_id]
    # Keep keyboard neutral for gameplay; use it only when you need menu actions.
    return FrameInput(joy_kempston=joy, keyboard_rows=(0xFF,) * 8)
```

If you need keyboard events (for example, navigating the title/menu), generate `keyboard_rows` from key presses. The mapping table is in `alien_evolution.zx.inputmap`.

### 6.3 Reading score and objective counters (semantic reward signals)

This port keeps several HUD-facing counters as explicit runtime fields. Two are especially useful for ML:

- Score: a 5-digit counter stored as digits (0..9) in:
  - `var_runtime_aux_c8_lo` (10,000s), `var_runtime_aux_c8_hi` (1,000s), `var_runtime_aux_ca` (100s), `var_runtime_aux_cb` (10s), `var_runtime_aux_cc` (1s)

- Alien population objective counter: a 3-digit counter stored as digits (0..9) in:
  - `var_runtime_progress_byte_2` (100s), `var_runtime_progress_byte_1` (10s), `var_runtime_progress_byte_0` (1s)

These are convenient because they are already “semantic”: you do not need to parse pixels.

```python
from alien_evolution.alienevolution.logic import AlienEvolutionPort


def read_score(rt: AlienEvolutionPort) -> int:
    return (
        (rt.var_runtime_aux_c8_lo & 0xFF) * 10_000
        + (rt.var_runtime_aux_c8_hi & 0xFF) * 1_000
        + (rt.var_runtime_aux_ca & 0xFF) * 100
        + (rt.var_runtime_aux_cb & 0xFF) * 10
        + (rt.var_runtime_aux_cc & 0xFF)
    )


def read_population(rt: AlienEvolutionPort) -> int:
    return (
        (rt.var_runtime_progress_byte_2 & 0xFF) * 100
        + (rt.var_runtime_progress_byte_1 & 0xFF) * 10
        + (rt.var_runtime_progress_byte_0 & 0xFF)
    )


def is_level_complete(rt: AlienEvolutionPort) -> bool:
    return read_population(rt) == 0
```

A simple shaped reward that aligns with the game objective is:

- positive when population decreases,
- negative when population increases (reproduction),
- plus (optionally) incremental score.

For example:

```python
def step_reward(rt: AlienEvolutionPort, prev_score: int, prev_pop: int) -> float:
    score = read_score(rt)
    pop = read_population(rt)

    # Reward progress toward clearing: killing aliens reduces the counter.
    # Penalize population growth (eggs).
    r_pop = float(prev_pop - pop)

    # Optionally add a small score delta term.
    r_score = 0.01 * float(score - prev_score)

    return r_pop + r_score
```

The exact scaling is a research choice; the important point is that you can measure the underlying quantities precisely.

### 6.4 Episode termination (“done”)

There is no universal “done” signal because different experiments want different episodes. Common definitions:

- End episode when the level is cleared (`population == 0`).
- End episode on failure (time bar exhausted, objective counter exhausted, or transition back to menu).
- Use a fixed horizon and treat everything as continuing control (useful for value estimation).

If you are comfortable depending on internal FSM fields, you can also define done in terms of `_fsm_transition_kind` or `_fsm_state` (these are part of the saved state). Otherwise, define done via counters you care about (population/time/lives) and/or via observation heuristics.

---

## 7. Workflow C: state snapshots, rollback, and tree search

If your goal is planning (not only reactive control), being able to branch from the same state is extremely valuable. This port provides full state snapshots.

### 7.1 What “state” means here

A runtime state is a JSON-serializable envelope (a nested dict) with these top-level fields:

- `format`: currently `zx-runtime-state-v1`
- `runtime_id`: identifies the runtime implementation
- `schema_version` and `schema_hash`: compatibility guardrails
- `payload`: the serialized dynamic runtime fields (values, pointers, object references)
- `meta`: metadata such as host frame counter

You do not need to interpret the payload to use it. Treat it as an opaque blob that can be saved, stored, and loaded.

### 7.2 Capturing and restoring state in Python

```python
from alien_evolution.alienevolution.logic import AlienEvolutionPort

rt = AlienEvolutionPort()
rt.reset()

s0 = rt.save_state()      # snapshot (dict)

# ... run some steps ...

rt.load_state(s0)         # restore exactly
```

The state envelope is validated on load (runtime id, schema version, schema hash). This is useful in experiments: it prevents accidental mixing of checkpoints across incompatible builds.

### 7.3 One-step branching evaluation (lookahead)

A minimal “evaluate all actions from the same state” pattern:

```python
from alien_evolution.alienevolution.logic import AlienEvolutionPort
from alien_evolution.zx.runtime import FrameInput


def evaluate_actions_from_state(rt: AlienEvolutionPort, state: dict[str, object], action_ids: list[int]) -> list[tuple[int, float]]:
    results: list[tuple[int, float]] = []

    # Establish baseline counters for reward deltas.
    rt.load_state(state)
    base_score = read_score(rt)
    base_pop = read_population(rt)

    for a in action_ids:
        rt.load_state(state)
        out, _host_frames = step_with_timing(rt, frame_input_from_action(a))

        r = step_reward(rt, prev_score=base_score, prev_pop=base_pop)
        results.append((a, r))

    return results
```

This is the core primitive for greedy planning, beam search, and the rollout phase of MCTS.

### 7.4 Depth-limited tree traversal skeleton

Below is a small, explicit skeleton for depth-limited best-first search over game states. It is not an “RL algorithm”; it is a planning baseline that is often informative when studying delayed reward.

```python
from __future__ import annotations

from dataclasses import dataclass
import heapq

from alien_evolution.alienevolution.logic import AlienEvolutionPort


@dataclass(frozen=True)
class Node:
    priority: float
    depth: int
    state: dict[str, object]
    score: int
    pop: int


def fitness(score: int, pop: int) -> float:
    # Example: higher score is better; lower population is better.
    # Adjust weights to your experiment.
    return float(score) - 1000.0 * float(pop)


def expand(rt: AlienEvolutionPort, node: Node, action_ids: list[int]) -> list[Node]:
    children: list[Node] = []

    for a in action_ids:
        rt.load_state(node.state)
        _out, _host_frames = step_with_timing(rt, frame_input_from_action(a))
        s1 = rt.save_state()
        score1 = read_score(rt)
        pop1 = read_population(rt)

        prio = -fitness(score1, pop1)  # heapq is min-heap; negate for max-search
        children.append(Node(priority=prio, depth=node.depth + 1, state=s1, score=score1, pop=pop1))

    return children


def best_first_plan(rt: AlienEvolutionPort, *, start_state: dict[str, object], depth_limit: int, budget: int = 10_000) -> Node:
    action_ids = list(range(len(ACTIONS)))

    rt.load_state(start_state)
    root = Node(
        priority=-fitness(read_score(rt), read_population(rt)),
        depth=0,
        state=start_state,
        score=read_score(rt),
        pop=read_population(rt),
    )

    frontier: list[Node] = [root]
    heapq.heapify(frontier)
    best = root

    steps = 0
    while frontier and steps < budget:
        cur = heapq.heappop(frontier)
        cur_fit = -cur.priority
        if cur_fit > (-best.priority):
            best = cur

        if cur.depth >= depth_limit:
            steps += 1
            continue

        # Optional termination: stop expanding solved states.
        if cur.pop == 0:
            return cur

        for child in expand(rt, cur, action_ids):
            heapq.heappush(frontier, child)

        steps += 1

    return best
```

What this gives you:

- A deterministic way to test “how much planning helps” relative to reactive baselines.
- A direct use of rollback: the search always expands children from identical parent states.

For MCTS, replace the priority queue with visit/value statistics and rollouts; the save/load primitive is the same.

### 7.5 Practical note: copying states

`save_state()` returns a nested Python dict containing lists and dicts. If you store it and then mutate it accidentally, your experiments will be non-reproducible.

In planning code, treat state envelopes as immutable. If you need defensive copying, use `copy.deepcopy(state)` or a JSON round-trip (`json.loads(json.dumps(state))`). The JSON round-trip is slower but guarantees no shared references.

---

## 8. Dataset generation, offline RL, and demonstrations

Because the headless interface is log-friendly, you can generate datasets in several ways:

- Online rollouts: generate JSONL inputs from a policy, run `alienevolution-cli`, store JSONL outputs, compute rewards offline.

- State-conditioned curricula: collect a library of mid-game state snapshots and sample episodes from them (this is much easier than scripting menu navigation).

- Demonstrations from emulator recordings:
  - Record an RZX run in Fuse (or another RZX-capable emulator).
  - Replay those inputs through the port using `--input-rzx`.
  - Emit JSONL telemetry (and optionally FMF) to build supervised / imitation datasets or to benchmark policy evaluation.

FMF output is useful even for ML work: it is a compact way to inspect whether a learned policy is actually doing what your reward suggests.

---

## 9. Time base and discounting

The environment exposes an explicit host-frame duration per step:

- `host_frames = 1 + delay_after_step_frames`

If you interpret discounting as “per real-time frame” (50 Hz), a consistent way to discount is:

- \(\gamma_{step} = \gamma_{host}^{host\_frames}\)

where `gamma_host` is your discount per host frame.

If you instead treat each environment step as one abstract time unit, you can ignore host-frame timing and use a constant step discount. Both are defensible; the choice should match what you are studying.

---

## 10. Minimal Gym-style wrapper (illustrative)

This is not a dependency of the project, but a reference for how you might wrap the runtime into the common `(obs, reward, done, info)` shape.

```python
from __future__ import annotations

from dataclasses import dataclass

from alien_evolution.alienevolution.logic import AlienEvolutionPort
from alien_evolution.zx.runtime import FrameInput


@dataclass
class StepResult:
    obs_bitmap: bytes
    obs_attrs: bytes
    flash_phase: int
    reward: float
    done: bool
    info: dict


class AlienEvolutionEnv:
    def __init__(self) -> None:
        self.rt = AlienEvolutionPort()
        self.prev_score = 0
        self.prev_pop = 0

    def reset(self, *, state: dict[str, object] | None = None) -> StepResult:
        if state is None:
            self.rt.reset()
        else:
            self.rt.load_state(state)

        # Establish baselines for reward deltas.
        self.prev_score = read_score(self.rt)
        self.prev_pop = read_population(self.rt)

        # Observation without advancing simulation.
        out = self.rt.snapshot_output()
        return StepResult(
            obs_bitmap=out.screen_bitmap,
            obs_attrs=out.screen_attrs,
            flash_phase=out.flash_phase,
            reward=0.0,
            done=False,
            info={"host_frames": 0},
        )

    def step(self, action_id: int) -> StepResult:
        inp = frame_input_from_action(action_id)
        out, host_frames = step_with_timing(self.rt, inp)

        score = read_score(self.rt)
        pop = read_population(self.rt)
        r = step_reward(self.rt, prev_score=self.prev_score, prev_pop=self.prev_pop)

        self.prev_score = score
        self.prev_pop = pop

        done = is_level_complete(self.rt)

        return StepResult(
            obs_bitmap=out.screen_bitmap,
            obs_attrs=out.screen_attrs,
            flash_phase=out.flash_phase,
            reward=r,
            done=done,
            info={"host_frames": host_frames, "score": score, "population": pop},
        )
```

The wrapper above deliberately treats “step time” as the agent’s decision frequency and folds post-step delays into the environment internals. This matches the runtime contract and avoids presenting the agent with states where the original program would be waiting in a HALT-driven loop.

---

## 11. What to log for reproducible ML experiments

If reproducibility matters (and it usually does):

- Store the exact JSONL input stream used for evaluation episodes.
- Store the produced JSONL output telemetry.
- Store the build identifier (git commit) and the state schema hash (available inside saved states).
- If you use saved-state curricula, store the exact state envelopes used as start states.

With those, you can reproduce runs deterministically and you can do counterfactual evaluation (“same start state, different policy”) reliably.
