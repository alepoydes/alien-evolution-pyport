from __future__ import annotations

import argparse
import ast
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Final


TARGET_HELPERS: Final[tuple[str, ...]] = (
    "_ptr_to_zx_addr",
    "_coerce_ptr_to_zx_addr",
    "_resolve_block_ptr",
    "_coerce_zx_addr_to_enum_ptr",
)

ALLOWLIST_METHODS: Final[frozenset[str]] = frozenset(
    {
        "__init__",
        "_init_runtime_state_from_loaded_image",
        "reset",
    }
)


@dataclass(frozen=True, slots=True)
class UsageSite:
    helper: str
    method: str
    lineno: int


def _default_logic_path() -> Path:
    return (
        Path(__file__).resolve().parents[1]
        / "src"
        / "alien_evolution"
        / "alienevolution"
        / "logic.py"
    )


def _default_baseline_path() -> Path:
    return Path(__file__).resolve().with_name("runtime_global_ptr_usage_baseline.json")


def _collect_usage_sites(logic_path: Path) -> list[UsageSite]:
    tree = ast.parse(logic_path.read_text(encoding="utf-8"), filename=str(logic_path))

    class_node: ast.ClassDef | None = None
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "AlienEvolutionPort":
            class_node = node
            break
    if class_node is None:
        raise ValueError(f"Class AlienEvolutionPort not found in {logic_path}")

    sites: list[UsageSite] = []
    for member in class_node.body:
        if not isinstance(member, ast.FunctionDef):
            continue
        if member.name in ALLOWLIST_METHODS:
            continue

        for node in ast.walk(member):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if not isinstance(func, ast.Attribute):
                continue
            if func.attr not in TARGET_HELPERS:
                continue
            if not isinstance(func.value, ast.Name) or func.value.id != "self":
                continue
            sites.append(UsageSite(helper=func.attr, method=member.name, lineno=node.lineno))

    return sites


def _counts_from_sites(sites: list[UsageSite]) -> dict[str, int]:
    counts = {name: 0 for name in TARGET_HELPERS}
    for site in sites:
        counts[site.helper] += 1
    return counts


def _extract_pointer_enum_cardinality(logic_path: Path) -> int:
    tree = ast.parse(logic_path.read_text(encoding="utf-8"), filename=str(logic_path))
    class_node: ast.ClassDef | None = None
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "AlienEvolutionPort":
            class_node = node
            break
    if class_node is None:
        raise ValueError(f"Class AlienEvolutionPort not found in {logic_path}")

    init_method: ast.FunctionDef | None = None
    for member in class_node.body:
        if isinstance(member, ast.FunctionDef) and member.name == "_init_pointer_enum_domains":
            init_method = member
            break
    if init_method is None:
        return 0

    for statement in init_method.body:
        value_node: ast.AST | None = None
        target: ast.AST | None = None
        if isinstance(statement, ast.Assign):
            if len(statement.targets) != 1:
                continue
            target = statement.targets[0]
            value_node = statement.value
        elif isinstance(statement, ast.AnnAssign):
            target = statement.target
            value_node = statement.value
        if target is None or value_node is None:
            continue
        if not isinstance(target, ast.Attribute):
            continue
        if target.attr != "_pointer_enum_domains":
            continue
        if not isinstance(value_node, ast.Tuple):
            raise ValueError(
                "_pointer_enum_domains initializer must be a tuple literal "
                f"in {logic_path}:{statement.lineno}",
            )
        return len(value_node.elts)
    return 0


def _load_baseline(path: Path) -> tuple[dict[str, int], int]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    raw = payload.get("counts")
    if not isinstance(raw, dict):
        raise ValueError(f"Baseline file has no 'counts' dict: {path}")
    counts: dict[str, int] = {}
    for helper in TARGET_HELPERS:
        value = raw.get(helper)
        if not isinstance(value, int):
            raise ValueError(f"Baseline count for {helper!r} is missing or not int in {path}")
        counts[helper] = value
    pointer_enum_limit = payload.get("pointer_enum_limit")
    if not isinstance(pointer_enum_limit, int):
        raise ValueError(f"Baseline file has no integer 'pointer_enum_limit': {path}")
    return counts, pointer_enum_limit


def _write_baseline(
    path: Path,
    counts: dict[str, int],
    logic_path: Path,
    *,
    pointer_enum_cardinality: int,
    pointer_enum_limit: int,
) -> None:
    try:
        logic_repr = str(logic_path.resolve().relative_to(Path.cwd().resolve()))
    except ValueError:
        logic_repr = str(logic_path)
    payload = {
        "version": 1,
        "logic_path": logic_repr,
        "targets": list(TARGET_HELPERS),
        "allowlist_methods": sorted(ALLOWLIST_METHODS),
        "pointer_enum_cardinality": pointer_enum_cardinality,
        "pointer_enum_limit": pointer_enum_limit,
        "counts": counts,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="check_runtime_global_ptr_usage",
        description=(
            "Guardrail for legacy runtime global-address helper usage in AlienEvolutionPort. "
            "Fails if usage counts grow beyond baseline."
        ),
    )
    parser.add_argument(
        "--logic",
        type=Path,
        default=_default_logic_path(),
        help="Path to logic.py",
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        default=_default_baseline_path(),
        help="Path to baseline JSON file.",
    )
    parser.add_argument(
        "--write-baseline",
        action="store_true",
        help="Write current counts into baseline file and exit successfully.",
    )
    parser.add_argument(
        "--pointer-enum-limit",
        type=int,
        default=32,
        help="Maximum allowed cardinality of _pointer_enum_domains tuple.",
    )
    args = parser.parse_args()

    sites = _collect_usage_sites(args.logic)
    counts = _counts_from_sites(sites)
    pointer_enum_cardinality = _extract_pointer_enum_cardinality(args.logic)

    if args.write_baseline:
        _write_baseline(
            args.baseline,
            counts,
            args.logic,
            pointer_enum_cardinality=pointer_enum_cardinality,
            pointer_enum_limit=args.pointer_enum_limit,
        )
        print(f"[ok] baseline written to {args.baseline}")
        for helper in TARGET_HELPERS:
            print(f"  {helper}: {counts[helper]}")
        print(
            "  _pointer_enum_domains cardinality: "
            f"{pointer_enum_cardinality} (limit {args.pointer_enum_limit})",
        )
        return 0

    if not args.baseline.exists():
        raise FileNotFoundError(
            f"Baseline file not found: {args.baseline}. "
            "Run with --write-baseline first.",
        )

    baseline_counts, pointer_enum_limit = _load_baseline(args.baseline)
    failed = False
    for helper in TARGET_HELPERS:
        current = counts[helper]
        baseline = baseline_counts[helper]
        if current > baseline:
            failed = True
            print(
                f"[fail] {helper}: current={current} exceeds baseline={baseline}",
            )
        else:
            print(
                f"[ok] {helper}: current={current}, baseline={baseline}",
            )

    if pointer_enum_cardinality > pointer_enum_limit:
        failed = True
        print(
            "[fail] _pointer_enum_domains cardinality exceeds baseline limit: "
            f"{pointer_enum_cardinality} > {pointer_enum_limit}",
        )
    else:
        print(
            "[ok] _pointer_enum_domains cardinality: "
            f"{pointer_enum_cardinality} <= {pointer_enum_limit}",
        )

    if failed:
        print("[details] runtime usage sites:")
        for site in sorted(sites, key=lambda item: (item.helper, item.method, item.lineno)):
            print(
                f"  {site.helper} at {args.logic}:{site.lineno} (method: {site.method})",
            )
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
