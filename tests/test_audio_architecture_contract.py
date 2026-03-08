from __future__ import annotations

from pathlib import Path
import ast
import unittest

from alien_evolution.zx.runtime import ZXSpectrumServiceLayer


_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_RUNTIME_CONTRACT_FILES = (
    _PROJECT_ROOT / "src/alien_evolution/zx/runtime.py",
    _PROJECT_ROOT / "src/alien_evolution/alienevolution/logic.py",
    _PROJECT_ROOT / "src/alien_evolution/demoline/logic.py",
)


class AudioArchitectureContractTests(unittest.TestCase):
    def test_runtime_layers_do_not_import_backend_modules_or_wall_clock(self) -> None:
        for path in _RUNTIME_CONTRACT_FILES:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names = tuple(alias.name for alias in node.names)
                    self.assertFalse(any(name == "pyxel" or name == "time" for name in names), path)
                if isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    self.assertFalse(module.startswith("alien_evolution.pyxel"), path)
                    self.assertFalse(module.startswith("alien_evolution.fileio"), path)
                if isinstance(node, ast.Attribute) and node.attr == "perf_counter":
                    self.fail(f"{path} must not reference wall-clock APIs directly")

    def test_service_layer_no_longer_exposes_live_audio_clock_query(self) -> None:
        self.assertFalse(hasattr(ZXSpectrumServiceLayer, "current_audio_tick"))


if __name__ == "__main__":
    unittest.main()
