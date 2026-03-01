from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from alien_evolution.alienevolution.logic import AlienEvolutionPort
from alien_evolution.fileio.cli_core import run_fileio_cli
from alien_evolution.fileio.stateio import save_state_json


class CLIStateIOTests(unittest.TestCase):
    def test_state_only_mode_load_and_save_without_frame_outputs(self) -> None:
        runtime = AlienEvolutionPort()
        state_in = runtime.save_state()

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            state_in_path = tmp_path / "in.state.json"
            state_out_path = tmp_path / "out.state.json"
            save_state_json(state_in_path, state_in)

            exit_code = run_fileio_cli(
                argv=[
                    "--load-state",
                    str(state_in_path),
                    "--save-state",
                    str(state_out_path),
                ],
                prog="alienevolution-cli",
                description="test",
                runtime_factory=AlienEvolutionPort,
                supports_fmf_output=True,
            )

            self.assertEqual(exit_code, 0)
            self.assertTrue(state_out_path.exists())


if __name__ == "__main__":
    unittest.main()

