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

Workflow files live in `.github/workflows/`:

- `ci.yml` runs the test suite on pushes to `main`, pull requests, and manual dispatches.
- `pages.yml` builds and deploys the Pages artifact.
- `release.yml` builds versioned GitHub Release assets when a `v*` tag is pushed.

To enable deployment in GitHub:

1. Open repository `Settings -> Pages`.
2. Under `Build and deployment`, choose `Source: GitHub Actions`.
3. Push to `main` or run the workflow manually from the `Actions` tab.

This keeps generated web build artifacts out of the repository history while still publishing them on Pages.

## Release Model

This repository uses two parallel distribution channels:

- GitHub Pages is the rolling public build from the current `main` branch.
- GitHub Releases are immutable tagged snapshots intended for citation, regression triage, and preservation.

When `release.yml` runs for a tag such as `v0.1.0`, it publishes:

- a standalone Pyxel web player HTML file;
- the matching `.pyxapp` package;
- a tarball snapshot of the generated static site.

GitHub automatically adds the tagged source archives (`zip` and `tar.gz`) to the release page as well.

Suggested release flow:

1. Ensure `pyproject.toml` version and release tag agree.
2. Run `uv run --with pytest pytest tests -q`.
3. Create and push a tag like `v0.1.0`.
4. Let GitHub Actions build and attach the release artifacts.

## Development and contribution rules (placeholder)

No repository-specific contribution rules are defined yet.
