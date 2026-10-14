# SPDX-License-Identifier: GPL-3.0-or-later
import copy
import hashlib
from types import SimpleNamespace
import unittest

from unitypackage_blender_importer.export.script_dependencies import (
    script_dependencies_for_tasks, missing_material_shader_dependencies_for_tasks)


def asset(guid, path, text):
    return SimpleNamespace(guid=guid, pathname=path, asset_bytes=text.encode())


class ScriptDependencyTests(unittest.TestCase):
    def setUp(self):
        self.root, self.child, self.provider = '1' * 32, '2' * 32, '3' * 32
        self.payload = self.script(101) + self.script(-102)
        self.assets = [asset(self.root, 'Assets/Selected.prefab', self.payload)]
        self.tasks = [dict(kind='RESTORE_DIRECT_SKIN_VARIANT_V1', prefab_guid=self.root,
                           prefab_source_sha256=hashlib.sha256(self.payload.encode()).hexdigest())]

    def script(self, component, file_id=-11500001, guid=None):
        return f'--- !u!114 &{component}\nMonoBehaviour:\n  m_Script: {{fileID: {file_id}, guid: {guid or self.provider}, type: 3}}\n'

    def test_exact_reference_dedup_and_revision_context(self):
        rows = script_dependencies_for_tasks(self.tasks, self.assets)
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row['kind'], 'UNITY_SCRIPT')
        self.assertEqual(row['file_id'], '-11500001')
        self.assertEqual(row['status'], 'EXTERNAL_DEPENDENCY_REQUIRED')
        self.assertEqual(row['classification'], 'UNRESOLVED_BUT_PRESERVED')
        self.assertEqual(row['reference_id'], 'VAPB-REF-' + hashlib.sha256(
            f'UNITY_SCRIPT:{self.provider}:-11500001'.encode()).hexdigest()[:32])
        self.assertEqual({r['component_file_id'] for r in row['required_by']}, {'101', '-102'})
        self.assertTrue(all(r['asset_sha256'] == self.tasks[0]['prefab_source_sha256'] for r in row['required_by']))
        self.assertNotIn('provider_package', row)

    def test_contained_provider_is_not_external(self):
        self.assets.append(asset(self.provider, 'Assets/Provider.dll', 'first-party'))
        self.assertEqual(script_dependencies_for_tasks(self.tasks, self.assets), ())

    def test_numeric_guid_leading_zeroes_preserved(self):
        guid = '0' * 31 + '7'
        a = asset(self.root, 'Assets/Selected.prefab', self.script(101, guid=guid))
        t = copy.deepcopy(self.tasks)
        t[0]['prefab_source_sha256'] = hashlib.sha256(a.asset_bytes).hexdigest()
        self.assertEqual(script_dependencies_for_tasks(t, [a])[0]['guid'], guid)

    def test_same_guid_different_signed_id_remains_distinct(self):
        self.assets[0] = asset(self.root, 'Assets/Selected.prefab', self.payload + self.script(103, -11500002))
        self.tasks[0]['prefab_source_sha256'] = hashlib.sha256(self.assets[0].asset_bytes).hexdigest()
        self.assertEqual(len(script_dependencies_for_tasks(self.tasks, self.assets)), 2)

    def test_nested_source_chain_only_and_deterministic(self):
        text = self.payload + f'--- !u!1001 &9\nPrefabInstance:\n  m_SourcePrefab: {{fileID: 100100000, guid: {self.child}, type: 3}}\n'
        self.assets[0] = asset(self.root, 'Assets/Selected.prefab', text)
        self.tasks[0]['prefab_source_sha256'] = hashlib.sha256(self.assets[0].asset_bytes).hexdigest()
        self.assets += [asset(self.child, 'Assets/Nested.prefab', self.script(104)),
                        asset('4' * 32, 'Assets/Unused.prefab', self.script(105, guid='5' * 32))]
        rows = script_dependencies_for_tasks(self.tasks, self.assets)
        self.assertEqual(len(rows), 1)
        self.assertEqual(len(rows[0]['required_by']), 3)
        self.assertEqual(rows, script_dependencies_for_tasks(self.tasks * 2, list(reversed(self.assets))))

    def test_malformed_references_and_stale_source_fail_closed(self):
        for file_id, guid in [(0, self.provider), (1 << 63, self.provider), ('1.2', self.provider), (1, 'bad')]:
            with self.subTest(file_id=file_id, guid=guid):
                a = asset(self.root, 'Assets/Selected.prefab', self.script(101, file_id, guid))
                t = copy.deepcopy(self.tasks)
                t[0]['prefab_source_sha256'] = hashlib.sha256(a.asset_bytes).hexdigest()
                with self.assertRaises(ValueError):
                    script_dependencies_for_tasks(t, [a])
        t = copy.deepcopy(self.tasks)
        t[0]['prefab_source_sha256'] = '0' * 64
        with self.assertRaises(ValueError):
            script_dependencies_for_tasks(t, self.assets)

    def test_null_script_stays_unexplained_and_unrelated_task_ignored(self):
        a = asset(self.root, 'Assets/Selected.prefab', '--- !u!114 &101\nMonoBehaviour:\n  m_Script: {fileID: 0}\n')
        t = copy.deepcopy(self.tasks)
        t[0]['prefab_source_sha256'] = hashlib.sha256(a.asset_bytes).hexdigest()
        self.assertEqual(script_dependencies_for_tasks(t, [a]), ())
        self.assertEqual(script_dependencies_for_tasks([{'kind': 'UNRELATED'}], self.assets), ())


