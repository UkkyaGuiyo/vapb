import tempfile
import unittest
from pathlib import Path

from unitypackage_blender_importer.unity.effective_prefab import (
    ModelSourceRecord,
    ModelSourceSemanticIndex,
    EffectivePrefabResolver,
)
from unitypackage_blender_importer.unity.prefab_parser import parse_prefab
from unitypackage_blender_importer.blender.provenance_bridge import (
    BlenderRealizationIndex,
    RealizationKey,
)
from unitypackage_blender_importer.unity.provenance_model import (
    BridgeKey,
    MeshKey,
    OccurrenceKey,
    OccurrenceRecord,
    OccurrenceStep,
    OwnerKey,
    SemanticProvenanceIndex,
    SourceComponentKey,
)
import json


MODEL_GUID = "a" * 32
PREFAB_GUID = "b" * 32
MESH_GUID = "c" * 32


class RendererProvenanceBridgeTests(unittest.TestCase):
    def _variant(self, target_file_id="700", material_guid="d" * 32):
        return f"""%YAML 1.1
--- !u!1001 &1
PrefabInstance:
  m_SourcePrefab: {{fileID: 100100000, guid: {MODEL_GUID}, type: 3}}
  m_Modification:
    m_Modifications:
    - target: {{fileID: {target_file_id}, guid: {MODEL_GUID}, type: 3}}
      propertyPath: m_Materials.Array.data[0]
      value: 
      objectReference: {{fileID: 2100000, guid: {material_guid}, type: 2}}
"""

    def test_model_renderer_index_preserves_distinct_owner_and_mesh_ids(self):
        index = ModelSourceSemanticIndex([
            ModelSourceRecord(MODEL_GUID, 700, 137, 900, MESH_GUID, 4300000, 901),
            ModelSourceRecord(MODEL_GUID, 701, 137, 901, MESH_GUID, 4300000, 902),
        ])
        first = index.lookup(MODEL_GUID, 700)
        second = index.lookup(MODEL_GUID, 701)
        self.assertEqual("EXACT", first.evidence)
        self.assertEqual(900, first.record.owner_game_object_id)
        self.assertEqual(4300000, first.record.mesh_file_id)
        self.assertEqual(901, second.record.owner_game_object_id)

    def test_duplicate_model_renderer_identity_fails_closed(self):
        index = ModelSourceSemanticIndex([
            ModelSourceRecord(MODEL_GUID, 700, 137, 900, MESH_GUID, 4300000),
            ModelSourceRecord(MODEL_GUID, 700, 137, 901, MESH_GUID, 4300001),
        ])
        result = index.lookup(MODEL_GUID, 700)
        self.assertEqual("AMBIGUOUS", result.evidence)
        self.assertIsNone(result.record)

    def test_prefab_override_uses_model_bridge_without_names(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "Variant.prefab"
            path.write_text(self._variant(), encoding="utf-8")
            index = ModelSourceSemanticIndex([
                ModelSourceRecord(MODEL_GUID, 700, 137, 900, MESH_GUID, 4300000, evidence="DERIVED")
            ])
            effective = EffectivePrefabResolver(model_source_index=index).resolve(parse_prefab(path))
        state = effective.renderer(MODEL_GUID, 700)
        self.assertIsNotNone(state)
        self.assertEqual(900, state.owner_game_object_id)
        self.assertEqual(MESH_GUID, state.mesh_guid)
        self.assertEqual(4300000, state.mesh_file_id)
        self.assertEqual("MODEL_PREFAB_SOURCE_COMPONENT", state.source_kind)
        self.assertEqual("DERIVED", state.evidence)

    def test_realization_uses_persisted_semantic_binding_not_object_name(self):
        class Obj(dict):
            pass

        obj = Obj(name="Duplicate")
        obj["_vapb_renderer_bindings"] = json.dumps({"renderers": [{
            "source_asset_guid": MODEL_GUID,
            "renderer_file_id": "700",
            "game_object_file_id": "900",
            "mesh_guid": MESH_GUID,
            "mesh_file_id": "4300000",
            "occurrence_id": "occurrence-1",
        }]})
        result = BlenderRealizationIndex([obj]).lookup(RealizationKey(
            MODEL_GUID, "700", "900", MESH_GUID, "4300000", "occurrence-1"
        ))
        self.assertIs(result.obj, obj)
        self.assertEqual("EXACT", result.evidence)

    def test_missing_or_duplicate_realization_fails_closed(self):
        class Obj(dict):
            pass

        def make(name):
            obj = Obj(name=name)
            obj["_vapb_renderer_bindings"] = json.dumps({"renderers": [{
                "source_asset_guid": MODEL_GUID,
                "renderer_file_id": "700",
                "game_object_file_id": "900",
                "mesh_guid": MESH_GUID,
                "mesh_file_id": "4300000",
                "occurrence_id": "occurrence-1",
            }]})
            return obj

        key = RealizationKey(MODEL_GUID, "700", "900", MESH_GUID, "4300000", "occurrence-1")
        self.assertEqual("UNKNOWN", BlenderRealizationIndex().lookup(key).evidence)
        self.assertEqual("AMBIGUOUS", BlenderRealizationIndex([make("A"), make("B")]).lookup(key).evidence)

    def test_occurrence_identity_keeps_same_source_renderer_instances_separate(self):
        source = SourceComponentKey("MODEL", MODEL_GUID, 700)
        owner = OwnerKey("MODEL", MODEL_GUID, 900)
        mesh = MeshKey(MESH_GUID, 4300000)
        first = OccurrenceKey("scene-A", (
            OccurrenceStep("container-A", 1001, PREFAB_GUID),
        ), source)
        second = OccurrenceKey("scene-A", (
            OccurrenceStep("container-A", 1002, PREFAB_GUID),
        ), source)
        index = SemanticProvenanceIndex([
            OccurrenceRecord(first, owner, mesh, BridgeKey("pkg", "primitive-A")),
            OccurrenceRecord(second, owner, mesh, BridgeKey("pkg", "primitive-B")),
        ])
        self.assertEqual("EXACT", index.lookup_occurrence(first).status)
        self.assertEqual("EXACT", index.lookup_occurrence(second).status)
        self.assertNotEqual(first, second)

    def test_source_kind_and_shared_mesh_do_not_conflate_components(self):
        model = SourceComponentKey("MODEL", MODEL_GUID, 700)
        local = SourceComponentKey("PREFAB_LOCAL", PREFAB_GUID, 700)
        self.assertNotEqual(model, local)
        self.assertEqual(MeshKey(MESH_GUID, 4300000), MeshKey(MESH_GUID, 4300000))

    def test_bridge_without_observable_token_is_unknown(self):
        source = SourceComponentKey("MODEL", MODEL_GUID, 700)
        occurrence = OccurrenceKey("scene-A", (), source)
        record = OccurrenceRecord(
            occurrence,
            OwnerKey("MODEL", MODEL_GUID, 900),
            MeshKey(MESH_GUID, 4300000),
            None,
        )
        index = SemanticProvenanceIndex([record])
        self.assertEqual("UNKNOWN", index.lookup_bridge(BridgeKey("pkg", "missing")).status)

    def test_conflicting_bridge_records_fail_closed(self):
        source_a = SourceComponentKey("MODEL", MODEL_GUID, 700)
        source_b = SourceComponentKey("MODEL", MODEL_GUID, 701)
        owner = OwnerKey("MODEL", MODEL_GUID, 900)
        mesh = MeshKey(MESH_GUID, 4300000)
        bridge = BridgeKey("pkg", "primitive")
        index = SemanticProvenanceIndex([
            OccurrenceRecord(OccurrenceKey("scene", (), source_a), owner, mesh, bridge),
            OccurrenceRecord(OccurrenceKey("scene", (), source_b), owner, mesh, bridge),
        ])
        self.assertEqual("AMBIGUOUS", index.lookup_bridge(bridge).status)


if __name__ == "__main__":
    unittest.main()
