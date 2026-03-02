from __future__ import annotations

from .logic import AlienEvolutionPort
from ..pyxel.runner import (
    DEFAULT_HISTORY_INTERVAL_HOST_FRAMES,
    DEFAULT_HISTORY_MAX_CHECKPOINTS,
    run_pyxel_game,
)

def main() -> None:
    run_pyxel_game(
        AlienEvolutionPort(),
        title="Alien Evolution (Python port)",
        history_interval_host_frames=DEFAULT_HISTORY_INTERVAL_HOST_FRAMES,
        history_max_checkpoints=DEFAULT_HISTORY_MAX_CHECKPOINTS,
    )
