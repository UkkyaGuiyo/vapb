"""Blender 5.2 persistence and panel probe for synthetic unresolved evidence.

Run twice, with ``-- <blend-path> write`` then ``-- <blend-path> read``.
"""

import json
from pathlib import Path
import sys
from types import SimpleNamespace

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import unitypackage_blender_importer as addon
from unitypackage_blender_importer.blender.fbx_receipt import make_receipt, persist_receipt
from unitypackage_blender_importer.ui.import_outcome_panel import (
    VAPB_PT_import_outcome, scene_import_outcome,
)
from unitypackage_blender_importer.unity.occurrence_projection import occurrence_identity


class Layout:
    def __init__(self):
        self.labels = []

    def label(self, *, text, icon="NONE"):
        self.labels.append(text)

    def box(self):
        return self


def main():
    target, mode = sys.argv[sys.argv.index("--") + 1:]
    addon.register()
    try:
        assert VAPB_PT_import_outcome.bl_category == "VAPB Result"
        source_guid, source_sha = "a" * 32, "b" * 64
        if mode == "write":
            root = bpy.data.objects.new("Synthetic import root", None)
            bpy.context.scene.collection.objects.link(root)
            root["_vapb_root_context_id"] = "synthetic-root"
            witness_package_sha = "f" * 64
            root["_vapb_witness_package_sha256"] = witness_package_sha
            row = {
                "root_context_id": "synthetic-root", "root_package_id": "root-package",
                "root_member_id": "root-member", "root_asset_guid": "c" * 32,
                "source_package_id": "child-package",
                "instance_edge_path": [{
                    "container_package_id": "root-package", "container_asset_guid": "c" * 32,
                    "prefab_instance_file_id": 42, "source_package_id": "child-package",
                    "source_prefab_guid": "d" * 32,
                }],
                "source_key": {"source_kind": "PREFAB_LOCAL", "source_asset_guid": source_guid,
                               "renderer_file_id": 101},
                "mesh": {"mesh_guid": source_guid, "mesh_file_id": 4300000,
                         "source_package_id": "child-package", "source_sha256": source_sha},
                "material_status": "EXACT", "materials": {
                    "0": {"guid": "e" * 32, "file_id": 2100000}},
            }
            row["occurrence_id"] = occurrence_identity(row)
            nested_occurrence = row["occurrence_id"]
            root["_vapb_renderer_occurrences"] = json.dumps({
                "records": [row],
                "issues": [{"code": "UNRESOLVED_SOURCE", "instance_edge_path": [{}]}],
            })
            bpy.context.scene["unitypackage_dependency_registry"] = json.dumps({
                "schema_version": 1,
                "dependencies": [{"dependency_type": "PREFAB_RENDERER_MATERIAL",
                                  "status": "MISSING_CONSUMER"}],
            })
            bpy.context.scene["unitypackage_fbx_count"] = 1
            bpy.context.scene["unitypackage_fbx_failed_count"] = 1
            mesh = bpy.data.meshes.new("Synthetic realized nested mesh")
            occurrence = bpy.data.objects.new("Synthetic nested occurrence", mesh)
            bpy.context.scene.collection.objects.link(occurrence)
            occurrence["_vapb_renderer_occurrence_id"] = nested_occurrence
            occurrence["_vapb_root_context_id"] = "synthetic-root"
            occurrence["unity_source_package_id"] = "child-package"

            def has_nested_warning():
                return "NESTED_PREFAB_RENDERER_NOT_REALIZED" in {
                    item["code"] for item in scene_import_outcome(bpy.context.scene)["items"]
                }

            assert has_nested_warning(), "bare marker without a receipt must not prove realization"
            persist_receipt(occurrence, make_receipt(11, 12, source_guid, source_sha))
            assert not has_nested_warning(), "unique matching persistent receipt should prove the saved occurrence"
            occurrence["_vapb_root_context_id"] = "wrong-root"
            assert has_nested_warning(), "wrong-root marker must not prove realization"
            occurrence["_vapb_root_context_id"] = "synthetic-root"
            occurrence["_vapb_fbx_object_receipt_id"] = "forged"
            assert has_nested_warning(), "invalid receipt must not prove realization"
            persist_receipt(occurrence, make_receipt(11, 12, source_guid, source_sha))
            duplicate = occurrence.copy()
            bpy.context.scene.collection.objects.link(duplicate)
            assert has_nested_warning(), "duplicate occurrence markers must remain ambiguous"
            bpy.data.objects.remove(duplicate, do_unlink=True)
            assert not has_nested_warning(), "unique matching persistent receipt should prove the saved occurrence"
            from unitypackage_blender_importer.blender.model_witness_bridge import plan_witness_material_dependencies
            dependency_obj = bpy.data.objects.new(
                "Synthetic competing dependency consumer", bpy.data.meshes.new("Competing mesh"))
            bpy.context.scene.collection.objects.link(dependency_obj)
            dependency_obj["_vapb_root_context_id"] = "synthetic-root"
            dependency_obj["unity_source_package_id"] = "child-package"
            persist_receipt(dependency_obj, make_receipt(11, 12, source_guid, source_sha))
            dependency_row = dict(row)
            dependency_row["materials"] = {0: {"guid": "e" * 32, "file_id": 2100000,
                                                "source_package_id": "child-package"}}
            conflicting = plan_witness_material_dependencies(
                [(dependency_row, dependency_obj)], witness_package_sha)
            assert len(conflicting) == 1
            bpy.context.scene["unitypackage_dependency_registry"] = json.dumps({
                "schema_version": 1, "dependencies": conflicting,
            })
            assert has_nested_warning(), "a separate dependency-resolved Object cannot override a conflicting marker Object"
            bpy.data.objects.remove(dependency_obj, do_unlink=True)
            bpy.context.scene["unitypackage_dependency_registry"] = json.dumps({
                "schema_version": 1,
                "dependencies": [{"dependency_type": "PREFAB_RENDERER_MATERIAL",
                                  "status": "MISSING_CONSUMER"}],
            })
        elif mode == "read":
            nested_occurrence = json.loads(next(
                obj["_vapb_renderer_occurrences"] for obj in bpy.context.scene.objects
                if obj.get("_vapb_renderer_occurrences")
            ))["records"][0]["occurrence_id"]
        report = scene_import_outcome(bpy.context.scene)
        assert report["overall"] == "PARTIAL", report
        assert report["counts"]["UNRESOLVED_IDENTITY"] == 2, report
        assert report["counts"]["MISSING_DEPENDENCY"] == 0, report
        nested_codes = {item["code"] for item in report["items"]}
        assert "FBX_IMPORT_PARTIAL_FAILURE" in nested_codes, report
        assert "NESTED_PREFAB_RENDERER_NOT_REALIZED" not in nested_codes, report
        layout = Layout()
        VAPB_PT_import_outcome.draw(SimpleNamespace(layout=layout),
                                     SimpleNamespace(scene=bpy.context.scene))
        assert any("一部未確認" in line for line in layout.labels), layout.labels
        assert any("一部の復元を保留" in line for line in layout.labels), layout.labels
        assert "対象Objectは証拠だけでは特定できません" in "".join(layout.labels), layout.labels
        if mode == "write":
            bpy.ops.wm.save_as_mainfile(filepath=target)
        print("IMPORT_OUTCOME_PROBE_PASS:" + mode)
    finally:
        addon.unregister()


if __name__ == "__main__":
    main()
