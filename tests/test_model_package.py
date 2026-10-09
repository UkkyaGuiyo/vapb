from __future__ import annotations

import hashlib
import io
from pathlib import Path
import tarfile
import tempfile
import unittest
from dataclasses import replace

from unitypackage_blender_importer.export.model_package import (
    ModelReplacement, SourcePackage, materialize_model_package,
)
from unitypackage_blender_importer.export.package_writer import UnityPackageWriter
from unitypackage_blender_importer.export.staging import StagedUnityAsset, StagingTree


A = "a" * 32
B = "b" * 32
C = "c" * 32


def sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def make_archive(path: Path, records: list[tuple[str, bytes]]) -> SourcePackage:
    with tarfile.open(path, "w:gz") as archive:
        for name, payload in records:
            info = tarfile.TarInfo(name)
            info.size = len(payload)
            archive.addfile(info, io.BytesIO(payload))
    return SourcePackage(path, sha(path.read_bytes()))


def fields(guid: str, path: str, asset: bytes | None, meta: bytes | None = None):
    result = [(f"{guid}/pathname", path.encode()), (f"{guid}/asset.meta", meta if meta is not None else f"guid: {guid}\n".encode())]
    if asset is not None:
        result.append((f"{guid}/asset", asset))
    return result


def replacement(source: SourcePackage, guid: str = A, **changes) -> ModelReplacement:
    values = dict(source_package_id="sha256:" + source.expected_sha256, source_guid=guid,
                  expected_asset_sha256=sha(b"old-model"), fbx_bytes=b"new-model",
                  rebind_payload={"renderer_mappings": [{"renderer_occurrence_id": "renderer-1", "source_mesh_file_id": "42"}]})
    values.update(changes)
    return ModelReplacement(**values)


