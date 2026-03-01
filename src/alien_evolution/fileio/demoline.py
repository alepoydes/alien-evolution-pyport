from __future__ import annotations

from collections.abc import Sequence

from ..demoline.logic import DemoLineGame
from .cli_core import run_fileio_cli


def main(argv: Sequence[str] | None = None) -> int:
    return run_fileio_cli(
        argv=argv,
        prog="demoline-cli",
        description="Run DemoLineGame with streaming file/stdin/stdout I/O.",
        runtime_factory=DemoLineGame,
        supports_fmf_output=True,
    )


if __name__ == "__main__":
    raise SystemExit(main())
