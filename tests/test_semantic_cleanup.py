import unittest

from unitypackage_blender_importer.blender.semantic_cleanup import bone_retention, slot_retention


class CleanupPolicyTests(unittest.TestCase):
    def test_weighted_descendant_protects_all_ancestors(self):
        result = bone_retention({'a': None, 'b': 'a', 'unused': None}, {'b': {'WEIGHT'}})
        self.assertEqual(result['unused'], ())
        self.assertIn('WEIGHT', result['b'])
        self.assertIn('USED_DESCENDANT', result['a'])

    def test_zero_weight_reference_is_kept(self):
        result = bone_retention({'root': None, 'target': 'root'}, {'target': {'BONE_PARENT'}})
        self.assertIn('BONE_PARENT', result['target'])
        self.assertTrue(result['root'])

    def test_unknown_keeps_every_bone(self):
        result = bone_retention({'a': None, 'b': None}, {}, {'UNITY_REFERENCE_UNRESOLVED'})
        self.assertTrue(all('UNITY_REFERENCE_UNRESOLVED' in value for value in result.values()))

    def test_invalid_parent_graph_fails_closed(self):
        for graph in ({'a': 'missing'}, {'a': 'b', 'b': 'a'}):
            with self.assertRaises(ValueError):
                bone_retention(graph, {})

    def test_material_slot_requires_no_geometry_or_other_reference(self):
        result = slot_retention(4, {0}, {1: {'ANIMATION'}}, set())
        self.assertEqual(result[2], ())
        self.assertEqual(result[3], ())
        self.assertIn('POLYGON', result[0])
        self.assertIn('ANIMATION', result[1])
        self.assertTrue(all(slot_retention(4, {0}, {}, {'UNKNOWN'}).values()))


if __name__ == '__main__':
    unittest.main()
