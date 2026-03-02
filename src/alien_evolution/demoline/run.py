from __future__ import annotations

from .logic import DemoLineGame
from ..pyxel.runner import run_pyxel_game

def main() -> None:
    run_pyxel_game(
        DemoLineGame(),
        title="Alien Evolution (ZX logic port)",
    )
