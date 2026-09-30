import copy
import unittest

from .hierarchy_comparator import compare, convert, unity_trs, point_multiset_equal, triangle_multiset_equal

SHA = 'a' * 64
GUID = 'b' * 32


def ref(number):
    return dict(guid=GUID, localId=str(number), globalId='fixture:' + str(number))


def fixture():
    nodes, objects = [], []
    # root, Hips, Spine, attachment, two occurrences of the same source.
    for index, parent in enumerate((None, 0, 1, 2, 0, 0)):
        node = dict(gameObject=ref(index), transform=ref(100+index),
            parentTransform=ref(100+parent) if parent is not None else None,
            diagnosticName='Same name', sourceChain=[ref(999)] if index in (4,5) else [],
            localPosition=dict(x=0,y=0,z=0), localRotation=dict(x=0,y=0,z=0,w=1),
            localScale=dict(x=1,y=1,z=1), worldMatrix=[1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1], renderers=[])
        nodes.append(node)
        matrix = convert(unity_trs(node))
        objects.append(dict(handle=index, classification='SEMANTIC', representation='EMPTY',
            diagnostic_name='Different name', actual_parent=parent, local_matrix=matrix,
            world_matrix=copy.deepcopy(matrix), metadata=dict(unity_asset_path='Assets/Root.prefab',
            unity_source_package_id='sha256:'+SHA, unity_prefab_file_id=str(index))))
    return dict(nodes=nodes), dict(package_sha256=SHA, import_result=['FINISHED'],
        assets={GUID:'Assets/Root.prefab'}, objects=objects)


def skin_fixture():
    oracle, observed = fixture()
    oracle['nodes'][0]['renderers'] = [dict(component=ref(500), mesh=ref(600),
        bones=[ref(101), ref(102)], rootBone=ref(101))]
    objects = observed['objects']
    mesh = copy.deepcopy(objects[0])
    mesh.update(handle=10, classification='NATIVE_REALIZATION', representation='MESH',
        actual_parent=0, metadata={'_vapb_fbx_model_uid': '900', '_vapb_fbx_mesh_receipt_id': 'mesh',
        '_vapb_renderer_occurrence_id': 'occurrence', '_vapb_skin_root_transform_file_id': '101',
        '_vapb_skin_root_frame_semantic_id': 'frame1'}, mesh_metadata={'_vapb_fbx_mesh_receipt_id': 'mesh'},
        armature_modifiers=[{'target': 11}])
    rig = copy.deepcopy(objects[0])
    rig.update(handle=11, classification='NATIVE_REALIZATION', representation='ARMATURE',
        metadata={}, bones=[dict(diagnostic_name='API channel 0', metadata={'_vapb_fbx_model_uid': '707'}, parent_index=None),
                           dict(diagnostic_name='API channel 1', metadata={'_vapb_fbx_model_uid': '808'}, parent_index=0)])
    objects.extend([mesh, rig])
    bones = []
    for index, uid in enumerate(('707', '808')):
        proxy = copy.deepcopy(objects[0])
        proxy.update(handle=12+index, classification='TECHNICAL_ONLY', metadata={},
            constraints=[dict(kind='CHILD_OF', target=11, subtarget='API channel '+str(index), muted=False, influence=1)])
        objects.append(proxy)
        objects[1+index]['constraints'] = [dict(kind='COPY_TRANSFORMS', target=12+index, muted=False, influence=1)]
        objects[1+index]['metadata']['_vapb_skin_bone_model_uid'] = uid
        objects[1+index]['metadata']['_vapb_semantic_id'] = 'frame'+str(1+index)
        bones.append(dict(model_uid=uid, prefab_transform={'guid':GUID, 'local_id':str(101+index)},
            semantic_carrier_handle=1+index, expected_source_parent_uid='707' if index else '999',
            carrier_constraint_valid=True, pose_delta_pass=True, evaluated_head_world=[0,0,0],
            evaluated_native_world_matrix=copy.deepcopy(objects[0]['world_matrix']),
            expected_native_world_matrix=copy.deepcopy(objects[0]['world_matrix']),
            prefab_unity_world_origin=dict(x=0,y=0,z=0)))
    skin = dict(renderer={'guid':GUID, 'local_id':'500'}, owner_transform={'guid':GUID, 'local_id':'100'},
        occurrence_id='occurrence', mesh_handle=10, armature_handle=11, mesh_guid=GUID, mesh_local_id='600',
        renderer_model_uid='900', bones=bones, root_bone_carrier_handle=1, root_bone_model_uid='707', root_representation='BONE_CARRIER',
        evaluated_world_triangle_corners=[[0,0,0], [-1,0,0], [0,0,1]],
        prefab_unity_world_triangle_corners=[dict(x=0,y=0,z=0),dict(x=1,y=0,z=0),dict(x=0,y=1,z=0)])
    observed['native_skin'] = dict(package_sha256=SHA, source_control_report_pass=True, skins=[skin])
    return oracle, observed


