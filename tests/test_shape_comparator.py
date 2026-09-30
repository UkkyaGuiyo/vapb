import copy
import hashlib
import json
import unittest

from unitypackage_blender_importer.tests.shape_comparator import compare_shapes
from unitypackage_blender_importer.tests.test_model_witness_bridge import record, GUID, FBX_SHA, PACKAGE_SHA
from unitypackage_blender_importer.blender.renderer_binding import semantic_owner_id


def fixture():
    oracle = dict(package_sha256=PACKAGE_SHA, source_fbx_sha256=FBX_SHA, source_meta_sha256='c'*64, meshes=[], prefab_renderers=[])
    witness = dict(source_unitypackage_sha256=PACKAGE_SHA, assets=[dict(asset_guid=GUID,
        source_fbx_sha256=FBX_SHA, source_meta_sha256='c'*64, models=[])])
    native = dict(package_sha256=PACKAGE_SHA, objects=[])
    for i in range(2):
        rec = record()
        rec['source_key']['renderer_file_id'] -= i
        rec['mesh']['mesh_file_id'] -= i
        uid, shape, geometry = 77+i, 88+i, 202+i
        mesh = dict(guid=GUID, local_id=str(rec['mesh']['mesh_file_id']))
        identity = dict(guid=rec['source_key']['source_asset_guid'], local_id=str(rec['source_key']['renderer_file_id']))
        oracle['meshes'].append(dict(mesh=mesh, channels=[dict(channel_index=0)]))
        oracle['prefab_renderers'].append(dict(renderer=identity, mesh=mesh, current_weights=[25]))
        witness['assets'][0]['models'].append(dict(geometry_uid=str(geometry), renderers=[dict(mesh_local_id=mesh['local_id'],
            shape_channels=[dict(unity_channel_index=0, channel_uid=str(uid), shape_uid=str(shape))])]))
        payload = json.dumps(dict(geometry_uid=geometry, fbx_sha256=FBX_SHA,
            channels=[dict(channel_uid=uid, shape_uid=shape, key_index=1, delta_sha256='delta')]))
        native['objects'].append(dict(renderer_record=rec, renderer_occurrence=rec['occurrence_id'], weight_occurrence=rec['occurrence_id'],
            actual_owner=semantic_owner_id(rec), fbx_sha256=FBX_SHA, geometry_uid=str(geometry),
            mesh_receipt='vapb-fbx-mesh:'+hashlib.sha256(f'{FBX_SHA}:{geometry}'.encode()).hexdigest(),
            key_properties={'_vapb_fbx_shape_receipts':payload,'_vapb_fbx_shape_receipt_sha256':hashlib.sha256(payload.encode()).hexdigest()},
            channels=[{},dict(relative_index=0,delta_sha256='delta',value=.25)]))
    return oracle, native, witness


class ShapeComparatorTests(unittest.TestCase):
    def test_missing_shaped_mesh_mapping_cannot_pass_from_another_mesh(self):
        oracle, native, witness = fixture()
        self.assertEqual(compare_shapes(oracle, native, witness)['status'], 'GREEN')
        for value in (None, []):
            bad = copy.deepcopy(witness)
            renderer = bad['assets'][0]['models'][0]['renderers'][0]
            if value is None: del renderer['shape_channels']
            else: renderer['shape_channels'] = value
            self.assertEqual(compare_shapes(oracle, native, bad)['status'], 'RED')

    def test_wrong_mesh_and_weight_are_distinct_errors(self):
        oracle, native, witness = fixture()
        native['objects'][0]['channels'][1]['value'] = .75
        self.assertIn('WEIGHT_VALUE_MISMATCH', compare_shapes(oracle, native, witness)['counts'])
        native['objects'][0]['geometry_uid'] = '999'
        self.assertIn('CHANNEL_IDENTITY_UNPROVEN', compare_shapes(oracle, native, witness)['counts'])
