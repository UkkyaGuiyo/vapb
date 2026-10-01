# SPDX-License-Identifier: GPL-3.0-or-later
import unittest

from unitypackage_blender_importer.export.model_skin import model_skin_material_bindings
from unitypackage_blender_importer.tests.blender_model_bounded_skin_compare import material_comparison_labels
from unitypackage_blender_importer.tests.geometry_abcd_metrics import material_label_partitions


class ModelBoundedMaterialCompareTests(unittest.TestCase):
    def setUp(self):
        self.refs = [dict(guid='a' * 32, file_id='2100000'), dict(guid='b' * 32, file_id='-2100001')]
        self.bindings = model_skin_material_bindings(self.refs)
        self.slots = [dict(slot=i, guid=ref['guid']) for i, ref in enumerate(self.refs)]

    def labels(self, refs):
        return material_comparison_labels(self.slots, self.bindings,
            [ref['guid'] for ref in refs], [ref['file_id'] for ref in refs])

    def test_measured_guid_file_id_face_partition_survives_slot_permutation(self):
        source, target = self.labels(list(reversed(self.refs)))
        triangles = [[0, 1, 2], [3, 4, 5]]
        self.assertEqual(material_label_partitions(triangles, [0, 1], source),
                         material_label_partitions(triangles, [1, 0], target))
        self.assertNotEqual(material_label_partitions(triangles, [0, 1], source),
                            material_label_partitions(triangles, [0, 1], target))

    def test_same_guid_wrong_signed_local_id_is_rejected(self):
        wrong = [dict(self.refs[0], file_id='2100002'), self.refs[1]]
        with self.assertRaisesRegex(ValueError, 'TARGET_MATERIAL_REFERENCE_MISMATCH'):
            self.labels(wrong)

    def test_original_display_name_cannot_replace_transport_identity(self):
        self.bindings[0]['transport_id'] = 'Original display name'
        with self.assertRaisesRegex(ValueError, 'MATERIAL_TRANSPORT_LABEL_MISMATCH'):
            self.labels(self.refs)

    def test_current_blender_slot_guid_must_match_declared_binding(self):
        self.slots[0]['guid'] = 'c' * 32
        with self.assertRaisesRegex(ValueError, 'CURRENT_MATERIAL_BINDING_MISMATCH'):
            self.labels(self.refs)


if __name__ == '__main__':
    unittest.main()
