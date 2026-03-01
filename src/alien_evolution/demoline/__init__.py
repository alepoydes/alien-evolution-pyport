"""Alien Evolution demo line layer.

This subpackage keeps game-specific code separate from the generic ZX helper
layer in :mod:`alien_evolution.zx`.
"""

from .logic import DemoLineGame


def main() -> None:
    from .run import main as _main

    _main()

__all__ = [
    "DemoLineGame",
    "main",
]
