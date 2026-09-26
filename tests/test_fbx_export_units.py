from types import SimpleNamespace
import unittest
from unittest.mock import patch

from unitypackage_blender_importer.blender.fbx_witness import source_export_scale_options


class FbxExportUnitsTests(unittest.TestCase):
    def mode(self, scales, scene_scale=1.0):
        properties = [SimpleNamespace(id=b'P', props=[b'UnitScaleFactor', b'double', b'Number', b'', value])
                      for value in scales]
        settings = SimpleNamespace(id=b'GlobalSettings', elems=[
            SimpleNamespace(id=b'Properties70', elems=properties)])
        root = SimpleNamespace(elems=[settings])
        parser = SimpleNamespace(parse=lambda *args, **kwargs: (root, 7400))
        with patch.dict('sys.modules', {'io_scene_fbx': SimpleNamespace(parse_fbx=parser)}):
            return source_export_scale_options('source.fbx', scene_scale)

    def test_recognized_native_unit_representations(self):
        self.assertEqual(self.mode([1.0]), 'FBX_SCALE_NONE')
        self.assertEqual(self.mode([100.0]), 'FBX_SCALE_ALL')

    def test_missing_duplicate_nonfinite_and_unsupported_scale_rejected(self):
        for scales in ([], [1.0, 1.0], [float('nan')], [float('inf')],
                       [0.0], [-1.0], [True], ['100'], [2.54]):
            with self.subTest(scales=scales), self.assertRaises(ValueError):
                self.mode(scales)

    def test_changed_scene_units_rejected(self):
        with self.assertRaises(ValueError):
            self.mode([100.0], 0.01)


if __name__ == '__main__':
    unittest.main()
