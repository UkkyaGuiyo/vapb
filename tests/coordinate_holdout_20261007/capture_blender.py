"""Capture one imported holdout FBX set in Blender 5.2.1.

Usage: blender --background --factory-startup --python capture_blender.py -- MANIFEST PREREG_DIR EXPECTED_MANIFEST_SHA256 NEW_CAPTURE_JSON
The final output must not already exist. This is Blender evidence only; Unity is not inferred.
"""
from __future__ import annotations
import hashlib, json, math, sys
from pathlib import Path
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from contract import BLENDER_IMPORT_CONTROLS, CASES, CORNER_UVS, ENGINE_VERSIONS, GEOMETRY, TOLERANCE, public_contract
from oracle import (EXPECTED_U_TAGS, authored_trs, expected_unity_world, local_matrix,
                    maxima_for_case, point, scale_authored_world, validate_u_tags, verdict)

ROOT = Path(__file__).resolve().parent


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def matrix_rows(m):
    return [[float(m[r][c]) for c in range(4)] for r in range(4)]


def finite_tree(value):
    if isinstance(value, dict): return all(finite_tree(v) for v in value.values())
    if isinstance(value, (list, tuple)): return all(finite_tree(v) for v in value)
    if isinstance(value, (int, float)): return math.isfinite(float(value))
    return True


def validate_prereg(prereg_dir):
    pp = prereg_dir / "preregistration.json"
    prereg = json.loads(pp.read_text(encoding="utf-8"))
    if prereg.get("schema") != "vapb-coordinate-holdout-preregistration-v1" or prereg.get("status") != "FROZEN_BEFORE_EXPORT_AND_IMPORT":
        raise RuntimeError("PREREGISTRATION_INVALID")
    sources = {p.name: sha256(p) for p in sorted(ROOT.glob("*.py")) if p.is_file()}
    if sources != prereg.get("source_sha256"):
        raise RuntimeError("PREREGISTRATION_SOURCE_HASH_MISMATCH")
    for name, key in (("contract.json", "contract_sha256"), ("authored-oracle.json", "authored_oracle_sha256")):
        if sha256(prereg_dir / name) != prereg.get(key):
            raise RuntimeError("PREREGISTRATION_ARTIFACT_HASH_MISMATCH:" + name)
    if json.loads((prereg_dir / "contract.json").read_text(encoding="utf-8")) != public_contract():
        raise RuntimeError("PREREGISTERED_CONTRACT_CONTENT_MISMATCH")
    return prereg, sha256(pp)


