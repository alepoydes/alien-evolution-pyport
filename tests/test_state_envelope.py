from __future__ import annotations

import unittest

from alien_evolution.zx.state import (
    STATE_ENVELOPE_FORMAT_V1,
    StateEnvelopeError,
    build_state_envelope,
    compute_schema_hash,
    validate_state_envelope,
)


class StateEnvelopeTests(unittest.TestCase):
    def test_compute_schema_hash_is_stable(self) -> None:
        manifest = {"fields": ["a", "b"], "ptrs": ["p"]}
        hash_a = compute_schema_hash(schema_version=1, manifest=manifest, codec_version=1)
        hash_b = compute_schema_hash(schema_version=1, manifest=manifest, codec_version=1)
        self.assertEqual(hash_a, hash_b)

    def test_validate_state_envelope_accepts_valid_payload(self) -> None:
        envelope = build_state_envelope(
            runtime_id="alien_evolution.alienevolution.logic.AlienEvolutionPort",
            schema_version=1,
            schema_hash="abc123",
            payload={"values": {}, "block_ptrs": {}, "struct_ptrs": {}, "object_refs": {}},
            meta={"frame_counter": 10, "host_frame_index": 10},
        )
        validated = validate_state_envelope(envelope)
        self.assertEqual(validated["format"], STATE_ENVELOPE_FORMAT_V1)

    def test_validate_state_envelope_rejects_unknown_format(self) -> None:
        envelope = {
            "format": "wrong",
            "runtime_id": "r",
            "schema_version": 1,
            "schema_hash": "h",
            "payload": {},
            "meta": {},
        }
        with self.assertRaises(StateEnvelopeError):
            validate_state_envelope(envelope)


if __name__ == "__main__":
    unittest.main()