class ComparatorTests(unittest.TestCase):
    def test_same_corner_multiset_does_not_prove_triangle_connectivity(self):
        oracle, observed = skin_fixture()
        skin = observed['native_skin']['skins'][0]
        a, b, c, d, e = ([-x, 0, z] for x, z in ((0, 0), (1, 0), (0, 1), (2, 0.3), (0.2, 2)))
        skin['evaluated_world_triangle_corners'] = [a, b, c, a, d, e]
        expected = [a, b, d, a, c, e]
        skin['prefab_unity_world_triangle_corners'] = [dict(x=-p[0], y=p[2], z=-p[1]) for p in expected]
        self.assertTrue(point_multiset_equal(skin['evaluated_world_triangle_corners'], skin['prefab_unity_world_triangle_corners']))
        result = compare(oracle, observed, SHA)
        self.assertEqual(result['status'], 'RED')
        self.assertIn('NATIVE_REPRESENTATION_MISMATCH', result['counts'])

    def test_triangle_matching_preserves_multiplicity_and_accepts_reordering(self):
        a, b, c, d = ([0, 0, 0], [-1, 0, 0], [0, 0, 1], [-1, 0, 1])
        actual = [a, b, c, b, d, c]
        expected = [dict(x=-p[0], y=p[2], z=-p[1]) for p in [c, d, b, c, a, b]]
        self.assertTrue(triangle_multiset_equal(actual, expected))
        self.assertFalse(triangle_multiset_equal(actual + actual, expected))
        self.assertFalse(triangle_multiset_equal([a, b], expected))
        bad = copy.deepcopy(actual)
        bad[0][0] = float('nan')
        self.assertFalse(triangle_multiset_equal(bad, expected))

    def test_native_skin_positive_and_corruption_controls(self):
        oracle, original = skin_fixture()
        self.assertEqual(compare(oracle, original, SHA)['status'], 'GREEN')
        changes = (
            ('owner', lambda s: s['objects'][6].update(actual_parent=5), 'WRONG_RENDERER_OWNER'),
            ('mesh', lambda s: s['objects'][6]['mesh_metadata'].update(_vapb_fbx_mesh_receipt_id='wrong'), 'MESH_BRIDGE_MISMATCH'),
            ('armature', lambda s: s['objects'][6]['armature_modifiers'][0].update(target=999), 'MESH_BRIDGE_MISMATCH'),
            ('parent', lambda s: s['objects'][7]['bones'][1].update(parent_index=None), 'BONE_BINDING_MISMATCH'),
            ('root', lambda s: s['objects'][1]['metadata'].update(_vapb_skin_bone_model_uid='808'), 'ROOT_BONE_MISMATCH'),
            ('disabled', lambda s: s['objects'][9]['constraints'][0].update(muted=True), 'BONE_BINDING_MISMATCH'),
            ('motion', lambda s: s['native_skin']['skins'][0]['bones'][1].update(pose_delta_pass=False), 'NATIVE_REPRESENTATION_MISMATCH'),
            ('attachment', lambda s: s['objects'][3].update(actual_parent=5), 'WRONG_PARENT'),
            ('geometry', lambda s: s['native_skin']['skins'][0]['evaluated_world_triangle_corners'][0].__setitem__(0,1), 'NATIVE_REPRESENTATION_MISMATCH'),
            ('pose_frame', lambda s: s['native_skin']['skins'][0]['bones'][1]['evaluated_native_world_matrix'][0].__setitem__(0, 2), 'NATIVE_REPRESENTATION_MISMATCH'),
            ('order', lambda s: s['native_skin']['skins'][0]['bones'].reverse(), 'BONE_BINDING_MISMATCH'),
        )
        for label, change, category in changes:
            with self.subTest(label=label):
                observed = copy.deepcopy(original)
                change(observed)
                result = compare(oracle, observed, SHA)
                self.assertEqual(result['status'], 'RED')
                self.assertIn(category, result['counts'])

    def test_root_frame_outside_weighted_slots(self):
        oracle, observed = skin_fixture()
        oracle['nodes'][0]['renderers'][0]['rootBone'] = ref(100)
        observed['objects'][0]['metadata']['_vapb_semantic_id'] = 'frame0'
        observed['objects'][6]['metadata'].update(
            _vapb_skin_root_transform_file_id='100', _vapb_skin_root_frame_semantic_id='frame0')
        observed['native_skin']['skins'][0].update(root_bone_carrier_handle=0,
            root_bone_model_uid=None, root_representation='ROOT_FRAME_OBJECT')
        self.assertEqual(compare(oracle, observed, SHA)['status'], 'GREEN')
        observed['objects'][6]['metadata']['_vapb_skin_root_frame_semantic_id'] = 'wrong'
        self.assertIn('ROOT_BONE_MISMATCH', compare(oracle, observed, SHA)['counts'])

    def test_geometry_multiset_ignores_order_preserves_corners(self):
        expected = [dict(x=1,y=2,z=3)]*2
        self.assertTrue(point_multiset_equal([[-1,-3,2]]*2, expected))
        self.assertFalse(point_multiset_equal([[-1,-3,2]], expected))

    def setUp(self):
        self.oracle, self.snapshot = fixture()

    def result(self):
        return compare(self.oracle, self.snapshot, SHA)

    def test_positive_and_rename(self):
        self.assertEqual(self.result()['status'], 'GREEN')
        for obj in self.snapshot['objects']:
            obj['diagnostic_name'] = 'Rename'
        self.assertEqual(self.result()['status'], 'GREEN')

    def test_missing_and_collapsed(self):
        self.snapshot['objects'].pop()
        self.assertEqual(self.result()['counts']['MISSING'], 1)
        self.assertEqual(self.result()['counts']['MISSING_OCCURRENCE'], 1)

    def test_duplicate_identity_and_repeated_occurrence(self):
        duplicate = copy.deepcopy(self.snapshot['objects'][-1])
        duplicate['handle'] = 10
        self.snapshot['objects'].append(duplicate)
        self.assertEqual(self.result()['counts']['DUPLICATE_OCCURRENCE'], 1)

    def test_wrong_parent_bone_chain_and_attachment(self):
        for index in (1, 2, 3):
            with self.subTest(index=index):
                original = self.snapshot['objects'][index]['actual_parent']
                self.snapshot['objects'][index]['actual_parent'] = 5
                self.assertEqual(self.result()['counts']['WRONG_PARENT'], 1)
                self.snapshot['objects'][index]['actual_parent'] = original

    def test_same_name_unrelated_technical_empty(self):
        extra = copy.deepcopy(self.snapshot['objects'][0])
        extra.update(handle=10, classification='TECHNICAL_ONLY', metadata={})
        self.snapshot['objects'].append(extra)
        self.assertEqual(self.result()['status'], 'GREEN')

    def test_extra_semantic(self):
        extra = copy.deepcopy(self.snapshot['objects'][0])
        extra['handle'] = 10
        extra['metadata']['unity_prefab_file_id'] = '999'
        self.snapshot['objects'].append(extra)
        self.assertEqual(self.result()['counts']['EXTRA_SEMANTIC'], 1)

    def test_transform_and_nonfinite(self):
        for change in (0.1, float('nan')):
            self.snapshot['objects'][0]['local_matrix'][0][3] = change
            self.assertIn('TRANSFORM_MISMATCH', self.result()['counts'])

    def test_revision_mismatch_rejected(self):
        self.snapshot['package_sha256'] = 'c'*64
        with self.assertRaises(ValueError):
            self.result()

    def test_source_identity_without_distinct_occurrence_bridge_is_ambiguous(self):
        self.oracle['nodes'][-1]['gameObject'] = dict(self.oracle['nodes'][-2]['gameObject'])
        self.oracle['nodes'][-1]['gameObject']['globalId'] = 'distinct-global-occurrence'
        self.assertEqual(self.result()['counts']['AMBIGUOUS'], 2)

    def test_native_skin_not_self_scored_from_source_projection(self):
        self.oracle['nodes'][0]['renderers'] = [dict()]
        self.assertEqual(self.result()['counts']['UNSUPPORTED_REPRESENTATION'], 5)
        self.assertEqual(self.result()['status'], 'RED')

    def test_exact_instance_handle_bridge_and_wrong_edge_rejection(self):
        for i in (4,5):
            self.oracle['nodes'][i]['instanceHandles'] = [ref(200+i)]
            self.snapshot['objects'][i]['metadata'].update(
                unity_source_prefab_guid=GUID, unity_prefab_file_id='999',
                _vapb_root_context_id='context', _vapb_model_instance_edge_path=__import__('json').dumps([
                    dict(container_asset_guid=GUID, prefab_instance_file_id=200+i,
                         container_package_id='sha256:'+SHA, source_package_id='sha256:'+SHA,
                         source_prefab_guid=GUID)]))
        self.assertEqual(self.result()['status'], 'GREEN')
        self.snapshot['objects'][5]['metadata']['_vapb_model_instance_edge_path'] = self.snapshot['objects'][4]['metadata']['_vapb_model_instance_edge_path']
        result = self.result()
        self.assertEqual(result['status'], 'RED')
        self.assertIn('DUPLICATE_OCCURRENCE', result['counts'])
