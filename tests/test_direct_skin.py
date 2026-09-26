import copy
import hashlib
from types import SimpleNamespace
import unittest

from unitypackage_blender_importer.export.model_skin import direct_skin_task


class DirectSkinTaskTests(unittest.TestCase):
    def setUp(self):
        self.prefab_guid, self.model_guid = 'a' * 32, 'b' * 32
        self.prefab = f'''%YAML 1.1
--- !u!1 &10
GameObject:
  m_Component:
  - component: {{fileID: 20}}
  - component: {{fileID: -137}}
--- !u!4 &20
Transform:
  m_GameObject: {{fileID: 10}}
--- !u!4 &21
Transform:
  m_Father: {{fileID: 20}}
--- !u!137 &-137
SkinnedMeshRenderer:
  m_GameObject: {{fileID: 10}}
  m_Mesh: {{fileID: -4300000, guid: {self.model_guid}, type: 3}}
  m_Bones:
  - {{fileID: 20}}
  - {{fileID: 21}}
  m_RootBone: {{fileID: 20}}
'''.encode()
        self.metadata = {'prefab_guid': self.prefab_guid,
            'prefab_source_sha256': hashlib.sha256(self.prefab).hexdigest(),
            'source_model_guid': self.model_guid,
            'source_model_sha256': hashlib.sha256(b'model').hexdigest(),
            'source_model_uid': '-900', 'source_geometry_uid': '800',
            'realization_id': 'native-instance-1'}
        self.bones = [{'edited_bone_realization_id': 'native-bone-a', 'source_model_uid': '100'},
                      {'edited_bone_realization_id': 'native-bone-b', 'source_model_uid': '101'}]

    def task(self, payload=None, metadata=None, bones=None):
        payload = self.prefab if payload is None else payload
        metadata = copy.deepcopy(self.metadata) if metadata is None else metadata
        if payload != self.prefab:
            metadata['prefab_source_sha256'] = hashlib.sha256(payload).hexdigest()
        assets = [SimpleNamespace(guid=self.prefab_guid, pathname='Assets/Avatar.prefab', asset_bytes=payload),
                  SimpleNamespace(guid=self.model_guid, pathname='Assets/Model.fbx', asset_bytes=b'model')]
        return direct_skin_task(metadata, self.bones if bones is None else bones, assets)

    def test_serialized_candidates_preserve_signed_ids_and_bone_slots(self):
        task = self.task()
        self.assertEqual(task['kind'], 'RESTORE_DIRECT_SKIN_VARIANT_V1')
        self.assertEqual(task['instance_edges'], [])
        self.assertEqual(task['renderer_candidates'], [{
            'renderer_file_id': '-137', 'source_mesh_file_id': '-4300000',
            'bone_transform_file_ids': ['20', '21'], 'root_bone_transform_file_id': '20'}])
        self.assertEqual(task['bone_mappings'], self.bones)
        self.assertEqual(task, self.task(bones=list(reversed(self.bones))))

    def test_same_mesh_candidates_remain_unresolved_for_unity(self):
        extra = self.prefab[self.prefab.index(b'--- !u!137'):].replace(b'&-137', b'&138')
        task = self.task(self.prefab + extra)
        self.assertEqual(len(task['renderer_candidates']), 2)
        self.assertNotIn('renderer_file_id', task)

    def test_missing_external_duplicate_or_invalid_bones_are_rejected(self):
        for payload in (self.prefab.replace(b'{fileID: 21}', b'{fileID: 99}'),
                        self.prefab.replace(b'{fileID: 21}', b'{fileID: 20}'),
                        self.prefab.replace(b'{fileID: 21}', b'{fileID: 0}'),
                        self.prefab.replace(b'{fileID: 21}', b'{fileID: 21, guid: cccccccccccccccccccccccccccccccc}'),
                        self.prefab + self.prefab[self.prefab.index(b'--- !u!137'):],
                        self.prefab.replace(self.model_guid.encode(), b'c' * 32)):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                self.task(payload)

    def test_stale_source_and_duplicate_receipts_rejected(self):
        for key in ('prefab_source_sha256', 'source_model_sha256'):
            metadata = dict(self.metadata, **{key: '0' * 64})
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.task(metadata=metadata)
        with self.assertRaises(ValueError):
            self.task(bones=[self.bones[0], self.bones[0]])


if __name__ == '__main__':
    unittest.main()
