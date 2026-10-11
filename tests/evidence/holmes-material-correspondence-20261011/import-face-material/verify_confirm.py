"""Native standard Import/Confirm regression. No UV correspondence input."""
import bpy, sys, importlib.util, json, hashlib, copy
from pathlib import Path
sys.dont_write_bytecode = True

def main():
    repo, work = map(Path, sys.argv[sys.argv.index('--') + 1:])
    spec = importlib.util.spec_from_file_location('unitypackage_blender_importer', repo/'__init__.py', submodule_search_locations=[str(repo)])
    addon = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = addon; spec.loader.exec_module(addon); addon.register()
    from unitypackage_blender_importer.operators import renderer_binding as rb
    from unitypackage_blender_importer.blender.fbx_receipt import material_geometry_sha
    bpy.ops.wm.read_factory_settings(use_empty=True)
    package = repo/'tests/evidence/holmes-material-correspondence-20261011/ordered-face-plan/OrderedSix.unitypackage'
    frozen = {str(p.relative_to(package.parent)): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in package.parent.iterdir() if p.suffix in {'.fbx','.meta','.mat','.prefab','.unitypackage'}}
    assert bpy.ops.import_scene.unitypackage(filepath=str(package), import_mode='RECONSTRUCT', prefab_choice='AUTO', source_storage_directory=str(work/'sources')) == {'FINISHED'}
    root = next(o for o in bpy.data.objects if o.get('_vapb_renderer_occurrences'))
    payload = json.loads(root['_vapb_renderer_occurrences']); record = payload['records'][0]
    obj = next(o for o in bpy.data.objects if o.type == 'MESH' and o.get('_vapb_root_context_id') == record['root_context_id'])
    source = next(o for o in bpy.data.objects if o.type == 'MESH' and o.data == obj.data and o != obj)
    receipt = json.loads(obj['_vapb_fbx_material_receipt'])
    bpy.context.scene.vapb_renderer_root = root; bpy.context.scene.vapb_renderer_mesh = obj
    def state(o):
        return repr((material_geometry_sha(o.data), [(s.link, s.material.as_pointer() if s.material else None) for s in o.material_slots],
                     [m.as_pointer() if m else None for m in o.data.materials], sorted((k,str(o[k])) for k in o.keys()), sorted((k,str(o.data[k])) for k in o.data.keys())))
    def confirm():
        try: return bpy.ops.vapb.confirm_renderer_binding(occurrence_id=record['occurrence_id'])
        except RuntimeError: return {'CANCELLED'}
    results = {}
    def refusal(name):
        before = state(obj)
        assert confirm() == {'CANCELLED'}, name+' accepted'
        assert before == state(obj), name+' changed state'
        results[name] = 'REFUSED_UNCHANGED'
    refusal('shared_mesh')
    original_state = state(source)
    obj.data = obj.data.copy()  # ordinary native Make Single User; no binding/receipt injection
    base_payload = root['_vapb_renderer_occurrences']
    for name, change in [('wrong_ref', lambda r: r['materials']['0'].update(guid='f'*32)),
                         ('null_ref', lambda r: r['materials'].update({'0':None})),
                         ('wrong_mesh_file_id',lambda r:r['mesh'].update(mesh_file_id=-123))]:
        altered = copy.deepcopy(payload); change(altered['records'][0]); root['_vapb_renderer_occurrences'] = json.dumps(altered)
        refusal(name); root['_vapb_renderer_occurrences'] = base_payload
    saved = obj['_vapb_fbx_material_receipt']; del obj['_vapb_fbx_material_receipt']
    refusal('unproven_source'); obj['_vapb_fbx_material_receipt'] = saved
    obj.data.materials.append(obj.data.materials[0]); refusal('unused_slot'); obj.data.materials.pop(index=2)
    obj.data.polygons[0].material_index = 1; refusal('user_face_edit'); obj.data.polygons[0].material_index = 0
    provider = next(m for m in bpy.data.materials if m.get('unity_material_guid') == record['materials']['0']['guid'])
    duplicate = provider.copy(); duplicate.name = provider.name; refusal('same_name_provider_conflict'); bpy.data.materials.remove(duplicate)
    revision = provider['_vapb_source_material_sha256']; provider['_vapb_source_material_sha256'] = '0'*64
    refusal('provider_revision'); provider['_vapb_source_material_sha256'] = revision
    provider_path = Path(provider['unity_source_material']); meta = Path(str(provider_path)+'.meta')
    saved_meta = meta.read_bytes()
    try:
        meta.write_bytes(saved_meta.replace(record['materials']['0']['guid'].encode(),b'f'*32))
        refusal('provider_meta_guid')
    finally: meta.write_bytes(saved_meta)
    missing_meta_source = work/'provider-without-meta.mat'
    missing_meta_source.write_bytes(provider_path.read_bytes())
    provider['unity_source_material'] = str(missing_meta_source)
    try: refusal('provider_meta_missing')
    finally: provider['unity_source_material'] = str(provider_path)
    before = state(obj); real_dumps = rb.json.dumps
    def fail_binding(value, *args, **kwargs):
        if isinstance(value,dict) and value.get('evidence') == 'USER_CONFIRMED': raise RuntimeError('injected binding-write failure')
        return real_dumps(value,*args,**kwargs)
    rb.json.dumps = fail_binding
    try: assert confirm() == {'CANCELLED'}
    finally: rb.json.dumps = real_dumps
    assert before == state(obj), 'rollback failed'; results['exception_rollback'] = 'RESTORED_ALL'
    assert confirm() == {'FINISHED'}
    expected_indices = [0,1,2,3,0,1]
    actual = []
    for face, expected in zip(obj.data.polygons, expected_indices):
        assert face.material_index == expected
        slot = obj.material_slots[face.material_index]; mat = slot.material
        reference = dict(guid=mat['unity_material_guid'],file_id=str(mat['unity_material_file_id']),source_package_id=mat['unity_source_package_id'])
        wanted = record['materials'][str(expected)]
        assert slot.link == 'OBJECT' and reference == dict(guid=wanted['guid'],file_id=str(wanted['file_id']),source_package_id=wanted['source_package_id'])
        actual.append(dict(uid=receipt['faces'][face.index]['uid'],topology=len(face.vertices),slot=face.material_index,material=reference))
    assert state(source) == original_state
    assert frozen == {str(p.relative_to(package.parent)): hashlib.sha256(p.read_bytes()).hexdigest() for p in package.parent.iterdir() if p.suffix in {'.fbx','.meta','.mat','.prefab','.unitypackage'}}
    report = dict(instruction_id='HOLMES-20261011-03',instruction_source='APPROVED_CHAT_ONLY',instruction_commit=None,
                  blender_version=bpy.app.version_string,importer_sha256=receipt['importer_sha256'],normal_import='PASS',standard_confirm='PASS',per_face_refs='PASS',
                  old_guard_refusals=results,original_preservation='PASS',unity_return_finalizer='NOT_RUN',render='NOT_RUN',uv_correspondence_consumed=False,
                  captured_receipt=receipt,actual_faces=actual,protected_asset_sha256=frozen)
    (work/'confirm.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    print('HOLMES03_STANDARD_CONFIRM_PASS')

if __name__ == '__main__': main()
