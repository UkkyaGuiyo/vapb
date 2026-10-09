from copy import deepcopy
from types import SimpleNamespace as Node
import unittest
from unittest.mock import patch

from unitypackage_blender_importer.blender.fbx_witness import source_skin_bone_uids


class SkinMembershipTests(unittest.TestCase):
    def setUp(self):
        self.objects = [Node(id=kind, props=[uid, b'', subtype], elems=[])
                        for uid, kind, subtype in (
                            (10, b'Model', b'Mesh'), (20, b'Geometry', b'Mesh'),
                            (30, b'Deformer', b'Skin'), (40, b'Deformer', b'Cluster'),
                            (41, b'Deformer', b'Cluster'), (50, b'Model', b'LimbNode'),
                            (51, b'Model', b'LimbNode'), (52, b'Model', b'LimbNode'))]
        self.links = [(20, 10), (30, 20), (40, 30), (41, 30), (50, 40), (51, 41)]

    def read(self, reader=source_skin_bone_uids):
        root = Node(elems=[Node(id=b'Objects', elems=self.objects),
                          Node(id=b'Connections', elems=[Node(id=b'C', props=[b'OO', a, b])
                                                        for a, b in self.links])])
        parser = Node(parse=lambda *args, **kwargs: (root, 7400))
        with patch.dict('sys.modules', {'io_scene_fbx': Node(parse_fbx=parser)}):
            return reader('source.fbx', '10', '20')

    def test_shared_nonbone_parent_requires_exact_unique_source_edges(self):
        from unitypackage_blender_importer.blender.fbx_witness import source_skin_shared_parent
        self.objects.append(Node(id=b'Model', props=[90, b'', b'Null'], elems=[]))
        self.links += [(50, 90), (51, 90)]
        self.assertEqual(self.read(source_skin_shared_parent), ('90', {'50': '90', '51': '90'}))
        original = list(self.links)
        for links in (original[:-1], original + [(50, 90)], original + [(51, 52)]):
            self.links = links
            with self.subTest(links=links), self.assertRaises(ValueError):
                self.read(source_skin_shared_parent)
        self.links = original
        self.objects[-1].props[2] = b'LimbNode'
        with self.assertRaises(ValueError): self.read(source_skin_shared_parent)

    def test_single_root_world_parent_preserves_established_route(self):
        from unitypackage_blender_importer.blender.fbx_witness import source_skin_shared_parent
        reader = lambda *args: source_skin_shared_parent(*args, allow_single=True)
        self.links += [(51, 50)]
        self.assertIsNone(self.read(reader))
        self.links += [(50, 0)]
        self.assertIsNone(self.read(reader))
        self.links += [(51, 50)]
        with self.assertRaises(ValueError): self.read(reader)

    def test_cluster_link_order_uses_exact_bone_receipts_and_keeps_other_rows(self):
        from unitypackage_blender_importer.blender.fbx_witness import ordered_skin_cluster_connections
        def bone(uid, receipt):
            return Node(id=b'Model', props=[uid, b'same-label', b'LimbNode'], elems=[
                Node(id=b'Properties70', elems=[Node(id=b'P', props=[b'_vapb_fbx_bone_realization_id', receipt.encode()])])])
        objects = [bone(901, 'a'), bone(902, 'b')]
        objects += [Node(id=b'Deformer', props=[uid, b'', kind], elems=[])
                    for uid, kind in ((1001, b'Skin'), (1040, b'Cluster'), (1041, b'Cluster'))]
        rows = [Node(id=b'C', props=[b'OO', a, b]) for a,b in
                ((901,1040),(902,1041),(1041,1001),(901,90),(1040,1001))]
        mappings = [dict(source_model_uid='50', edited_bone_realization_id='a'),
                    dict(source_model_uid='51', edited_bone_realization_id='b')]
        original = list(rows)
        ordered = ordered_skin_cluster_connections(objects, rows, mappings, ['50','51'])
        self.assertEqual(ordered, [rows[0],rows[1],rows[4],rows[3],rows[2]])
        self.assertEqual(rows, original)
        self.assertTrue(all(a is b for a,b in zip(ordered[:2],rows[:2])))
        self.assertIs(ordered[3], rows[3])
        self.assertEqual(ordered_skin_cluster_connections(objects, rows, mappings, ['51','50']), rows)
        for changed, order in ((rows, ['50']), (rows, ['50','50','51']),
                               (rows[:-1], ['50','51']), (rows+[rows[2]], ['50','51']),
                               (rows[1:], ['50','51'])):
            with self.subTest(order=order), self.assertRaises(ValueError):
                ordered_skin_cluster_connections(objects, changed, mappings, order)
        objects[0].props[2] = b'Null'
        with self.assertRaises(ValueError):
            ordered_skin_cluster_connections(objects, rows, mappings, ['50','51'])

    def test_membership_comes_from_clusters_including_empty_clusters(self):
        self.assertEqual(self.read(), frozenset({'50', '51'}))
        ordered = lambda *args: source_skin_bone_uids(*args, ordered=True)
        self.assertEqual(self.read(ordered), ('50', '51'))
        self.links[2:4] = reversed(self.links[2:4])
        self.assertEqual(self.read(ordered), ('51', '50'))

    def test_missing_or_ambiguous_connections_rejected(self):
        original = list(self.links)
        for links in (original[:-1], original + [(52, 41)], original + [(30, 20)],
                      original + [(40, 30)], original + [(20, 10)],
                      [(a, b) for a, b in original if b != 30]):
            self.links = links
            with self.subTest(links=links), self.assertRaises(ValueError):
                self.read()

    def test_shared_bone_duplicate_objects_and_unknown_skin_child_rejected(self):
        self.links[-1] = (50, 41)
        with self.assertRaises(ValueError):
            self.read()
        self.setUp()
        self.objects.append(deepcopy(self.objects[0]))
        with self.assertRaises(ValueError):
            self.read()
        self.setUp()
        self.links.append((52, 30))
        with self.assertRaises(ValueError):
            self.read()


if __name__ == '__main__':
    unittest.main()
