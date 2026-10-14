# SPDX-License-Identifier: GPL-3.0-or-later
"""One first-party authoring candidate; adapt existing shape/material fixture patterns.

Only run after host resource gates and an owned empty Blender session are verified.
Usage in a newly owned process: Blender --background --factory-startup
  --python-expr "import bpy; bpy.ops.wm.read_factory_settings(use_empty=True)"
  --python make_fixture.py -- NEW_FOLDER
The script itself refuses non-empty scenes and never resets an existing session.
No Unity eligibility, correspondence or PASS result is inferred here.
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import sys


def main():
    import bpy
    from mathutils import Vector

    data_path = Path(__file__).with_name('fixture.json')
    fixture = json.loads(data_path.read_text(encoding='utf-8'))
    output = Path(sys.argv[sys.argv.index('--') + 1]).resolve()
    if output.exists():
        raise RuntimeError('OUTPUT_ALREADY_EXISTS')
    if len(bpy.data.objects):
        raise RuntimeError('OWNED_EMPTY_SCENE_REQUIRED')
    # Load only the existing first-party explicit preset, no addon registration.
    repo = Path(__file__).resolve().parents[3]
    spec = importlib.util.spec_from_file_location('fixture_fbx_preset', repo / 'export/fbx_export.py')
    preset = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(preset)
    rig = bpy.data.objects.new('DiagnosticRig', bpy.data.armatures.new('DiagnosticBones'))
    bpy.context.scene.collection.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    bones = {}
    for row in fixture['bones']:
        bone = rig.data.edit_bones.new(row['role'])
        bone.head, bone.tail = row['head'], row['tail']
        if row['parent']:
            bone.parent = bones[row['parent']]
        bone.use_connect = False
        bones[row['role']] = bone
    bpy.ops.object.mode_set(mode='OBJECT')
    mesh = bpy.data.meshes.new('DiagnosticMesh')
    mesh.from_pydata(fixture['vertices'], [], fixture['faces'])
    mesh.update()
    body = bpy.data.objects.new('DiagnosticBody', mesh)
    bpy.context.scene.collection.objects.link(body)
    body.parent = rig
    body.modifiers.new('DiagnosticSkin', 'ARMATURE').object = rig
    groups = {name: body.vertex_groups.new(name=name) for name in ('Hips', 'Spine')}
    for index, row in enumerate(fixture['weights']):
        for name, weight in row.items():
            groups[name].add([index], weight, 'REPLACE')
    for index, color in enumerate(fixture['material_rgba']):
        material = bpy.data.materials.new('DiagnosticMaterial' + str(index))
        material.diffuse_color = color
        mesh.materials.append(material)
    uv = mesh.uv_layers.new(name='DiagnosticUV')
    for face, slot in zip(mesh.polygons, fixture['face_materials']):
        face.material_index = slot
        values = ((face.index / 16, .125), (face.index / 16 + .03125, .125),
                  (face.index / 16, .15625))
        for loop, value in zip(face.loop_indices, values):
            uv.data[loop].uv = value
    body.shape_key_add(name='Basis')
    for name, deltas in fixture['shape_deltas'].items():
        shape = body.shape_key_add(name=name)
        for index, delta in deltas.items():
            shape.data[int(index)].co += Vector(delta)
        shape.value = 0
    body.select_set(True)
    bpy.context.view_layer.objects.active = body
    output.mkdir(parents=True, exist_ok=False)
    fbx = output / 'Source.fbx'
    options = dict(preset.FBX_EXPORT_PRESET, filepath=str(fbx))
    if bpy.ops.export_scene.fbx(**options) != {'FINISHED'}:
        raise RuntimeError('FBX_EXPORT_NOT_FINISHED')
    blend = output / 'Source.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(blend), check_existing=True)
    observation = dict(status='AUTHORED_NOT_UNITY_ELIGIBLE_PROOF',
                       blender_version=bpy.app.version_string,
                       vertices=[list(v.co) for v in mesh.vertices],
                       faces=[list(p.vertices) for p in mesh.polygons],
                       uv=[list(x.uv) for x in uv.data],
                       face_materials=[p.material_index for p in mesh.polygons],
                       weights=[{body.vertex_groups[g.group].name: g.weight for g in v.groups}
                                for v in mesh.vertices],
                       bone_rest=[dict(name=b.name, parent=b.parent.name if b.parent else None,
                                       matrix=[list(row) for row in b.matrix_local]) for b in rig.data.bones],
                       shapes={k.name:[list(v.co) for v in k.data] for k in mesh.shape_keys.key_blocks},
                       hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                               for p in (data_path, fbx, blend)},
                       unity_eligibility='NOT_MEASURED', c_state='NOT_AUTHORED')
    (output / 'authoring.json').write_text(json.dumps(observation, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
