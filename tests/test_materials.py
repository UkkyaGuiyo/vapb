from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from unitypackage_blender_importer.unity.asset_database import AssetDatabase, AssetEntry
from unitypackage_blender_importer.unity.material_mapping import (
    external_object_guid_for_name,
    find_material_entry_by_name,
    parse_external_objects,
    parse_external_object_rows,
    resolve_material_entry,
)
from unitypackage_blender_importer.unity.material_parser import parse_material
from unitypackage_blender_importer.unity.profiles.base import normalize_material


def material_text(name: str, shader: str, properties: str) -> str:
    return f"""%YAML 1.1
--- !u!21 &2100000
Material:
  m_Name: {name}
  m_Shader: {shader}
  m_CustomRenderQueue: -1
  m_ValidKeywords: []
  m_InvalidKeywords: []
  m_SavedProperties:
    serializedVersion: 3
    m_TexEnvs:
{properties}
    m_Ints: []
    m_Floats: []
    m_Colors: []
"""


class MaterialParserTests(unittest.TestCase):
    def test_material_local_id_is_signed_and_never_assumed(self):
        text = material_text("Synthetic", "{fileID: 0}", "")
        for header, expected in (("--- !u!21 &-9223372036854775808", -9223372036854775808),
                                 ("", None),
                                 ("--- !u!21 &1\n--- !u!21 &2", None)):
            with self.subTest(header=header):
                path = self.write_material("Identity.mat", "a" * 32, text.replace("--- !u!21 &2100000", header))
                self.assertEqual(expected, parse_material(path, self.db()).file_id)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="unity_material_test_")
        self.root = Path(self.temp.name)
        self.material_dir = self.root / "Assets" / "Materials"
        self.material_dir.mkdir(parents=True)
        self.entries: list[AssetEntry] = []

    def tearDown(self):
        self.temp.cleanup()

    def write_material(self, filename: str, guid: str, text: str) -> Path:
        path = self.material_dir / filename
        path.write_text(text, encoding="utf-8")
        self.entries.append(AssetEntry(guid, path.relative_to(self.root).as_posix(), path))
        return path

    def db(self) -> AssetDatabase:
        return AssetDatabase(self.root, self.entries)

    def test_liltoon_properties_and_texture_transform(self):
        path = self.write_material(
            "Lil.mat",
            "1" * 32,
            material_text(
                "Lil",
                "{fileID: 1, guid: unknown, type: 3}",
                """    - _MainTex:
        m_Texture: {fileID: 2800000, guid: 2, type: 3}
        m_Scale: {x: 2, y: 3}
        m_Offset: {x: 0.1, y: 0.2}
    - _BumpMap:
        m_Texture: {fileID: 2800000, guid: 3, type: 3}
        m_Scale: {x: 1, y: 1}
        m_Offset: {x: 0, y: 0}
    m_Floats:
    - _lilToonVersion: 1
    - _UseBumpMap: 1
    - _UseEmission: 1
    - _AlphaClip: 1
    - _Cutoff: 0.4
    m_Colors:
    - _Color: {r: 0.8, g: 0.7, b: 0.6, a: 1}
    - _EmissionColor: {r: 1, g: 0.2, b: 0.1, a: 1}
""",
            ),
        )
        normalized = normalize_material(parse_material(path, self.db()))
        data = parse_material(path, self.db())
        self.assertEqual(data.guid, "1" * 32)
        self.assertEqual(data.unity_path, "Assets/Materials/Lil.mat")
        self.assertEqual(data.textures["_MainTex"].guid, "2")
        self.assertEqual(data.textures["_MainTex"].scale, (2.0, 3.0))
        self.assertEqual(normalized.family, "liltoon")
        self.assertEqual(normalized.alpha_mode, "cutout")
        self.assertIsNotNone(normalized.normal_tex)
        self.assertIn("shadow", normalized.extras)

    def test_known_shader_profiles(self):
        cases = [
            (
                "Standard.mat",
                "a" * 32,
                "{fileID: 46, guid: 0000000000000000f000000000000000, type: 0}",
                """    - _MainTex:
        m_Texture: {fileID: 1, guid: tex, type: 3}
    m_Floats:
    - _Metallic: 0.2
    - _Glossiness: 0.8
""",
                "standard",
            ),
            (
                "MToon.mat",
                "b" * 32,
                "{fileID: 1, guid: unknown, type: 3}",
                """    - _ShadeTexture:
        m_Texture: {fileID: 1, guid: shade, type: 3}
    m_Colors:
    - _ShadeColor: {r: 0.5, g: 0.5, b: 0.5, a: 1}
    m_Ints:
    - _MToonVersion: 1
    - _BlendMode: 0
    - _AlphaMode: 0
""",
                "mtoon",
            ),
            (
                "Poi.mat",
                "c" * 32,
                "{fileID: 1, guid: unknown, type: 3}",
                """    m_Floats:
    - _PoiVersion: 8
    - _LightingMode: 1
""",
                "poiyomi",
            ),
            (
                "Mobile.mat",
                "d" * 32,
                "{fileID: 1, guid: unknown, type: 3}",
                """    - _Ramp:
        m_Texture: {fileID: 1, guid: ramp, type: 3}
    m_Floats:
    - _ShadowBoost: 0.2
    - _MinBrightness: 0.1
    - _MetallicStrength: 0.3
""",
                "vrchat_mobile",
            ),
        ]
        for filename, guid, shader, properties, family in cases:
            path = self.write_material(filename, guid, material_text(filename[:-4], shader, properties))
            normalized = normalize_material(parse_material(path, self.db()))
            self.assertEqual(normalized.family, family, filename)

    def test_unknown_shader_preserves_common_slots(self):
        path = self.write_material(
            "Unknown.mat",
            "e" * 32,
            material_text(
                "Unknown",
                "{fileID: 1, guid: deadbeef, type: 3}",
                """    - _MainTex:
        m_Texture: {fileID: 1, guid: base, type: 3}
    - _BumpMap:
        m_Texture: {fileID: 1, guid: normal, type: 3}
    - _EmissionMap:
        m_Texture: {fileID: 1, guid: emit, type: 3}
    m_Colors:
    - _Color: {r: 0.1, g: 0.2, b: 0.3, a: 1}
    - _EmissionColor: {r: 1, g: 1, b: 1, a: 1}
""",
            ),
        )
        normalized = normalize_material(parse_material(path, self.db()))
        self.assertEqual(normalized.family, "unknown")
        self.assertEqual(normalized.base_color_tex.guid, "base")
        self.assertEqual(normalized.normal_tex.guid, "normal")
        self.assertEqual(normalized.emission_tex.guid, "emit")

    def test_duplicate_material_names_keep_distinct_guids(self):
        first = self.write_material("A.mat", "f" * 32, material_text("Same", "{fileID: 46}", ""))
        second = self.write_material("B.mat", "0" * 32, material_text("Same", "{fileID: 46}", ""))
        first_data = parse_material(first, self.db())
        second_data = parse_material(second, self.db())
        self.assertEqual(first_data.name, second_data.name)
        self.assertNotEqual(first_data.guid, second_data.guid)
        self.assertNotEqual(first_data.unity_path, second_data.unity_path)

    def test_external_object_mapping_has_priority(self):
        self.write_material("Mapped.mat", "1" * 32, material_text("Mapped", "{fileID: 46}", ""))
        mapped = """externalObjects:
  - first:
      type: 23
      assembly: UnityEngine.CoreModule
      name: Body
    second:
      fileID: 2100000
      guid: 11111111111111111111111111111111
      type: 2
"""
        self.write_material("Fallback.mat", "2" * 32, material_text("Body", "{fileID: 46}", ""))
        db = self.db()
        self.assertEqual(parse_external_objects(mapped)["Body"], "1" * 32)
        # The external GUID is deliberately different from the fallback Body.mat.
        self.assertEqual(resolve_material_entry(mapped, "Body", db).guid, "1" * 32)

    def test_external_object_mapping_reads_real_model_importer_form(self):
        expected_guid = "3" * 32
        self.write_material("BodyMapped.mat", expected_guid, material_text("BodyMapped", "{fileID: 46}", ""))
        meta = """externalObjects:
  - first:
      type: UnityEngine:Material
      assembly: UnityEngine.CoreModule
      name: BodyMaterial
    second: {fileID: 2100000, guid: 33333333333333333333333333333333, type: 2}
"""
        db = self.db()
        self.assertEqual(parse_external_objects(meta), {"BodyMaterial": expected_guid})
        self.assertEqual(resolve_material_entry(meta, "BodyMaterial", db).guid, expected_guid)

    def test_external_object_rows_preserve_order_and_parse_block_and_inline_forms(self):
        meta = '''fileFormatVersion: 2
guid: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
externalObjects:
  - first:
      type: UnityEngine:Material
      assembly: UnityEngine.CoreModule
      name: "Body, Main"
    second: {fileID: 2100000, guid: 33333333333333333333333333333333, type: 2}
  - first: {type: 23, assembly: UnityEngine.CoreModule, name: Face}
    second:
      fileID: -9223372036854775808
      guid: 44444444444444444444444444444444
      type: 2
userData:
  first: {name: Outside, second: {fileID: 12, guid: 55555555555555555555555555555555}}
'''
        rows = parse_external_object_rows(meta)
        self.assertEqual([0, 1], [row.row_index for row in rows])
        self.assertEqual(["Body, Main", "Face"], [row.canonical_name for row in rows])
        self.assertEqual("3" * 32, rows[0].canonical_guid)
        self.assertEqual(-9223372036854775808, rows[1].canonical_file_id)
        self.assertTrue(all(row.row_status == "valid" for row in rows))
        self.assertEqual({}, parse_external_objects("guid: " + "6" * 32 + "\n"))

    def test_external_object_rows_keep_duplicates_and_mark_name_ambiguity(self):
        row = '''  - first:
      type: 23
      name: Shared
    second: {fileID: 2100000, guid: 77777777777777777777777777777777, type: 2}'''
        meta = "externalObjects:\n" + row + "\n" + row + "\n"
        first = parse_external_object_rows(meta)
        second = parse_external_object_rows(meta)
        self.assertEqual(2, len(first))
        self.assertEqual([0, 1], [r.row_index for r in first])
        self.assertNotEqual(first[0].row_identity, first[1].row_identity)
        self.assertEqual([r.row_identity for r in first], [r.row_identity for r in second])
        self.assertTrue(all(r.ambiguous for r in first))

    def test_external_object_rows_retain_shared_targets_and_reject_duplicate_keys(self):
        target = "7" * 32
        meta = f'''externalObjects:
  - first: {{type: 23, name: Left}}
    second: {{fileID: 2100000, guid: {target}, type: 2}}
  - first: {{type: 23, name: Right}}
    second: {{fileID: 2100000, guid: {target}, type: 2}}
  - first: {{type: 23, type: 23, name: RepeatedKey}}
    second: {{fileID: 2100000, guid: 88888888888888888888888888888888, type: 2}}
'''
        rows = parse_external_object_rows(meta)
        self.assertEqual(3, len(rows))
        self.assertEqual([target, target], [r.canonical_guid for r in rows[:2]])
        self.assertEqual("valid", rows[0].row_status)
        self.assertEqual("valid", rows[1].row_status)
        self.assertEqual("malformed_mapping", rows[2].validation_status)
        self.assertIsNone(rows[2].canonical_guid)

    def test_external_object_rows_do_not_parse_identity_from_quoted_or_nested_text(self):
        guid = "a" * 32
        meta = f'''externalObjects:
  - first: {{type: 23, name: QuotedFake}}
    second: {{note: "x, fileID: 2100000, guid: {guid}, type: 2, x"}}
  - first:
      type: 23
      name: NestedFake
      details:
        type: 23
        name: Forged
    second:
      note:
        fileID: 2100000
        guid: {guid}
        type: 2
  - first: {{type: 23, name: DuplicateSecond}}
    second: {{fileID: 2100000}}
    second: {{guid: {guid}, type: 2}}
'''
        rows = parse_external_object_rows(meta)
        self.assertEqual(3, len(rows))
        self.assertTrue(all(row.row_status == "malformed" for row in rows))
        self.assertTrue(all(row.canonical_guid is None for row in rows))

    def test_external_object_rows_reject_duplicate_first_mapping_after_header(self):
        meta = '''externalObjects:
  - first: {type: 28, name: Original}
    first: {type: 23, name: Body}
    second: {fileID: 2100000, guid: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa, type: 2}
'''
        rows = parse_external_object_rows(meta)
        self.assertEqual(1, len(rows))
        self.assertEqual("malformed", rows[0].row_status)
        self.assertEqual("malformed_mapping", rows[0].validation_status)
        self.assertIsNone(rows[0].canonical_guid)

    def test_malformed_explicit_null_identity_is_not_accepted(self):
        meta = '''externalObjects:
  - first: {type: 23, name: JunkFileId}
    second: {fileID: 0junk, guid: 00000000000000000000000000000000, type: 0}
  - first: {type: 23, name: QuotedType}
    second: {fileID: 0, guid: 00000000000000000000000000000000, type: "0"}
'''
        rows = parse_external_object_rows(meta)
        self.assertTrue(all(row.row_status == "malformed" for row in rows))
        self.assertTrue(all(row.canonical_file_id is None for row in rows))

    def test_malformed_explicit_external_mapping_blocks_name_fallback(self):
        expected = "6" * 32
        self.write_material("Body.mat", expected, material_text("Body", "{fileID: 46}", ""))
        malformed = '''externalObjects:
  - first: {type: 23, name: Body}
    second: {fileID: 2100000.5, guid: 77777777777777777777777777777777, type: 2}
'''
        self.assertEqual({}, parse_external_objects(malformed))
        self.assertIsNone(resolve_material_entry(malformed, "Body", self.db()))

    def test_external_object_rows_separate_null_wrong_type_and_malformed_ids(self):
        meta = '''externalObjects:
  - first: {type: 23, name: NullSlot}
    second: {fileID: 0, guid: 00000000000000000000000000000000, type: 0}
  - first: {type: 28, name: WrongKind}
    second: {fileID: 10, guid: 88888888888888888888888888888888, type: 2}
  - first: {type: 23, name: Fractional}
    second: {fileID: 10.5, guid: 99999999999999999999999999999999, type: 2}
  - first: {type: 23, name: Boolean}
    second: {fileID: true, guid: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa, type: 2}
  - first: {type: 23, name: Quoted}
    second: {fileID: "10", guid: bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb, type: 2}
  - first: {type: 23, name: Junk}
    second: {fileID: 10tail, guid: cccccccccccccccccccccccccccccccc, type: 2}
  - first: {type: 23, name: BadGuid}
    second: {fileID: 10, guid: deadbeef, type: 2}
'''
        rows = parse_external_object_rows(meta)
        self.assertEqual("explicit_null", rows[0].row_status)
        self.assertEqual(0, rows[0].canonical_file_id)
        self.assertEqual("wrong_first_type", rows[1].validation_status)
        for row in rows[1:]:
            if row.canonical_name != "NullSlot":
                self.assertNotEqual("valid", row.row_status, row.canonical_name)
        self.assertEqual("10.5", rows[2].raw_second_file_id)
        self.assertIsNone(rows[2].canonical_file_id)

    def test_external_object_rows_enforce_signed_int64_limits(self):
        values = ["9223372036854775807", "9223372036854775808", "-9223372036854775808", "-9223372036854775809"]
        items = []
        for index, value in enumerate(values):
            items.append(f'''  - first: {{type: 23, name: N{index}}}
    second: {{fileID: {value}, guid: {index:032x}, type: 2}}''')
        rows = parse_external_object_rows("externalObjects:\n" + "\n".join(items) + "\n")
        self.assertEqual(9223372036854775807, rows[0].canonical_file_id)
        self.assertEqual("valid", rows[0].row_status)
        self.assertEqual("malformed", rows[1].row_status)
        self.assertEqual(-9223372036854775808, rows[2].canonical_file_id)
        self.assertEqual("valid", rows[2].row_status)
        self.assertEqual("malformed", rows[3].row_status)

    def test_external_mapping_presence_is_distinct_from_provider_resolution(self):
        meta = """externalObjects:
  - first:
      type: 23
      assembly: UnityEngine.CoreModule
      name: Body
    second: {fileID: 2100000, guid: 77777777777777777777777777777777, type: 2}
"""
        mapping = parse_external_objects(meta)
        self.assertEqual(
            (True, "7" * 32), external_object_guid_for_name(mapping, "Body.001")
        )
        self.assertEqual((False, None), external_object_guid_for_name(mapping, "Other"))

    def test_missing_explicit_external_guid_does_not_fallback_by_name(self):
        self.write_material("Body.mat", "6" * 32, material_text("Body", "{fileID: 46}", ""))
        meta = """externalObjects:
  - first:
      type: 23
      assembly: UnityEngine.CoreModule
      name: Body
    second: {fileID: 2100000, guid: 77777777777777777777777777777777, type: 2}
"""
        self.assertIsNone(resolve_material_entry(meta, "Body", self.db()))

    def test_unity_same_indent_external_objects_list_is_parsed_before_next_key(self):
        meta = '''ModelImporter:
  serializedVersion: 23
  externalObjects:
  - first:
      type: UnityEngine:Material
      assembly: UnityEngine.CoreModule
      name: Body
    second: {fileID: 2100000, guid: 77777777777777777777777777777777, type: 2}
  materials:
    importMaterials: 1
'''
        rows = parse_external_object_rows(meta)
        self.assertEqual(1, len(rows))
        self.assertEqual("Body", rows[0].canonical_name)
        self.assertEqual("77777777777777777777777777777777", rows[0].canonical_guid)
        self.assertEqual("valid", rows[0].row_status)

    def test_unity_same_indent_explicit_mapping_does_not_enable_name_fallback(self):
        self.write_material("Body.mat", "6" * 32, material_text("Body", "{fileID: 46}", ""))
        meta = '''ModelImporter:
  externalObjects: # Explicit mapping; do not allow name fallback.
  - first:
      type: UnityEngine:Material
      assembly: UnityEngine.CoreModule
      name: Body
    second: {fileID: 2100000, guid: 77777777777777777777777777777777, type: 2}
  materials:
    importMaterials: 1
'''
        self.assertIsNone(resolve_material_entry(meta, "Body", self.db()))

    def test_external_objects_row_markers_inside_block_scalar_are_not_parsed(self):
        guid = "7" * 32
        meta = f'''ModelImporter:
  externalObjects:
  - first:
      type: UnityEngine:Material
      name: |
        - first: {{type: 23, name: Body}}
          second: {{fileID: 2100000, guid: {guid}, type: 2}}
    second: {{fileID: 0, guid: 00000000000000000000000000000000, type: 0}}
  materials:
    importMaterials: 1
'''
        rows = parse_external_object_rows(meta)
        self.assertEqual(1, len(rows))
        self.assertFalse(any(row.canonical_name == "Body" and row.canonical_guid == guid for row in rows))

    def test_external_objects_header_inside_user_data_scalar_is_not_selected(self):
        guid = "7" * 32
        meta = f'''ModelImporter:
  serializedVersion: 23
  userData: |
    externalObjects:
    - first:
        type: UnityEngine:Material
        assembly: UnityEngine.CoreModule
        name: Body
      second: {{fileID: 2100000, guid: {guid}, type: 2}}
  externalObjects: {{}}
  materials:
    importMaterials: 1
'''
        self.assertEqual([], parse_external_object_rows(meta))

    def test_external_objects_block_scalar_is_not_parsed_as_rows(self):
        guid = "7" * 32
        meta = f'''ModelImporter:
  externalObjects: |
    - first: {{type: 23, name: Body}}
      second: {{fileID: 2100000, guid: {guid}, type: 2}}
  materials:
    importMaterials: 1
'''
        self.assertEqual([], parse_external_object_rows(meta))

    def test_explicit_indent_block_scalar_content_is_not_scanned_as_header(self):
        guid = "7" * 32
        for indicator in ("|2", "|2-", "|-2", ">2+", ">+2", "|-", "|+", ">-", ">+"):
            with self.subTest(indicator=indicator):
                meta = f'''ModelImporter:
  userData: {indicator}
    externalObjects:
    - first: {{type: 23, name: Body}}
      second: {{fileID: 2100000, guid: {guid}, type: 2}}
  externalObjects: {{}}
'''
                self.assertEqual([], parse_external_object_rows(meta))

    def test_unsupported_sequence_item_does_not_hide_later_explicit_mapping(self):
        self.write_material("Body.mat", "6" * 32, material_text("Body", "{fileID: 46}", ""))
        guid = "7" * 32
        meta = f'''ModelImporter:
  externalObjects:
  - unsupported: {{}}
  - first: {{type: 23, name: Body}}
    second: {{fileID: 2100000, guid: {guid}, type: 2}}
  materials:
    importMaterials: 1
'''
        rows = parse_external_object_rows(meta)
        self.assertEqual(["Body"], [row.canonical_name for row in rows])
        self.assertIsNone(resolve_material_entry(meta, "Body", self.db()))

    def test_explicit_non_material_guid_does_not_fallback_by_name(self):
        self.write_material("Body.mat", "6" * 32, material_text("Body", "{fileID: 46}", ""))
        texture_path = self.material_dir / "Body.png"
        texture_path.write_bytes(b"synthetic texture")
        self.entries.append(AssetEntry("8" * 32, "Assets/Materials/Body.png", texture_path))
        meta = """externalObjects:
  - first:
      type: 23
      assembly: UnityEngine.CoreModule
      name: Body
    second: {fileID: 2800000, guid: 88888888888888888888888888888888, type: 3}
"""
        self.assertIsNone(resolve_material_entry(meta, "Body", self.db()))

    def test_name_fallback_remains_available_without_external_mapping(self):
        self.write_material("Body.mat", "6" * 32, material_text("Body", "{fileID: 46}", ""))
        resolved = resolve_material_entry("externalObjects: []\n", "Body", self.db())
        self.assertIsNotNone(resolved)
        self.assertEqual("6" * 32, resolved.guid)

    def test_ambiguous_name_fallback_is_rejected(self):
        self.write_material("Left.mat", "4" * 32, material_text("Shared", "{fileID: 46}", ""))
        self.write_material("Right.mat", "5" * 32, material_text("Shared", "{fileID: 46}", ""))
        self.assertIsNone(find_material_entry_by_name("Shared", self.db()))

