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

### Build a source archive from repository

```bash
git archive --format=tar.gz --prefix=alien-evolution/ --output alien-evolution-src.tar.gz HEAD
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

Optional custom output directory:

```bash
./scripts/build_pyxapp.sh alien-evolution /tmp/alien-evolution-web
```

Expected outputs (created in `build/web/` by default):

- `build/web/alien-evolution.pyxapp`
- `build/web/alien-evolution.html`

Run the built app:

```bash
uv run pyxel play build/web/alien-evolution.pyxapp
```

## Build the GitHub Pages site locally

This repository deploys GitHub Pages from a workflow artifact rather than from committed build outputs. The playable web build and static documentation are assembled into `site/` during CI.

Build the same Pages artifact locally:

```bash
./scripts/build_pages_site.sh
```

Expected outputs:

- `site/index.html` and the rendered documentation pages
- `site/play/index.html` for the playable web build

## Enable GitHub Pages deployment

The workflow file is `.github/workflows/pages.yml`.

To enable deployment in GitHub:

1. Open repository `Settings -> Pages`.
2. Under `Build and deployment`, choose `Source: GitHub Actions`.
3. Push to `main` or run the workflow manually from the `Actions` tab.

This keeps generated web build artifacts out of the repository history while still publishing them on Pages.

## Development and contribution rules (placeholder)

No repository-specific contribution rules are defined yet.
