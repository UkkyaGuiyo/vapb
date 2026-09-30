# SPDX-License-Identifier: GPL-3.0-or-later
import unittest
from unitypackage_blender_importer.tests.geometry_abcd_metrics import material_label_partitions

class MaterialTriangleTransportTests(unittest.TestCase):
    def test_export_label_survives_submesh_reorder(self):
        triangles=[[0,1,2],[3,4,5],[6,7,8]]
        labels=['VAPB-EXP-MAT-0','VAPB-EXP-MAT-1','VAPB-EXP-MAT-2']
        a=material_label_partitions(triangles,[0,2,1],labels)
        b=material_label_partitions(triangles,[0,1,2],[labels[0],labels[2],labels[1]])
        self.assertEqual(a,b)
    def test_wrong_binding_is_red(self):
        triangles=[[0,1,2],[3,4,5]]
        labels=['VAPB-EXP-MAT-0','VAPB-EXP-MAT-1']
        self.assertNotEqual(material_label_partitions(triangles,[0,1],labels),material_label_partitions(triangles,[1,0],labels))
    def test_missing_or_original_name_is_unproven(self):
        for label in (None,'Original display name'):
            with self.assertRaises(ValueError):material_label_partitions([[0,1,2]],[0],[label])
