"""Public synthetic controls for an optional, revision-bound Unity model witness."""

import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from unitypackage_blender_importer.blender.fbx_receipt import FbxModelLink, RawFbxSemanticIndex
from unitypackage_blender_importer.unity.model_identity_witness import (
    ModelAssetRevision, ModelWitnessError, build_model_witness_from_probe,
    load_model_witness,
    validate_model_witness,
)


PACKAGE_SHA = "a" * 64
FBX_SHA = "b" * 64
META_SHA = "c" * 64
GUID = "d" * 32


def fixture():
    document = {
        "schema_version": "vapb-model-identity-witness-v1",
        "source_unitypackage_sha256": PACKAGE_SHA,
        "unity_version": "2022.3.22f1",
        "source_validation": {"probe_pass": True, "original_revision_equivalent": True},
        "assets": [{
            "asset_guid": GUID,
            "source_fbx_sha256": FBX_SHA,
            "source_meta_sha256": META_SHA,
            "models": [{
                "model_uid": "101", "geometry_uid": "202",
                "transform_local_id": "-303", "game_object_local_id": "-404",
                "renderers": [{"class_id": 137, "renderer_local_id": "-505",
                               "mesh_local_id": "-606"}],
            }],
        }],
    }
    revisions = {GUID: ModelAssetRevision(
        FBX_SHA, META_SHA,
        RawFbxSemanticIndex([FbxModelLink(101, 202)], [101]),
    )}
    return document, revisions


class ModelIdentityWitnessTests(unittest.TestCase):
    def test_exact_revision_exposes_signed_identity_bridge(self):
        document, revisions = fixture()
        index = validate_model_witness(document, PACKAGE_SHA, revisions)
        row = index.mesh(GUID, -606)
        self.assertEqual((101, 202, -505, -404),
                         (row.model_uid, row.geometry_uid,
                          row.renderer_local_id, row.game_object_local_id))

    def test_package_fbx_meta_or_geometry_revision_mismatch_rejects(self):
        document, revisions = fixture()
        with self.assertRaises(ModelWitnessError):
            validate_model_witness(document, "0" * 64, revisions)
        for key in ("source_fbx_sha256", "source_meta_sha256"):
            changed = copy.deepcopy(document)
            changed["assets"][0][key] = "0" * 64
            with self.subTest(key=key), self.assertRaises(ModelWitnessError):
                validate_model_witness(changed, PACKAGE_SHA, revisions)
        wrong_graph = {GUID: ModelAssetRevision(
            FBX_SHA, META_SHA, RawFbxSemanticIndex([FbxModelLink(101, 999)], [101]))}
        with self.assertRaises(ModelWitnessError):
            validate_model_witness(document, PACKAGE_SHA, wrong_graph)

    def test_duplicate_or_missing_identity_rejects_without_guessing(self):
        document, revisions = fixture()
        duplicate = copy.deepcopy(document)
        duplicate["assets"][0]["models"].append(copy.deepcopy(duplicate["assets"][0]["models"][0]))
        with self.assertRaises(ModelWitnessError):
            validate_model_witness(duplicate, PACKAGE_SHA, revisions)
        incomplete = copy.deepcopy(document)
        del incomplete["assets"][0]["models"][0]["game_object_local_id"]
        with self.assertRaises(ModelWitnessError):
            validate_model_witness(incomplete, PACKAGE_SHA, revisions)

    def test_failed_source_probe_is_not_authoritative(self):
        document, revisions = fixture()
        document["source_validation"]["original_revision_equivalent"] = False
        with self.assertRaises(ModelWitnessError):
            validate_model_witness(document, PACKAGE_SHA, revisions)

    def test_public_unity_probe_conversion_ignores_non_mesh_models(self):
        _, revisions = fixture()
        probe = {
            "schema_version": "vapb-source-fbx-model-witness-1",
            "source_fbx_sha256": FBX_SHA,
            "source_meta_sha256": META_SHA,
            "model_guid": GUID,
            "unity_version": "2022.3.22f1",
            "models": [
                {"model_uid": "101", "transform_local_id": "-303",
                 "game_object_local_id": "-404",
                 "renderers": [{"class_id": "137", "renderer_local_id": "-505",
                                "mesh_local_id": "-606"}]},
                {"model_uid": "707", "transform_local_id": "-808",
                 "game_object_local_id": "-909", "renderers": []},
            ],
        }
        report = {"pass": True, "originalRevisionEquivalent": True,
                  "sourceMetaRestored": True, "sourceRawRestored": True}
        document = build_model_witness_from_probe(probe, report, PACKAGE_SHA, revisions)
        self.assertEqual(1, len(document["assets"][0]["models"]))
        self.assertEqual(101, validate_model_witness(document, PACKAGE_SHA, revisions)
                         .mesh(GUID, -606).model_uid)
        report["pass"] = False
        with self.assertRaises(ModelWitnessError):
            build_model_witness_from_probe(probe, report, PACKAGE_SHA, revisions)

    def test_import_loader_rechecks_extracted_fbx_and_meta_bytes(self):
        document, revisions = fixture()
        with tempfile.TemporaryDirectory() as temp:
            fbx = Path(temp) / "Model.fbx"
            meta = Path(str(fbx) + ".meta")
            sidecar = Path(temp) / "witness.json"
            fbx.write_bytes(b"public synthetic FBX revision")
            meta.write_bytes(b"public synthetic importer revision")
            from unitypackage_blender_importer.blender.fbx_receipt import source_sha256
            document["assets"][0]["source_fbx_sha256"] = source_sha256(fbx)
            document["assets"][0]["source_meta_sha256"] = source_sha256(meta)
            import json
            sidecar.write_text(json.dumps(document), encoding="utf-8")

            class Database:
                def find_guid(self, guid):
                    from types import SimpleNamespace
                    return SimpleNamespace(path=fbx) if guid == GUID else None

            with patch("unitypackage_blender_importer.unity.model_identity_witness.RawFbxSemanticIndex.from_file",
                       return_value=revisions[GUID].fbx_index):
                self.assertEqual(1, len(load_model_witness(sidecar, PACKAGE_SHA, Database()).rows))
                meta.write_bytes(b"changed importer revision")
                with self.assertRaises(ModelWitnessError):
                    load_model_witness(sidecar, PACKAGE_SHA, Database())


if __name__ == "__main__":
    unittest.main()
