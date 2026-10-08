import sys,json,hashlib,tarfile,tempfile,importlib.util
from pathlib import Path
from collections import Counter
import bpy
repo=Path(sys.argv[sys.argv.index('--')+1]).resolve();work=Path(sys.argv[sys.argv.index('--')+2]).resolve()
spec=importlib.util.spec_from_file_location('_vapb_strict',repo/'tests/strict_source_import.py');strict=importlib.util.module_from_spec(spec);spec.loader.exec_module(strict)
addon=strict.load_source_package(repo);addon.register()
from unitypackage_blender_importer.unity.material_mapping import parse_external_object_rows
from io_scene_fbx import parse_fbx
package=work/'SourceProject/RemappedInput.unitypackage';package_sha=hashlib.sha256(package.read_bytes()).hexdigest()
with tarfile.open(package,'r:gz') as t:
    paths={m.name.rsplit('/',1)[0]:t.extractfile(m).read().decode() for m in t.getmembers() if m.isfile() and m.name.endswith('/pathname')}
    assert not any(p.endswith('.prefab') for p in paths.values())
    key=next(k for k,p in paths.items() if p.endswith('Input.fbx'))
    payload=t.extractfile(key+'/asset').read();meta=t.extractfile(key+'/asset.meta').read().decode()
rows=parse_external_object_rows(meta);assert len(rows)==3 and all(r.row_status=='valid' and not r.ambiguous for r in rows)
refs={r.canonical_name:(r.canonical_guid,str(r.canonical_file_id)) for r in rows};assert len(refs)==3
with tempfile.TemporaryDirectory(prefix='fbx-read-',dir=work) as temp:
    file=Path(temp)/'Input.fbx';file.write_bytes(payload);raw,_=parse_fbx.parse(str(file),use_namedtuple=True)
objects=next(e for e in raw.elems if e.id==b'Objects');connections=next(e for e in raw.elems if e.id==b'Connections')
geometry=[e for e in objects.elems if e.id==b'Geometry' and e.props[2]==b'Mesh'];assert len(geometry)==1;geometry=geometry[0]
model=next(c.props[2] for c in connections.elems if c.id==b'C' and c.props[1]==geometry.props[0])
materials={e.props[0]:e.props[1].split(b'\x00')[0].decode() for e in objects.elems if e.id==b'Material'}
slots=[c.props[1] for c in connections.elems if c.id==b'C' and c.props[2]==model and c.props[1] in materials]
values=next(e.props[0] for e in geometry.elems if e.id==b'Vertices');vertices=[tuple(values[i:i+3]) for i in range(0,len(values),3)]
indices=next(e.props[0] for e in geometry.elems if e.id==b'PolygonVertexIndex');polygons=[];current=[]
for i in indices:
    current.append(-i-1 if i<0 else i)
    if i<0:polygons.append(current);current=[]
layer=next(e for e in geometry.elems if e.id==b'LayerElementMaterial')
assert next(e.props[0] for e in layer.elems if e.id==b'MappingInformationType')==b'ByPolygon'
assert next(e.props[0] for e in layer.elems if e.id==b'ReferenceInformationType')==b'IndexToDirect'
assignments=next(e.props[0] for e in layer.elems if e.id==b'Materials');assert len(assignments)==len(polygons)==12 and all(len(p)==3 for p in polygons)
def corners(vs):return tuple(sorted(tuple(round(float(v),6) for v in point) for point in vs))
expected=Counter((corners([vertices[i] for i in p]),refs[materials[slots[index]]]) for p,index in zip(polygons,assignments))
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
result=bpy.ops.import_scene.unitypackage(filepath=str(package),import_mode='RECONSTRUCT',keep_extracted=True,source_storage_directory=str(work/'BlenderSources'))
assert result=={'FINISHED'},result
meshes=[o for o in bpy.context.scene.objects if o.type=='MESH'];assert len(meshes)==1,len(meshes);obj=meshes[0];obj.data.calc_loop_triangles()
actual=Counter();identities=[]
for slot in obj.material_slots:
    m=slot.material;identities.append((m.get('unity_material_guid',''),str(m.get('unity_material_file_id','')),m.get('unity_source_package_id','')) if m else ('','',''))
for tri in obj.data.loop_triangles:
    identity=identities[tri.material_index];assert identity[2]=='sha256:'+package_sha,identity
    actual[(corners([obj.data.vertices[i].co for i in tri.vertices]),identity[:2])]+=1
ok=actual==expected
report=dict(status='PASS_RAW_FBX_FACE_AND_EXPLICIT_REMAP_IDENTITY' if ok else 'FAIL_FACE_OR_IDENTITY',package_sha256=package_sha,fbx_sha256=hashlib.sha256(payload).hexdigest(),triangle_count=sum(actual.values()),raw_fbx_expected_triangle_count=sum(expected.values()),material_slot_identities=identities,full_labelled_triangle_multiset_matches=ok,coordinate_frame='raw FBX geometry local versus native Blender Mesh local; no fit',coordinate_quantization_decimals=6,winding='not asserted; corners unoriented',normal_import=True,confirm_or_identity_repair=False,prefab_present=False)
(work/'blender-import-observation.json').write_text(json.dumps(report,indent=2)+'\n')
print('VAPB_REMAPPED_INPUT_IMPORT',report['status']);assert ok,report
addon.unregister()
