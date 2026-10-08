"""Confirm boundary regression; no Blender or Unity process is launched."""
import ast
import json
from pathlib import Path
from types import SimpleNamespace
import unittest

REPO = Path(__file__).resolve().parents[1]

class Mesh(dict):
    def __init__(self, faces):
        super().__init__(untouched=True)
        self.data = SimpleNamespace(materials=[None, None], users=1, library=None,
                                    polygons=faces)
        self.material_slots = [SimpleNamespace(link="DATA", material=None) for _ in range(2)]
        self.users_scene = [object()]
        self.library = None

class ConfirmMaterialFaceTests(unittest.TestCase):
    def run_confirm(self, uniform=False):
        # Same equal-count disjoint partition control as the saved diagnostic.
        corners = [((x, 0., 0.), (x, 1., 0.), (x, 0., 1.)) for x in (10., 11., 12., 13.)]
        # Blender partitions reverse the source's two groups, with equal counts.
        faces = [SimpleNamespace(material_index=i // 2, corners=c)
                 for i, c in enumerate(corners[2:] + corners[:2])]
        mesh = Mesh(faces)
        root = SimpleNamespace(library=None)
        materials = [dict(unity_source_package_id="synthetic",
                          unity_material_guid=char * 32, unity_material_file_id="2100000")
                     for char in "ab"]
        refs = {str(i): dict(source_package_id="synthetic", guid=m["unity_material_guid"],
                            file_id="2100000") for i, m in enumerate(materials)}
        if uniform:
            refs["1"] = refs["0"].copy()
        record = dict(occurrence_id="renderer", material_status="EXACT",
                      material_slot_count=2, materials=refs)
        tree = ast.parse((REPO / "operators/renderer_binding.py").read_text(encoding="utf-8-sig"))
        plan = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_material_plan")
        operator = next(n for n in tree.body if isinstance(n, ast.ClassDef)
                        and n.name == "VAPB_OT_confirm_renderer_binding")
        execute = next(n for n in operator.body if isinstance(n, ast.FunctionDef) and n.name == "execute")
        namespace = dict(json=json, BindingError=ValueError,
                         bpy=SimpleNamespace(data=SimpleNamespace(materials=materials, objects=[])),
                         projection_records=lambda r: [record],
                         validate_binding=lambda *args: {"scope": "already validated"},
                         _display_error=str)
        exec(compile(ast.Module(body=[plan, execute], type_ignores=[]), str(REPO / "operators/renderer_binding.py"), "exec"), namespace)
        reports = []
        operator_stub = SimpleNamespace(occurrence_id="renderer", report=lambda *r: reports.append(r))
        context = SimpleNamespace(mode="OBJECT", scene=SimpleNamespace(
            vapb_renderer_root=root, vapb_renderer_mesh=mesh, objects=[root, mesh]))
        result = namespace["execute"](operator_stub, context)
        return result, mesh, corners, materials

    def test_equal_count_reversed_partitions_do_not_receive_ordinal_materials(self):
        result, mesh, corners, materials = self.run_confirm()
        self.assertEqual(result, {"CANCELLED"})
        self.assertEqual(dict(mesh), {"untouched": True})
        self.assertTrue(all(s.material is None and s.link == "DATA" for s in mesh.material_slots))
        self.assertEqual([f.corners for f in mesh.data.polygons], corners[2:] + corners[:2])

    def test_uniform_material_assignment_is_independent_of_partition_order(self):
        result, mesh, _, materials = self.run_confirm(uniform=True)
        self.assertEqual(result, {"FINISHED"})
        self.assertTrue(all(s.material is materials[0] and s.link == "OBJECT" for s in mesh.material_slots))

if __name__ == "__main__":
    unittest.main()