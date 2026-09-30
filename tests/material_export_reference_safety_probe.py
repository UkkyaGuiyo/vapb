"""Diagnostic requirements probe: currently RED; excluded from normal discovery."""
from pathlib import Path
import tempfile
import unittest

from unitypackage_blender_importer.unity.asset_database import AssetDatabase
from unitypackage_blender_importer.unity.material_parser import parse_material

class ExportReferenceSafety(unittest.TestCase):
    def parse(self, property_name='_FutureTexture', file_id='2800000'):
        text = f'''%YAML 1.1
--- !u!21 &2100000
Material:
  m_Name: Synthetic
  m_Shader: {{fileID: 46, guid: 0000000000000000f000000000000000, type: 0}}
  m_SavedProperties:
    m_TexEnvs:
    - {property_name}:
        m_Texture: {{fileID: {file_id}, guid: 22222222222222222222222222222222, type: 3}}
        m_Scale: {{x: 1, y: 1}}
        m_Offset: {{x: 0, y: 0}}
'''
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'Synthetic.mat'
            path.write_text(text, encoding='utf-8')
            return parse_material(path, AssetDatabase(Path(tmp)))

    def test_unknown_underscore_property_preserved(self):
        self.assertEqual(2800000, self.parse().textures['_FutureTexture'].file_id)

    def test_unknown_nonunderscore_property_preserved(self):
        self.assertIn('FutureTexture', self.parse('FutureTexture').textures)

    def test_invalid_fileid_rejected_instead_of_null(self):
        with self.assertRaises(ValueError):
            self.parse(file_id='not_an_integer')

    def test_explicit_null_remains_null(self):
        self.assertEqual(0, self.parse(file_id='0').textures['_FutureTexture'].file_id)

if __name__ == '__main__':
    unittest.main(verbosity=2)
