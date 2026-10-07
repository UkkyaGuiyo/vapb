"""Plain-Python comparator for the offline inbound material face diagnostic.

This is evidence tooling, not product code. It never reads material names, counts, slot ordinals,
or fitted transforms to infer identity. Geometry is compared as oriented triangle-corner Counters.
"""
from __future__ import annotations

from collections import Counter
from itertools import permutations
import hashlib
import json
from pathlib import Path
import sys

PACKAGE_SHA256 = "d6245d25c3cbd513c49b8d2e241b313a752331cd338563becab6eb7c819bfa0c"
UNITY_DIAGNOSTIC_SHA256 = "af56ccfa654dcf8c09dcd91c5eb62dc58f773682a9dc339a7372056068a690d2"
SOURCE_FBX_SHA256 = "fbe25a43a81a066c443093a0788a05569a4ec54e2d673fe133bffa7f801309c5"
CONFIRMED_BLEND_SHA256 = "58a3863a44198555bf07fdb56eb86e411b0804523ac2db694283a0ed9d8d122c"
EXPECTED_MATERIALS = {
    ("eb805efb35118044db5e74adc652673a", "2100000"),
    ("0318f358e4c29034aa90cc8c50b58a93", "2100000"),
    ("64f92a1bd9b35a040bf9e2c6d200b34c", "2100000"),
}
EXPECTED_SOURCE_MESH = ("abcdefabcdefabcdefabcdefabcdefab", "3538053534738119282")
EXPECTED_SOURCE_FBX_META_SHA256 = "ed9bb63c5bbc23e8dc2fa01353a037fef0b907b2842992598c1e1db911c8240d"
EXPECTED_SOURCE_PREFAB_GUID = "7cbdcbe81fde386408bcfb379e62b6bb"
EXPECTED_RENDERER_FILE_ID = "3728717051629469441"
UNITY_TO_BLENDER = ((-1.0, 0.0, 0.0), (0.0, 0.0, -1.0), (0.0, 1.0, 0.0))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def qpoint(point):
    return tuple(round(float(x), 6) for x in point)


def cyclic_key(triangle):
    """Canonicalize only cyclic rotations; reversed winding remains distinct."""
    tri = tuple(qpoint(p) for p in triangle)
    return min(tri, tri[1:] + tri[:1], tri[2:] + tri[:2])


def reverse_key(triangle):
    tri = tuple(qpoint(p) for p in triangle)
    return cyclic_key((tri[0], tri[2], tri[1]))


def unity_source_partitions(diag):
    if (diag.get("source_renderer_mesh_guid", "").lower(),
            str(diag.get("source_renderer_mesh_local_file_id", ""))) != EXPECTED_SOURCE_MESH:
        raise ValueError("PINNED_SOURCE_MESH_IDENTITY_MISMATCH")
    vertices = diag.get("source_mesh_vertices")
    submeshes = diag.get("source_submeshes")
    matrix = diag.get("source_mesh_to_prefab_root")
    materials = diag.get("source_renderer_materials")
    if not all((vertices, submeshes, matrix, materials)):
        raise ValueError("UNITY_SOURCE_GEOMETRY_WITNESS_INCOMPLETE")
    if len(submeshes) != len(materials) or not submeshes:
        raise ValueError("UNITY_SUBMESH_MATERIAL_CARDINALITY_MISMATCH")

    def unity_root(v):
        xyz = (float(v["x"]), float(v["y"]), float(v["z"]))
        mapped = tuple(sum(float(matrix[f"e{r}{c}"]) * xyz[c] for c in range(3))
                       + float(matrix[f"e{r}3"]) for r in range(3))
        # Apply the repository's explicit Unity-to-Blender basis: (-x, -z, y).
        x, y, z = mapped
        return (-x, -z, y)

    refs = []
    parts = []
    for material, submesh in zip(materials, submeshes):
        if material.get("is_null") or not material.get("guid_lookup_succeeded"):
            raise ValueError("UNITY_SOURCE_MATERIAL_IDENTITY_UNPROVEN")
        guid = str(material.get("guid", "")).lower()
        file_id = str(material.get("local_file_id", ""))
        if not guid or not file_id:
            raise ValueError("UNITY_SOURCE_MATERIAL_IDENTITY_INCOMPLETE")
        indices = submesh.get("indices", [])
        if not indices or len(indices) % 3:
            raise ValueError("EMPTY_OR_INVALID_UNITY_SUBMESH")
        if any(type(index) is not int or index < 0 or index >= len(vertices)
               for index in indices):
            raise ValueError("UNITY_SUBMESH_INDEX_OUT_OF_RANGE")
        if int(submesh.get("triangle_count", -1)) != len(indices) // 3:
            raise ValueError("UNITY_SUBMESH_TRIANGLE_COUNT_WITNESS_INVALID")
        part = Counter()
        for i in range(0, len(indices), 3):
            try:
                tri = [unity_root(vertices[indices[i + j]]) for j in range(3)]
            except (IndexError, KeyError, TypeError, ValueError):
                raise ValueError("UNITY_SUBMESH_INDEX_OUT_OF_RANGE")
            # The basis matrix has determinant -1. Keep the parity explicit:
            # the reversed candidate is reported independently, never silently folded in.
            part[cyclic_key(tri)] += 1
        refs.append((guid, file_id))
        parts.append(part)
    return refs, parts


