import unittest

from unitypackage_blender_importer.unity.prefab_parser import ref_file_id


class PrefabFileIdTests(unittest.TestCase):
    def test_large_file_id_is_preserved_as_python_integer_for_internal_links(self):
        value = 9223372036854775807
        self.assertEqual(value, ref_file_id({"fileID": str(value)}))

    def test_negative_file_id_is_preserved_for_internal_links(self):
        value = -9223372036854775808
        self.assertEqual(value, ref_file_id({"fileID": value}))

    def test_invalid_file_id_is_not_coerced(self):
        self.assertIsNone(ref_file_id({"fileID": "not-a-number"}))


if __name__ == "__main__":
    unittest.main()
