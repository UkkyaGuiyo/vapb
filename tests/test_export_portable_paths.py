"""Public synthetic regressions for platform-independent staging destinations."""
import unittest

from unitypackage_blender_importer.export.staging import StagedUnityAsset, StagingTree


def asset(guid, path):
    return StagedUnityAsset(guid, path, b'm_Name: Body\n', f'guid: {guid}\n'.encode())


class PortablePathTests(unittest.TestCase):
    def test_casefold_collision(self):
        with self.assertRaisesRegex(ValueError, 'pathname collision'):
            StagingTree([asset('a' * 32, 'Assets/Majun/Body.mat'),
                         asset('b' * 32, 'Assets/majun/body.mat')])

    def test_unicode_normalization_collision(self):
        with self.assertRaisesRegex(ValueError, 'pathname collision'):
            StagingTree([asset('a' * 32, 'Assets/Majun/Caf\u00e9.mat'),
                         asset('b' * 32, 'Assets/Majun/Cafe\u0301.mat')])

    def test_reserved_components(self):
        for name in ('CON', 'con.mat', 'PRN', 'AUX', 'NUL', 'COM1', 'LPT9', 'COM\u00b9'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                asset('a' * 32, f'Assets/{name}/Body.mat')

    def test_invalid_components(self):
        for name in ('x<y', 'x>y', 'x:y', 'x"y', 'x|y', 'x?y', 'x*y',
                     'x\x01y', 'Body.', 'Body ', '', '.', '..'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                asset('a' * 32, f'Assets/{name}/Body.mat')

    def test_absolute_and_traversal_paths(self):
        for path in ('/Assets/Body.mat', 'C:/Assets/Body.mat',
                     'Assets/../Body.mat', 'Assets//Body.mat', ' Assets/Body.mat'):
            with self.subTest(path=path), self.assertRaises(ValueError):
                asset('a' * 32, path)

    def test_length_budgets(self):
        for path in ('Assets/' + 'a' * 121 + '.mat',
                     'Assets/' + '/'.join(['a' * 80] * 3) + '/Body.mat'):
            with self.subTest(path=path), self.assertRaises(ValueError):
                asset('a' * 32, path)

    def test_unicode_valid_and_payload_unchanged(self):
        entry = asset('a' * 32, 'Assets/マジュン/Materials/マジュン_Body.mat')
        tree = StagingTree([entry, entry])
        self.assertEqual(len(tree), 1)
        self.assertEqual(tree.get(entry.guid).asset_bytes, b'm_Name: Body\n')
        self.assertEqual(tree.get(entry.guid).meta_bytes, entry.meta_bytes)


if __name__ == '__main__':
    unittest.main()
