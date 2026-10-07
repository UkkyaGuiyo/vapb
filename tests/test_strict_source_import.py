import tempfile
import types
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from strict_source_import import load_source_package


class StrictSourceImportTests(unittest.TestCase):
    def make_package(self, root: Path, marker: str) -> Path:
        package = root / "fixture_pkg"
        package.mkdir(parents=True)
        (package / "__init__.py").write_text(
            f"from .child import VALUE\nROOT_MARKER = {marker!r}\n", encoding="utf-8")
        (package / "child.py").write_text(f"VALUE = {marker!r}\n", encoding="utf-8")
        return package

    def clear_fixture_namespace(self):
        for name in list(sys.modules):
            if name == "fixture_pkg" or name.startswith("fixture_pkg."):
                del sys.modules[name]

    def test_rejects_child_preloaded_from_another_checkout_without_replacing_it(self):
        with tempfile.TemporaryDirectory() as temp:
            root_a = Path(temp) / "checkout-a"
            root_b = Path(temp) / "checkout-b"
            package_a = self.make_package(root_a, "A")
            self.make_package(root_b, "B")
            self.clear_fixture_namespace()
            cached_child = type(sys)("fixture_pkg.child")
            cached_child.__file__ = str(package_a / "child.py")
            sys.modules["fixture_pkg.child"] = cached_child

            try:
                with self.assertRaisesRegex(ImportError, "fixture_pkg.child"):
                    load_source_package(root_b / "fixture_pkg", "fixture_pkg")
                self.assertIs(sys.modules["fixture_pkg.child"], cached_child)
                self.assertNotIn("fixture_pkg", sys.modules)
            finally:
                self.clear_fixture_namespace()

    def test_rejects_child_preloaded_from_the_selected_root(self):
        with tempfile.TemporaryDirectory() as temp:
            package = self.make_package(Path(temp) / "checkout", "selected")
            self.clear_fixture_namespace()
            cached_child = type(sys)("fixture_pkg.child")
            cached_child.__file__ = str(package / "child.py")
            sys.modules["fixture_pkg.child"] = cached_child

            try:
                with self.assertRaisesRegex(ImportError, "fixture_pkg.child"):
                    load_source_package(package, "fixture_pkg")
                self.assertIs(sys.modules["fixture_pkg.child"], cached_child)
                self.assertNotIn("fixture_pkg", sys.modules)
            finally:
                self.clear_fixture_namespace()

    def test_rejects_cached_root_even_without_children(self):
        with tempfile.TemporaryDirectory() as temp:
            package = self.make_package(Path(temp) / "checkout", "selected")
            self.clear_fixture_namespace()
            cached_root = type(sys)("fixture_pkg")
            cached_root.__file__ = str(package / "__init__.py")
            sys.modules["fixture_pkg"] = cached_root

            try:
                with self.assertRaisesRegex(ImportError, "fixture_pkg"):
                    load_source_package(package, "fixture_pkg")
                self.assertIs(sys.modules["fixture_pkg"], cached_root)
            finally:
                self.clear_fixture_namespace()

    def test_empty_namespace_loads_only_from_selected_root(self):
        with tempfile.TemporaryDirectory() as temp:
            root_a = Path(temp) / "checkout-a"
            root_b = Path(temp) / "checkout-b"
            self.make_package(root_a, "A")
            package_b = self.make_package(root_b, "B")
            self.clear_fixture_namespace()
            try:
                loaded = load_source_package(package_b, "fixture_pkg")
                self.assertEqual(loaded.ROOT_MARKER, "B")
                self.assertEqual(loaded.VALUE, "B")
                self.assertEqual(Path(loaded.__file__).resolve(), (package_b / "__init__.py").resolve())
                for name in list(sys.modules):
                    if name == "fixture_pkg" or name.startswith("fixture_pkg."):
                        self.assertTrue(Path(sys.modules[name].__file__).resolve().is_relative_to(package_b.resolve()))
            finally:
                self.clear_fixture_namespace()

    def test_rejects_foreign_child_inserted_during_execution_and_cleans_namespace(self):
        with tempfile.TemporaryDirectory() as temp:
            package = self.make_package(Path(temp) / "selected", "selected")
            foreign_path = Path(temp) / "foreign.py"
            (package / "__init__.py").write_text(
                "import sys, types\n"
                "child = types.ModuleType('fixture_pkg.injected')\n"
                f"child.__file__ = {str(foreign_path)!r}\n"
                "sys.modules['fixture_pkg.injected'] = child\n",
                encoding="utf-8")
            self.clear_fixture_namespace()

            try:
                with self.assertRaisesRegex(ImportError, "escaped selected root"):
                    load_source_package(package, "fixture_pkg")
                self.assertFalse(any(name == "fixture_pkg" or name.startswith("fixture_pkg.")
                                     for name in sys.modules))
            finally:
                self.clear_fixture_namespace()

    def test_cleans_partial_namespace_after_base_exception(self):
        with tempfile.TemporaryDirectory() as temp:
            package = self.make_package(Path(temp) / "selected", "selected")
            (package / "__init__.py").write_text(
                "from .child import VALUE\nraise SystemExit(9)\n", encoding="utf-8")
            self.clear_fixture_namespace()

            try:
                with self.assertRaises(SystemExit):
                    load_source_package(package, "fixture_pkg")
                self.assertFalse(any(name == "fixture_pkg" or name.startswith("fixture_pkg.")
                                     for name in sys.modules))
            finally:
                self.clear_fixture_namespace()


if __name__ == "__main__":
    sys.argv = [__file__]
    unittest.main()
