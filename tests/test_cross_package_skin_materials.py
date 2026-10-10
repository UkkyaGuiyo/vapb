"""Selected cross-package Skin Material closure, without Blender/Unity startup."""
import ast
import hashlib
from pathlib import Path
import re
import tempfile
from types import SimpleNamespace
import unittest

from unitypackage_blender_importer.blender.identity_registry import load_scene_registry
from unitypackage_blender_importer.export.final_state_package import _source_assets, _material_texture_guids
from unitypackage_blender_importer.export.model_package import SourcePackage, TextureReplacement, materialize_model_package
from unitypackage_blender_importer.tests.test_model_package import make_archive, fields
from unitypackage_blender_importer.unity.identity import SceneIdentityRegistry

ROOT = Path(__file__).resolve().parents[1]

class CrossPackageSkinMaterials(unittest.TestCase):
    def setUp(self):
        tree = ast.parse((ROOT / 'operators/export_unitypackage.py').read_text(encoding='utf-8-sig'))
        names = {'_model_material_sources', '_materials', '_working_textures'}
        functions = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
        self.ns = dict(Path=Path, re=re, hashlib=hashlib, SourcePackage=SourcePackage,
                       TextureReplacement=TextureReplacement, load_scene_registry=load_scene_registry,
                       _source_assets=_source_assets, _material_texture_guids=_material_texture_guids)
        exec(compile(ast.Module(body=functions, type_ignores=[]), str(ROOT / 'operators/export_unitypackage.py'), 'exec'), self.ns)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.primary = make_archive(root / 'primary.unitypackage', fields('a'*32, 'Assets/Original.fbx', b'original-fbx'))
        self.mat = b'''%YAML 1.1
--- !u!21 &2100000
Material:
  m_Name: Synthetic
  m_Shader: {fileID: 46, guid: 0000000000000000f000000000000000, type: 0}
  m_SavedProperties:
    m_TexEnvs:
    - FutureTexture:
        m_Texture: {fileID: 2800000, guid: cccccccccccccccccccccccccccccccc, type: 3}
'''
        self.donor = make_archive(root / 'donor.unitypackage', fields('b'*32, 'Assets/Donor.mat', self.mat) +
            fields('c'*32, 'Assets/Color.png', b'original-png', b'guid: '+b'c'*32+b'\nTextureImporter:\n'))
        self.pid = 'sha256:' + self.primary.expected_sha256
        self.did = 'sha256:' + self.donor.expected_sha256
        registry = SceneIdentityRegistry()
        for source in (self.primary, self.donor):
            registry.register_package(dict(source_package_id='sha256:'+source.expected_sha256,
                package_sha256=source.expected_sha256, source_archive_path=str(source.path)))
        self.scene = {'unitypackage_identity_registry': registry.to_json()}
        self.material = dict(unity_source_package_id=self.did, unity_material_guid='b'*32,
                             unity_material_file_id='2100000')
        self.mesh = SimpleNamespace(material_slots=[SimpleNamespace(material=self.material)])

    def closure(self):
        self.assertTrue('_model_material_sources' in self.ns, 'Skin export must collect verified selected Material sources')
        return self.ns['_model_material_sources'](self.scene, [self.mesh], self.pid)

    def test_selected_donor_closure_preserves_original_fbx_material_and_meta(self):
        sources, assets = self.closure()
        self.assertEqual({self.pid, self.did}, set(assets))
        refs = self.ns['_materials'](self.mesh, self.pid, list(assets[self.pid].values()), assets_by_package=assets)
        self.assertEqual([dict(guid='b'*32, file_id='2100000')], refs)
        tree, _ = materialize_model_package(sources, [], generator_version='test', blender_version='test')
        self.assertEqual(b'original-fbx', tree.get('a'*32).asset_bytes)
        self.assertEqual(self.mat, tree.get('b'*32).asset_bytes)
        self.assertEqual(assets[self.did]['b'*32].meta_bytes, tree.get('b'*32).meta_bytes)

    def test_stale_donor_archive_is_refused(self):
        self.donor.path.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'revision'):
            self.closure()

    def test_unregistered_donor_is_refused(self):
        self.material['unity_source_package_id'] = 'sha256:'+'e'*64
        with self.assertRaisesRegex(ValueError, 'unavailable'):
            self.closure()

    def test_missing_unpreviewed_texture_is_still_refused(self):
        _, assets = self.closure()
        del assets[self.did]['c'*32]
        with self.assertRaisesRegex(ValueError, 'Texture'):
            self.ns['_materials'](self.mesh, self.pid, list(assets[self.pid].values()), assets_by_package=assets)

    def test_working_donor_texture_retains_actual_source_namespace(self):
        _, assets = self.closure()
        class Image(dict):
            library = None
            source = 'FILE'
            is_dirty = False
            packed_file = SimpleNamespace(data=b'edited-png')
            def as_pointer(self): return 1
        image = Image(unity_guid='c'*32, unity_source_package_id=self.did, unity_asset_path='Assets/Color.png')
        tree = SimpleNamespace(as_pointer=lambda: 2, nodes=[SimpleNamespace(image=image, type='TEX_IMAGE')])
        class Material(dict): pass
        material = Material(self.material)
        material.node_tree = tree
        self.mesh.material_slots[0].material = material
        edits = self.ns['_working_textures'](self.mesh, self.pid, list(assets[self.pid].values()), assets_by_package=assets)
        self.assertEqual(1, len(edits))
        self.assertEqual(self.did, edits[0].source_package_id)
        self.assertEqual(hashlib.sha256(b'original-png').hexdigest(), edits[0].expected_asset_sha256)
        self.assertEqual(b'edited-png', edits[0].encoded_bytes)

    def test_unassigned_slot_does_not_include_unselected_donor(self):
        self.mesh.material_slots[0].material = None
        sources, assets = self.closure()
        self.assertEqual({self.pid}, set(assets))
        self.assertEqual([self.primary], sources)

    def test_donor_material_wrong_local_id_is_refused(self):
        _, assets = self.closure()
        self.material['unity_material_file_id'] = '2100001'
        with self.assertRaisesRegex(ValueError, 'identity'):
            self.ns['_materials'](self.mesh, self.pid, list(assets[self.pid].values()), assets_by_package=assets)

    def test_legacy_single_package_call_keeps_cross_package_refusal(self):
        _, assets = self.closure()
        with self.assertRaises(ValueError):
            self.ns['_materials'](self.mesh, self.pid, list(assets[self.pid].values()))