def capture_case(root, case, oracle_case):
    path = root / case["filename"]
    if sha256(path) != case.get("sha256"):
        raise RuntimeError("INPUT_HASH_MISMATCH:" + case["id"])
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (bpy.data.meshes, bpy.data.materials):
        for datablock in list(datablocks):
            if datablock.users == 0:
                datablocks.remove(datablock)
    bpy.ops.import_scene.fbx(filepath=str(path), **BLENDER_IMPORT_CONTROLS)
    objects = sorted(list(bpy.context.scene.objects), key=lambda x: x.name)
    meshes = [obj for obj in objects if obj.type == "MESH"]
    roots = [obj for obj in objects if obj.parent is None]
    if len(meshes) != 1 or len(roots) != 1 or meshes[0] is not roots[0]:
        raise RuntimeError("EXPECTED_ONE_MESH_ROOT:%s:%d:%d" % (case["id"], len(meshes), len(roots)))
    obj, mesh = meshes[0], meshes[0].data
    if not mesh.uv_layers:
        raise RuntimeError("UV_LAYER_MISSING:" + case["id"])
    points = {}
    triangles = []
    source_by_name = {r["name"]: r for r in case.get("materials_by_fixture_identity", [])}
    source_id_by_name = {r["name"]: r["fixture_material_id"] for r in case.get("materials_by_fixture_identity", [])}
    face_by_u = {tuple(sorted(face["uvs"][i][0] for i in range(3))): face for face in GEOMETRY["faces"]}
    expected_materials = {face["face_id"]: face["material_id"] for face in GEOMETRY["faces"]}
    observed_materials = {}
    for poly in mesh.polygons:
        if len(poly.loop_indices) != 3:
            raise RuntimeError("NON_TRIANGLE_POLYGON:%s:%d" % (case["id"], poly.index))
        uvs = [[float(x) for x in mesh.uv_layers.active.data[li].uv] for li in poly.loop_indices]
        material = mesh.materials[poly.material_index] if poly.material_index < len(mesh.materials) else None
        name = material.name if material else ""
        source_face = face_by_u.get(tuple(sorted(tri_tag for tri_tag in (uv[0] for uv in uvs))))
        face_id = source_face["face_id"] if source_face else "UNMATCHED"
        material_id = source_id_by_name.get(name, "")
        if face_id != "UNMATCHED":
            observed_materials[face_id] = material_id
        tri = {"uvs": uvs, "u_tags": [uv[0] for uv in uvs],
               "face_id_by_u": face_id,
               "vertices_local": [[float(x) for x in mesh.vertices[i].co] for i in poly.vertices],
               "material_slot_index": int(poly.material_index),
               "material_name_diagnostic": name,
               "fixture_material_id_joined_by_name": material_id,
               "source_fbx_material_object_uid": source_by_name.get(name, {}).get("fbx_object_uid")}
        triangles.append(tri)
        for tag, vertex in zip(tri["u_tags"], tri["vertices_local"]):
            if tag in points:
                raise RuntimeError("CORNER_TAG_DUPLICATE:%s:%s" % (case["id"], tag))
            points[tag] = vertex
    validate_u_tags(points.keys())
    if set(points) != set(EXPECTED_U_TAGS):
        raise RuntimeError("CORNER_TAG_SET_MISMATCH:" + case["id"])
    face_membership = (len(triangles) == 6 and len(observed_materials) == 6 and
                       all(observed_materials.get(fid) == identity for fid, identity in expected_materials.items()))
    world = matrix_rows(obj.matrix_world)
    return {"case_id": case["id"], "input_sha256": case["sha256"],
            "mesh_name": obj.name, "mesh_world_matrix": world,
            "mesh_local_vertices": [[float(x) for x in v.co] for v in mesh.vertices],
            "triangles": triangles,
            "material_slot_names_diagnostic": [m.name if m else "" for m in mesh.materials],
            "face_membership_matches_fixture_material_identity": face_membership,
            "corner_points_by_u": {str(k): v for k, v in sorted(points.items())},
            "hierarchy": [{"name": x.name, "type": x.type, "parent_name": x.parent.name if x.parent else "",
                           "matrix_local": matrix_rows(x.matrix_local), "matrix_world": matrix_rows(x.matrix_world)}
                          for x in objects]}


