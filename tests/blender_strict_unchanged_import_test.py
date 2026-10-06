"""T0-A: import a fixed public package and inspect slots without repairing them."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import sys
import tarfile

import bpy


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
EXPECTED_PACKAGE_SHA256 = "d6245d25c3cbd513c49b8d2e241b313a752331cd338563becab6eb7c819bfa0c"
MATERIAL_ROW = re.compile(
    rb"(?m)^\s*-\s*\{\s*fileID:\s*(-?\d+)\s*,\s*guid:\s*([0-9a-fA-F]{32})\s*,\s*type:\s*(\d+)\s*\}"
)


def read_package(package_path: Path) -> dict[str, dict[str, bytes]]:
    assets: dict[str, dict[str, bytes]] = {}
    with tarfile.open(package_path, "r:*") as archive:
        for member in archive.getmembers():
            parts = member.name.split("/")
            if len(parts) != 2 or not member.isfile():
                continue
            guid, kind = parts
            if kind not in {"asset", "pathname", "asset.meta"}:
                continue
            stream = archive.extractfile(member)
            if stream is None:
                raise ValueError("cannot read package member " + member.name)
            assets.setdefault(guid, {})[kind] = stream.read()
    return assets


def expected_materials(assets: dict[str, dict[str, bytes]]) -> tuple[str, list[dict[str, str]]]:
    prefabs = [(guid, row) for guid, row in assets.items()
               if row.get("pathname", b"").decode("utf-8").lower().endswith(".prefab")]
    if len(prefabs) != 1:
        raise AssertionError("fixture must contain exactly one Prefab")
    _, prefab = prefabs[0]
    payload = prefab.get("asset", b"")
    # The fixture is fixed and first-party; parse only its Unity serialized list.
    renderers = re.split(rb"(?m)^---\s*!u!\d+\s+&[^\r\n]*\r?\n", payload)
    docs = re.findall(rb"(?m)^---\s*!u!(\d+)\s+&[^\r\n]*\r?\n", payload)
    rows: list[dict[str, str]] = []
    for class_id, body in zip(docs, renderers[1:]):
        if class_id != b"137":
            continue
        lines = body.splitlines()
        in_materials = False
        key_indent = -1
        for line in lines:
            indent = len(line) - len(line.lstrip(b" \t"))
            stripped = line.strip()
            if not in_materials:
                if re.fullmatch(rb"m_Materials\s*:", stripped):
                    in_materials = True
                    key_indent = indent
                continue
            if not stripped:
                continue
            if stripped.startswith(b"-"):
                match = MATERIAL_ROW.fullmatch(stripped)
                if match is None:
                    raise AssertionError("unsupported Material row in fixed fixture: " + repr(stripped))
                rows.append({"file_id": match.group(1).decode("ascii"),
                             "guid": match.group(2).decode("ascii").lower(),
                             "type": match.group(3).decode("ascii")})
                continue
            if indent <= key_indent:
                break
    if len(rows) != 3:
        raise AssertionError("expected three ordered SkinnedMeshRenderer Material refs, got " + repr(rows))
    for reference in rows:
        provider = assets.get(reference["guid"])
        if provider is None or not provider.get("pathname", b"").decode("utf-8").lower().endswith(".mat"):
            raise AssertionError("Prefab Material reference has no matching .mat asset: " + repr(reference))
        header = re.search(rb"(?m)^---\s*!u!21\s+&(-?\d+)\b", provider.get("asset", b""))
        if header is None or header.group(1).decode("ascii") != reference["file_id"]:
            raise AssertionError("Prefab fileID does not identify the serialized Material document")
    fbxs = [(guid, row) for guid, row in assets.items()
            if row.get("pathname", b"").decode("utf-8").lower().endswith(".fbx")]
    if len(fbxs) != 1:
        raise AssertionError("fixture must contain exactly one FBX")
    return fbxs[0][0], rows


def triangles_by_slot(mesh) -> list[int]:
    mesh.data.calc_loop_triangles()
    counts = [0] * len(mesh.material_slots)
    for triangle in mesh.data.loop_triangles:
        slot_index = mesh.data.polygons[triangle.polygon_index].material_index
        if slot_index < 0 or slot_index >= len(counts):
            raise AssertionError("polygon references an absent material slot")
        counts[slot_index] += 1
    return counts


def diagnostic_snapshot(source_fbx_guid: str, source_fbx_sha256: str,
                        package_id: str, expected_ids: list[dict[str, str]],
                        source_fbx_meta: str, expected_owner_game_object_ids: list[str]) -> dict:
    """Capture the identity joins without changing the imported scene."""
    from unitypackage_blender_importer.blender.dependency_resolver import (
        SCENE_DEPENDENCY_REGISTRY, load_dependency_registry)
    from unitypackage_blender_importer.blender.fbx_receipt import validate_persistent_receipt

    wanted = {(row["guid"], row["file_id"]) for row in expected_ids}
    providers = []
    for material in bpy.data.materials:
        guid = str(material.get("unity_material_guid", "")).lower()
        file_id = str(material.get("unity_material_file_id", ""))
        if (guid, file_id) in wanted or guid in {row[0] for row in wanted}:
            providers.append({
                "name_diagnostic_only": material.name,
                "guid": guid,
                "file_id": file_id,
                "package_id": str(material.get("unity_source_package_id", "")),
                "asset_path": str(material.get("unity_material_path", "")),
                "source_path": str(material.get("unity_source_path", "")),
            })

    semantic_objects = []
    projections = []
    for obj in bpy.context.scene.objects:
        row = {
            "type": obj.type,
            "name_diagnostic_only": obj.name,
            "semantic_id": str(obj.get("_vapb_semantic_id", "")),
            "semantic_owner_id": str(obj.get("_vapb_semantic_owner_id", "")),
            "root_context_id": str(obj.get("_vapb_root_context_id", "")),
            "package_id": str(obj.get("unity_source_package_id", "")),
            "prefab_file_id": str(obj.get("unity_prefab_file_id", "")),
            "parent_name_diagnostic_only": obj.parent.name if obj.parent else "",
            "persistent_receipt_valid": bool(validate_persistent_receipt(obj))
                if obj.type == "MESH" else None,
            "fbx_guid": str(obj.get("_vapb_fbx_source_asset_guid", "")).lower(),
            "fbx_sha256": str(obj.get("_vapb_fbx_source_asset_sha256", "")).lower(),
            "mesh_uid": str(obj.get("_vapb_fbx_model_uid", "")),
            "geometry_uid": str(obj.get("_vapb_fbx_geometry_uid", "")),
            "renderer_occurrence_id": str(obj.get("_vapb_renderer_occurrence_id", "")),
            "renderer_binding": str(obj.get("_vapb_renderer_binding", "")),
        }
        if (row["semantic_id"] or row["semantic_owner_id"] or row["root_context_id"]
                or (obj.type == "MESH" and row["fbx_guid"])):
            semantic_objects.append(row)
        raw_projection = obj.get("_vapb_renderer_occurrences")
        if raw_projection:
            try:
                projection = json.loads(str(raw_projection))
                records = []
                for record in projection.get("records", []):
                    owner = record.get("owner") or {}
                    mesh = record.get("mesh") or {}
                    records.append({
                        "root_package_id": record.get("root_package_id", ""),
                        "root_member_id": record.get("root_member_id", ""),
                        "root_asset_guid": record.get("root_asset_guid", ""),
                        "source_package_id": record.get("source_package_id", ""),
                        "source_member_id": record.get("source_member_id", ""),
                        "instance_edge_path": record.get("instance_edge_path", []),
                        "occurrence_id": record.get("occurrence_id", ""),
                        "source_key": record.get("source_key", {}),
                        "renderer_class_id": record.get("renderer_class_id"),
                        "owner": owner,
                        "owner_name": record.get("owner_name", ""),
                        "mesh": {key: mesh.get(key) for key in (
                            "mesh_guid", "mesh_file_id", "source_sha256", "source_package_id")},
                        "materials": record.get("materials", {}),
                        "material_slot_count": record.get("material_slot_count"),
                        "material_status": record.get("material_status", ""),
                        "issues": record.get("issues", []),
                    })
                projections.append({
                    "root_name_diagnostic_only": obj.name,
                    "root_type": obj.type,
                    "root_context_id": str(obj.get("_vapb_root_context_id", "")),
                    "records": records,
                    "issues": projection.get("issues", []),
                })
            except (TypeError, ValueError):
                projections.append({"root_name_diagnostic_only": obj.name,
                                    "parse_error": "invalid renderer occurrence JSON"})

    registry_raw = bpy.context.scene.get(SCENE_DEPENDENCY_REGISTRY)
    registry_parse_error = ""
    try:
        registry_value = json.loads(str(registry_raw)) if registry_raw is not None else None
    except (TypeError, ValueError, json.JSONDecodeError) as error:
        registry_value = None
        registry_parse_error = type(error).__name__ + ": " + str(error)
    dependency_rows = load_dependency_registry(bpy.context.scene).get("dependencies", [])
    dependencies = [{key: record.get(key) for key in (
        "dependency_type", "status", "binding_status", "consumer_receipt_valid",
        "consumer_package_id", "consumer_asset_guid", "consumer_asset_path",
        "consumer_object_path", "consumer_slot_index", "consumer_occurrence_id",
        "consumer_root_context_id", "consumer_native_realization_id",
        "consumer_fbx_guid", "consumer_fbx_sha256", "consumer_fbx_model_uid",
        "consumer_fbx_geometry_uid", "target_guid", "target_file_id", "target_type",
        "resolved_provider_guid", "resolved_provider_package_id", "issues")}
        for record in dependency_rows]

    from unitypackage_blender_importer.unity.material_mapping import parse_external_object_rows
    parsed_external = parse_external_object_rows(source_fbx_meta)
    external_rows = [{key: getattr(row, key, None) for key in (
        "row_index", "canonical_name", "raw_first_name", "canonical_guid",
        "canonical_file_id", "canonical_second_type", "row_status",
        "validation_status", "ambiguous", "raw_row")}
        for row in parsed_external]

    return {
        "expected_provider_identities": sorted([{"guid": guid, "file_id": file_id}
                                                  for guid, file_id in wanted], key=lambda row: row["guid"]),
        "canonical_material_datablocks": providers,
        "semantic_scene_objects": semantic_objects,
        "renderer_projections": projections,
        "expected_owner_game_object_ids": expected_owner_game_object_ids,
        "owner_scene_object_matches": [row for row in semantic_objects
                                        if row["prefab_file_id"] in expected_owner_game_object_ids],
        "dependency_registry_raw_present": registry_raw is not None,
        "dependency_registry_raw": str(registry_raw) if registry_raw is not None else None,
        "dependency_registry_parse_error": registry_parse_error,
        "dependency_registry_has_dependencies_key": isinstance(registry_value, dict)
            and "dependencies" in registry_value,
        "dependency_records": dependencies,
        "fbx_external_object_rows": external_rows,
        "fbx_external_object_row_count": len(external_rows),
        "expected_fbx_guid": source_fbx_guid,
        "expected_fbx_sha256": source_fbx_sha256,
        "expected_package_id": package_id,
    }


def main() -> None:
    args = sys.argv[sys.argv.index("--") + 1:]
    if len(args) != 4:
        raise SystemExit("usage: -- <source.unitypackage> <run-dir> <fbx-oracle.json> <result.json>")
    package_path, run_dir, oracle_path, result_path = map(Path, args)
    package_path, run_dir = package_path.resolve(), run_dir.resolve()
    oracle_path, result_path = oracle_path.resolve(), result_path.resolve()
    if result_path.exists():
        raise FileExistsError(result_path)
    report = {"stage": "T0-A-STRICT-IMPORT", "status": "FAIL"}
    try:
        package_sha = hashlib.sha256(package_path.read_bytes()).hexdigest()
        if package_sha != EXPECTED_PACKAGE_SHA256:
            raise AssertionError("source fixture hash changed: " + package_sha)
        oracle = json.loads(oracle_path.read_text(encoding="utf-8"))
        if oracle.get("status") != "PASS" or oracle.get("source_package_sha256") != package_sha:
            raise AssertionError("native FBX oracle is absent, failed, or for another package")
        assets = read_package(package_path)
        source_fbx_guid, references = expected_materials(assets)

        import unitypackage_blender_importer as addon
        addon.register()
        result = bpy.ops.import_scene.unitypackage(
            filepath=str(package_path), import_mode="RECONSTRUCT", prefab_choice="AUTO",
            use_materials=True, use_textures=True, keep_extracted=False,
            source_storage_directory=str(run_dir / "source_archive"),
        )
        if "FINISHED" not in result:
            raise AssertionError("VAPB production import did not finish: " + repr(result))
        all_meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
        from unitypackage_blender_importer.blender.fbx_receipt import validate_persistent_receipt
        report["scene_mesh_candidates"] = [{
            "name_diagnostic_only": obj.name,
            "vertex_count": len(obj.data.vertices),
            "slot_count": len(obj.material_slots),
            "material_refs": [{
                "guid": str(slot.material.get("unity_material_guid", "")).lower()
                         if slot.material else "",
                "file_id": str(slot.material.get("unity_material_file_id", ""))
                           if slot.material else "",
            } for slot in obj.material_slots],
            "receipt_fields": {key: str(obj.get(key, "")) for key in (
                "_vapb_fbx_source_asset_guid", "_vapb_fbx_source_asset_sha256",
                "_vapb_fbx_realization_id", "_vapb_fbx_object_receipt_id",
                "_vapb_fbx_mesh_receipt_id", "_vapb_root_context_id",
                "_vapb_fbx_model_uid", "_vapb_fbx_geometry_uid")},
            "persistent_receipt_valid": bool(validate_persistent_receipt(obj)),
            "armature_modifiers": sum(modifier.type == "ARMATURE" for modifier in obj.modifiers),
        } for obj in all_meshes]
        receipt_candidates = [obj for obj in all_meshes
                  if str(obj.get("_vapb_fbx_source_asset_guid", "")).lower() == source_fbx_guid
                  and str(obj.get("_vapb_fbx_source_asset_sha256", "")).lower()
                  == str(oracle.get("source_fbx_sha256", "")).lower()
                  and obj.get("_vapb_fbx_realization_id")
                  and obj.get("_vapb_root_context_id")
                  and obj.data.get("_vapb_fbx_source_asset_sha256")
                  and str(obj.data.get("_vapb_fbx_source_asset_sha256", "")).lower()
                  == str(oracle.get("source_fbx_sha256", "")).lower()
                  and any(modifier.type == "ARMATURE" for modifier in obj.modifiers)]
        meshes = [obj for obj in receipt_candidates if validate_persistent_receipt(obj)]
        report["receipt_candidate_count"] = len(receipt_candidates)
        report["persistent_receipt_valid_candidate_count"] = len(meshes)
        if len(meshes) != 1:
            report["diagnostic_snapshot"] = diagnostic_snapshot(
                source_fbx_guid, str(oracle.get("source_fbx_sha256", "")),
                "sha256:" + package_sha,
                [{"guid": row["guid"], "file_id": row["file_id"]} for row in references],
                assets[source_fbx_guid].get("asset.meta", b"").decode("utf-8", errors="replace"),
                [str((row.get("owner") or {}).get("owner_game_object_id", ""))
                 for obj in bpy.context.scene.objects if obj.get("_vapb_renderer_occurrences")
                 for row in json.loads(str(obj["_vapb_renderer_occurrences"])).get("records", [])])
            raise AssertionError("expected one exact imported native skin Mesh with valid persistent receipt, got " +
                                 json.dumps(report["scene_mesh_candidates"], sort_keys=True))
        mesh = meshes[0]
        observed = []
        for slot in mesh.material_slots:
            material = slot.material
            observed.append({
                "link": slot.link,
                "guid": str(material.get("unity_material_guid", "")).lower() if material else "",
                "file_id": str(material.get("unity_material_file_id", "")) if material else "",
                "package_id": str(material.get("unity_source_package_id", "")) if material else "",
                "material_present": material is not None,
            })
        expected_ids = [{"guid": row["guid"], "file_id": row["file_id"]} for row in references]
        observed_ids = [{"guid": row["guid"], "file_id": row["file_id"]} for row in observed]
        face_counts = triangles_by_slot(mesh)
        expected_counts = oracle.get("triangle_counts_by_native_slot")
        package_id = str(mesh.get("unity_source_package_id", ""))
        package_id_ok = package_id == "sha256:" + package_sha
        report["diagnostic_snapshot"] = diagnostic_snapshot(
            source_fbx_guid, str(oracle.get("source_fbx_sha256", "")), package_id, expected_ids,
            assets[source_fbx_guid].get("asset.meta", b"").decode("utf-8", errors="replace"),
            [str((row.get("owner") or {}).get("owner_game_object_id", ""))
             for obj in bpy.context.scene.objects if obj.get("_vapb_renderer_occurrences")
             for row in json.loads(str(obj["_vapb_renderer_occurrences"])).get("records", [])])
        report.update({
            "source_package_sha256": package_sha,
            "native_fbx_oracle_sha256": oracle.get("source_fbx_sha256"),
            "source_fbx_guid": source_fbx_guid,
            "expected_material_refs": expected_ids,
            "observed_slots": observed,
            "face_triangle_counts": face_counts,
            "source_fbx_face_triangle_counts": expected_counts,
            "source_package_id": package_id,
            "source_package_id_matches_input_sha": package_id_ok,
            "native_receipts": {key: str(mesh.get(key, "")) for key in (
                "_vapb_fbx_realization_id", "_vapb_fbx_object_receipt_id",
                "_vapb_fbx_mesh_receipt_id", "_vapb_fbx_model_uid",
                "_vapb_fbx_geometry_uid", "_vapb_root_context_id")},
        })
        if len(observed) != 3:
            raise AssertionError("imported slot count differs from fixed three-slot expectation")
        if observed_ids != expected_ids:
            raise AssertionError("imported Material GUID/fileID sequence differs from source Prefab")
        if not all(row["material_present"] and row["package_id"] == package_id for row in observed):
            raise AssertionError("one or more slot Materials lack exact source-package provenance")
        if not package_id_ok:
            raise AssertionError("imported package identity does not match fixed input archive hash")
        if face_counts != expected_counts:
            raise AssertionError("imported face-to-slot counts differ from independent native FBX baseline")
        if not all(report["native_receipts"].values()):
            raise AssertionError("required native receipt field is missing")
        report["status"] = "PASS"
    except Exception as error:
        report["error"] = type(error).__name__ + ": " + str(error)
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print("T0_A_STRICT_IMPORT_" + report["status"] + " " + json.dumps(report, sort_keys=True))
    if report["status"] != "PASS":
        raise RuntimeError(report.get("error", "strict import failed"))


if __name__ == "__main__":
    main()
