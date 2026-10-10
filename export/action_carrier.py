"""Dedicated single-Action FBX transport; ordinary Skin remains rest-pose only."""
from pathlib import Path
import math
import bpy


def action_plan(rig, bone_mappings):
    if rig.library or rig.data.library or rig.override_library:
        raise ValueError('ACTION_CARRIER_CONTEXT_UNSUPPORTED')
    data = rig.animation_data
    if data is None:
        return None
    action = data.action
    if (action is None or action.library or action.override_library or data.drivers or data.nla_tracks
            or data.use_tweak_mode or data.action_blend_type != 'REPLACE' or data.action_influence != 1
            or not action.is_action_layered or len(action.slots) != 1 or len(action.layers) != 1
            or len(action.layers[0].strips) != 1 or data.action_slot is None):
        raise ValueError('ACTION_CARRIER_CONTEXT_UNSUPPORTED')
    if rig.constraints or rig.data.animation_data or any(p.constraints for p in rig.pose.bones):
        raise ValueError('ACTION_CARRIER_CONTEXT_UNSUPPORTED')
    allowed = {row['edited_bone_realization_id'] for row in bone_mappings}
    if len(allowed) != len(bone_mappings):
        raise ValueError('ACTION_CARRIER_BONE_IDENTITY_INVALID')
    paths, identities = {}, {}
    for pose in rig.pose.bones:
        bone = pose.bone
        identity = pose.get('_vapb_fbx_bone_realization_id')
        if not isinstance(identity, str) or identity not in allowed or identity in identities:
            raise ValueError('ACTION_CARRIER_BONE_IDENTITY_INVALID')
        identities[identity] = pose.name
        if (bone.bbone_segments != 1 or bone.inherit_scale != 'FULL' or not bone.use_inherit_rotation
                or not bone.use_local_location or bone.use_relative_parent or bone.use_connect):
            raise ValueError('ACTION_CARRIER_BONE_INHERITANCE_UNSUPPORTED')
        rotation = ('rotation_quaternion' if pose.rotation_mode == 'QUATERNION' else
                    'rotation_axis_angle' if pose.rotation_mode == 'AXIS_ANGLE' else 'rotation_euler')
        for prop, size in (('location',3),('scale',3),(rotation,3 if rotation=='rotation_euler' else 4)):
            paths[pose.path_from_id()+'.'+prop] = (identity,prop,size)
    if set(identities) != allowed:
        raise ValueError('ACTION_CARRIER_BONE_IDENTITY_INVALID')
    strip = action.layers[0].strips[0]
    bag = strip.channelbag(data.action_slot) if strip.type == 'KEYFRAME' else None
    if bag is None or not bag.fcurves:
        raise ValueError('ACTION_CARRIER_CHANNELS_MISSING')
    addresses, animated, frames = set(), set(), []
    for curve in bag.fcurves:
        row = paths.get(curve.data_path)
        if row is None or not 0 <= curve.array_index < row[2] or curve.modifiers or curve.mute:
            raise ValueError('ACTION_CARRIER_CHANNEL_UNSUPPORTED')
        address = (row[0],row[1],curve.array_index)
        if address in addresses or not curve.keyframe_points:
            raise ValueError('ACTION_CARRIER_CHANNEL_UNSUPPORTED')
        addresses.add(address); animated.add(row[0])
        for key in curve.keyframe_points:
            if not all(math.isfinite(v) for v in (*key.co,*key.handle_left,*key.handle_right)):
                raise ValueError('ACTION_CARRIER_CHANNEL_UNSUPPORTED')
            frames.append(float(key.co.x))
    start,end = min(frames),max(frames)
    if start != int(start) or end != int(end) or end <= start or end-start > 10000:
        raise ValueError('ACTION_CARRIER_FRAME_RANGE_UNSUPPORTED')
    return dict(action=action,slot=data.action_slot.identifier,identities=identities,paths=paths,
                animated_bone_realization_ids=sorted(animated),frames=[start,(start+end)/2,end])


