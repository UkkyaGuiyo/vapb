import unittest
import hashlib
from types import SimpleNamespace

from unitypackage_blender_importer.export.direct_renderer import direct_renderer_task


class DirectRendererExportTest(unittest.TestCase):
    def setUp(self):
        self.model, self.prefab = 'a' * 32, 'b' * 32
        self.binding = {'occurrence': {'renderer_class_id': 23, 'instance_edge_path': [],
            'root_asset_guid': self.prefab, 'source_key': {'source_asset_guid': self.prefab,
            'renderer_file_id': -20}}, 'mesh_receipt': {'mesh_guid': self.model, 'mesh_file_id': -40},
            'native_realization_id': 'synthetic-id'}
        self.yaml = f'''%YAML 1.1
--- !u!23 &-20
MeshRenderer:
  m_GameObject: {{fileID: 10}}
--- !u!33 &30
MeshFilter:
  m_GameObject: {{fileID: 10}}
  m_Mesh: {{fileID: -40, guid: {self.model}, type: 3}}
'''
        self.binding['occurrence']['source_revision_sha256'] = hashlib.sha256(self.yaml.encode()).hexdigest()

    def asset(self, guid=None, text=None, path='Assets/Fixture.prefab'):
        return SimpleNamespace(guid=guid or self.prefab, pathname=path,
            asset_bytes=(self.yaml if text is None else text).encode(),
            meta_bytes=f'guid: {guid or self.prefab}\n'.encode())

    def assets(self):
        return [self.asset(), self.asset(self.model, 'model', 'Assets/Model.fbx')]

    def test_exact_signed_renderer_and_mesh(self):
        task = direct_renderer_task(self.binding, [None], self.assets())
        self.assertEqual(task['renderer_file_id'], '-20')
        self.assertEqual(task['materials'], [None])

    def test_missing_dependency_rejected(self):
        with self.assertRaises(ValueError):
            direct_renderer_task(self.binding, [], [self.asset()])

    def test_other_prefab_reference_rejected(self):
        with self.assertRaisesRegex(ValueError, '別Asset'):
            direct_renderer_task(self.binding, [], self.assets() + [self.asset('c' * 32)])

    def test_unknown_serialized_state_protected(self):
        with self.assertRaisesRegex(ValueError, '未対応の保存state'):
            direct_renderer_task(self.binding, [], self.assets() + [self.asset('c' * 32, 'opaque', 'Assets/State.asset')])

    def test_skin_and_nested_rejected(self):
        self.binding['occurrence']['renderer_class_id'] = 137
        with self.assertRaises(ValueError):
            direct_renderer_task(self.binding, [], self.assets())

    def test_stale_mesh_reference_rejected(self):
        self.binding['mesh_receipt']['mesh_file_id'] = 41
        with self.assertRaises(ValueError):
            direct_renderer_task(self.binding, [], self.assets())
