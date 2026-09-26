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

    def read(self):
        root = Node(elems=[Node(id=b'Objects', elems=self.objects),
                          Node(id=b'Connections', elems=[Node(id=b'C', props=[b'OO', a, b])
                                                        for a, b in self.links])])
        parser = Node(parse=lambda *args, **kwargs: (root, 7400))
        with patch.dict('sys.modules', {'io_scene_fbx': Node(parse_fbx=parser)}):
            return source_skin_bone_uids('source.fbx', '10', '20')

    def test_membership_comes_from_clusters_including_empty_clusters(self):
        self.assertEqual(self.read(), frozenset({'50', '51'}))

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
