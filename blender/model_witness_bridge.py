"""Join package Renderer occurrences to native FBX objects by exact witness IDs.

This is a read-only plan. Material and Prefab semantics stay in the package
projection; callers must not apply a row with an issue.
"""

from __future__ import annotations

import json

from ..unity.occurrence_projection import occurrence_identity
from .fbx_receipt import RECEIPT_VERSION


def matches_witnessed_source(obj, asset_guid, source_sha, target_uids):
    """Select only an FBX Object with the witnessed Model/Geometry receipt."""
    return (getattr(obj, "type", None) == "MESH"
            and str(obj.get("_vapb_fbx_source_asset_guid", "")).lower() == asset_guid
            and str(obj.get("_vapb_fbx_source_asset_sha256", "")).lower() == source_sha
            and (str(obj.get("_vapb_fbx_model_uid", "")),
                 str(obj.get("_vapb_fbx_geometry_uid", "")))
            in {(str(model_uid), str(geometry_uid))
                for model_uid, geometry_uid in target_uids})


def _edge_path(obj):
    raw = obj.get("_vapb_model_instance_edge_path")
    if raw is None:
        return []
    try:
        value = json.loads(raw) if isinstance(raw, str) else raw
    except (TypeError, ValueError):
        return None
    return value if isinstance(value, list) else None


def plan_witness_realizations(records, objects, witness):
    """Return unique (occurrence, Mesh Object) pairs and explicit failures."""
    bindings, issues = [], []
    objects = tuple(objects)
    for record in records:
        occurrence = record.get("occurrence_id", "")

        def reject(code):
            issues.append({"occurrence_id": occurrence, "code": code})

        if witness is None:
            reject("WITNESS_MISSING")
            continue
        try:
            if occurrence != occurrence_identity(record):
                reject("OCCURRENCE_IDENTITY_MISMATCH")
                continue
            mesh = record["mesh"]
            row = witness.mesh(mesh["mesh_guid"], mesh["mesh_file_id"])
            if row is None:
                reject("WITNESS_MISSING")
                continue
            source = record["source_key"]
            if source["source_kind"] == "MODEL_SOURCE":
                owner = record["owner"]
                if (source["source_asset_guid"].lower() != row.asset_guid
                        or int(source["renderer_file_id"]) != row.renderer_local_id
                        or int(owner["owner_game_object_id"]) != row.game_object_local_id
                        or int(record["renderer_class_id"]) != row.class_id):
                    reject("SOURCE_IDENTITY_MISMATCH")
                    continue
            elif source["source_kind"] != "PREFAB_LOCAL":
                reject("SOURCE_IDENTITY_MISMATCH")
                continue
            path = list(record["instance_edge_path"])
            candidates = [obj for obj in objects
                          if getattr(obj, "type", None) == "MESH"
                          and obj.get("_vapb_root_context_id") == record["root_context_id"]
                          and obj.get("unity_source_package_id") == mesh["source_package_id"]
                          and str(obj.get("_vapb_fbx_source_asset_guid", "")).lower() == row.asset_guid
                          and str(obj.get("_vapb_fbx_source_asset_sha256", "")).lower() == mesh["source_sha256"].lower()
                          and str(obj.get("_vapb_fbx_model_uid", "")) == str(row.model_uid)
                          and str(obj.get("_vapb_fbx_geometry_uid", "")) == str(row.geometry_uid)
                          and _edge_path(obj) == path
                          and obj.get("_vapb_fbx_realization_id")]
            if not candidates:
                reject("NATIVE_MISSING")
            elif len(candidates) != 1:
                reject("NATIVE_AMBIGUOUS")
            else:
                bindings.append((record, candidates[0]))
        except (KeyError, TypeError, ValueError, AttributeError):
            reject("INCOMPLETE_IDENTITY")
    claims = {}
    for record, obj in bindings:
        claims[id(obj)] = claims.get(id(obj), 0) + 1
    unique = []
    for record, obj in bindings:
        if claims[id(obj)] == 1:
            unique.append((record, obj))
        else:
            issues.append({"occurrence_id": record["occurrence_id"],
                           "code": "NATIVE_AMBIGUOUS"})
    return unique, issues


