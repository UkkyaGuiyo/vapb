"""Public-safe regressions for real-package Material Math socket failures."""
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from unitypackage_blender_importer.blender import material_builder as builder
from unitypackage_blender_importer.unity.material_model import NormalizedMaterial, UnityMaterialData, UnityTextureRef


class MaterialMathTests(unittest.TestCase):
    def setUp(self):
        self.image = bpy.data.images.new('Synthetic pixels', width=2, height=2)
        self.data = UnityMaterialData(path='synthetic.mat', name='Synthetic Material')
        self.ref = UnityTextureRef(property_name='_Synthetic', guid='a' * 32)
        self.material = None

    def tearDown(self):
        if self.material is not None:
            bpy.data.materials.remove(self.material)
        bpy.data.images.remove(self.image)

    def build(self, normalized):
        with patch.object(builder, 'normalize_material', return_value=normalized), \
             patch.object(builder, 'load_texture_by_guid', side_effect=lambda db, guid, **kw: self.image if guid else None):
            self.material = builder.build_material(self.data, SimpleNamespace())
        return self.material.node_tree

    def test_smoothness_uses_first_math_operand_and_image_alpha(self):
        tree = self.build(NormalizedMaterial(name=self.data.name, metallic_tex=self.ref))
        math = next(node for node in tree.nodes if node.type == 'MATH')
        self.assertEqual(math.operation, 'SUBTRACT')
        self.assertEqual(math.inputs[0].default_value, 1.0)
        self.assertEqual(math.inputs[1].links[0].from_socket.name, 'Alpha')
        self.assertEqual(math.outputs[0].links[0].to_socket.name, 'Roughness')

    def test_cutout_uses_second_math_operand_as_threshold(self):
        tree = self.build(NormalizedMaterial(name=self.data.name, base_color_tex=self.ref,
                                             alpha_mode='cutout', alpha_cutoff=0.3))
        math = next(node for node in tree.nodes if node.type == 'MATH')
        self.assertEqual(math.operation, 'GREATER_THAN')
        self.assertAlmostEqual(math.inputs[1].default_value, 0.3)
        self.assertEqual(math.inputs[0].links[0].from_socket.name, 'Alpha')
        self.assertEqual(math.outputs[0].links[0].to_socket.name, 'Alpha')


if __name__ == '__main__':
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(MaterialMathTests))
    if not result.wasSuccessful():
        raise RuntimeError('MATERIAL_MATH_REGRESSION_FAILED')
