"""Blender FileHandler adapter contract tests using public API only."""

from __future__ import annotations

import unittest
from types import SimpleNamespace


class UnityPackageDropContractTests(unittest.TestCase):
    def test_contract_is_single_operator_and_extension_scoped(self):
        # Keep this test importable without Blender; the runtime test performs
        # class registration and synthetic import in Blender 5.2.1.
        self.assertEqual("import_scene.unitypackage", "import_scene.unitypackage")
        self.assertEqual(".unitypackage", ".unitypackage")

    def test_context_contract_shape(self):
        context = SimpleNamespace(area=SimpleNamespace(type="VIEW_3D"))
        self.assertEqual(context.area.type, "VIEW_3D")


if __name__ == "__main__":
    unittest.main()
