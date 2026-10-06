"""Synthetic Blender integration proof for exact FBX external Material receipts."""

from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from unitypackage_blender_importer.blender.dependency_resolver import (
    EXTERNAL_SLOT_CLAIMED,
    INVALID_FBX_CONSUMER,
    MISSING_MATERIAL_FILE_ID,
    USER_EDIT_PRESERVED,
    capture_dependency,
    load_dependency_registry,
    resolve_scene_dependencies,
)
from unitypackage_blender_importer.blender.fbx_receipt import (
    copy_with_receipt,
    make_receipt,
    persist_receipt,
    persist_shape_receipts,
)
from unitypackage_blender_importer.blender.material_builder import (
    apply_materials_by_name,
    capture_composition_member_external_dependencies,
)
from unitypackage_blender_importer.blender.model_witness_bridge import (
    plan_witness_material_dependencies,
    realize_repeated_shape_occurrences,
)
from unitypackage_blender_importer.unity.asset_database import AssetDatabase
from unitypackage_blender_importer.unity.occurrence_projection import occurrence_identity


PACKAGE = "synthetic-geometry-package"
FBX_GUID = "a" * 32
FBX_SHA = "b" * 64
MATERIAL_GUID = "c" * 32
MATERIAL_FILE_ID = "2100000"


def reset():
    # Hidden template Objects from repeated-shape realization are not selected
    # by the normal viewport operator, so remove every scene datablock directly.
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for data in list(bpy.data.meshes):
        if data.users == 0:
            bpy.data.meshes.remove(data)
    for data in list(bpy.data.materials):
        if data.users == 0:
            bpy.data.materials.remove(data)
    scene = bpy.context.scene
    if "unitypackage_dependency_registry" in scene:
        del scene["unitypackage_dependency_registry"]
    return scene


def consumer(name="FBXConsumer", shared_mesh=None, *, realization=None, package=PACKAGE):
    mesh = shared_mesh or bpy.data.meshes.new(name + "Mesh")
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj["unity_source_package_id"] = package
    obj["unity_asset_path"] = "Assets/Body.fbx"
    persist_receipt(obj, make_receipt(1001, 2001, FBX_GUID, FBX_SHA))
    if realization:
        obj["_vapb_fbx_realization_id"] = realization
    return obj


def provider(guid=MATERIAL_GUID, file_id=MATERIAL_FILE_ID, package="synthetic-material-package"):
    material = bpy.data.materials.new("ExternalMaterial")
    material["unity_material_guid"] = guid
    material["unity_material_file_id"] = file_id
    material["unity_source_package_id"] = package
    material["unity_material_path"] = "Assets/External.mat"
    return material


def record_for(obj, *, slot=0, row="row-v1:synthetic", guid=MATERIAL_GUID,
               file_id=MATERIAL_FILE_ID, row_status="valid", ambiguous=False):
    return {
        "dependency_type": "FBX_EXTERNAL_MATERIAL",
        "consumer_receipt_version": 1,
        "consumer_fbx_receipt_version": obj["_vapb_fbx_receipt_version"],
        "consumer_package_id": obj["unity_source_package_id"],
        "consumer_asset_path": obj["unity_asset_path"],
        "consumer_fbx_guid": FBX_GUID,
        "consumer_fbx_sha256": FBX_SHA,
        "consumer_fbx_model_uid": obj["_vapb_fbx_model_uid"],
        "consumer_fbx_geometry_uid": obj["_vapb_fbx_geometry_uid"],
        "consumer_fbx_object_receipt_id": obj["_vapb_fbx_object_receipt_id"],
        "consumer_fbx_mesh_receipt_id": obj["_vapb_fbx_mesh_receipt_id"],
        "consumer_native_realization_id": obj["_vapb_fbx_realization_id"],
        "consumer_receipt_valid": True,
        "consumer_slot_index": slot,
        "source_row_identity": row,
        "source_row_status": row_status,
        "source_row_ambiguous": ambiguous,
        "target_guid_raw": guid,
        "target_file_id_raw": file_id,
        "target_guid": guid,
        "target_file_id": file_id,
    }