def _inspect_curve_targets(output, expected):
    from io_scene_fbx import parse_fbx
    root,_ = parse_fbx.parse(str(output),use_namedtuple=True)
    objects = next(n for n in root.elems if n.id == b'Objects')
    connections = next(n for n in root.elems if n.id == b'Connections')
    models = {int(n.props[0]):n.props[1].split(b'\x00')[0].decode() for n in objects.elems if n.id==b'Model'}
    curve_nodes = {int(n.props[0]) for n in objects.elems if n.id==b'AnimationCurveNode'}
    stacks = [n for n in objects.elems if n.id==b'AnimationStack']
    curve_count = sum(n.id==b'AnimationCurve' for n in objects.elems)
    target_by_node = {int(n.props[1]):models[int(n.props[2])] for n in connections.elems
                     if n.id==b'C' and int(n.props[1]) in curve_nodes and int(n.props[2]) in models}
    targets = set(target_by_node.values())
    omitted = {uid for uid,name in target_by_node.items() if name not in expected}
    curves = {int(n.props[0]):n for n in objects.elems if n.id==b'AnimationCurve'}
    for curve in curves.values():
        values = next(n.props[0] for n in curve.elems if n.id==b'KeyValueFloat')
        if not len(values) or any(not math.isfinite(value) for value in values):
            raise ValueError('ACTION_CARRIER_BAKED_VALUES_INVALID')
    # The native baker also emits static rig/untouched-bone channels. They must
    # never become extra authored bindings: only verified constant curves may
    # be excluded by the consumer's explicit animated-Bone scope.
    for link in connections.elems:
        if link.id==b'C' and int(link.props[1]) in curves and int(link.props[2]) in omitted:
            values = next(n.props[0] for n in curves[int(link.props[1])].elems if n.id==b'KeyValueFloat')
            if not len(values) or any(value != values[0] for value in values):
                raise ValueError('ACTION_CARRIER_UNEXPECTED_BAKED_MOTION')
    if len(stacks)!=1 or not curve_count or not expected <= targets:
        raise ValueError('ACTION_CARRIER_UNEXPECTED_BAKED_TARGETS')
    return curve_count


def export_action_carrier(context, rig, output, bone_mappings, *, scale_options='FBX_SCALE_NONE'):
    output = Path(output)
    if output.exists():
        raise ValueError('ACTION_CARRIER_OUTPUT_OCCUPIED')
    plan = action_plan(rig,bone_mappings)
    if plan is None:
        raise ValueError('ACTION_CARRIER_ACTION_MISSING')
    scene = bpy.data.scenes.new('VAPB Action Staging')
    scene.unit_settings.scale_length = context.scene.unit_settings.scale_length
    scene.render.fps = context.scene.render.fps
    scene.render.fps_base = context.scene.render.fps_base
    scene.frame_start,scene.frame_end = int(plan['frames'][0]),int(plan['frames'][-1])
    staged = data = copied_action = None
    try:
        staged = rig.copy(); data = rig.data.copy(); staged.data = data
        scene.collection.objects.link(staged)
        staged.parent = None; staged.matrix_world = rig.matrix_world.copy()
        staged.name = 'VAPB-ActionRoot'
        for block in (staged,data):
            for key in list(block.keys()): del block[key]
        staged['_vapb_fbx_realization_id'] = 'VAPB-ActionRoot'
        copied_action = plan['action'].copy(); copied_action.name = 'VAPB-Action'
        copied_action.use_fake_user = False
        for key in list(copied_action.keys()): del copied_action[key]
        staged.animation_data.action = copied_action
        staged.animation_data.action_slot = copied_action.slots[plan['slot']]
        bag = copied_action.layers[0].strips[0].channelbag(staged.animation_data.action_slot)
        captured = [(curve, plan['paths'][curve.data_path]) for curve in bag.fcurves]
        labels = {}
        for identity,name in plan['identities'].items():
            pose = staged.pose.bones[name]
            label = 'VAPB-BONE-'+identity
            pose.bone.name = label
            if pose.name != label: raise ValueError('ACTION_CARRIER_LABEL_COLLISION')
            labels[identity] = label
            for block in (pose,pose.bone):
                for key in list(block.keys()): del block[key]
            pose['_vapb_fbx_bone_realization_id'] = identity
        for curve, (identity,prop,_) in captured:
            curve.data_path = staged.pose.bones[labels[identity]].path_from_id()+'.'+prop
        layer = scene.view_layers[0]; layer.objects.active=staged
        with context.temp_override(scene=scene,view_layer=layer,object=staged,active_object=staged,
                                   selected_objects=[staged],selected_editable_objects=[staged]):
            staged.select_set(True)
            scene.frame_set(scene.frame_start)
            result=bpy.ops.export_scene.fbx(filepath=str(output),use_selection=True,
                object_types={'ARMATURE'},use_custom_props=True,add_leaf_bones=False,
                use_armature_deform_only=False,bake_anim=True,bake_anim_use_all_bones=False,
                bake_anim_use_nla_strips=False,bake_anim_use_all_actions=False,
                bake_anim_force_startend_keying=False,bake_anim_step=0.5,bake_anim_simplify_factor=0.0,
                bake_space_transform=False,apply_scale_options=scale_options,path_mode='STRIP',embed_textures=False)
        if result!={'FINISHED'} or not output.is_file(): raise ValueError('ACTION_CARRIER_EXPORT_FAILED')
        count=_inspect_curve_targets(output,{labels[i] for i in plan['animated_bone_realization_ids']})
        return dict(animated_bone_realization_ids=plan['animated_bone_realization_ids'],
                    frames=plan['frames'],fps=scene.render.fps/scene.render.fps_base,animation_curve_count=count)
    except BaseException:
        if output.is_file(): output.unlink()
        raise
    finally:
        if staged is not None: bpy.data.objects.remove(staged,do_unlink=True)
        if data is not None and data.users==0: bpy.data.armatures.remove(data)
        if copied_action is not None and copied_action.users==0: bpy.data.actions.remove(copied_action)
        bpy.data.scenes.remove(scene)