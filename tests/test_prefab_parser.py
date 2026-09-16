from pathlib import Path
import tempfile
import unittest

from unitypackage_blender_importer.unity.prefab_parser import parse_prefab, ref_file_id


class PrefabFileIdTests(unittest.TestCase):
    def test_wrapped_transform_and_renderer_refs_preserve_geometry_dependencies(self):
        text = """%YAML 1.1
--- !u!1 &100
GameObject:
  m_Name: Mesh
--- !u!4 &101
Transform:
  m_GameObject: {fileID: 100}
  m_Father: {fileID: 0}
  m_LocalPosition: {x: 0, y: 1,
    z: 2}
  m_LocalRotation: {x: -3.65e-12, y: 2.45e-9, z: -2.25e-7,
    w: 1}
  m_LocalScale: {x: 1, y: 1, z: 1}
--- !u!137 &102
SkinnedMeshRenderer:
  m_GameObject: {fileID: 100}
  m_Mesh: {fileID: 4300000, guid: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa,
    type: 3}
  m_Materials:
  - {fileID: 2100000, guid: bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb,
      type: 2}
"""
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "Wrapped.prefab"
            path.write_text(text, encoding="utf-8")
            prefab = parse_prefab(path)
        self.assertEqual(prefab.transforms[101].rotation["w"], 1.0)
        self.assertEqual(prefab.transforms[101].position, {"x": 0.0, "y": 1.0, "z": 2.0})
        self.assertEqual(prefab.referenced_fbx_guids(), {"a" * 32, "b" * 32})

    def test_large_file_id_is_preserved_as_python_integer_for_internal_links(self):
        value = 9223372036854775807
        self.assertEqual(value, ref_file_id({"fileID": str(value)}))

    def test_negative_file_id_is_preserved_for_internal_links(self):
        value = -9223372036854775808
        self.assertEqual(value, ref_file_id({"fileID": value}))

    def test_invalid_file_id_is_not_coerced(self):
        self.assertIsNone(ref_file_id({"fileID": "not-a-number"}))

    def test_wrapped_prefab_instance_material_override_is_parsed(self):
        text = """%YAML 1.1
--- !u!1001 &100
PrefabInstance:
  m_Modification:
    m_Modifications:
    - target: {fileID: -123, guid: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa,
        type: 3}
      propertyPath: m_Name
      value: Coat
    - target: {fileID: -123, guid: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa,
        type: 3}
      propertyPath: m_Materials.Array.data[0]
      value:
      objectReference: {fileID: 2100000, guid: bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb,
        type: 2}
"""
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "Avatar.prefab"
            path.write_text(text, encoding="utf-8")
            overrides = parse_prefab(path).modification_materials()
        self.assertEqual(overrides, [{
            "target_file_id": "-123",
            "target_source_guid": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "slot_index": 0,
            "material_guid": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
            "object_name": "Coat",
        }])


if __name__ == "__main__":
    unittest.main()