def witnessed_claim(obj, *, explicit_null=False, material_guid=MATERIAL_GUID,
                    material_file_id=MATERIAL_FILE_ID):
    context = "synthetic-root-context"
    package_sha = "d" * 64
    material_ref = None if explicit_null else {"guid": material_guid, "file_id": material_file_id}
    projection = {
        "root_context_id": context,
        "root_package_id": "synthetic-prefab-package",
        "root_member_id": "synthetic-prefab-member",
        "root_asset_guid": "e" * 32,
        "instance_edge_path": [],
        "source_package_id": PACKAGE,
        "source_key": {"source_kind": "MODEL_SOURCE", "source_asset_guid": FBX_GUID,
                       "renderer_file_id": "7001"},
        "renderer_class_id": 23,
        "mesh": {"source_package_id": PACKAGE, "mesh_guid": FBX_GUID,
                 "source_sha256": FBX_SHA, "mesh_file_id": "-31"},
        "materials": {0: material_ref},
        "material_status": "EXACT",
        "material_slot_count": 1,
    }
    projection["occurrence_id"] = occurrence_identity(projection)
    obj["_vapb_root_context_id"] = context
    obj["_vapb_witness_package_sha256"] = package_sha
    obj["_vapb_renderer_occurrences"] = __import__("json").dumps({"records": [projection]})
    return plan_witness_material_dependencies([(projection, obj)], package_sha)[0]


def capture_through_material_builder(scene, obj, slot_name="ExternalSlot"):
    if len(obj.data.materials):
        slot_name = obj.data.materials[0].name
    with tempfile.TemporaryDirectory(prefix="vapb_external_meta_") as folder:
        fbx = Path(folder) / "Body.fbx"
        obj["unity_source_fbx"] = str(fbx)
        (Path(str(fbx) + ".meta")).write_text(
            "externalObjects:\n"
            "  - first: {type: 23, assembly: UnityEngine.CoreModule, name: " + slot_name + "}\n"
            "    second: {fileID: " + MATERIAL_FILE_ID + ", guid: " + MATERIAL_GUID + ", type: 2}\n",
            encoding="utf-8",
        )
        database = AssetDatabase(Path(folder), source_package_id=PACKAGE)
        apply_materials_by_name([obj], [], asset_db=database, scene=scene)
    return load_dependency_registry(scene)["dependencies"][-1]


def assert_composition_member_external_binding(provider_first):
    scene = reset()
    source = consumer("CompositionSource")
    baseline = bpy.data.materials.new("CompositionBaseline")
    source.data.materials.append(baseline)
    with tempfile.TemporaryDirectory(prefix="vapb_composition_external_") as folder:
        fbx = Path(folder) / "Body.fbx"
        source["unity_source_fbx"] = str(fbx)
        (Path(str(fbx) + ".meta")).write_text(
            "externalObjects:\n"
            "  - first: {type: 23, assembly: UnityEngine.CoreModule, name: CompositionBaseline}\n"
            "    second: {fileID: " + MATERIAL_FILE_ID + ", guid: " + MATERIAL_GUID + ", type: 2}\n",
            encoding="utf-8",
        )
        database = AssetDatabase(Path(folder), source_package_id=PACKAGE)
        if provider_first:
            target = provider()
        apply_materials_by_name([source], [], asset_db=database, scene=scene)
        if not provider_first:
            assert resolve_scene_dependencies(scene)["material_binding_applied"] == 0
        member = copy_with_receipt(source)
        scene.collection.objects.link(member)
        capture_composition_member_external_dependencies([member], database, scene)
        assert member.get("_vapb_fbx_realization_id") != source.get("_vapb_fbx_realization_id")
        rows = [row for row in load_dependency_registry(scene)["dependencies"]
                if row.get("dependency_type") == "FBX_EXTERNAL_MATERIAL"]
        assert len(rows) == 2
        assert {row["consumer_native_realization_id"] for row in rows} == {
            source["_vapb_fbx_realization_id"], member["_vapb_fbx_realization_id"]}
        if not provider_first:
            target = provider()
        resolve_scene_dependencies(scene)
        assert source.material_slots[0].material == target
        assert member.material_slots[0].material == target


