# SPDX-License-Identifier: GPL-3.0-or-later
"""Actual production FBX output must contain explicit Blender triangles."""
from pathlib import Path
import sys
import bpy
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from unitypackage_blender_importer.export.fbx_export import export_fbx
from io_scene_fbx import parse_fbx


import json
from types import SimpleNamespace
from unitypackage_blender_importer.export.triangle_staging import triangle_export_scene
from unitypackage_blender_importer.tests.blender_geometry_abcd import observe

bpy.ops.wm.read_factory_settings(use_empty=True)
mesh=bpy.data.meshes.new('Nonplanar')
mesh.from_pydata([(0,0,0),(2,0,0),(2,2,.6),(0,2,0)],[],[(0,1,2,3)])
obj=bpy.data.objects.new('Final mesh',mesh)
bpy.context.scene.collection.objects.link(obj)
obj.select_set(True);bpy.context.view_layer.objects.active=obj
for name in ('UV0','UV1'):
    layer=mesh.uv_layers.new(name=name)
    for loop in mesh.loops:layer.data[loop.index].uv=(loop.vertex_index*.2,loop.index*.3)
for name in ('Material A','Material B'):
    mesh.materials.append(bpy.data.materials.new(name))
mesh.polygons[0].material_index=1
obj.material_slots[1].link='OBJECT'
obj.material_slots[1].material=bpy.data.materials.new('Object material')
obj['_vapb_export_object_id']='VAPB-OBJ-'+'1'*32
mesh['_vapb_recipe_test']='KEEP'
basis=obj.shape_key_add(name='Basis')
key=obj.shape_key_add(name='Shape')
key.data[2].co.z+=.2;key.value=.4;key.slider_min=-.5
mesh.shape_keys['fixture']='first-party'
bpy.ops.object.armature_add()
rig=bpy.context.object
rig.data.bones[0]['_vapb_export_bone_id']='BONE-TEST'
rig.data.bones[0].name='Root'
modifier=obj.modifiers.new('Skin','ARMATURE');modifier.object=rig
obj.parent=rig
obj.vertex_groups.new(name='Root').add(list(range(4)),1,'REPLACE')
obj.vertex_groups[0].lock_weight=True
shared=bpy.data.objects.new('Shared occurrence',mesh)
bpy.context.scene.collection.objects.link(shared)
for item in bpy.context.selected_objects:item.select_set(False)
obj.select_set(True);rig.select_set(True);bpy.context.view_layer.objects.active=obj
bpy.context.view_layer.update()
output=Path(sys.argv[sys.argv.index('--')+1])

def state():
    row=observe(obj,0)
    return (row, tuple((o.as_pointer(),o.data.as_pointer() if o.data else None,
                o.parent.as_pointer() if o.parent else None,tuple(tuple(r) for r in o.matrix_world),
                tuple(sorted((k,str(o[k])) for k in o.keys()))) for o in bpy.context.scene.objects),
        tuple((slot.link,slot.material.as_pointer() if slot.material else None) for slot in obj.material_slots),
        tuple((g.name,g.lock_weight) for g in obj.vertex_groups),
        tuple(o.as_pointer() for o in bpy.context.selected_objects),bpy.context.view_layer.objects.active.as_pointer(),
        tuple(len(getattr(bpy.data,name)) for name in ('objects','meshes','armatures','shape_keys','scenes')),
        rig.data.bones[0].name,rig.data.bones[0]['_vapb_export_bone_id'])

bpy.context.scene.unit_settings.system='METRIC'
before=state()
mesh.calc_loop_triangles();expected=[tuple(t.vertices) for t in mesh.loop_triangles]
# Inspection inside the production context, using actual selected Object handles.
with triangle_export_scene(bpy.context,(obj,rig)) as (staged_scene,copies):
    assert staged_scene.unit_settings.system==bpy.context.scene.unit_settings.system=='METRIC'
    staged=next(o for o in copies if o.type=='MESH')
    assert all(len(p.vertices)==3 for p in staged.data.polygons)
    assert staged['_vapb_export_object_id']==obj['_vapb_export_object_id']
    assert staged.data['_vapb_recipe_test']=='KEEP'
    assert staged.modifiers[0].object in copies and staged.parent in copies
    assert staged.data.shape_keys.key_blocks[1].value==key.value
    assert staged.vertex_groups[0].lock_weight
    assert staged.material_slots[1].link=='OBJECT'
    assert staged.material_slots[1].material==obj.material_slots[1].material
    a,b=observe(obj,0),observe(staged,0)
    for field in ('positions','triangles','triangle_material_slots','uv_channels','skin_weights'):
        assert a[field]==b[field],field
    assert [r['deltas'] for r in a['shapes']]==[r['deltas'] for r in b['shapes']]
