"""Import the generated FBXs once in Blender and capture face/transform observations."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import bpy


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def args_after_separator():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if len(args) != 2:
        raise SystemExit("EXPECTED_MANIFEST_AND_OUTPUT_JSON")
    return Path(args[0]).resolve(), Path(args[1]).resolve()


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablock in list(bpy.data.meshes):
        if datablock.users == 0:
            bpy.data.meshes.remove(datablock)
    for datablock in list(bpy.data.materials):
        if datablock.users == 0:
            bpy.data.materials.remove(datablock)


def matrix_rows(matrix):
    return [[float(matrix[r][c]) for c in range(4)] for r in range(4)]


def rounded_uv(uv):
    return tuple(round(float(component), 6) for component in uv)


def capture_case(root: Path, case: dict, spec: dict) -> dict:
    fbx_path = root / case["filename"]
    if sha256(fbx_path) != case["sha256"]:
        raise RuntimeError("INPUT_HASH_MISMATCH:%s" % case["id"])
    clear_scene()
    bpy.ops.import_scene.fbx(
        filepath=str(fbx_path),
        axis_forward="-Z",
        axis_up="Y",
        global_scale=1.0,
        use_anim=False,
        use_custom_props=True,
        use_image_search=False,
        automatic_bone_orientation=False,
    )
    objects = sorted((obj for obj in bpy.context.scene.objects if obj.type == "MESH"), key=lambda obj: obj.name)
    if len(objects) != 1:
        raise RuntimeError("EXPECTED_ONE_IMPORTED_MESH:%s:%d" % (case["id"], len(objects)))
    obj = objects[0]
    mesh = obj.data
    mesh.calc_loop_triangles()
    if not mesh.uv_layers:
        raise RuntimeError("UV_LAYER_MISSING:%s" % case["id"])

    expected_faces = spec["geometry"]["faces"]
    face_by_uv = {
        tuple(sorted(round(float(uv["x"]), 6) for uv in face["uvs"])): face
        for face in expected_faces
    }
    triangles = []
    uv_to_face = []
    source_materials = {row["name"]: row for row in case["raw_fbx"]["materials_by_fixture_identity"]}
    for polygon in mesh.polygons:
        if len(polygon.loop_indices) != 3:
            raise RuntimeError("NON_TRIANGLE_POLYGON:%s:%d" % (case["id"], polygon.index))
        uvs = [rounded_uv(mesh.uv_layers.active.data[index].uv) for index in polygon.loop_indices]
        key = tuple(sorted(uv[0] for uv in uvs))
        source_face = face_by_uv.get(key)
        face_id = source_face["face_id"] if source_face else "UNMATCHED"
        slot_index = int(polygon.material_index)
        material = mesh.materials[slot_index] if slot_index < len(mesh.materials) else None
        material_name = material.name if material else ""
        material_id = case["source_material_id_by_name"].get(material_name, "")
        source_material_uid = source_materials.get(material_name, {}).get("fbx_object_uid", 0)
        triangle = {
            "face_id_by_uv": face_id,
            "uvs": [list(uv) for uv in uvs],
            "vertex_indices": [int(index) for index in polygon.vertices],
            "vertices_local": [[float(v) for v in mesh.vertices[index].co] for index in polygon.vertices],
            "material_slot_index": slot_index,
            "material_name_diagnostic": material_name,
            "material_id_from_pinned_source_connection": material_id,
            "source_fbx_material_object_uid": source_material_uid,
        }
        triangles.append(triangle)
        uv_to_face.append((face_id, material_id))

    expected_by_face = {face["face_id"]: face["material"] for face in expected_faces}
    observed_by_face = {face_id: material_id for face_id, material_id in uv_to_face}
    membership_match = (len(triangles) == len(expected_faces)
                        and len(observed_by_face) == len(expected_faces)
                        and all(observed_by_face.get(face_id) == material_id
                                for face_id, material_id in expected_by_face.items()))
    hierarchy = []
    for item in sorted(bpy.context.scene.objects, key=lambda value: value.name):
        hierarchy.append({
            "name": item.name,
            "type": item.type,
            "parent_name": item.parent.name if item.parent else "",
            "matrix_local": matrix_rows(item.matrix_local),
            "matrix_world": matrix_rows(item.matrix_world),
        })
    return {
        "case_id": case["id"],
        "input_sha256": case["sha256"],
        "raw_fbx": case["raw_fbx"],
        "blender_importer": {"axis_forward": "-Z", "axis_up": "Y", "global_scale": 1.0,
                             "use_custom_props": True, "use_anim": False},
        "mesh_vertices_local": [[float(c) for c in vertex.co] for vertex in mesh.vertices],
        "mesh_normals_local": [[float(c) for c in vertex.normal] for vertex in mesh.vertices],
        "triangles": triangles,
        "material_slot_names_diagnostic": [material.name if material else "" for material in mesh.materials],
        "hierarchy": hierarchy,
        "face_membership_matches_source_identity": membership_match,
        "unmatched_face_count": sum(triangle["face_id_by_uv"] == "UNMATCHED" for triangle in triangles),
    }


def main():
    manifest_path, output_path = args_after_separator()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema") != "vapb-coordinate-intervention-manifest-v1":
        raise RuntimeError("UNEXPECTED_MANIFEST_SCHEMA")
    root = manifest_path.parent
    cases = [capture_case(root, case, manifest["spec"]) for case in manifest["cases"]]
    passed = all(case["face_membership_matches_source_identity"] for case in cases)
    result = {
        "schema": "vapb-coordinate-intervention-blender-capture-v1",
        "blender_version": bpy.app.version_string,
        "manifest_sha256": sha256(manifest_path),
        "status": "BLENDER_FACE_IDENTITY_PASS" if passed else "BLENDER_FACE_IDENTITY_UNPROVEN",
        "mapping": None,
        "cases": cases,
        "interpretation": "Blender observations only; this does not establish Unity coordinate factorization.",
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print("VAPB_COORDINATE_BLENDER_CAPTURE=" + result["status"])
    print("CASES=%d" % len(cases))
    print("RESULT_SHA256=" + sha256(output_path))


if __name__ == "__main__":
    main()