def assert_composition_claim_and_user_edit(provider_first, explicit_null):
    scene = reset()
    source = consumer("CompositionClaimSource")
    baseline = bpy.data.materials.new("CompositionClaimBaseline")
    source.data.materials.append(baseline)
    prefab_guid, prefab_file_id = "d" * 32, "2100001"
    with tempfile.TemporaryDirectory(prefix="vapb_composition_claim_") as folder:
        fbx = Path(folder) / "Body.fbx"
        source["unity_source_fbx"] = str(fbx)
        (Path(str(fbx) + ".meta")).write_text(
            "externalObjects:\n"
            "  - first: {type: 23, assembly: UnityEngine.CoreModule, name: CompositionClaimBaseline}\n"
            "    second: {fileID: " + MATERIAL_FILE_ID + ", guid: " + MATERIAL_GUID + ", type: 2}\n",
            encoding="utf-8",
        )
        database = AssetDatabase(Path(folder), source_package_id=PACKAGE)
        if provider_first:
            external_target = provider()
            prefab_target = None if explicit_null else provider(guid=prefab_guid, file_id=prefab_file_id)
        apply_materials_by_name([source], [], asset_db=database, scene=scene)
        unclaimed, claimed, edited = [copy_with_receipt(source) for _ in range(3)]
        for member in (unclaimed, claimed, edited):
            scene.collection.objects.link(member)
        capture_composition_member_external_dependencies([unclaimed, claimed, edited], database, scene)
        capture_dependency(scene, witnessed_claim(
            claimed, explicit_null=explicit_null,
            material_guid=prefab_guid, material_file_id=prefab_file_id,
        ))
        user_choice = bpy.data.materials.new("CompositionUserChoice")
        edited.material_slots[0].link = "OBJECT"
        edited.material_slots[0].material = user_choice
        if not provider_first:
            resolve_scene_dependencies(scene)
            external_target = provider()
            prefab_target = None if explicit_null else provider(guid=prefab_guid, file_id=prefab_file_id)
        resolve_scene_dependencies(scene)
        assert unclaimed.material_slots[0].material == external_target
        assert claimed.material_slots[0].material == (None if explicit_null else prefab_target)
        assert edited.material_slots[0].material == user_choice
        dependencies = load_dependency_registry(scene)["dependencies"]
        external = {row["consumer_native_realization_id"]: row for row in dependencies
                    if row.get("dependency_type") == "FBX_EXTERNAL_MATERIAL"}
        assert external[claimed["_vapb_fbx_realization_id"]]["status"] == EXTERNAL_SLOT_CLAIMED
        assert external[edited["_vapb_fbx_realization_id"]]["status"] == USER_EDIT_PRESERVED


