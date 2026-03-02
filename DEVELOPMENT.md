# Development and Contributing

This document is a lightweight onboarding page for developers who want to work on this repository and contribute changes.

There are intentionally no contribution rules defined yet.
This file is currently focused on practical local commands and workflows.

## Common Commands

### Environment setup

```bash
uv sync
```

### Run the interactive Pyxel game

```bash
uv run alienevolution
```

### Run the demoline variant

```bash
uv run demoline
```

### Run tests

```bash
uv run --with pytest pytest tests -q
```

## Build a `pyxapp` and HTML build

Build artifacts with the helper script:

```bash
./scripts/build_pyxapp.sh
```

Optional custom output basename:

```bash
./scripts/build_pyxapp.sh alien-evolution
```

Expected outputs (created in repository root):

- `alien-evolution.pyxapp`
- `alien-evolution.html`

Run the built app:

```bash
uv run pyxel play alien-evolution.pyxapp
```

## Development and contribution rules (placeholder)

No repository-specific contribution rules are defined yet.
