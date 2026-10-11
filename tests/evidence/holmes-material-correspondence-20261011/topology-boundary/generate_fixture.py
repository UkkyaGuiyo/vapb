"""One self-authored four-polygon input; run once in the existing Blender."""
import bpy
import json
from pathlib import Path
import sys

out = Path(sys.argv[sys.argv.index('--') + 1])
if out.exists():
    raise RuntimeError('occupied fixture output')
bpy.ops.wm.read_factory_settings(use_empty=True)
vertices, faces = [], []
shapes = [(0, [(0, 0), (1, 0), (0, 1)]),
          (3, [(0, 0), (1, 0), (1, 1), (0, 1)]),
          (6, [(0, 0), (1, 0), (1, 1), (0, 1)]),
          (9, [(0, 0), (1, 0), (0, 1)])]
for offset, corners in shapes:
    start = len(vertices)
    vertices.extend((offset + x, y, 0) for x, y in corners)
    faces.append(tuple(range(start, len(vertices))))
mesh = bpy.data.meshes.new('MixedFourMesh')
mesh.from_pydata(vertices, [], faces)
mesh.update()
obj = bpy.data.objects.new('MixedFour', mesh)
bpy.context.collection.objects.link(obj)
for label in ['SyntheticMaterialA', 'SyntheticMaterialB']:
    mesh.materials.append(bpy.data.materials.new(label))
uv = mesh.uv_layers.new(name='ExactCornerFingerprint')
for p, (_, corners) in zip(mesh.polygons, shapes):
    p.material_index = [0, 1, 0, 1][p.index]
    for loop, (x, y) in zip(p.loop_indices, corners):
        uv.data[loop].uv = (p.index / 4 + x / 16, y / 16)
obj.select_set(True)
bpy.context.view_layer.objects.active = obj
bpy.ops.export_scene.fbx(filepath=str(out), use_selection=True, object_types={'MESH'},
                         use_triangles=False, bake_anim=False, add_leaf_bones=False,
                         path_mode='STRIP', embed_textures=False)
if [len(p.vertices) for p in mesh.polygons] != [3, 4, 4, 3]:
    raise RuntimeError('source polygon construction differs')
print(json.dumps({'result': 'GENERATED', 'blender': bpy.app.version_string,
                  'source_corner_counts': [3, 4, 4, 3]}))
