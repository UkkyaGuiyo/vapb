"""Install, enable and disable a ZIP through Blender with isolated user paths."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tempfile

import bpy


def state(obj):
    rig = next(m.object for m in obj.modifiers if m.type == 'ARMATURE')
    keys = obj.data.shape_keys
    return dict(
        vertices=[list(v.co) for v in obj.data.vertices],
        faces=[list(p.vertices) for p in obj.data.polygons],
        loops=[l.vertex_index for l in obj.data.loops],
        face_materials=[p.material_index for p in obj.data.polygons],
        uv=[list(x.uv) for x in obj.data.uv_layers.active.data],
        weights=[[[g.group, g.weight] for g in v.groups] for v in obj.data.vertices],
        groups=[g.name for g in obj.vertex_groups],
        matrix=[list(row) for row in obj.matrix_world],
        rig_matrix=[list(row) for row in rig.matrix_world],
        bones=[dict(uid=str(b.get('_vapb_fbx_model_uid', '')),
                    realization=str(b.get('_vapb_fbx_bone_realization_id', '')),
                    parent_uid=str(b.parent.get('_vapb_fbx_model_uid', '')) if b.parent else '',
                    matrix=[list(row) for row in b.matrix_local], head=list(b.head_local), tail=list(b.tail_local), connected=b.use_connect) for b in rig.data.bones],
        materials=[dict(guid=str(s.material.get('unity_material_guid', '')),
                        file_id=str(s.material.get('unity_material_file_id', ''))) for s in obj.material_slots],
        channels=[dict(name=k.name, value=k.value, relative=keys.key_blocks.find(k.relative_key.name),
                       points=[list(p.co) for p in k.data]) for k in keys.key_blocks] if keys else [],
        shape_receipt=keys['_vapb_fbx_shape_receipts'] if keys else None,
        shape_receipt_sha256=keys['_vapb_fbx_shape_receipt_sha256'] if keys else None,
        model_uid=str(obj.get('_vapb_fbx_model_uid', '')),
        geometry_uid=str(obj.get('_vapb_fbx_geometry_uid', '')),
        realization_id=str(obj.get('_vapb_fbx_realization_id', '')))



def install_in_isolated_child(archive_path: Path) -> None:
    import addon_utils

    scripts = Path(os.environ['BLENDER_USER_SCRIPTS']).resolve()
    config = Path(os.environ['BLENDER_USER_CONFIG']).resolve()
    assert Path(bpy.utils.user_resource('SCRIPTS')).resolve() == scripts
    assert Path(bpy.utils.user_resource('CONFIG')).resolve() == config
    assert not (config / 'userpref.blend').exists()
    module = 'unitypackage_blender_importer'
    assert module not in sys.modules
    assert module not in bpy.context.preferences.addons
    assert bpy.ops.preferences.addon_install(filepath=str(archive_path), overwrite=False) == {'FINISHED'}
    assert bpy.ops.preferences.addon_enable(module=module) == {'FINISHED'}
    addon = sys.modules[module]
    assert Path(addon.__file__).resolve().is_relative_to(scripts)
    assert addon.PREFERENCES_CLASSES
    assert module in bpy.context.preferences.addons
    assert addon_utils.check(module) == (True, True)
    import hashlib,json,tarfile
    args = sys.argv[sys.argv.index('--') + 1:]
    scene = Path(args[args.index('--blend')+1]).resolve()
    source = Path(args[args.index('--source')+1]).resolve()
    output = Path(args[args.index('--output')+1]).resolve()
    result = Path(args[args.index('--result')+1]).resolve()
    sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
    before_hash=sha(scene);source_hash=sha(source)
    assert bpy.ops.wm.open_mainfile(filepath=str(scene))=={'FINISHED'}
    obj, = [o for o in bpy.context.scene.objects if o.type=='MESH']
    before=state(obj)
    assert len(before['vertices'])==4 and len(before['faces'])==2 and all(len(f)==3 for f in before['faces'])
    assert obj.data.shape_keys is None and len(before['bones'])==2
    shared=sorted(set(before['faces'][0])&set(before['faces'][1]));assert len(shared)==2
    cp=shared[0];occurrences=[i for i,c in enumerate(before['loops']) if c==cp];assert len(occurrences)==2
    assert before['uv'][occurrences[0]]==before['uv'][occurrences[1]]
    loop=occurrences[0];obj.data.uv_layers.active.data[loop].uv.x+=0.125
    after=state(obj);wanted=json.loads(json.dumps(before));wanted['uv'][loop][0]+=0.125;assert after==wanted
    saved=Path(args[args.index('--saved')+1]);assert not saved.exists()
    original_blend_sha256=before_hash
    assert bpy.ops.wm.save_as_mainfile(filepath=str(saved))=={'FINISHED'}
    assert sha(scene)==original_blend_sha256
    assert bpy.ops.wm.open_mainfile(filepath=str(saved))=={'FINISHED'}
    obj, = [o for o in bpy.context.scene.objects if o.type=='MESH'];assert state(obj)==after
    scene=saved;before_hash=sha(saved);before=after

    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
    assert not output.exists()
    assert bpy.ops.export_scene.vapb_unitypackage(filepath=str(output))=={'FINISHED'}
    assert state(obj)==before and sha(scene)==before_hash and sha(source)==source_hash
    from unitypackage_blender_importer.export.raw_assets import RawAssetRepository
    assets=RawAssetRepository(output).read_all();by={a.guid:a for a in assets}
    assert all(by[a.guid].asset_bytes==a.asset_bytes and by[a.guid].meta_bytes==a.meta_bytes for a in RawAssetRepository(source).read_all())
    manifest=json.loads(next(a.asset_bytes for a in assets if a.pathname=='Assets/VAPBExport/manifest.json'))
    task, = manifest['reference_rebind_tasks']
    assert task['kind']=='RESTORE_SOURCE_MODEL_SKIN_VARIANT_V1' and not task.get('action_clip')
    helper_path='unity_editor/Editor/VapbModelSkinFinalizer.cs'
    installed=(Path(addon.__file__).parent/helper_path).read_bytes()
    helper=next(a.asset_bytes for a in assets if a.pathname=='Assets/VAPBExport/Editor/VapbModelSkinFinalizer.cs')
    assert helper==installed
    assert hashlib.sha256(helper.replace(bytes([13,10]),bytes([10]))).hexdigest()=='62d34a43f44714c0edc758dc9297f4c6f25fced6430ba51c09c9cdb67e659698'
    observation=dict(original_blend_sha256=original_blend_sha256,changed_cp=cp,changed_loop=loop,delta_u=0.125,only_uv_changed=True,save_reopen_state_exact=True,before=before,state=after,status='PASS',installed_normal_rest_export=True,source_and_blend_preserved=True,state_exact=True,blend_sha256=before_hash,source_sha256=source_hash,output_sha256=sha(output),helper_sha256=hashlib.sha256(helper).hexdigest(),human_gui_clicks='NOT_RUN',unity_remeasurement='NOT_RUN')
    assert bpy.ops.preferences.addon_disable(module=module) == {'FINISHED'}
    assert module not in bpy.context.preferences.addons
    assert addon_utils.check(module) == (False, False)
    assert not (config / 'userpref.blend').exists()
    observation.update(standard_install_enable_disable=True,isolated_preferences_unsaved=True)
    result.write_text(json.dumps(observation,indent=2),encoding='utf-8')
    print('DIST_INSTALLED_NORMAL_REST_EXPORT_OK')


def main() -> None:
    if "--" not in sys.argv:
        raise SystemExit("usage: blender ... --python blender_distribution_install_test.py -- ZIP")
    archive_path = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
    assert archive_path.is_file()
    if '--isolated-child' in sys.argv[sys.argv.index('--') + 2:]:
        install_in_isolated_child(archive_path)
        return
    with tempfile.TemporaryDirectory(prefix="unitypackage_install_") as temp:
        install_root = Path(temp)
        env = os.environ.copy()
        for suffix in ('CONFIG', 'SCRIPTS', 'DATAFILES', 'EXTENSIONS'):
            isolated = install_root / suffix.lower()
            isolated.mkdir()
            env['BLENDER_USER_' + suffix] = str(isolated)
        env['BLENDER_USER_RESOURCES'] = str(install_root)
        env.pop('PYTHONPATH', None)
        subprocess.run([
            bpy.app.binary_path, '--background', '--factory-startup', '--disable-autoexec',
            '--python-exit-code', '1', '--python', str(Path(__file__).resolve()),
            '--', str(archive_path), *sys.argv[sys.argv.index('--') + 2:], '--isolated-child',
        ], cwd=install_root, env=env, check=True)


main()
