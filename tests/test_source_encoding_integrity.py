"""Guard user-facing source files against UTF-8 transfer corruption."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
USER_FACING_SOURCES = (ROOT / "operators" / "import_unitypackage.py",)
_REQUIRED_UI_TEXT = (
    "\u539f\u672c\u306e\u4fdd\u7ba1\u5148",
    "UnityPackage\u539f\u672c\u3092\u4fdd\u7ba1\u3057\u307e\u3059\u3002\u7a7a\u6b04\u306a\u3089Blender\u30e6\u30fc\u30b6\u30fc\u30c7\u30fc\u30bf\u5185\u306eVAPB\u4fdd\u7ba1\u5148\u3092\u4f7f\u7528",
    "UnityPackage\u539f\u672c\u3092\u4fdd\u7ba1\u4e2d",
    "Scene\u5185\u306eImport\u8a18\u9332\u306b\u672a\u89e3\u6c7a\u9805\u76ee\u304c\u3042\u308a\u307e\u3059\u3002",
    "3D\u30d3\u30e5\u30fc\u306eN\u30ad\u30fc > VAPB Result > Import\u7d50\u679c\u3092\u78ba\u8a8d\u3057\u3066\u304f\u3060\u3055\u3044",
)


def source_is_intact(text: str) -> bool:
    return "\ufffd" not in text and all(phrase in text for phrase in _REQUIRED_UI_TEXT)


class SourceEncodingIntegrityTests(unittest.TestCase):
    def test_user_facing_sources_are_utf8_without_replacement_characters(self):
        for path in USER_FACING_SOURCES:
            with self.subTest(path=path.name):
                text = path.read_bytes().decode("utf-8", errors="strict")
                self.assertTrue(source_is_intact(text))

    def test_guard_rejects_replacement_and_malformed_ui_text(self):
        source = USER_FACING_SOURCES[0].read_bytes().decode("utf-8", errors="strict")
        self.assertFalse(source_is_intact(source + "\ufffd"))
        self.assertFalse(source_is_intact(source.replace(_REQUIRED_UI_TEXT[0], "???", 1)))


if __name__ == "__main__":
    unittest.main()
