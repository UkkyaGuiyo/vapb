"""Phase-2 RED controls; generate first-party fixtures, no private inputs.

Run Blender with --python-exit-code 1 and -- <unused scratch directory>.
Exit 0 means both current refusals were observed, not successful roundtrip.
"""
from pathlib import Path
import struct
import sys
import zlib

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import unitypackage_blender_importer as addon
from unitypackage_blender_importer.export.final_state_package import export_final_state_package
from unitypackage_blender_importer.export.package_writer import UnityPackageWriter
from unitypackage_blender_importer.export.staging import StagedUnityAsset, StagingTree

MATERIAL_GUID = '1' * 32
TEXTURE_GUID = '2' * 32
SHADER_GUID = '3' * 32
SHADER = b'''Shader "VAPB/SyntheticUnlit" {
Properties { _MainTex ("Main", 2D) = "white" {}
             _FutureTexture ("Preserved use", 2D) = "white" {} }
SubShader { Pass { SetTexture [_MainTex] { combine texture } } }
Fallback Off
}
'''


def png():
    def chunk(kind, payload):
        return (struct.pack('>I', len(payload)) + kind + payload
                + struct.pack('>I', zlib.crc32(kind + payload)))
    return (b'\x89PNG\r\n\x1a\n'
            + chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 6, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(b'\x00\x40\x80\xc0\xff'))
            + chunk(b'IEND', b''))


def fixture(root, nonstandard):
    shader_ref = (f'{{fileID: 4800000, guid: {SHADER_GUID}, type: 3}}' if nonstandard
                  else '{fileID: 46, guid: 0000000000000000f000000000000000, type: 0}')
    material = f'''%YAML 1.1
%TAG !u! tag:unity3d.com,2011:
--- !u!21 &2100000
Material:
  serializedVersion: 8
  m_Name: SyntheticReference
  m_Shader: {shader_ref}
  m_CustomRenderQueue: -1
  m_SavedProperties:
    serializedVersion: 3
    m_TexEnvs:
'''
    for prop in ('_MainTex', '_FutureTexture'):
        material += f'''    - {prop}:
        m_Texture: {{fileID: 2800000, guid: {TEXTURE_GUID}, type: 3}}
        m_Scale: {{x: 1, y: 1}}
        m_Offset: {{x: 0, y: 0}}
'''
    material += '    m_Ints: []\n    m_Floats: []\n    m_Colors: []\n'
    def asset(guid, suffix, payload, importer):
        meta = f'fileFormatVersion: 2\nguid: {guid}\n{importer}:\n  serializedVersion: 2\n'.encode()
        return StagedUnityAsset(guid, 'Assets/VAPBPhase2/' + suffix, payload, meta)
    entries = [asset(MATERIAL_GUID, 'SyntheticReference.mat', material.encode(), 'NativeFormatImporter')]
    if nonstandard:
        entries.append(asset(SHADER_GUID, 'SyntheticUnlit.shader', SHADER, 'ShaderImporter'))
    UnityPackageWriter().write(StagingTree(entries), root / 'Material.unitypackage')
    UnityPackageWriter().write(StagingTree([
        asset(TEXTURE_GUID, 'SyntheticTexture.png', png(), 'TextureImporter')]), root / 'Texture.unitypackage')


def main():
    scratch = Path(sys.argv[sys.argv.index('--') + 1])
    if scratch.exists():
        raise ValueError('use an unused scratch directory')
    scratch.mkdir(parents=True)
    for phase in ('NONSTANDARD_GATE', 'CROSS_PACKAGE_PROVIDER'):
        root = scratch / phase
        root.mkdir()
        fixture(root, phase == 'NONSTANDARD_GATE')
        bpy.ops.wm.read_factory_settings(use_empty=True)
        addon.register()
        try:
            for filename in ('Material.unitypackage', 'Texture.unitypackage'):
                assert bpy.ops.import_scene.unitypackage(
                    filepath=str(root / filename), import_mode='RECONSTRUCT',
                    use_materials=True, use_textures=True, keep_extracted=False,
                    source_storage_directory=str(root / 'archive')) == {'FINISHED'}
            materials = [m for m in bpy.data.materials if m.get('unity_material_guid') == MATERIAL_GUID]
            assert len(materials) == 1
            assert any(image.get('unity_guid') == TEXTURE_GUID for image in bpy.data.images)
            bpy.ops.mesh.primitive_cube_add()
            cube = bpy.context.object
            assert cube.data.uv_layers
            assert not any(key in cube for key in (
                '_vapb_renderer_binding', '_vapb_fbx_realization_id',
                '_vapb_fbx_mesh_receipt_id', '_vapb_occurrence_id'))
            cube.data.materials.append(materials[0])
            output = root / 'Unexpected.unitypackage'
            try:
                export_final_state_package(bpy.context, cube, output)
            except ValueError as error:
                expected = ('only the synthetic built-in Standard shader is supported'
                            if phase == 'NONSTANDARD_GATE'
                            else 'selected Material Texture provider is unavailable')
                assert str(error) == expected, str(error)
                assert not output.exists()
                print('PHASE2_RED_CONFIRMED', phase)
            else:
                raise AssertionError('expected export refusal was not observed')
        finally:
            addon.unregister()


if __name__ == '__main__':
    main()
