import sys,json,hashlib,tempfile,importlib.util
from pathlib import Path
from collections import Counter
import bpy
repo=Path(sys.argv[sys.argv.index('--')+1]).resolve();work=Path(sys.argv[sys.argv.index('--')+2]).resolve()
package=work.parent/'remapped-model-input-20261008-01/SourceProject/RemappedInput.unitypackage'
input_sha=hashlib.sha256(package.read_bytes()).hexdigest();assert input_sha=='3f0612d120949d692883cd318b7d5f72a358b9105e77e54b5368dd9e3ffde65b'
spec=importlib.util.spec_from_file_location('_vapb_strict',repo/'tests/strict_source_import.py');strict=importlib.util.module_from_spec(spec);spec.loader.exec_module(strict)
addon=strict.load_source_package(repo);addon.register()
from unitypackage_blender_importer.export.raw_assets import RawAssetRepository
from io_scene_fbx import parse_fbx
try:
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    assert bpy.ops.import_scene.unitypackage(filepath=str(package),import_mode='RECONSTRUCT',keep_extracted=True,source_storage_directory=str(work/'BlenderSources'))=={'FINISHED'}
    meshes=[o for o in bpy.context.scene.objects if o.type=='MESH'];assert len(meshes)==1;obj=meshes[0]
    assert len(obj.material_slots)==3 and all(s.material for s in obj.material_slots)
    source_materials={str(s.material.get('unity_material_guid')):s.material for s in obj.material_slots}
    if '--native-only' in sys.argv:
        edit_scale = 1.0 if '--native-unchanged' in sys.argv else 1.25
        if edit_scale != 1.0:
            for v in obj.data.vertices: v.co *= edit_scale
        vertices = [tuple(v.co) for v in obj.data.vertices]
        rig = obj.modifiers[0].object
        bone_state = [(b.get('_vapb_fbx_model_uid'), b.get('_vapb_fbx_bone_realization_id'),
                       tuple(tuple(row) for row in b.matrix_local)) for b in rig.data.bones]
        reopened = '--native-reopen' in sys.argv
        if reopened:
            material_state = [(slot.material.get('unity_material_guid'), slot.material.get('unity_material_file_id')) for slot in obj.material_slots]
            assert bpy.ops.wm.save_as_mainfile(filepath=str(work/'NativeSkinEdit.blend')) == {'FINISHED'}
            assert bpy.ops.wm.open_mainfile(filepath=str(work/'NativeSkinEdit.blend')) == {'FINISHED'}
            meshes = [o for o in bpy.context.scene.objects if o.type=='MESH'];assert len(meshes)==1;obj=meshes[0]
            rig = obj.modifiers[0].object
            assert vertices == [tuple(v.co) for v in obj.data.vertices]
            assert material_state == [(slot.material.get('unity_material_guid'), slot.material.get('unity_material_file_id')) for slot in obj.material_slots]
            assert bone_state == [(b.get('_vapb_fbx_model_uid'), b.get('_vapb_fbx_bone_realization_id'), tuple(tuple(row) for row in b.matrix_local)) for b in rig.data.bones]
        obj.select_set(True);bpy.context.view_layer.objects.active=obj
        output = work/'NativeSkinOutput.unitypackage'
        assert bpy.ops.export_scene.vapb_unitypackage(filepath=str(output)) == {'FINISHED'}
        assets = RawAssetRepository(output).read_all();source = RawAssetRepository(package).read_all()
        by_guid = {a.guid:a for a in assets}
        assert all(by_guid[a.guid].asset_bytes == a.asset_bytes and by_guid[a.guid].meta_bytes == a.meta_bytes for a in source)
        assert vertices == [tuple(v.co) for v in obj.data.vertices]
        assert bone_state == [(b.get('_vapb_fbx_model_uid'), b.get('_vapb_fbx_bone_realization_id'),
                               tuple(tuple(row) for row in b.matrix_local)) for b in rig.data.bones]
        manifest = json.loads(next(a.asset_bytes for a in assets if a.pathname=='Assets/VAPBExport/manifest.json'))
        task = manifest['reference_rebind_tasks'][0]
        assert task['kind']=='RESTORE_SOURCE_MODEL_SKIN_VARIANT_V1' and not task.get('prefab_guid')
        assert task['model_guid'] != task['source_model_guid'] and not task['instance_edges']
        report = dict(status='PASS_BOUNDED_NATIVE_SKIN_EXPORT_ONLY', input_sha256=input_sha,
                      output_sha256=hashlib.sha256(output.read_bytes()).hexdigest(), task=task,
                      source_assets_and_meta_byte_preserved=True, editing_mesh_and_bones_unchanged_by_export=True,
                      edit_scale=edit_scale, scene_saved_reopened=reopened, unity_return='NOT_RUN', scope='single no-Prefab source-model Skin unchanged export' if edit_scale == 1.0 else 'single no-Prefab source-model Skin geometry edit')
        (work/'native-skin-export-observation.json').write_text(json.dumps(report,indent=2)+'\n')
        print('VAPB_NATIVE_SKIN_EXPORT',report['status']);sys.exit(0)
    if '--replacement-only' not in sys.argv:
        native=dict(operator='export_scene.vapb_unitypackage',modifier_types=[m.type for m in obj.modifiers],has_uv=bool(obj.data.uv_layers),root_context_present=bool(obj.get('_vapb_root_context_id')),edit_scale=1.25)
        for v in obj.data.vertices:v.co*=1.25
        for o in bpy.context.selected_objects:o.select_set(False)
        obj.select_set(True);bpy.context.view_layer.objects.active=obj
        try:
            native['operator_result']=sorted(bpy.ops.export_scene.vapb_unitypackage(filepath=str(work/'NativeSkinOutput.unitypackage')))
        except RuntimeError as error:
            native['operator_result']=['CANCELLED'];native['exception_type']=type(error).__name__;native['local_error_message']=str(error)
        native['output_created']=(work/'NativeSkinOutput.unitypackage').exists()
        (work/'native-skin-export-boundary.json').write_text(json.dumps(native,indent=2)+'\n')
        assert native['operator_result']==['CANCELLED'] and not native['output_created']
    bpy.data.objects.remove(obj,do_unlink=True)
    bpy.ops.mesh.primitive_cube_add();obj=bpy.context.object;obj.name='Authored replacement Cube'
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project();bpy.ops.object.mode_set(mode='OBJECT')
    for guid in ('64f92a1bd9b35a040bf9e2c6d200b34c','0318f358e4c29034aa90cc8c50b58a93','eb805efb35118044db5e74adc652673a'):obj.data.materials.append(source_materials[guid])
    for polygon in obj.data.polygons:polygon.material_index=max(range(3),key=lambda axis:abs(polygon.normal[axis]))
    assert not obj.modifiers and obj.data.shape_keys is None and obj.data.uv_layers
    original_vertices=[tuple(v.co) for v in obj.data.vertices]
    for v in obj.data.vertices:v.co*=1.25
    obj.data.update();obj.data.calc_loop_triangles()
    def signature(points):return tuple(sorted(tuple(round(float(v),6) for v in p) for p in points))
    def identity(m):return (str(m.get('unity_material_guid','')),str(m.get('unity_material_file_id','')))
    expected=Counter((signature([obj.data.vertices[i].co for i in tri.vertices]),identity(obj.material_slots[tri.material_index].material)) for tri in obj.data.loop_triangles)
    assert sum(expected.values())==12 and len({ref for _,ref in expected})==3
    final_vertices=[tuple(v.co) for v in obj.data.vertices];face_indices=[p.material_index for p in obj.data.polygons]
    material_refs=[identity(s.material) for s in obj.material_slots];world=[list(r) for r in obj.matrix_world]
    export_ids_before=[obj.get('_vapb_export_object_id'),*[s.material.get('_vapb_export_material_id') for s in obj.material_slots]]
    for o in bpy.context.selected_objects:o.select_set(False)
    obj.select_set(True);bpy.context.view_layer.objects.active=obj
    output=work/'EditedOutput.unitypackage'
    assert bpy.ops.export_scene.vapb_final_state_unitypackage(filepath=str(output))=={'FINISHED'}
    assert final_vertices==[tuple(v.co) for v in obj.data.vertices] and face_indices==[p.material_index for p in obj.data.polygons]
    assert material_refs==[identity(s.material) for s in obj.material_slots] and world==[list(r) for r in obj.matrix_world]
    assert export_ids_before==[obj.get('_vapb_export_object_id'),*[s.material.get('_vapb_export_material_id') for s in obj.material_slots]]
    source={a.guid:a for a in RawAssetRepository(package).read_all()};assets=RawAssetRepository(output).read_all();by_guid={a.guid:a for a in assets}
    manifest=json.loads(next(a.asset_bytes for a in assets if a.pathname=='Assets/VAPBExport/manifest.json'))
    records=manifest['material_mappings'];assert len(records)==3
    mapping={r['export_material_id']:(r['guid'],r['file_id']) for r in records};assert set(mapping.values())==set(material_refs)
    preserved=[]
    for guid,file_id in material_refs:
        assert file_id=='2100000' and by_guid[guid].asset_bytes==source[guid].asset_bytes and by_guid[guid].meta_bytes==source[guid].meta_bytes
        preserved.append(dict(guid=guid,file_id=file_id,payload_sha256=hashlib.sha256(by_guid[guid].asset_bytes).hexdigest(),meta_sha256=hashlib.sha256(by_guid[guid].meta_bytes).hexdigest()))
    fbx=next(a for a in assets if a.pathname.lower().endswith('.fbx'))
    with tempfile.TemporaryDirectory(prefix='output-fbx-read-',dir=work) as temp:
        file=Path(temp)/'Output.fbx';file.write_bytes(fbx.asset_bytes);raw,_=parse_fbx.parse(str(file),use_namedtuple=True)
    objects=next(e for e in raw.elems if e.id==b'Objects');connections=next(e for e in raw.elems if e.id==b'Connections')
    geometries=[e for e in objects.elems if e.id==b'Geometry' and e.props[2]==b'Mesh'];assert len(geometries)==1;geometry=geometries[0]
    model=next(c.props[2] for c in connections.elems if c.id==b'C' and c.props[1]==geometry.props[0])
    mats={e.props[0]:e.props[1].split(b'\x00')[0].decode() for e in objects.elems if e.id==b'Material'}
    slots=[c.props[1] for c in connections.elems if c.id==b'C' and c.props[2]==model and c.props[1] in mats]
    assert len(slots)==3 and set(mats.values())==set(mapping)
    values=next(e.props[0] for e in geometry.elems if e.id==b'Vertices');vertices=[tuple(values[i:i+3]) for i in range(0,len(values),3)]
    indices=next(e.props[0] for e in geometry.elems if e.id==b'PolygonVertexIndex');polygons=[];current=[]
    for i in indices:
        current.append(-i-1 if i<0 else i)
        if i<0:polygons.append(current);current=[]
    layer=next(e for e in geometry.elems if e.id==b'LayerElementMaterial')
    assert next(e.props[0] for e in layer.elems if e.id==b'MappingInformationType')==b'ByPolygon'
    assert next(e.props[0] for e in layer.elems if e.id==b'ReferenceInformationType')==b'IndexToDirect'
    assignments=next(e.props[0] for e in layer.elems if e.id==b'Materials');assert len(assignments)==len(polygons)==12 and all(len(p)==3 for p in polygons)
    actual=Counter((signature([vertices[i] for i in p]),mapping[mats[slots[index]]]) for p,index in zip(polygons,assignments))
    matches=actual==expected
    bbox=lambda vs:[max(v[a] for v in vs)-min(v[a] for v in vs) for a in range(3)]
    digest=lambda c:hashlib.sha256(json.dumps(sorted((k,count) for k,count in c.items()),separators=(',',':')).encode()).hexdigest()
    report=dict(status='PASS_MULTIMATERIAL_REPLACEMENT_EXPORT_ONLY' if matches else 'FAIL_FACE_OR_FRAME',input_sha256=input_sha,output_sha256=hashlib.sha256(output.read_bytes()).hexdigest(),output_fbx_sha256=hashlib.sha256(fbx.asset_bytes).hexdigest(),operator='export_scene.vapb_final_state_unitypackage',route='T4 replacement Cube; source Skin removed from editing scene',authored_material_faces='absolute face normal X/Y/Z -> three exact selected Unity Material GUIDs',edit_scale=1.25,source_mesh_local_bbox=bbox(original_vertices),edited_mesh_local_bbox=bbox(final_vertices),output_raw_geometry_bbox=bbox(vertices),expected_labelled_triangle_sha256=digest(expected),actual_labelled_triangle_sha256=digest(actual),full_labelled_triangle_multiset_matches=matches,triangle_count=sum(actual.values()),distinct_material_count=3,material_assets_preserved=preserved,material_mappings=records,reference_rebind_tasks=manifest['reference_rebind_tasks'],editing_scene_unchanged_by_export=True,source_export_ids_unchanged=True,coordinate_quantization_decimals=6,coordinate_frame='edited Blender Mesh local versus output raw FBX Geometry local; no fitted transform',winding='unoriented membership only',unity_return='NOT_RUN',input_archive_unchanged=hashlib.sha256(package.read_bytes()).hexdigest()==input_sha)
    (work/'edit-export-observation.json').write_text(json.dumps(report,indent=2)+'\n');(work/'output-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('VAPB_MULTIMATERIAL_EDIT_EXPORT',report['status']);assert matches,report
finally:
    addon.unregister()
