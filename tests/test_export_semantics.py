from __future__ import annotations

import json
import unittest

from unitypackage_blender_importer.export.asset_plan import (
    AssetOperation,
    ExportStrategy,
    FinalizerTaskType,
    GuidDecision,
    PathStatus,
    plan_assets,
)
from unitypackage_blender_importer.export.manifest import ExportManifest
from unitypackage_blender_importer.export.semantic_graph import (
    EdgeType,
    GraphNode,
    NodeType,
    Provenance,
    SemanticGraph,
    SourceIdentity,
)


class ExportSemanticGraphTests(unittest.TestCase):
    def _graph(self) -> SemanticGraph:
        graph = SemanticGraph()
        root = graph.add_node(GraphNode("root", NodeType.EXPORT_ROOT, Provenance("EXACT")))
        renderer = graph.add_node(
            GraphNode(
                "renderer-occurrence",
                NodeType.RENDERER_OCCURRENCE,
                Provenance("EXACT", source_package_id="sha256:" + "a" * 64, source_guid="prefab-guid", source_file_id="300"),
            )
        )
        mesh = graph.add_node(
            GraphNode(
                "mesh",
                NodeType.MESH_ASSET,
                Provenance("EXACT", source_package_id="sha256:" + "a" * 64, source_guid="model-guid", source_file_id="-100"),
                attributes={"operation": "PRESERVE"},
            )
        )
        material = graph.add_node(GraphNode("material", NodeType.MATERIAL_ASSET, Provenance("DERIVED")))
        texture = graph.add_node(GraphNode("texture", NodeType.TEXTURE_ASSET, Provenance("EXACT")))
        graph.add_edge("root", "renderer-occurrence", EdgeType.ROOT_CONTAINS_OBJECT)
        graph.add_edge("renderer-occurrence", "mesh", EdgeType.RENDERER_USES_MESH)
        graph.add_edge("renderer-occurrence", "material", EdgeType.RENDERER_USES_MATERIAL)
        graph.add_edge("material", "texture", EdgeType.MATERIAL_USES_TEXTURE)
        return graph

    def test_typed_reachability_keeps_shared_resource_and_proof_path(self):
        graph = self._graph()
        result = graph.reachable_from(["root"])
        self.assertEqual(set(result.included), {"root", "renderer-occurrence", "mesh", "material", "texture"})
        self.assertEqual(result.proof_path("texture"), ["root", "renderer-occurrence", "material", "texture"])
        self.assertEqual(
            result.edge_types("texture"),
            [EdgeType.ROOT_CONTAINS_OBJECT, EdgeType.RENDERER_USES_MATERIAL, EdgeType.MATERIAL_USES_TEXTURE],
        )

    def test_unknown_reference_is_preserved_and_reachable(self):
        graph = self._graph()
        graph.add_node(GraphNode("unknown", NodeType.PRESERVED_UNKNOWN_ASSET, Provenance("UNKNOWN")))
        graph.add_edge("material", "unknown", EdgeType.RAW_SERIALIZED_REFERENCE)
        result = graph.reachable_from(["root"])
        self.assertIn("unknown", result.included)
        self.assertIn("unknown", result.unsupported_preserved)
        plan = plan_assets(graph, ["root"])
        unknown = next(item for item in plan.assets if item.node_id == "unknown")
        self.assertEqual(unknown.operation.value, "UNSUPPORTED_PRESERVED")
        self.assertEqual(unknown.strategy.value, "UNSUPPORTED_BUT_PRESERVED")

    def test_ambiguous_provider_is_not_auto_selected(self):
        graph = self._graph()
        graph.add_node(GraphNode("provider-a", NodeType.TEXTURE_ASSET, Provenance("EXACT")))
        graph.add_node(GraphNode("provider-b", NodeType.TEXTURE_ASSET, Provenance("EXACT")))
        graph.add_edge("material", "provider-a", EdgeType.MATERIAL_USES_TEXTURE, {"provider_candidate": True})
        graph.add_edge("material", "provider-b", EdgeType.MATERIAL_USES_TEXTURE, {"provider_candidate": True})
        result = graph.reachable_from(["root"])
        self.assertIn("provider-a", result.included)
        self.assertIn("provider-b", result.included)
        self.assertTrue(result.ambiguous_edges)
        plan = plan_assets(graph, ["root"])
        provider = next(item for item in plan.assets if item.node_id == "provider-a")
        self.assertEqual(provider.operation, AssetOperation.AMBIGUOUS)
        self.assertEqual(provider.guid_decision.value, "AMBIGUOUS")

    def test_ambiguous_renderer_relation_is_an_export_error(self):
        graph = self._graph()
        graph.add_node(GraphNode("mesh-a", NodeType.MESH_ASSET, Provenance("EXACT")))
        graph.add_node(GraphNode("mesh-b", NodeType.MESH_ASSET, Provenance("EXACT")))
        graph.add_edge("renderer-occurrence", "mesh-a", EdgeType.RENDERER_USES_MESH)
        graph.add_edge("renderer-occurrence", "mesh-b", EdgeType.RENDERER_USES_MESH)
        plan = plan_assets(graph, ["root"])
        self.assertTrue(any(error.startswith("AMBIGUOUS_EDGE") for error in plan.errors))

    def test_semantic_nodes_are_not_planned_as_unity_assets(self):
        plan = plan_assets(self._graph(), ["root"])
        self.assertNotIn("root", {item.node_id for item in plan.assets})
        self.assertNotIn("renderer-occurrence", {item.node_id for item in plan.assets})

    def test_per_occurrence_material_slots_are_not_collapsed(self):
        graph = self._graph()
        graph.add_node(GraphNode("slot-0", NodeType.MATERIAL_ASSET, Provenance("EXACT")))
        graph.add_node(GraphNode("slot-1", NodeType.MATERIAL_ASSET, Provenance("EXACT")))
        graph.add_edge("renderer-occurrence", "slot-0", EdgeType.RENDERER_USES_MATERIAL, {"slot_index": 0})
        graph.add_edge("renderer-occurrence", "slot-1", EdgeType.RENDERER_USES_MATERIAL, {"slot_index": 1})
        result = graph.reachable_from(["root"])
        self.assertFalse(any(item[0] == "renderer-occurrence" and item[1] == EdgeType.RENDERER_USES_MATERIAL for item in result.ambiguous_edges))

    def test_asset_plan_separates_operation_strategy_and_guid(self):
        graph = self._graph()
        plan = plan_assets(graph, ["root"])
        mesh = next(item for item in plan.assets if item.node_id == "mesh")
        self.assertEqual(mesh.operation, AssetOperation.PRESERVE)
        self.assertEqual(mesh.strategy, ExportStrategy.PRESERVE_VERBATIM)
        self.assertEqual(mesh.guid_decision, GuidDecision.PRESERVE_SOURCE_GUID)
        self.assertEqual(mesh.path_status, PathStatus.DEFER)

    def test_created_mesh_emits_only_typed_future_rebind_task(self):
        graph = SemanticGraph()
        graph.add_node(GraphNode("root", NodeType.EXPORT_ROOT, Provenance("EXACT")))
        graph.add_node(GraphNode("new-mesh", NodeType.MESH_ASSET, Provenance("DERIVED"), {"operation": "CREATE"}))
        graph.add_edge("root", "new-mesh", EdgeType.ROOT_CONTAINS_OBJECT)
        plan = plan_assets(graph, ["root"])
        item = next(asset for asset in plan.assets if asset.node_id == "new-mesh")
        self.assertEqual(item.postimport_tasks, (FinalizerTaskType.REBIND_MODEL_SUBASSET.value,))

    def test_collision_is_reported_without_suffix_guessing(self):
        graph = self._graph()
        graph.add_node(GraphNode("other", NodeType.MATERIAL_ASSET, Provenance("EXACT", source_package_id="sha256:" + "b" * 64, source_guid="same"), {"source_path": "Assets/A.mat"}))
        graph.nodes["material"].attributes.update({"source_package_id": "sha256:" + "a" * 64, "source_guid": "same", "source_path": "Assets/A.mat"})
        graph.add_edge("root", "other", EdgeType.RAW_SERIALIZED_REFERENCE)
        plan = plan_assets(graph, ["root"])
        self.assertTrue(any(item.code == "CROSS_PACKAGE_GUID_COLLISION" for item in plan.collisions))
        self.assertFalse(any(item.path_status == PathStatus.NEW_PATH for item in plan.assets))

    def test_same_bytes_and_different_bytes_collisions_are_distinct(self):
        graph = SemanticGraph()
        graph.add_node(GraphNode("root", NodeType.EXPORT_ROOT, Provenance("EXACT")))
        graph.add_node(GraphNode("same-a", NodeType.MATERIAL_ASSET, Provenance("EXACT", "pkg", "guid-a"), {"bytes_sha256": "1"}))
        graph.add_node(GraphNode("same-b", NodeType.MATERIAL_ASSET, Provenance("EXACT", "pkg", "guid-b"), {"bytes_sha256": "1"}))
        graph.add_node(GraphNode("diff-a", NodeType.TEXTURE_ASSET, Provenance("EXACT", "pkg", "guid-c"), {"bytes_sha256": "2"}))
        graph.add_node(GraphNode("diff-b", NodeType.TEXTURE_ASSET, Provenance("EXACT", "pkg", "guid-c"), {"bytes_sha256": "3"}))
        for node_id in ("same-a", "same-b", "diff-a", "diff-b"):
            graph.add_edge("root", node_id, EdgeType.RAW_SERIALIZED_REFERENCE)
        plan = plan_assets(graph, ["root"])
        codes = {collision.code for collision in plan.collisions}
        self.assertIn("SAME_BYTES_DIFFERENT_GUID", codes)
        self.assertIn("DIFFERENT_BYTES_SAME_GUID", codes)

    def test_subassets_under_one_asset_guid_are_not_collisions(self):
        graph = SemanticGraph()
        graph.add_node(GraphNode("root", NodeType.EXPORT_ROOT, Provenance("EXACT")))
        graph.add_node(GraphNode("mesh-a", NodeType.MESH_ASSET, Provenance("EXACT", "pkg", "model", 100, "Assets/A.fbx")))
        graph.add_node(GraphNode("mesh-b", NodeType.MESH_ASSET, Provenance("EXACT", "pkg", "model", 200, "Assets/A.fbx")))
        graph.add_edge("root", "mesh-a", EdgeType.RAW_SERIALIZED_REFERENCE)
        graph.add_edge("root", "mesh-b", EdgeType.RAW_SERIALIZED_REFERENCE)
        self.assertFalse(plan_assets(graph, ["root"]).collisions)

    def test_move_delete_and_external_preserve_semantics(self):
        graph = SemanticGraph()
        graph.add_node(GraphNode("root", NodeType.EXPORT_ROOT, Provenance("EXACT")))
        graph.add_node(GraphNode("moved", NodeType.MATERIAL_ASSET, Provenance("EXACT", "pkg", "m", 1, "Assets/Old.mat"), {"operation": "MOVE", "desired_export_path": "Assets/New.mat"}))
        graph.add_node(GraphNode("deleted", NodeType.TEXTURE_ASSET, Provenance("EXACT", "pkg", "d", 2, "Assets/Delete.png"), {"operation": "DELETE"}))
        graph.add_node(GraphNode("external", NodeType.EXTERNAL_DEPENDENCY, Provenance("EXACT", "pkg", "e", 3, "Assets/External.mat")))
        for node_id in ("moved", "deleted", "external"):
            graph.add_edge("root", node_id, EdgeType.RAW_SERIALIZED_REFERENCE)
        assets = {item.node_id: item for item in plan_assets(graph, ["root"]).assets}
        self.assertEqual(assets["moved"].path_status.value, "MOVE")
        self.assertEqual(assets["moved"].guid_decision.value, "PRESERVE_SOURCE_GUID")
        self.assertEqual(assets["deleted"].reference_stability.value, "SOURCE_TARGET_REMOVED")
        self.assertEqual(assets["deleted"].postimport_tasks, ("DELETE_ASSET",))
        self.assertEqual(assets["external"].operation.value, "PRESERVE_EXTERNAL")

    def test_target_path_collision_is_fail_closed(self):
        graph = SemanticGraph()
        graph.add_node(GraphNode("root", NodeType.EXPORT_ROOT, Provenance("EXACT")))
        for node_id, guid in (("a", "a"), ("b", "b")):
            graph.add_node(GraphNode(node_id, NodeType.MATERIAL_ASSET, Provenance("EXACT", "pkg", guid, 1, f"Assets/{node_id}.mat"), {"operation": "MOVE", "desired_export_path": "Assets/Shared.mat"}))
            graph.add_edge("root", node_id, EdgeType.RAW_SERIALIZED_REFERENCE)
        plan = plan_assets(graph, ["root"])
        self.assertTrue(any(item.code == "TARGET_PATH_COLLISION" for item in plan.collisions))
        self.assertTrue(all(item.path_status.value == "COLLISION" for item in plan.assets if item.node_id in {"a", "b"}))

    def test_same_target_path_same_subasset_is_distinguished(self):
        graph = SemanticGraph()
        graph.add_node(GraphNode("root", NodeType.EXPORT_ROOT, Provenance("EXACT")))
        for node_id in ("a", "b"):
            graph.add_node(GraphNode(node_id, NodeType.MESH_ASSET, Provenance("EXACT", "pkg", "same", 7, "Assets/A.fbx"), {"operation": "MOVE", "desired_export_path": "Assets/Same.fbx"}))
            graph.add_edge("root", node_id, EdgeType.RAW_SERIALIZED_REFERENCE)
        codes = {item.code for item in plan_assets(graph, ["root"]).collisions}
        self.assertIn("SAME_TARGET_PATH_SAME_ASSET", codes)

    def test_manifest_contains_future_rebind_tasks_and_export_path(self):
        graph = SemanticGraph()
        graph.add_node(GraphNode("root", NodeType.EXPORT_ROOT, Provenance("EXACT")))
        graph.add_node(GraphNode("mesh", NodeType.MESH_ASSET, Provenance("DERIVED"), {"operation": "CREATE", "desired_export_path": "Assets/New.fbx"}))
        graph.add_edge("root", "mesh", EdgeType.RAW_SERIALIZED_REFERENCE)
        payload = json.loads(ExportManifest.from_plan(plan_assets(graph, ["root"]), generator_version="v", blender_version="b").to_json())
        self.assertEqual(payload["export_assets"][0]["desired_export_path"], "Assets/New.fbx")
        self.assertEqual(payload["reference_rebind_tasks"][0]["tasks"], ["REBIND_MODEL_SUBASSET"])

    def test_cross_package_and_extended_semantic_edges_remain_reachable(self):
        graph = SemanticGraph()
        graph.add_node(GraphNode("root-a", NodeType.EXPORT_ROOT, Provenance("EXACT")))
        graph.add_node(GraphNode("root-b", NodeType.EXPORT_ROOT, Provenance("EXACT")))
        graph.add_node(GraphNode("prefab", NodeType.PREFAB_ASSET, Provenance("EXACT", "pkg-a", "prefab")))
        graph.add_node(GraphNode("variant", NodeType.PREFAB_ASSET, Provenance("EXACT", "pkg-a", "variant")))
        graph.add_node(GraphNode("material", NodeType.MATERIAL_ASSET, Provenance("EXACT", "pkg-b", "mat")))
        graph.add_node(GraphNode("texture", NodeType.TEXTURE_ASSET, Provenance("EXACT", "pkg-c", "tex")))
        graph.add_node(GraphNode("controller", NodeType.ANIMATOR_CONTROLLER_ASSET, Provenance("EXACT", "pkg-a", "controller")))
        graph.add_node(GraphNode("physbone", NodeType.VRC_COMPONENT_STATE, Provenance("EXACT")))
        graph.add_node(GraphNode("unknown-ref", NodeType.PRESERVED_UNKNOWN_ASSET, Provenance("UNKNOWN")))
        graph.add_edge("root-a", "prefab", EdgeType.ROOT_CONTAINS_OBJECT)
        graph.add_edge("prefab", "variant", EdgeType.PREFAB_SOURCE_CHAIN)
        graph.add_edge("variant", "material", EdgeType.RENDERER_USES_MATERIAL)
        graph.add_edge("material", "texture", EdgeType.MATERIAL_USES_TEXTURE, {"property": "_MainTex"})
        graph.add_edge("prefab", "controller", EdgeType.AVATAR_USES_CONTROLLER)
        graph.add_edge("prefab", "physbone", EdgeType.RAW_SERIALIZED_REFERENCE)
        graph.add_edge("physbone", "unknown-ref", EdgeType.MONOBEHAVIOUR_REFERENCES_OBJECT)
        result = graph.reachable_from(["root-a", "root-b"])
        self.assertEqual({"material", "texture", "controller", "unknown-ref"}.issubset(result.included), True)
        manifest = ExportManifest.from_plan(plan_assets(graph, ["root-a", "root-b"]), generator_version="v", blender_version="b")
        package_ids = {item["source_package_id"] for item in json.loads(manifest.to_json())["source_packages"]}
        self.assertEqual(package_ids, {"pkg-a", "pkg-b", "pkg-c"})

    def test_semantic_fixture_preserves_renderer_occurrence_bones_and_shape_keys(self):
        graph = SemanticGraph()
        graph.add_node(GraphNode("root", NodeType.EXPORT_ROOT, Provenance("EXACT")))
        graph.add_node(GraphNode("mesh", NodeType.MESH_ASSET, Provenance("EXACT", "pkg", "mesh", 1), {"operation": "MODIFY"}))
        graph.add_node(GraphNode("r1", NodeType.RENDERER_OCCURRENCE, Provenance("EXACT", "pkg", "prefab", 10, "Assets/A.prefab"), {"material_slot": 0, "blendshape_weight": 0.1}))
        graph.add_node(GraphNode("r2", NodeType.RENDERER_OCCURRENCE, Provenance("EXACT", "pkg", "prefab", 11, "Assets/A.prefab"), {"material_slot": 0, "blendshape_weight": 0.9}))
        graph.add_node(GraphNode("bone", NodeType.BONE_SEMANTIC, Provenance("DERIVED"), {"semantic_status": "RENAMED_BONE", "old_name": "A", "new_name": "B"}))
        graph.add_node(GraphNode("shape", NodeType.SHAPE_KEY_DEFINITION, Provenance("DERIVED"), {"semantic_status": "CREATED_SHAPE_KEY", "name": "Smile"}))
        graph.add_node(GraphNode("weights", NodeType.BLENDSHAPE_OCCURRENCE, Provenance("DERIVED"), {"renderer_occurrence": "r2", "weight": 0.9}))
        graph.add_edge("root", "r1", EdgeType.ROOT_CONTAINS_OBJECT)
        graph.add_edge("root", "r2", EdgeType.ROOT_CONTAINS_OBJECT)
        graph.add_edge("r1", "mesh", EdgeType.RENDERER_USES_MESH)
        graph.add_edge("r2", "mesh", EdgeType.RENDERER_USES_MESH)
        graph.add_edge("r2", "bone", EdgeType.RAW_SERIALIZED_REFERENCE)
        graph.add_edge("r2", "shape", EdgeType.RAW_SERIALIZED_REFERENCE)
        graph.add_edge("r2", "weights", EdgeType.RAW_SERIALIZED_REFERENCE)
        payload = json.loads(ExportManifest.from_plan(plan_assets(graph, ["root"]), generator_version="v", blender_version="b").to_json())
        self.assertEqual(len(payload["renderer_mappings"]), 2)
        self.assertEqual(len(payload["bone_mappings"]), 1)
        self.assertEqual(len(payload["shape_key_mappings"]), 2)

    def test_required_negative_and_prefab_occurrence_scope(self):
        graph = SemanticGraph()
        graph.add_node(GraphNode("root", NodeType.EXPORT_ROOT, Provenance("EXACT")))
        graph.add_node(GraphNode("prefab", NodeType.PREFAB_ASSET, Provenance("EXACT", "pkg", "prefab", 1, "Assets/A.prefab")))
        graph.add_node(GraphNode("variant-occurrence", NodeType.RENDERER_OCCURRENCE, Provenance("EXACT", "pkg", "prefab", 20, "Assets/A.prefab", "occurrence-variant"), {"prefab_local": True, "variant_source": "Assets/Base.prefab"}))
        graph.add_node(GraphNode("duplicate-material", NodeType.MATERIAL_ASSET, Provenance("DERIVED"), {"operation": "DUPLICATE", "display_name": "SameName"}))
        graph.add_node(GraphNode("deleted-bone", NodeType.BONE_SEMANTIC, Provenance("DERIVED"), {"semantic_status": "DELETED_BONE", "display_name": "SameName"}))
        graph.add_node(GraphNode("unreachable", NodeType.TEXTURE_ASSET, Provenance("EXACT", "pkg", "unreachable")))
        graph.add_node(GraphNode("missing-provenance", NodeType.MATERIAL_ASSET, Provenance("DERIVED"), {"operation": "PRESERVE"}))
        graph.add_edge("root", "prefab", EdgeType.ROOT_CONTAINS_OBJECT)
        graph.add_edge("prefab", "variant-occurrence", EdgeType.ROOT_CONTAINS_OBJECT)
        graph.add_edge("variant-occurrence", "duplicate-material", EdgeType.RENDERER_USES_MATERIAL, {"slot_index": 0})
        graph.add_edge("variant-occurrence", "deleted-bone", EdgeType.RAW_SERIALIZED_REFERENCE)
        graph.add_edge("root", "missing-provenance", EdgeType.RAW_SERIALIZED_REFERENCE)
        plan = plan_assets(graph, ["root"])
        self.assertNotIn("unreachable", plan.proof_relations)
        self.assertTrue(any("MISSING_SOURCE_PROVENANCE" in error for error in plan.errors))
        duplicated = next(item for item in plan.assets if item.node_id == "duplicate-material")
        self.assertEqual(duplicated.guid_decision.value, "ALLOCATE_NEW_GUID")
        payload = json.loads(ExportManifest.from_plan(plan, generator_version="v", blender_version="b").to_json())
        self.assertEqual(payload["renderer_mappings"][0]["attributes"]["prefab_local"], True)
        self.assertEqual(payload["bone_mappings"][0]["attributes"]["semantic_status"], "DELETED_BONE")

    def test_unrecoverable_reference_and_duplicate_names_fail_without_name_matching(self):
        graph = SemanticGraph()
        graph.add_node(GraphNode("root", NodeType.EXPORT_ROOT, Provenance("EXACT")))
        with self.assertRaises(KeyError):
            graph.add_edge("root", "does-not-exist", EdgeType.RAW_SERIALIZED_REFERENCE)
        left = SourceIdentity("pkg", "guid-left", 1, "Assets/A.prefab")
        right = SourceIdentity("pkg", "guid-right", 1, "Assets/A.prefab")
        self.assertNotEqual(left.key, right.key)

    def test_manifest_round_trip_is_deterministic(self):
        graph = self._graph()
        plan = plan_assets(graph, ["root"])
        manifest = ExportManifest.from_plan(plan, generator_version="0.4.0-candidate", blender_version="5.2.1")
        first = manifest.to_json()
        second = ExportManifest.from_dict(json.loads(first)).to_json()
        self.assertEqual(first, second)
        self.assertEqual(json.loads(first)["schema_version"], "vapb-export-manifest-1")
        self.assertEqual(json.loads(first)["export_roots"], ["root"])
        self.assertTrue(json.loads(first)["renderer_mappings"])
        self.assertIn("proof_relations", json.loads(first)["reachability"][0])

    def test_unknown_manifest_fields_are_ignored_for_forward_compatibility(self):
        graph = self._graph()
        manifest = ExportManifest.from_plan(plan_assets(graph, ["root"]), generator_version="v", blender_version="b")
        payload = json.loads(manifest.to_json())
        payload["future_field"] = {"not": "understood"}
        restored = ExportManifest.from_dict(payload)
        self.assertEqual(restored.schema_version, manifest.schema_version)

    def test_manifest_stability_does_not_depend_on_node_insertion_order(self):
        left = self._graph()
        right = SemanticGraph()
        for node_id in reversed(list(left.nodes)):
            right.add_node(left.nodes[node_id])
        for edge in reversed(left.edges):
            right.add_edge(edge.source, edge.target, edge.edge_type, edge.attributes)
        left_json = ExportManifest.from_plan(plan_assets(left, ["root"]), generator_version="v", blender_version="b").to_json()
        right_json = ExportManifest.from_plan(plan_assets(right, ["root"]), generator_version="v", blender_version="b").to_json()
        self.assertEqual(left_json, right_json)

    def test_source_identity_does_not_use_name(self):
        identity = SourceIdentity("sha256:" + "a" * 64, "guid", "42", "Assets/A.prefab")
        self.assertNotIn("name", identity.key)
        self.assertEqual(identity.key, ("sha256:" + "a" * 64, "guid", "guid", "file_id", "42"))


if __name__ == "__main__":
    unittest.main()
