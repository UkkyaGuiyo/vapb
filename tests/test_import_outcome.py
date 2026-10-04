"""Public, synthetic user-facing import outcome controls."""

import unittest

from unitypackage_blender_importer.unity.import_outcome import summarize_import_outcome


def projection(*, records=(), issues=()):
    return {"records": list(records), "issues": list(issues)}


def dependency(status, *, kind="PREFAB_RENDERER_MATERIAL", label=""):
    return {"dependency_type": kind, "status": status,
            "binding_status": "BOUND" if status == "RESOLVED_LOCAL" else status,
            "texture_label": label}


class ImportOutcomeTests(unittest.TestCase):
    def test_a_resolved_has_no_false_warning(self):
        result = summarize_import_outcome(
            [projection(records=[{"material_status": "EXACT"}])],
            [dependency("RESOLVED_LOCAL"), dependency("UNRESOLVED", kind="MATERIAL_TEXTURE", label="Preserve Only")],
        )
        self.assertEqual(result["overall"], "SUCCESS")
        self.assertEqual(result["counts"]["RESOLVED"], 1)
        self.assertEqual(result["counts"]["MISSING_DEPENDENCY"], 0)

    def test_b_model_source_is_unknown_object_not_missing_material(self):
        result = summarize_import_outcome(
            [projection(issues=[{"code": "UNRESOLVED_SOURCE", "instance_edge_path": [{}]}])],
            [dependency("RESOLVED_LOCAL")],
        )
        self.assertEqual(result["overall"], "PARTIAL")
        self.assertEqual(result["counts"]["UNRESOLVED_IDENTITY"], 1)
        self.assertEqual(result["counts"]["MISSING_DEPENDENCY"], 0)
        self.assertIn("UnityPackage", result["items"][0]["reason"])

    def test_c_ambiguous_native_candidate_is_not_resolved(self):
        result = summarize_import_outcome([projection(issues=[{"code": "NATIVE_AMBIGUOUS"}])], [])
        self.assertEqual(result["counts"]["AMBIGUOUS"], 1)
        self.assertEqual(result["counts"]["RESOLVED"], 0)

    def test_d_missing_provider_is_distinct_from_identity(self):
        result = summarize_import_outcome([], [dependency("UNRESOLVED")])
        self.assertEqual(result["counts"]["MISSING_DEPENDENCY"], 1)
        self.assertEqual(result["counts"]["UNRESOLVED_IDENTITY"], 0)

    def test_builtin_preview_is_explained_partial_not_exact_material_success(self):
        result = summarize_import_outcome([], [{
            "dependency_type": "PREFAB_RENDERER_MATERIAL",
            "status": "RESOLVED_BUILTIN_PREVIEW",
            "binding_status": "BOUND",
            "resolution_provenance": "UNITY_BUILTIN_PREVIEW_APPROXIMATE",
        }])
        self.assertEqual(result["overall"], "PARTIAL")
        self.assertEqual(result["counts"]["RESOLVED"], 0)
        self.assertEqual(result["counts"]["MISSING_DEPENDENCY"], 0)
        self.assertEqual(result["counts"]["PARTIAL"], 1)
        self.assertEqual(result["items"][0]["code"], "BUILTIN_PREVIEW_APPROXIMATE")

    def test_e_alias_uncertainty_keeps_nested_scope_without_guessing_object(self):
        issue = {"code": "UNRESOLVED_ALIAS_OVERRIDE", "uncertainty_scope": "NESTED_INSTANCE"}
        result = summarize_import_outcome([projection(issues=[issue])], [])
        self.assertEqual(result["counts"]["UNRESOLVED_IDENTITY"], 1)
        self.assertEqual(result["items"][0]["scope"], "Importルート 1 の入れ子Prefab個体")

    def test_f_exact_witness_binding_is_counted_not_required(self):
        result = summarize_import_outcome(
            [projection(records=[{"material_status": "PARTIAL"}])],
            [dependency("RESOLVED_LOCAL")],
        )
        self.assertEqual(result["overall"], "SUCCESS")
        self.assertEqual(result["counts"]["RESOLVED"], 1)

    def test_missing_consumer_is_not_a_missing_provider(self):
        result = summarize_import_outcome([], [dependency("MISSING_CONSUMER")])
        self.assertEqual(result["counts"]["UNRESOLVED_IDENTITY"], 1)
        self.assertEqual(result["counts"]["MISSING_DEPENDENCY"], 0)

    def test_unknown_issue_fails_explained_not_success(self):
        result = summarize_import_outcome([projection(issues=[{"code": "FUTURE_CODE"}])], [])
        self.assertEqual(result["counts"]["ERROR"], 1)
        self.assertEqual(result["overall"], "PARTIAL")

    def test_texture_state_without_receipt_is_unverified_not_an_unknown_error(self):
        result = summarize_import_outcome([], [dependency(
            "UNVERIFIED_TEXTURE_STATE", kind="MATERIAL_TEXTURE", label="Base Color")])
        self.assertEqual(result["counts"]["UNRESOLVED_IDENTITY"], 1)
        self.assertEqual(result["counts"]["ERROR"], 0)

    def test_preserved_texture_edit_explains_texture_not_material_slot(self):
        result = summarize_import_outcome([], [dependency(
            "USER_EDIT_PRESERVED", kind="MATERIAL_TEXTURE", label="Base Color")])
        self.assertEqual(result["counts"]["PARTIAL"], 1)
        self.assertIn("Texture", result["items"][0]["reason"])

    def test_known_null_material_is_not_reported_as_fully_realized(self):
        result = summarize_import_outcome([projection(records=[{
            "material_status": "EXACT", "material_slot_count": 1,
            "materials": {"0": None},
        }])], [])
        self.assertEqual(result["overall"], "PARTIAL")
        self.assertEqual(result["counts"]["PARTIAL"], 1)
        self.assertEqual(result["items"][0]["code"], "NULL_MATERIAL_REALIZATION_UNVERIFIED")

    def test_partial_material_source_with_known_null_is_not_fully_realized(self):
        result = summarize_import_outcome([projection(records=[{
            "material_status": "PARTIAL", "materials": {0: None},
        }])], [])
        self.assertEqual(result["overall"], "PARTIAL")
        self.assertEqual(result["items"][0]["code"], "NULL_MATERIAL_REALIZATION_UNVERIFIED")

    def test_null_slot_requires_scoped_live_proof(self):
        row = {"root_context_id": "root", "occurrence_id": "occurrence",
               "material_status": "EXACT", "material_slot_count": 1,
               "materials": {0: None}}
        projected = [projection(records=[row])]
        key = ("root", "occurrence", 0)
        self.assertEqual("PARTIAL", summarize_import_outcome(projected, [])["overall"])
        self.assertEqual("PARTIAL", summarize_import_outcome(
            projected, [], verified_null_slots={("other", "occurrence", 0)})["overall"])
        self.assertEqual("SUCCESS", summarize_import_outcome(
            projected, [], verified_null_slots={key})["overall"])
        edited = summarize_import_outcome(projected, [{
            "dependency_type": "CLEAR_MATERIAL_SLOT", "status": "USER_EDIT_PRESERVED",
        }], edited_null_slots={key})
        self.assertEqual("PARTIAL", edited["overall"])
        self.assertEqual(["USER_EDIT_PRESERVED"], [item["code"] for item in edited["items"]])

    def test_nested_non_null_renderer_without_blender_occurrence_is_partial(self):
        row = {
            "root_context_id": "root",
            "occurrence_id": "nested-renderer",
            "instance_edge_path": [{"source_prefab_guid": "synthetic"}],
            "source_key": {"source_kind": "PREFAB_LOCAL"},
            "material_status": "EXACT",
            "materials": {"0": {"guid": "material"}},
        }
        result = summarize_import_outcome([projection(records=[row])], [])
        self.assertEqual("PARTIAL", result["overall"])
        self.assertIn("NESTED_PREFAB_RENDERER_NOT_REALIZED", {item["code"] for item in result["items"]})

    def test_nested_renderer_with_realized_occurrence_has_no_geometry_warning(self):
        row = {
            "root_context_id": "root",
            "occurrence_id": "nested-renderer",
            "instance_edge_path": [{"source_prefab_guid": "synthetic"}],
            "source_key": {"source_kind": "PREFAB_LOCAL"},
            "material_status": "EXACT",
            "materials": {"0": {"guid": "material"}},
        }
        result = summarize_import_outcome(
            [projection(records=[row])], [],
            realized_renderer_occurrences={"nested-renderer"},
        )
        self.assertEqual("SUCCESS", result["overall"])


if __name__ == "__main__":
    unittest.main()
