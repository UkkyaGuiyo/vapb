import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from strict_run_paths import validate_run_paths, validate_strict_runner_paths, write_json_exclusive


class StrictRunPathTests(unittest.TestCase):
    def test_rejects_result_alias_of_package(self):
        with tempfile.TemporaryDirectory() as temp:
            package = Path(temp) / "input.unitypackage"
            package.write_bytes(b"package")
            with self.assertRaisesRegex(ValueError, "aliases protected input"):
                validate_run_paths(
                    {"package": package},
                    {"result": package.parent / "." / package.name},
                )

    def test_rejects_export_alias_of_result(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "result.unitypackage"
            with self.assertRaisesRegex(ValueError, "output paths alias"):
                validate_run_paths({}, {"result": output, "export": output.parent / "x" / ".." / output.name})

    def test_rejects_t0b_report_alias_of_derived_export(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with self.assertRaisesRegex(ValueError, "output paths alias"):
                validate_strict_runner_paths(root / "in.pkg", root / "oracle.json",
                    root / "witness.json", root / "result.json", root / "scene.blend",
                    root / "t0b-report.unitypackage")

    def test_rejects_t0b_report_alias_of_saved_blend(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with self.assertRaisesRegex(ValueError, "output paths alias"):
                validate_strict_runner_paths(root / "in.pkg", root / "oracle.json",
                    root / "witness.json", root / "result.json", root / "t0b-report.blend",
                    root / "t0b-report.blend")

    def test_rejects_existing_output_without_changing_it(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "result.json"
            output.write_bytes(b"preserve me")
            with self.assertRaisesRegex(FileExistsError, "output already exists"):
                validate_run_paths({}, {"result": output})
            self.assertEqual(output.read_bytes(), b"preserve me")

    def test_accepts_distinct_new_outputs(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            package = root / "input.unitypackage"
            package.write_bytes(b"package")
            outputs = {name: root / name for name in ("result.json", "scene.blend", "export.unitypackage")}
            validate_run_paths({"package": package}, outputs)

    def test_exclusive_json_write_does_not_replace_existing_file(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "result.json"
            output.write_bytes(b"preserve me")
            with self.assertRaises(FileExistsError):
                write_json_exclusive(output, "new result")
            self.assertEqual(output.read_bytes(), b"preserve me")


if __name__ == "__main__":
    sys.argv = [__file__]
    unittest.main()
