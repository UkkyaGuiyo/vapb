from __future__ import annotations

import unittest
from pathlib import Path
import tempfile

from unitypackage_blender_importer.unity.asset_database import AssetDatabase, AssetEntry
from unitypackage_blender_importer.unity.material_model import UnityMaterialData, UnityTextureRef
from unitypackage_blender_importer.unity.profiles.base import normalize_material
from unitypackage_blender_importer.unity.shader_preview import (
    BUILTIN_SHADER, EXTERNAL_PROVIDER_MISSING, GENERIC_FALLBACK_PREVIEW,
    LOCAL_PROVIDER_FOUND, SEMANTIC_PREVIEW, build_shader_preview_ir,
)


def data(**kwargs):
    value = UnityMaterialData(path=Path("Material.mat"), name="Preview", **kwargs)
    return value


def normalized(value):
    return normalize_material(value)


class ShaderPreviewTests(unittest.TestCase):
    def test_preview_001_builtin_is_semantic(self):
        value = data(shader_guid="0000000000000000f000000000000000", shader_file_id=46)
        ir = build_shader_preview_ir(value, normalized(value))
        self.assertEqual(ir.provider_status, BUILTIN_SHADER)
        self.assertEqual(ir.mode, SEMANTIC_PREVIEW)

    def test_preview_002_external_provider_uses_fallback(self):
        value = data(shader_guid="a" * 32)
        ir = build_shader_preview_ir(value, normalized(value))
        self.assertEqual(ir.provider_status, EXTERNAL_PROVIDER_MISSING)
        self.assertEqual(ir.mode, GENERIC_FALLBACK_PREVIEW)

    def test_preview_003_local_shader_provider_is_semantic(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            shader = root / "Assets" / "Preview.shader"
            shader.parent.mkdir(parents=True)
            shader.write_text("Shader {}", encoding="utf-8")
            db = AssetDatabase(root, [AssetEntry("b" * 32, "Assets/Preview.shader", shader)])
            value = data(shader_guid="b" * 32)
            ir = build_shader_preview_ir(value, normalized(value), db)
        self.assertEqual(ir.provider_status, LOCAL_PROVIDER_FOUND)

    def test_preview_004_identity_is_preserved_separately(self):
        value = data(guid="c" * 32, unity_path="Assets/Preview.mat", shader_guid="d" * 32)
        ir = build_shader_preview_ir(value, normalized(value))
        self.assertEqual((ir.material_guid, ir.material_path), ("c" * 32, "Assets/Preview.mat"))
        self.assertEqual(ir.shader_guid, "d" * 32)

    def test_preview_005_maintex_is_base_color(self):
        value = data(textures={"_MainTex": UnityTextureRef("_MainTex", "e" * 32)})
        self.assertEqual(build_shader_preview_ir(value, normalized(value)).base_color_tex.guid, "e" * 32)

    def test_preview_006_bumpmap_is_normal(self):
        value = data(textures={"_BumpMap": UnityTextureRef("_BumpMap", "f" * 32)})
        self.assertEqual(build_shader_preview_ir(value, normalized(value)).normal_tex.guid, "f" * 32)

    def test_preview_007_normal_never_becomes_base_color(self):
        value = data(textures={"_BumpMap": UnityTextureRef("_BumpMap", "1" * 32)})
        ir = build_shader_preview_ir(value, normalized(value))
        self.assertIsNone(ir.base_color_tex)
        self.assertEqual(ir.normal_tex.property_name, "_BumpMap")

    def test_preview_008_main_and_normal_remain_distinct(self):
        value = data(textures={"_MainTex": UnityTextureRef("_MainTex", "2" * 32), "_NormalMap": UnityTextureRef("_NormalMap", "3" * 32)})
        ir = build_shader_preview_ir(value, normalized(value))
        self.assertEqual(ir.base_color_tex.guid, "2" * 32)
        self.assertEqual(ir.normal_tex.guid, "3" * 32)

    def test_preview_009_missing_base_does_not_substitute_normal(self):
        value = data(textures={"_NormalMap": UnityTextureRef("_NormalMap", "4" * 32)})
        self.assertIsNone(build_shader_preview_ir(value, normalized(value)).base_color_tex)

    def test_preview_010_liltoon_common_roles_are_conservative(self):
        value = data(textures={"_MainTex": UnityTextureRef("_MainTex", "5" * 32), "_BumpMap": UnityTextureRef("_BumpMap", "6" * 32)})
        ir = build_shader_preview_ir(value, normalized(value))
        self.assertEqual(ir.mode, GENERIC_FALLBACK_PREVIEW)
        self.assertNotIn("texture:_MainTex", ir.unsupported_features)

    def test_preview_011_emission_requires_explicit_property(self):
        value = data(colors={"_EmissionColor": (1, 0, 0, 1)})
        self.assertEqual(build_shader_preview_ir(value, normalized(value)).emission_color, (1, 0, 0, 1))

    def test_preview_012_unknown_color_is_not_emission(self):
        value = data(colors={"_Tint": (1, 0, 0, 1)})
        self.assertEqual(build_shader_preview_ir(value, normalized(value)).emission_color, (0, 0, 0, 1))

    def test_preview_013_metallic_requires_explicit_property(self):
        value = data(floats={"_Metallic": 0.75})
        self.assertEqual(build_shader_preview_ir(value, normalized(value)).metallic, 0.75)

    def test_preview_014_unknown_float_does_not_become_metallic(self):
        value = data(floats={"_Shine": 0.75})
        self.assertEqual(build_shader_preview_ir(value, normalized(value)).metallic, 0.0)

    def test_preview_015_glossiness_becomes_roughness(self):
        value = data(floats={"_Glossiness": 0.8})
        self.assertAlmostEqual(build_shader_preview_ir(value, normalized(value)).roughness, 0.2)

    def test_preview_016_missing_provider_is_nonfatal(self):
        value = data(shader_guid="7" * 32, textures={"_MainTex": UnityTextureRef("_MainTex", "8" * 32)})
        ir = build_shader_preview_ir(value, normalized(value))
        self.assertEqual(ir.base_color_tex.guid, "8" * 32)
        self.assertIn("external_shader_provider", ir.unsupported_features)

    def test_preview_017_unknown_texture_is_reported(self):
        value = data(textures={"_Mystery": UnityTextureRef("_Mystery", "9" * 32)})
        self.assertIn("texture:_Mystery", build_shader_preview_ir(value, normalized(value)).unsupported_features)

    def test_preview_018_alpha_stays_explicit(self):
        value = data(floats={"_Mode": 2})
        self.assertEqual(build_shader_preview_ir(value, normalized(value)).alpha_mode, "blend")

    def test_preview_019_cutout_cutoff_is_preserved(self):
        value = data(floats={"_AlphaClip": 1, "_Cutoff": 0.35})
        self.assertEqual(build_shader_preview_ir(value, normalized(value)).alpha_cutoff, 0.35)

    def test_preview_020_to_dict_is_machine_readable(self):
        ir = build_shader_preview_ir(data(), normalized(data()))
        self.assertEqual(ir.to_dict()["mode"], ir.mode)
        self.assertIsInstance(ir.to_dict()["unsupported_features"], list)

    def test_preview_021_provider_status_is_not_shader_family(self):
        value = data(shader_guid="a" * 32)
        ir = build_shader_preview_ir(value, normalized(value))
        self.assertNotEqual(ir.provider_status, ir.shader_name)

    def test_preview_022_no_provider_db_is_safe(self):
        value = data(shader_guid="b" * 32)
        self.assertIsNotNone(build_shader_preview_ir(value, normalized(value), None))

    def test_preview_023_non_shader_guid_does_not_count_as_local_provider(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            texture = root / "Assets" / "Texture.png"
            texture.parent.mkdir(parents=True)
            texture.write_bytes(b"x")
            db = AssetDatabase(root, [AssetEntry("c" * 32, "Assets/Texture.png", texture)])
            value = data(shader_guid="c" * 32)
            self.assertEqual(build_shader_preview_ir(value, normalized(value), db).provider_status, EXTERNAL_PROVIDER_MISSING)

    def test_preview_024_unsupported_features_are_sorted(self):
        value = data(textures={"_Zed": UnityTextureRef("_Zed"), "_Able": UnityTextureRef("_Able")})
        features = build_shader_preview_ir(value, normalized(value)).unsupported_features
        self.assertEqual(features, tuple(sorted(features)))

    def test_preview_025_material_path_is_not_overwritten_by_shader_path(self):
        value = data(unity_path="Assets/Materials/A.mat", shader_guid="d" * 32)
        self.assertEqual(build_shader_preview_ir(value, normalized(value)).material_path, "Assets/Materials/A.mat")

    def test_preview_026_empty_shader_is_unknown(self):
        self.assertNotEqual(build_shader_preview_ir(data(), normalized(data())).provider_status, BUILTIN_SHADER)

    def test_preview_027_base_color_is_preserved(self):
        value = data(colors={"_Color": (0.1, 0.2, 0.3, 1)})
        self.assertEqual(build_shader_preview_ir(value, normalized(value)).base_color, (0.1, 0.2, 0.3, 1))

    def test_preview_028_normal_strength_is_preserved(self):
        value = data(floats={"_BumpScale": 0.25}, textures={"_BumpMap": UnityTextureRef("_BumpMap", "e" * 32)})
        self.assertEqual(build_shader_preview_ir(value, normalized(value)).normal_strength, 0.25)


if __name__ == "__main__":
    unittest.main()