def main():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if len(args) != 4:
        raise SystemExit("EXPECTED_MANIFEST_PREREG_DIR_EXPECTED_MANIFEST_SHA256_NEW_OUTPUT")
    manifest_path, prereg_dir = Path(args[0]).resolve(), Path(args[1]).resolve()
    expected_manifest_sha, output = args[2].lower(), Path(args[3]).resolve()
    actual_manifest_sha = sha256(manifest_path)
    if actual_manifest_sha != expected_manifest_sha:
        raise RuntimeError("MANIFEST_EXTERNAL_HASH_MISMATCH")
    prereg, prereg_hash = validate_prereg(prereg_dir)
    if bpy.app.version_string != ENGINE_VERSIONS["blender"]:
        raise RuntimeError("BLENDER_VERSION_MISMATCH:" + bpy.app.version_string)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema") != "vapb-coordinate-holdout-manifest-v1":
        raise RuntimeError("MANIFEST_SCHEMA_INVALID")
    if manifest.get("contract") != public_contract():
        raise RuntimeError("MANIFEST_CONTRACT_MISMATCH")
    if manifest.get("blender_version") != ENGINE_VERSIONS["blender"]:
        raise RuntimeError("MANIFEST_BLENDER_VERSION_MISMATCH")
    if manifest.get("preregistration_sha256") != prereg_hash:
        raise RuntimeError("MANIFEST_PREREGISTRATION_RECEIPT_MISMATCH")
    if manifest.get("source_sha256") != prereg.get("source_sha256"):
        raise RuntimeError("MANIFEST_SOURCE_RECEIPT_MISMATCH")
    cases = manifest.get("cases")
    if [row.get("id") for row in cases or []] != [row["id"] for row in CASES]:
        raise RuntimeError("CASE_SET_OR_ORDER_MISMATCH")
    contract_cases = {row["id"]: row for row in CASES}
    for row in cases:
        frozen = contract_cases[row["id"]]
        if row.get("filename") != row["id"] + ".fbx":
            raise RuntimeError("CASE_FILENAME_INVALID:" + row["id"])
        for key, expected in frozen.items():
            if row.get(key) != expected:
                raise RuntimeError("MANIFEST_CASE_CONTRACT_MISMATCH:%s:%s" % (row["id"], key))
        if not isinstance(row.get("sha256"), str) or len(row["sha256"]) != 64:
            raise RuntimeError("CASE_SHA256_INVALID:" + row["id"])
    oracle = json.loads((prereg_dir / "authored-oracle.json").read_text(encoding="utf-8"))
    if oracle.get("schema") != "vapb-coordinate-holdout-authored-oracle-v1":
        raise RuntimeError("AUTHORED_ORACLE_SCHEMA_INVALID")
    oracle_cases = {row["id"]: row for row in oracle["cases"]}
    captured = [capture_case(manifest_path.parent, case, oracle_cases[case["id"]]) for case in cases]
    by_id = {row["case_id"]: row for row in captured}

    authored_rows, authored_points = [], {}
    for case in cases:
        row = by_id[case["id"]]
        pred = oracle_cases[case["id"]]
        observed = {float(k): v for k, v in row["corner_points_by_u"].items()}
        expected = {float(c["u_tag"]): c["blender_local_authored"] for c in pred["corners"]}
        local_max = max(abs(observed[t][i] - expected[t][i]) for t in expected for i in range(3))
        expected_world = pred["blender_world_authored"]
        matrix_max = max(abs(row["mesh_world_matrix"][r][c] - expected_world[r][c])
                         for r in range(4) for c in range(4))
        world_corner_max = max(abs(point(row["mesh_world_matrix"], observed[t])[i] -
                                   pred["corners"][j]["blender_world_authored"][i])
                               for j, t in enumerate(EXPECTED_U_TAGS) for i in range(3))
        authored_rows.append({"case_id": case["id"], "max_abs_local_corner_delta": local_max,
                              "max_abs_world_matrix_delta": matrix_max,
                              "max_abs_world_corner_delta": world_corner_max,
                              "local_and_matrix_are_diagnostic_only": True,
                              "status": "PASS" if world_corner_max <= TOLERANCE else "FAIL"})
        authored_points[case["id"]] = observed

    def point_world(case_id, tag):
        return point(by_id[case_id]["mesh_world_matrix"], authored_points[case_id][tag])
    tags = EXPECTED_U_TAGS
    h0 = {tag: point_world("H0", tag) for tag in tags}
    h1_delta = max(abs(point_world("H1", tag)[i] - h0[tag][i]) for tag in tags for i in range(3))
    h2_delta = max(abs(point_world("H2", tag)[i] - .1*h0[tag][i]) for tag in tags for i in range(3))
    within = {"H1_world_minus_H0_max_abs": h1_delta,
              "H2_world_minus_0.1_times_H0_max_abs": h2_delta,
              "status": "PASS" if max(h1_delta, h2_delta) <= TOLERANCE else "FAIL"}
    blender_authored_status = "PASS" if all(row["status"] == "PASS" for row in authored_rows) else "FAIL"
    result = {"schema": "vapb-coordinate-holdout-blender-capture-v1",
              "blender_version": bpy.app.version_string,
              "blender_import_controls": BLENDER_IMPORT_CONTROLS,
              "manifest_sha256": sha256(manifest_path), "preregistration_sha256": prereg_hash,
              "candidate_status": "NOT_RUN_UNITY_CAPTURE_REQUIRED",
              "blender_face_identity": {"status": "PASS" if all(r["face_membership_matches_fixture_material_identity"] for r in captured) else "FAIL"},
              "blender_authored_hypothesis": {"status": blender_authored_status, "per_case": authored_rows},
              "within_tool_intervention": within,
              "cases": captured,
              "interpretation": "Blender-only authored checks. Candidate acceptance is not evaluated until Unity capture is paired."}
    if not finite_tree(result):
        raise RuntimeError("CAPTURE_NONFINITE")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
    print("BLENDER_AUTHORED_HYPOTHESIS=" + blender_authored_status)
    print("BLENDER_WITHIN_TOOL=" + within["status"])
    print("CANDIDATE_STATUS=NOT_RUN_UNITY_CAPTURE_REQUIRED")
    print("CAPTURE_SHA256=" + sha256(output))


if __name__ == "__main__":
    main()
