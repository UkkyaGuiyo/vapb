import io
import tarfile
import tempfile
import unittest
from pathlib import Path

from tools.shader_semantic_oracle.material_inventory import (
    inventory_material_package,
    public_safe_summary,
)


def write_package(path, entries):
    with tarfile.open(path, "w:gz") as archive:
        for guid, pathname, asset in entries:
            for suffix, payload in (("pathname", pathname.encode()), ("asset", asset.encode())):
                info = tarfile.TarInfo(f"{guid}/{suffix}")
                info.size = len(payload)
                archive.addfile(info, io.BytesIO(payload))


class MaterialInventoryTests(unittest.TestCase):
    def test_extracts_public_material_schema_without_texture_decode(self):
        with tempfile.TemporaryDirectory() as temp:
            package = Path(temp) / "sample.unitypackage"
            write_package(package, [
                ("a" * 32, "Assets/Sample.mat", """
m_Shader: {fileID: 4800000, guid: bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb, type: 3}
m_SavedProperties:
  m_TexEnvs:
  - _MainTex:
      m_Texture: {fileID: 2800000, guid: cccccccccccccccccccccccccccccccc, type: 3}
      m_Scale: {x: 2, y: 3}
      m_Offset: {x: 0.1, y: 0.2}
  m_Colors:
  - _Color: {r: 1, g: 0, b: 0, a: 1}
  m_Floats:
  - _Cutoff: 0.5
  m_Vectors:
  - _Direction: {x: 1, y: 0, z: 0, w: 0}
"""),
                ("c" * 32, "Assets/Sample.png", "not decoded"),
            ])
            result = inventory_material_package(package)
            self.assertEqual(result["material_count"], 1)
            material = result["materials"][0]
            self.assertEqual(material["shader_guid"], "b" * 32)
            self.assertEqual(material["property_counts"], {"Texture": 1, "Color": 1, "Float": 1, "Vector": 1})
            self.assertEqual(material["texture_references"], ["c" * 32])
            self.assertEqual(material["texture_transforms"]["_MainTex"]["scale"], {"x": 2.0, "y": 3.0})

    def test_public_summary_removes_private_identity(self):
        result = {"materials": [{"material_id": "M-0001", "asset_path": "LOCAL_PATH_REQUIRES_CONFIGURATION", "shader_guid": "a" * 32, "property_counts": {"Texture": 1}}], "shader_frequency": {"a" * 32: 1}}
        safe = public_safe_summary(result)
        self.assertNotIn("Product.mat", str(safe))
        self.assertNotIn("a" * 32, str(safe))
        self.assertEqual(safe["materials"][0]["material_id"], "M-0001")


if __name__ == "__main__":
    unittest.main()
