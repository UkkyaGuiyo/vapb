import copy
import unittest

from .hierarchy_comparator import compare, convert, unity_trs

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


class ComparatorTests(unittest.TestCase):
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
