"""One owned Bone Merge Action through the dedicated FBX carrier."""
from pathlib import Path
import importlib.util
import sys
import tempfile
from types import SimpleNamespace
import bpy
root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / 'tests'))
from strict_source_import import load_source_package
load_source_package(root)
spec = importlib.util.spec_from_file_location('owned_merge_fixture', root / 'tests/blender_bone_merge_test.py')
fixture = importlib.util.module_from_spec(spec); spec.loader.exec_module(fixture)
from unitypackage_blender_importer.blender.bone_merge import prepare_merge, apply_merge
from unitypackage_blender_importer.export.action_carrier import export_action_carrier
fixture.reset()
a = fixture.rig('Carrier target', (0,0,0), (0,0,0))
b = fixture.rig('Carrier source', (0,0,0), (0,0,0))
mesh, mod = fixture.mesh('Carrier Skin', b)
pose = b.pose.bones['Root']
for frame, value in ((1,0.0),(5,0.25),(10,0.5)):
    pose.location.x = value
    pose.keyframe_insert(data_path='location', index=0, frame=frame)
bpy.context.scene.frame_set(1)
original = b.animation_data.action
original_name = original.name
rows = [SimpleNamespace(source_name='Root', target_name='Root', classification='EQUIVALENT', confirmed=True)]
assert apply_merge(prepare_merge(a,b,rows,bpy.context.scene)) == (0,1)
a.pose.bones['Root']['_vapb_fbx_bone_realization_id'] = 'owned-root'
a.animation_data.action.use_fake_user = True
with tempfile.TemporaryDirectory(prefix='vapb_owned_action_') as folder:
    output = Path(folder)/'Carrier.fbx'
    actions_before = set(bpy.data.actions)
    data = export_action_carrier(bpy.context, a, output, [{'edited_bone_realization_id':'owned-root','source_model_uid':'1'}])
    assert set(bpy.data.actions) == actions_before
    assert a.animation_data.action.use_fake_user
    assert data['animated_bone_realization_ids'] == ['owned-root']
    assert data['frames'] == [1,5.5,10]
    assert output.is_file() and data['animation_curve_count'] > 0
    expected, vertices = {}, {}
    for frame in (1,5.5,10):
        bpy.context.scene.frame_set(int(frame),subframe=frame%1)
        expected[frame] = a.matrix_world @ a.pose.bones['Root'].matrix.copy()
        vertices[frame] = fixture.evaluated_world_vertices(mesh)
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=str(output),use_custom_props=True,use_anim=True,anim_offset=0.0,
                            automatic_bone_orientation=False)
    imported = [obj for obj in bpy.data.objects if obj not in before and obj.type=='ARMATURE']
    assert len(imported)==1
    carrier = imported[0]
    marked = [pose for pose in carrier.pose.bones if pose.get('_vapb_fbx_bone_realization_id')=='owned-root']
    assert len(marked)==1
    returned_mesh = mesh.copy(); returned_mesh.data = mesh.data.copy()
    bpy.context.collection.objects.link(returned_mesh)
    returned_mesh.modifiers['Skin'].object = carrier
    returned_mesh.vertex_groups['Root'].name = marked[0].name
    for frame in (1,5.5,10):
        bpy.context.scene.frame_set(int(frame),subframe=frame%1)
        actual = carrier.matrix_world @ marked[0].matrix
        assert fixture.close_matrix(expected[frame],actual), (frame,expected[frame],actual)
        assert all((x-y).length<1e-4 for x,y in zip(vertices[frame],fixture.evaluated_world_vertices(returned_mesh)))
    saved = Path(folder)/'Carrier.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(saved))
    bpy.ops.wm.open_mainfile(filepath=str(saved))
    a = bpy.data.objects['Carrier target']; b = bpy.data.objects['Carrier source']
    assert a.animation_data.action is not None
    source_curves = tuple((c.data_path,c.array_index,tuple(tuple(k.co) for k in c.keyframe_points))
        for c in b.animation_data.action.layers[0].strips[0].channelbag(b.animation_data.action_slot).fcurves)
    try: export_action_carrier(bpy.context,a,output,[{'edited_bone_realization_id':'owned-root','source_model_uid':'1'}])
    except ValueError as error: assert 'OUTPUT_OCCUPIED' in str(error)
    else: raise AssertionError('Occupied output was overwritten')
    untouched = Path(folder)/'Rejected.fbx'
    try: export_action_carrier(bpy.context,a,untouched,[])
    except ValueError as error: assert 'IDENTITY' in str(error)
    else: raise AssertionError('Missing Bone identity accepted')
    assert not untouched.exists()
    a.location.x=1; a.keyframe_insert(data_path='location',index=0,frame=1)
    try: export_action_carrier(bpy.context,a,untouched,[{'edited_bone_realization_id':'owned-root','source_model_uid':'1'}])
    except ValueError as error: assert 'CHANNEL_UNSUPPORTED' in str(error)
    else: raise AssertionError('Object channel accepted')
    assert not untouched.exists()
    driver = a.driver_add('location',0)
    try: export_action_carrier(bpy.context,a,untouched,[{'edited_bone_realization_id':'owned-root','source_model_uid':'1'}])
    except ValueError as error: assert 'CONTEXT_UNSUPPORTED' in str(error)
    else: raise AssertionError('Driver accepted')
    a.driver_remove('location',0)
    track = a.animation_data.nla_tracks.new()
    try: export_action_carrier(bpy.context,a,untouched,[{'edited_bone_realization_id':'owned-root','source_model_uid':'1'}])
    except ValueError as error: assert 'CONTEXT_UNSUPPORTED' in str(error)
    else: raise AssertionError('NLA accepted')
    a.animation_data.nla_tracks.remove(track)
    assert not untouched.exists()
    assert source_curves == tuple((c.data_path,c.array_index,tuple(tuple(k.co) for k in c.keyframe_points))
        for c in b.animation_data.action.layers[0].strips[0].channelbag(b.animation_data.action_slot).fcurves)
assert b.animation_data.action.name == original_name
assert a.animation_data.action is not None
print('OWNED_ACTION_CARRIER_PASS native_pose_and_skin_samples=3 save_reopen=1 source_action_preserved=1 fake_user_no_leak=1 identity_channel_driver_nla_collision_refused=1 unity=NOT_RUN normal_package_consumer=UNIMPLEMENTED')