"""Execute the actual import Material assignment helper without Blender startup."""
import ast
from pathlib import Path
from types import SimpleNamespace
import unittest


class Material(dict):
    def __init__(self, name, guid):
        super().__init__(unity_material_guid=guid)
        self.name = name


class MaterialNameAssignmentTests(unittest.TestCase):
    def test_unique_matching_name_is_not_an_asset_reference(self):
        source = Path(__file__).resolve().parents[1] / 'blender/material_builder.py'
        tree = ast.parse(source.read_text(encoding='utf-8-sig'))
        nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and
                 n.name in ('_material_maps', 'apply_materials_by_name')]
        # Annotations only need the names supplied by the normal module import.
        from typing import Iterable, Optional
        preview = Material('Body', '')
        unrelated = Material('Body', 'a' * 32)
        obj = SimpleNamespace(data=SimpleNamespace(materials=[preview]), get=lambda k: None)
        assignments = []
        namespace = dict(Iterable=Iterable, Optional=Optional,
                         bpy=SimpleNamespace(types=SimpleNamespace(Material=object, Object=object)),
                         strip_material_suffix=lambda n: n,
                         _assign_object_material=lambda *args: assignments.append(args))
        exec(compile(ast.Module(body=nodes, type_ignores=[]), str(source), 'exec'), namespace)
        namespace['apply_materials_by_name']([obj], [unrelated])
        self.assertEqual([], assignments, 'same name / sole candidate is not GUID/fileID evidence')
        self.assertIs(obj.data.materials[0], preview)

