"""Two-process save/reopen check for an explicitly confirmed Renderer binding."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import bpy

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from blender_three_slot_fixture_oracle import (
    EXPECTED_PACKAGE_SHA256, package_sha256, raw_prefab_material_refs)

EXPECTED_TRIANGLES = [2, 4, 6]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def triangle_counts(mesh) -> list[int]:
    mesh.data.calc_loop_triangles()
    counts = [0] * len(mesh.material_slots)
    for triangle in mesh.data.loop_triangles:
        polygon = mesh.data.polygons[triangle.polygon_index]
        if polygon.material_index < 0 or polygon.material_index >= len(counts):
            raise AssertionError("polygon references a missing material slot")
        counts[polygon.material_index] += 1
    return counts


def slot_records(mesh) -> list[dict[str, str]]:
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


def binding_for(mesh):
    raw = mesh.get("_vapb_renderer_binding")
    if not raw:
        return None
    return json.loads(str(raw))


def expected_material_refs(record) -> list[dict[str, str]]:
    return [{"guid": str((value or {}).get("guid", "")).lower(),
             "file_id": str((value or {}).get("file_id", ""))}
            for _, value in sorted(record.get("materials", {}).items(),
                                   key=lambda item: int(item[0]))]


def install_addon() -> None:
    import unitypackage_blender_importer as addon
    addon.register()


def prepare(package_path: Path, run_dir: Path, blend_path: Path, result_path: Path) -> dict:
    report = {"stage": "CONFIRM-BINDING-PREPARE", "status": "FAIL"}
    package_sha = package_sha256(package_path)
    if package_sha != EXPECTED_PACKAGE_SHA256:
        raise AssertionError("fixed source package hash changed: " + package_sha)
    if blend_path.exists() or result_path.exists():
        raise FileExistsError("refusing to overwrite prepared blend or result")
    install_addon()
    imported = bpy.ops.import_scene.unitypackage(
        filepath=str(package_path), import_mode="RECONSTRUCT", prefab_choice="AUTO",
        use_materials=True, use_textures=True, keep_extracted=False,
        source_storage_directory=str(run_dir / "source_archive"),
    )
    if imported != {"FINISHED"}:
        raise AssertionError("VAPB import did not finish: " + repr(imported))
    roots = [obj for obj in bpy.context.scene.objects if obj.get("_vapb_renderer_occurrences")]
    if len(roots) != 1:
        raise AssertionError("expected exactly one Renderer projection root")
    root = roots[0]
    projection = json.loads(str(root["_vapb_renderer_occurrences"]))
    records = projection.get("records", [])
    if len(records) != 1:
        raise AssertionError("expected exactly one Renderer occurrence")
    record = records[0]
    expected = raw_prefab_material_refs(package_path)
    if expected_material_refs(record) != expected:
        raise AssertionError("Renderer projection differs from independently parsed raw Prefab")
    mesh_guid = str(record.get("mesh", {}).get("mesh_guid", "")).lower()
    mesh_sha = str(record.get("mesh", {}).get("source_sha256", "")).lower()
    meshes = [obj for obj in bpy.context.scene.objects
              if obj.type == "MESH"
              and str(obj.get("_vapb_root_context_id", "")) == str(root.get("_vapb_root_context_id", ""))
              and str(obj.get("_vapb_fbx_source_asset_guid", "")).lower() == mesh_guid
              and str(obj.get("_vapb_fbx_source_asset_sha256", "")).lower() == mesh_sha]
    from unitypackage_blender_importer.blender.fbx_receipt import validate_persistent_receipt
    meshes = [obj for obj in meshes if validate_persistent_receipt(obj)]
    if len(meshes) != 1:
        raise AssertionError("expected one exact receipt-valid native Mesh")
    mesh = meshes[0]
    scene = bpy.context.scene
    scene.vapb_renderer_root = root
    scene.vapb_renderer_mesh = mesh
    from unitypackage_blender_importer.blender.renderer_binding import validate_binding
    validate_binding(record, root, mesh, bpy.data.objects)
    operator_result = bpy.ops.vapb.confirm_renderer_binding(
        occurrence_id=str(record["occurrence_id"]))
    if operator_result != {"FINISHED"}:
        raise AssertionError("Renderer confirmation did not finish: " + repr(operator_result))

    slots = slot_records(mesh)
    faces = triangle_counts(mesh)
    actual_refs = [{"guid": row["guid"], "file_id": row["file_id"]} for row in slots]
    binding = binding_for(mesh)
    if actual_refs != expected or not all(
            row["present"] and row["link"] == "OBJECT"
            and row["package_id"] == "sha256:" + package_sha for row in slots):
        raise AssertionError("confirmed Material slots do not match the fixed source Prefab")
    if faces != EXPECTED_TRIANGLES:
        raise AssertionError("prepared face-slot counts differ from fixture baseline")
    if not binding or binding.get("evidence") != "USER_CONFIRMED":
        raise AssertionError("confirmation evidence was not present before save")

    report.update({
        "status": "PASS",
        "source_package_sha256": package_sha,
        "root_context_id": str(root.get("_vapb_root_context_id", "")),
        "occurrence_id": str(record.get("occurrence_id", "")),
        "native_realization_id": str(mesh.get("_vapb_fbx_realization_id", "")),
        "fbx_guid": str(mesh.get("_vapb_fbx_source_asset_guid", "")).lower(),
        "fbx_sha256": str(mesh.get("_vapb_fbx_source_asset_sha256", "")).lower(),
        "fbx_model_uid": str(mesh.get("_vapb_fbx_model_uid", "")),
        "fbx_geometry_uid": str(mesh.get("_vapb_fbx_geometry_uid", "")),
        "mesh_receipt_id": str(mesh.get("_vapb_fbx_mesh_receipt_id", "")),
        "binding_evidence": binding.get("evidence", ""),
        "expected_material_refs": expected,
        "slots_before_save": slots,
        "triangle_counts_before_save": faces,
    })
    if blend_path.exists():
        raise FileExistsError("refusing to overwrite prepared blend")
    if bpy.ops.wm.save_as_mainfile(filepath=str(blend_path)) != {"FINISHED"}:
        raise AssertionError("Blender did not save the prepared scene")
    report["blend_sha256"] = sha256(blend_path)
    return report


def verify(blend_path: Path, expected_blend_sha: str, package_path: Path,
           expected_refs: list[dict[str, str]], result_path: Path) -> dict:
    report = {"stage": "CONFIRM-BINDING-FRESH-PROCESS-REOPEN", "status": "FAIL"}
    if result_path.exists():
        raise FileExistsError("refusing to overwrite verification result")
    actual_blend_sha = sha256(blend_path)
    if actual_blend_sha != expected_blend_sha:
        raise AssertionError("prepared .blend SHA does not match the prepare-stage SHA")
    install_addon()
    if bpy.ops.wm.open_mainfile(filepath=str(blend_path)) != {"FINISHED"}:
        raise AssertionError("Blender did not reopen the prepared scene")
    roots = [obj for obj in bpy.context.scene.objects if obj.get("_vapb_renderer_occurrences")]
    if len(roots) != 1:
        raise AssertionError("reopened scene does not have exactly one Renderer root")
    root = roots[0]
    projection = json.loads(str(root["_vapb_renderer_occurrences"]))
    records = projection.get("records", [])
    if len(records) != 1:
        raise AssertionError("reopened Renderer projection is not unique")
    record = records[0]
    package_sha = package_sha256(package_path)
    if package_sha != EXPECTED_PACKAGE_SHA256:
        raise AssertionError("fixed source package SHA-256 mismatch on reopen stage")
    raw_expected = raw_prefab_material_refs(package_path)
    if raw_expected != expected_refs or expected_material_refs(record) != raw_expected:
        raise AssertionError("reopened projection differs from raw Prefab expectation")
    bindings = []
    for obj in bpy.context.scene.objects:
        binding = binding_for(obj) if obj.type == "MESH" else None
        if binding and binding.get("occurrence_id") == record.get("occurrence_id"):
            bindings.append((obj, binding))
    if len(bindings) != 1:
        raise AssertionError("reopened scene does not have exactly one saved binding for the occurrence")
    mesh, binding = bindings[0]
    from unitypackage_blender_importer.blender.fbx_receipt import validate_persistent_receipt
    from unitypackage_blender_importer.blender.renderer_binding import validate_existing_binding
    object_receipt_valid = bool(validate_persistent_receipt(mesh))
    data = mesh.data
    data_receipt = {
        "fbx_sha256": str(data.get("_vapb_fbx_source_asset_sha256", "")).lower(),
        "mesh_receipt_id": str(data.get("_vapb_fbx_mesh_receipt_id", "")),
        "geometry_uid": str(data.get("_vapb_fbx_geometry_uid", "")),
    }
    binding_check = validate_existing_binding(binding, root, mesh, bpy.data.objects)
    expected = raw_expected
    slots = slot_records(mesh)
    actual_refs = [{"guid": row["guid"], "file_id": row["file_id"]} for row in slots]
    faces = triangle_counts(mesh)
    package_id = str(record.get("source_package_id", ""))
    if actual_refs != expected or not all(
            row["present"] and row["link"] == "OBJECT" and row["package_id"] == package_id
            for row in slots):
        raise AssertionError("reopened slot identity/link/package differs from projection")
    if faces != EXPECTED_TRIANGLES:
        raise AssertionError("reopened face-slot counts differ from fixture baseline")
    if not object_receipt_valid:
        raise AssertionError("reopened Object native FBX receipt is invalid")
    if (data_receipt["fbx_sha256"] != str(mesh.get("_vapb_fbx_source_asset_sha256", "")).lower()
            or data_receipt["mesh_receipt_id"] != str(mesh.get("_vapb_fbx_mesh_receipt_id", ""))
            or data_receipt["geometry_uid"] != str(mesh.get("_vapb_fbx_geometry_uid", ""))):
        raise AssertionError("reopened Mesh datablock receipt does not match Object receipt")

    report.update({
        "status": "PASS",
        "blend_sha256": actual_blend_sha,
        "source_package_sha256": package_sha,
        "root_context_id": str(root.get("_vapb_root_context_id", "")),
        "occurrence_id": str(record.get("occurrence_id", "")),
        "native_realization_id": str(mesh.get("_vapb_fbx_realization_id", "")),
        "fbx_guid": str(mesh.get("_vapb_fbx_source_asset_guid", "")).lower(),
        "fbx_sha256": str(mesh.get("_vapb_fbx_source_asset_sha256", "")).lower(),
        "fbx_model_uid": str(mesh.get("_vapb_fbx_model_uid", "")),
        "fbx_geometry_uid": str(mesh.get("_vapb_fbx_geometry_uid", "")),
        "mesh_receipt_id": str(mesh.get("_vapb_fbx_mesh_receipt_id", "")),
        "object_receipt_valid": object_receipt_valid,
        "mesh_datablock_receipt": data_receipt,
        "binding_check_equals_saved": binding_check == binding,
        "binding_evidence": binding.get("evidence", ""),
        "expected_material_refs": expected,
        "slots_after_reopen": slots,
        "triangle_counts_after_reopen": faces,
    })
    if binding_check != binding:
        raise AssertionError("revalidated binding differs from its saved representation")
    if binding.get("evidence") != "USER_CONFIRMED":
        raise AssertionError("reopened binding evidence is not USER_CONFIRMED")
    return report


def write_report(path: Path, report: dict) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(report, indent=2, sort_keys=True))
    print("CONFIRM_BINDING_" + report["stage"] + "_" + report["status"] + " "
          + json.dumps(report, sort_keys=True))


def validate_paths(run_dir: Path, outputs: list[Path], inputs: list[Path]) -> None:
    run_root = run_dir.resolve()
    if not run_root.is_dir() or not (run_root / ".vapb-disposable-run-owned").is_file():
        raise RuntimeError("run directory is not an existing marked disposable directory")
    resolved_outputs = [path.resolve() for path in outputs]
    resolved_inputs = [path.resolve() for path in inputs]
    for output in resolved_outputs:
        try:
            output.relative_to(run_root)
        except ValueError as error:
            raise RuntimeError("output is outside the marked disposable run directory") from error
        if output.exists():
            raise FileExistsError("refusing to overwrite output: " + str(output))
    if len(set(resolved_outputs)) != len(resolved_outputs):
        raise RuntimeError("output paths alias each other")
    if set(resolved_outputs) & set(resolved_inputs):
        raise RuntimeError("output path aliases an input")


def main() -> None:
    args = sys.argv[sys.argv.index("--") + 1:]
    if not args:
        raise SystemExit("usage: -- prepare <package> <run-dir> <blend> <result> | verify <blend> <prepare-result> <package> <run-dir> <result>")
    mode = args[0]
    if mode == "prepare" and len(args) == 5:
        package_path, run_dir, blend_path, result_path = map(
            lambda item: Path(item).resolve(), args[1:])
        validate_paths(run_dir, [blend_path, result_path], [package_path])
        report = {"stage": "CONFIRM-BINDING-PREPARE", "status": "FAIL"}
    elif mode == "verify" and len(args) == 6:
        blend_path, prepare_path, package_path, run_dir, result_path = map(
            lambda item: Path(item).resolve(), args[1:])
        validate_paths(run_dir, [result_path], [blend_path, prepare_path, package_path])
        report = {"stage": "CONFIRM-BINDING-FRESH-PROCESS-REOPEN", "status": "FAIL"}
    else:
        raise SystemExit("usage: -- prepare <package> <run-dir> <blend> <result> | verify <blend> <prepare-result> <package> <run-dir> <result>")

    try:
        if mode == "prepare":
            report = prepare(package_path, run_dir, blend_path, result_path)
        else:
            prepare_result = json.loads(prepare_path.read_text(encoding="utf-8"))
            if prepare_result.get("status") != "PASS":
                raise AssertionError("prepare-stage result is not PASS")
            package_sha = package_sha256(package_path)
            if package_sha != EXPECTED_PACKAGE_SHA256:
                raise AssertionError("fixed source package SHA-256 mismatch")
            if prepare_result.get("source_package_sha256") != package_sha:
                raise AssertionError("source package SHA differs from prepare result")
            expected_refs = raw_prefab_material_refs(package_path)
            if prepare_result.get("expected_material_refs") != expected_refs:
                raise AssertionError("prepare expectations differ from raw Prefab oracle")
            report = verify(blend_path, str(prepare_result["blend_sha256"]),
                            package_path, expected_refs, result_path)
            if str(prepare_result.get("root_context_id", "")) != report.get("root_context_id"):
                raise AssertionError("reopened root context differs from prepare stage")
            for key in ("source_package_sha256", "occurrence_id", "native_realization_id", "fbx_guid", "fbx_sha256",
                        "fbx_model_uid", "fbx_geometry_uid", "mesh_receipt_id",
                        "expected_material_refs"):
                if prepare_result.get(key) != report.get(key):
                    raise AssertionError("prepare/reopen identity mismatch: " + key)
    except Exception as error:
        report["status"] = "FAIL"
        report["error"] = type(error).__name__ + ": " + str(error)
    write_report(result_path, report)
    if report.get("status") != "PASS":
        raise RuntimeError(report.get("error", "binding persistence probe failed"))


if __name__ == "__main__":
    main()
