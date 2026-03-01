"""File-based backend for Alien Evolution frame-step runtimes."""

from .cli_core import run_fileio_cli
from .fmf import FMFScreenFrame, FMFScreenReader, FMFScreenWriter
from .runner import (
    iter_jsonl_frame_inputs_from_path,
    iter_jsonl_frame_inputs_from_stream,
    iter_rzx_frame_inputs,
    load_frame_inputs,
    run_frame_loop,
)
from .rzx import RZXFrameControls, RZXFrameInputIterator
from .stateio import load_runtime_state, load_state_json, save_runtime_state, save_state_json

__all__ = [
    "run_fileio_cli",
    "FMFScreenFrame",
    "FMFScreenReader",
    "FMFScreenWriter",
    "iter_jsonl_frame_inputs_from_path",
    "iter_jsonl_frame_inputs_from_stream",
    "iter_rzx_frame_inputs",
    "load_frame_inputs",
    "run_frame_loop",
    "RZXFrameControls",
    "RZXFrameInputIterator",
    "load_state_json",
    "save_state_json",
    "load_runtime_state",
    "save_runtime_state",
]
