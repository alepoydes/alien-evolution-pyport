from __future__ import annotations

from ..demoline.logic import DemoLineGame
from .runner import run_pyxel_game


def main() -> None:
    run_pyxel_game(
        DemoLineGame(),
        title="Alien Evolution (ZX logic port)",
    )