def captured_groups(mesh):
    groups = {}
    for tri in mesh.get("triangles", []):
        idx = int(tri["material_index"])
        if idx < 0:
            raise ValueError("NEGATIVE_BLENDER_MATERIAL_INDEX")
        groups.setdefault(idx, Counter())[cyclic_key(tri["corners"])] += 1
    if not groups:
        raise ValueError("CAPTURED_MESH_HAS_NO_TRIANGLES")
    return groups


def match_partitions(source_parts, target_groups, reverse_source=False):
    """Return source-partition -> target-slot only for unique nonempty exact multisets."""
    normalized = [Counter({(reverse_key(t) if reverse_source else t): n for t, n in part.items()})
                  for part in source_parts]
    if any(not part for part in normalized) or any(not part for part in target_groups.values()):
        raise ValueError("EMPTY_PARTITION_FAIL_CLOSED")
    mapping = {}
    for source_index, source in enumerate(normalized):
        matches = [target_index for target_index, target in target_groups.items()
                   if source == target]
        if len(matches) != 1:
            raise ValueError("PARTITION_MATCH_NOT_UNIQUE")
        mapping[source_index] = matches[0]
    used = list(mapping.values())
    if len(used) != len(set(used)) or set(used) != set(target_groups):
        raise ValueError("UNUSED_OR_UNMATCHED_PARTITION_FAIL_CLOSED")
    return mapping


def triangle_union(meshes):
    result = Counter()
    for mesh in meshes:
        for tri in mesh.get("triangles", []):
            result[cyclic_key(tri["corners"])] += 1
    return result


def transform_modes_match(unity_parts, meshes):
    expected = Counter()
    for part in unity_parts:
        expected.update(part)
    actual = triangle_union(meshes)
    direct = expected == actual
    reverse = Counter()
    for triangle, multiplicity in expected.items():
        reverse[reverse_key(triangle)] += multiplicity
    reversed_only = reverse == actual
    return {
        "oriented_corner_multiset_equal": direct,
        "uniform_reverse_corner_multiset_equal": reversed_only,
        "aggregate_triangle_multiplicity_equal": sum(expected.values()) == sum(actual.values()),
    }


def identity_failures(mapping, refs, mesh, source_package_id):
    failures = []
    slots = mesh.get("object_slots", [])
    for source_index, blender_slot in mapping.items():
        expected = refs[source_index]
        if blender_slot >= len(slots):
            failures.append({"source_submesh": source_index, "blender_slot": blender_slot,
                             "error": "BLENDER_SLOT_IDENTITY_MISSING"})
            continue
        actual = slots[blender_slot].get("identity", {})
        if (actual.get("package_id") != source_package_id
                or str(actual.get("guid", "")).lower() != expected[0]
                or str(actual.get("file_id", "")) != expected[1]):
            failures.append({
                "source_submesh": source_index,
                "blender_slot": blender_slot,
                "expected_package_id": source_package_id,
                "expected_guid": expected[0],
                "expected_file_id": expected[1],
                "actual_package_id": actual.get("package_id", ""),
                "actual_guid": actual.get("guid", ""),
                "actual_file_id": actual.get("file_id", ""),
            })
    return failures


