"""Produce current production Outputs from an existing public naming fixture .blend.

Blender --python FILE -- SOURCE_FIXTURE UNUSED_DEST [single]
Expected.json comes from original fixture assets and fixed synthetic slot policy,
not from the output manifest. No private inputs are permitted.
"""
from pathlib import Path
import sys
import hashlib
import json
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from unitypackage_blender_importer.export.final_state_package import export_final_state_package, _material_data
from unitypackage_blender_importer.export.raw_assets import RawAssetRepository


def main():
    args = sys.argv[sys.argv.index('--') + 1:]
    source, dest = map(Path, args[:2])
    dest.mkdir(exist_ok=False)
    bpy.ops.wm.open_mainfile(filepath=str(source/'Cube.blend'))
    cube = next(o for o in bpy.data.objects if o.get('_vapb_export_object_id'))
    guids = ['1'*32, '7'*32, '8'*32, '9'*32, 'a'*32]
    single = len(args) > 2 and args[2] == 'single'
    if single:
        material = next(m for m in bpy.data.materials if m.get('unity_material_guid') == guids[0])
        cube.data.materials.clear()
        cube.data.materials.append(material)
        guids = guids[:1]
    else:
        # Exercise all selected slots in the positive multi-Material fixture.
        # The separate original unused-slot Output is retained as a rejected
        # existing Finalizer boundary, not repaired by this naming mission.
        assert len(cube.data.polygons) >= len(guids)
        for i, polygon in enumerate(cube.data.polygons):
            polygon.material_index = i % len(guids)
    bpy.context.view_layer.objects.active = cube
    cube.select_set(True)
    export_final_state_package(bpy.context, cube, dest/'Output.unitypackage')
    originals = {a.guid: a for a in RawAssetRepository(source/'Materials.unitypackage').read_all()}
    output = {a.guid: a for a in RawAssetRepository(dest/'Output.unitypackage').read_all()}
    records = []
    for index, guid in enumerate(guids):
        original = originals[guid]
        data = _material_data(original.asset_bytes)
        owner = 'Majun' if index in (0, 2) else 'Other' if index == 1 else 'Shared' if index == 3 else 'Unassigned'
        stem = (owner+'_' if owner in ('Majun', 'Other') else '') + data.name
        if not single and index in (0, 2):
            stem += '__' + hashlib.sha256(guid.encode()).hexdigest()[:12]
        path = f'Assets/VAPBExport/{owner}/Materials/{stem}.mat'
        assert output[guid].pathname == path
        assert output[guid].asset_bytes == original.asset_bytes
        assert output[guid].meta_bytes == original.meta_bytes
        records.append({'guid': guid, 'file_id': str(data.file_id), 'path': path,
            'name': data.name, 'sha256': hashlib.sha256(original.asset_bytes).hexdigest(),
            'meta_sha256': hashlib.sha256(original.meta_bytes).hexdigest(),
            'shader_guid': data.shader_guid, 'shader_id': str(data.shader_file_id),
            'textures': [{'property': r.property_name, 'guid': r.guid, 'file_id': str(r.file_id)}
                         for r in data.textures.values() if r.file_id != 0]})
    # Source fixture defines the exact Blender final slot order independently.
    assert [slot.material.get('unity_material_guid') for slot in cube.material_slots] == guids
    expected = {'materials': records, 'slot_guids': guids, 'slot_ids': [r['file_id'] for r in records]}
    (dest/'Expected.json').write_text(json.dumps(expected, indent=2), encoding='utf-8')
    print('NAMING_PRODUCTION_OUTPUT_PASS materials='+str(len(records)))


if __name__ == '__main__':
    main()
