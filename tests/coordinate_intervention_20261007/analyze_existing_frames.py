"""Offline coordinate diagnostics for the pinned 2026-10-07 captures.

This report is exploratory. Its candidate matrices were inferred from all seven
observed cases, so no case is a held-out validation and no result is a product
acceptance decision.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path


CASE_IDS = (
    "baseline", "axis_only", "unit_only", "translation_only", "rotation_only",
    "positive_nonuniform_scale_only", "negative_scale_only",
)
INPUT_SHA256 = {
    "manifest": "b281b0f36c8652271514ed754291dfa3d0fa96d39db3dbc160aa14102df83043",
    "blender_capture": "00eaadf3a43e1bd9151a5df957e58d18bb62c91cbad4adfd55f2e20ed174b821",
    "unity_capture": "35a88f5f3cc3181ae87da35d89e7acd7749a245e5c2ea53eb73b0c8889ab29aa",
    "fixed_comparison": "98ae07472e88e036aac483ffbd8d094e400a27f41f7ff94bcc5a1bfee4c212e0",
}
CWORLD = (
    (-1.0, 0.0, 0.0, 0.0),
    (0.0, 0.0, 1.0, 0.0),
    (0.0, -1.0, 0.0, 0.0),
    (0.0, 0.0, 0.0, 1.0),
)


def matrix4(value):
    if isinstance(value, (list, tuple)) and len(value) == 16 and not isinstance(value[0], (list, tuple)):
        rows = [value[row * 4:(row + 1) * 4] for row in range(4)]
    elif isinstance(value, (list, tuple)) and len(value) == 4 and all(
            isinstance(row, (list, tuple)) and len(row) == 4 for row in value):
        rows = value
    else:
        raise ValueError("MATRIX_SHAPE_INVALID")
    result = tuple(tuple(float(component) for component in row) for row in rows)
    if not all(math.isfinite(component) for row in result for component in row):
        raise ValueError("MATRIX_NONFINITE")
    return result


def multiply(left, right):
    a, b = matrix4(left), matrix4(right)
    return tuple(tuple(sum(a[row][k] * b[k][column] for k in range(4))
                       for column in range(4)) for row in range(4))


def transform_point(matrix, point):
    rows = matrix4(matrix)
    if isinstance(point, dict):
        if any(key not in point for key in ("x", "y", "z")):
            raise ValueError("VECTOR_COMPONENT_MISSING")
        values = (point["x"], point["y"], point["z"])
    elif isinstance(point, (list, tuple)) and len(point) == 3:
        values = point
    else:
        raise ValueError("VECTOR_SHAPE_INVALID")
    xyz = tuple(float(value) for value in values)
    if not all(math.isfinite(value) for value in xyz):
        raise ValueError("VECTOR_NONFINITE")
    homogeneous = xyz + (1.0,)
    result = tuple(sum(rows[row][column] * homogeneous[column] for column in range(4))
                   for row in range(4))
    if abs(result[3]) < 1.0e-12:
        raise ValueError("POINT_TRANSFORM_W_ZERO")
    output = tuple(value / result[3] for value in result[:3])
    if not all(math.isfinite(value) for value in output):
        raise ValueError("TRANSFORMED_POINT_NONFINITE")
    return output


def local_conversion(scale):
    scale = float(scale)
    if not math.isfinite(scale) or scale <= 0.0:
        raise ValueError("UNIT_RATIO_INVALID")
    return ((-scale, 0.0, 0.0, 0.0),
            (0.0, scale, 0.0, 0.0),
            (0.0, 0.0, scale, 0.0),
            (0.0, 0.0, 0.0, 1.0))


def _tag(uv):
    if isinstance(uv, dict):
        if "x" not in uv or "y" not in uv:
            raise ValueError("CORNER_UV_COMPONENT_MISSING")
        raw = (uv["x"], uv["y"])
    elif isinstance(uv, (list, tuple)) and len(uv) == 2:
        raw = uv
    else:
        raise ValueError("CORNER_UV_SHAPE_INVALID")
    values = tuple(float(value) for value in raw)
    if not all(math.isfinite(value) for value in values):
        raise ValueError("CORNER_UV_NONFINITE")
    return values


def _corner_map(case, tool):
    points = {}
    if tool == "blender":
        meshes = [row for row in case.get("hierarchy", []) if row.get("type") == "MESH"]
        if len(meshes) != 1:
            raise ValueError("BLENDER_MESH_TRANSFORM_NOT_UNIQUE:" + case.get("case_id", "?"))
        world = matrix4(meshes[0].get("matrix_world"))
        triangles = case.get("triangles")
        if not isinstance(triangles, list) or not triangles:
            raise ValueError("BLENDER_TRIANGLES_MISSING:" + case.get("case_id", "?"))
        for triangle in triangles:
            uvs, vertices = triangle.get("uvs"), triangle.get("vertices_local")
            if not isinstance(uvs, list) or not isinstance(vertices, list) or len(uvs) != 3 or len(vertices) != 3:
                raise ValueError("BLENDER_CORNER_INPUT_INVALID:" + case.get("case_id", "?"))
            for uv, vertex in zip(uvs, vertices):
                tag = _tag(uv)
                if tag in points:
                    raise ValueError("CORNER_TAG_DUPLICATE:%s:%s" % (tool, tag))
                points[tag] = tuple(float(value) for value in vertex)
        return points, world

    renderers = case.get("renderers")
    if not isinstance(renderers, list) or len(renderers) != 1:
        raise ValueError("UNITY_RENDERER_NOT_UNIQUE:" + case.get("case_id", "?"))
    renderer = renderers[0]
    path = renderer.get("transform_path")
    transforms = [row for row in case.get("hierarchy", []) if row.get("path") == path]
    if len(transforms) != 1:
        raise ValueError("UNITY_RENDERER_TRANSFORM_NOT_UNIQUE:" + case.get("case_id", "?"))
    world = matrix4(transforms[0].get("world_matrix"))
    vertices = renderer.get("vertices_local")
    submeshes = renderer.get("submeshes")
    if not isinstance(vertices, list) or not isinstance(submeshes, list) or not submeshes:
        raise ValueError("UNITY_CORNER_INPUT_MISSING:" + case.get("case_id", "?"))
    for submesh in submeshes:
        faces = submesh.get("faces")
        if not isinstance(faces, list):
            raise ValueError("UNITY_FACE_INPUT_MISSING:" + case.get("case_id", "?"))
        for face in faces:
            uvs, indices = face.get("corner_uvs"), face.get("vertex_indices")
            if not isinstance(uvs, list) or not isinstance(indices, list) or len(uvs) != 3 or len(indices) != 3:
                raise ValueError("UNITY_CORNER_INPUT_INVALID:" + case.get("case_id", "?"))
            for uv, index in zip(uvs, indices):
                if not isinstance(index, int) or index < 0 or index >= len(vertices):
                    raise ValueError("UNITY_VERTEX_INDEX_INVALID:" + case.get("case_id", "?"))
                tag = _tag(uv)
                if tag in points:
                    raise ValueError("CORNER_TAG_DUPLICATE:%s:%s" % (tool, tag))
                point = vertices[index]
                if isinstance(point, dict):
                    if any(key not in point for key in ("x", "y", "z")):
                        raise ValueError("VECTOR_COMPONENT_MISSING")
                    points[tag] = tuple(float(point[key]) for key in ("x", "y", "z"))
                elif isinstance(point, (list, tuple)) and len(point) == 3:
                    points[tag] = tuple(float(value) for value in point)
                else:
                    raise ValueError("VECTOR_SHAPE_INVALID")
    if not points:
        raise ValueError("UNITY_CORNER_INPUT_EMPTY:" + case.get("case_id", "?"))
    return points, world


def _vector_max(values):
    return max((abs(float(value)) for value in values), default=0.0)


def _matrix_max(left, right):
    a, b = matrix4(left), matrix4(right)
    return max(abs(a[row][column] - b[row][column])
               for row in range(4) for column in range(4))


def frame_residuals(blender_vertex, unity_vertex, blender_world, unity_world, unit_ratio):
    """Evaluate the three candidate equations for one UV-tagged corner."""
    d = local_conversion(unit_ratio)
    blender_world = matrix4(blender_world)
    unity_world = matrix4(unity_world)
    converted_local = transform_point(d, blender_vertex)
    blender_point = transform_point(blender_world, blender_vertex)
    unity_point = transform_point(unity_world, unity_vertex)
    converted_chain_point = transform_point(unity_world, converted_local)
    candidate_point = transform_point(CWORLD, blender_point)
    local_delta = tuple(unity_vertex[i] - converted_local[i] for i in range(3))
    chain_delta = tuple(converted_chain_point[i] - candidate_point[i] for i in range(3))
    observed_delta = tuple(unity_point[i] - candidate_point[i] for i in range(3))
    matrix_delta = _matrix_max(multiply(unity_world, d), multiply(CWORLD, blender_world))
    return {
        "local_vu_minus_dc_vb": local_delta,
        "world_wu_dc_vb_minus_cwb_vb": chain_delta,
        "world_pu_minus_cpb": observed_delta,
        "matrix_max_abs_wu_dc_minus_cwb": matrix_delta,
    }


def analyze_payloads(manifest, blender, unity, fixed_comparison, input_hashes):
    if input_hashes != INPUT_SHA256:
        raise ValueError("INPUT_SHA256_RECEIPT_MISMATCH")
    if blender.get("manifest_sha256") != input_hashes["manifest"] or unity.get("manifest_sha256") != input_hashes["manifest"]:
        raise ValueError("CAPTURE_MANIFEST_RECEIPT_MISMATCH")
    manifest_cases = manifest.get("cases")
    blender_cases = blender.get("cases")
    unity_cases = unity.get("cases")
    if not all(isinstance(rows, list) for rows in (manifest_cases, blender_cases, unity_cases)):
        raise ValueError("CASE_LIST_MISSING")
    if ([row.get("id") for row in manifest_cases] != list(CASE_IDS)
            or [row.get("case_id") for row in blender_cases] != list(CASE_IDS)
            or [row.get("case_id") for row in unity_cases] != list(CASE_IDS)):
        raise ValueError("CASE_SET_OR_ORDER_MISMATCH")
    comparison_cases = {row.get("case_id"): row for row in fixed_comparison.get("cases", [])}
    if set(comparison_cases) != set(CASE_IDS):
        raise ValueError("FIXED_COMPARISON_CASE_SET_MISMATCH")
    expected_tags = {_tag(uv) for face in manifest["spec"]["geometry"]["faces"] for uv in face["uvs"]}
    if len(expected_tags) != 18:
        raise ValueError("EXPECTED_CORNER_SET_INVALID")

    b_by_id = {row["case_id"]: row for row in blender_cases}
    u_by_id = {row["case_id"]: row for row in unity_cases}
    manifest_baseline = manifest_cases[0]
    unit_case = next(row for row in manifest_cases if row["id"] == "unit_only")
    baseline_raw_unit = float(manifest_baseline["raw_fbx"]["global_settings"]["UnitScaleFactor"])
    unit_raw = float(unit_case["raw_fbx"]["global_settings"]["UnitScaleFactor"])
    raw_unit_ratio = unit_raw / baseline_raw_unit
    authored_unit_ratio = float(unit_case["unit_scale_length"]) / float(manifest_baseline["unit_scale_length"])
    if (not math.isfinite(raw_unit_ratio) or raw_unit_ratio <= 0.0
            or not math.isfinite(authored_unit_ratio) or authored_unit_ratio <= 0.0):
        raise ValueError("UNIT_SCALE_RATIO_INVALID")
    for manifest_case in manifest_cases:
        case_id = manifest_case["id"]
        expected_hash = manifest_case.get("sha256")
        if not expected_hash or b_by_id.get(case_id, {}).get("input_sha256") != expected_hash:
            raise ValueError("BLENDER_CASE_INPUT_RECEIPT_MISMATCH:" + case_id)
        if u_by_id.get(case_id, {}).get("input_sha256") != expected_hash:
            raise ValueError("UNITY_CASE_INPUT_RECEIPT_MISMATCH:" + case_id)

    per_case = []
    all_corners = []
    world_by_tool = {"blender": {}, "unity": {}}
    for case_id in CASE_IDS:
        b_points, b_world = _corner_map(b_by_id[case_id], "blender")
        u_points, u_world = _corner_map(u_by_id[case_id], "unity")
        if set(b_points) != expected_tags or set(u_points) != expected_tags:
            raise ValueError("CORNER_TAG_SET_MISMATCH:" + case_id)
        scale = authored_unit_ratio if case_id == "unit_only" else 1.0
        d = local_conversion(scale)
        matrix_residual = _matrix_max(multiply(u_world, d), multiply(CWORLD, b_world))
        maxima = {"local_vu_minus_dc_vb": 0.0, "world_wu_dc_vb_minus_cwb_vb": 0.0,
                  "world_pu_minus_cpb": 0.0}
        for tag in sorted(expected_tags):
            vb, vu = b_points[tag], u_points[tag]
            residuals = frame_residuals(vb, vu, b_world, u_world, scale)
            local_delta = residuals["local_vu_minus_dc_vb"]
            pb = transform_point(b_world, vb)
            pu = transform_point(u_world, vu)
            chain_delta = residuals["world_wu_dc_vb_minus_cwb_vb"]
            observed_delta = residuals["world_pu_minus_cpb"]
            maxima["local_vu_minus_dc_vb"] = max(maxima["local_vu_minus_dc_vb"], _vector_max(local_delta))
            maxima["world_wu_dc_vb_minus_cwb_vb"] = max(maxima["world_wu_dc_vb_minus_cwb_vb"], _vector_max(chain_delta))
            maxima["world_pu_minus_cpb"] = max(maxima["world_pu_minus_cpb"], _vector_max(observed_delta))
            all_corners.append({
                "case_id": case_id,
                "corner_tag": [tag[0], tag[1]],
                "local_vu_minus_dc_vb": list(local_delta),
                "world_wu_dc_vb_minus_cwb_vb": list(chain_delta),
                "world_pu_minus_cpb": list(observed_delta),
            })
            world_by_tool["blender"].setdefault(case_id, {})[tag] = pb
            world_by_tool["unity"].setdefault(case_id, {})[tag] = pu
        per_case.append({
            "case_id": case_id,
            "raw_fbx_unit_scale_factor": float(next(row for row in manifest_cases if row["id"] == case_id)["raw_fbx"]["global_settings"]["UnitScaleFactor"]),
            "authored_unit_scale_length": float(next(row for row in manifest_cases if row["id"] == case_id)["unit_scale_length"]),
            "local_unit_ratio_applied_to_blender_vertices": scale,
            "max_abs_matrix_wu_dc_minus_cwb": matrix_residual,
            "max_abs_corner_residuals": maxima,
            "fixed_direct_comparison_status": comparison_cases[case_id].get("status"),
            "fixed_direct_max_world_corner_component_delta": comparison_cases[case_id].get("max_world_corner_component_delta_blender_vs_unity"),
        })

    cross_case = {}
    for tool in ("blender", "unity"):
        baseline_worlds = world_by_tool[tool]["baseline"]
        axis = world_by_tool[tool]["axis_only"]
        unit = world_by_tool[tool]["unit_only"]
        cross_case[tool] = {
            "axis_only_world_minus_baseline_world_max_abs": max(
                _vector_max(tuple(axis[tag][i] - baseline_worlds[tag][i] for i in range(3))) for tag in expected_tags),
            "unit_only_world_minus_authored_unit_ratio_times_baseline_max_abs": max(
                _vector_max(tuple(unit[tag][i] - authored_unit_ratio * baseline_worlds[tag][i] for i in range(3)))
                for tag in expected_tags),
        }

    return {
        "schema": "vapb-coordinate-intervention-exploratory-frame-analysis-v1",
        "status": "EXPLORATORY_DATA_DERIVED_CANDIDATE_NO_HOLDOUT",
        "holdout_validated": False,
        "interpretation": (
            "Candidate Cworld and D were inferred after observing all seven cases. "
            "This is diagnostic evidence, not calibration, a held-out prediction, or product acceptance."
        ),
        "inputs": input_hashes,
        "fixed_comparator": {
            "status": fixed_comparison.get("status"),
            "mapping": fixed_comparison.get("mapping"),
            "tolerance": fixed_comparison.get("tolerance"),
            "holdout_validated": False,
            "meaning": "Original comparator output is reported as received and was not changed or recomputed here.",
        },
        "candidates": {
            "Cworld": [list(row) for row in CWORLD],
            "D_c": "diag(-s_c, s_c, s_c, 1); s_c=0.01 only for unit_only, otherwise 1",
            "unit_scale_ratio_source": {
                "baseline_authored_unit_scale_length": float(manifest_baseline["unit_scale_length"]),
                "unit_only_authored_unit_scale_length": float(unit_case["unit_scale_length"]),
                "authored_ratio_used_for_D_c": authored_unit_ratio,
                "baseline_raw_fbx_UnitScaleFactor": baseline_raw_unit,
                "unit_only_raw_fbx_UnitScaleFactor": unit_raw,
                "raw_metadata_ratio_diagnostic_only": raw_unit_ratio,
                "meaning": "D_c uses the authored unit-scale ratio; the raw FBX metadata ratio is reported separately.",
            },
            "equations": [
                "V_U - D_c V_B",
                "W_U D_c - Cworld W_B",
                "P_U - Cworld P_B",
            ],
        },
        "observed_local_and_world_diagnostics": per_case,
        "same_tool_intervention_diagnostics": cross_case,
        "corner_residuals": all_corners,
        "scope_notes": [
            "All seven observed cases were used to identify the candidate; none is held out.",
            "Each capture has one mesh/renderer root and no parent chain; parent composition is tested only by pure algebra tests.",
            "Face membership remains limited to fixture-authored UV identities and the unique fixture-name material join.",
            "The production GUID/fileID to native submesh to source-face bridge is not independently established.",
            "Winding and normals are outside this diagnostic report.",
        ],
    }


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_fixed_report():
    root = Path(__file__).resolve().parents[2]
    evidence = root / "tests" / "evidence" / "coordinate_intervention_20261007"
    inputs = {
        "manifest": evidence / "final" / "manifest.json",
        "blender_capture": evidence / "final" / "blender-capture.json",
        "unity_capture": evidence / "unity-run-01" / "unity-capture.json",
        "fixed_comparison": evidence / "unity-run-01" / "comparison.json",
    }
    actual_hashes = {key: _sha256(path) for key, path in inputs.items()}
    if actual_hashes != INPUT_SHA256:
        raise ValueError("INPUT_SHA256_RECEIPT_MISMATCH")
    payloads = {key: json.loads(path.read_text(encoding="utf-8")) for key, path in inputs.items()}
    report = analyze_payloads(payloads["manifest"], payloads["blender_capture"],
                              payloads["unity_capture"], payloads["fixed_comparison"], actual_hashes)
    output_dir = evidence / "offline-analysis-01"
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / "report-authored-unit.json"
    if output.resolve() in {path.resolve() for path in inputs.values()}:
        raise ValueError("OUTPUT_ALIASES_INPUT")
    encoded = json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n"
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(encoded)
    return output


if __name__ == "__main__":
    print(run_fixed_report())
