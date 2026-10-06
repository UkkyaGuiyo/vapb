"""Diagnostic integration probe for the existing explicit Renderer confirmation route."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import bpy

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def triangle_counts(mesh) -> list[int]:
    mesh.data.calc_loop_triangles()
    counts = [0] * len(mesh.material_slots)
    for triangle in mesh.data.loop_triangles:
        polygon = mesh.data.polygons[triangle.polygon_index]
        if polygon.material_index < 0 or polygon.material_index >= len(counts):
            raise AssertionError("polygon references a missing material slot")
        counts[polygon.material_index] += 1
    return counts


def material_refs(mesh) -> list[dict[str, str]]:
    return [{
        "link": slot.link,
        "guid": str(slot.material.get("unity_material_guid", "")).lower()
            if slot.material else "",
        "file_id": str(slot.material.get("unity_material_file_id", ""))
            if slot.material else "",
        "package_id": str(slot.material.get("unity_source_package_id", ""))
            if slot.material else "",
        "present": slot.material is not None,
    } for slot in mesh.material_slots]


def main() -> None:
    args = sys.argv[sys.argv.index("--") + 1:]
    if len(args) != 3:
        raise SystemExit("usage: -- <source.unitypackage> <run-dir> <result.json>")
    package_path, run_dir, result_path = map(lambda item: Path(item).resolve(), args)
    if result_path.exists():
        raise FileExistsError(result_path)
    report = {"stage": "T0-A-EXPLICIT-RENDERER-CONFIRMATION", "status": "FAIL"}
    try:
        package_sha = hashlib.sha256(package_path.read_bytes()).hexdigest()
        import unitypackage_blender_importer as addon
        addon.register()
        imported = bpy.ops.import_scene.unitypackage(
            filepath=str(package_path), import_mode="RECONSTRUCT", prefab_choice="AUTO",
            use_materials=True, use_textures=True, keep_extracted=False,
            source_storage_directory=str(run_dir / "source_archive"),
        )
        if "FINISHED" not in imported:
            raise AssertionError("VAPB production import did not finish: " + repr(imported))

        roots = [obj for obj in bpy.context.scene.objects
                 if obj.get("_vapb_renderer_occurrences")]
        if len(roots) != 1:
            raise AssertionError("expected one occurrence projection root, got " + str(len(roots)))
        root = roots[0]
        payload = json.loads(str(root["_vapb_renderer_occurrences"]))
        records = payload.get("records", [])
        if len(records) != 1:
            raise AssertionError("expected one exact renderer occurrence, got " + str(len(records)))
        record = records[0]
        mesh_guid = str(record.get("mesh", {}).get("mesh_guid", "")).lower()
        mesh_sha = str(record.get("mesh", {}).get("source_sha256", "")).lower()
        candidates = [obj for obj in bpy.context.scene.objects
                      if obj.type == "MESH"
                      and str(obj.get("_vapb_root_context_id", ""))
                      == str(root.get("_vapb_root_context_id", ""))
                      and str(obj.get("_vapb_fbx_source_asset_guid", "")).lower() == mesh_guid
                      and str(obj.get("_vapb_fbx_source_asset_sha256", "")).lower() == mesh_sha]
        from unitypackage_blender_importer.blender.fbx_receipt import validate_persistent_receipt
        candidates = [obj for obj in candidates if validate_persistent_receipt(obj)]
        if len(candidates) != 1:
            raise AssertionError("expected one receipt-valid exact native mesh, got " + str(len(candidates)))
        mesh = candidates[0]

        expected = [{"guid": str((value or {}).get("guid", "")).lower(),
                     "file_id": str((value or {}).get("file_id", ""))}
                    for _, value in sorted(record.get("materials", {}).items(),
                                           key=lambda item: int(item[0]))]
        package_id = "sha256:" + package_sha
        before_slots = material_refs(mesh)
        before_faces = triangle_counts(mesh)
        scene = bpy.context.scene
        scene.vapb_renderer_root = root
        scene.vapb_renderer_mesh = mesh

        from unitypackage_blender_importer.blender.renderer_binding import (
            BindingError, validate_binding)
        try:
            validate_binding(record, root, mesh, bpy.data.objects)
            report["read_only_binding_preflight"] = "VALID"
            report["preflight_error"] = ""
        except (BindingError, TypeError, ValueError) as error:
            report["read_only_binding_preflight"] = "REJECTED"
            report["preflight_error"] = type(error).__name__ + ": " + str(error)

        operator_result = bpy.ops.vapb.confirm_renderer_binding(
            occurrence_id=str(record["occurrence_id"]))
        after_slots = material_refs(mesh)
        after_faces = triangle_counts(mesh)
        binding_raw = mesh.get("_vapb_renderer_binding")
        binding = json.loads(str(binding_raw)) if binding_raw else None
        actual = [{"guid": row["guid"], "file_id": row["file_id"]} for row in after_slots]
        report.update({
            "source_package_sha256": package_sha,
            "root_type": root.type,
            "root_context_id": str(root.get("_vapb_root_context_id", "")),
            "renderer_occurrence_id": str(record.get("occurrence_id", "")),
            "owner": record.get("owner", {}),
            "owner_name_diagnostic_only": record.get("owner_name", ""),
            "material_status": record.get("material_status", ""),
            "expected_material_refs": expected,
            "selected_mesh": {
                "fbx_guid": str(mesh.get("_vapb_fbx_source_asset_guid", "")).lower(),
                "fbx_sha256": str(mesh.get("_vapb_fbx_source_asset_sha256", "")).lower(),
                "receipt_valid": bool(validate_persistent_receipt(mesh)),
                "renderer_binding": str(mesh.get("_vapb_renderer_binding", "")),
            },
            "operator_result": sorted(operator_result),
            "slots_before": before_slots,
            "slots_after": after_slots,
            "actual_material_refs": actual,
            "triangle_counts_before": before_faces,
            "triangle_counts_after": after_faces,
            "binding_evidence": binding.get("evidence", "") if binding else "",
        })
        if operator_result != {"FINISHED"}:
            raise AssertionError("confirm_renderer_binding did not finish: " + repr(operator_result))
        if actual != expected or not all(
                row["present"] and row["package_id"] == package_id for row in after_slots):
            raise AssertionError("confirmed slot identity/package does not match the exact projection")
        if before_faces != after_faces:
            raise AssertionError("confirmation changed the source face-to-slot counts")
        if binding is None or binding.get("evidence") != "USER_CONFIRMED":
            raise AssertionError("confirmation did not persist USER_CONFIRMED binding evidence")
        report["status"] = "PASS"
    except Exception as error:
        report["error"] = type(error).__name__ + ": " + str(error)

    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print("CONFIRM_RENDERER_BINDING_" + report["status"] + " " + json.dumps(report, sort_keys=True))
    if report["status"] != "PASS":
        raise RuntimeError(report.get("error", "confirmation probe failed"))


if __name__ == "__main__":
    main()
