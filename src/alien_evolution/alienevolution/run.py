from __future__ import annotations

import sys

from .logic import AlienEvolutionPort
from ..pyxel.runner import (
    run_pyxel_game,
)


def _is_web_runtime() -> bool:
    return sys.platform == "emscripten"


def main() -> None:
    is_web_runtime = _is_web_runtime()
    run_pyxel_game(
        AlienEvolutionPort(),
        title="Alien Evolution (Python port)",
        # Periodic full-state checkpoints are expensive and disabled in the
        # default play entry-point for both desktop and web.
        history_interval_host_frames=0,
        history_max_checkpoints=0,
        # Keep manual state hotkeys on desktop; disable in web builds.
        dev_tools=not is_web_runtime,
    )
