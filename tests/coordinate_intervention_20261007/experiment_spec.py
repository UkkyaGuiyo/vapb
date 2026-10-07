"""Pinned one-factor fixture contract for the Unity/Blender coordinate probe."""

from copy import deepcopy


GEOMETRY_ID = "vapb-coordinate-intervention-20261007-v1"
MATERIAL_IDS = ("fixture-material-A", "fixture-material-B", "fixture-material-C")
EXPORT_CONTROLS = {
    "global_scale": 1.0,
    "apply_scale_options": "FBX_SCALE_UNITS",
    "apply_unit_scale": True,
    "bake_space_transform": False,
    "bake_anim": False,
    "add_leaf_bones": False,
    "use_mesh_modifiers": False,
    "use_custom_props": True,
    "object_types": ["MESH"],
}

# Six unequal, non-coplanar triangles, with exactly two faces per intended partition.
_TRIANGLES = (
    ((0.13, 0.21, 0.37), (1.71, 0.24, 0.41), (0.31, 1.48, 0.62)),
    ((0.22, 0.33, 1.17), (1.62, 0.51, 1.39), (0.44, 1.31, 1.72)),
    ((-0.47, 0.18, 0.26), (-1.58, 0.52, 0.49), (-0.24, 1.27, 0.88)),
    ((-0.38, 0.29, 1.08), (-1.73, 0.42, 1.56), (-0.19, 1.64, 1.21)),
    ((0.19, -0.41, 0.56), (1.43, -0.22, 0.91), (0.36, -1.62, 0.68)),
    ((0.28, -0.35, 1.37), (1.84, -0.57, 1.62), (0.53, -1.39, 1.91)),
)

