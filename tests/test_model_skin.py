import copy
import hashlib
from types import SimpleNamespace
import unittest

from unitypackage_blender_importer.export.model_skin import model_skin_task


def asset(guid, pathname, payload):
    return SimpleNamespace(guid=guid, pathname=pathname, asset_bytes=payload)


class ModelSkinTaskTests(unittest.TestCase):
    def setUp(self):
        self.root, self.nested, self.model = 'a' * 32, 'b' * 32, 'c' * 32
        self.root_bytes = f'''%YAML 1.1
--- !u!1001 &-101
PrefabInstance:
  m_SourcePrefab: {{fileID: 100100000, guid: {self.nested}, type: 3}}
'''.encode()
        self.nested_bytes = f'''%YAML 1.1
--- !u!1001 &202
PrefabInstance:
  m_SourcePrefab: {{fileID: 100100000, guid: {self.model}, type: 3}}
'''.encode()
        self.assets = [asset(self.root, 'Assets/Root.prefab', self.root_bytes),
                       asset(self.nested, 'Assets/Nested.prefab', self.nested_bytes),
                       asset(self.model, 'Assets/Model.fbx', b'raw model')]
        sha = lambda value: hashlib.sha256(value).hexdigest()
        self.metadata = {
            'prefab_guid': self.root, 'prefab_source_sha256': sha(self.root_bytes),
            'source_model_guid': self.model, 'source_model_sha256': sha(b'raw model'),
            'source_model_uid': '-9223372036854775807',
            'source_geometry_uid': '9223372036854775807',
            'realization_id': 'native-instance-1',
            'instance_edges': [
                {'container_guid': self.root, 'container_sha256': sha(self.root_bytes),
                 'instance_file_id': '-101', 'source_guid': self.nested},
                {'container_guid': self.nested, 'container_sha256': sha(self.nested_bytes),
                 'instance_file_id': '202', 'source_guid': self.model},
            ],
        }
        self.bones = [
            {'edited_bone_realization_id': 'edit-a', 'source_model_uid': '-9223372036854775806'},
            {'edited_bone_realization_id': 'edit-b', 'source_model_uid': '9223372036854775806'},
        ]

    def test_two_edge_task_preserves_signed_identity_and_is_deterministic(self):
        task = model_skin_task(self.metadata, self.bones, self.assets)
        self.assertEqual(task['kind'], 'RESTORE_MODEL_SKIN_VARIANT_V1')
        self.assertEqual(task['instance_edges'], self.metadata['instance_edges'])
        self.assertEqual(task['bone_mappings'], self.bones)
        self.assertEqual(task['source_model_uid'], '-9223372036854775807')
        self.assertTrue(task['variant_path'].startswith('Assets/VAPBExport/EditedVariant_'))
        self.assertEqual(task, model_skin_task(self.metadata, list(reversed(self.bones)), self.assets))

    def test_wrong_source_hash_chain_and_missing_document_rejected(self):
        cases = []
        changed = copy.deepcopy(self.metadata)
        changed['instance_edges'][0]['source_guid'] = self.model
        cases.append(changed)
        changed = copy.deepcopy(self.metadata)
        changed['instance_edges'][1]['container_sha256'] = '0' * 64
        cases.append(changed)
        changed = copy.deepcopy(self.metadata)
        changed['instance_edges'][1]['container_guid'] = self.root
        cases.append(changed)
        changed = copy.deepcopy(self.metadata)
        changed['instance_edges'][0]['instance_file_id'] = '-102'
        cases.append(changed)
        changed = copy.deepcopy(self.metadata)
        changed['prefab_source_sha256'] = '0' * 64
        cases.append(changed)
        changed = copy.deepcopy(self.metadata)
        changed['source_model_sha256'] = '0' * 64
        cases.append(changed)
        for metadata in cases:
            with self.subTest(metadata=metadata), self.assertRaises(ValueError):
                model_skin_task(metadata, self.bones, self.assets)
        wrong_serialized_source = self.nested_bytes.replace(self.model.encode(), self.root.encode())
        changed_assets = [self.assets[0], asset(self.nested, 'Assets/Nested.prefab', wrong_serialized_source), self.assets[2]]
        changed = copy.deepcopy(self.metadata)
        changed['instance_edges'][1]['container_sha256'] = hashlib.sha256(wrong_serialized_source).hexdigest()
        with self.assertRaises(ValueError):
            model_skin_task(changed, self.bones, changed_assets)

    def test_duplicate_guid_and_duplicate_document_rejected(self):
        with self.assertRaises(ValueError):
            model_skin_task(self.metadata, self.bones, self.assets + [self.assets[0]])
        duplicate_doc = self.root_bytes + self.root_bytes[self.root_bytes.index(b'--- !u!1001'):]
        changed_assets = [asset(self.root, 'Assets/Root.prefab', duplicate_doc), *self.assets[1:]]
        changed = copy.deepcopy(self.metadata)
        changed['prefab_source_sha256'] = hashlib.sha256(duplicate_doc).hexdigest()
        changed['instance_edges'][0]['container_sha256'] = changed['prefab_source_sha256']
        with self.assertRaises(ValueError):
            model_skin_task(changed, self.bones, changed_assets)

    def test_zero_out_of_range_and_duplicate_bones_rejected(self):
        for key in ('source_model_uid', 'source_geometry_uid'):
            changed = copy.deepcopy(self.metadata)
            changed[key] = '0'
            with self.assertRaises(ValueError):
                model_skin_task(changed, self.bones, self.assets)
        changed = copy.deepcopy(self.metadata)
        changed['instance_edges'][0]['instance_file_id'] = '-9223372036854775809'
        with self.assertRaises(ValueError):
            model_skin_task(changed, self.bones, self.assets)
        for bones in ([self.bones[0], self.bones[0]],
                      [{**self.bones[0], 'edited_bone_realization_id': 'edit-b'}, self.bones[1]],
                      [{**self.bones[0], 'source_model_uid': '0'}]):
            with self.assertRaises(ValueError):
                model_skin_task(self.metadata, bones, self.assets)

