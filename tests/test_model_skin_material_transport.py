# SPDX-License-Identifier: GPL-3.0-or-later
import unittest

from ..export.model_skin import model_skin_material_bindings


class ModelSkinMaterialTransportTests(unittest.TestCase):
    def test_exact_source_ids_make_deterministic_transport_labels(self):
        refs = [{'guid': 'A' * 32, 'file_id': '-2100000'},
                {'guid': 'b' * 32, 'file_id': '2100000'}]
        first = model_skin_material_bindings(refs)
        self.assertEqual(first, model_skin_material_bindings(refs))
        self.assertEqual(first[0]['guid'], 'a' * 32)
        self.assertEqual(first[0]['file_id'], '-2100000')
        self.assertRegex(first[0]['transport_id'], r'^VAPB-MAT-[0-9a-f]{32}$')
        self.assertNotEqual(first[0]['transport_id'], first[1]['transport_id'])
        self.assertEqual(model_skin_material_bindings(list(reversed(refs))), list(reversed(first)))

    def test_repeated_source_identity_is_one_material_entity(self):
        ref = {'guid': 'a' * 32, 'file_id': '2100000'}
        result = model_skin_material_bindings([ref, ref])
        self.assertEqual(result[0], result[1])

    def test_unassigned_and_invalid_material_identity_fail_closed(self):
        for ref in (None, {'guid': 'bad', 'file_id': '2100000'},
                    {'guid': 'a' * 32, 'file_id': '0'},
                    {'guid': 'a' * 32, 'file_id': '1.2'},
                    {'guid': 'a' * 32, 'file_id': str(1 << 63)}):
            with self.subTest(ref=ref), self.assertRaises(ValueError):
                model_skin_material_bindings([ref])
