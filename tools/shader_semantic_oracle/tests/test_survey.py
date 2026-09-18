import tempfile
import unittest
from pathlib import Path

from tools.shader_semantic_oracle.survey import validate_output_root


class SurveySafetyTests(unittest.TestCase):
    def test_rejects_repository_output(self):
        repository_root = Path(__file__).resolve().parents[3]
        with self.assertRaises(ValueError):
            validate_output_root(repository_root / "diagnostics")

    def test_allows_external_output(self):
        with tempfile.TemporaryDirectory() as temp:
            self.assertEqual(validate_output_root(Path(temp)), Path(temp).resolve())


if __name__ == "__main__":
    unittest.main()