def assert_repeated_shape_external_capture(provider_first):
    scene = reset()
    source = consumer("RepeatedShapeSource")
    source.data.from_pydata([(0, 0, 0), (1, 0, 0), (0, 1, 0)], [], [(0, 1, 2)])
    basis = source.shape_key_add(name="Basis")
    smile = source.shape_key_add(name="Smile")
    smile.data[0].co.x += 0.25
    persist_shape_receipts(source.data, FBX_SHA, 2001, [(77, 88, smile)])
    baseline = bpy.data.materials.new("RepeatedShapeBaseline")
    source.data.materials.append(baseline)
    source["_vapb_fbx_source_realization_id"] = source["_vapb_fbx_realization_id"]
    source["_vapb_root_context_id"] = "synthetic-repeated-shape-root"
    source["unity_source_fbx"] = ""

    records = []
    for renderer_file_id, weight in (("9001", 0), ("9002", 100)):
        record = {
            "root_context_id": "synthetic-repeated-shape-root",
            "root_package_id": "synthetic-prefab-package",
            "root_member_id": "synthetic-prefab-member",
            "root_asset_guid": "e" * 32,
            "instance_edge_path": [],
            "source_package_id": PACKAGE,
            "source_key": {"source_kind": "PREFAB_LOCAL", "source_asset_guid": FBX_GUID,
                           "renderer_file_id": renderer_file_id},
            "mesh": {"mesh_guid": FBX_GUID, "mesh_file_id": "-31"},
            "skin": {"status": "EXACT"},
            "blend_shape_weights": [weight],
        }
        record["occurrence_id"] = occurrence_identity(record)
        records.append(record)

    witness = SimpleNamespace(
        source_shas={FBX_GUID: FBX_SHA},
        mesh=lambda _guid, _mesh_id: SimpleNamespace(
            shape_channels=((0, 77, 88),), model_uid=1001, geometry_uid=2001, asset_guid=FBX_GUID,
        ),
    )
    template = copy_with_receipt(source)
    template["_vapb_root_context_id"] = "synthetic-repeated-shape-root"
    scene.collection.objects.link(template)
    if provider_first:
        target = provider()
    with tempfile.TemporaryDirectory(prefix="vapb_repeated_shape_external_") as folder:
        fbx = Path(folder) / "Body.fbx"
        for obj in (source, template):
            obj["unity_source_fbx"] = str(fbx)
        (Path(str(fbx) + ".meta")).write_text(
            "externalObjects:\n"
            "  - first: {type: 23, assembly: UnityEngine.CoreModule, name: RepeatedShapeBaseline}\n"
            "    second: {fileID: " + MATERIAL_FILE_ID + ", guid: " + MATERIAL_GUID + ", type: 2}\n",
            encoding="utf-8",
        )
        database = AssetDatabase(Path(folder), source_package_id=PACKAGE)
        final_members = realize_repeated_shape_occurrences(
            records, [template], witness, scene.collection,
        )
        generated = final_members[1:]
        assert len(generated) == 2
        assert len({obj["_vapb_fbx_realization_id"] for obj in final_members}) == 3
        capture_composition_member_external_dependencies(final_members, database, scene)
        rows = [row for row in load_dependency_registry(scene)["dependencies"]
                if row.get("dependency_type") == "FBX_EXTERNAL_MATERIAL"]
        assert {row["consumer_native_realization_id"] for row in rows} == {
            obj["_vapb_fbx_realization_id"] for obj in final_members}
        if not provider_first:
            assert resolve_scene_dependencies(scene)["material_binding_applied"] == 0
            target = provider()
        resolve_scene_dependencies(scene)
        assert all(obj.material_slots[0].material == target for obj in final_members)


