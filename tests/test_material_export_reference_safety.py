"""Focused strict export-reference requirements, runnable independently."""
from pathlib import Path
import tempfile
import unittest

from unitypackage_blender_importer.unity.asset_database import AssetDatabase
from unitypackage_blender_importer.unity.material_parser import parse_material
from unitypackage_blender_importer.export.final_state_package import _material_texture_guids

class ExportReferenceSafety(unittest.TestCase):
    def parse(self, property_name='_FutureTexture', file_id='2800000', guid='22222222222222222222222222222222', extra=''):
        text = f'''%YAML 1.1
--- !u!21 &2100000
Material:
  m_Name: Synthetic
  m_Shader: {{fileID: 46, guid: 0000000000000000f000000000000000, type: 0}}
  m_SavedProperties:
    m_TexEnvs:
    - {property_name}:
        m_Texture: {{fileID: {file_id}, guid: {guid}, type: 3}}
        m_Scale: {{x: 1, y: 1}}
        m_Offset: {{x: 0, y: 0}}
{extra}
'''
        self.payload = text.encode('utf-8')
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'Synthetic.mat'
            path.write_text(text, encoding='utf-8')
            return parse_material(path, AssetDatabase(Path(tmp)), strict_references=True)

    def test_unknown_underscore_property_preserved(self):
        self.assertEqual(2800000, self.parse().textures['_FutureTexture'].file_id)

    def test_unknown_nonunderscore_property_preserved(self):
        self.assertIn('FutureTexture', self.parse('FutureTexture').textures)

    def test_quoted_property_name_preserved(self):
        self.assertIn('Future:Texture', self.parse('"Future:Texture"').textures)

    def test_invalid_fileid_rejected_instead_of_null(self):
        with self.assertRaises(ValueError):
            self.parse(file_id='not_an_integer')

    def test_explicit_null_remains_null(self):
        self.assertEqual(0, self.parse(file_id='0').textures['_FutureTexture'].file_id)

    def test_numeric_guid_keeps_leading_zeroes(self):
        guid = '0' * 31 + '2'
        self.assertEqual(guid, self.parse(guid=guid).textures['_FutureTexture'].guid)

    def test_same_asset_keeps_separate_property_uses(self):
        extra = '''    - OtherTexture:
        m_Texture: {fileID: 2800000, guid: 22222222222222222222222222222222, type: 3}'''
        data = self.parse(extra=extra)
        self.assertEqual(2, len(data.textures))
        self.assertEqual(1, len({r.guid for r in data.textures.values()}))

    def test_duplicate_reference_fields_rejected(self):
        with self.assertRaises(ValueError):
            self.parse(file_id='2800000, fileID: 2800001')

    def test_invalid_guid_and_overflow_rejected(self):
        with self.assertRaises(ValueError):
            self.parse(guid='unknown')
        with self.assertRaises(ValueError):
            self.parse(file_id=str(1 << 63))

    def test_duplicate_property_rejected(self):
        extra = '''    - _FutureTexture:
        m_Texture: {fileID: 2800000, guid: 22222222222222222222222222222222, type: 3}'''
        with self.assertRaises(ValueError):
            self.parse(extra=extra)

    def test_exporter_collects_unknown_property_and_excludes_null(self):
        self.parse('FutureTexture')
        self.assertEqual({'2' * 32}, _material_texture_guids(self.payload))
        self.parse('FutureTexture', file_id='0')
        self.assertEqual(set(), _material_texture_guids(self.payload))

    def test_exporter_rejects_malformed_reference(self):
        with self.assertRaises(ValueError):
            self.parse(file_id='not_an_integer')
        with self.assertRaises(ValueError):
            _material_texture_guids(self.payload)


try:
    import bpy
except ImportError:
    bpy = None

@unittest.skipIf(bpy is None, "actual Skin export operator requires Blender")
class SkinExportTextureClosure(unittest.TestCase):
    def test_selected_material_requires_unpreviewed_texture_provider(self):
        from unitypackage_blender_importer.operators.export_unitypackage import _materials
        from unitypackage_blender_importer.export.raw_assets import RawAsset
        parser = ExportReferenceSafety()
        parser.parse('FutureTexture')
        material = bpy.data.materials.new('SourceTextureClosure')
        mesh = bpy.data.meshes.new('SourceTextureClosure')
        obj = bpy.data.objects.new('SourceTextureClosure', mesh)
        try:
            material['unity_source_package_id'] = 'sha256:' + 'a' * 64
            material['unity_material_guid'] = 'a' * 32
            material['unity_material_file_id'] = '2100000'
            mesh.materials.append(material)
            source = RawAsset('a' * 32, 'Assets/Source.mat', parser.payload, b'guid: ' + b'a' * 32)
            # No preview Image node exists for this serialized future property.
            with self.assertRaisesRegex(ValueError, 'Texture'):
                _materials(obj, material['unity_source_package_id'], [source])
            provider = RawAsset('2' * 32, 'Assets/Color.png', b'source-png', b'guid: ' + b'2' * 32)
            self.assertEqual([{'guid': 'a' * 32, 'file_id': '2100000'}],
                _materials(obj, material['unity_source_package_id'], [source, provider]))
            self.assertEqual(parser.payload, source.asset_bytes)
            parser.parse('FutureTexture', file_id='0')
            null_source = RawAsset('a' * 32, 'Assets/Source.mat', parser.payload, source.meta_bytes)
            self.assertEqual([{'guid': 'a' * 32, 'file_id': '2100000'}],
                _materials(obj, material['unity_source_package_id'], [null_source]))
            unused = RawAsset('b' * 32, 'Assets/Unused.mat', source.asset_bytes, b'guid: ' + b'b' * 32)
            self.assertEqual([{'guid': 'a' * 32, 'file_id': '2100000'}],
                _materials(obj, material['unity_source_package_id'], [null_source, unused]))
            parser.parse('FutureTexture', file_id='10300', guid='0000000000000000f000000000000000')
            builtin_source = RawAsset('a' * 32, 'Assets/Source.mat', parser.payload, source.meta_bytes)
            self.assertEqual([{'guid': 'a' * 32, 'file_id': '2100000'}],
                _materials(obj, material['unity_source_package_id'], [builtin_source]))
        finally:
            bpy.data.objects.remove(obj)
            bpy.data.meshes.remove(mesh)
            bpy.data.materials.remove(material)

if __name__ == '__main__':
    unittest.main(verbosity=2)
