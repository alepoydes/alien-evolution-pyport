"""Alien Evolution game-port package."""

from .logic import AlienEvolutionPort


def main() -> None:
    from .run import main as _main

    _main()


__all__ = ["AlienEvolutionPort", "main"]