def plan_witness_skin_carriers(bindings, witness, prefab, semantic_objects):
    """Bounded direct Skin slot-to-Bone plan; source membership is witness-validated.

    Slots are Mesh bindpose channel identities, never native collection order.
    Unsupported overrides/rest frames are rejected before any Scene mutation.
    """
    from .fbx_receipt import make_bone_receipt
    plans, issues, claims = [], [], {}
    for record, mesh in bindings:
        if record.get('renderer_class_id') != 137:
            continue
        try:
            row = witness.mesh(record['mesh']['mesh_guid'], record['mesh']['mesh_file_id'])
            if not row.bone_model_uids:
                continue  # v1 continues its existing Mesh-only behavior.
            skin = record['skin']
            if record['instance_edge_path'] or skin['status'] != 'EXACT':
                raise ValueError('SKIN_OCCURRENCE_UNSUPPORTED')
            slots = skin['bones']
            if len(slots) != len(row.bone_model_uids):
                raise ValueError('SKIN_SLOT_MISMATCH')
            slot_uids = {str(slot['transform_file_id']): uid for slot, uid in zip(slots, row.bone_model_uids)}
            root_transform = prefab.transforms.get(int(skin['root_bone_transform_file_id']))
            root_frame = semantic_objects.get(root_transform.game_object_id) if root_transform else None
            if (root_frame is None or root_frame.type != 'EMPTY'
                    or root_frame.get('_vapb_root_context_id') != record['root_context_id']):
                raise ValueError('SKIN_ROOT_MISMATCH')
            modifiers = [m for m in mesh.modifiers if m.type == 'ARMATURE']
            if len(modifiers) != 1 or modifiers[0].object is None:
                raise ValueError('SKIN_ARMATURE_AMBIGUOUS')
            rig = modifiers[0].object
            if rig.type != 'ARMATURE' or rig.get('_vapb_root_context_id') != record['root_context_id']:
                raise ValueError('SKIN_ARMATURE_SCOPE_MISMATCH')
            pending = []
            for slot_index, (slot, uid) in enumerate(zip(slots, row.bone_model_uids)):
                bones = [b for b in rig.data.bones if str(b.get('_vapb_fbx_model_uid')) == str(uid)]
                if len(bones) != 1:
                    raise ValueError('SKIN_BONE_AMBIGUOUS')
                bone = bones[0]
                receipt = make_bone_receipt(uid, row.asset_guid, record['mesh']['source_sha256'])
                if (bone.get('_vapb_fbx_bone_receipt_id') != receipt.blender_bone_receipt_id
                        or bone.get('_vapb_fbx_receipt_version') != RECEIPT_VERSION
                        or bone.get('_vapb_fbx_receipt_evidence') != receipt.evidence
                        or not bone.get('_vapb_fbx_bone_realization_id')):
                    raise ValueError('SKIN_BONE_RECEIPT_MISMATCH')
                parent_uid = slot_uids.get(str(slot['parent_transform_file_id']))
                actual_parent_uid = int(bone.parent.get('_vapb_fbx_model_uid', 0)) if bone.parent else None
                if parent_uid != actual_parent_uid:
                    raise ValueError('SKIN_BONE_PARENT_MISMATCH')
                transform = prefab.transforms.get(int(slot['transform_file_id']))
                carrier = semantic_objects.get(transform.game_object_id) if transform else None
                if (carrier is None or carrier.type != 'EMPTY'
                        or carrier.get('_vapb_root_context_id') != record['root_context_id']
                        or carrier.constraints):
                    raise ValueError('SKIN_SEMANTIC_CARRIER_UNSUPPORTED')
                pose_world = None
                if row.source_bone_world_matrices:
                    from mathutils import Matrix
                    from .hierarchy_builder import _UNITY_TO_BLENDER
                    values = row.source_bone_world_matrices[slot_index]
                    basis = _UNITY_TO_BLENDER.to_4x4()
                    source_world = basis @ Matrix([[values[j*4+i] for j in range(4)] for i in range(4)]) @ basis.inverted()
                    native_rest = rig.matrix_world @ bone.matrix_local
                    # Identity is established above; position only corroborates
                    # the source/native rest-frame basis bridge, never selects it.
                    if (source_world.translation - native_rest.translation).length > 1e-5:
                        raise ValueError('SKIN_SOURCE_FRAME_MISMATCH')
                    pose_world = carrier.matrix_world @ source_world.inverted() @ native_rest
                elif (carrier.matrix_world.translation - rig.matrix_world @ bone.head_local).length > 1e-5:
                    raise ValueError('SKIN_REST_FRAME_UNSUPPORTED')
                prior = claims.get(carrier)
                target = (rig, uid)
                if prior is not None and prior != target:
                    raise ValueError('SKIN_CARRIER_AMBIGUOUS')
                pending.append((carrier, rig, bone, pose_world))
            for carrier, rig, bone, pose_world in pending:
                claims[carrier] = (rig, int(bone['_vapb_fbx_model_uid']))
            plans.extend(pending)
        except (KeyError, TypeError, ValueError, AttributeError) as exc:
            issues.append({'occurrence_id': record['occurrence_id'], 'code': str(exc)})
    return list({plan[0]: plan for plan in plans}.values()), issues


