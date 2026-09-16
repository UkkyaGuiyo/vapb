import unittest

from unitypackage_blender_importer.unity.texture_roles import TextureRole, canonical_texture_properties, classify_texture_property


class TextureRoleTests(unittest.TestCase):
    def test_explicit_roles_and_unknown_preserve_only(self):
        cases = {
            "_MainTex": TextureRole.BASE_COLOR,
            "_BaseMap": TextureRole.BASE_COLOR,
            "_BaseColorMap": TextureRole.BASE_COLOR,
            "_BumpMap": TextureRole.NORMAL,
            "_NormalMap": TextureRole.NORMAL,
            "_EmissionMap": TextureRole.EMISSION,
            "_MetallicGlossMap": TextureRole.METALLIC,
            "_SmoothnessTex": TextureRole.ROUGHNESS,
            "_OcclusionMap": TextureRole.OCCLUSION,
            "_MatCapTex": TextureRole.PRESERVE_ONLY,
            "_ShadowBorderMask": TextureRole.PRESERVE_ONLY,
            "_UnknownShaderSlot": TextureRole.PRESERVE_ONLY,
        }
        for property_name, expected in cases.items():
            with self.subTest(property_name=property_name):
                self.assertEqual(classify_texture_property("liltoon", "lilToon/lts_o", property_name), expected)

    def test_canonical_precedence_is_iteration_order_independent(self):
        first = {"_MainTex": {"guid": "a"}, "_BaseMap": {"guid": "b"}, "_BumpMap": {"guid": "c"}}
        second = {"_BumpMap": {"guid": "c"}, "_BaseMap": {"guid": "b"}, "_MainTex": {"guid": "a"}}
        self.assertEqual(canonical_texture_properties(first)[TextureRole.BASE_COLOR], "_MainTex")
        self.assertEqual(canonical_texture_properties(second)[TextureRole.BASE_COLOR], "_MainTex")

    def test_main_and_bump_have_distinct_canonical_roles(self):
        roles = canonical_texture_properties({"_MainTex": {"guid": "a"}, "_BumpMap": {"guid": "b"}, "_MatCapTex": {"guid": "c"}, "_ShadowBorderMask": {"guid": "d"}})
        self.assertEqual(roles[TextureRole.BASE_COLOR], "_MainTex")
        self.assertEqual(roles[TextureRole.NORMAL], "_BumpMap")
        self.assertNotIn(TextureRole.PRESERVE_ONLY, roles)


if __name__ == "__main__":
    unittest.main()
