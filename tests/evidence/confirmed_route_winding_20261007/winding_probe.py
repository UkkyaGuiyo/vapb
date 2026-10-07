from __future__ import annotations

import collections
import hashlib
import json
import sys
from pathlib import Path

import bpy


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_cyclic(points):
    p = tuple(tuple(round(float(c), 6) for c in point) for point in points)
    return min(p, p[1:] + p[:1], p[2:] + p[:2])


def grouped_oriented_triangles(obj, keys):
    obj.data.calc_loop_triangles()
    groups = {key: [] for key in keys}
    for tri in obj.data.loop_triangles:
        poly = obj.data.polygons[tri.polygon_index]
        slot = int(poly.material_index)
        if slot < 0 or slot >= len(keys):
            raise AssertionError(f"material index {slot} outside {len(keys)} labels")
        points = [obj.matrix_world @ obj.data.vertices[i].co for i in tri.vertices]
        groups[keys[slot]].append(canonical_cyclic(points))
    return {key: collections.Counter(values) for key, values in groups.items()}


def canonical_reversed(points):
    return canonical_cyclic((points[0], points[2], points[1]))


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    if len(args) != 7:
        raise SystemExit("repo blend output_fbx export_report closure_report source_package out_json")
    repo, blend, fbx, report_path, closure_path, package, output = [Path(a).resolve() for a in args]
    report = json.loads(report_path.read_text(encoding="utf-8"))
    closure = json.loads(closure_path.read_text(encoding="utf-8"))
    if report.get("status") != "PASS":
        raise AssertionError("export evidence is not PASS")
    if closure.get("status") != "PASS":
        raise AssertionError("package/FBX closure evidence is not PASS")
    if sha256(package) != report["input_hashes_after"]["package"]:
        raise AssertionError("source package hash changed")
    if sha256(blend) != report["input_hashes_after"]["blend"]:
        raise AssertionError("source blend hash differs from export evidence")
    if sha256(fbx) != closure["generated_fbx"]["sha256"]:
        raise AssertionError("generated FBX hash differs from closure report")
    refs = report["manifest_material_bindings_expected"]
    source_keys = [ref["guid"] for ref in refs]
    target_keys = [ref["transport_id"] for ref in refs]
    if (not source_keys or not target_keys or len(set(source_keys)) != len(source_keys)
            or len(set(target_keys)) != len(target_keys)):
        raise AssertionError("empty binding set or duplicate source GUID/transport label")

    sys.path.insert(0, str(repo.parent))
    sys.path.insert(0, str(repo / "tests"))
    from blender_three_slot_fixture_oracle import raw_prefab_material_refs
    raw_refs = raw_prefab_material_refs(package)
    if [(r["guid"], str(r["file_id"])) for r in raw_refs] != [
        (r["guid"], str(r["file_id"])) for r in refs
    ]:
        raise AssertionError("export report material refs differ from raw source Prefab")

    bpy.ops.wm.open_mainfile(filepath=str(blend))
    sources = [o for o in bpy.context.scene.objects if
               o.type == "MESH" and o.get("_vapb_renderer_binding")]
    if len(sources) != 1:
        raise AssertionError(f"expected one bound source mesh, found {len(sources)}")
    source = sources[0]
    binding = json.loads(str(source["_vapb_renderer_binding"]))
    if binding.get("evidence") != "USER_CONFIRMED":
        raise AssertionError("source mesh is not the reopened USER_CONFIRMED occurrence")
    source_package_id = str(source.get("unity_source_package_id", ""))
    expected_source_package_id = "sha256:" + sha256(package)
    if source_package_id != expected_source_package_id:
        raise AssertionError("source occurrence package identity differs from source package SHA")
    source_slot_identity = []
    for slot in source.material_slots:
        material = slot.material
        source_slot_identity.append({
            "guid": str(material.get("unity_material_guid", "")).lower() if material else "",
            "file_id": str(material.get("unity_material_file_id", "")) if material else "",
            "package_id": str(material.get("unity_source_package_id", "")) if material else "",
            "link": str(slot.link),
        })
    expected_slot_identity = [{
        "guid": str(ref["guid"]).lower(),
        "file_id": str(ref["file_id"]),
        "package_id": source_package_id,
        "link": "OBJECT",
    } for ref in refs]
    if source_slot_identity != expected_slot_identity:
        raise AssertionError(f"source slot identities differ from raw Prefab refs: {source_slot_identity!r}")
    source_by_guid = grouped_oriented_triangles(source, source_keys)

    before = set(bpy.data.objects)
    result = bpy.ops.import_scene.fbx(filepath=str(fbx))
    if result != {"FINISHED"}:
        raise AssertionError(f"FBX import result: {result!r}")
    imported_meshes = [o for o in bpy.data.objects if o not in before and o.type == "MESH"]
    matches = [o for o in imported_meshes if
               [slot.material.name if slot.material else "" for slot in o.material_slots]
               == target_keys]
    if len(matches) != 1:
        raise AssertionError(f"expected one FBX mesh with exported transport labels, found {len(matches)}")
    target = matches[0]
    target_by_id = grouped_oriented_triangles(target, target_keys)

    details = {}
    all_pass = True
    for ref in refs:
        guid, label = ref["guid"], ref["transport_id"]
        src = source_by_guid[guid]
        dst = target_by_id[label]
        same = sum((src & dst).values())
        reversed_dst = collections.Counter()
        for tri, count in dst.items():
            reversed_dst[canonical_reversed(tri)] += count
        reverse_only = sum((src & (reversed_dst - dst)).values())
        group_pass = src == dst
        all_pass = all_pass and group_pass
        details[guid] = {
            "transport_id": label,
            "source_triangle_count": sum(src.values()),
            "generated_triangle_count": sum(dst.values()),
            "same_winding_matches": same,
            "reverse_only_matches": reverse_only,
            "source_minus_generated_oriented": sum((src - dst).values()),
            "generated_minus_source_oriented": sum((dst - src).values()),
            "oriented_triangle_multiset_equal": group_pass,
        }

    control = ((0, 0, 0), (1, 0, 0), (0, 1, 0))
    if canonical_cyclic(control) == canonical_cyclic((control[0], control[2], control[1])):
        raise AssertionError("winding comparator self-control failed to distinguish reversal")
    output_value = {
        "status": "PASS" if all_pass else "FAIL",
        "stage": "CONFIRMED-ROUTE-FBX-WINDING-PRESERVATION",
        "blender_version": bpy.app.version_string,
        "input_source_blend_sha256": sha256(blend),
        "input_source_package_sha256": sha256(package),
        "generated_fbx_sha256": sha256(fbx),
        "source_mesh": source.name,
        "source_package_id_matches_input_sha256": source_package_id == expected_source_package_id,
        "source_package_id_consistent_across_slots": all(row["package_id"] == source_package_id for row in source_slot_identity),
        "source_material_slot_identity_validation": "PASS: GUID/fileID/order match raw Prefab; OBJECT links and shared nonempty occurrence package ID",
        "generated_mesh": target.name,
        "comparison": "multiset of world-space triangulated Mesh coordinates, rounded to 6 decimals; cyclic start-point permutations are equivalent and reversal is distinct",
        "triangle_group_oriented_results": details,
        "orientation_self_control": "PASS: reversed nondegenerate triangle compares differently",
        "strict_t0a": "FAIL",
        "t0b": "BLOCKED",
    }
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(output_value, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps(output_value, sort_keys=True))
    if not all_pass:
        raise SystemExit(1)


main()
