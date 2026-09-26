"""Unity TRS must undergo the same basis change for position, rotation and scale."""
from math import sqrt
from pathlib import Path
import sys

import bpy
from mathutils import Matrix, Quaternion, Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from unitypackage_blender_importer.blender.hierarchy_builder import build_prefab_hierarchy
from unitypackage_blender_importer.unity.prefab_parser import PrefabData, PrefabGameObject, PrefabTransform


def main():
    # Unity (x,y,z) becomes Blender (x,z,-y). The scale signs stay on their axes.
    basis = Matrix(((1, 0, 0, 0), (0, 0, 1, 0), (0, -1, 0, 0), (0, 0, 0, 1)))
    inverse = basis.inverted()
    cases = [
        ((1, 2, 3), (1, 0, 0, 0), (2, 3, 5)),
        ((-2, 1, 4), (sqrt(0.5), 0, sqrt(0.5), 0), (-2, 4, 0.5)),
        ((3, -1, 2), (sqrt(0.5), sqrt(0.5), 0, 0), (1, 0, 2)),
    ]
    transforms = {}
    unity_world = Matrix.Identity(4)
    expected = {}
    for index, (position, rotation, scale) in enumerate(cases, 1):
        transforms[100 + index] = PrefabTransform(
            100 + index, index, 100 + index - 1 if index > 1 else 0,
            dict(zip('xyz', position)), dict(zip('wxyz', rotation)), dict(zip('xyz', scale)))
        local = Matrix.LocRotScale(Vector(position), Quaternion(rotation), Vector(scale))
        unity_world = unity_world @ local
        expected[index] = (basis @ local @ inverse, basis @ unity_world @ inverse)
    prefab = PrefabData(Path('SyntheticScale.prefab'), [],
        {i: PrefabGameObject(i, f'Node_{i}') for i in expected}, transforms)
    root, objects = build_prefab_hierarchy(prefab, [])
    try:
        bpy.context.view_layer.update()
        for index, obj in objects.items():
            for actual, target in zip((obj.matrix_basis, obj.matrix_world), expected[index]):
                error = max(abs(actual[i][j] - target[i][j]) for i in range(4) for j in range(4))
                assert error < 1e-5, f'SEMANTIC_SCALE_BASIS_MISMATCH node={index} error={error}'
            if index > 1:
                assert obj.parent == objects[index - 1]
        print('SEMANTIC_SCALE_BASIS_PASS nodes=3 local_and_world_checks=6')
    finally:
        for obj in [*objects.values(), root]:
            bpy.data.objects.remove(obj, do_unlink=True)


if __name__ == '__main__':
    main()
