"""Actual-FBX regression for used slots sharing one canonical Material.

Run with Blender background/factory-startup, then -- output-directory repo-root.
Generated geometry/materials only; directly exercises production static staging.
"""
from pathlib import Path
import json
import re
import sys
import types
import bpy
from io_scene_fbx import parse_fbx


def main():
    args = sys.argv[sys.argv.index('--') + 1:]
    work, repo = map(Path, args[:2])
    work.mkdir(exist_ok=False)
    if 'unitypackage_blender_importer' not in sys.modules:
        package = types.ModuleType('unitypackage_blender_importer')
        package.__path__ = [str(repo)]
        sys.modules[package.__name__] = package
    from unitypackage_blender_importer.export import final_state_package as product
    reports = []
    for mode in ('DATA', 'OBJECT'):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        data = bpy.data.meshes.new('FirstPartyThreeFaces')
        data.from_pydata([(x + offset, y, 0) for offset in (0, 2, 4)
                         for x, y in ((0, 0), (1, 0), (0, 1))], [],
                        [(0, 1, 2), (3, 4, 5), (6, 7, 8)])
        obj = bpy.data.objects.new('FirstPartyRepeatedSlots', data)
        bpy.context.collection.objects.link(obj)
        material = bpy.data.materials.new('CanonicalMaterial')
        material['_vapb_export_material_id'] = 'VAPB-MAT-' + 'a' * 32
        material['first_party_state'] = 'retain'
        for _ in range(3):
            data.materials.append(material)
        for index, face in enumerate(data.polygons):
            face.material_index = index
        for slot in obj.material_slots:
            slot.link = mode
            slot.material = material
        uv = data.uv_layers.new(name='FirstPartyUV')
        for face in data.polygons:
            for loop, value in zip(face.loop_indices, ((0, 0), (1, 0), (0, 1))):
                uv.data[loop].uv = value
        data.update()
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.context.view_layer.update()
        def state():
            return (obj.data.as_pointer(), tuple(tuple(v.co) for v in data.vertices),
                    tuple((tuple(f.vertices), f.material_index) for f in data.polygons),
                    tuple(tuple(x.uv) for x in data.uv_layers.active.data),
                    tuple((s.link, s.material.as_pointer()) for s in obj.material_slots),
                    material.name, dict(material), tuple(bpy.context.selected_objects),
                    bpy.context.view_layer.objects.active)
        before = state()
        ids, slots = product._material_slot_export_ids(obj.material_slots, bpy.data.materials)
        assert len(set(slots)) == 1 and len(slots) == 3
        output = work / (mode + '.fbx')
        product._stage_fbx(bpy.context, obj, 'VAPB-OBJ-' + 'b' * 32, output, ids)
        assert state() == before, 'SOURCE_STATE_CHANGED'
        root, _ = parse_fbx.parse(str(output), use_namedtuple=True)
        objects = next(x for x in root.elems if x.id == b'Objects')
        nodes = {int(x.props[0]): x for x in objects.elems}
        model, = [uid for uid, x in nodes.items() if x.id == b'Model' and x.props[2] == b'Mesh']
        geometry, = [x for x in nodes.values() if x.id == b'Geometry' and x.props[2] == b'Mesh']
        materials = {uid: x for uid, x in nodes.items() if x.id == b'Material'}
        connections = next(x for x in root.elems if x.id == b'Connections')
        ordered = [int(x.props[1]) for x in connections.elems if x.id == b'C'
                   and x.props[0] == b'OO' and int(x.props[2]) == model
                   and int(x.props[1]) in materials]
        labels = [materials[uid].props[1].split(b'\x00')[0].decode() for uid in ordered]
        layer, = [x for x in geometry.elems if x.id == b'LayerElementMaterial']
        values = {x.id: x.props[0] for x in layer.elems if x.props}
        row = dict(mode=mode, declared_slots=3, canonical_material_ids=1,
                   fbx_connections=len(ordered), labels=labels,
                   mapping=values[b'MappingInformationType'].decode(),
                   material_indices=list(values[b'Materials']), source_preserved=True)
        reports.append(row)
        (work / 'result.json').write_text(json.dumps(reports, indent=2), encoding='utf-8')
        assert len(ordered) == 3, 'USED_REPEATED_SLOT_CONNECTIONS_COLLAPSED'
        occurrence = []
        for label in labels:
            match = re.fullmatch(r'(VAPB-MAT-[0-9a-f]{32})-SLOT-(0|[1-9][0-9]*)', label)
            assert match and match.group(1) == slots[0], 'CANONICAL_SLOT_LABEL_LOST'
            occurrence.append(int(match.group(2)))
        assert sorted(occurrence) == [0, 1, 2], 'SLOT_OCCURRENCE_LOST'
        assert values[b'MappingInformationType'] == b'ByPolygon'
        assert [occurrence[index] for index in values[b'Materials']] == [0, 1, 2], 'FACE_SLOT_PARTITION_CHANGED'
    print('REPEATED_MATERIAL_SLOT_TRANSPORT_PASS', len(reports), 'LINK_MODES')


if __name__ == '__main__':
    main()
