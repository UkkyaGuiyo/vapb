import unittest
import hashlib
import json
from unitypackage_blender_importer.export.material_naming import allocate_material_paths


def row(guid, owners=(), name='Body'):
    return {'guid': guid, 'name': name, 'owners': dict(owners)}


class MaterialNamingTests(unittest.TestCase):
    def test_owner_shared_unassigned(self):
        rows = [row('a'*32, [('owner-a', 'Majun')]),
                row('b'*32, [('owner-b', 'Other')]),
                row('c'*32, [('owner-a', 'Majun'), ('owner-b', 'Other')], 'SharedSkin'),
                row('d'*32)]
        paths = allocate_material_paths(rows)
        self.assertEqual(paths['a'*32], 'Assets/VAPBExport/Majun/Materials/Majun_Body.mat')
        self.assertEqual(paths['b'*32], 'Assets/VAPBExport/Other/Materials/Other_Body.mat')
        self.assertEqual(paths['c'*32], 'Assets/VAPBExport/Shared/Materials/SharedSkin.mat')
        self.assertEqual(paths['d'*32], 'Assets/VAPBExport/Unassigned/Materials/Body.mat')

    def test_symmetric_deterministic_collision(self):
        rows = [row('a'*32, [('owner', 'Majun')]), row('b'*32, [('owner', 'Majun')])]
        paths = allocate_material_paths(rows)
        self.assertEqual(paths, allocate_material_paths(list(reversed(rows))))
        self.assertEqual(paths, allocate_material_paths(rows))
        self.assertTrue(all('/Majun_Body__' in p for p in paths.values()))
        self.assertEqual(len(set(paths.values())), 2)

    def test_portable_collision(self):
        for names in [('Body', 'body'), ('Caf\u00e9', 'Cafe\u0301')]:
            paths = allocate_material_paths([row('a'*32, name=names[0]), row('b'*32, name=names[1])])
            self.assertTrue(all('__' in p for p in paths.values()))

    def test_invalid_human_labels_are_safe(self):
        paths = allocate_material_paths([row('a'*32, [('owner', 'CON')], 'x<>:*?'),
                                         row('b'*32, name='.'), row('c'*32, name='a'*500)])
        from unitypackage_blender_importer.export.staging import normalize_unity_path
        for path in paths.values():
            self.assertEqual(normalize_unity_path(path), path)

    def test_removing_usage_becomes_unassigned(self):
        self.assertIn('/Majun/', allocate_material_paths([row('a'*32, [('owner', 'Majun')])])['a'*32])
        self.assertIn('/Unassigned/', allocate_material_paths([row('a'*32)])['a'*32])

    def test_owner_persistence_identity_revision_and_late_provider(self):
        from unitypackage_blender_importer.blender.material_owner_usage import (
            capture_scene_owner_usage, proven_owners)
        package = 'sha256:' + 'a'*64
        payload = b'm_Name: Body\n'
        material = {'unity_source_package_id': package, 'unity_material_guid': 'b'*32,
                    'unity_material_file_id': '-2100000',
                    '_vapb_source_material_sha256': hashlib.sha256(payload).hexdigest()}
        record = {'root_package_id': 'sha256:'+'c'*64, 'root_member_id': 'd'*32,
                  'root_asset_guid': 'd'*32, 'root_revision_sha256': 'e'*64,
                  'source_revision_sha256': 'e'*64, 'occurrence_id': 'synthetic-occurrence',
                  'material_status': 'EXACT', 'materials': {0: {'source_package_id': 'sha256:'+'c'*64,
                  'guid': 'b'*32, 'file_id': -2100000}}}
        root = {'_vapb_material_owner_label': 'Majun',
                '_vapb_renderer_occurrences': json.dumps({'records': [record]})}
        capture_scene_owner_usage([root], [])  # Provider is not present yet.
        capture_scene_owner_usage([root], [material])
        del root  # Geometry/root removal cannot remove the Material evidence.
        material = json.loads(json.dumps(material))  # Persistence representation.
        owners = proven_owners(material, package, 'b'*32, '-2100000', payload)
        self.assertEqual(list(owners.values()), ['Majun'])
        self.assertEqual(proven_owners(material, package, 'b'*32, '-2100000', payload+b'x'), {})
        self.assertEqual(proven_owners(material, 'sha256:'+'f'*64, 'b'*32, '-2100000', payload), {})