assert state()==before,'STAGING_CHANGED_SOURCE'
export_fbx(output)
raw,_=parse_fbx.parse(str(output),use_namedtuple=True)
geometry=next(n for n in next(n for n in raw.elems if n.id==b'Objects').elems if n.id==b'Geometry' and n.props[2]==b'Mesh')
indices=next(n.props[0] for n in geometry.elems if n.id==b'PolygonVertexIndex')
polygons=[];face=[]
for value in indices:
    face.append(~value if value<0 else value)
    if value<0:polygons.append(tuple(face));face=[]
assert polygons==expected,'PRODUCTION_TRIANGLES_RED'
assert state()==before,'SUCCESS_CHANGED_SOURCE'

failure_calls=[]
def fail(**options):
    failure_calls.append(1)
    assert all(len(p.vertices)==3 for o in bpy.context.selected_objects if o.type=='MESH' for p in o.data.polygons)
    raise RuntimeError('INJECTED_EXPORT_FAILURE')
proxy=SimpleNamespace(context=bpy.context,data=bpy.data,types=bpy.types,
    ops=SimpleNamespace(export_scene=SimpleNamespace(fbx=fail)))
try:export_fbx(output.with_name('intentional_failure.fbx'),bpy_module=proxy)
except RuntimeError as exc:assert str(exc)=='INJECTED_EXPORT_FAILURE'
else:raise AssertionError('INJECTED_FAILURE_NOT_PROPAGATED')
assert failure_calls==[1]
assert state()==before,'FAILURE_CHANGED_SOURCE'
assert not output.with_name('intentional_failure.fbx').exists()
# Existing final-state and receipt-based static production call sites.
from unittest.mock import patch
from unitypackage_blender_importer.export.final_state_package import _stage_fbx
from unitypackage_blender_importer.operators.export_unitypackage import _export_staged_mesh
static_data=bpy.data.meshes.new('Static nonplanar')
static_data.from_pydata([(0,0,0),(2,0,0),(2,2,.6),(0,2,0)],[],[(0,1,2,3)])
static=bpy.data.objects.new('Static final',static_data)
bpy.context.scene.collection.objects.link(static)
static['_vapb_fbx_realization_id']='SYNTHETIC-RECEIPT'
static['_vapb_export_object_id']='VAPB-OBJ-'+'2'*32
for fn,label in ((_stage_fbx,'final_state'),(_export_staged_mesh,'static_receipt')):
    current=state()
    target=output.with_name(label+'.fbx')
    args=(bpy.context,static,static['_vapb_export_object_id'],target) if label=='final_state' else (bpy.context,static,target)
    fn(*args)
    assert state()==current and static.data is static_data
    tree,_=parse_fbx.parse(str(target),use_namedtuple=True)
    geometries=[n for n in next(n for n in tree.elems if n.id==b'Objects').elems if n.id==b'Geometry' and n.props[2]==b'Mesh']
    assert len(geometries)==1
    values=next(n.props[0] for n in geometries[0].elems if n.id==b'PolygonVertexIndex')
    lengths=[];length=0
    for value in values:
        length+=1
        if value<0:lengths.append(length);length=0
    assert lengths==[3,3],label+'_ROUTE_DID_NOT_FREEZE_TRIANGLES'
    import unitypackage_blender_importer.operators.export_unitypackage as receipt_export
    with patch.dict(sys.modules, {'bpy':proxy}), patch.object(receipt_export,'bpy',proxy):
        try:fn(*args)
        except RuntimeError as exc:assert str(exc)=='INJECTED_EXPORT_FAILURE'
        else:raise AssertionError(label+'_FAILURE_NOT_PROPAGATED')
    assert state()==current and static.data is static_data,label+'_ROLLBACK'

# Reopen semantic proof, not unstable Blender file byte equality.
blend=output.with_suffix('.blend')
bpy.ops.wm.save_as_mainfile(filepath=str(blend))
semantic=observe(obj,0)
bpy.ops.wm.open_mainfile(filepath=str(blend))
obj=bpy.context.view_layer.objects.active
assert observe(obj,0)==semantic,'REOPEN_CHANGED_SOURCE'
assert len(obj.data.polygons[0].vertices)==4
assert obj.modifiers[0].object is obj.parent
print('PRODUCTION_TRIANGLES_GREEN skin=1 shape=1 UV=1 materials=1 IDs=1 shared_mesh=1 success_unchanged=1 failure_rollback=1 reopen=1')
