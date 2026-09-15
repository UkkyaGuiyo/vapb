"""Generic public-repository safety checks without product-specific deny lists."""

from __future__ import annotations

from pathlib import Path
import re
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {
    ".py", ".md", ".json", ".yaml", ".yml", ".toml", ".txt", ".ps1",
    ".bat", ".cmd", ".sh", ".ini", ".cfg", ".log", ".csv", ".cs",
}
FORBIDDEN_BINARY_SUFFIXES = {".unitypackage", ".fbx", ".blend", ".psd", ".tga"}
LOCAL_PATH_PATTERNS = (
    re.compile(r"[A-Za-z]:" + re.escape("\\") + "Users" + re.escape("\\") + r"[^\\\r\n\"'`]+"),
    re.compile(re.escape("/") + "Users" + re.escape("/") + r"[^/\r\n\"'`]+"),
    re.compile(re.escape("/") + "home" + re.escape("/") + r"[^/\r\n\"'`]+"),
)
SECRET_PATTERNS = (
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\b(?:ghp_|github_pat_|xoxb-|xoxp-|sk-)[A-Za-z0-9_-]{16,}"),
    re.compile(r"\bBearer\s+[A-Za-z0-9._-]{20,}"),
)


def tracked_files() -> list[Path]:
    output = subprocess.check_output(["git", "ls-files"], cwd=ROOT, text=True)
    return [ROOT / line for line in output.splitlines() if line]


class PublicRepositoryHygieneTests(unittest.TestCase):
    def test_no_developer_paths_or_obvious_secrets_in_tracked_text(self):
        for path in tracked_files():
            if path.suffix.lower() not in TEXT_SUFFIXES:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            for pattern in LOCAL_PATH_PATTERNS + SECRET_PATTERNS:
                self.assertIsNone(pattern.search(text), str(path))

    def test_no_proprietary_asset_binaries_are_tracked(self):
        offenders = [
            str(path.relative_to(ROOT))
            for path in tracked_files()
            if path.suffix.lower() in FORBIDDEN_BINARY_SUFFIXES
        ]
        self.assertEqual(offenders, [])

    def test_real_package_probe_is_explicitly_local_only(self):
        probe = (ROOT / "tests" / "blender_real_identity_verify.py").read_text(encoding="utf-8")
        self.assertIn("UNITYPACKAGE_REAL_TEST_FILE", probe)
        self.assertIn("REAL_PACKAGE_TEST_SKIPPED", probe)


if __name__ == "__main__":
    unittest.main()