def realize_witness_skin_carriers(plans, collection, bindings=(), semantic_objects=None, prefab=None):
    """Keep semantic parent edges while driving carriers by native Bone delta.

    A technical proxy isolates Bone rest-axis differences and avoids applying
    ancestor pose motion twice. Constraints use native API handles only after
    UID receipts established the targets. No USER_CONFIRMED binding is invented.
    """
    import bpy
    from .renderer_binding import semantic_owner_id
    # Apply only UID-selected pose channels; preserve native rest/bindpose data.
    framed = [(rig, bone, world) for _, rig, bone, world in plans if world is not None]
    desired = {(rig, str(bone['_vapb_fbx_model_uid'])): world for rig, bone, world in framed}
    disconnect = {}
    from mathutils import Vector
    for rig, bone, world in framed:
        if not bone.use_connect or bone.parent is None:
            continue
        parent_world = desired.get((rig, str(bone.parent.get('_vapb_fbx_model_uid'))))
        if parent_world is None:
            parent_world = rig.matrix_world @ rig.pose.bones[bone.parent.name].matrix
        if (world.translation - parent_world @ Vector((0, bone.parent.length, 0))).length > 1e-5:
            disconnect.setdefault(rig, set()).add(str(bone['_vapb_fbx_model_uid']))
    original_data = {}
    active, selected = bpy.context.view_layer.objects.active, tuple(bpy.context.selected_objects)
    try:
        for rig, uids in disconnect.items():
            original_data[rig] = rig.data
            rig.data = rig.data.copy()  # A member pose must not alter shared/source connection flags.
            bpy.context.view_layer.objects.active = rig
            rig.select_set(True)
            bpy.ops.object.mode_set(mode='EDIT')
            for bone in rig.data.edit_bones:
                if str(bone.get('_vapb_fbx_model_uid')) in uids:
                    bone.use_connect = False
            bpy.ops.object.mode_set(mode='OBJECT')
    finally:
        if bpy.context.object and bpy.context.object.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        for obj in bpy.context.selected_objects:
            obj.select_set(False)
        for obj in selected:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = active
    poses = [(rig, rig.pose.bones[bone.name], world) for rig, bone, world in framed]
    saved = [(rig, pose.name, pose.matrix_basis.copy()) for rig, pose, _ in poses]
    def depth(pose):
        value, parent = 0, pose.parent
        while parent is not None:
            value, parent = value+1, parent.parent
        return value
    try:
        for rig, pose, world in sorted(poses, key=lambda item: depth(item[1])):
            pose.matrix = rig.matrix_world.inverted() @ world
            bpy.context.view_layer.update()
        for rig, pose, world in poses:
            observed = rig.matrix_world @ pose.matrix
            tolerance = 2e-5 + 1e-6 * max(abs(v) for matrix in (observed, world) for row in matrix for v in row)
            if max(abs(observed[i][j]-world[i][j]) for i in range(4) for j in range(4)) > tolerance:
                raise ValueError('SKIN_POSE_FRAME_UNSUPPORTED')
    except (ValueError, RuntimeError):
        for rig, data in original_data.items():
            rig.data = data
        for rig, channel, original in saved:
            rig.pose.bones[channel].matrix_basis = original
        bpy.context.view_layer.update()
        return False  # No owner/constraint receipts are emitted for failed poses.
    rigs = {rig for _, rig, _, _ in plans}
    for carrier, rig, bone, pose_world in plans:
        if bone.parent is None and carrier.parent is not None:
            world = rig.matrix_world.copy()
            rig.parent = carrier.parent
            rig.matrix_world = world
    for record, mesh in bindings:
        modifiers = [m for m in mesh.modifiers if m.type == 'ARMATURE']
        if len(modifiers) != 1 or modifiers[0].object not in rigs:
            continue
        if modifiers[0].object in original_data and mesh.data.users > 1:
            # Blender propagates vertex-group renames across linked Mesh users.
            # An independent Armature therefore needs independent deform data.
            mesh.data = mesh.data.copy()
            mesh.data['_vapb_fbx_mesh_session_uid'] = str(mesh.data.session_uid)
            mesh.data['_vapb_fbx_mesh_copy_evidence'] = 'OBSERVED_MEMBER_DEFORM_COPY'
        owner = (semantic_objects or {}).get(record['owner']['owner_game_object_id'])
        if owner is None or owner.get('_vapb_semantic_owner_id') != semantic_owner_id(record):
            continue
        world = mesh.matrix_world.copy()
        mesh.parent = owner
        mesh.matrix_world = world
        mesh['_vapb_renderer_occurrence_id'] = record['occurrence_id']
        root_id = record['skin']['root_bone_transform_file_id']
        root_transform = prefab.transforms[int(root_id)]
        root_frame = semantic_objects[root_transform.game_object_id]
        mesh['_vapb_skin_root_transform_file_id'] = root_id
        mesh['_vapb_skin_root_frame_semantic_id'] = root_frame['_vapb_semantic_id']
    bpy.context.view_layer.update()
    for carrier, rig, bone, pose_world in plans:
        world = carrier.matrix_world.copy()
        target_world = rig.matrix_world @ rig.pose.bones[bone.name].matrix
        proxy = bpy.data.objects.new('VAPB Bone frame', None)
        collection.objects.link(proxy)
        proxy.matrix_world = world
        proxy['_vapb_technical_bone_proxy'] = True
        proxy['_vapb_root_context_id'] = carrier['_vapb_root_context_id']
        proxy['_vapb_skin_bone_receipt_id'] = bone['_vapb_fbx_bone_receipt_id']
        proxy['_vapb_skin_bone_model_uid'] = bone['_vapb_fbx_model_uid']
        proxy.hide_render = True
        proxy.hide_set(True)
        delta = proxy.constraints.new('CHILD_OF')
        delta.target, delta.subtarget = rig, bone.name
        delta.inverse_matrix = target_world.inverted()
        driver = carrier.constraints.new('COPY_TRANSFORMS')
        driver.target = proxy
        driver.owner_space = driver.target_space = 'WORLD'
        carrier['_vapb_skin_bone_receipt_id'] = bone['_vapb_fbx_bone_receipt_id']
        carrier['_vapb_skin_bone_model_uid'] = bone['_vapb_fbx_model_uid']
    return True


