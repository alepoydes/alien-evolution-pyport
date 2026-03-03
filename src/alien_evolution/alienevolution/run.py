from __future__ import annotations

from .logic import AlienEvolutionPort
from ..pyxel.runner import (
    run_pyxel_game,
)

def main() -> None:
    run_pyxel_game(
        AlienEvolutionPort(),
        title="Alien Evolution (Python port)",
        # In the browser, periodic full-state snapshots are a noticeable source
        # of stutter. Keep the runner feature available for debugging/ML
        # workflows, but disable it for the default "play" entry-point.
        history_interval_host_frames=0,
        history_max_checkpoints=0,
        dev_tools=False,
    )
