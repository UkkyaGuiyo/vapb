import copy
import unittest

from unitypackage_blender_importer.export import model_skin


class ModelSkinGroupTests(unittest.TestCase):
    def setUp(self):
        self.first = {
            'kind': 'RESTORE_DIRECT_SKIN_VARIANT_V1',
            'prefab_guid': 'a' * 32, 'prefab_source_sha256': 'b' * 64,
            'model_guid': 'c' * 32, 'realization_id': 'skin-one',
            'instance_edges': [], 'variant_path': 'Assets/VAPBExport/Single.prefab',
        }
        self.second = {**self.first, 'model_guid': 'd' * 32, 'realization_id': 'skin-two'}

    def test_group_is_order_independent_one_variant_and_does_not_mutate_inputs(self):
        inputs = [self.first, self.second]
        before = copy.deepcopy(inputs)
        result = model_skin.group_model_skin_tasks(inputs)
        self.assertEqual(result, model_skin.group_model_skin_tasks(list(reversed(inputs))))
        self.assertEqual(len(result), 2)
        self.assertEqual(len({row['variant_path'] for row in result}), 1)
        self.assertNotEqual(result[0]['variant_path'], self.first['variant_path'])
        self.assertEqual(inputs, before)

    def test_single_task_keeps_existing_variant_identity(self):
        self.assertEqual(model_skin.group_model_skin_tasks([self.first]), (self.first,))

    def test_different_prefab_or_revision_and_duplicate_targets_rejected(self):
        for field, value in (
            ('prefab_guid', 'e' * 32), ('prefab_source_sha256', 'f' * 64),
            ('realization_id', self.first['realization_id']),
            ('model_guid', self.first['model_guid']),
        ):
            with self.subTest(field=field), self.assertRaises(ValueError):
                model_skin.group_model_skin_tasks([self.first, {**self.second, field: value}])

    def test_empty_unknown_kind_and_missing_identity_rejected(self):
        for tasks in ([], [{**self.first, 'kind': 'UNKNOWN'}],
                      [{**self.first, 'realization_id': ''}],
                      [{**self.first, 'model_guid': ''}]):
            with self.subTest(tasks=tasks), self.assertRaises(ValueError):
                model_skin.group_model_skin_tasks(tasks)


if __name__ == '__main__':
    unittest.main()