def plan_witness_material_dependencies(bindings, package_sha256):
    """Use only serialized Material references from proven occurrence rows."""
    dependencies = []
    for record, obj in bindings:
        if record.get("material_status") not in {"EXACT", "PARTIAL"}:
            continue
        for slot, reference in record.get("materials", {}).items():
            if not isinstance(slot, int) or slot < 0:
                continue
            explicit_null = (reference is None and record.get("material_status") == "EXACT"
                             and isinstance(record.get("material_slot_count"), int)
                             and slot < record["material_slot_count"])
            if not explicit_null and (not isinstance(reference, dict)
                                      or not reference.get("guid") or not reference.get("file_id")):
                continue
            dependency = {
                "dependency_type": "CLEAR_MATERIAL_SLOT" if explicit_null else "PREFAB_RENDERER_MATERIAL",
                "consumer_package_id": record["mesh"]["source_package_id"],
                "consumer_root_context_id": record["root_context_id"],
                "consumer_occurrence_id": record["occurrence_id"],
                "consumer_native_realization_id": str(obj["_vapb_fbx_realization_id"]),
                "consumer_source_package_sha256": package_sha256,
                "consumer_fbx_guid": record["mesh"]["mesh_guid"],
                "consumer_fbx_sha256": record["mesh"]["source_sha256"],
                "consumer_fbx_model_uid": str(obj["_vapb_fbx_model_uid"]),
                "consumer_fbx_geometry_uid": str(obj["_vapb_fbx_geometry_uid"]),
                "consumer_fbx_object_receipt_id": str(obj["_vapb_fbx_object_receipt_id"]),
                "consumer_fbx_mesh_receipt_id": str(obj["_vapb_fbx_mesh_receipt_id"]),
                "consumer_slot_index": slot,
                "identity_bridge": "UNITY_MODEL_WITNESS",
            }
            if not explicit_null:
                dependency["target_guid"] = str(reference["guid"]).lower()
                dependency["target_file_id"] = str(reference["file_id"])
            dependencies.append(dependency)
    return dependencies


