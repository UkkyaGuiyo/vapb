import sys,json,hashlib
from pathlib import Path
import bpy
from mathutils import Matrix
args=sys.argv[sys.argv.index('--')+1:]
blend=Path(args[args.index('--blend')+1]);out=Path(args[args.index('--out')+1])
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
hash_before=sha(blend);bpy.ops.wm.open_mainfile(filepath=str(blend))
obj, = [o for o in bpy.context.scene.objects if o.type=='MESH']
rig=next(m.object for m in obj.modifiers if m.type=='ARMATURE')
child, = [b for b in rig.data.bones if str(b.get('_vapb_fbx_model_uid'))=='529385132']
pose=rig.pose.bones[child.name];basis=pose.matrix_basis.copy()
def points():
 deps=bpy.context.evaluated_depsgraph_get();e=obj.evaluated_get(deps);mesh=e.to_mesh()
 try:return [list(e.matrix_world@v.co) for v in mesh.vertices]
 finally:e.to_mesh_clear()
bpy.context.view_layer.update();before=points();world_before=rig.matrix_world@pose.matrix
pose.matrix_basis=basis@Matrix.Rotation(0.45,4,'Z');bpy.context.view_layer.update();after=points();world_after=rig.matrix_world@pose.matrix
delta=world_after@world_before.inverted()
max_displacement=max(sum((x-y)**2 for x,y in zip(a,b))**.5 for a,b in zip(before,after));assert max_displacement>0.01
assert sha(blend)==hash_before
out.write_text(json.dumps(dict(status='OBSERVED',selected_bone_uid='529385132',parent_uid=str(child.parent.get('_vapb_fbx_model_uid')),rotation_radians=0.45,rotation_axis_in_Blender_pose_basis='Z',rest_points=before,posed_points=after,world_before=[list(row) for row in world_before],world_after=[list(row) for row in world_after],world_delta=[list(row) for row in delta],blender_nonzero_max_displacement_m=max_displacement,blend_sha256=hash_before,blend_bytes_preserved=True,shape_values=[k.value for k in obj.data.shape_keys.key_blocks[1:]],temporary_memory_pose_only=True),indent=2),encoding='utf-8')
