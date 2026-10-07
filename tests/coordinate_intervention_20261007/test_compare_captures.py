import unittest
from copy import deepcopy

from compare_captures import (compare_payloads, point_deltas, partition_errors, transform_point,
                              _unity_material_identity_errors)


class CaptureComparisonTests(unittest.TestCase):
    def test_material_permutation_with_equal_counts_is_detected_per_face(self):
        expected = {
            "f0": "material-A", "f1": "material-A",
            "f2": "material-B", "f3": "material-B",
            "f4": "material-C", "f5": "material-C",
        }
        swapped = {
            "f0": "material-C", "f1": "material-C",
            "f2": "material-B", "f3": "material-B",
            "f4": "material-A", "f5": "material-A",
        }
        self.assertEqual(sorted(expected.values()), sorted(swapped.values()))
        errors = partition_errors(expected, swapped, "UNITY")
        self.assertEqual(len(errors), 4)
        self.assertTrue(all("FACE_MATERIAL_MISMATCH" in error for error in errors))

    def test_world_point_comparison_supports_unity_flat_and_blender_matrix_rows(self):
        matrix = [
            [0.0, -1.0, 0.0, 2.0],
            [1.0, 0.0, 0.0, -3.0],
            [0.0, 0.0, 1.0, 4.0],
            [0.0, 0.0, 0.0, 1.0],
        ]
        flat = [value for row in matrix for value in row]
        expected = (1.0, -2.0, 7.0)
        self.assertEqual(transform_point(matrix, (1.0, 1.0, 3.0)), expected)
        self.assertEqual(transform_point(flat, (1.0, 1.0, 3.0)), expected)
        self.assertEqual(transform_point(matrix, {"x": 1.0, "y": 1.0, "z": 3.0}), expected)
        nan_matrix = [float("nan") if index == 0 else value for index, value in enumerate(flat)]
        with self.assertRaisesRegex(ValueError, "MATRIX_NONFINITE"):
            transform_point(nan_matrix, (1.0, 1.0, 3.0))
        overflow_matrix = [1.0e308 if index == 0 else value for index, value in enumerate(flat)]
        with self.assertRaisesRegex(ValueError, "TRANSFORMED_POINT_NONFINITE"):
            transform_point(overflow_matrix, (2.0, 1.0, 3.0))

    def test_corner_delta_reports_missing_identity_and_numeric_residual(self):
        maximum, errors = point_deltas({"1": (0.0, 0.0, 0.0)}, {"1": (0.0002, 0.0, 0.0), "2": (0, 0, 0)})
        self.assertAlmostEqual(maximum, 0.0002)
        self.assertEqual(len(errors), 2)
        self.assertTrue(any(error.startswith("CORNER_ID_MISSING") for error in errors))

    def test_unity_material_guid_local_id_and_source_fbx_uid_are_required(self):
        fixture_case = {"filename": "input.fbx", "source_material_ids": ["A", "B", "C"],
                        "source_material_fbx_uids": [10, 20, 30]}
        material_rows = [
            {"fixture_material_id_from_pinned_input_connection": identity,
             "source_fbx_material_object_uid": uid, "guid": "g", "local_file_id": str(index),
             "imported_asset_path": "Assets/VapbCoordinateIntervention/input.fbx"}
            for index, (identity, uid) in enumerate(zip(fixture_case["source_material_ids"],
                                                          fixture_case["source_material_fbx_uids"]), 1)]
        unity_case = {"case_id": "baseline", "renderers": [{"materials": [
            *material_rows], "mesh_guid": "g"}]}
        self.assertEqual(_unity_material_identity_errors(unity_case, fixture_case), [])
        unity_case["renderers"][0]["materials"][0]["source_fbx_material_object_uid"] = 20
        self.assertTrue(any("SOURCE_MATERIAL_OBJECT_ID_MISMATCH" in error
                            for error in _unity_material_identity_errors(unity_case, fixture_case)))

    def _valid_payloads(self):
        manifest_sha = "manifest-pin"
        faces = [{"face_id": "f%d" % index, "material": "A", "uvs": [
            {"x": float(index * 10 + corner), "y": 0.1 + corner * 0.1}
            for corner in range(3)]} for index in range(6)]
        manifest = {"blender_version": "5.2.1 LTS", "spec": {"geometry": {"faces": faces}},
                    "cases": [{"id": "baseline", "factor": "baseline", "filename": "baseline.fbx",
                     "sha256": "fixture-pin", "source_material_ids": ["A", "B", "C"],
                     "source_material_fbx_uids": [77, 78, 79]}]}
        blender = {"schema": "vapb-coordinate-intervention-blender-capture-v1",
                   "status": "BLENDER_FACE_IDENTITY_PASS", "manifest_sha256": manifest_sha,
                   "blender_version": "5.2.1 LTS",
                   "cases": [{"case_id": "baseline", "input_sha256": "fixture-pin",
                              "face_membership_matches_source_identity": True, "unmatched_face_count": 0,
                              "hierarchy": [{"type": "MESH", "matrix_world": [
                                  [1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]}],
                              "triangles": [{"face_id_by_uv": "f%d" % face_index,
                                  "material_id_from_pinned_source_connection": "A",
                                  "uvs": [[float(face_index * 10 + corner), 0.1 + corner * 0.1]
                                          for corner in range(3)],
                                  "vertices_local": [[float(face_index * 3 + corner), 0.0, 0.0]
                                                     for corner in range(3)]}
                                  for face_index in range(6)]}]}
        unity = {"schema": "vapb-coordinate-intervention-unity-capture-v1",
                 "status": "UNITY_FACE_IDENTITY_CAPTURED", "errors": [],
                 "material_identity_join_method": "fixture-authored-unique-material-name",
                 "unity_version": "2022.3.22f1", "manifest_sha256": manifest_sha,
                 "cases": [{"case_id": "baseline", "input_sha256": "fixture-pin",
                            "face_membership_matches_source_identity": True, "unmatched_face_count": 0,
                            "importer": {"bake_axis_conversion": False, "use_file_scale": True,
                                "use_file_units": True, "global_scale": 1.0, "import_normals": "Import",
                                "import_tangents": "Import", "preserve_hierarchy": True,
                                "mesh_compression": "Off"},
                            "hierarchy": [{"path": "root/mesh", "world_matrix": [
                                1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]}],
                            "renderers": [{"transform_path": "root/mesh", "mesh_guid": "mesh-guid",
                                "mesh_local_file_id": "4", "vertices_local": [
                                    {"x": float(index), "y": 0.0, "z": 0.0} for index in range(18)],
                                "materials": [{"fixture_material_id_from_pinned_input_connection": identity,
                                    "source_fbx_material_object_uid": uid, "guid": "mesh-guid",
                                    "local_file_id": str(index),
                                    "imported_asset_path": "Assets/VapbCoordinateIntervention/baseline.fbx"}
                                    for index, (identity, uid) in enumerate(zip(["A", "B", "C"],
                                                                                [77, 78, 79]), 1)],
                                "submeshes": [{"faces": [{"face_id_by_corner_uv": "f%d" % face_index,
                                    "renderer_material_id": "A", "corner_uvs": [
                                        {"x": float(face_index * 10 + corner), "y": 0.1 + corner * 0.1}
                                        for corner in range(3)],
                                    "vertex_indices": [face_index * 3, face_index * 3 + 1,
                                                       face_index * 3 + 2]}
                                    for face_index in range(6)]}]}]}]}
        names = ["baseline", "axis_only", "unit_only", "translation_only", "rotation_only",
                 "positive_nonuniform_scale_only", "negative_scale_only"]
        factors = ["baseline", "axis", "unit", "translation", "rotation",
                   "positive_nonuniform_scale", "negative_scale"]
        manifest["cases"] = [dict(manifest["cases"][0], id=case_id, factor=factor,
                                  filename=case_id + ".fbx")
                             for case_id, factor in zip(names, factors)]
        blender["cases"] = [dict(deepcopy(blender["cases"][0]), case_id=case_id) for case_id in names]
        unity["cases"] = [dict(deepcopy(unity["cases"][0]), case_id=case_id) for case_id in names]
        for unity_case in unity["cases"]:
            for material in unity_case["renderers"][0]["materials"]:
                material["imported_asset_path"] = "Assets/VapbCoordinateIntervention/" + unity_case["case_id"] + ".fbx"
        return manifest, blender, unity, manifest_sha

    def test_unity_jsonutility_vectors_and_complete_capture_compare(self):
        manifest, blender, unity, manifest_sha = self._valid_payloads()
        result = compare_payloads(manifest, blender, unity, manifest_sha)
        self.assertEqual(result["status"], "COORDINATE_AND_FACE_IDENTITY_PASS")
        unity["cases"][0]["renderers"][0]["submeshes"][0]["faces"][0]["corner_uvs"] = []
        result = compare_payloads(manifest, blender, unity, manifest_sha)
        self.assertEqual(result["status"], "COORDINATE_AND_FACE_IDENTITY_UNPROVEN")
        self.assertTrue(any("FACE_CORNER_CARDINALITY_INVALID" in error for error in result["errors"]))

    def test_capture_failure_receipt_and_missing_settings_are_rejected(self):
        manifest, blender, unity, manifest_sha = self._valid_payloads()
        unity["status"] = "UNITY_FACE_IDENTITY_UNPROVEN"
        unity["cases"][0]["importer"] = {}
        blender["manifest_sha256"] = "wrong"
        result = compare_payloads(manifest, blender, unity, manifest_sha)
        self.assertEqual(result["status"], "COORDINATE_AND_FACE_IDENTITY_UNPROVEN")
        for marker in ("UNITY_CAPTURE_NOT_PASS", "UNITY_IMPORTER_SETTINGS_INCOMPLETE",
                       "BLENDER_MANIFEST_RECEIPT_MISMATCH"):
            self.assertTrue(any(marker in error for error in result["errors"]))

    def test_duplicate_case_ids_are_rejected_before_building_capture_maps(self):
        manifest, blender, unity, manifest_sha = self._valid_payloads()
        blender["cases"][1]["case_id"] = "baseline"
        result = compare_payloads(manifest, blender, unity, manifest_sha)
        self.assertEqual(result["status"], "COORDINATE_AND_FACE_IDENTITY_UNPROVEN")
        self.assertEqual(result["errors"], ["CASE_CARDINALITY_OR_UNIQUENESS_INVALID"])


if __name__ == "__main__":
    unittest.main()
