"""Bounded fresh-process reopen/export comparison against the fixed T0-A oracle."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import bpy


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
FIXED_BLEND_SHA256 = "1e4f75e36ff5d0ed76523fdd54eaf936a8275426e3186082eca9e2421de6aa05"
FIXED_SOURCE_SHA256 = "d6245d25c3cbd513c49b8d2e241b313a752331cd338563becab6eb7c819bfa0c"
sys.path.insert(0, str(ROOT.parent))
spec = importlib.util.spec_from_file_location(
    "unitypackage_blender_importer", ROOT / "__init__.py",
    submodule_search_locations=[str(ROOT)],
)
if spec is None or spec.loader is None:
    raise RuntimeError("cannot load checked-out VAPB add-on")
addon = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = addon
spec.loader.exec_module(addon)
from unitypackage_blender_importer.blender.fbx_receipt import validate_persistent_receipt


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def mesh_snapshot(meshes):
    rows = []
    for obj in meshes:
        mesh = obj.data
        mesh.calc_loop_triangles()
        counts = [0] * len(obj.material_slots)
        for triangle in mesh.loop_triangles:
            slot_index = mesh.polygons[triangle.polygon_index].material_index
            if slot_index < 0 or slot_index >= len(counts):
                raise AssertionError("Mesh face references missing material slot")
            counts[slot_index] += 1
        rows.append({
            "source_fbx_guid": str(obj.get("_vapb_fbx_source_asset_guid", "")).lower(),
            "source_fbx_sha256": str(obj.get("_vapb_fbx_source_asset_sha256", "")).lower(),
            "receipt_valid": bool(validate_persistent_receipt(obj)),
            "receipt_fields": {key: str(obj.get(key, "")) for key in (
                "_vapb_fbx_source_asset_guid", "_vapb_fbx_source_asset_sha256",
                "_vapb_fbx_realization_id", "_vapb_fbx_object_receipt_id",
                "_vapb_fbx_mesh_receipt_id", "_vapb_fbx_model_uid",
                "_vapb_fbx_geometry_uid", "_vapb_root_context_id")},
            "armature_modifier_count": sum(mod.type == "ARMATURE" for mod in obj.modifiers),
            "vertices": len(mesh.vertices), "edges": len(mesh.edges),
            "polygons": len(mesh.polygons), "triangle_counts": counts,
            "slot_refs": [{"link": slot.link,
                           "guid": str(slot.material.get("unity_material_guid", "")).lower()
                               if slot.material else "",
                           "file_id": str(slot.material.get("unity_material_file_id", ""))
                               if slot.material else "",
                           "package_id": str(slot.material.get("unity_source_package_id", ""))
                               if slot.material else ""}
                          for slot in obj.material_slots],
        })
    return rows


def main() -> None:
    args = sys.argv[sys.argv.index("--") + 1:]
    if len(args) != 5:
        raise SystemExit("usage: -- <saved.blend> <source.unitypackage> <t0a-result.json> <output.unitypackage> <result.json>")
    blend_path, source_path, t0a_path, output_path, result_path = map(
        lambda value: Path(value).resolve(), args)
    from strict_run_paths import validate_run_paths, write_json_exclusive
    validate_run_paths({"saved blend": blend_path, "source package": source_path,
                        "T0-A result": t0a_path},
                       {"T1 output package": output_path, "T1 report": result_path})
    blend_sha_before = sha256_file(blend_path)
    if blend_sha_before != FIXED_BLEND_SHA256:
        raise ValueError("saved blend SHA differs from pinned T0-B scene")
    source_sha_before = sha256_file(source_path)
    if source_sha_before != FIXED_SOURCE_SHA256:
        raise ValueError("source package SHA differs from pinned fixture")
    t0a = json.loads(t0a_path.read_text(encoding="utf-8"))
    if t0a.get("status") != "PASS" or t0a.get("source_package_sha256") != FIXED_SOURCE_SHA256:
        raise ValueError("fixed T0-A oracle is not PASS")

    report = {"stage": "T1-SAVED-SCENE-REOPEN-EXPORT", "status": "FAIL",
              "saved_blend_sha256": blend_sha_before, "source_package_sha256": source_sha_before}
    try:
        open_result = bpy.ops.wm.open_mainfile(filepath=str(blend_path))
        if "FINISHED" not in open_result:
            raise AssertionError("saved .blend did not open: " + repr(open_result))
        all_meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
        all_rows = mesh_snapshot(all_meshes)
        expected_guid = str(t0a.get("source_fbx_guid", "")).lower()
        expected_receipt = t0a.get("native_receipts", {})
        selected = [index for index, row in enumerate(all_rows)
                    if row["source_fbx_guid"] == expected_guid
                    and row["receipt_fields"].get("_vapb_root_context_id")
                    == expected_receipt.get("_vapb_root_context_id")
                    and all(row["receipt_fields"].get(key) == value
                            for key, value in expected_receipt.items())]
        meshes = [all_meshes[index] for index in selected]
        scene_rows = [all_rows[index] for index in selected]
        report["all_reopened_meshes_diagnostic"] = all_rows
        report["expected_source_fbx_guid"] = expected_guid
        report["selected_reopened_meshes"] = scene_rows
        before_rows = t0a.get("scene_mesh_candidates", [])
        normalize_before = sorted([{
            "vertices": row.get("vertex_count"),
            "slot_count": row.get("slot_count"),
            "material_refs": row.get("material_refs", []),
            "receipt_fields": row.get("receipt_fields", {}),
            "receipt_valid": row.get("persistent_receipt_valid"),
            "armature_modifier_count": row.get("armature_modifiers"),
        } for row in before_rows], key=lambda row: json.dumps(row, sort_keys=True))
        normalize_after = sorted([{
            "vertices": row.get("vertices"),
            "slot_count": len(row.get("slot_refs", [])),
            "material_refs": [{"guid": slot["guid"], "file_id": slot["file_id"]}
                              for slot in row.get("slot_refs", [])],
            "receipt_fields": row.get("receipt_fields", {}),
            "receipt_valid": row.get("receipt_valid"),
            "armature_modifier_count": row.get("armature_modifier_count"),
        } for row in all_rows], key=lambda row: json.dumps(row, sort_keys=True))
        report["scene_candidate_set_matches_t0a"] = normalize_before == normalize_after
        if not report["scene_candidate_set_matches_t0a"]:
            raise AssertionError("reopened scene semantic Mesh candidate set differs from T0-A")
        if len(scene_rows) != 1 or not scene_rows[0]["receipt_valid"]:
            raise AssertionError("reopened scene does not contain exactly one valid native source Mesh receipt")
        mesh_row = scene_rows[0]
        expected_refs = [{"guid": row["guid"], "file_id": row["file_id"]}
                         for row in t0a["expected_material_refs"]]
        actual_refs = [{"guid": row["guid"], "file_id": row["file_id"]}
                       for row in mesh_row["slot_refs"]]
        if actual_refs != expected_refs or any(row["link"] != "OBJECT" for row in mesh_row["slot_refs"]):
            raise AssertionError("reopened Material slot identity/order/link differs from T0-A")
        if any(row["package_id"] != "sha256:" + FIXED_SOURCE_SHA256 for row in mesh_row["slot_refs"]):
            raise AssertionError("reopened Material package provenance differs from source fixture")
        if mesh_row["triangle_counts"] != t0a.get("face_triangle_counts"):
            raise AssertionError("reopened native mesh face groups differ from T0-A")
        if any(mesh_row["receipt_fields"].get(key) != value
               for key, value in expected_receipt.items()):
            raise AssertionError("reopened persistent receipt identity differs from T0-A")

        addon.register()
        bpy.context.view_layer.objects.active = meshes[0]
        before_export = mesh_snapshot(meshes)
        export_result = bpy.ops.export_scene.vapb_unitypackage(
            filepath=str(output_path), export_scope="ACTIVE")
        after_export = mesh_snapshot(meshes)
        if "FINISHED" not in export_result or before_export != after_export:
            raise AssertionError("reopened scene export failed or changed the observed Mesh fields")
        report.update({"open_result": sorted(open_result),
                       "export_result": sorted(export_result), "reopened_mesh": mesh_row,
                       "observed_mesh_fields_unchanged_during_export": before_export == after_export,
                       "output_package_sha256": sha256_file(output_path),
                       "source_package_sha256_after_export": sha256_file(source_path),
                       "saved_blend_sha256_after_export": sha256_file(blend_path)})
        if report["source_package_sha256_after_export"] != FIXED_SOURCE_SHA256:
            raise AssertionError("source fixture changed during T1 export")
        if report["saved_blend_sha256_after_export"] != FIXED_BLEND_SHA256:
            raise AssertionError("saved .blend changed during T1 export")
        report["status"] = "PASS"
    except Exception as error:
        report["status"] = "FAIL"
        report["error"] = type(error).__name__ + ": " + str(error)
    result_path.parent.mkdir(parents=True, exist_ok=True)
    write_json_exclusive(result_path, json.dumps(report, indent=2, sort_keys=True))
    print("T1_SAVED_SCENE_REOPEN_" + report["status"] + " " + json.dumps(report, sort_keys=True))
    if report["status"] != "PASS":
        raise RuntimeError(report.get("error", "T1 saved-scene reopen failed"))


if __name__ == "__main__":
    main()
