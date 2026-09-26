from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from unitypackage_blender_importer.unity.asset_database import AssetDatabase, AssetEntry
from unitypackage_blender_importer.unity.material_mapping import (
    find_material_entry_by_name,
    parse_external_objects,
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

    def test_ambiguous_name_fallback_is_rejected(self):
        self.write_material("Left.mat", "4" * 32, material_text("Shared", "{fileID: 46}", ""))
        self.write_material("Right.mat", "5" * 32, material_text("Shared", "{fileID: 46}", ""))
        self.assertIsNone(find_material_entry_by_name("Shared", self.db()))
