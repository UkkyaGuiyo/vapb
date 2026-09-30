"""Persisted native channel receipts must survive labels and reject corruption."""
import json
import unittest
from types import SimpleNamespace

from unitypackage_blender_importer.blender import fbx_receipt


class ShapeReceiptTests(unittest.TestCase):
    def test_serialized_weight_tail_is_zero_without_source_cache_fallback(self):
        from unitypackage_blender_importer.blender import model_witness_bridge
        normalize = getattr(model_witness_bridge, 'renderer_shape_weights', None)
        self.assertTrue(callable(normalize), 'SERIALIZED_WEIGHT_TAIL_UNPROVEN')
        self.assertEqual(normalize([25], 3), [0.25, 0.0, 0.0])
        self.assertEqual(normalize([], 3), [0.0, 0.0, 0.0])
        for bad in (None, [25, 0, 0, 0], [float('nan')], [True], [1001]):
            with self.assertRaises(ValueError):
                normalize(bad, 3)

    def test_channel_receipt_validator_exists_before_weights_can_be_applied(self):
        self.assertTrue(callable(getattr(fbx_receipt, 'validate_shape_receipts', None)),
                        'CHANNEL_IDENTITY_UNPROVEN: native channel receipt validator missing')

    def fixture(self):
        def block(label, points):
            return SimpleNamespace(name=label, data=[SimpleNamespace(co=p) for p in points])
        basis = block('Basis', [(0, 0, 0), (1, 0, 0)])
        a, b = block('A', [(0, .25, 0), (1, 0, 0)]), block('B', [(0, 0, 0), (1, 0, .5)])
        for key in (basis, a, b):
            key.relative_key = basis
        class Keys(dict):
            pass
        keys = Keys()
        keys.key_blocks = [basis, a, b]
        mesh = SimpleNamespace(shape_keys=keys)
        fbx_receipt.persist_shape_receipts(mesh, 'a'*64, 20, [(30, 40, a), (31, 41, b)])
        return mesh

    def test_direct_receipts_survive_rename_and_validate_source_revision(self):
        mesh = self.fixture()
        mesh.shape_keys.key_blocks[1].name = 'Changed label'
        self.assertEqual(set(fbx_receipt.validate_shape_receipts(mesh, 'a'*64, 20)), {30, 31})
        with self.assertRaises(ValueError):
            fbx_receipt.validate_shape_receipts(mesh, 'b'*64, 20)
        with self.assertRaises(ValueError):
            fbx_receipt.validate_shape_receipts(mesh, 'a'*64, 21)

    def test_wrong_duplicate_swapped_receipts_and_missing_or_decoy_key_reject(self):
        for kind in ('wrong', 'duplicate', 'swap', 'missing', 'decoy', 'relative'):
            with self.subTest(kind=kind):
                mesh = self.fixture()
                keys = mesh.shape_keys
                records = json.loads(keys['_vapb_fbx_shape_receipts'])
                if kind == 'wrong': records['channels'][0]['channel_uid'] = 99
                elif kind == 'duplicate': records['channels'][1]['channel_uid'] = 30
                elif kind == 'swap':
                    records['channels'][0]['key_index'], records['channels'][1]['key_index'] = 2, 1
                elif kind == 'missing': keys.key_blocks.pop()
                elif kind == 'decoy': keys.key_blocks.append(keys.key_blocks[1])
                else: keys.key_blocks[1].relative_key = keys.key_blocks[2]
                keys['_vapb_fbx_shape_receipts'] = json.dumps(records)
                with self.assertRaises(ValueError):
                    fbx_receipt.validate_shape_receipts(mesh, 'a'*64, 20)


if __name__ == '__main__':
    unittest.main()
