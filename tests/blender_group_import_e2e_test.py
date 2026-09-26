"""GI-001..007: synthetic split import in background or a fresh foreground UI."""
from pathlib import Path
import base64
import json
import sys
import tempfile
import time

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import unitypackage_blender_importer as addon
from unitypackage_blender_importer.tests.blender_cross_package_dependency_test import package, material, make_fbx
from unitypackage_blender_importer.operators import import_unitypackage as m
from unitypackage_blender_importer.operators.renderer_binding import _material_plan
from unitypackage_blender_importer.blender.renderer_binding import BindingError


def prefab(fbx_guid, material_guid):
    return f"""%YAML 1.1
--- !u!1 &1001
GameObject:
  m_Name: Coat
  m_Component:
  - component: {{fileID: 101}}
  - component: {{fileID: 103}}
  - component: {{fileID: 102}}
--- !u!4 &101
Transform:
  m_GameObject: {{fileID: 1001}}
  m_Father: {{fileID: 0}}
  m_LocalPosition: {{x: 0, y: 0, z: 0}}
  m_LocalRotation: {{x: -3.65e-12, y: 2.45e-9, z: -2.25e-7,
    w: 1}}
  m_LocalScale: {{x: 1, y: 1, z: 1}}
--- !u!33 &103
MeshFilter:
  m_GameObject: {{fileID: 1001}}
  m_Mesh: {{fileID: 4300000, guid: {fbx_guid},
    type: 3}}
--- !u!23 &102
MeshRenderer:
  m_GameObject: {{fileID: 1001}}
  m_Materials:
  - {{fileID: 2100000, guid: {material_guid},
      type: 2}}
""".encode()