def find_witness_consumer(record, objects):
    """Resolve a saved dependency by occurrence and unique native realization."""
    realization = record.get("consumer_native_realization_id")
    context = record.get("consumer_root_context_id")
    package = record.get("consumer_package_id")
    if not realization or not context or not package or not record.get("consumer_occurrence_id"):
        return None
    objects = tuple(objects)
    roots = [obj for obj in objects
             if obj.get("_vapb_root_context_id") == context
             and obj.get("_vapb_renderer_occurrences") is not None
             and obj.get("_vapb_witness_package_sha256") == record.get("consumer_source_package_sha256")]
    if len(roots) != 1:
        return None
    try:
        raw = roots[0]["_vapb_renderer_occurrences"]
        projection = json.loads(raw) if isinstance(raw, str) else raw
        matching = [item for item in projection["records"]
                    if item.get("occurrence_id") == record["consumer_occurrence_id"]]
        if len(matching) != 1 or matching[0]["occurrence_id"] != occurrence_identity(matching[0]):
            return None
        projected_mesh = matching[0]["mesh"]
        if (projected_mesh["mesh_guid"] != record["consumer_fbx_guid"]
                or projected_mesh["source_sha256"] != record["consumer_fbx_sha256"]):
            return None
        materials = matching[0]["materials"]
        slot = record["consumer_slot_index"]
        if str(slot) in materials:
            reference = materials[str(slot)]
        elif slot in materials:
            reference = materials[slot]
        else:
            return None
        if record.get("dependency_type") == "CLEAR_MATERIAL_SLOT":
            if (reference is not None or matching[0].get("material_status") != "EXACT"
                    or not isinstance(matching[0].get("material_slot_count"), int)
                    or not isinstance(slot, int) or slot < 0
                    or slot >= matching[0]["material_slot_count"]):
                return None
        elif (not isinstance(reference, dict)
              or str(reference.get("guid", "")).lower() != str(record.get("target_guid", "")).lower()
              or str(reference.get("file_id", "")) != str(record.get("target_file_id", ""))):
            return None
    except (KeyError, TypeError, ValueError, AttributeError):
        return None
    matches = [obj for obj in objects
               if getattr(obj, "type", None) == "MESH"
               and obj.get("_vapb_fbx_realization_id") == realization
               and obj.get("_vapb_root_context_id") == context
               and obj.get("unity_source_package_id") == package
               and obj.get("_vapb_fbx_receipt_version") == RECEIPT_VERSION
               and obj.get("_vapb_fbx_source_asset_guid") == record.get("consumer_fbx_guid")
               and obj.get("_vapb_fbx_source_asset_sha256") == record.get("consumer_fbx_sha256")
               and obj.get("_vapb_fbx_model_uid") == record.get("consumer_fbx_model_uid")
               and obj.get("_vapb_fbx_geometry_uid") == record.get("consumer_fbx_geometry_uid")
               and obj.get("_vapb_fbx_object_receipt_id") == record.get("consumer_fbx_object_receipt_id")
               and obj.get("_vapb_fbx_mesh_receipt_id") == record.get("consumer_fbx_mesh_receipt_id")
               and getattr(obj, "data", None) is not None
               and obj.data.get("_vapb_fbx_receipt_version") == RECEIPT_VERSION
               and obj.data.get("_vapb_fbx_source_asset_sha256") == record.get("consumer_fbx_sha256")
               and obj.data.get("_vapb_fbx_geometry_uid") == record.get("consumer_fbx_geometry_uid")
               and obj.data.get("_vapb_fbx_mesh_receipt_id") == record.get("consumer_fbx_mesh_receipt_id")]
    return matches[0] if len(matches) == 1 else None


def reserve_witness_slots(dependencies, objects):
    """Stabilize shared Mesh slot capacity before any slot snapshots are saved."""
    ready, rejected = [], []
    objects = tuple(objects)
    for dependency in dependencies:
        obj = find_witness_consumer(dependency, objects)
        slot = dependency.get("consumer_slot_index")
        if (obj is None or not isinstance(slot, int) or slot < 0
                or getattr(obj, "data", None) is None
                or not hasattr(obj.data, "materials")):
            rejected.append({"occurrence_id": dependency.get("consumer_occurrence_id", ""),
                             "code": "WITNESS_CONSUMER_MISSING"})
            continue
        while len(obj.data.materials) <= slot:
            obj.data.materials.append(None)
        ready.append(dependency)
    return ready, rejected
