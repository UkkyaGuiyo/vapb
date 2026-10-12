"""Read saved owned scene; reuse existing evaluated_get/to_mesh world capture."""
import hashlib,json,sys
from pathlib import Path
import bpy
args=sys.argv[sys.argv.index('--')+1:]
source=Path(args[args.index('--blend')+1]);out=Path(args[args.index('--out')+1])
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
before=sha(source)
assert bpy.ops.wm.open_mainfile(filepath=str(source))=={'FINISHED'}
obj,=[o for o in bpy.context.scene.objects if o.type=='MESH']
keys=obj.data.shape_keys
assert [k.value for k in keys.key_blocks[1:]]==[1.0,0.0]
rig=next(m.object for m in obj.modifiers if m.type=='ARMATURE')
assert len(rig.data.bones)==2 and len(obj.data.vertices)==8
basis_error=max(abs(p.matrix_basis[i][j]-(1.0 if i==j else 0.0)) for p in rig.pose.bones for i in range(4) for j in range(4))
bpy.context.view_layer.update()
evaluated=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=evaluated.to_mesh()
try:
 assert len(mesh.vertices)==len(obj.data.vertices)
 row=dict(status='OBSERVED',blend_sha256=before,frame=bpy.context.scene.frame_current,
  active_values=[k.value for k in keys.key_blocks[1:]],labels=[k.name for k in keys.key_blocks[1:]],
  vertex_control_point_indices=list(range(len(mesh.vertices))),
  basis_local=[list(v.co) for v in obj.data.vertices],matrix=[list(x) for x in evaluated.matrix_world],
  baked_positions=[list(evaluated.matrix_world@v.co) for v in mesh.vertices],
  rig_matrix=[list(x) for x in rig.matrix_world],pose_basis_max_identity_error=basis_error,
  pose_matrices=[dict(matrix=[list(x) for x in p.matrix],basis=[list(x) for x in p.matrix_basis],rest=[list(x) for x in p.bone.matrix_local]) for p in rig.pose.bones])
finally:evaluated.to_mesh_clear()
assert sha(source)==before
row['blend_bytes_preserved']=True
out.write_bytes(json.dumps(row,indent=2).encode())
print('BLENDER_ACTIVE_SHAPE_EVALUATED_CAPTURE')
