"""Actual production Skin staging regression; self-authored assets only.

Blender --background --factory-startup --python this_file -- output_dir repo_root.
"""
from pathlib import Path
import json
import sys
import types
import re
import bpy
from io_scene_fbx import parse_fbx


def main():
    work, repo = map(Path, sys.argv[sys.argv.index('--') + 1:][:2])
    work.mkdir(exist_ok=False)
    package = types.ModuleType('unitypackage_blender_importer')
    package.__path__ = [str(repo)]
    sys.modules[package.__name__] = package
    from unitypackage_blender_importer.operators.export_unitypackage import _export_staged_skin
    from unitypackage_blender_importer.export.model_skin import model_skin_material_bindings
    rows = []
    for mode in ('DATA', 'OBJECT'):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        rig_data = bpy.data.armatures.new('FirstPartyRig')
        rig = bpy.data.objects.new('FirstPartyRig', rig_data)
        bpy.context.collection.objects.link(rig)
        rig.select_set(True)
        bpy.context.view_layer.objects.active = rig
        bpy.ops.object.mode_set(mode='EDIT')
        bone = rig_data.edit_bones.new('FirstPartyRoot')
        bone.head, bone.tail = (0, 0, 0), (0, 0, 1)
        bpy.ops.object.mode_set(mode='OBJECT')
        receipt = '00000000-0000-4000-8000-000000000001'
        rig.pose.bones[0]['_vapb_fbx_bone_realization_id'] = receipt
        data = bpy.data.meshes.new('FirstPartyTwoFaces')
        data.from_pydata([(0, 0, 0), (1, 0, 0), (0, 1, 0),
                         (2, 0, 0), (3, 0, 0), (2, 1, 0)], [], [(0, 1, 2), (3, 4, 5)])
        mesh = bpy.data.objects.new('FirstPartySkin', data)
        bpy.context.collection.objects.link(mesh)
        mesh['_vapb_fbx_realization_id'] = '00000000-0000-4000-8000-000000000002'
        modifier = mesh.modifiers.new('FirstPartySkin', 'ARMATURE')
        modifier.object = rig
        mesh.vertex_groups.new(name=rig_data.bones[0].name).add(list(range(6)), 1, 'REPLACE')
        mat = bpy.data.materials.new('FirstPartyCanonicalMaterial')
        mat['first_party_state'] = 'retain'
        data.materials.append(mat)
        data.materials.append(mat)
        for index, face in enumerate(data.polygons):
            face.material_index = index
        for slot in mesh.material_slots:
            slot.link, slot.material = mode, mat
        uv = data.uv_layers.new(name='FirstPartyUV')
        for face in data.polygons:
            for loop, value in zip(face.loop_indices, ((0, 0), (1, 0), (0, 1))):
                uv.data[loop].uv = value
        mesh.select_set(True)
        bpy.context.view_layer.objects.active = mesh
        bpy.context.view_layer.update()
        def state():
            return (data.as_pointer(), tuple(tuple(v.co) for v in data.vertices),
                    tuple((tuple(p.vertices), p.material_index) for p in data.polygons),
                    tuple(tuple(x.uv) for x in uv.data),
                    tuple(tuple((g.group, g.weight) for g in v.groups) for v in data.vertices),
                    tuple((s.link, s.material.as_pointer()) for s in mesh.material_slots),
                    tuple(tuple(x) for x in mesh.matrix_world), modifier.object.as_pointer(),
                    rig_data.as_pointer(), tuple(tuple(x) for x in rig.matrix_world),
                    tuple((b.name, b.use_connect, tuple(tuple(x) for x in b.matrix_local)) for b in rig_data.bones),
                    tuple(tuple(x) for x in rig.pose.bones[0].matrix_basis), dict(rig.pose.bones[0]),
                    mat.name, dict(mat), tuple(bpy.context.selected_objects), bpy.context.view_layer.objects.active)
        before = state()
        binding = model_skin_material_bindings([{'guid': 'a' * 32, 'file_id': '2100000'}] * 2)
        assert binding[0] == binding[1], 'CANONICAL_MATERIAL_IDENTITY_SPLIT'
        output = work / (mode + '.fbx')
        _export_staged_skin(bpy.context, mesh, rig, output,
                            {'mappings': [{'edited_bone_realization_id': receipt}]},
                            material_bindings=binding)
        assert state() == before, 'SOURCE_SKIN_STATE_CHANGED'
        tree, _ = parse_fbx.parse(str(output), use_namedtuple=True)
        nodes = {int(x.props[0]): x for p in tree.elems if p.id == b'Objects' for x in p.elems}
        model, = [u for u, n in nodes.items() if n.id == b'Model' and n.props[2] == b'Mesh']
        geometry, = [n for n in nodes.values() if n.id == b'Geometry' and n.props[2] == b'Mesh']
        mats = {u: n for u, n in nodes.items() if n.id == b'Material'}
        edges = [x.props for p in tree.elems if p.id == b'Connections' for x in p.elems if x.id == b'C']
        ordered = [int(e[1]) for e in edges if e[0] == b'OO' and int(e[2]) == model and int(e[1]) in mats]
        labels = [mats[u].props[1].split(b'\x00')[0].decode() for u in ordered]
        layer, = [x for x in geometry.elems if x.id == b'LayerElementMaterial']
        values = {x.id: x.props[0] for x in layer.elems if x.props}
        rows.append(dict(mode=mode, authored_slots=2, canonical_materials=1,
                         connections=len(ordered), labels=labels,
                         mapping=values[b'MappingInformationType'].decode(),
                         face_material_indices=list(values[b'Materials']), source_preserved=True))
        (work / 'result.json').write_text(json.dumps(rows, indent=2))
        assert len(ordered) == 2, 'USED_REPEATED_SKIN_SLOT_CONNECTIONS_COLLAPSED'
        occurrences = []
        for label in labels:
            match = re.fullmatch(re.escape(binding[0]['transport_id']) + r'-SLOT-(0|[1-9][0-9]*)', label)
            assert match, 'CANONICAL_SKIN_SLOT_LABEL_LOST'
            occurrences.append(int(match[1]))
        assert sorted(occurrences) == [0, 1]
        assert values[b'MappingInformationType'] == b'ByPolygon'
        assert [occurrences[i] for i in values[b'Materials']] == [0, 1], 'SKIN_FACE_SLOT_ASSIGNMENT_CHANGED'
    print('REPEATED_SKIN_MATERIAL_TRANSPORT_PASS', len(rows))


if __name__ == '__main__':
    main()
