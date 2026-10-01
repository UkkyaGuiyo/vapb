"""Public controls for exact source-Oracle staging; no Unity process required."""
import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from unitypackage_blender_importer.tests.stage_corpus_source_assets import StageError, stage


class SourceAssetStagingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        (self.folder / 'inputs').mkdir()
        self.source = self.folder / 'inputs' / 'Public.unitypackage'
        self.guid = '1' * 32
        self.project = self.folder / 'Oracle'
        self.output_lock = self.folder / 'staging.json'
        self.output_context = self.folder / 'runtime.json'

    def package(self, path=None, *, pathname='Assets/Public.prefab', payload=b'exact prefab'):
        path = path or self.source
        with tarfile.open(path, 'w:gz') as archive:
            rows = [(self.guid, pathname, payload, False),
                    ('2' * 32, 'Assets/PublicMarker.cs', b'// exact script\n', False),
                    ('3' * 32, 'Assets/EmptyFolder', b'', True)]
            for guid, unity_path, value, folder in rows:
                fields = [('pathname', unity_path.encode()),
                          ('asset.meta', (('folderAsset: yes\n' if folder else '') + 'guid: ' + guid + '\n').encode())]
                if not folder:
                    fields.append(('asset', value))
                for field, data in fields:
                    info = tarfile.TarInfo(guid + '/' + field)
                    info.size = len(data)
                    archive.addfile(info, io.BytesIO(data))
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def run_stage(self, paths=None, hashes=None):
        paths = paths or [str(self.source)]
        hashes = hashes or {str(self.source): hashlib.sha256(self.source.read_bytes()).hexdigest()}
        return stage(dict(package_paths=paths, prefab_guids=[self.guid]),
                     dict(package_hashes=hashes), self.project, self.output_lock, self.output_context)

    def test_all_payloads_scripts_and_folder_meta_are_exact(self):
        original = self.package()
        counts = self.run_stage()
        self.assertEqual(counts['assets'], 3)
        self.assertEqual((self.project / 'Assets/PublicMarker.cs').read_bytes(), b'// exact script\n')
        self.assertTrue((self.project / 'Assets/EmptyFolder').is_dir())
        self.assertEqual(hashlib.sha256(self.source.read_bytes()).hexdigest(), original)
        lock = json.loads(self.output_lock.read_text())
        for row in lock['files']:
            self.assertEqual(hashlib.sha256((self.project / row['unity_path']).read_bytes()).hexdigest(), row['sha256'])
        runtime = json.loads(self.output_context.read_text())
        self.assertEqual(runtime['capture_mode'], 'EXACT_ASSET_EXTRACTION_CAPTURE')
        self.assertEqual(runtime['native_import_status'], 'NOT_PASS')

    def test_conflicting_guid_rejected_before_copy(self):
        first = self.package()
        second_path = self.folder / 'inputs' / 'Other.unitypackage'
        second = self.package(second_path, payload=b'conflicting prefab')
        with self.assertRaises(StageError):
            self.run_stage([str(self.source), str(second_path)], {str(self.source): first, str(second_path): second})
        self.assertFalse(self.project.exists())

    def test_path_escape_rejected_before_copy(self):
        self.package(pathname='Assets/../Escape.prefab')
        with self.assertRaises(StageError):
            self.run_stage()
        self.assertFalse(self.project.exists())

    def test_source_revision_mismatch_rejected_before_copy(self):
        self.package()
        with self.assertRaises(StageError):
            self.run_stage(hashes={str(self.source): '0' * 64})
        self.assertFalse(self.project.exists())


if __name__ == '__main__':
    unittest.main()