def source_revision_join_valid(join, diagnostic_refs, output_package_sha):
    return (
        join.get("status") == "PASS"
        and join.get("fixture_package_context_sha256") == PACKAGE_SHA256
        and join.get("unity_diagnostic_output_package_sha256") == output_package_sha
        and join.get("source_fbx_sha256") == SOURCE_FBX_SHA256
        and join.get("source_fbx_meta_sha256") == EXPECTED_SOURCE_FBX_META_SHA256
        and join.get("source_fbx_meta_guid") == EXPECTED_SOURCE_MESH[0]
        and join.get("source_prefab_meta_guid") == EXPECTED_SOURCE_PREFAB_GUID
        and join.get("source_mesh_guid") == EXPECTED_SOURCE_MESH[0]
        and str(join.get("source_mesh_file_id", "")) == EXPECTED_SOURCE_MESH[1]
        and str(join.get("source_renderer_file_id_from_unity_override", "")) == EXPECTED_RENDERER_FILE_ID
        and str(join.get("source_renderer_file_id_from_raw_prefab", "")) == EXPECTED_RENDERER_FILE_ID
        and join.get("raw_prefab_material_refs") == diagnostic_refs
    )


def control_tests():
    # Six partitions with distinct geometry, then every possible target slot order.
    source = [Counter({((float(i), 0.0, 0.0),
                        (float(i), 1.0, 0.0),
                        (float(i), 0.0, 1.0)): 1}) for i in range(6)]
    six = 0
    for order in permutations(range(6)):
        targets = {slot: source[source_index] for slot, source_index in enumerate(order)}
        actual = match_partitions(source, targets)
        expected = {source_index: order.index(source_index) for source_index in range(6)}
        if actual != expected:
            raise AssertionError("six-permutation face geometry mapping control failed")
        six += 1

    # Equal counts are deliberately uninformative; distinct geometry still maps exactly.
    equal_source = [
        Counter({((0.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)): 2}),
        Counter({((7.0, 0.0, 0.0), (7.0, 1.0, 0.0), (7.0, 0.0, 1.0)): 2}),
    ]
    equal_targets = {0: equal_source[1], 1: equal_source[0]}
    if match_partitions(equal_source, equal_targets) != {0: 1, 1: 0}:
        raise AssertionError("equal-count disjoint-geometry control failed")
    changed_geometry_rejected = False
    try:
        mutated_targets = dict(equal_targets)
        mutated_targets[0] = Counter({cyclic_key(((99.0, 0.0, 0.0),
                                                 (99.0, 1.0, 0.0),
                                                 (99.0, 0.0, 1.0))): 2})
        match_partitions(equal_source, mutated_targets)
    except ValueError:
        changed_geometry_rejected = True
    if not changed_geometry_rejected:
        raise AssertionError("changed geometry control unexpectedly matched")
    duplicate_refs = [("same-guid", "2100000"), ("same-guid", "2100000")]
    duplicate_ref_map = match_partitions(equal_source, equal_targets)
    combined_by_identity = {}
    for source_index, slot in duplicate_ref_map.items():
        combined_by_identity.setdefault(duplicate_refs[source_index], set()).add(slot)
    if (len(combined_by_identity) != 1
            or len(next(iter(combined_by_identity.values()))) != 2):
        raise AssertionError("repeated exact material identity geometry control failed")

    # Swap one distinct triangle's assigned material while preserving both counts.
    face_a1 = ((10.0, 0.0, 0.0), (10.0, 1.0, 0.0), (10.0, 0.0, 1.0))
    face_a2 = ((11.0, 0.0, 0.0), (11.0, 1.0, 0.0), (11.0, 0.0, 1.0))
    face_b1 = ((12.0, 0.0, 0.0), (12.0, 1.0, 0.0), (12.0, 0.0, 1.0))
    face_b2 = ((13.0, 0.0, 0.0), (13.0, 1.0, 0.0), (13.0, 0.0, 1.0))
    correct_equal = [
        Counter({cyclic_key(face_a1): 1, cyclic_key(face_a2): 1}),
        Counter({cyclic_key(face_b1): 1, cyclic_key(face_b2): 1}),
    ]
    wrong_equal = {
        0: Counter({cyclic_key(face_a1): 1, cyclic_key(face_b1): 1}),
        1: Counter({cyclic_key(face_a2): 1, cyclic_key(face_b2): 1}),
    }
    if [sum(part.values()) for part in correct_equal] != [
            sum(part.values()) for part in wrong_equal.values()]:
        raise AssertionError("negative control did not preserve per-slot counts")
    try:
        match_partitions(correct_equal, wrong_equal)
    except ValueError:
        equal_count_label_swap_rejected = True
    else:
        raise AssertionError("equal-count distinct-face label swap was not detected")

    # Reordering corners cyclically preserves orientation; reversing is detected separately.
    tri = ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0))
    if cyclic_key(tri) != cyclic_key((tri[1], tri[2], tri[0])):
        raise AssertionError("cyclic winding control failed")
    if cyclic_key(tri) == cyclic_key((tri[0], tri[2], tri[1])):
        raise AssertionError("reverse winding control failed")

    # Duplicate geometry across distinct partitions and empty/unused targets must reject.
    rejected = {}
    for name, parts, targets in (
        ("duplicate_geometry", [source[0], source[0]], {0: source[0], 1: source[0]}),
        ("empty_source", [Counter()], {0: source[0]}),
        ("unused_target", [source[0]], {0: source[0], 1: source[1]}),
    ):
        try:
            match_partitions(parts, targets)
        except ValueError:
            rejected[name] = True
        else:
            rejected[name] = False
    if not all(rejected.values()):
        raise AssertionError("duplicate/empty/unused fail-closed controls failed")

    # Repeated face multiplicity is meaningful and cannot be collapsed to a set.
    one_face = ((20.0, 0.0, 0.0), (20.0, 1.0, 0.0), (20.0, 0.0, 1.0))
    repeated = [Counter({cyclic_key(one_face): 2})]
    try:
        match_partitions(repeated, {0: Counter({cyclic_key(one_face): 1})})
    except ValueError:
        pass
    else:
        raise AssertionError("triangle multiplicity control unexpectedly accepted")

    return {
        "six_slot_permutations_passed": six,
        "equal_count_disjoint_geometry_passed": True,
        "changed_geometry_rejected": changed_geometry_rejected,
        "equal_count_distinct_face_label_swap_rejected": equal_count_label_swap_rejected,
        "repeated_exact_material_identity_with_distinct_geometry_mapped": True,
        "cyclic_orientation_passed": True,
        "reversed_orientation_detected": True,
        "duplicate_geometry_rejected": rejected["duplicate_geometry"],
        "empty_partition_rejected": rejected["empty_source"],
        "unused_partition_rejected": rejected["unused_target"],
        "triangle_multiplicity_preserved": True,
    }


