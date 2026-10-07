import unittest

from experiment_spec import (CASES, EXPORT_CONTROLS, GEOMETRY, public_spec,
                             validate_emitted_factor_metadata, validate_spec)


class InterventionSpecTests(unittest.TestCase):
    def test_has_one_baseline_and_six_single_factor_interventions(self):
        self.assertEqual(
            [case["id"] for case in CASES],
            [
                "baseline",
                "axis_only",
                "unit_only",
                "translation_only",
                "rotation_only",
                "positive_nonuniform_scale_only",
                "negative_scale_only",
            ],
        )
        self.assertEqual(validate_spec(), [])

    def test_geometry_has_equal_face_counts_and_unique_corner_uv_identity(self):
        faces = GEOMETRY["faces"]
        counts = {material: 0 for material in GEOMETRY["materials"]}
        uv_signatures = []
        for face in faces:
            counts[face["material"]] += 1
            self.assertEqual(len(face["vertices"]), 3)
            self.assertEqual(len(face["uvs"]), 3)
            self.assertEqual(len({uv[0] for uv in face["uvs"]}), 3)
            uv_signatures.append(tuple(tuple(uv) for uv in face["uvs"]))
        self.assertEqual(sorted(counts.values()), [2, 2, 2])
        self.assertEqual(len(uv_signatures), len(set(uv_signatures)))

    def test_all_cases_preserve_geometry_and_material_partition_inputs(self):
        baseline = CASES[0]
        invariant_keys = ("geometry_id", "material_ids", "face_material_ids", "corner_uv_ids")
        for case in CASES[1:]:
            for key in invariant_keys:
                self.assertEqual(case[key], baseline[key], (case["id"], key))

    def test_json_boundary_uses_unity_serializable_uv_objects(self):
        spec = public_spec()
        self.assertEqual(spec["schema"], "vapb-coordinate-intervention-v1")
        self.assertEqual(len(spec["geometry"]["faces"]), 6)
        self.assertEqual(set(spec["geometry"]["faces"][0]["uvs"][0]), {"x", "y"})

    def test_export_controls_are_common_and_do_not_enable_axis_baking(self):
        self.assertEqual(EXPORT_CONTROLS["global_scale"], 1.0)
        self.assertFalse(EXPORT_CONTROLS["bake_space_transform"])
        self.assertTrue(EXPORT_CONTROLS["apply_unit_scale"])
        self.assertEqual(EXPORT_CONTROLS["apply_scale_options"], "FBX_SCALE_UNITS")
        self.assertFalse(EXPORT_CONTROLS["bake_anim"])
        self.assertEqual(EXPORT_CONTROLS["object_types"], ["MESH"])

    def test_raw_fbx_metadata_proves_axis_and_unit_interventions(self):
        materials = [
            {"name": "A", "fixture_material_id": "mat-A", "fbx_object_uid": 10},
            {"name": "B", "fixture_material_id": "mat-B", "fbx_object_uid": 20},
            {"name": "C", "fixture_material_id": "mat-C", "fbx_object_uid": 30},
        ]
        base_global = {"UpAxis": 1, "UpAxisSign": 1, "FrontAxis": 2, "FrontAxisSign": 1,
                       "CoordAxis": 0, "CoordAxisSign": 1, "UnitScaleFactor": 100.0}
        rows = []
        for case in CASES:
            global_settings = dict(base_global)
            if case["id"] == "axis_only":
                global_settings.update(UpAxis=2, FrontAxis=1, FrontAxisSign=-1)
            if case["id"] == "unit_only":
                global_settings["UnitScaleFactor"] = 1.0
            rows.append({"id": case["id"], "raw_fbx": {
                "global_settings": global_settings,
                "materials_by_fixture_identity": materials,
            }})
        self.assertEqual(validate_emitted_factor_metadata(rows), [])
        rows[2]["raw_fbx"]["global_settings"]["UnitScaleFactor"] = 100.0
        self.assertIn("RAW_UNIT_FACTOR_NOT_DISTINCT:unit_only",
                      validate_emitted_factor_metadata(rows))


if __name__ == "__main__":
    unittest.main()
