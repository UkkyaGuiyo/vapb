"""Frozen preparation contract for an unseen coordinate holdout.

No previous capture is an oracle for this fixture. This module only defines
the authored inputs and candidate equations selected before generation.
"""
from __future__ import annotations

from copy import deepcopy
import math

GEOMETRY_ID = "vapb-coordinate-holdout-20261007-v1"
MATERIAL_IDS = ("holdout-material-A", "holdout-material-B", "holdout-material-C")
CORNER_UVS = tuple((100.0 + 8.0 * face + corner, y)
                   for face in range(6) for corner, y in enumerate((0.125, 0.25, 0.375)))
TRIANGLES = (
    ((.17, -.29, .43), (1.93, -.11, .67), (.38, 1.27, .91)),
    ((-.61, .32, 1.43), (.84, .73, 1.91), (-.27, 1.88, 1.16)),
    ((-1.21, -.42, .24), (-.33, -1.73, .59), (-1.67, -.86, 1.38)),
    ((.49, -1.14, 1.72), (1.56, -.37, 2.13), (.11, -.68, 2.64)),
    ((-.92, 1.31, -.57), (.23, 2.07, -.19), (-1.38, .76, .36)),
    ((1.12, .54, -1.29), (2.31, .91, -.63), (.77, 1.69, -.84)),
)
FACES = tuple({"face_id": "face-%02d" % i,
               "material_id": MATERIAL_IDS[i // 2],
               "vertices": [3 * i, 3 * i + 1, 3 * i + 2],
               "uvs": [list(CORNER_UVS[3 * i + j]) for j in range(3)]}
              for i in range(6))
VERTICES = tuple(vertex for triangle in TRIANGLES for vertex in triangle)
GEOMETRY = {"geometry_id": GEOMETRY_ID, "materials": list(MATERIAL_IDS),
            "vertices": [list(v) for v in VERTICES], "faces": list(FACES)}
EXPORT_CONTROLS = {
    "global_scale": 1.0, "apply_scale_options": "FBX_SCALE_UNITS",
    "apply_unit_scale": True, "bake_space_transform": False,
    "bake_anim": False, "add_leaf_bones": False,
    "use_mesh_modifiers": False, "use_custom_props": True,
    "object_types": ["MESH"], "axis_forward": "-Z", "axis_up": "Y",
    "path_mode": "AUTO",
}
BLENDER_IMPORT_CONTROLS = {
    "axis_forward": "-Z", "axis_up": "Y", "global_scale": 1.0,
    "use_custom_props": True, "use_anim": False,
    "use_image_search": False, "automatic_bone_orientation": False,
}
UNITY_IMPORT_SETTINGS = {
    "bakeAxisConversion": False, "useFileScale": True, "useFileUnits": True,
    "globalScale": 1.0, "importNormals": "Import", "importTangents": "CalculateMikk",
    "preserveHierarchy": False, "meshCompression": "Off",
}
ENGINE_VERSIONS = {"blender": "5.2.1", "unity": "2022.3.22f1"}
CWORLD = ((-1., 0., 0., 0.), (0., 0., 1., 0.), (0., -1., 0., 0.), (0., 0., 0., 1.))
TOLERANCE = 1.0e-4
METADATA_TOLERANCE = 1.0e-4
EXPECTED_RAW_UNIT_SCALE_FACTOR = {"H0": 100.0, "H1": 100.0, "H2": 10.0, "H3": 10.0}
CASES = (
    {"id": "H0", "axis_up": "Y", "axis_forward": "-Z", "unit_system": "NONE", "unit_scale_length": 1.0,
     "location": [0., 0., 0.], "rotation_degrees": [0., 0., 0.], "scale": [1., 1., 1.]},
    {"id": "H1", "axis_up": "X", "axis_forward": "-Y", "unit_system": "NONE", "unit_scale_length": 1.0,
     "location": [0., 0., 0.], "rotation_degrees": [0., 0., 0.], "scale": [1., 1., 1.]},
    {"id": "H2", "axis_up": "Y", "axis_forward": "-Z", "unit_system": "METRIC", "unit_scale_length": .1,
     "location": [0., 0., 0.], "rotation_degrees": [0., 0., 0.], "scale": [1., 1., 1.]},
    {"id": "H3", "axis_up": "X", "axis_forward": "-Y", "unit_system": "METRIC", "unit_scale_length": .1,
     "location": [1.375, -2.125, .625], "rotation_degrees": [31., -19., 47.], "scale": [-1.25, .6, 1.8]},
)


def validate_contract():
    errors = []
    if tuple(case["id"] for case in CASES) != ("H0", "H1", "H2", "H3"):
        errors.append("CASE_SET_OR_ORDER_INVALID")
    if len(VERTICES) != 18 or len(FACES) != 6 or len(set(CORNER_UVS)) != 18:
        errors.append("AUTHORED_GEOMETRY_OR_TAGS_INVALID")
    if any(len(face["vertices"]) != 3 or len(face["uvs"]) != 3 for face in FACES):
        errors.append("FACE_SHAPE_INVALID")
    if any(not math.isfinite(float(c)) for v in VERTICES for c in v):
        errors.append("GEOMETRY_NONFINITE")
    for triangle in TRIANGLES:
        a, b, c = triangle
        ab = tuple(b[i] - a[i] for i in range(3)); ac = tuple(c[i] - a[i] for i in range(3))
        cross = (ab[1]*ac[2] - ab[2]*ac[1], ab[2]*ac[0] - ab[0]*ac[2], ab[0]*ac[1] - ab[1]*ac[0])
        if not math.isfinite(sum(x*x for x in cross)) or sum(x*x for x in cross) <= 1.e-12:
            errors.append("DEGENERATE_TRIANGLE")
    if set(UNITY_IMPORT_SETTINGS) != {"bakeAxisConversion", "useFileScale", "useFileUnits", "globalScale",
                                       "importNormals", "importTangents", "preserveHierarchy", "meshCompression"}:
        errors.append("UNITY_EFFECTIVE_IMPORT_FIELDS_INCOMPLETE")
    return errors


def public_contract():
    return {"schema": "vapb-coordinate-holdout-contract-v1", "geometry": deepcopy(GEOMETRY),
            "cases": deepcopy(CASES), "export_controls": deepcopy(EXPORT_CONTROLS),
            "blender_import_controls": deepcopy(BLENDER_IMPORT_CONTROLS),
            "unity_import_settings": deepcopy(UNITY_IMPORT_SETTINGS),
            "engine_versions": deepcopy(ENGINE_VERSIONS),
            "candidate": {"Cworld": [list(row) for row in CWORLD], "D": "diag(-s, s, s, 1)",
                          "tolerance_max_abs_per_component": TOLERANCE,
                          "metadata_relative_tolerance": METADATA_TOLERANCE,
                          "expected_raw_unit_scale_factor": dict(EXPECTED_RAW_UNIT_SCALE_FACTOR),
                          "required_residuals": ["local", "world_matrix", "world_point"],
                          "diagnostic_only_residuals": ["world_matrix_chain_point"],
                          "authored_unit_ratio": "unit_scale_length / H0.unit_scale_length",
                          "matrix_convention": "column vectors; W_U * D = Cworld * W_B; XYZ Euler uses T * Rz * Ry * Rx * S",
                          "holdout_policy": "no fitting, no rebase, each frozen case evaluated independently; candidate is not validated until Unity capture passes",
                          "required_observation_checks": ["one_mesh_one_root", "exact_case_set", "exact_18_authored_U_tags",
                                                          "blender_authored_hypothesis", "within_tool_H1_over_H0",
                                                          "within_tool_H2_over_0.1_H0"]},
            "expected_fbx_axis_tuple": {"Y/-Z": [1, 1, 2, 1, 0, 1], "X/-Y": [0, 1, 1, 1, 2, 1]}}
