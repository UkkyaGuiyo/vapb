"""Compare two importer observations by authored corner UV identity, without fitting."""
from __future__ import annotations

import json
import math
from pathlib import Path


TOLERANCE = 1.0e-4
IMPORTER_FIELDS = (
    "bake_axis_conversion", "use_file_scale", "use_file_units", "global_scale",
    "import_normals", "import_tangents", "preserve_hierarchy", "mesh_compression",
)


def _vector(value, dimensions):
    keys = ("x", "y", "z")[:dimensions]
    if isinstance(value, dict):
        if any(key not in value for key in keys):
            raise ValueError("VECTOR_COMPONENT_MISSING")
        values = [value[key] for key in keys]
    elif isinstance(value, (list, tuple)) and len(value) == dimensions:
        values = value
    else:
        raise ValueError("VECTOR_SHAPE_INVALID")
    result = tuple(float(component) for component in values)
    if not all(math.isfinite(component) for component in result):
        raise ValueError("VECTOR_NONFINITE")
    return result


def _matrix4(value):
    if len(value) == 16 and not isinstance(value[0], (list, tuple)):
        rows = [list(value[row * 4:(row + 1) * 4]) for row in range(4)]
    elif len(value) == 4 and all(hasattr(row, "__len__") and len(row) == 4 for row in value):
        rows = value
    else:
        raise ValueError("MATRIX_SHAPE_INVALID")
    if not all(math.isfinite(float(component)) for row in rows for component in row):
        raise ValueError("MATRIX_NONFINITE")
    return rows


def transform_point(matrix, point):
    rows = _matrix4(matrix)
    homogeneous = list(_vector(point, 3)) + [1.0]
    result = [sum(float(rows[row][column]) * homogeneous[column] for column in range(4))
              for row in range(4)]
    if abs(result[3]) < 1.0e-12:
        raise ValueError("POINT_TRANSFORM_W_ZERO")
    point = tuple(value / result[3] for value in result[:3])
    if not all(math.isfinite(value) for value in point):
        raise ValueError("TRANSFORMED_POINT_NONFINITE")
    return point


def point_deltas(blender_points, unity_points):
    errors = []
    max_component = 0.0
    for key in sorted(set(blender_points) | set(unity_points)):
        if key not in blender_points or key not in unity_points:
            errors.append("CORNER_ID_MISSING:%s" % key)
            continue
        b_point, u_point = _vector(blender_points[key], 3), _vector(unity_points[key], 3)
        delta = tuple(u - b for b, u in zip(b_point, u_point))
        if not all(math.isfinite(value) for value in delta):
            errors.append("WORLD_CORNER_DELTA_NONFINITE:%s" % key)
            continue
        maximum = max(abs(value) for value in delta)
        max_component = max(max_component, maximum)
        if maximum > TOLERANCE:
            errors.append("WORLD_CORNER_DELTA_OVER_TOLERANCE:%s:%g" % (key, maximum))
    return max_component, errors


def partition_errors(expected_by_face, observed_by_face, label):
    errors = []
    for face_id in sorted(set(expected_by_face) | set(observed_by_face)):
        expected = expected_by_face.get(face_id)
        observed = observed_by_face.get(face_id)
        if expected != observed:
            errors.append("%s_FACE_MATERIAL_MISMATCH:%s:%s:%s" % (label, face_id, expected, observed))
    return errors


def _u_tag(uv):
    return str(round(_vector(uv, 2)[0] * 1000.0))


def _blender_case(case):
    mesh_rows = [row for row in case["hierarchy"] if row["type"] == "MESH"]
    if len(mesh_rows) != 1:
        raise ValueError("BLENDER_MESH_TRANSFORM_NOT_UNIQUE:" + case["case_id"])
    matrix = mesh_rows[0]["matrix_world"]
    points = {}
    materials = {}
    for triangle in case["triangles"]:
        face_id = triangle["face_id_by_uv"]
        materials[face_id] = triangle["material_id_from_pinned_source_connection"]
        if len(triangle["uvs"]) != 3 or len(triangle["vertices_local"]) != 3:
            raise ValueError("BLENDER_TRIANGLE_CORNER_COUNT_INVALID:" + case["case_id"])
        for uv, point in zip(triangle["uvs"], triangle["vertices_local"]):
            tag = _u_tag(uv)
            if tag in points:
                raise ValueError("BLENDER_CORNER_TAG_NOT_UNIQUE:" + tag)
            points[tag] = transform_point(matrix, point)
    return points, materials


