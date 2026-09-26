"""Public synthetic Unity YAML scalar cases, including quoted Unicode names."""

import unittest

from unitypackage_blender_importer.unity.yaml_parser import parse_scalar, parse_unity_yaml


class UnityYAMLScalarEscapeTests(unittest.TestCase):
    def test_double_quoted_unicode_and_name(self):
        self.assertEqual(parse_scalar(r'"\u5171\u901A"'), "共通")
        self.assertEqual(parse_scalar(r'"\U0001F600"'), "😀")
        source = "%YAML 1.1\n--- !u!1 &101\nGameObject:\n  m_Name: " + r'"Rei_\u5171\u901A"' + "\n"
        self.assertEqual(parse_unity_yaml(source)[0].data["m_Name"], "Rei_共通")

    def test_quote_style_controls_escaping(self):
        self.assertEqual(parse_scalar('"生の日本語"'), "生の日本語")
        self.assertEqual(parse_scalar(r"'\u5171'"), r"\u5171")
        self.assertEqual(parse_scalar(r"\u5171"), r"\u5171")
        self.assertEqual(parse_scalar("'it''s'"), "it's")
        self.assertEqual(parse_scalar(r'"a\"b\\c"'), 'a"b\\c')
        self.assertEqual(parse_scalar(r"C:\Work\VAPB"), r"C:\Work\VAPB")

    def test_invalid_double_quoted_escapes_fail_closed(self):
        for value in (r'"\uXYZ1"', r'"\U00110000"', r'"C:\Work"'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_scalar(value)


if __name__ == "__main__":
    unittest.main()
