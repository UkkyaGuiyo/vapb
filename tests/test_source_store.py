from __future__ import annotations

import hashlib
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from unitypackage_blender_importer.unity.source_store import _fingerprint, archive_source


class SourceStoreTests(unittest.TestCase):
    def test_creation_time_drift_is_not_content_mutation(self):
        fields = dict(st_dev=1, st_ino=2, st_size=3, st_mtime_ns=4)
        from_handle = SimpleNamespace(**fields, st_ctime_ns=5)
        from_path = SimpleNamespace(**fields, st_ctime_ns=6)
        self.assertEqual(_fingerprint(from_handle), _fingerprint(from_path))

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "incoming.unitypackage"
        self.storage = self.root / "source-store"
        self.payload = b"synthetic raw archive bytes\x00\xff"
        self.source.write_bytes(self.payload)
        self.digest = hashlib.sha256(self.payload).hexdigest()

    def test_archives_exact_bytes_without_changing_source(self):
        result = archive_source(self.source, self.storage, self.digest)
        self.assertEqual(self.storage / f"{self.digest}.unitypackage", result)
        self.assertEqual(self.payload, result.read_bytes())
        self.assertEqual(self.payload, self.source.read_bytes())

    def test_reuses_verified_existing_snapshot(self):
        first = archive_source(self.source, self.storage, self.digest)
        with patch("unitypackage_blender_importer.unity.source_store.shutil.copyfileobj", side_effect=AssertionError("unexpected copy")):
            second = archive_source(self.source, self.storage, self.digest)
        self.assertEqual(first, second)

    def test_rejects_invalid_or_incorrect_digest_without_publishing(self):
        for digest in ("../x", "a" * 63, "z" * 64, "0" * 64):
            with self.subTest(digest=digest):
                with self.assertRaises(ValueError):
                    archive_source(self.source, self.storage, digest)
        self.assertEqual([], list(self.storage.iterdir()))

    def test_rejects_corrupted_existing_snapshot_without_overwrite(self):
        self.storage.mkdir()
        destination = self.storage / f"{self.digest}.unitypackage"
        destination.write_bytes(b"different")
        with self.assertRaises(ValueError):
            archive_source(self.source, self.storage, self.digest)
        self.assertEqual(b"different", destination.read_bytes())
        self.assertEqual([destination], list(self.storage.iterdir()))

    def test_copy_failure_removes_partial_temporary(self):
        def fail_after_partial_copy(source, target, **kwargs):
            target.write(source.read(4))
            raise OSError("synthetic copy failure")

        with patch("unitypackage_blender_importer.unity.source_store.shutil.copyfileobj", fail_after_partial_copy):
            with self.assertRaises(OSError):
                archive_source(self.source, self.storage, self.digest)
        self.assertEqual([], list(self.storage.iterdir()))

    def test_source_mutation_during_copy_is_rejected(self):
        def mutate_source_during_copy(source, target, **kwargs):
            target.write(source.read())
            self.source.write_bytes(b"replaced while copying")

        with patch("unitypackage_blender_importer.unity.source_store.shutil.copyfileobj", mutate_source_during_copy):
            with self.assertRaises(ValueError):
                archive_source(self.source, self.storage, self.digest)
        self.assertEqual([], list(self.storage.iterdir()))

    def test_concurrent_publish_never_overwrites_other_file(self):
        real_link = os.link
        destination = self.storage / f"{self.digest}.unitypackage"
        link_calls = []

        def race(source, target):
            link_calls.append((source, target))
            destination.write_bytes(b"other completed content")
            return real_link(source, target)

        with patch("unitypackage_blender_importer.unity.source_store.os.link", race):
            with self.assertRaises(ValueError):
                archive_source(self.source, self.storage, self.digest)
        self.assertEqual(1, len(link_calls))
        self.assertEqual(b"other completed content", destination.read_bytes())
        self.assertEqual([destination], list(self.storage.iterdir()))


if __name__ == "__main__":
    unittest.main()
