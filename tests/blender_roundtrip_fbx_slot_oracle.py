"""Measure native Blender FBX slot/face data in an isolated disposable run.

This test helper deliberately does not import or call the VAPB add-on.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tarfile

import bpy


def package_assets(package_path: Path) -> dict[str, dict[str, bytes]]:
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


def find_fbx(package_path: Path, output_dir: Path) -> tuple[Path, str]:
    assets = package_assets(package_path)
    matches = [(guid, row) for guid, row in assets.items()
               if row.get("pathname", b"").decode("utf-8").lower().endswith(".fbx")]
    if len(matches) != 1:
        raise AssertionError("expected exactly one source FBX, got " + str(len(matches)))
    guid, row = matches[0]
    payload = row.get("asset")
    if payload is None:
        raise AssertionError("source FBX has no asset payload")
    path = output_dir / "SourceOracle.fbx"
    if path.exists():
        raise FileExistsError(path)
    path.write_bytes(payload)
    return path, guid


def face_slot_counts(mesh) -> list[int]:
    mesh.data.calc_loop_triangles()
    counts = [0] * len(mesh.material_slots)
    for triangle in mesh.data.loop_triangles:
        polygon = mesh.data.polygons[triangle.polygon_index]
        if polygon.material_index < 0 or polygon.material_index >= len(counts):
            raise AssertionError("source FBX polygon references an absent material slot")
        counts[polygon.material_index] += 1
    return counts


def main() -> None:
    args = sys.argv[sys.argv.index("--") + 1:]
    if len(args) != 3:
        raise SystemExit("usage: -- <source.unitypackage> <run-dir> <result.json>")
    package_path, run_dir, result_path = map(Path, args)
    package_path = package_path.resolve()
    run_dir = run_dir.resolve()
    result_path = result_path.resolve()
    run_dir.mkdir(parents=True, exist_ok=True)
    if result_path.exists():
        raise FileExistsError(result_path)
    report = {"stage": "T0-FBX-ORACLE", "status": "FAIL"}
    try:
        fbx_path, guid = find_fbx(package_path, run_dir)
        result = bpy.ops.import_scene.fbx(filepath=str(fbx_path))
        if "FINISHED" not in result:
            raise AssertionError("native FBX import did not finish: " + repr(result))
        meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
        report["mesh_candidates"] = [{
            "name_diagnostic_only": obj.name,
            "vertex_count": len(obj.data.vertices),
            "polygon_count": len(obj.data.polygons),
            "slot_count": len(obj.material_slots),
            "triangle_counts": face_slot_counts(obj),
            "materials_diagnostic_only": [slot.material.name if slot.material else None
                                           for slot in obj.material_slots],
            "armature_modifiers": sum(mod.type == "ARMATURE" for mod in obj.modifiers),
        } for obj in meshes]
        native_skins = [obj for obj in meshes if len(obj.material_slots) == 3
                        and any(mod.type == "ARMATURE" for mod in obj.modifiers)]
        if len(native_skins) != 1:
            raise AssertionError("expected one three-slot Mesh with an Armature modifier, got " +
                                 json.dumps(report["mesh_candidates"], sort_keys=True))
        mesh = native_skins[0]
        counts = face_slot_counts(mesh)
        if len(counts) != 3 or any(value <= 0 for value in counts) or len(set(counts)) != 3:
            raise AssertionError("fixture must have three distinguishable populated face groups: " + repr(counts))
        report.update({
            "status": "PASS",
            "source_package_sha256": hashlib.sha256(package_path.read_bytes()).hexdigest(),
            "source_fbx_guid": guid,
            "source_fbx_sha256": hashlib.sha256(fbx_path.read_bytes()).hexdigest(),
            "native_mesh_name_diagnostic_only": mesh.name,
            "material_names_diagnostic_only": [slot.material.name if slot.material else None
                                                for slot in mesh.material_slots],
            "material_slot_count": len(mesh.material_slots),
            "triangle_counts_by_native_slot": counts,
        })
    except Exception as error:
        report["error"] = type(error).__name__ + ": " + str(error)
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print("ROUNDTRIP_FBX_SLOT_ORACLE_" + report["status"] + " " + json.dumps(report, sort_keys=True))
    if report["status"] != "PASS":
        raise RuntimeError(report.get("error", "FBX oracle failed"))


if __name__ == "__main__":
    main()
