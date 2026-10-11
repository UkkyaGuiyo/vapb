import bpy, sys, json, hashlib, importlib.util
from pathlib import Path
repo=Path(sys.argv[sys.argv.index('--')+1]); work=Path(__file__).parent
sys.dont_write_bytecode=True
from io_scene_fbx import import_fbx as native
materials={}; layers={}
origmat=native.blen_read_material; origlayer=native.blen_read_geom_layer_material
def shape(mesh):
    return dict(starts=[p.loop_start for p in mesh.polygons], loops=[l.vertex_index for l in mesh.loops],indices=[p.material_index for p in mesh.polygons])
def mat_hook(t,o,s):
    mat=origmat(t,o,s); materials[mat.as_pointer()]=int(o.props[0]); return mat
def layer_hook(o,m):
    result=origlayer(o,m)
    ls=[x for x in o.elems if x.id==b'LayerElementMaterial']
    layers[m.as_pointer()]=dict(geometry_uid=int(o.props[0]), layer_count=len(ls),
        mapping=native.elem_prop_first(native.elem_find_first(ls[0],b'MappingInformationType')).decode(),
        reference=native.elem_prop_first(native.elem_find_first(ls[0],b'ReferenceInformationType')).decode(),
        source_indices=list(native.elem_prop_first(native.elem_find_first(ls[0],b'Materials'))),written=shape(m))
    return result
spec=importlib.util.spec_from_file_location('unitypackage_blender_importer',repo/'__init__.py',submodule_search_locations=[str(repo)])
addon=importlib.util.module_from_spec(spec);sys.modules[spec.name]=addon;spec.loader.exec_module(addon);addon.register()
native.blen_read_material=mat_hook;native.blen_read_geom_layer_material=layer_hook
try:
    status=bpy.ops.import_scene.unitypackage(filepath=str(repo/'tests/unity_model_material_probe/fixtures/ThreeSlotSource.unitypackage'),import_mode='RECONSTRUCT',prefab_choice='AUTO',source_storage_directory=str(work/'sources'))
finally:
    native.blen_read_material=origmat;native.blen_read_geom_layer_material=origlayer
rows=[]
for obj in bpy.data.objects:
    if obj.type=='MESH':
        capture=layers.get(obj.data.as_pointer())
        rows.append(dict(object=obj.name,users=obj.data.users,root_context=obj.get('_vapb_root_context_id'),capture=capture,final=shape(obj.data),slot_uids=[materials.get(s.material.as_pointer()) if s.material else None for s in obj.material_slots],props=dict(obj.items())))
roots=[dict(name=o.name,records=json.loads(o['_vapb_renderer_occurrences'])) for o in bpy.data.objects if o.get('_vapb_renderer_occurrences')]
result=dict(instruction_id='HOLMES-20261011-03',version=bpy.app.version_string,importer_sha256=hashlib.sha256(Path(native.__file__).read_bytes()).hexdigest(),status=list(status),objects=rows,roots=roots)
(work/'probe.json').write_text(json.dumps(result,indent=2,default=str),encoding='utf8')
print('HOLMES03_PROBE_DONE')
