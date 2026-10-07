import sys
import tempfile
import unittest
from pathlib import Path


SAFETY_DIR = (Path(__file__).parent / 'evidence' / 'confirmed_route_winding_20261007').resolve()
sys.path.insert(0, str(SAFETY_DIR))
from confirmed_route_output_safety import (
    resolve_product_package_root, validate_output_path, write_text_exclusive,
)


class ConfirmedRouteOutputSafetyTests(unittest.TestCase):
    def test_rejects_output_path_equal_to_package_input(self):
        with tempfile.TemporaryDirectory() as directory:
            package = Path(directory) / 'fixture.unitypackage'
            package.write_bytes(b'package')
            with self.assertRaisesRegex(ValueError, 'OUTPUT_PATH_ALIASES_INPUT'):
                validate_output_path(package, (package,))

    def test_rejects_output_path_equal_to_open_blend_input(self):
        with tempfile.TemporaryDirectory() as directory:
            blend = Path(directory) / 'scene.blend'
            blend.write_bytes(b'blend')
            alias = Path(directory) / '.' / 'scene.blend'
            with self.assertRaisesRegex(ValueError, 'OUTPUT_PATH_ALIASES_INPUT'):
                validate_output_path(alias, (blend,))

    def test_does_not_overwrite_existing_output(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'result.json'
            output.write_text('keep me', encoding='utf-8')
            with self.assertRaises(FileExistsError):
                write_text_exclusive(output, 'replace me')
            self.assertEqual(output.read_text(encoding='utf-8'), 'keep me')

    def test_creates_new_output(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'result.json'
            write_text_exclusive(output, '{"status":"PASS"}\n')
            self.assertEqual(output.read_text(encoding='utf-8'), '{"status":"PASS"}\n')

    def test_resolves_normal_clone_root(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'vapb'
            self._write_package_layout(root)
            self.assertEqual(resolve_product_package_root(root), root.resolve())

    def test_resolves_checkout_parent_with_addon_named_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package_root = root / 'unitypackage_blender_importer'
            self._write_package_layout(package_root)
            self.assertEqual(resolve_product_package_root(root), package_root.resolve())

    @staticmethod
    def _write_package_layout(root):
        (root / 'blender').mkdir(parents=True)
        (root / '__init__.py').write_text('', encoding='utf-8')
        (root / 'blender' / 'fbx_receipt.py').write_text('', encoding='utf-8')
        (root / 'blender' / 'renderer_binding.py').write_text('', encoding='utf-8')


if __name__ == '__main__':
    unittest.main()