def main():
    args = sys.argv[1:]
    if len(args) != 5:
        raise SystemExit("usage: <Input.fbx> <UnityDiagnostic.json> <capture.json> <package.unitypackage> <result.json>")
    fbx_path, unity_path, capture_path, package_path, output = map(
        lambda item: Path(item).resolve(), args)
    if output.exists():
        raise FileExistsError(output)
    pins = ((fbx_path, SOURCE_FBX_SHA256), (unity_path, UNITY_DIAGNOSTIC_SHA256),
            (package_path, PACKAGE_SHA256))
    for path, expected in pins:
        if sha256(path) != expected:
            raise AssertionError("input SHA-256 pin mismatch: " + path.name)
    capture = json.loads(capture_path.read_text(encoding="utf-8"))
    if capture.get("status") != "CAPTURED":
        raise ValueError("BLENDER_CAPTURE_NOT_COMPLETE")
    if capture.get("input_sha256_postflight") != capture.get("input_sha256"):
        raise ValueError("CAPTURE_INPUT_POSTFLIGHT_HASH_MISMATCH")
    captured_hashes = capture.get("input_sha256", {})
    if captured_hashes.get("source_fbx") != SOURCE_FBX_SHA256:
        raise ValueError("CAPTURE_SOURCE_FBX_HASH_MISMATCH")
    if captured_hashes.get("unity_diagnostic") != UNITY_DIAGNOSTIC_SHA256:
        raise ValueError("CAPTURE_UNITY_DIAGNOSTIC_HASH_MISMATCH")
    if captured_hashes.get("package") != PACKAGE_SHA256:
        raise ValueError("CAPTURE_PACKAGE_HASH_MISMATCH")

    diag = json.loads(unity_path.read_text(encoding="utf-8"))
    unity_package_sha = str(diag.get("package_sha256", "")).lower()
    if len(unity_package_sha) != 64 or any(c not in "0123456789abcdef" for c in unity_package_sha):
        raise ValueError("UNITY_DIAGNOSTIC_PACKAGE_IDENTITY_MISSING")
    refs, source_parts = unity_source_partitions(diag)
    diag_refs = [
        {"guid": str(row.get("guid", "")).lower(),
         "file_id": str(row.get("local_file_id", ""))}
        for row in diag.get("source_renderer_materials", [])
    ]
    if capture.get("fixture_raw_prefab_material_refs") != diag_refs:
        raise ValueError("UNITY_DIAGNOSTIC_MATERIAL_REFS_DO_NOT_MATCH_RAW_FIXTURE_PREFAB")
    revision_join = capture.get("source_revision_join", {})
    if not source_revision_join_valid(revision_join, diag_refs, unity_package_sha):
        raise ValueError("SOURCE_CONTENT_REVISION_JOIN_NOT_PROVEN_OR_STALE")
    fbx_table = capture.get("raw_input_fbx_semantic_table", {})
    if (fbx_table.get("model_uid") != 208084244
            or fbx_table.get("geometry_uid") != 329684292
            or not fbx_table.get("global_settings_properties70")
            or not fbx_table.get("model_object_properties70")
            or not fbx_table.get("geometry_layer_element_material")
            or not fbx_table.get("model_material_connections_in_file_order")):
        raise ValueError("OFFICIAL_FBX_SEMANTIC_TABLE_INCOMPLETE")
    source_ref_set = set(refs)
    if source_ref_set != EXPECTED_MATERIALS or len(refs) != len(EXPECTED_MATERIALS):
        raise ValueError("PINNED_SOURCE_MATERIAL_IDENTITIES_MISMATCH")
    controls = control_tests()
    result = {
        "status": "UNPROVEN",
        "read_only_diagnostic": True,
        "input_sha256": {
            "source_fbx": sha256(fbx_path),
            "unity_diagnostic": sha256(unity_path),
            "package": sha256(package_path),
            "capture": sha256(capture_path),
        },
        "unity_diagnostic_output_package_identity": "sha256:" + unity_package_sha,
        "source_fixture_package_context": "sha256:" + PACKAGE_SHA256,
        "package_contexts_are_distinct": unity_package_sha != PACKAGE_SHA256,
        "source_content_revision_join": revision_join,
        "raw_input_fbx_semantic_table": fbx_table,
        "raw_prefab_material_refs_match_unity_diagnostic": True,
        "source_mesh_identity": {"guid": EXPECTED_SOURCE_MESH[0],
                                 "file_id": EXPECTED_SOURCE_MESH[1]},
        "source_material_refs_by_unity_submesh": [
            {"submesh": index, "guid": guid, "file_id": file_id,
             "package_id": "sha256:" + PACKAGE_SHA256}
            for index, (guid, file_id) in enumerate(refs)
        ],
        "geometry_controls": controls,
        "comparisons": {},
        "mapping": None,
    }

    raw_meshes = capture.get("raw_input_fbx_native_import", [])
    before = capture.get("package_import", {}).get("before_confirm", {})
    after = capture.get("package_import", {}).get("after_confirm", {})
    saved = capture.get("confirmed_saved_scene", {}).get("mesh", {})
    if not raw_meshes or not before or not after or not saved:
        result["reason"] = "REQUIRED_CAPTURE_STAGE_MISSING"
    else:
        raw_modes = transform_modes_match(source_parts, raw_meshes)
        before_modes = transform_modes_match(source_parts, [before])
        after_modes = transform_modes_match(source_parts, [after])
        saved_modes = transform_modes_match(source_parts, [saved])
        result["comparisons"] = {
            "unity_source_to_raw_input_fbx": raw_modes,
            "unity_source_to_package_mesh_before_confirm": before_modes,
            "unity_source_to_package_mesh_after_confirm": after_modes,
            "unity_source_to_confirmed_saved_scene": saved_modes,
            "before_after_geometry_equal_by_slot": (
                {k: v["corners"] for k, v in enumerate(before.get("triangles", []))}
                == {k: v["corners"] for k, v in enumerate(after.get("triangles", []))}
                and [t["material_index"] for t in before.get("triangles", [])]
                == [t["material_index"] for t in after.get("triangles", [])]
            ),
        }
        mapping_candidates = {}
        for orientation, reverse_source in (("direct", False), ("uniform_reverse_observed", True)):
            stages = {}
            for stage_name, mesh in (("raw_input_fbx", raw_meshes[0]),
                                     ("before_confirm", before),
                                     ("after_confirm", after),
                                     ("confirmed_saved_scene", saved)):
                try:
                    stage_meshes = raw_meshes if stage_name == "raw_input_fbx" else [mesh]
                    stage_groups = {}
                    for native_mesh in stage_meshes:
                        for slot_index, counter in captured_groups(native_mesh).items():
                            if slot_index in stage_groups:
                                stage_groups[slot_index].update(counter)
                            else:
                                stage_groups[slot_index] = counter
                    mapping = match_partitions(source_parts, stage_groups, reverse_source)
                except ValueError as error:
                    stages[stage_name] = {"status": "UNPROVEN", "error": str(error)}
                    continue
                mesh_for_identity = mesh if stage_name != "raw_input_fbx" else None
                failures = (identity_failures(mapping, refs, mesh_for_identity,
                                              "sha256:" + PACKAGE_SHA256)
                            if mesh_for_identity is not None
                            else [])
                stages[stage_name] = {
                    "status": "EXACT_MULTIMAP",
                    "source_submesh_to_blender_slot": {
                        str(source_index): target_index for source_index, target_index in mapping.items()
                    },
                    "identity_failures": failures,
                }
            mapping_candidates[orientation] = stages
        result["mapping_candidates_by_orientation"] = mapping_candidates
        result["status"] = "UNPROVEN_ORIENTATION_OR_FRAME"
        direct_geometry = all(mode["oriented_corner_multiset_equal"]
                              for mode in (raw_modes, before_modes, after_modes, saved_modes))
        direct_maps = mapping_candidates.get("direct", {})
        direct_identity = direct_maps.get("after_confirm", {}).get("identity_failures", [])
        if direct_geometry and direct_maps.get("after_confirm", {}).get("status") == "EXACT_MULTIMAP":
            result["mapping"] = {
                "orientation": "direct",
                "source_submesh_to_blender_slot":
                    direct_maps["after_confirm"]["source_submesh_to_blender_slot"],
                "identity_failures_by_stage": {
                    stage: evidence.get("identity_failures", [])
                    for stage, evidence in direct_maps.items()
                    if stage != "raw_input_fbx"
                },
            }
            if not direct_identity:
                result["status"] = "MAPPING_PROVEN_DIAGNOSTIC"
            else:
                result["status"] = "GEOMETRY_PROVEN_MATERIAL_IDENTITY_MISMATCH"
        else:
            result["reason"] = "NO_SINGLE_PINNED_ROOT_FRAME_ORIENTATION_MATCH"

    # Identity and revision negative controls exercise the exact comparison gate.
    fake_refs = [("mat-a", "2100000"), ("mat-b", "2100000")]
    fake_mesh = {"object_slots": [
        {"identity": {"package_id": "sha256:" + PACKAGE_SHA256,
                      "guid": "mat-a", "file_id": "2100000"}},
        {"identity": {"package_id": "sha256:" + PACKAGE_SHA256,
                      "guid": "mat-b", "file_id": "2100000"}},
    ]}
    wrong_identity_rejected = bool(identity_failures(
        {0: 0, 1: 1}, [("wrong-a", "2100000"), ("wrong-b", "2100000")],
        fake_mesh, "sha256:" + PACKAGE_SHA256))
    fake_wrong_package_mesh = {"object_slots": [
        {"identity": {"package_id": "sha256:" + "0" * 64,
                      "guid": "mat-a", "file_id": "2100000"}},
        {"identity": {"package_id": "sha256:" + "0" * 64,
                      "guid": "mat-b", "file_id": "2100000"}},
    ]}
    wrong_package_rejected = bool(identity_failures(
        {0: 0, 1: 1}, fake_refs, fake_wrong_package_mesh,
        "sha256:" + PACKAGE_SHA256))
    stale_join = dict(revision_join)
    stale_join["source_fbx_meta_sha256"] = "0" * 64
    stale_meta_rejected = not source_revision_join_valid(
        stale_join, diag_refs, unity_package_sha)
    controls.update({
        "wrong_material_identity_rejected": wrong_identity_rejected,
        "wrong_package_context_rejected": wrong_package_rejected,
        "stale_source_meta_rejected": stale_meta_rejected,
    })
    if not all((wrong_identity_rejected, wrong_package_rejected,
                stale_meta_rejected, controls["changed_geometry_rejected"])):
        raise AssertionError("identity/package/revision/geometry negative control failed")

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print("INBOUND_MATERIAL_FACE_COMPARISON_" + result["status"] + " "
          + json.dumps({"output": str(output), "reason": result.get("reason", "")}, sort_keys=True))
    if result["status"] != "MAPPING_PROVEN_DIAGNOSTIC":
        raise SystemExit(2)


if __name__ == "__main__":
    main()

