"""HOLMES-04: actual separate-process persistence and edited standard export."""
import argparse, hashlib, importlib.util, json, sys
from pathlib import Path
import bpy
sys.dont_write_bytecode = True

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def register(repo):
    spec=importlib.util.spec_from_file_location('unitypackage_blender_importer',repo/'__init__.py',submodule_search_locations=[str(repo)])
    addon=importlib.util.module_from_spec(spec);sys.modules[spec.name]=addon;spec.loader.exec_module(addon);addon.register()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--repo',type=Path,required=True);ap.add_argument('--work',type=Path,required=True)
    ap.add_argument('--phase',choices=['import','confirm-edit','export'],required=True)
    args=ap.parse_args(sys.argv[sys.argv.index('--')+1:]);repo,work=args.repo,args.work
    report=dict(instruction_id='HOLMES-20261011-04',phase=args.phase,blender_version=bpy.app.version_string,status='NOT_RUN')
    error_class={'import':'PRE_CONFIRM_PERSISTENCE','confirm-edit':'PRE_CONFIRM_PERSISTENCE','export':'POST_CONFIRM_FINAL_STATE'}[args.phase]
    try:
        register(repo)
        from unitypackage_blender_importer.blender.renderer_binding import validate_existing_binding
        from unitypackage_blender_importer.blender.fbx_receipt import material_geometry_sha
        evidence=repo/'tests/evidence/holmes-material-correspondence-20261011/ordered-face-plan'
        frozen=json.loads((evidence/'input-and-predictions.json').read_text(encoding='utf-8-sig'))
        assert sha(evidence/'OrderedSix.unitypackage')==frozen['package_sha256']
        protected={p.name:sha(p) for p in evidence.iterdir() if p.suffix in {'.fbx','.meta','.prefab','.mat','.unitypackage'}}
        if args.phase=='import':
            bpy.ops.wm.read_factory_settings(use_empty=True)
            assert bpy.ops.import_scene.unitypackage(filepath=str(evidence/'OrderedSix.unitypackage'),import_mode='RECONSTRUCT',prefab_choice='AUTO',source_storage_directory=str(work/'archive'))=={'FINISHED'}
        else:
            filename='BeforeConfirm.blend' if args.phase=='confirm-edit' else 'EditedFinal.blend'
            assert bpy.ops.wm.open_mainfile(filepath=str(work/filename))=={'FINISHED'}
        roots=[o for o in bpy.context.scene.objects if o.get('_vapb_renderer_occurrences')]
        assert len(roots)==1;root=roots[0];record=json.loads(root['_vapb_renderer_occurrences'])['records'][0]
        candidates=[o for o in bpy.context.scene.objects if o.type=='MESH' and o.get('_vapb_root_context_id')==record['root_context_id']]
        assert len(candidates)==1;obj=candidates[0]
        if args.phase=='import':obj.data=obj.data.copy() # standard native Make Single User
        bpy.context.scene.vapb_renderer_root=root;bpy.context.scene.vapb_renderer_mesh=obj
        bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
        def refs():
            return [dict(guid=s.material.get('unity_material_guid',''),file_id=str(s.material.get('unity_material_file_id','')),package_id=s.material.get('unity_source_package_id',''),fbx_uid=s.material.get('_vapb_fbx_material_uid',''),link=s.link) for s in obj.material_slots]
        def state():
            receipt_keys=[k for k in obj.keys() if k.startswith('_vapb_fbx_') or k in ('_vapb_root_context_id','unity_source_package_id')]
            mesh_keys=[k for k in obj.data.keys() if k.startswith('_vapb_fbx_')]
            return dict(receipt=obj.get('_vapb_fbx_material_receipt'),binding=obj.get('_vapb_renderer_binding'),geometry_sha256=material_geometry_sha(obj.data),slots=refs(),
                        object_receipts={k:str(obj[k]) for k in receipt_keys},mesh_receipts={k:str(obj.data[k]) for k in mesh_keys})
        if args.phase=='import':
            assert obj.get('_vapb_fbx_material_receipt') and not obj.get('_vapb_renderer_binding')
            (work/'before-state.json').write_text(json.dumps(state(),indent=2),encoding='utf8')
            assert bpy.ops.wm.save_as_mainfile(filepath=str(work/'BeforeConfirm.blend'),check_existing=False)=={'FINISHED'}
            report.update(status='PASS',normal_import='PASS',before_blend_sha256=sha(work/'BeforeConfirm.blend'))
        elif args.phase=='confirm-edit':
            saved=json.loads((work/'before-state.json').read_text())
            actual_state=state()
            assert actual_state==saved,'save/reopen changed fields: '+', '.join(k for k in saved if actual_state.get(k)!=saved[k])
            assert bpy.ops.vapb.confirm_renderer_binding(occurrence_id=record['occurrence_id'])=={'FINISHED'}
            error_class='POST_CONFIRM_FINAL_STATE'
            sys.path.insert(0,str(evidence));sys.path.insert(0,str(evidence.parent/'topology-boundary'))
            from apply_copy import face_join
            from judge import cover
            joined=face_join(obj,frozen['raw'],cover)
            actual={raw:face for face in obj.data.polygons for raw in [joined[face.index]]}
            expected=[0,1,2,3,0,1]
            assert len(actual)==6
            def ref(face):
                mat=obj.material_slots[face.material_index].material
                return dict(guid=mat['unity_material_guid'],file_id=str(mat['unity_material_file_id']),source_package_id=mat['unity_source_package_id'])
            for raw,face in actual.items():
                wanted=record['materials'][str(expected[raw])]
                assert ref(face)==dict(guid=wanted['guid'],file_id=str(wanted['file_id']),source_package_id=wanted['source_package_id'])
            p0,p4=actual[0],actual[4]
            assert p0!=p4 and p0.material_index==p4.material_index==0
            # Evidence-backed actual polygon selection, not raw/Blender ordinal equality.
            p4.material_index=2
            assert p0.material_index==0 and ref(p4)['guid']==record['materials']['2']['guid']
            final=[dict(source_polygon=raw,uv=[list(obj.data.uv_layers.active.data[i].uv) for i in face.loop_indices],material=ref(face),topology=len(face.vertices)) for raw,face in sorted(actual.items())]
            (work/'final-state.json').write_text(json.dumps(dict(state=state(),faces=final),indent=2),encoding='utf8')
            assert bpy.ops.wm.save_as_mainfile(filepath=str(work/'EditedFinal.blend'),check_existing=False)=={'FINISHED'}
            report.update(status='PASS',pre_confirm_persistence='PASS',standard_confirm='PASS',edit='p4 R0 to R2; p0 R0 retained',faces=final,blend_sha256=sha(work/'EditedFinal.blend'))
        else:
            final=json.loads((work/'final-state.json').read_text());actual_state=state()
            assert actual_state==final['state'],'final save/reopen changed fields: '+', '.join(k for k in final['state'] if actual_state.get(k)!=final['state'][k])
            binding=json.loads(obj['_vapb_renderer_binding']);validate_existing_binding(binding,root,obj,bpy.data.objects)
            sys.path.insert(0,str(evidence));sys.path.insert(0,str(evidence.parent/'topology-boundary'))
            from apply_copy import face_join
            from judge import cover
            reopened_join=face_join(obj,frozen['raw'],cover)
            reopened_faces=[]
            for face in obj.data.polygons:
                mat=obj.material_slots[face.material_index].material
                reopened_faces.append(dict(source_polygon=reopened_join[face.index],
                    uv=[list(obj.data.uv_layers.active.data[i].uv) for i in face.loop_indices],
                    material=dict(guid=mat['unity_material_guid'],file_id=str(mat['unity_material_file_id']),source_package_id=mat['unity_source_package_id']),
                    topology=len(face.vertices)))
            reopened_faces.sort(key=lambda row:row['source_polygon'])
            assert reopened_faces==final['faces'],'reopened UV/topology/material evidence changed'
            report['post_confirm_final_state']='PASS'
            error_class='EXPORT_TRANSPORT'
            output=work/'EditedMaterialOutput.unitypackage';assert not output.exists()
            assert bpy.ops.export_scene.vapb_unitypackage(filepath=str(output),export_scope='ACTIVE')=={'FINISHED'}
            from unitypackage_blender_importer.export.raw_assets import RawAssetRepository
            assets=RawAssetRepository(output).read_all()
            manifest_asset=next(a for a in assets if a.pathname=='Assets/VAPBExport/manifest.json')
            manifest=json.loads(manifest_asset.asset_bytes)
            (work/'manifest.json').write_bytes(manifest_asset.asset_bytes)
            for a in assets:
                if a.pathname.endswith('.fbx') and a.asset_bytes!=next(x for x in RawAssetRepository(evidence/'OrderedSix.unitypackage').read_all() if x.pathname.endswith('.fbx')).asset_bytes:
                    (work/'Exported.fbx').write_bytes(a.asset_bytes)
            assert (work/'Exported.fbx').is_file()
            report.update(status='PASS',standard_export='PASS',package_sha256=sha(output),exported_fbx_sha256=sha(work/'Exported.fbx'),manifest_sha256=sha(work/'manifest.json'),faces=reopened_faces,assets=[dict(guid=a.guid,path=a.pathname,sha256=hashlib.sha256(a.asset_bytes).hexdigest()) for a in assets])
        assert protected=={p.name:sha(p) for p in evidence.iterdir() if p.suffix in {'.fbx','.meta','.prefab','.mat','.unitypackage'}}
        report['original_preservation']='PASS'
    except Exception as error:
        report.update(status='FAIL',first_failure=error_class,error=type(error).__name__+': '+str(error))
    (work/(args.phase+'.json')).write_text(json.dumps(report,indent=2),encoding='utf8')
    print('HOLMES04',args.phase,report['status'],report.get('error',''))

if __name__=='__main__':main()
