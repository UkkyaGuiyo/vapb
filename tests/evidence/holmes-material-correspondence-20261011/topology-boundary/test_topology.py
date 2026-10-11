"""Focused source-diagnostic and exact-cover controls, no application launch."""
import copy
import unittest

class TopologyControls(unittest.TestCase):
    def test_active_layer_binding(self):
        from types import SimpleNamespace as N
        from read_input import validate_layer_binding
        def node(name, props=(), elems=()): return N(id=name, props=list(props), elems=list(elems))
        uv = node(b'LayerElementUV', [0])
        mat = node(b'LayerElementMaterial', [0])
        def ref(kind, index): return node(b'LayerElement', elems=[node(b'Type', [kind]), node(b'TypedIndex', [index])])
        layer = node(b'Layer', [0], [ref(b'LayerElementUV', 0), ref(b'LayerElementMaterial', 0)])
        geometry = node(b'Geometry', elems=[uv, mat, layer])
        validate_layer_binding(geometry, uv, mat)
        bad = copy.deepcopy(geometry); bad.elems[-1].elems[0].elems[-1].props[0] = 1
        with self.assertRaises(ValueError): validate_layer_binding(bad, uv, mat)
        bad = copy.deepcopy(geometry); bad.elems[-1].elems.pop()
        with self.assertRaises(ValueError): validate_layer_binding(bad, uv, mat)

    def test_source_only_scope_and_predictions(self):
        from diagnose import diagnose
        polygons = [{'polygon': i, 'uid': uid, 'uv': [[0, 0]] * n}
                    for i, (uid, n) in enumerate([(11, 3), (22, 4), (11, 4), (22, 3)])]
        raw = {'polygons': polygons}
        self.assertEqual(diagnose(raw, {'keepQuads': 0})['status'], 'TRIANGULATION_BOUNDARY_UNVERIFIED')
        on = diagnose(raw, {'keepQuads': 1})
        self.assertEqual(on['status'], 'MIXED_TOPOLOGY_REQUIRES_PARTITION_RULE')
        self.assertEqual(on['P_UID'], [{'uid': 11, 'polygons': [0, 2]}, {'uid': 22, 'polygons': [1, 3]}])
        self.assertEqual(len(on['P_UID_TOPOLOGY_unordered']), 4)
        self.assertEqual(diagnose(raw, {})['status'], 'UNKNOWN_SCOPE')
        self.assertEqual(diagnose(raw, {'keepQuads': 'true'})['status'], 'UNKNOWN_SCOPE')
        tri = {'polygons': [polygons[0], polygons[3]]}
        self.assertEqual(diagnose(tri, {'keepQuads': 0})['status'], 'TRIANGLE_ONLY_CANDIDATE')
        bad = copy.deepcopy(raw); bad['polygons'][0]['uv'].append([0, 0]); bad['polygons'][0]['uv'].append([0, 0])
        self.assertEqual(diagnose(bad, {'keepQuads': 1})['status'], 'UNKNOWN_SCOPE')

    def test_cover_controls_and_topology_not_inferred_from_count(self):
        from judge import cover, native_faces, validate_labels
        quad = [[0, 0], [1, 0], [1, 1], [0, 1]]
        triangles = [[quad[0], quad[1], quad[2]], [quad[0], quad[2], quad[3]]]
        self.assertEqual(cover(quad, triangles), 1)
        self.assertEqual(cover(quad, [list(reversed(t)) for t in triangles]), -1)
        self.assertEqual(cover(quad, [[quad[0], quad[1], quad[3]], [quad[1], quad[2], quad[3]]]), 1)
        for bad in [triangles[:1], triangles + [triangles[0]], [triangles[0], triangles[0]]]:
            with self.assertRaises(ValueError): cover(quad, bad)
        snapshot = {'uv': [{'x': x, 'y': y} for x, y in quad * 3],
                    'groups': [{'topology': 'Quads', 'indices': list(range(12)), 'index_count': 12, 'base_vertex': 0}],
                    'apply_base_vertex': True}
        self.assertEqual(len(native_faces(snapshot)), 3)  # 12 indices are three quads.
        bad = copy.deepcopy(snapshot); bad['groups'][0]['topology'] = 'Triangles'
        with self.assertRaises(ValueError): cover(quad, [f['uv'] for f in native_faces(bad)])
        report = [{'polygon': 0, 'group': 0, 'raw_uid': 11}]
        validate_labels(report, copy.deepcopy(report))
        bad = copy.deepcopy(report); bad[0]['group'] = 1
        with self.assertRaises(ValueError): validate_labels(report, bad)
        bad = copy.deepcopy(report); bad[0]['raw_uid'] = 22
        with self.assertRaises(ValueError): validate_labels(report, bad)

if __name__ == '__main__':
    unittest.main()
