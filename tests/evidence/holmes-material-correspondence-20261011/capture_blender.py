"""Read-only product import/Confirm capture for generated public packages. No export/save."""
import bpy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
sys.dont_write_bytecode = True


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo', type=Path, required=True)
    ap.add_argument('--work', type=Path, required=True)
    ap.add_argument('--select-cases', nargs='+', choices=['R','A','B','E','U','D'], default=['R','A','B'])
    args = ap.parse_args(sys.argv[sys.argv.index('--')+1:])
    spec = importlib.util.spec_from_file_location('unitypackage_blender_importer', args.repo/'__init__.py', submodule_search_locations=[str(args.repo)])
    addon = importlib.util.module_from_spec(spec); sys.modules[spec.name] = addon; spec.loader.exec_module(addon); addon.register()
    capture = load('holmes_existing_capture', args.repo/'tests/evidence/inbound-material-face-membership-20261007/capture_inbound_material_faces.py')
    manifest = json.loads((args.work/'cases/generation.json').read_text())
    if len(set(args.select_cases)) != len(args.select_cases):
        raise ValueError('duplicate case selection')
    for case in args.select_cases:
        output = args.work/(case+'-blender.json')
        if output.exists():
            raise ValueError('occupied capture')
        package = args.work/'cases'/(case+'.unitypackage')
        bpy.ops.wm.read_factory_settings(use_empty=True)
        if bpy.ops.import_scene.unitypackage(filepath=str(package), import_mode='RECONSTRUCT', prefab_choice='AUTO', source_storage_directory=str(args.work/('blender-sources-'+case))) != {'FINISHED'}:
            raise ValueError('product import failed')
        root, record, mesh = capture.exact_renderer_mesh(args.repo)
        if record['mesh']['source_sha256'] != manifest['cases'][case]['fbx_sha256']:
            raise ValueError('actual receipt hash differs')
        def complete():
            mesh.data.calc_loop_triangles()
            layer = mesh.data.uv_layers.active
            if layer is None:
                raise ValueError('active UV absent')
            rows = [dict(uv=[tuple(layer.data[i].uv) for i in tri.loops],
                         corners=[tuple(mesh.data.vertices[i].co) for i in tri.vertices],
                         normals=[tuple(mesh.data.corner_normals[i].vector) for i in tri.loops],
                         slot=mesh.data.polygons[tri.polygon_index].material_index) for tri in mesh.data.loop_triangles]
            return dict(mesh=capture.capture_mesh(mesh,root.matrix_world.inverted()@mesh.matrix_world), faces=rows)
        before = complete()
        bpy.context.scene.vapb_renderer_root=root; bpy.context.scene.vapb_renderer_mesh=mesh
        try:
            result=bpy.ops.vapb.confirm_renderer_binding(occurrence_id=record['occurrence_id']); error=''
        except RuntimeError as exc:
            result={'CANCELLED'}; error=str(exc)
        after=complete()
        if before != after or result != {'CANCELLED'}:
            raise ValueError('Confirm guard/nonmutation differs')
        report=dict(fbx_sha256=manifest['cases'][case]['fbx_sha256'],meta_sha256=manifest['meta_sha256'],
                    package_sha256=capture.sha256(package),blender_version=bpy.app.version_string,
                    faces=before['faces'],before=before,after=after,mesh_unchanged=True,
                    operator_result=sorted(result),operator_error=error,receipt=record)
        with output.open('x',encoding='utf-8') as stream:
            json.dump(report,stream,indent=2)
        print('HOLMES_BLENDER_CAPTURE',case,len(before['faces']))


if __name__ == '__main__':
    main()