_VERTICES = []
_FACES = []
for face_index, triangle in enumerate(_TRIANGLES):
    first = len(_VERTICES)
    _VERTICES.extend(triangle)
    uv_base = face_index * 10.0
    _FACES.append({
        "face_id": "face-%02d" % face_index,
        "material": MATERIAL_IDS[face_index // 2],
        "vertices": [first, first + 1, first + 2],
        "uvs": [[uv_base, 0.125], [uv_base + 1.0, 0.25], [uv_base + 2.0, 0.375]],
    })

GEOMETRY = {
    "geometry_id": GEOMETRY_ID,
    "materials": list(MATERIAL_IDS),
    "vertices": [list(vertex) for vertex in _VERTICES],
    "faces": _FACES,
}

_BASE = {
    "geometry_id": GEOMETRY_ID,
    "material_ids": list(MATERIAL_IDS),
    "face_material_ids": [face["material"] for face in _FACES],
    "corner_uv_ids": [face["uvs"] for face in _FACES],
    "axis_up": "Y",
    "axis_forward": "-Z",
    "unit_system": "NONE",
    "unit_scale_length": 1.0,
    "location": [0.0, 0.0, 0.0],
    "rotation_degrees": [0.0, 0.0, 0.0],
    "scale": [1.0, 1.0, 1.0],
}

CASES = [
    {"id": "baseline", "factor": "baseline", **deepcopy(_BASE)},
    {"id": "axis_only", "factor": "axis", **(deepcopy(_BASE) | {"axis_up": "Z", "axis_forward": "Y"})},
    {"id": "unit_only", "factor": "unit", **(deepcopy(_BASE) | {"unit_system": "METRIC", "unit_scale_length": 0.01})},
    {"id": "translation_only", "factor": "translation", **(deepcopy(_BASE) | {"location": [2.25, -0.75, 1.125]})},
    {"id": "rotation_only", "factor": "rotation", **(deepcopy(_BASE) | {"rotation_degrees": [23.0, -37.0, 61.0]})},
    {"id": "positive_nonuniform_scale_only", "factor": "positive_nonuniform_scale", **(deepcopy(_BASE) | {"scale": [2.0, 0.5, 1.5]})},
    {"id": "negative_scale_only", "factor": "negative_scale", **(deepcopy(_BASE) | {"scale": [-1.0, 1.0, 1.0]})},
]


_FACTOR_KEYS = {
    "axis": ("axis_up", "axis_forward"),
    "unit": ("unit_system", "unit_scale_length"),
    "translation": ("location",),
    "rotation": ("rotation_degrees",),
    "positive_nonuniform_scale": ("scale",),
    "negative_scale": ("scale",),
}
_VARIABLE_KEYS = ("axis_up", "axis_forward", "unit_system", "unit_scale_length",
                  "location", "rotation_degrees", "scale")


def validate_spec():
    errors = []
    if len(CASES) != 7 or CASES[0]["factor"] != "baseline":
        errors.append("EXPECTED_BASELINE_AND_SIX_INTERVENTIONS")
        return errors
    if len({case["id"] for case in CASES}) != len(CASES):
        errors.append("CASE_IDS_NOT_UNIQUE")
    baseline = CASES[0]
    for case in CASES[1:]:
        changed = tuple(key for key in _VARIABLE_KEYS if case[key] != baseline[key])
        expected = _FACTOR_KEYS.get(case["factor"])
        if expected is None or set(changed) != set(expected):
            errors.append("NOT_SINGLE_FACTOR:%s:%s" % (case["id"], ",".join(changed)))
        for key in ("geometry_id", "material_ids", "face_material_ids", "corner_uv_ids"):
            if case[key] != baseline[key]:
                errors.append("INPUT_GEOMETRY_CHANGED:%s:%s" % (case["id"], key))
    counts = {identity: 0 for identity in MATERIAL_IDS}
    uv_ids = []
    for face in GEOMETRY["faces"]:
        if face["material"] not in counts:
            errors.append("UNKNOWN_MATERIAL:%s" % face["face_id"])
            continue
        counts[face["material"]] += 1
        if len(face["vertices"]) != 3 or len(face["uvs"]) != 3:
            errors.append("FACE_NOT_TRIANGLE_OR_UV_MISSING:%s" % face["face_id"])
        uv_ids.append(tuple(tuple(uv) for uv in face["uvs"]))
    if set(counts.values()) != {2}:
        errors.append("MATERIAL_FACE_COUNTS_NOT_EQUAL_2:%s" % counts)
    if len(uv_ids) != len(set(uv_ids)):
        errors.append("CORNER_UV_FACE_IDENTITIES_NOT_UNIQUE")
    return errors


def validate_emitted_factor_metadata(records):
    """Check that the exported files actually encode distinct axis and unit inputs."""
    errors = []
    by_id = {record.get("id"): record for record in records}
    if len(by_id) != 7 or any(case["id"] not in by_id for case in CASES):
        return ["RAW_FBX_CASE_SET_INVALID"]
    baseline = by_id["baseline"]["raw_fbx"]
    baseline_global = baseline.get("global_settings", {})
    axis_keys = ("UpAxis", "UpAxisSign", "FrontAxis", "FrontAxisSign", "CoordAxis", "CoordAxisSign")
    baseline_axis = tuple(baseline_global.get(key) for key in axis_keys)
    baseline_unit = baseline_global.get("UnitScaleFactor")
    if baseline_unit is None:
        errors.append("RAW_BASELINE_UNIT_SCALE_MISSING")
    axis_global = by_id["axis_only"]["raw_fbx"].get("global_settings", {})
    axis_tuple = tuple(axis_global.get(key) for key in axis_keys)
    if axis_tuple == baseline_axis:
        errors.append("RAW_AXIS_FACTOR_NOT_DISTINCT:axis_only")
    if axis_global.get("UnitScaleFactor") != baseline_unit:
        errors.append("RAW_AXIS_CHANGED_UNIT_METADATA")

    unit_global = by_id["unit_only"]["raw_fbx"].get("global_settings", {})
    unit_value = unit_global.get("UnitScaleFactor")
    if baseline_unit is None or unit_value is None or abs(float(unit_value) - float(baseline_unit)) < 1.0e-5:
        errors.append("RAW_UNIT_FACTOR_NOT_DISTINCT:unit_only")
    if tuple(unit_global.get(key) for key in axis_keys) != baseline_axis:
        errors.append("RAW_UNIT_CHANGED_AXIS_METADATA")

    baseline_materials = baseline.get("materials_by_fixture_identity", [])
    baseline_material_map = sorted((row.get("name"), row.get("fixture_material_id"), row.get("fbx_object_uid"))
                                   for row in baseline_materials)
    for case in CASES:
        raw = by_id[case["id"]].get("raw_fbx", {})
        global_settings = raw.get("global_settings", {})
        if case["factor"] not in ("axis", "unit"):
            if tuple(global_settings.get(key) for key in axis_keys) != baseline_axis:
                errors.append("RAW_UNEXPECTED_AXIS_CHANGE:%s" % case["id"])
            if global_settings.get("UnitScaleFactor") != baseline_unit:
                errors.append("RAW_UNEXPECTED_UNIT_CHANGE:%s" % case["id"])
        material_map = sorted((row.get("name"), row.get("fixture_material_id"), row.get("fbx_object_uid"))
                              for row in raw.get("materials_by_fixture_identity", []))
        if material_map != baseline_material_map:
            errors.append("RAW_MATERIAL_IDENTITIES_CHANGED:%s" % case["id"])
    return errors


def public_spec():
    unity_geometry = {
        "geometry_id": GEOMETRY_ID,
        "materials": list(MATERIAL_IDS),
        "faces": [
            {
                "face_id": face["face_id"],
                "material": face["material"],
                "uvs": [{"x": uv[0], "y": uv[1]} for uv in face["uvs"]],
            }
            for face in _FACES
        ],
    }
    return {"schema": "vapb-coordinate-intervention-v1", "geometry": unity_geometry,
            "cases": CASES, "export_controls": EXPORT_CONTROLS}
