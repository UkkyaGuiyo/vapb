"""GI-001..007: synthetic split import in background or a fresh foreground UI."""
from pathlib import Path
import base64
import sys
import tempfile
import time

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import unitypackage_blender_importer as addon
from unitypackage_blender_importer.tests.blender_cross_package_dependency_test import package, material, make_fbx
from unitypackage_blender_importer.operators import import_unitypackage as m


def prefab(fbx_guid, material_guid):
    return f"""%YAML 1.1
--- !u!1 &1001
GameObject:
  m_Name: Coat
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
        obj = next(o for o in bpy.data.objects if o.type=='MESH' and o.get('unity_prefab_file_id')=='1001')
        surface = obj.data.materials[0]
        assert surface.get('unity_material_guid') == material_guid
        bsdf = next(n for n in surface.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
        mix = bsdf.inputs['Base Color'].links[0].from_node
        image = mix.inputs['Color2'].links[0].from_node.image
        assert image.get('unity_guid') == image_guid
        assert 'PrefabB.prefab' in obj.get('unity_asset_path',''), obj.get('unity_asset_path')
        assert not m._PREPARED_SESSIONS, m._PREPARED_SESSIONS
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