def main():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    temp = tempfile.TemporaryDirectory(prefix='group_lifecycle_')
    root = Path(temp.name)
    geometry, provider = root/'Geometry.unitypackage', root/'Appearance.unitypackage'
    fbx_guid, material_guid, image_guid = 'a'*32, 'b'*32, 'c'*32
    package(geometry, [(fbx_guid, 'Assets/Body.fbx', make_fbx())] + [
        (str(i)*32, f'Assets/Prefab{label}.prefab', prefab(fbx_guid, material_guid))
        for i, label in enumerate(('A','B','C'), 1)
    ])
    png = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=')
    package(provider, [(material_guid, 'Assets/Surface.mat', material(image_guid)), (image_guid, 'Assets/Base.png', png)])
    evidence = {'children': [], 'async_children': 0, 'child_discovery': 0, 'final_resolvers': []}
    stack = []
    original_execute = m.UNITYPACKAGE_OT_import.execute
    original_async = m.UNITYPACKAGE_OT_import._start_async_prepare
    original_discover = m.discover_siblings
    original_resolve = m.resolve_after_import

    def mesh_pointers():
        return {o.as_pointer() for o in bpy.data.objects if o.type == 'MESH'}

    def execute(self, context):
        child = bool(self.group_child)
        before = mesh_pointers()
        sessions = set(m._PREPARED_SESSIONS)
        stack.append(child)
        try:
            result = original_execute(self, context)
        finally:
            stack.pop()
        if child:
            assert result == {'FINISHED'}, result
            assert before and before <= mesh_pointers(), 'Primary Mesh did not survive'
            assert set(m._PREPARED_SESSIONS) == sessions, 'Child spawned a prepared dialog'
            evidence['children'].append(sorted(result))
        return result

    def async_prepare(self, *args, **kwargs):
        if self.group_child:
            evidence['async_children'] += 1
        return original_async(self, *args, **kwargs)

    def discover(*args, **kwargs):
        if stack and stack[-1]:
            evidence['child_discovery'] += 1
        return original_discover(*args, **kwargs)

    def resolve(scene):
        # Both provider completion and the primary final pass must see providers.
        available = sum(x.get('unity_material_guid') == material_guid for x in bpy.data.materials)
        evidence['final_resolvers'].append(available)
        return original_resolve(scene)

    def select(self, context, event):
        self.prefab_choice = 'PREFAB_1'
        return self.execute(context)

    def together(self, context, event):
        self.import_action = 'TOGETHER'
        return self.execute(context)

    m.UNITYPACKAGE_OT_import.execute = execute
    m.UNITYPACKAGE_OT_import._start_async_prepare = async_prepare
    m.discover_siblings = discover
    m.resolve_after_import = resolve
    m.UNITYPACKAGE_OT_import_prefab.invoke = select
    m.UNITYPACKAGE_OT_import_siblings.invoke = together
    addon.register()

    def verify():
        assert evidence['children'] == [['FINISHED']], evidence
        assert not evidence['async_children'] and not evidence['child_discovery'], evidence
        assert evidence['final_resolvers'] and all(evidence['final_resolvers']), evidence
        roots = [o for o in bpy.data.objects if o.get('_vapb_renderer_occurrences')
                 and o.get('unity_composition_member_id') == '2' * 32]
        assert len(roots) == 1
        selected_root = roots[0]
        records = json.loads(selected_root['_vapb_renderer_occurrences'])['records']
        assert len(records) == 1 and records[0]['source_key']['renderer_file_id'] == 102
        natives = [o for o in bpy.data.objects if o.type == 'MESH'
                   and o.get('_vapb_root_context_id') == selected_root['_vapb_root_context_id']
                   and o.get('_vapb_fbx_source_asset_guid') == fbx_guid]
        assert len(natives) == 1
        obj = natives[0]
        record = records[0]
        authored_package = record['materials']['0']['source_package_id']
        source_data = obj.data
        source_materials = tuple(source_data.materials)
        assert source_data.users > 1
        obj.data = source_data.copy()
        assert obj.data.users == 1
        bpy.context.scene.vapb_renderer_root = selected_root
        bpy.context.scene.vapb_renderer_mesh = obj
        occurrence_id = record['occurrence_id']
        surface = _material_plan(record, obj)[0]
        assert surface.get('unity_source_package_id') != authored_package
        original_slots = tuple((slot.link, slot.material) for slot in obj.material_slots)
        original_binding = obj.get('_vapb_renderer_binding')
        def rejected_confirmation():
            try:
                result = bpy.ops.vapb.confirm_renderer_binding(occurrence_id=occurrence_id)
                assert result == {'CANCELLED'}, result
            except RuntimeError as exc:
                assert '素材を一意に特定' in str(exc), str(exc)
            assert tuple((slot.link, slot.material) for slot in obj.material_slots) == original_slots
            assert obj.get('_vapb_renderer_binding') == original_binding
        original_file_id = surface['unity_material_file_id']
        surface['unity_material_file_id'] = '999999'
        try:
            try:
                _material_plan(record, obj)
                raise AssertionError('Wrong local ID resolved')
            except BindingError:
                pass
            rejected_confirmation()
        finally:
            surface['unity_material_file_id'] = original_file_id
        competing = surface.copy()
        competing['unity_source_package_id'] = 'competing-package'
        try:
            try:
                _material_plan(record, obj)
                raise AssertionError('Ambiguous cross-package provider resolved')
            except BindingError:
                pass
            rejected_confirmation()
            competing['unity_source_package_id'] = authored_package
            assert _material_plan(record, obj)[0] == competing, 'Local provider was not preferred'
        finally:
            bpy.data.materials.remove(competing)
        assert bpy.ops.vapb.confirm_renderer_binding(occurrence_id=occurrence_id) == {'FINISHED'}
        assert tuple(source_data.materials) == source_materials, 'Source template material changed'
        surface = obj.material_slots[0].material
        assert surface.get('unity_source_package_id') != authored_package
        assert obj.get('_vapb_renderer_binding')
        assert surface.get('unity_material_guid') == material_guid
        provider_package = surface.get('unity_source_package_id')
        bsdf = next(n for n in surface.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
        mix = bsdf.inputs['Base Color'].links[0].from_node
        image = mix.inputs['Color2'].links[0].from_node.image
        assert image.get('unity_guid') == image_guid
        assert selected_root.get('unity_asset_path') == 'Assets/PrefabB.prefab'
        assert not m._PREPARED_SESSIONS, m._PREPARED_SESSIONS
        blend_path = root/'confirmed.blend'
        bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
        bpy.ops.wm.open_mainfile(filepath=str(blend_path))
        confirmed = [o for o in bpy.data.objects if o.type == 'MESH' and o.get('_vapb_renderer_binding')]
        assert len(confirmed) == 1
        assert confirmed[0].material_slots[0].material.get('unity_source_package_id') == provider_package
        assert str(confirmed[0].material_slots[0].material.get('unity_material_file_id')) == str(original_file_id)
        print('GROUP_IMPORT_E2E_OK', evidence, flush=True)
        addon.unregister()
        temp.cleanup()

    result = bpy.ops.import_scene.unitypackage(filepath=str(geometry), prefab_choice='PREFAB_1', keep_extracted=False)
    if bpy.app.background:
        assert result == {'FINISHED'}, result
        verify()
    else:
        assert result == {'RUNNING_MODAL'}, result
        deadline = time.perf_counter()+30
        def wait_done():
            try:
                if evidence['children'] and not m._PREPARED_SESSIONS:
                    verify()
                    bpy.ops.wm.quit_blender()
                    return None
                assert time.perf_counter()<deadline, 'Foreground group did not finish'
                return .2
            except Exception:
                import traceback
                traceback.print_exc()
                sys.stdout.flush(); sys.stderr.flush()
                # Exit only this isolated test process with a failing result.
                import os
                os._exit(1)
        bpy.app.timers.register(wait_done, first_interval=.3)


if __name__ == '__main__':
    main()
