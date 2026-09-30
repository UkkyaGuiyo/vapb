# SPDX-License-Identifier: GPL-3.0-or-later
"""Freeze Blender loop triangles only on disposable export Objects."""
from contextlib import contextmanager


@contextmanager
def frozen_export_meshes(objects, *, bpy_module=None):
    if bpy_module is None:
        import bpy as bpy_module
    staged = []
    try:
        for obj in objects:
            if obj.type != 'MESH':
                continue
            source = obj.data
            source.calc_loop_triangles()
            groups = [(group.name, group.lock_weight) for group in obj.vertex_groups]
            triangles = tuple(source.loop_triangles)
            loops = [index for tri in triangles for index in tri.loops]
            # Copy ID properties/material slots before rebuilding only topology.
            mesh = source.copy()
            staged.append((obj, source, mesh))
            obj.data = mesh
            if mesh.shape_keys:
                obj.shape_key_clear()
            mesh.clear_geometry()
            mesh.from_pydata([tuple(v.co) for v in source.vertices], [],
                             [tuple(t.vertices) for t in triangles])
            for layer in source.uv_layers:
                target = mesh.uv_layers.new(name=layer.name)
                target.active_render = layer.active_render
                for index, old in enumerate(loops):
                    target.data[index].uv = layer.data[old].uv
            mesh.uv_layers.active_index = source.uv_layers.active_index
            for face, tri in zip(mesh.polygons, triangles):
                face.material_index = source.polygons[tri.polygon_index].material_index
                # Original corner normals retain flat as well as smooth shading.
                face.use_smooth = True
            mesh.normals_split_custom_set([tuple(source.corner_normals[i].vector) for i in loops])
            obj.vertex_groups.clear()
            for name, locked in groups:
                obj.vertex_groups.new(name=name).lock_weight = locked
            for vertex in source.vertices:
                for influence in vertex.groups:
                    obj.vertex_groups[influence.group].add([vertex.index], influence.weight, 'REPLACE')
            if source.shape_keys:
                old_keys = list(source.shape_keys.key_blocks)
                keys = []
                for old in old_keys:
                    key = obj.shape_key_add(name=old.name)
                    for index, point in enumerate(old.data):
                        key.data[index].co = point.co
                    for field in ('value', 'slider_min', 'slider_max', 'mute', 'interpolation', 'vertex_group'):
                        setattr(key, field, getattr(old, field))
                    keys.append(key)
                for old, key in zip(old_keys, keys):
                    key.relative_key = keys[old_keys.index(old.relative_key)]
                mesh.shape_keys.use_relative = source.shape_keys.use_relative
                mesh.shape_keys.eval_time = source.shape_keys.eval_time
                for name in source.shape_keys.keys():
                    mesh.shape_keys[name] = source.shape_keys[name]
        bpy_module.context.view_layer.update()
        yield
    finally:
        for obj, source, mesh in reversed(staged):
            obj.data = source
            if mesh.users == 0:
                bpy_module.data.meshes.remove(mesh)


@contextmanager
def triangle_export_scene(context, objects, *, bpy_module=None):
    """Copy selected final state and remap its actual parent/Armature handles."""
    if bpy_module is None:
        import bpy as bpy_module
    bpy = bpy_module
    sources = tuple(objects)
    scene = bpy.data.scenes.new('VAPB Triangle Export')
    for field in ('system', 'system_rotation', 'scale_length'):
        setattr(scene.unit_settings, field, getattr(context.scene.unit_settings, field))
    mapping, data = {}, []
    try:
        for source in sources:
            copy = source.copy()
            mapping[source] = copy
            if source.type in {'MESH', 'ARMATURE'}:
                copy.data = source.data.copy()
                data.append(copy.data)
            scene.collection.objects.link(copy)
        for source, copy in mapping.items():
            world = source.matrix_world.copy()
            copy.parent = mapping.get(source.parent)
            copy.matrix_world = world
            for modifier in copy.modifiers:
                if modifier.type == 'ARMATURE' and modifier.object is not None:
                    if modifier.object not in mapping:
                        raise ValueError('export Armature is outside selected scope')
                    modifier.object = mapping[modifier.object]
        layer = scene.view_layers[0]
        with context.temp_override(scene=scene, view_layer=layer,
                                   selected_objects=list(mapping.values()),
                                   selected_editable_objects=list(mapping.values()),
                                   active_object=next(iter(mapping.values()), None),
                                   object=next(iter(mapping.values()), None)):
            for obj in mapping.values():
                obj.select_set(True)
            layer.objects.active = next(iter(mapping.values()), None)
            layer.update()
            with frozen_export_meshes(mapping.values(), bpy_module=bpy):
                layer.update()
                yield scene, tuple(mapping.values())
    finally:
        for obj in mapping.values():
            bpy.data.objects.remove(obj, do_unlink=True)
        for block in data:
            if block.users == 0:
                collection = bpy.data.meshes if isinstance(block, bpy.types.Mesh) else bpy.data.armatures
                collection.remove(block)
        bpy.data.scenes.remove(scene)
