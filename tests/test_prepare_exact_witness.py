# SPDX-License-Identifier: GPL-3.0-or-later
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest


SCRIPT = Path(__file__).parent / 'unity_hierarchy_probe' / 'prepare_exact_witness.py'


class PrepareExactWitnessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.package = self.root / 'source.unitypackage'
        self.project = self.root / 'project'
        self.guids = ['1' * 32, '2' * 32]

    def fixture(self, count=2, duplicate=False):
        with tarfile.open(self.package, 'w:gz') as archive:
            for index, guid in enumerate(self.guids[:count]):
                for name, payload in [('pathname', ('Assets/SameName%d.fbx' % index).encode()),
                                      ('asset', ('exact model %d' % index).encode()),
                                      ('asset.meta', ('guid: %s\n' % guid).encode())]:
                    member = tarfile.TarInfo(guid + '/' + name)
                    member.size = len(payload)
                    archive.addfile(member, io.BytesIO(payload))
            if duplicate:
                member = tarfile.TarInfo(self.guids[0] + '/pathname')
                payload = b'Assets/Duplicate.fbx'
                member.size = len(payload)
                archive.addfile(member, io.BytesIO(payload))
        self.original = self.package.read_bytes()
        self.sha = hashlib.sha256(self.original).hexdigest()

    def run_prepare(self, *selection):
        return subprocess.run([sys.executable, str(SCRIPT), str(self.package), self.sha,
                               str(self.project), *selection], capture_output=True, text=True)

    def test_explicit_guid_selects_exact_model_from_multi_fbx(self):
        self.fixture()
        result = self.run_prepare(self.guids[1])
        self.assertEqual(result.returncode, 0, result.stderr)
        identity = json.loads((self.project / 'ExactSourceIdentity.json').read_text())
        self.assertEqual(identity['model_guid'], self.guids[1])
        self.assertEqual(identity['package_sha256'], self.sha)
        self.assertEqual((self.project / 'Source.fbx').read_bytes(), b'exact model 1')
        self.assertEqual((self.project / 'Source.fbx.meta').read_bytes(), ('guid: %s\n' % self.guids[1]).encode())
        self.assertEqual(identity['source_fbx_sha256'], hashlib.sha256(b'exact model 1').hexdigest())
        self.assertEqual((self.project / 'ExactPackage.unitypackage').read_bytes(), self.original)
        self.assertEqual(self.package.read_bytes(), self.original)

    def test_legacy_single_fbx_invocation_still_works(self):
        self.fixture(count=1)
        result = self.run_prepare()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads((self.project / 'ExactSourceIdentity.json').read_text())['model_guid'], self.guids[0])

    def test_multi_fbx_without_selection_is_rejected(self):
        self.fixture()
        result = self.run_prepare()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('EXACT_FBX_AMBIGUOUS', result.stderr)
        self.assertFalse(self.project.exists())

    def test_malformed_and_missing_guid_are_rejected_before_output(self):
        self.fixture()
        for guid, reason in [('wrong', 'MODEL_GUID_INVALID'), ('A'*32, 'MODEL_GUID_INVALID'),
                             ('3'*32, 'MODEL_GUID_NOT_FOUND')]:
            result = self.run_prepare(guid)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(reason, result.stderr)
            self.assertFalse(self.project.exists())
        self.assertEqual(self.package.read_bytes(), self.original)

    def test_duplicate_asset_identity_is_rejected(self):
        self.fixture(duplicate=True)
        result = self.run_prepare(self.guids[0])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('PACKAGE_MEMBER_DUPLICATE', result.stderr)
        self.assertFalse(self.project.exists())


if __name__ == '__main__':
    unittest.main()
