"""Generated public deferred Shader acceptance. Blender --python-exit-code 1 --python FILE -- NEW_SCRATCH [--addon-zip ZIP]."""
from pathlib import Path
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile

import bpy


def main():
    args = sys.argv[sys.argv.index('--') + 1:]
    scratch = Path(args[0]).resolve()
    if '--addon-zip' in args and '--isolated-child' not in args:
        with tempfile.TemporaryDirectory(prefix='vapb_deferred_install_') as temp:
            env = os.environ.copy()
            for suffix in ('CONFIG', 'SCRIPTS', 'DATAFILES', 'EXTENSIONS'):
                path = Path(temp) / suffix.lower()
                path.mkdir()
                env['BLENDER_USER_' + suffix] = str(path)
            env['BLENDER_USER_RESOURCES'] = temp
            env.pop('PYTHONPATH', None)
            subprocess.run([bpy.app.binary_path, '--background', '--factory-startup',
                '--disable-autoexec', '--python-exit-code', '1', '--python', __file__,
                '--', *args, '--isolated-child'], cwd=temp, env=env, check=True)
        return
    if scratch.exists():
        raise ValueError('UNUSED_SCRATCH_REQUIRED')
    scratch.mkdir(parents=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    installed = '--addon-zip' in args
    if installed:
        archive = Path(args[args.index('--addon-zip') + 1]).resolve()
        assert bpy.ops.preferences.addon_install(filepath=str(archive), overwrite=False) == {'FINISHED'}
        assert bpy.ops.preferences.addon_enable(module='unitypackage_blender_importer') == {'FINISHED'}
    else:
        sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import blender_material_return_phase2_test as fixture
    addon = fixture.addon
    if installed:
        assert Path(addon.__file__).resolve().is_relative_to(Path(os.environ['BLENDER_USER_SCRIPTS']))
    else:
        addon.register()
    try:
        inputs = scratch / 'SyntheticInputs'
        inputs.mkdir()
        fixture.fixture(inputs, True)
        material_assets = fixture.RawAssetRepository(inputs / 'Material.unitypackage').read_all()
        material = next(a for a in material_assets if a.guid == fixture.MATERIAL_GUID)
        shader = next(a for a in material_assets if a.guid == fixture.SHADER_GUID)
        fixture.UnityPackageWriter().write(fixture.StagingTree([material]), inputs / 'PackageA.unitypackage')
        (inputs / 'Texture.unitypackage').rename(inputs / 'PackageB.unitypackage')
        # Shader is a separate later Unity input. It never enters Blender/VAPB.
        fixture.UnityPackageWriter().write(fixture.StagingTree([shader]), scratch / 'ExternalShader.unitypackage')
        (inputs / 'Material.unitypackage').unlink()
        for name in ('PackageA.unitypackage', 'PackageB.unitypackage'):
            assert bpy.ops.import_scene.unitypackage(filepath=str(inputs / name), import_mode='RECONSTRUCT',
                use_materials=True, use_textures=True, keep_extracted=False,
                source_storage_directory=str(scratch / 'archive')) == {'FINISHED'}
        materials = [m for m in bpy.data.materials if m.get('unity_material_guid') == fixture.MATERIAL_GUID]
        assert len(materials) == 1
        bpy.ops.mesh.primitive_cube_add()
        cube = bpy.context.object
        assert cube.data.uv_layers
        cube.data.materials.append(materials[0])
        output = scratch / 'Output.unitypackage'
        # Replay control starts with explicit fixture IDs; fresh read-only IDs have a separate control.
        from uuid import uuid4
        cube["_vapb_export_object_id"] = "VAPB-OBJ-" + uuid4().hex
        for slot in cube.material_slots:
            if slot.material and not slot.material.get("_vapb_export_material_id"):
                slot.material["_vapb_export_material_id"] = "VAPB-MAT-" + uuid4().hex
        manifest = fixture.export_final_state_package(bpy.context, cube, output)
        record = manifest.material_mappings[0]
        ref = record['shader']
        assert ref['classification'] == ref['status'] == 'UNRESOLVED_BUT_PRESERVED'
        assert ref['kind'] == 'SHADER'
        assert re.fullmatch(r'VAPB-REF-[0-9a-f]{32}', ref['reference_id'])
        assert ref['guid'] == fixture.SHADER_GUID and ref['file_id'] == '4800000'
        assert manifest.external_dependencies == (ref,)
        assert len(record['textures']) == 2
        assert {t['guid'] for t in record['textures']} == {fixture.TEXTURE_GUID}
        assets = {a.guid: a for a in fixture.RawAssetRepository(output).read_all()}
        assert assets[fixture.MATERIAL_GUID].asset_bytes == material.asset_bytes
        assert assets[fixture.TEXTURE_GUID].asset_bytes == fixture.png()
        assert fixture.SHADER_GUID not in assets
        assert not any(a.pathname.lower().endswith('.shader') for a in assets.values())
        assert any(a.pathname.endswith('.fbx') for a in assets.values())
        assert any(a.pathname.endswith('VapbFinalStateFinalizer.cs') for a in assets.values())
        expected = {'material_guid': fixture.MATERIAL_GUID, 'material_file_id': '2100000',
            'shader_guid': fixture.SHADER_GUID, 'shader_file_id': '4800000',
            'texture_guid': fixture.TEXTURE_GUID, 'texture_file_id': '2800000',
            'reference_id': ref['reference_id'],
            'source_material_sha256': hashlib.sha256(material.asset_bytes).hexdigest()}
        (scratch / 'Expected.json').write_text(json.dumps(expected), encoding='utf-8')
        bpy.ops.wm.save_as_mainfile(filepath=str(scratch / 'Cube.blend'))
        export_id = cube.get('_vapb_export_object_id')
        assert export_id
        assert bpy.ops.wm.open_mainfile(filepath=str(scratch / 'Cube.blend')) == {'FINISHED'}
        reopened = next(o for o in bpy.context.scene.objects if o.get('_vapb_export_object_id') == export_id)
        reopened.name = 'RenamedAfterReopen'
        replay = fixture.export_final_state_package(bpy.context, reopened, scratch / 'Reopened.unitypackage')
        assert replay.material_mappings == manifest.material_mappings
        assert replay.external_dependencies == manifest.external_dependencies
        replay_assets = {a.guid: a for a in fixture.RawAssetRepository(scratch / 'Reopened.unitypackage').read_all()}
        assert replay_assets[fixture.MATERIAL_GUID].asset_bytes == material.asset_bytes
        assert replay_assets[fixture.TEXTURE_GUID].asset_bytes == fixture.png()
        assert fixture.SHADER_GUID not in replay_assets
        # Only generated fixtures become unavailable, after the exports have finished.
        inputs.rename(scratch / 'UnavailableSyntheticInputs')
        (scratch / 'archive').rename(scratch / 'UnavailableSyntheticArchive')
        print('DEFERRED_SHADER_BLENDER_PASS')
    finally:
        if installed:
            import addon_utils
            assert bpy.ops.preferences.addon_disable(module='unitypackage_blender_importer') == {'FINISHED'}
            assert addon_utils.check('unitypackage_blender_importer') == (False, False)
        else:
            addon.unregister()


if __name__ == '__main__':
    main()
