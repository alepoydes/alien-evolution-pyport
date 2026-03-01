from __future__ import annotations

from collections.abc import Sequence


def main(argv: Sequence[str] | None = None) -> int:
    from ..fileio.demoline import main as _main

    return _main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
