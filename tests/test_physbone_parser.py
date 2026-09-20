from pathlib import Path
import tempfile
import unittest

from unitypackage_blender_importer.unity.physbone_parser import extract_physbone_snapshot
from unitypackage_blender_importer.unity.prefab_parser import parse_prefab


FIXTURE = """%YAML 1.1
--- !u!1 &1001
GameObject:
  m_Name: HairRoot
--- !u!4 &2001
Transform:
  m_GameObject: {fileID: 1001}
  m_Father: {fileID: 0}
--- !u!114 &3001
MonoBehaviour:
  m_GameObject: {fileID: 1001}
  m_Script: {fileID: 1661641543, guid: 11111111111111111111111111111111, type: 3}
  rootTransform: {fileID: 0}
  pull: 0.2
  spring: 0.3
  stiffness: 0.4
  gravity: 0.5
  gravityFalloff: 0.6
  immobile: 0.1
  radius: 0.02
  limitType: 1
  maxAngleX: 25
  maxAngleZ: 30
  colliders:
  - {fileID: 4001}
  customFutureField: 42
--- !u!114 &4001
MonoBehaviour:
  m_GameObject: {fileID: 1001}
  m_Script: {fileID: 542108242, guid: 22222222222222222222222222222222, type: 3}
  shapeType: 0
  insideBounds: 0
  radius: 0.1
  height: 0.5
  position: {x: 1, y: 2, z: 3}
  rotation: {x: 0, y: 0, z: 0, w: 1}
"""


class PhysBoneParserTests(unittest.TestCase):
    def test_extracts_semantics_and_preserves_unknown_source_payload(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "fixture.prefab"
            path.write_text(FIXTURE, encoding="utf-8")
            snapshot = extract_physbone_snapshot(parse_prefab(path))
        self.assertEqual(1, len(snapshot.physbones))
        self.assertEqual(1, len(snapshot.colliders))
        bone = snapshot.physbones[0]
        self.assertEqual("1001", bone.owner_game_object_file_id)
        self.assertEqual("0", bone.root_transform_reference_file_id)
        self.assertFalse(bone.root_transform_explicit)
        self.assertEqual(0.3, bone.parameters["spring"])
        self.assertEqual(("4001",), bone.collider_file_ids)
        self.assertIn("customFutureField: 42", bone.raw_payload)
        self.assertEqual("4001", snapshot.colliders[0].component_file_id)
        serialized = snapshot.to_dict()
        self.assertEqual(1, serialized["schema_version"])
        self.assertNotIn("positions", serialized)
        self.assertIn("shapeType: 0", serialized["colliders"][0]["raw_payload"])

    def test_missing_physics_metadata_is_empty_and_safe(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "empty.prefab"
            path.write_text("%YAML 1.1\n--- !u!1 &1\nGameObject:\n  m_Name: Empty\n", encoding="utf-8")
            snapshot = extract_physbone_snapshot(parse_prefab(path))
        self.assertEqual((), snapshot.physbones)
        self.assertEqual((), snapshot.colliders)

    def test_explicit_root_transform_is_distinguished_from_null_owner_root(self):
        explicit_fixture = FIXTURE.replace("&3001", "&3002", 1).replace(
            "rootTransform: {fileID: 0}", "rootTransform: {fileID: 2001}", 1
        )
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "explicit.prefab"
            path.write_text(explicit_fixture, encoding="utf-8")
            snapshot = extract_physbone_snapshot(parse_prefab(path))
        self.assertEqual(1, len(snapshot.physbones))
        self.assertEqual("2001", snapshot.physbones[0].root_transform_file_id)
        self.assertEqual("2001", snapshot.physbones[0].root_transform_reference_file_id)
        self.assertTrue(snapshot.physbones[0].root_transform_explicit)
        self.assertEqual("1001", snapshot.physbones[0].root_game_object_file_id)


if __name__ == "__main__":
    unittest.main()
