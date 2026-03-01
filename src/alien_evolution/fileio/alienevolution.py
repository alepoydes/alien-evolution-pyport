from __future__ import annotations

from collections.abc import Sequence

from ..alienevolution.logic import AlienEvolutionPort
from .cli_core import run_fileio_cli


def main(argv: Sequence[str] | None = None) -> int:
    return run_fileio_cli(
        argv=argv,
        prog="alienevolution-cli",
        description="Run AlienEvolutionPort with streaming file/stdin/stdout I/O.",
        runtime_factory=AlienEvolutionPort,
        supports_fmf_output=True,
    )


if __name__ == "__main__":
    raise SystemExit(main())