def _unity_case(case):
    if len(case["renderers"]) != 1:
        raise ValueError("UNITY_RENDERER_NOT_UNIQUE:" + case["case_id"])
    renderer = case["renderers"][0]
    transforms = [row for row in case["hierarchy"] if row["path"] == renderer["transform_path"]]
    if len(transforms) != 1:
        raise ValueError("UNITY_RENDERER_TRANSFORM_NOT_UNIQUE:" + case["case_id"])
    matrix = transforms[0]["world_matrix"]
    points = {}
    materials = {}
    for submesh in renderer["submeshes"]:
        for face in submesh["faces"]:
            face_id = face["face_id_by_corner_uv"]
            materials[face_id] = face["renderer_material_id"]
            if len(face["corner_uvs"]) != 3 or len(face["vertex_indices"]) != 3:
                raise ValueError("UNITY_TRIANGLE_CORNER_COUNT_INVALID:" + case["case_id"])
            for uv, vertex_index in zip(face["corner_uvs"], face["vertex_indices"]):
                tag = _u_tag(uv)
                if tag in points:
                    raise ValueError("UNITY_CORNER_TAG_NOT_UNIQUE:" + tag)
                points[tag] = transform_point(matrix, renderer["vertices_local"][vertex_index])
    return points, materials


def _unity_material_identity_errors(case, fixture_case):
    if len(case["renderers"]) != 1:
        return ["UNITY_MATERIAL_RENDERER_NOT_UNIQUE:" + case["case_id"]]
    ids = fixture_case.get("source_material_ids", [])
    uids = fixture_case.get("source_material_fbx_uids", [])
    if len(ids) != len(uids) or len(ids) != 3:
        return ["UNITY_SOURCE_MATERIAL_MAP_INVALID:" + case["case_id"]]
    expected = dict(zip(ids, uids))
    observed_ids = {}
    errors = []
    renderer = case["renderers"][0]
    rows = renderer["materials"]
    expected_path = "Assets/VapbCoordinateIntervention/" + fixture_case["filename"]
    if len(rows) != len(expected):
        errors.append("UNITY_IMPORTED_MATERIAL_ROW_COUNT_INVALID:" + case["case_id"])
    for row in rows:
        logical_id = row.get("fixture_material_id_from_pinned_input_connection", "")
        source_uid = row.get("source_fbx_material_object_uid", 0)
        try:
            source_uid_matches = logical_id in expected and int(source_uid) == int(expected[logical_id])
        except (TypeError, ValueError, OverflowError):
            source_uid_matches = False
        if not source_uid_matches:
            errors.append("UNITY_SOURCE_MATERIAL_OBJECT_ID_MISMATCH:%s:%s" % (case["case_id"], logical_id))
        if not row.get("guid") or not row.get("local_file_id"):
            errors.append("UNITY_IMPORTED_MATERIAL_ASSET_ID_MISSING:%s:%s" % (case["case_id"], logical_id))
        if row.get("imported_asset_path") != expected_path:
            errors.append("UNITY_IMPORTED_MATERIAL_ASSET_PATH_INVALID:%s:%s" % (case["case_id"], logical_id))
        if row.get("guid") != renderer.get("mesh_guid"):
            errors.append("UNITY_MATERIAL_NOT_EMBEDDED_IN_FIXTURE_ASSET:%s:%s" % (case["case_id"], logical_id))
        if logical_id in observed_ids:
            errors.append("UNITY_IMPORTED_MATERIAL_ID_DUPLICATE:%s:%s" % (case["case_id"], logical_id))
        observed_ids[logical_id] = (row.get("guid"), row.get("local_file_id"))
    if set(observed_ids) != set(expected):
        errors.append("UNITY_IMPORTED_MATERIAL_SET_MISMATCH:" + case["case_id"])
    if len(set(observed_ids.values())) != len(observed_ids):
        errors.append("UNITY_IMPORTED_MATERIAL_ASSET_IDS_NOT_UNIQUE:" + case["case_id"])
    return errors


def _capture_preflight(manifest, blender, unity, expected_manifest_sha256):
    errors = []
    if blender.get("schema") != "vapb-coordinate-intervention-blender-capture-v1":
        errors.append("BLENDER_SCHEMA_INVALID")
    if unity.get("schema") != "vapb-coordinate-intervention-unity-capture-v1":
        errors.append("UNITY_SCHEMA_INVALID")
    if blender.get("status") != "BLENDER_FACE_IDENTITY_PASS":
        errors.append("BLENDER_CAPTURE_NOT_PASS")
    if blender.get("blender_version") != manifest.get("blender_version"):
        errors.append("BLENDER_VERSION_MISMATCH")
    if unity.get("status") != "UNITY_FACE_IDENTITY_CAPTURED":
        errors.append("UNITY_CAPTURE_NOT_PASS")
    if unity.get("errors") != []:
        errors.append("UNITY_CAPTURE_ERRORS_PRESENT")
    if unity.get("unity_version") != "2022.3.22f1":
        errors.append("UNITY_VERSION_INVALID")
    if unity.get("material_identity_join_method") != "fixture-authored-unique-material-name":
        errors.append("UNITY_MATERIAL_IDENTITY_JOIN_METHOD_UNDECLARED")
    for label, capture in (("BLENDER", blender), ("UNITY", unity)):
        if capture.get("manifest_sha256") != expected_manifest_sha256:
            errors.append(label + "_MANIFEST_RECEIPT_MISMATCH")
    return errors