class ModelPackageTests(unittest.TestCase):
    def test_material_path_moves_preserve_bytes_identity_repeat_and_package_readback(self):
        from unitypackage_blender_importer.export.material_naming import allocate_material_paths
        from unitypackage_blender_importer.export.raw_assets import RawAssetRepository
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            payloads = {B: b"Material:\n  m_Name: Body\n", C: b"Material:\n  m_Name: body\n"}
            source = make_archive(root / "source.unitypackage", fields(A, "Assets/Model.fbx", b"source-model")
                                  + fields(B, "Assets/First.mat", payloads[B])
                                  + fields(C, "Assets/Second.mat", payloads[C]))
            original = source.path.read_bytes()
            rows = [{'guid': guid, 'name': name, 'owners': {}} for guid, name in ((B, 'Body'), (C, 'body'))]
            destinations = allocate_material_paths(rows)
            self.assertTrue(all('/Unassigned/Materials/' in path and '__' in path for path in destinations.values()))
            for order in (rows, list(reversed(rows))):
                tree, manifest = materialize_model_package([source], [], generator_version='test', blender_version='test',
                    material_paths=allocate_material_paths(order))
                self.assertEqual(tree.get(A).pathname, 'Assets/Model.fbx')
                for guid, payload in payloads.items():
                    self.assertEqual((tree.get(guid).pathname, tree.get(guid).asset_bytes, tree.get(guid).meta_bytes),
                                     (destinations[guid], payload, f'guid: {guid}\n'.encode()))
                self.assertEqual({item['desired_export_path'] for item in manifest.material_mappings}, set(destinations.values()))
                self.assertTrue(all(item['operation'] == 'MOVE' and item['path_status'] == 'MOVE'
                                    and item['guid_decision'] == 'PRESERVE_SOURCE_GUID' for item in manifest.material_mappings))
                output = root / ('output-' + str(len(list(root.glob('output-*')))) + '.unitypackage')
                UnityPackageWriter().write(tree, output)
                readback = {asset.guid: asset for asset in RawAssetRepository(output).read_all()}
                for guid in payloads:
                    self.assertEqual((readback[guid].pathname, readback[guid].asset_bytes, readback[guid].meta_bytes),
                                     (destinations[guid], payloads[guid], f'guid: {guid}\n'.encode()))
            self.assertEqual(source.path.read_bytes(), original)

    def test_material_destinations_reject_unknown_or_non_material_assets(self):
        with tempfile.TemporaryDirectory() as temp:
            source = make_archive(Path(temp) / 'source.unitypackage', fields(A, 'Assets/Model.fbx', b'source-model'))
            for guid in (A, B):
                with self.subTest(guid=guid), self.assertRaises(ValueError):
                    materialize_model_package([source], [], generator_version='test', blender_version='test',
                        material_paths={guid: 'Assets/VAPBExport/Unassigned/Materials/Body.mat'})

    def test_working_texture_preserves_identity_meta_and_other_source_assets(self):
        from unitypackage_blender_importer.export.model_package import TextureReplacement
        with tempfile.TemporaryDirectory() as temp:
            meta = f"guid: {B}\nTextureImporter:\n  sRGBTexture: 1\n".encode()
            source = make_archive(Path(temp) / "source.unitypackage",
                fields(A, "Assets/Model.fbx", b"old-model") + fields(B, "Assets/Color.png", b"original-png", meta))
            before = source.path.read_bytes()
            texture = TextureReplacement("sha256:" + source.expected_sha256, B, sha(b"original-png"), b"edited-png")
            tree, manifest = materialize_model_package([source], [], generator_version="test", blender_version="test",
                texture_replacements=[texture])
            self.assertEqual(source.path.read_bytes(), before)
            self.assertEqual(tree.get(A).asset_bytes, b"old-model")
            self.assertEqual((tree.get(B).asset_bytes, tree.get(B).meta_bytes, tree.get(B).pathname),
                             (b"edited-png", meta, "Assets/Color.png"))
            item, = manifest.texture_mappings
            self.assertEqual((item["operation"], item["strategy"]), ("MODIFY", "PRESERVE_META_REPLACE_BYTES"))
            self.assertEqual(item["source_identity"]["source_sha256"], sha(b"original-png"))
            self.assertEqual(item["postimport_identity"]["content_sha256"], sha(b"edited-png"))

    def test_working_texture_rejects_stale_ambiguous_or_wrong_source(self):
        from unitypackage_blender_importer.export.model_package import TextureReplacement
        with tempfile.TemporaryDirectory() as temp:
            source = make_archive(Path(temp) / "source.unitypackage",
                fields(A, "Assets/Model.fbx", b"old-model") +
                fields(B, "Assets/Color.png", b"original-png", f"guid: {B}\nTextureImporter:\n".encode()))
            texture = TextureReplacement("sha256:" + source.expected_sha256, B, sha(b"original-png"), b"edited-png")
            for replacements in ([texture, texture], [replace(texture, expected_asset_sha256="0" * 64)],
                                 [replace(texture, encoded_bytes=b"")], [replace(texture, encoded_bytes=b"original-png")],
                                 [replace(texture, source_guid=A, expected_asset_sha256=sha(b"old-model"))],
                                 [replace(texture, source_package_id="sha256:" + "0" * 64)],
                                 [replace(texture, source_guid=C)]):
                with self.subTest(replacements=replacements), self.assertRaises(ValueError):
                    materialize_model_package([source], [], generator_version="test", blender_version="test",
                        texture_replacements=replacements)

    def test_source_closure_exact_preservation_and_typed_model_modification(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            model_meta = f"guid: {A}\nModelImporter:\n  rig: 1\n".encode()
            source = make_archive(root / "source.unitypackage", fields(A, "Assets/Model.fbx", b"old-model", model_meta)
                                  + fields(B, "Assets/Other.prefab", b"unchanged")
                                  + fields(C, "Assets/Folder", None, f"guid: {C}\nfolderAsset: yes\n".encode()))
            tree, manifest = materialize_model_package([source], [replacement(source)], generator_version="test", blender_version="test")
            self.assertEqual(len(tree), 3)
            self.assertEqual(tree.get(A).asset_bytes, b"new-model")
            self.assertEqual(tree.get(A).meta_bytes, model_meta)
            self.assertEqual(tree.get(A).pathname, "Assets/Model.fbx")
            self.assertEqual(tree.get(B).asset_bytes, b"unchanged")
            self.assertEqual(tree.get(B).meta_bytes, f"guid: {B}\n".encode())
            self.assertEqual(tree.get(C).asset_bytes, b"")
            changed = next(item for item in manifest.export_assets if item["source_identity"]["source_guid"] == A)
            self.assertEqual((changed["operation"], changed["strategy"]), ("MODIFY", "PRESERVE_META_REPLACE_BYTES"))
            self.assertEqual(changed["source_identity"]["source_sha256"], sha(b"old-model"))
            self.assertEqual(changed["reference_stability"], "POSTIMPORT_REBIND_REQUIRED")
            self.assertEqual(changed["postimport_tasks"], ["REBIND_MODEL_SUBASSET", "REBIND_RENDERER_MESH"])
            self.assertEqual(manifest.warnings, ("CONSERVATIVE_WHOLE_SOURCE_CLOSURE",))
            self.assertEqual(len(manifest.renderer_mappings), 1)
            output = root / "out.unitypackage"
            UnityPackageWriter().write(tree, output)
            with self.assertRaises(FileExistsError):
                UnityPackageWriter().write(tree, output)

    def test_rejects_stale_hashes_invalid_replacement_and_ambiguous_provider(self):
        with tempfile.TemporaryDirectory() as temp:
            source = make_archive(Path(temp) / "source.unitypackage", fields(A, "Assets/Model.fbx", b"old-model"))
            good = replacement(source)
            cases = [([SourcePackage(source.path, "0" * 64)], [good]),
                     ([source], [replacement(source, expected_asset_sha256="0" * 64)]),
                     ([source], [replacement(source, fbx_bytes=b"")]),
                     ([source], [replacement(source, rebind_payload={})]),
                     ([source], [replacement(source, fbx_bytes=b"old-model")]),
                     ([source], [replacement(source, rebind_payload={"renderer_mappings": [{"source_guid": B}]})]),
                     ([source], [good, good]),
                     ([source], [replacement(source, source_guid=B)])]
            for sources, replacements in cases:
                with self.subTest(case=(sources, replacements)), self.assertRaises(ValueError):
                    materialize_model_package(sources, replacements, generator_version="t", blender_version="t")

    def test_rejects_duplicate_fields_incomplete_assets_and_cross_package_collisions(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            clean = make_archive(root / "clean.unitypackage", fields(A, "Assets/Model.fbx", b"old-model"))
            malformed = [
                fields(A, "Assets/Model.fbx", b"old-model") + [(f"{A}/asset", b"other")],
                fields(A, "Assets/Model.fbx", None),
                fields(A, "Assets/Model.fbx", None, f"guid: {A}\nfolderAsset: true\n".encode()),
            ]
            for index, records in enumerate(malformed):
                bad = make_archive(root / f"bad{index}.unitypackage", records)
                with self.assertRaises(ValueError):
                    materialize_model_package([bad], [replacement(bad)], generator_version="t", blender_version="t")
            collision = make_archive(root / "collision.unitypackage", fields(A, "Assets/Other.fbx", b"old-model"))
            with self.assertRaises(ValueError):
                materialize_model_package([clean, collision], [replacement(clean)], generator_version="t", blender_version="t")
            path_collision = make_archive(root / "path-collision.unitypackage", fields(B, "Assets/Model.fbx", b"other"))
            with self.assertRaises(ValueError):
                materialize_model_package([clean, path_collision], [replacement(clean)], generator_version="t", blender_version="t")

    def test_rejects_non_fbx_and_accepts_meta_only_folder(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            non_fbx = make_archive(root / "non-fbx.unitypackage", fields(A, "Assets/Model.prefab", b"old-model"))
            with self.assertRaises(ValueError):
                materialize_model_package([non_fbx], [replacement(non_fbx)], generator_version="t", blender_version="t")
            source = make_archive(root / "folder.unitypackage", fields(A, "Assets/Model.fbx", b"old-model")
                                  + fields(B, "Assets/Folder", None, f"guid: {B}\nfolderAsset: yes\n".encode()))
            tree, _ = materialize_model_package([source], [replacement(source)], generator_version="t", blender_version="t")
            self.assertEqual(tree.get(B).asset_bytes, b"")


if __name__ == "__main__":
    unittest.main()
