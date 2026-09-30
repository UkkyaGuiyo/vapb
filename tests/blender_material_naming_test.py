"""Production import/export naming cases; generated first-party packages only."""
from pathlib import Path
import sys
import hashlib
import json
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import unitypackage_blender_importer as addon
from unitypackage_blender_importer.tests import blender_material_return_phase2_test as fixture
from unitypackage_blender_importer.blender.material_owner_usage import KEY


def prefab(name, refs):
    return ('''%YAML 1.1
%TAG !u! tag:unity3d.com,2011:
--- !u!1 &100
GameObject:
  m_Component:
  - component: {fileID: 101}
  - component: {fileID: 102}
  - component: {fileID: 103}
  m_Name: ''' + name + '''
  m_IsActive: 1
--- !u!4 &101
Transform:
  m_GameObject: {fileID: 100}
  m_Father: {fileID: 0}
  m_Children: []
  m_LocalPosition: {x: 0, y: 0, z: 0}
  m_LocalRotation: {x: 0, y: 0, z: 0, w: 1}
  m_LocalScale: {x: 1, y: 1, z: 1}
--- !u!33 &102
MeshFilter:
  m_GameObject: {fileID: 100}
  m_Mesh: {fileID: 4300000, guid: ''' + '4'*32 + ''', type: 3}
--- !u!23 &103
MeshRenderer:
  m_GameObject: {fileID: 100}
  m_Materials:
''' + ''.join('  - {fileID: 2100000, guid: '+guid+', type: 2}\n' for guid in refs)).encode()


def main():
    root = Path(sys.argv[sys.argv.index('--')+1])
    root.mkdir(exist_ok=False)
    fixture.fixture(root, False)
    source = fixture.RawAssetRepository(root/'Material.unitypackage').read_all()[0]
    (root/'Material.unitypackage').rename(root/'HistoricalSeed.bin')
    guids = ['1'*32, '7'*32, '8'*32, '9'*32, 'a'*32]
    entries = []
    for i, guid in enumerate(guids):
        name = 'SharedSkin' if i == 3 else 'Body'
        payload = source.asset_bytes.replace(b'm_Name: SyntheticReference', ('m_Name: '+name).encode())
        entries.append(fixture.StagedUnityAsset(guid, f'Assets/Inputs/{i}/{name}.mat', payload,
                       source.meta_bytes.replace(source.guid.encode(), guid.encode())))
    fixture.UnityPackageWriter().write(fixture.StagingTree(entries), root/'Materials.unitypackage')
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.mesh.primitive_cube_add()
    bpy.ops.export_scene.fbx(filepath=str(root/'Input.fbx'), use_selection=True, add_leaf_bones=False)
    geometry = fixture.StagedUnityAsset('4'*32, 'Assets/Inputs/Input.fbx',
                    (root/'Input.fbx').read_bytes(), b'fileFormatVersion: 2\nguid: '+b'4'*32+b'\nModelImporter:\n  serializedVersion: 22200\n')
    for guid, name, refs in [('5'*32, 'Majun', [guids[0], guids[2], guids[3]]),
                             ('6'*32, 'Other', [guids[1], guids[3]])]:
        entry = fixture.StagedUnityAsset(guid, f'Assets/Inputs/{name}.prefab', prefab(name, refs),
                        f'fileFormatVersion: 2\nguid: {guid}\nPrefabImporter:\n'.encode())
        fixture.UnityPackageWriter().write(fixture.StagingTree([entry, geometry]), root/(name+'.unitypackage'))
    bpy.ops.wm.read_factory_settings(use_empty=True)
    addon.register()
    try:
        for name in ('Materials', 'Texture', 'Majun', 'Other'):
            assert bpy.ops.import_scene.unitypackage(filepath=str(root/(name+'.unitypackage')),
                    import_mode='RECONSTRUCT', use_materials=True, use_textures=True,
                    prefab_choice='PREFAB_0' if name in ('Majun', 'Other') else 'AUTO',
                    keep_extracted=False, source_storage_directory=str(root/'archive')) == {'FINISHED'}
        materials = {guid: next(m for m in bpy.data.materials if m.get('unity_material_guid') == guid) for guid in guids}
        assert all(materials[g].get(KEY) for g in guids[:4]), 'OWNER_CAPTURE_MISSING'
        assert not materials[guids[4]].get(KEY)
        # Standard A keeps the imported Mesh; B severs source geometry lineage.
        assert any(o.type == 'MESH' for o in bpy.data.objects)
        if '--unchanged' in sys.argv:
            cube = next(o for o in bpy.data.objects if o.type == 'MESH' and o.data.uv_layers)
            for obj in bpy.context.selected_objects:
                obj.select_set(False)
            cube.select_set(True)
            bpy.context.view_layer.objects.active = cube
            cube.data.materials.clear()
        else:
            for obj in list(bpy.data.objects):
                bpy.data.objects.remove(obj, do_unlink=True)
            bpy.ops.mesh.primitive_cube_add()
            cube = bpy.context.object
            assert not cube.get('_vapb_fbx_realization_id')
        for guid in guids:
            cube.data.materials.append(materials[guid])
        manifest = fixture.export_final_state_package(bpy.context, cube, root/'Output.unitypackage')
        output = {a.guid: a for a in fixture.RawAssetRepository(root/'Output.unitypackage').read_all()}
        assert '/Majun/Materials/Majun_Body__' in output[guids[0]].pathname
        assert '/Other/Materials/Other_Body.mat' in output[guids[1]].pathname
        assert '/Majun/Materials/Majun_Body__' in output[guids[2]].pathname
        assert output[guids[3]].pathname.endswith('/Shared/Materials/SharedSkin.mat')
        assert output[guids[4]].pathname.endswith('/Unassigned/Materials/Body.mat')
        for entry in entries:
            assert output[entry.guid].asset_bytes == entry.asset_bytes
            assert output[entry.guid].meta_bytes == entry.meta_bytes
        paths = {g: output[g].pathname for g in guids}
        bpy.ops.wm.save_as_mainfile(filepath=str(root/'Cube.blend'))
        bpy.ops.wm.open_mainfile(filepath=str(root/'Cube.blend'))
        cube = next(o for o in bpy.data.objects if o.get('_vapb_export_object_id'))
        fixture.export_final_state_package(bpy.context, cube, root/'Reopened.unitypackage')
        replay = {a.guid: a for a in fixture.RawAssetRepository(root/'Reopened.unitypackage').read_all()}
        assert paths == {g: replay[g].pathname for g in guids}
        assert all(replay[e.guid].asset_bytes == e.asset_bytes for e in entries)
        print('MATERIAL_NAMING_PRODUCTION_PASS cases=7 payload_meta_preserved=5')
    finally:
        addon.unregister()


if __name__ == '__main__':
    main()
