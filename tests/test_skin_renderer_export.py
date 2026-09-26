import hashlib
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest

from unitypackage_blender_importer.export.skin_renderer import skin_renderer_task
from unitypackage_blender_importer.export.model_package import materialize_model_package
from unitypackage_blender_importer.tests.test_model_package import make_archive, fields


class SkinExportTests(unittest.TestCase):
    def setUp(self):
        self.model, self.prefab = 'a' * 32, 'b' * 32
        self.yaml = f'''%YAML 1.1
--- !u!137 &-20
SkinnedMeshRenderer:
  m_GameObject: {{fileID: 10}}
  m_Mesh: {{fileID: -40, guid: {self.model}, type: 3}}
  m_Bones:
  - {{fileID: -101}}
  - {{fileID: 102}}
  m_RootBone: {{fileID: -101}}
--- !u!4 &-101
Transform:
  m_GameObject: {{fileID: 11}}
  m_Father: {{fileID: 0}}
--- !u!4 &102
Transform:
  m_GameObject: {{fileID: 12}}
  m_Father: {{fileID: -101}}
'''
        self.binding = {'occurrence': {'renderer_class_id': 137, 'instance_edge_path': [],
            'root_asset_guid': self.prefab, 'source_revision_sha256': hashlib.sha256(self.yaml.encode()).hexdigest(),
            'source_key': {'source_asset_guid': self.prefab, 'renderer_file_id': '-20'}},
            'mesh_receipt': {'mesh_guid': self.model, 'mesh_file_id': '-40',
                             'source_sha256': hashlib.sha256(b'model').hexdigest()},
            'native_realization_id': 'synthetic-skin'}
        self.skin = {'mappings': [{'target_transform_file_id': '-101', 'edited_bone_realization_id': 'bone-a'},
                                  {'target_transform_file_id': '102', 'edited_bone_realization_id': 'bone-b'}],
                     'root_bone_target_transform_file_id': '-101'}
        self.assets = [SimpleNamespace(guid=self.prefab, pathname='Assets/Avatar.prefab',
                         asset_bytes=self.yaml.encode(), meta_bytes=f'guid: {self.prefab}\n'.encode()),
                       SimpleNamespace(guid=self.model, pathname='Assets/Model.fbx',
                         asset_bytes=b'model', meta_bytes=f'guid: {self.model}\n'.encode())]

    def test_direct_skin_uses_explicit_signed_transform_ids(self):
        task = skin_renderer_task(self.binding, self.skin, [], self.assets)
        self.assertEqual(task['kind'], 'REBIND_SKINNED_RENDERER_V1')
        self.assertEqual(task['source_mesh_file_id'], '-40')
        self.assertEqual(task['bones'], self.skin['mappings'])

    def test_missing_or_duplicate_bone_proof_rejected(self):
        for mappings in (self.skin['mappings'][:1], [self.skin['mappings'][0]] * 2):
            with self.assertRaises(ValueError):
                skin_renderer_task(self.binding, {**self.skin, 'mappings': mappings}, [], self.assets)

    def test_mapping_order_is_independent_of_serialized_bone_slots(self):
        self.skin['mappings'].reverse()
        task = skin_renderer_task(self.binding, self.skin, [], self.assets)
        self.assertEqual(task['source_bone_transform_file_ids'], ['-101', '102'])
        self.assertEqual(task['bones'], self.skin['mappings'])

    def test_root_outside_weighted_bone_array_has_separate_explicit_mapping(self):
        self.yaml = self.yaml.replace('m_RootBone: {fileID: -101}', 'm_RootBone: {fileID: 103}')
        self.yaml += '\n--- !u!4 &103\nTransform:\n  m_GameObject: {fileID: 13}\n  m_Father: {fileID: 0}\n'
        self.assets[0].asset_bytes = self.yaml.encode()
        self.binding['occurrence']['source_revision_sha256'] = hashlib.sha256(self.yaml.encode()).hexdigest()
        self.skin['root_bone_target_transform_file_id'] = '103'
        self.skin['mappings'].append({'target_transform_file_id': '103', 'edited_bone_realization_id': 'bone-root'})
        task = skin_renderer_task(self.binding, self.skin, [], self.assets)
        self.assertEqual(task['source_bone_transform_file_ids'], ['-101', '102'])
        self.assertEqual(task['root_bone_target_transform_file_id'], '103')
        self.assertEqual(len(task['bones']), 3)

    def test_source_revision_and_mesh_identity_checked(self):
        self.binding['mesh_receipt']['mesh_file_id'] = '40'
        with self.assertRaises(ValueError):
            skin_renderer_task(self.binding, self.skin, [], self.assets)
        self.binding['mesh_receipt']['mesh_file_id'] = '-40'
        self.binding['occurrence']['source_revision_sha256'] = '0' * 64
        with self.assertRaises(ValueError):
            skin_renderer_task(self.binding, self.skin, [], self.assets)

    def test_whole_source_closure_can_be_staged_without_replacement(self):
        with tempfile.TemporaryDirectory() as directory:
            source = make_archive(Path(directory) / 'Source.unitypackage',
                                  fields(self.model, 'Assets/Model.fbx', b'model'))
            tree, manifest = materialize_model_package([source], [], generator_version='test', blender_version='test')
            self.assertEqual(tree.get(self.model).asset_bytes, b'model')
            self.assertEqual(manifest.reference_rebind_tasks, ())


if __name__ == '__main__':
    unittest.main()
