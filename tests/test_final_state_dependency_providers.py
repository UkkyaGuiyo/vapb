"""Package provenance resolution for final-state dependencies, no bpy required."""
from pathlib import Path
import hashlib
import tempfile
import unittest
from types import SimpleNamespace

from unitypackage_blender_importer.blender.identity_registry import save_scene_registry
from unitypackage_blender_importer.unity.identity import SceneIdentityRegistry
from unitypackage_blender_importer.export.final_state_package import _resolve_source_asset, _shader_dependency
from unitypackage_blender_importer.export.package_writer import UnityPackageWriter
from unitypackage_blender_importer.export.staging import StagedUnityAsset, StagingTree


class FinalStateDependencyProviders(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.scene = {}
        self.registry = SceneIdentityRegistry()

    def tearDown(self):
        self.temp.cleanup()

    def package(self, name, guid, payload, suffix='.png', importer='TextureImporter'):
        path = self.root / (name + '.unitypackage')
        asset = StagedUnityAsset(guid, f'Assets/{name}{suffix}', payload,
                                f'fileFormatVersion: 2\nguid: {guid}\n{importer}:\n'.encode())
        UnityPackageWriter().write(StagingTree([asset]), path)
        sha = hashlib.sha256(path.read_bytes()).hexdigest()
        package_id = 'sha256:' + sha
        self.registry.register_package({'source_package_id': package_id,
            'package_sha256': sha, 'source_archive_path': str(path)})
        save_scene_registry(self.scene, self.registry)
        return package_id, path

    def test_unique_cross_package_provider(self):
        consumer, _ = self.package('Consumer', '1' * 32, b'consumer')
        self.package('Texture', '2' * 32, b'texture')
        self.assertEqual(b'texture', _resolve_source_asset(self.scene, consumer, '2' * 32).asset_bytes)

    def test_local_wins_over_other_package(self):
        consumer, _ = self.package('Local', '2' * 32, b'local')
        self.package('Other', '2' * 32, b'other')
        self.assertEqual(b'local', _resolve_source_asset(self.scene, consumer, '2' * 32).asset_bytes)

    def test_missing_provider_refused(self):
        consumer, _ = self.package('Consumer', '1' * 32, b'consumer')
        with self.assertRaisesRegex(ValueError, 'UNRESOLVED'):
            _resolve_source_asset(self.scene, consumer, '2' * 32)

    def test_multiple_providers_refused_even_with_equal_payload(self):
        consumer, _ = self.package('Consumer', '1' * 32, b'consumer')
        self.package('First', '2' * 32, b'same')
        self.package('Second', '2' * 32, b'same')
        with self.assertRaisesRegex(ValueError, 'AMBIGUOUS'):
            _resolve_source_asset(self.scene, consumer, '2' * 32)

    def test_changed_provider_revision_refused(self):
        consumer, _ = self.package('Consumer', '1' * 32, b'consumer')
        _, provider = self.package('Texture', '2' * 32, b'texture')
        provider.write_bytes(provider.read_bytes() + b'changed')
        with self.assertRaisesRegex(ValueError, 'revision changed'):
            _resolve_source_asset(self.scene, consumer, '2' * 32)

    def test_builtin_shader_needs_no_source_provider(self):
        data = SimpleNamespace(shader_guid='0000000000000000f000000000000000', shader_file_id=46)
        record, source = _shader_dependency({}, 'absent', data, {})
        self.assertEqual('UNITY_BUILTIN', record['classification'])
        self.assertIsNone(source)

    def test_shader_unique_registered_provider(self):
        consumer, _ = self.package('Consumer', '1' * 32, b'consumer')
        self.package('Shader', '3' * 32, b'Shader "Synthetic" {}', '.shader', 'ShaderImporter')
        record, source = _shader_dependency(self.scene, consumer,
            SimpleNamespace(shader_guid='3' * 32, shader_file_id=4800000), {})
        self.assertEqual('PACKAGE_PROVIDER', record['classification'])
        self.assertEqual('3' * 32, source.guid)

    def test_unresolved_shader_refused(self):
        consumer, _ = self.package('Consumer', '1' * 32, b'consumer')
        with self.assertRaisesRegex(ValueError, 'UNRESOLVED'):
            _shader_dependency(self.scene, consumer,
                SimpleNamespace(shader_guid='3' * 32, shader_file_id=4800000), {})

    def test_shader_framework_closure_not_silently_assumed(self):
        for index, shader in enumerate((b'#include "missing.cginc"', b'UsePass "Other/Pass"', b'Fallback "Other"')):
            with self.subTest(shader=shader):
                consumer, _ = self.package('Shader' + str(index), '3' * 32, shader, '.shader', 'ShaderImporter')
                with self.assertRaisesRegex(ValueError, 'external dependency closure'):
                    _shader_dependency(self.scene, consumer,
                        SimpleNamespace(shader_guid='3' * 32, shader_file_id=4800000), {})