class SourceModelSkinTaskTests(unittest.TestCase):
    setUp = ModelSkinTaskTests.setUp
    def source_metadata(self):
        return {key: value for key, value in self.metadata.items()
                if key not in ('prefab_guid', 'prefab_source_sha256', 'instance_edges')}

    def test_source_model_task_has_no_invented_prefab(self):
        from unitypackage_blender_importer.export.model_skin import source_model_skin_task, group_model_skin_tasks
        task = source_model_skin_task(self.source_metadata(), self.bones, [self.assets[-1]])
        self.assertEqual(task['kind'], 'RESTORE_SOURCE_MODEL_SKIN_VARIANT_V1')
        self.assertNotIn('prefab_guid', task)
        self.assertEqual(task['instance_edges'], [])
        self.assertEqual(task['source_geometry_uid'], self.metadata['source_geometry_uid'])
        task['model_guid'] = 'd' * 32
        self.assertEqual(group_model_skin_tasks([task]), (task,))
        with self.assertRaises(ValueError):
            group_model_skin_tasks([task, task])

    def test_source_parent_transform_mapping_has_a_distinct_role(self):
        from unitypackage_blender_importer.export.model_skin import source_model_skin_task
        row = dict(source_model_uid='91', edited_transform_realization_id='parent-object')
        task = source_model_skin_task({**self.source_metadata(), 'parent_transform_mapping': row},
                                     self.bones, [self.assets[-1]])
        self.assertEqual(task['parent_transform_mapping'], row)
        self.assertEqual(task['bone_mappings'], self.bones)
        for bad in ({**row, 'source_model_uid': self.bones[0]['source_model_uid']},
                    {**row, 'source_model_uid': self.metadata['source_model_uid']},
                    {**row, 'edited_transform_realization_id': 'edit-a'},
                    {**row, 'edited_transform_realization_id': ''}, []):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                source_model_skin_task({**self.source_metadata(), 'parent_transform_mapping': bad},
                                       self.bones, [self.assets[-1]])

    def test_source_model_rejects_false_revision_prefab_and_duplicate_source(self):
        from unitypackage_blender_importer.export.model_skin import source_model_skin_task
        metadata = self.source_metadata()
        for sources in (self.assets, [self.assets[-1], self.assets[-1]], []):
            with self.assertRaises(ValueError):
                source_model_skin_task(metadata, self.bones, sources)
        for key, value in (('source_model_sha256', '0' * 64), ('source_geometry_uid', '0'),
                           ('prefab_guid', self.root), ('instance_edges', self.metadata['instance_edges'])):
            with self.subTest(key=key), self.assertRaises(ValueError):
                source_model_skin_task({**metadata, key: value}, self.bones, [self.assets[-1]])


if __name__ == '__main__':
    unittest.main()