def _expected_corner_tags(manifest):
    return {str(round(float(uv["x"]) * 1000.0))
            for face in manifest["spec"]["geometry"]["faces"] for uv in face["uvs"]}


def _validate_case_payload(case, label, expected_faces, expected_tags):
    errors = []
    if label == "UNITY":
        if case.get("face_membership_matches_source_identity") is not True:
            errors.append("UNITY_FACE_MEMBERSHIP_FLAG_FALSE:" + case.get("case_id", "?"))
        if case.get("unmatched_face_count") != 0:
            errors.append("UNITY_UNMATCHED_FACE_COUNT_NONZERO:" + case.get("case_id", "?"))
        settings = case.get("importer")
        if not isinstance(settings, dict) or any(settings.get(key) is None for key in IMPORTER_FIELDS):
            errors.append("UNITY_IMPORTER_SETTINGS_INCOMPLETE:" + case.get("case_id", "?"))
        renderers = case.get("renderers") or []
        if len(renderers) != 1:
            errors.append("UNITY_RENDERER_COUNT_INVALID:" + case.get("case_id", "?"))
        else:
            renderer = renderers[0]
            if not renderer.get("mesh_guid") or not renderer.get("mesh_local_file_id"):
                errors.append("UNITY_MESH_ASSET_IDENTITY_MISSING:" + case.get("case_id", "?"))
            observed_faces = [face for submesh in renderer.get("submeshes", [])
                              for face in submesh.get("faces", [])]
            if len(observed_faces) != len(expected_faces) or any(
                    len(face.get("corner_uvs", [])) != 3
                    or len(face.get("vertex_indices", [])) != 3 for face in observed_faces):
                errors.append("UNITY_FACE_CORNER_CARDINALITY_INVALID:" + case.get("case_id", "?"))
    else:
        if case.get("face_membership_matches_source_identity") is not True:
            errors.append("BLENDER_FACE_MEMBERSHIP_FLAG_FALSE:" + case.get("case_id", "?"))
        if case.get("unmatched_face_count") != 0:
            errors.append("BLENDER_UNMATCHED_FACE_COUNT_NONZERO:" + case.get("case_id", "?"))
        triangles = case.get("triangles") or []
        if len(triangles) != len(expected_faces):
            errors.append("BLENDER_TRIANGLE_COUNT_INVALID:" + case.get("case_id", "?"))
    try:
        points, materials = _unity_case(case) if label == "UNITY" else _blender_case(case)
        if set(materials) != set(expected_faces):
            errors.append(label + "_FACE_SET_INCOMPLETE:" + case.get("case_id", "?"))
        if set(points) != expected_tags or len(points) != len(expected_tags):
            errors.append(label + "_CORNER_TAG_SET_INCOMPLETE:" + case.get("case_id", "?"))
    except (KeyError, TypeError, ValueError, IndexError, OverflowError) as exc:
        errors.append(label + "_PAYLOAD_INVALID:" + str(exc))
    return errors


