"""Runtime configuration switches.

The project started as a *fidelity-first* port: lots of validation and
debug-oriented checks to catch mismatches between the Python routines/data and
their ZX Spectrum originals.

Those checks are invaluable during reverse-engineering, but in the browser
(Pyodide / pyxelapp) they have a real CPU cost.

This module centralizes opt-in switches so the default path can stay fast,
while developers can re-enable heavy validation when needed.
"""

from __future__ import annotations

import os


def _env_flag(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return bool(default)
    value = value.strip().lower()
    return value not in ("", "0", "false", "no", "off")


# Bounds/pointer validation is great for development but expensive.
# Default: off (fast path).
ENABLE_RUNTIME_CHECKS: bool = _env_flag("ALIEN_EVOLUTION_RUNTIME_CHECKS", False)
