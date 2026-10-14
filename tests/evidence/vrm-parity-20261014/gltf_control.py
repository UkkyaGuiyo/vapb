# SPDX-License-Identifier: GPL-3.0-or-later
"""One bundled-glTF transport observation from the owned source Blend.

Run only in a new owned process after resource gates. This is a generic rig
preliminary control, not the UnityPackage V0 or SoulFlame R0 comparison.
No exporter implementation is inspected and no source file is saved over.
"""
import hashlib
import json
from pathlib import Path
import sys


def capture(bpy):
    meshes, rigs = [], []
    for obj in bpy.context.scene.objects:
        if obj.type == 'ARMATURE':
            rigs.append(dict(diagnostic_name=obj.name, matrix_world=[list(r) for r in obj.matrix_world],
                bones=[dict(diagnostic_name=b.name, diagnostic_parent=b.parent.name if b.parent else None,
                    matrix_local=[list(r) for r in b.matrix_local],
                    world_head=list(obj.matrix_world @ b.head_local)) for b in obj.data.bones]))
        if obj.type != 'MESH':
            continue
        mesh = obj.data
        mesh.calc_tangents(uvmap=mesh.uv_layers.active.name)
        basis = mesh.shape_keys.key_blocks[0] if mesh.shape_keys else None
        faces = []
        for face in mesh.polygons:
            corners = []
            for index in face.loop_indices:
                loop = mesh.loops[index]; vertex = mesh.vertices[loop.vertex_index]
                corners.append(dict(native_vertex=vertex.index, uv=list(mesh.uv_layers.active.data[index].uv),
                    local_position=list(vertex.co), world_position=list(obj.matrix_world @ vertex.co),
                    local_normal=list(mesh.corner_normals[index].vector), local_tangent=list(loop.tangent),
                    tangent_sign=loop.bitangent_sign,
                    weights={obj.vertex_groups[g.group].name:g.weight for g in vertex.groups},
                    shapes={k.name:list(obj.matrix_world.to_3x3() @ (k.data[vertex.index].co-basis.data[vertex.index].co))
                            for k in mesh.shape_keys.key_blocks[1:]} if basis else {}))
            faces.append(dict(material_slot=face.material_index, corners=corners))
        meshes.append(dict(diagnostic_name=obj.name, native_vertex_count=len(mesh.vertices), faces=faces,
            matrix_world=[list(r) for r in obj.matrix_world],
            materials=[dict(diagnostic_name=m.name, rgba=list(m.diffuse_color)) for m in mesh.materials]))
    return dict(meshes=meshes, rigs=rigs)


def main():
    import bpy
    source = Path(bpy.data.filepath).resolve()
    if source.name != 'Source.blend' or set(bpy.context.scene.objects.keys()) != {'DiagnosticRig','DiagnosticBody'}:
        raise RuntimeError('OWNED_AUTHORING_SOURCE_REQUIRED')
    output = Path(sys.argv[sys.argv.index('--')+1]).resolve()
    if output.exists():
        raise RuntimeError('OUTPUT_EXISTS')
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    before = capture(bpy)
    output.mkdir(parents=True, exist_ok=False)
    glb = output/'GenericRig.glb'
    result = bpy.ops.export_scene.gltf(filepath=str(glb), export_format='GLB', use_selection=False,
        export_yup=True, export_animations=False, export_skins=True, export_all_influences=True,
        export_morph=True, export_texcoords=True, export_normals=True, export_tangents=True,
        export_draco_mesh_compression_enable=False, export_meshopt_compression_enable=False,
        will_save_settings=False)
    if result != {'FINISHED'}:
        raise RuntimeError('GLTF_EXPORT_NOT_FINISHED')
    # Reset only this newly owned process; the original file remains byte-preserved.
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if bpy.ops.import_scene.gltf(filepath=str(glb), merge_vertices=False, import_shading='NORMALS') != {'FINISHED'}:
        raise RuntimeError('GLTF_IMPORT_NOT_FINISHED')
    after = capture(bpy)
    if hashlib.sha256(source.read_bytes()).hexdigest() != digest:
        raise RuntimeError('SOURCE_FILE_CHANGED')
    observation = dict(scope='GENERIC_RIG_BUNDLED_GLTF_PRELIMINARY_NOT_V0_R0',
        blender_version=bpy.app.version_string, source_blend_sha256=digest,
        glb_sha256=hashlib.sha256(glb.read_bytes()).hexdigest(), before=before, after=after,
        unity_source='NOT_CREATED', unity_restore='NOT_MEASURED', human_eligibility='NOT_MEASURED',
        original_unity_material_identity='NOT_AUTHORED', verdict='NATIVE_ARRAYS_CAPTURED_NOT_JUDGED')
    (output/'observation.json').write_text(json.dumps(observation,indent=2),encoding='utf-8')


if __name__ == '__main__':
    main()
