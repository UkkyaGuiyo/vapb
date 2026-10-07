"""Fresh-process native FBX carrier and face-group check; no VAPB add-on import."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import bpy


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    args = sys.argv[sys.argv.index("--") + 1:]
    if len(args) != 4:
        raise SystemExit("usage: -- <generated.fbx> <t0c-result.json> <t0a-result.json> <result.json>")
    fbx_path, t0c_path, t0a_path, result_path = map(lambda value: Path(value).resolve(), args)
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from strict_run_paths import validate_run_paths, write_json_exclusive
    validate_run_paths({"generated FBX": fbx_path, "T0-C report": t0c_path,
                        "independent T0-A source oracle": t0a_path}, {"native FBX result": result_path})
    t0c = json.loads(t0c_path.read_text(encoding="utf-8"))
    t0a = json.loads(t0a_path.read_text(encoding="utf-8"))
    expected_sha = t0c.get("closure", {}).get("generated_fbx_sha256")
    if t0c.get("status") != "PASS" or expected_sha != sha256_file(fbx_path):
        raise ValueError("T0-C generated FBX identity/hash is not fixed")
    if t0a.get("status") != "PASS" or t0a.get("source_fbx_face_triangle_counts") != [2, 4, 6]:
        raise ValueError("independent source FBX face-count oracle is not the pinned PASS")

    report = {"stage": "T0-C-NATIVE-FBX-IMPORT", "status": "FAIL",
              "generated_fbx_sha256": expected_sha,
              "expected_transport_ids": t0c["closure"]["material_transport_ids"],
              "expected_triangle_counts": t0a["source_fbx_face_triangle_counts"]}
    try:
        result = bpy.ops.import_scene.fbx(filepath=str(fbx_path))
        if "FINISHED" not in result:
            raise AssertionError("native FBX importer did not finish: " + repr(result))
        meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
        candidates = []
        for obj in meshes:
            obj.data.calc_loop_triangles()
            counts = [0] * len(obj.material_slots)
            for triangle in obj.data.loop_triangles:
                slot = obj.data.polygons[triangle.polygon_index].material_index
                if slot < 0 or slot >= len(counts):
                    raise AssertionError("native FBX polygon references missing Material slot")
                counts[slot] += 1
            candidates.append({
                "name_diagnostic_only": obj.name,
                "armature_modifier_count": sum(mod.type == "ARMATURE" for mod in obj.modifiers),
                "triangle_counts_by_slot": counts,
                "slots": [{"link": slot.link,
                           "material_name_diagnostic_only": slot.material.name if slot.material else None,
                           "carrier_label": slot.material.name if slot.material else ""}
                          for slot in obj.material_slots],
            })
        report["native_meshes"] = candidates
        matching = [row for row in candidates if row["armature_modifier_count"] > 0
                    and len(row["slots"]) == 3]
        if len(matching) != 1:
            raise AssertionError("expected exactly one skinned native Mesh with three slots")
        mesh = matching[0]
        observed_ids = [slot["carrier_label"] for slot in mesh["slots"]]
        observed_counts = mesh["triangle_counts_by_slot"]
        if observed_ids != report["expected_transport_ids"]:
            raise AssertionError("native FBX Material carriers do not identify ordered manifest transport IDs")
        if observed_counts != report["expected_triangle_counts"]:
            raise AssertionError("native FBX face-group counts differ from independent source FBX baseline")
        report.update({"status": "PASS", "observed_transport_ids": observed_ids,
                       "observed_triangle_counts": observed_counts})
    except Exception as error:
        report["error"] = type(error).__name__ + ": " + str(error)
    result_path.parent.mkdir(parents=True, exist_ok=True)
    write_json_exclusive(result_path, json.dumps(report, indent=2, sort_keys=True))
    print("T0_C_NATIVE_FBX_" + report["status"] + " " + json.dumps(report, sort_keys=True))
    if report["status"] != "PASS":
        raise RuntimeError(report.get("error", "native FBX check failed"))


if __name__ == "__main__":
    main()
