"""Synthetic contract tests for Semantic Contract v0.

The adapter below is deliberately a test oracle.  It is not wired into the
importer and must not be treated as a production projection fix.
"""

import unittest

from unitypackage_blender_importer.unity.semantic_contract import (
    CONTRACT_VERSION,
    ContractMaterialOverride,
    OccurrenceProjectionContext,
    ProjectionSource,
    RendererOccurrenceContract,
    SyntheticOccurrenceProjectionAdapter,
)
from unitypackage_blender_importer.unity.provenance_model import (
    MeshKey,
    OccurrenceStep,
    OwnerKey,
    SourceComponentKey,
)


MODEL = "1" * 32
MESH = "2" * 32
MATERIAL_A = "3" * 32
MATERIAL_B = "4" * 32


def source(renderer_file_id=700):
    return ProjectionSource(
        SourceComponentKey("MODEL", MODEL, renderer_file_id),
        OwnerKey("MODEL", MODEL, 900 + renderer_file_id),
        MeshKey(MESH, 4300000 + renderer_file_id),
    )


class SemanticContractV0Tests(unittest.TestCase):
    def test_contract_version_and_two_contexts_preserve_shared_source_identity(self):
        contexts = (
            OccurrenceProjectionContext("root-A", (OccurrenceStep("container", 10, MODEL),)),
            OccurrenceProjectionContext("root-B", (OccurrenceStep("container", 11, MODEL),)),
        )
        result = SyntheticOccurrenceProjectionAdapter().project((source(),), contexts)

        self.assertEqual("v0", CONTRACT_VERSION)
        self.assertEqual(2, len(result.occurrences))
        self.assertEqual({"root-A", "root-B"}, {
            item.occurrence_key.root_context_id for item in result.occurrences
        })
        self.assertEqual(
            {item.occurrence_key.source_key for item in result.occurrences},
            {source().source_key},
        )
        self.assertNotEqual(
            result.occurrences[0].occurrence_key,
            result.occurrences[1].occurrence_key,
        )

    def test_instance_edge_path_is_part_of_occurrence_identity(self):
        contexts = (
            OccurrenceProjectionContext("root-A", (OccurrenceStep("container", 10, MODEL),)),
            OccurrenceProjectionContext("root-A", (
                OccurrenceStep("container", 10, MODEL),
                OccurrenceStep("nested", 20, MODEL),
            )),
        )
        result = SyntheticOccurrenceProjectionAdapter().project((source(),), contexts)

        self.assertEqual(2, len(result.occurrences))
        self.assertNotEqual(
            result.occurrences[0].occurrence_key.instance_edge_path,
            result.occurrences[1].occurrence_key.instance_edge_path,
        )

    def test_material_override_does_not_mutate_occurrence_identity(self):
        item = SyntheticOccurrenceProjectionAdapter().project(
            (source(),), (OccurrenceProjectionContext("root-A"),)
        ).occurrences[0]
        changed = item.with_material_overrides((ContractMaterialOverride(0, MATERIAL_A),))
        changed_again = changed.with_material_overrides((ContractMaterialOverride(0, MATERIAL_B),))

        self.assertEqual(item.occurrence_key, changed.occurrence_key)
        self.assertEqual(item.occurrence_key, changed_again.occurrence_key)
        self.assertEqual(MATERIAL_A, changed.material_overrides[0].material_guid)
        self.assertEqual(MATERIAL_B, changed_again.material_overrides[0].material_guid)

    def test_conflicting_source_relations_fail_closed(self):
        conflicting = ProjectionSource(
            SourceComponentKey("MODEL", MODEL, 700),
            OwnerKey("MODEL", MODEL, 901),
            MeshKey(MESH, 4300999),
        )
        result = SyntheticOccurrenceProjectionAdapter().project(
            (source(), conflicting), (OccurrenceProjectionContext("root-A"),)
        )

        self.assertEqual((), result.occurrences)
        self.assertEqual((source().source_key,), result.ambiguous_source_keys)

    def test_contract_serialization_contains_identity_not_names(self):
        item = SyntheticOccurrenceProjectionAdapter().project(
            (source(),), (OccurrenceProjectionContext("root-A"),)
        ).occurrences[0]
        payload = item.to_dict()

        self.assertEqual("v0", payload["contract_version"])
        self.assertEqual("root-A", payload["occurrence"]["root_context_id"])
        self.assertEqual("MODEL", payload["source"]["source_kind"])
        self.assertEqual(700, payload["source"]["renderer_file_id"])
        self.assertNotIn("name", str(payload).lower())


if __name__ == "__main__":
    unittest.main()
