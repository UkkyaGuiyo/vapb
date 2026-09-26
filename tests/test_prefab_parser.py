from pathlib import Path
import tempfile
import unittest

from unitypackage_blender_importer.unity.prefab_parser import parse_prefab, ref_file_id
from unitypackage_blender_importer.unity.effective_prefab import EffectivePrefabResolver


class PrefabFileIdTests(unittest.TestCase):
    def test_prefab_local_renderer_identity_is_not_mesh_identity(self):
        prefab_guid = "1" * 32
        mesh_guid = "2" * 32
        text = f"""%YAML 1.1
--- !u!1 &100
GameObject:
  m_Name: LocalRenderer
  m_Component:
  - component: {{fileID: 101}}
--- !u!137 &-303
SkinnedMeshRenderer:
  m_GameObject: {{fileID: 100}}
  m_Mesh: {{fileID: -2984155000744113726, guid: {mesh_guid}, type: 3}}
"""
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "Local.prefab"
            path.write_text(text, encoding="utf-8")
            path.with_name(path.name + ".meta").write_text(f"fileFormatVersion: 2\nguid: {prefab_guid}\n", encoding="utf-8")
            effective = EffectivePrefabResolver().resolve(parse_prefab(path))
        state = effective.renderer(prefab_guid, -303)
        self.assertIsNotNone(state)
        self.assertEqual(prefab_guid, state.renderer_guid)
        self.assertEqual(mesh_guid, state.mesh_guid)
        self.assertEqual(-2984155000744113726, state.mesh_file_id)
        self.assertIsNone(effective.renderer(mesh_guid, -303))

    def test_negative_prefab_local_renderer_file_id_is_effective(self):
        prefab_guid = "3" * 32
        text = f"""%YAML 1.1
--- !u!1 &100
GameObject:
  m_Name: NegativeRenderer
--- !u!137 &-9223372036854775000
SkinnedMeshRenderer:
  m_GameObject: {{fileID: 100}}
  m_Mesh: {{fileID: 4300000, guid: {'4' * 32}, type: 3}}
"""
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "Negative.prefab"
            path.write_text(text, encoding="utf-8")
            path.with_name(path.name + ".meta").write_text(f"fileFormatVersion: 2\nguid: {prefab_guid}\n", encoding="utf-8")
            effective = EffectivePrefabResolver().resolve(parse_prefab(path))
        self.assertIsNotNone(effective.renderer(prefab_guid, -9223372036854775000))

    def test_component_graph_keeps_distinct_renderers_that_share_external_mesh(self):
        prefab_guid = "5" * 32
        mesh_guid = "6" * 32
        text = f"""%YAML 1.1
--- !u!1 &100
GameObject:
  m_Name: A
--- !u!137 &201
SkinnedMeshRenderer:
  m_GameObject: {{fileID: 100}}
  m_Mesh: {{fileID: -2984155000744113726, guid: {mesh_guid}, type: 3}}
--- !u!1 &101
GameObject:
  m_Name: B
--- !u!137 &202
SkinnedMeshRenderer:
  m_GameObject: {{fileID: 101}}
  m_Mesh: {{fileID: -2984155000744113726, guid: {mesh_guid}, type: 3}}
"""
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "SharedMesh.prefab"
            path.write_text(text, encoding="utf-8")
            path.with_name(path.name + ".meta").write_text(f"fileFormatVersion: 2\nguid: {prefab_guid}\n", encoding="utf-8")
            graph = EffectivePrefabResolver().resolve(parse_prefab(path)).component_graph
        self.assertEqual(2, len(graph.renderers))
        self.assertEqual({mesh_guid}, {item.mesh_guid for item in graph.renderers.values()})
        self.assertEqual({201, 202}, {item.file_id for item in graph.renderers.values()})

    def test_direct_renderer_without_mesh_reference_remains_prefab_local(self):
        prefab_guid = "f" * 32
        text = """%YAML 1.1
--- !u!1 &100
GameObject:
  m_Name: Body
--- !u!4 &101
Transform:
  m_GameObject: {fileID: 100}
  m_Father: {fileID: 0}
--- !u!33 &200
MeshFilter:
  m_GameObject: {fileID: 100}
  m_Mesh: {fileID: 4300000, guid: {mesh_guid}, type: 3}
--- !u!137 &300
SkinnedMeshRenderer:
  m_GameObject: {fileID: 100}
  m_Mesh: {fileID: 0}
""".replace("{mesh_guid}", "a" * 32)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "Body.prefab"
            path.write_text(text, encoding="utf-8")
            path.with_name(path.name + ".meta").write_text(
                f"fileFormatVersion: 2\nguid: {prefab_guid}\n", encoding="utf-8"
            )
            effective = EffectivePrefabResolver().resolve(parse_prefab(path))
        state = effective.renderer(prefab_guid, 300)
        self.assertIsNotNone(state)
        self.assertEqual("PREFAB_LOCAL", state.source_kind)
        self.assertEqual("a" * 32, state.mesh_guid)

    def test_non_renderer_variant_modifications_do_not_create_renderer_states(self):
        source_guid = "a" * 32
        text = f"""%YAML 1.1
--- !u!1 &100
GameObject:
  m_Name: Root
--- !u!4 &101
Transform:
  m_GameObject: {{fileID: 100}}
  m_Father: {{fileID: 0}}
--- !u!1001 &500
PrefabInstance:
  m_SourcePrefab: {{fileID: 1001, guid: {source_guid}, type: 3}}
  m_Modification:
    m_Modifications:
    - target: {{fileID: 77, guid: {source_guid}, type: 3}}
      propertyPath: m_LocalPosition.x
      value: 1
    - target: {{fileID: 88, guid: {source_guid}, type: 3}}
      propertyPath: m_AABB.center.x
      value: 2
"""
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "Variant.prefab"
            path.write_text(text, encoding="utf-8")
            effective = EffectivePrefabResolver().resolve(parse_prefab(path))
        self.assertEqual({}, effective.renderers)

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
            "prefab_instance_file_id": "100",
            "material_file_id": "2100000",
        }])

    def test_modification_identity_retains_instance_and_source_scope(self):
        # The same signed renderer localID appears in two instances. Names
        # are display data; they must not leak from one instance to another.
        text = "%YAML 1.1\n"
        for instance_id, name, material_id in ((-901, "Left", -21), (902, "Right", 22)):
            text += f"""--- !u!1001 &{instance_id}
PrefabInstance:
  m_Modification:
    m_Modifications:
    - target: {{fileID: -123, guid: {'a' * 32}, type: 3}}
      propertyPath: m_Name
      value: {name}
    - target: {{fileID: -123, guid: {'a' * 32}, type: 3}}
      propertyPath: m_Materials.Array.data[0]
      value:
      objectReference: {{fileID: {material_id}, guid: {'b' * 32}, type: 2}}
"""
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "Instances.prefab"
            path.write_text(text, encoding="utf-8")
            prefab = parse_prefab(path)
            modifications = prefab.modifications()
            overrides = prefab.modification_materials()
        self.assertEqual([-901, -901, 902, 902], [m.prefab_instance_file_id for m in modifications])
        self.assertEqual(["Left", "Right"], [o["object_name"] for o in overrides])
        self.assertEqual(["-901", "902"], [o["prefab_instance_file_id"] for o in overrides])
        self.assertEqual(["-21", "22"], [o["material_file_id"] for o in overrides])
        self.assertEqual([3] * 4, [m.target_type for m in modifications])
        self.assertEqual([2, 2], [m.object_reference["type"] for m in modifications if m.object_reference])

    def test_effective_prefab_preserves_target_identity_and_last_override(self):
        text = """%YAML 1.1
--- !u!1001 &100
PrefabInstance:
  m_Modification:
    m_Modifications:
    - target: {fileID: 77, guid: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa,
        type: 3}
      propertyPath: m_Materials.Array.data[0]
      value:
      objectReference: {fileID: 2100000, guid: bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb,
        type: 2}
    - target: {fileID: 77, guid: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa,
        type: 3}
      propertyPath: m_Materials.Array.data[0]
      value:
      objectReference: {fileID: 2100000, guid: cccccccccccccccccccccccccccccccc,
        type: 2}
"""
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "Variant.prefab"
            path.write_text(text, encoding="utf-8")
            effective = EffectivePrefabResolver().resolve(parse_prefab(path))
        state = effective.renderer("a" * 32, 77)
        self.assertIsNotNone(state)
        self.assertEqual("c" * 32, state.material_slots[0]["guid"])
        self.assertEqual({"a" * 32}, effective.referenced_source_guids)

    def test_effective_prefab_inheritance_precedence_and_source_scope(self):
        def prefab_text(source_guid=None, source_slots=(), overrides=()):
            source = f"  m_SourcePrefab: {{fileID: 1001, guid: {source_guid}, type: 3}}\n" if source_guid else ""
            renderer = "" if source_slots == () else f"""--- !u!33 &200
MeshFilter:
  m_GameObject: {{fileID: 100}}
  m_Mesh: {{fileID: 4300000, guid: {'e' * 32}, type: 3}}
--- !u!23 &300
MeshRenderer:
  m_GameObject: {{fileID: 100}}
  m_Materials:
""" + "".join(f"  - {{fileID: 2100000, guid: {guid}, type: 2}}\n" for guid in source_slots)
            mods = "".join(
                f"""    - target: {{fileID: 300, guid: {'e' * 32}, type: 3}}
      propertyPath: m_Materials.Array.data[{slot}]
      value:
      objectReference: {{fileID: 2100000, guid: {guid}, type: 2}}
                """ for slot, guid in overrides
            )
            mods_text = mods or "    []\n"
            return f"""%YAML 1.1
--- !u!1 &100
GameObject:
  m_Name: Root
--- !u!4 &101
Transform:
  m_GameObject: {{fileID: 100}}
  m_Father: {{fileID: 0}}
--- !u!1001 &500
PrefabInstance:
{source}  m_Modification:
    m_Modifications:
{mods_text}""" + renderer

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            base_guid, v1_guid, v2_guid, v3_guid = [value * 32 for value in "1234"]
            a, b, x, y, c, d, q = [value * 32 for value in "abcdefq"]
            paths = {
                base_guid: root / "Base.prefab", v1_guid: root / "V1.prefab",
                v2_guid: root / "V2.prefab", v3_guid: root / "V3.prefab",
            }
            paths[base_guid].write_text(prefab_text(source_slots=(a, x, q)), encoding="utf-8")
            paths[v1_guid].write_text(prefab_text(base_guid, overrides=((1, y),)), encoding="utf-8")
            paths[v2_guid].write_text(prefab_text(v1_guid, overrides=((0, b),)), encoding="utf-8")
            paths[v3_guid].write_text(prefab_text(v2_guid, overrides=((0, c),)), encoding="utf-8")
            parsed = {guid: parse_prefab(path) for guid, path in paths.items()}
            resolved = EffectivePrefabResolver(lambda guid: parsed.get(guid)).resolve(parsed[v3_guid])
            state = resolved.renderer("e" * 32, 300)
            self.assertEqual({0: {"fileID": 2100000, "guid": c, "type": 2}, 1: {"fileID": 2100000, "guid": y, "type": 2}, 2: {"fileID": 2100000, "guid": q, "type": 2}}, state.material_slots)
            self.assertNotEqual(
                EffectivePrefabResolver().resolve(parsed[base_guid]).renderer("e" * 32, 300),
                EffectivePrefabResolver().resolve(parsed[v3_guid]).renderer("e" * 32, 300),
            )


if __name__ == "__main__":
    unittest.main()