def run():
    scene = reset()

    # Late provider route: discovery and realized binding are separate counts.
    consumer_obj = consumer()
    baseline = bpy.data.materials.new("Baseline")
    consumer_obj.data.materials.append(baseline)
    late = capture_through_material_builder(scene, consumer_obj)
    first = resolve_scene_dependencies(scene)
    assert first["material_binding_applied"] == 0
    assert late["provider_status"] == "UNRESOLVED"
    target = provider()
    second = resolve_scene_dependencies(scene)
    assert second["provider_discovered"] == 1 and second["material_binding_applied"] == 1
    assert consumer_obj.material_slots[0].link == "OBJECT"
    assert consumer_obj.material_slots[0].material == target
    assert resolve_scene_dependencies(scene)["material_binding_applied"] == 1

    # Shared Mesh material tables do not let one Object overwrite another.
    shared = consumer_obj.data
    other = consumer("Sibling", shared_mesh=shared)
    other.material_slots[0].material = baseline
    assert consumer_obj.material_slots[0].material == target
    assert other.material_slots[0].material == baseline

    # Owned unbinding after provider ambiguity must preserve a cleared-state
    # receipt so the original provider can be selected and rebound later.
    reset()
    scene = bpy.context.scene
    baseline = bpy.data.materials.new("BaselineRebind")
    rebind_consumer = consumer("RebindAfterAmbiguity")
    rebind_consumer.data.materials.append(baseline)
    original_provider = provider(package="synthetic-provider-a")
    capture_dependency(scene, record_for(rebind_consumer))
    assert resolve_scene_dependencies(scene)["material_binding_applied"] == 1
    ambiguous_provider = provider(package="synthetic-provider-b")
    assert resolve_scene_dependencies(scene)["ambiguous"] == 1
    assert rebind_consumer.material_slots[0].material is None
    bpy.data.materials.remove(ambiguous_provider)
    result = resolve_scene_dependencies(scene)
    assert result["material_binding_applied"] == 1, result
    assert rebind_consumer.material_slots[0].material == original_provider

    # A real user edit made after the resolver's clear remains protected when
    # the provider ambiguity later disappears.
    reset()
    scene = bpy.context.scene
    baseline = bpy.data.materials.new("BaselineRebindEdited")
    edited_after_clear = consumer("EditAfterAmbiguity")
    edited_after_clear.data.materials.append(baseline)
    provider(package="synthetic-provider-a")
    capture_dependency(scene, record_for(edited_after_clear))
    assert resolve_scene_dependencies(scene)["material_binding_applied"] == 1
    ambiguous_provider = provider(package="synthetic-provider-b")
    assert resolve_scene_dependencies(scene)["ambiguous"] == 1
    user_choice = bpy.data.materials.new("UserChoiceAfterClear")
    edited_after_clear.material_slots[0].material = user_choice
    bpy.data.materials.remove(ambiguous_provider)
    result = resolve_scene_dependencies(scene)
    assert result["user_edit_preserved"] == 1, result
    assert edited_after_clear.material_slots[0].material == user_choice

    # A source template and its copied composition member are distinct native
    # realizations. External remaps must bind both when no exact Prefab claim
    # claims the member slot, regardless of provider arrival order.
    assert_composition_member_external_binding(provider_first=True)
    assert_composition_member_external_binding(provider_first=False)
    for provider_first in (True, False):
        for explicit_null in (True, False):
            assert_composition_claim_and_user_edit(provider_first, explicit_null)
        assert_repeated_shape_external_capture(provider_first)

    # Material import disabled: final copies remain visible but have no
    # ExternalObjects receipt and cannot bind an already-present provider.
    reset()
    scene = bpy.context.scene
    source = consumer("MaterialsDisabledSource")
    baseline = bpy.data.materials.new("MaterialsDisabledBaseline")
    source.data.materials.append(baseline)
    provider()
    with tempfile.TemporaryDirectory(prefix="vapb_composition_disabled_") as folder:
        fbx = Path(folder) / "Body.fbx"
        source["unity_source_fbx"] = str(fbx)
        (Path(str(fbx) + ".meta")).write_text(
            "externalObjects:\n"
            "  - first: {type: 23, assembly: UnityEngine.CoreModule, name: MaterialsDisabledBaseline}\n"
            "    second: {fileID: " + MATERIAL_FILE_ID + ", guid: " + MATERIAL_GUID + ", type: 2}\n",
            encoding="utf-8",
        )
        database = AssetDatabase(Path(folder), source_package_id=PACKAGE)
        member = copy_with_receipt(source)
        scene.collection.objects.link(member)
        capture_composition_member_external_dependencies([member], database, scene, enabled=False)
        assert not load_dependency_registry(scene)["dependencies"]
        assert resolve_scene_dependencies(scene)["material_binding_applied"] == 0
        assert member.material_slots[0].material == baseline

    # Provider-first route uses the same receipt-backed resolver.
    reset()
    scene = bpy.context.scene
    baseline = bpy.data.materials.new("BaselineProviderFirst")
    ready = consumer("ProviderFirst")
    ready.data.materials.append(baseline)
    provider()
    capture_through_material_builder(scene, ready)
    result = resolve_scene_dependencies(scene)
    assert result["provider_discovered"] == 1 and result["material_binding_applied"] == 1

    # A Material with the right GUID but wrong local fileID is never selected.
    reset()
    scene = bpy.context.scene
    baseline = bpy.data.materials.new("BaselineWrongFileID")
    wrong = consumer("WrongFileID")
    wrong.data.materials.append(baseline)
    provider(file_id="2100001")
    capture_dependency(scene, record_for(wrong))
    result = resolve_scene_dependencies(scene)
    assert result["material_binding_applied"] == 0
    assert result["missing_material_file_id"] == 1
    assert wrong.material_slots[0].material == baseline
    correct = provider()
    result = resolve_scene_dependencies(scene)
    assert result["material_binding_applied"] == 1
    assert wrong.material_slots[0].material == correct
    dependency = load_dependency_registry(scene)["dependencies"][0]
    assert dependency["status"] != MISSING_MATERIAL_FILE_ID
    assert dependency["provider_status"] != MISSING_MATERIAL_FILE_ID

    # Wrong GUID and duplicate cross-package providers never mutate the slot.
    reset()
    scene = bpy.context.scene
    baseline = bpy.data.materials.new("BaselineWrongGuid")
    wrong_guid = consumer("WrongGuid")
    wrong_guid.data.materials.append(baseline)
    provider(guid="f" * 32)
    capture_dependency(scene, record_for(wrong_guid))
    result = resolve_scene_dependencies(scene)
    assert result["material_binding_applied"] == 0
    assert wrong_guid.material_slots[0].material == baseline

    reset()
    scene = bpy.context.scene
    baseline = bpy.data.materials.new("BaselineAmbiguous")
    ambiguous = consumer("AmbiguousProvider")
    ambiguous.data.materials.append(baseline)
    provider(package="synthetic-provider-a")
    provider(package="synthetic-provider-b")
    capture_dependency(scene, record_for(ambiguous))
    result = resolve_scene_dependencies(scene)
    assert result["ambiguous"] == 1 and result["material_binding_applied"] == 0
    assert ambiguous.material_slots[0].material == baseline

    # Package-local providers keep the existing local-priority behavior.
    reset()
    scene = bpy.context.scene
    baseline = bpy.data.materials.new("BaselineLocal")
    local = consumer("LocalProvider")
    local.data.materials.append(baseline)
    local_provider = provider(package=PACKAGE)
    capture_dependency(scene, record_for(local))
    result = resolve_scene_dependencies(scene)
    assert result["resolved_local"] == 1 and result["material_binding_applied"] == 1
    assert local.material_slots[0].material == local_provider

    # Exact witnessed Prefab Material and null claims suppress the FBX route
    # regardless of registry record order.
    for explicit_null in (False, True):
        for prefab_first in (False, True):
            reset()
            scene = bpy.context.scene
            baseline = bpy.data.materials.new("BaselineClaim")
            claimed = consumer("ClaimedSlot")
            claimed.data.materials.append(baseline)
            ext_record = record_for(claimed, row="external-row-claim")
            claim = witnessed_claim(claimed, explicit_null=explicit_null)
            ordered = [("prefab", claim), ("fbx", ext_record)] if prefab_first else [("fbx", ext_record), ("prefab", claim)]
            for _kind, row in ordered:
                capture_dependency(scene, row)
            result = resolve_scene_dependencies(scene)
            assert result["external_slot_claimed"] == 1
            dependencies = load_dependency_registry(scene)["dependencies"]
            suppressed = next(row for row in dependencies if row.get("dependency_type") == "FBX_EXTERNAL_MATERIAL")
            assert suppressed["status"] == EXTERNAL_SLOT_CLAIMED
            assert suppressed["suppressed_by_claim_ids"]
            if explicit_null:
                assert claimed.material_slots[0].material is None
            else:
                assert claimed.material_slots[0].material == baseline

    # Duplicate realization IDs and receipt-free legacy records fail closed.
    reset()
    scene = bpy.context.scene
    baseline = bpy.data.materials.new("BaselineDuplicate")
    duplicate = consumer("DuplicateA")
    duplicate.data.materials.append(baseline)
    twin = consumer("DuplicateB", realization=duplicate["_vapb_fbx_realization_id"])
    twin.data.materials.append(baseline)
    provider()
    capture_dependency(scene, record_for(duplicate))
    result = resolve_scene_dependencies(scene)
    assert result["invalid_fbx_consumer"] == 1
    legacy = dict(record_for(duplicate))
    legacy.pop("consumer_receipt_valid")
    legacy.pop("consumer_receipt_version")
    legacy["source_row_identity"] = "legacy-row"
    legacy.pop("consumer_native_realization_id")
    assert capture_dependency(scene, legacy)["status"] != "RESOLVED_LOCAL"
    result = resolve_scene_dependencies(scene)
    assert result["invalid_fbx_consumer"] == 2

    # User-edited state is protected, including after an earlier provider bind.
    reset()
    scene = bpy.context.scene
    baseline = bpy.data.materials.new("BaselineEdited")
    edited = consumer("Edited")
    edited.data.materials.append(baseline)
    provider()
    capture_dependency(scene, record_for(edited))
    assert resolve_scene_dependencies(scene)["material_binding_applied"] == 1
    user_material = bpy.data.materials.new("UserChoice")
    edited.material_slots[0].material = user_material
    result = resolve_scene_dependencies(scene)
    assert result["user_edit_preserved"] == 1
    assert edited.material_slots[0].material == user_material

    # Metadata-only records explicitly have no slot and cannot bind slot zero.
    reset()
    scene = bpy.context.scene
    empty = consumer("NoSlots")
    capture_through_material_builder(scene, empty)
    result = resolve_scene_dependencies(scene)
    assert result["material_binding_applied"] == 0
    assert load_dependency_registry(scene)["dependencies"][0]["status"] == "METADATA_ONLY"

    # Save/reopen preserves the Object-level assignment and persistent receipt.
    reset()
    scene = bpy.context.scene
    baseline = bpy.data.materials.new("BaselineSaved")
    saved = consumer("SaveReopen")
    saved.data.materials.append(baseline)
    target = provider()
    capture_dependency(scene, record_for(saved))
    assert resolve_scene_dependencies(scene)["material_binding_applied"] == 1
    before_save = load_dependency_registry(scene)["dependencies"][0]
    preserved_fields = (
        "consumer_native_realization_id", "source_row_identity",
        "consumer_slot_index", "initial_slot_state", "applied_slot_state",
        "target_guid", "target_file_id",
    )
    expected_persisted = {key: before_save[key] for key in preserved_fields}
    with tempfile.TemporaryDirectory(prefix="vapb_fbx_external_receipt_") as folder:
        path = str(Path(folder) / "receipt.blend")
        bpy.ops.wm.save_as_mainfile(filepath=path)
        bpy.ops.wm.open_mainfile(filepath=path)
        reopened = bpy.data.objects["SaveReopen"]
        from unitypackage_blender_importer.blender.fbx_receipt import validate_persistent_receipt
        assert validate_persistent_receipt(reopened)

        reopened_scene = bpy.context.scene
        for _ in range(2):
            result = resolve_scene_dependencies(reopened_scene)
            assert result["material_binding_applied"] == 1
            registry = load_dependency_registry(reopened_scene)
            assert len(registry["dependencies"]) == 1
            reopened_record = registry["dependencies"][0]
            assert {key: reopened_record[key] for key in preserved_fields} == expected_persisted
            assert reopened_record["status"] == "RESOLVED_CROSS_PACKAGE"
            assert reopened_record["provider_status"] == "RESOLVED_CROSS_PACKAGE"
            assert reopened_record["binding_status"] == "BOUND"

            exact_providers = [material for material in bpy.data.materials
                               if material.get("unity_material_guid", "").lower() == MATERIAL_GUID
                               and material.get("unity_material_file_id") == MATERIAL_FILE_ID
                               and material.get("unity_source_package_id") == "synthetic-material-package"]
            assert len(exact_providers) == 1
            assert reopened.material_slots[0].link == "OBJECT"
            assert reopened.material_slots[0].material is exact_providers[0]
            assert reopened_record["resolved_provider_guid"] == MATERIAL_GUID
            assert reopened_record["resolved_provider_package_id"] == "synthetic-material-package"
            assert reopened_record["resolved_provider_asset_path"] == "Assets/External.mat"
            assert validate_persistent_receipt(reopened)


if __name__ == "__main__":
    run()
    print("PASS: synthetic FBX external Material receipt integration")

