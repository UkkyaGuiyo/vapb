from __future__ import annotations

import hashlib
import os
import tarfile
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from unitypackage_blender_importer.export.fbx_export import FBX_EXPORT_PRESET, export_fbx
from unitypackage_blender_importer.export.asset_plan import plan_assets
from unitypackage_blender_importer.export.material_export import patch_material_texture_guid
from unitypackage_blender_importer.export.package_writer import UnityPackageWriter
from unitypackage_blender_importer.export.raw_assets import RawAssetRepository
from unitypackage_blender_importer.export.staging import StagedUnityAsset, StagingTree
from unitypackage_blender_importer.export.staging import stage_asset_plan
from unitypackage_blender_importer.export.texture_export import materialize_texture
from unitypackage_blender_importer.export.semantic_graph import EdgeType, GraphNode, NodeType, Provenance, SemanticGraph
from unitypackage_blender_importer.unity.package_reader import UnityPackageReader


GUID_A = "a" * 32
GUID_B = "b" * 32


class ExportMaterializationTests(unittest.TestCase):
    def test_writer_does_not_overwrite_a_racing_output(self):
        tree = StagingTree([StagedUnityAsset(GUID_A, "Assets/A.bin", b"data", b"guid: " + GUID_A.encode())])
        link = os.link
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "result.unitypackage"
            def race(source, destination):
                output.write_bytes(b"other completed output")
                return link(source, destination)
            with patch('unitypackage_blender_importer.export.package_writer.os.link', race):
                with self.assertRaises(FileExistsError):
                    UnityPackageWriter().write(tree, output)
            self.assertEqual(b"other completed output", output.read_bytes())
            self.assertEqual([output], list(Path(temp).iterdir()))

    def test_writer_failure_leaves_no_final_or_staging_file(self):
        tree = StagingTree([StagedUnityAsset(GUID_A, "Assets/A.bin", b"data", b"guid: " + GUID_A.encode())])
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "result.unitypackage"
            with patch.object(tarfile.TarFile, "addfile", side_effect=OSError("synthetic disk failure")):
                with self.assertRaises(OSError):
                    UnityPackageWriter().write(tree, output)
            self.assertFalse(output.exists())
            self.assertEqual([], list(Path(temp).iterdir()))

    def test_writer_publishes_only_after_archive_is_complete(self):
        tree = StagingTree([StagedUnityAsset(GUID_A, "Assets/A.bin", b"data", b"guid: " + GUID_A.encode())])
        original = tarfile.TarFile.addfile
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "result.unitypackage"
            def observe(archive, *args, **kwargs):
                self.assertFalse(output.exists(), "Incomplete archive is already visible at final path")
                return original(archive, *args, **kwargs)
            with patch.object(tarfile.TarFile, "addfile", observe):
                UnityPackageWriter().write(tree, output)
            self.assertEqual([output], list(Path(temp).iterdir()))
            with self.assertRaises(FileExistsError):
                UnityPackageWriter().write(tree, output)

    def test_staging_preserves_bytes_and_rejects_unsafe_path(self):
        tree = StagingTree()
        asset = StagedUnityAsset(GUID_A, "Assets/VAPB/テスト/モデル.txt", b"payload", b"guid: " + GUID_A.encode("ascii") + b"\n")
        tree.add(asset)
        self.assertEqual(tree.get(GUID_A).content_hash, hashlib.sha256(b"payload").hexdigest())
        with self.assertRaises(ValueError):
            tree.add(StagedUnityAsset(GUID_B, "../../evil", b"x", b"y"))

    def test_staging_rejects_duplicate_path_and_guid_conflict(self):
        tree = StagingTree()
        tree.add(StagedUnityAsset(GUID_A, "Assets/A.txt", b"one", b"guid: " + GUID_A.encode()))
        with self.assertRaises(ValueError):
            tree.add(StagedUnityAsset(GUID_B, "Assets/A.txt", b"two", b"guid: " + GUID_B.encode()))
        with self.assertRaises(ValueError):
            tree.add(StagedUnityAsset(GUID_A, "Assets/B.txt", b"different", b"guid: " + GUID_A.encode()))

    def test_raw_repository_preserves_asset_and_meta_bytes(self):
        with tempfile.TemporaryDirectory(prefix="vapb_raw_") as temp:
            source = Path(temp) / "source.unitypackage"
            tree = StagingTree([StagedUnityAsset(GUID_A, "Assets/A.bin", b"\x00\x01binary", b"guid: " + GUID_A.encode())])
            UnityPackageWriter().write(tree, source)
            raw = RawAssetRepository(source).read(GUID_A)
            self.assertEqual(raw.asset_bytes, b"\x00\x01binary")
            self.assertEqual(raw.meta_bytes, b"guid: " + GUID_A.encode())

    def test_material_patch_changes_only_matching_object_reference(self):
        old = "a" * 32
        new = "b" * 32
        source = ("m_Shader: {fileID: 1, guid: " + old + ", type: 3}\n"
                  "m_SavedProperties:\n  m_TexEnvs:\n  - _MainTex:\n"
                  "      m_Texture: {fileID: 2800000, guid: " + old + ", type: 3}\n"
                  "    _BumpMap:\n      m_Texture: {fileID: 2800000, guid: " + old + ", type: 3}\n")
        patched = patch_material_texture_guid(source.encode(), old, new, property_name="_MainTex").decode()
        self.assertIn("guid: " + new, patched)
        self.assertIn("m_Shader: {fileID: 1, guid: " + old, patched)
        self.assertIn("_BumpMap:\n      m_Texture: {fileID: 2800000, guid: " + old, patched)

    def test_material_patch_fails_closed_for_non_texture_reference(self):
        old, new = "a" * 32, "b" * 32
        shader_only = b"m_Shader: {fileID: 1, guid: " + old.encode() + b", type: 3}\n"
        with self.assertRaises(ValueError):
            patch_material_texture_guid(shader_only, old, new)

    def test_material_patch_rejects_same_key_outside_saved_properties(self):
        old, new = "a" * 32, "b" * 32
        source = ("OtherBlock:\n  m_TexEnvs:\n  - _MainTex:\n"
                  "      m_Texture: {fileID: 2800000, guid: " + old + ", type: 3}\n")
        with self.assertRaises(ValueError):
            patch_material_texture_guid(source.encode(), old, new, property_name="_MainTex")

    def test_writer_round_trip_and_repeated_hash_are_deterministic(self):
        tree = StagingTree([
            StagedUnityAsset(GUID_A, "Assets/VAPB/テスト/モデル.txt", b"payload", b"guid: " + GUID_A.encode()),
            StagedUnityAsset(GUID_B, "Assets/VAPB/テスト/画像.png", b"PNG synthetic", b"guid: " + GUID_B.encode()),
        ])
        with tempfile.TemporaryDirectory(prefix="vapb_writer_") as temp:
            first = Path(temp) / "first.unitypackage"
            second = Path(temp) / "second.unitypackage"
            UnityPackageWriter().write(tree, first)
            UnityPackageWriter().write(tree, second)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            records = UnityPackageReader(first).inspect()
            self.assertEqual([item[0] for item in records], [GUID_A, GUID_B])
            self.assertEqual([item[1] for item in records], ["Assets/VAPB/テスト/モデル.txt", "Assets/VAPB/テスト/画像.png"])

    def test_writer_round_trip_extracts_exact_payload_and_meta(self):
        tree = StagingTree([StagedUnityAsset(GUID_A, "Assets/A.bin", b"\x00payload", b"guid: " + GUID_A.encode())])
        with tempfile.TemporaryDirectory(prefix="vapb_extract_") as temp:
            package = Path(temp) / "roundtrip.unitypackage"
            output = Path(temp) / "extracted"
            UnityPackageWriter().write(tree, package)
            result = UnityPackageReader(package).extract(output)
            self.assertEqual(result.errors, [])
            self.assertEqual((output / "Assets/A.bin").read_bytes(), b"\x00payload")
            self.assertEqual((output / "Assets/A.bin.meta").read_bytes(), b"guid: " + GUID_A.encode())

    def test_writer_uses_meta_only_record_for_folder_assets(self):
        folder_guid = "d" * 32
        tree = StagingTree([StagedUnityAsset(
            folder_guid, "Assets/Folder", b"", b"guid: " + folder_guid.encode() + b"\nfolderAsset: yes\n", asset_type="Folder"
        )])
        with tempfile.TemporaryDirectory(prefix="vapb_folder_") as temp:
            package = Path(temp) / "folder.unitypackage"
            output = Path(temp) / "out"
            UnityPackageWriter().write(tree, package)
            with tarfile.open(package, "r:*") as archive:
                names = archive.getnames()
            self.assertNotIn(folder_guid + "/asset", names)
            self.assertIn(folder_guid + "/asset.meta", names)
            result = UnityPackageReader(package).extract(output)
            self.assertEqual(result.errors, [])
            self.assertTrue((output / "Assets/Folder").is_dir())

    def test_texture_materialization_preserves_raw_bytes_and_meta(self):
        staged = materialize_texture(
            guid=GUID_A,
            pathname="Assets/Textures/albedo.png",
            asset_bytes=b"raw-image",
            meta_bytes=b"guid: " + GUID_A.encode(),
        )
        self.assertEqual(staged.asset_bytes, b"raw-image")
        self.assertEqual(staged.meta_bytes, b"guid: " + GUID_A.encode())
        self.assertEqual(staged.strategy, "PRESERVE_VERBATIM")

    def test_staging_materializes_only_valid_non_deleted_plan_assets(self):
        class Item:
            def __init__(self, node_id, operation):
                self.node_id = node_id
                self.operation = operation
                self.export_identity = {"export_guid": GUID_A}
                self.desired_export_path = "Assets/A.bin"
                self.guid_decision = "PRESERVE_SOURCE_GUID"

        class Plan:
            errors = ()
            collisions = ()
            assets = (Item("a", "PRESERVE"), Item("deleted", "DELETE"))

        tree = stage_asset_plan(
            Plan(),
            lambda item: StagedUnityAsset(GUID_A, "Assets/A.bin", b"payload", b"guid: " + GUID_A.encode()),
        )
        self.assertEqual(len(tree), 1)

    def test_staging_rejects_meta_guid_mismatch(self):
        with self.assertRaises(ValueError):
            StagingTree([StagedUnityAsset(GUID_A, "Assets/A.bin", b"x", b"guid: " + GUID_B.encode())])

    def test_staging_rejects_payload_identity_mismatch(self):
        class Item:
            operation = "PRESERVE"
            export_identity = {"export_guid": GUID_A}
            desired_export_path = "Assets/A.bin"
            guid_decision = "PRESERVE_SOURCE_GUID"

        class Plan:
            errors = ()
            collisions = ()
            assets = (Item(),)

        with self.assertRaises(ValueError):
            stage_asset_plan(Plan(), lambda item: StagedUnityAsset(GUID_B, "Assets/B.bin", b"x", b"guid: " + GUID_B.encode()))

    def test_staging_uses_source_path_for_preserved_plan_asset(self):
        class Item:
            operation = "PRESERVE"
            export_identity = {"export_guid": GUID_A}
            source_identity = {"source_guid": GUID_A, "source_path": "Assets/Original.bin"}
            desired_export_path = ""
            guid_decision = "PRESERVE_SOURCE_GUID"

        class Plan:
            errors = ()
            collisions = ()
            assets = (Item(),)

        tree = stage_asset_plan(
            Plan(),
            lambda item: StagedUnityAsset(GUID_A, "Assets/Original.bin", b"x", b"guid: " + GUID_A.encode()),
        )
        self.assertEqual(tree.entries[0].pathname, "Assets/Original.bin")

    def test_actual_create_plan_without_allocated_guid_is_rejected(self):
        graph = SemanticGraph()
        graph.add_node(GraphNode("root", NodeType.EXPORT_ROOT, Provenance("EXACT")))
        graph.add_node(GraphNode("created", NodeType.TEXTURE_ASSET, Provenance("DERIVED"), {"operation": "CREATE"}))
        graph.add_edge("root", "created", EdgeType.ROOT_CONTAINS_OBJECT)
        plan = plan_assets(graph, ["root"])
        with self.assertRaises(ValueError):
            stage_asset_plan(plan, lambda item: StagedUnityAsset(GUID_A, "Assets/Created.png", b"x", b"guid: " + GUID_A.encode()))

    def test_actual_move_plan_without_destination_path_is_rejected(self):
        graph = SemanticGraph()
        graph.add_node(GraphNode("root", NodeType.EXPORT_ROOT, Provenance("EXACT")))
        graph.add_node(GraphNode(
            "moved", NodeType.MATERIAL_ASSET,
            Provenance("EXACT", "package", GUID_A, 1, "Assets/Old.mat"),
            {"operation": "MOVE"},
        ))
        graph.add_edge("root", "moved", EdgeType.ROOT_CONTAINS_OBJECT)
        plan = plan_assets(graph, ["root"])
        with self.assertRaises(ValueError):
            stage_asset_plan(plan, lambda item: StagedUnityAsset(GUID_A, "Assets/Old.mat", b"x", b"guid: " + GUID_A.encode()))

    def test_fbx_preset_is_explicit_and_export_calls_public_operator(self):
        calls = []

        class Ops:
            class export_scene:
                @staticmethod
                def fbx(**kwargs):
                    calls.append(kwargs)
                    return {"FINISHED"}

        class FakeBpy:
            ops = Ops()
            context = type("Context", (), {"selected_objects": []})()

        with tempfile.TemporaryDirectory(prefix="vapb_fbx_") as temp:
            output = Path(temp) / "Avatar.fbx"
            from contextlib import nullcontext
            from unittest.mock import patch
            with patch("unitypackage_blender_importer.export.triangle_staging.triangle_export_scene",
                       return_value=nullcontext()):
                result = export_fbx(output, bpy_module=FakeBpy())
        self.assertEqual(result, output)
        self.assertEqual(calls[0]["add_leaf_bones"], False)
        self.assertEqual(set(FBX_EXPORT_PRESET), set(calls[0]))


if __name__ == "__main__":
    unittest.main()