def compare_payloads(manifest, blender, unity, expected_manifest_sha256):
    source_faces = manifest["spec"]["geometry"]["faces"]
    if len(source_faces) != 6:
        return {"status": "COORDINATE_AND_FACE_IDENTITY_UNPROVEN", "mapping": None,
                "errors": ["EXPECTED_FACE_CARDINALITY_INVALID"], "cases": []}
    expected = {face["face_id"]: face["material"] for face in source_faces}
    case_ids = [case["id"] for case in manifest["cases"]]
    cases_b, cases_u = blender.get("cases", []), unity.get("cases", [])
    if (len(case_ids) != 7 or len(set(case_ids)) != 7
            or len(cases_b) != 7 or len(cases_u) != 7
            or len({case.get("case_id") for case in cases_b}) != 7
            or len({case.get("case_id") for case in cases_u}) != 7):
        return {"status": "COORDINATE_AND_FACE_IDENTITY_UNPROVEN", "mapping": None,
                "errors": ["CASE_CARDINALITY_OR_UNIQUENESS_INVALID"], "cases": []}
    case_map_b = {case["case_id"]: case for case in cases_b}
    case_map_u = {case["case_id"]: case for case in cases_u}
    result_cases = []
    errors = _capture_preflight(manifest, blender, unity, expected_manifest_sha256)
    if set(case_map_b) != set(case_ids) or set(case_map_u) != set(case_ids):
        return {"status": "COORDINATE_AND_FACE_IDENTITY_UNPROVEN", "mapping": None,
                "errors": ["CASE_SET_MISMATCH"], "cases": []}

    expected_tags = _expected_corner_tags(manifest)
    if len(expected_tags) != 18:
        return {"status": "COORDINATE_AND_FACE_IDENTITY_UNPROVEN", "mapping": None,
                "errors": ["EXPECTED_CORNER_TAG_CARDINALITY_INVALID"], "cases": []}
    for fixture_case in manifest["cases"]:
        case_id = fixture_case["id"]
        b_case, u_case = case_map_b[case_id], case_map_u[case_id]
        case_errors = (_validate_case_payload(b_case, "BLENDER", expected, expected_tags)
                       + _validate_case_payload(u_case, "UNITY", expected, expected_tags))
        if case_errors:
            errors.extend(case_errors)
            result_cases.append({"case_id": case_id, "factor": fixture_case["factor"],
                                 "input_hash_match": False, "status": "UNPROVEN",
                                 "errors": case_errors})
            continue
        observed_b_points, observed_b_materials = _blender_case(b_case)
        observed_u_points, observed_u_materials = _unity_case(u_case)
        material_errors = (partition_errors(expected, observed_b_materials, "BLENDER")
                           + partition_errors(expected, observed_u_materials, "UNITY"))
        material_errors.extend(_unity_material_identity_errors(case_map_u[case_id], fixture_case))
        point_delta, point_errors = point_deltas(observed_b_points, observed_u_points)
        input_hash_match = (case_map_b[case_id].get("input_sha256") == fixture_case.get("sha256")
                            and case_map_u[case_id].get("input_sha256") == fixture_case.get("sha256"))
        if not input_hash_match:
            errors.append("INPUT_HASH_MISMATCH:" + case_id)
        case_errors.extend(material_errors + point_errors)
        errors.extend(case_errors)
        result_cases.append({
            "case_id": case_id,
            "factor": fixture_case["factor"],
            "input_hash_match": input_hash_match,
            "max_world_corner_component_delta_blender_vs_unity": point_delta,
            "blender_face_material_errors": [e for e in material_errors if e.startswith("BLENDER_")],
            "unity_face_material_errors": [e for e in material_errors if e.startswith("UNITY_")],
            "coordinate_errors": point_errors,
            "status": "OBSERVATION_MATCH" if input_hash_match and not case_errors else "UNPROVEN",
        })

    settings = [case.get("importer") for case in unity["cases"]]
    settings_stable = (bool(settings) and all(isinstance(item, dict)
                         and all(item.get(key) is not None for key in IMPORTER_FIELDS)
                         for item in settings)
                       and all(item == settings[0] for item in settings[1:]))
    if not settings_stable:
        errors.append("UNITY_IMPORTER_SETTINGS_NOT_CONSTANT")
    passed = not errors and blender.get("status") == "BLENDER_FACE_IDENTITY_PASS"
    return {
        "schema": "vapb-coordinate-intervention-comparison-v1",
        "status": "COORDINATE_AND_FACE_IDENTITY_PASS" if passed else "COORDINATE_AND_FACE_IDENTITY_UNPROVEN",
        "mapping": None,
        "tolerance": TOLERANCE,
        "unity_importer_settings_constant": settings_stable,
        "errors": errors,
        "cases": result_cases,
        "interpretation": "A bounded importer comparison only; no product mapping or global coordinate rule is adopted.",
    }


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("blender_capture", type=Path)
    parser.add_argument("unity_capture", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    manifest_text = args.manifest.read_text(encoding="utf-8")
    manifest_sha256 = __import__("hashlib").sha256(manifest_text.encode("utf-8")).hexdigest()
    payload = compare_payloads(
        json.loads(manifest_text),
        json.loads(args.blender_capture.read_text(encoding="utf-8")),
        json.loads(args.unity_capture.read_text(encoding="utf-8")),
        manifest_sha256,
    )
    with args.output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(payload, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print("VAPB_COORDINATE_COMPARISON=" + payload["status"])
    print("ERRORS=" + str(len(payload["errors"])))


if __name__ == "__main__":
    main()
