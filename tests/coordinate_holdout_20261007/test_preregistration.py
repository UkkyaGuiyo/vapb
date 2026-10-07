import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from prepare_contract import (canonical_bytes, make_oracle, prepare, validate_authored_oracle,
                              verify_frozen_payload)
from contract import public_contract


class PreregistrationTests(unittest.TestCase):
    def payload(self):
        source = {"contract.py": "a" * 64, "oracle.py": "b" * 64}
        contract = canonical_bytes(public_contract())
        oracle = canonical_bytes(make_oracle())
        prereg = {"schema": "vapb-coordinate-holdout-preregistration-v1",
                  "source_sha256": source,
                  "contract_sha256": hashlib.sha256(contract).hexdigest(),
                  "authored_oracle_sha256": hashlib.sha256(oracle).hexdigest()}
        return prereg, source, contract, oracle

    def test_frozen_payload_accepts_exact_pinned_bytes(self):
        prereg, source, contract, oracle = self.payload()
        self.assertTrue(verify_frozen_payload(prereg, source, contract, oracle))

    def test_frozen_payload_rejects_source_and_artifact_tampering(self):
        prereg, source, contract, oracle = self.payload()
        with self.assertRaisesRegex(ValueError, "SOURCE_HASH_MISMATCH"):
            verify_frozen_payload(prereg, {**source, "oracle.py": "c" * 64}, contract, oracle)
        with self.assertRaisesRegex(ValueError, "CONTRACT_HASH_MISMATCH"):
            verify_frozen_payload(prereg, source, contract + b" ", oracle)
        with self.assertRaisesRegex(ValueError, "ORACLE_HASH_MISMATCH"):
            verify_frozen_payload(prereg, source, contract, oracle + b" ")

    def test_oracle_rejects_missing_case_and_nonfinite_corner(self):
        oracle = make_oracle()
        broken = dict(oracle, cases=oracle["cases"][:-1])
        with self.assertRaisesRegex(ValueError, "CASE_SET_INVALID"):
            validate_authored_oracle(broken)
        broken = json.loads(json.dumps(oracle))
        broken["cases"][0]["corners"][0]["blender_local_authored"][0] = float("nan")
        with self.assertRaisesRegex(ValueError, "VECTOR_INVALID"):
            validate_authored_oracle(broken)

    def test_capture_of_existing_output_directory_is_refused_without_modification(self):
        with tempfile.TemporaryDirectory() as parent:
            destination = Path(parent) / "already-frozen"
            destination.mkdir()
            sentinel = destination / "sentinel.txt"
            sentinel.write_text("keep", encoding="utf-8")
            before = sentinel.read_bytes()
            with self.assertRaises(FileExistsError):
                prepare(destination)
            self.assertEqual(sentinel.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