class MissingMaterialShaderTests(unittest.TestCase):
    def dependencies(self, tasks, assets):
        return missing_material_shader_dependencies_for_tasks(tasks, assets)

    def setUp(self):
        self.material, self.shader = '6' * 32, '7' * 32
        self.text = ('--- !u!21 &2100000\nMaterial:\n'
                     f'  m_Shader: {{fileID: 4800000, guid: {self.shader}, type: 3}}\n')
        self.asset = asset(self.material, 'Assets/Bound.mat', self.text)
        self.task = dict(kind='RESTORE_DIRECT_SKIN_VARIANT_V1', material_bindings=[
            dict(guid=self.material, file_id='2100000')])

    def test_missing_bound_provider_declared_without_changing_material(self):
        rows = self.dependencies([self.task], [self.asset])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['kind'], 'SHADER')
        self.assertEqual(rows[0]['guid'], self.shader)
        self.assertEqual(rows[0]['file_id'], '4800000')
        self.assertEqual(rows[0]['status'], 'UNRESOLVED_BUT_PRESERVED')
        self.assertEqual(rows[0]['required_by'], [dict(asset_guid=self.material,
            asset_sha256=hashlib.sha256(self.text.encode()).hexdigest(), component_file_id='2100000')])
        self.assertEqual(self.asset.asset_bytes, self.text.encode())

    def test_bundled_or_builtin_provider_is_not_missing(self):
        self.assertEqual(self.dependencies([self.task], [self.asset,
            asset(self.shader, 'Assets/Provider.shader', 'Shader "Authored" {}')]), ())
        self.asset.asset_bytes = self.text.replace(self.shader,
            '0000000000000000f000000000000000').replace('4800000', '46').encode()
        self.assertEqual(self.dependencies([self.task], [self.asset]), ())

    def test_only_bound_materials_and_supported_task_kinds(self):
        self.assertEqual(self.dependencies([], [self.asset]), ())
        task = copy.deepcopy(self.task)
        task['kind'] = 'UNRELATED'
        self.assertEqual(self.dependencies([task], [self.asset]), ())
        self.assertEqual(len(self.dependencies([self.task] * 2, [self.asset])), 1)

    def test_material_file_id_mismatch_is_not_a_name_match(self):
        self.task['material_bindings'][0]['file_id'] = '2100001'
        with self.assertRaises(ValueError):
            self.dependencies([self.task], [self.asset])

    def test_null_or_malformed_shader_is_not_a_deferred_provider(self):
        for text in (self.text.replace(self.shader, '0' * 32),
                     self.text.replace('4800000', '0'),
                     self.text.replace('4800000', '9223372036854775808')):
            with self.subTest(text=text):
                self.asset.asset_bytes = text.encode()
                with self.assertRaises(ValueError):
                    self.dependencies([self.task], [self.asset])


if __name__ == '__main__':
    unittest.main()
