from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping

from ..zx.state import ensure_stateful_runtime, validate_state_envelope


def load_state_json(path: Path) -> dict[str, object]:
    if not path.exists():
        raise FileNotFoundError(f"State file not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        raw = json.load(f)
    envelope = validate_state_envelope(raw)
    return envelope


def save_state_json(path: Path, state: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as f:
        json.dump(dict(state), f, ensure_ascii=True)
        f.write("\n")
    tmp_path.replace(path)


def load_runtime_state(runtime: object, path: Path) -> dict[str, object]:
    envelope = load_state_json(path)
    stateful = ensure_stateful_runtime(runtime)
    stateful.load_state(envelope)
    return envelope


def save_runtime_state(runtime: object, path: Path) -> dict[str, object]:
    stateful = ensure_stateful_runtime(runtime)
    envelope = stateful.save_state()
    save_state_json(path, envelope)
    return envelope

