"""Blender 5.2 persistence and panel probe for synthetic unresolved evidence.

Run twice, with ``-- <blend-path> write`` then ``-- <blend-path> read``.
"""

import json
from pathlib import Path
import sys
from types import SimpleNamespace

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import unitypackage_blender_importer as addon
from unitypackage_blender_importer.ui.import_outcome_panel import (
    VAPB_PT_import_outcome, scene_import_outcome,
)


class Layout:
    def __init__(self):
        self.labels = []

    def label(self, *, text, icon="NONE"):
        self.labels.append(text)

    def box(self):
        return self


def main():
    target, mode = sys.argv[sys.argv.index("--") + 1:]
    addon.register()
    try:
        assert VAPB_PT_import_outcome.bl_category == "VAPB Result"
        if mode == "write":
            root = bpy.data.objects.new("Synthetic import root", None)
            bpy.context.scene.collection.objects.link(root)
            root["_vapb_renderer_occurrences"] = json.dumps({
                "records": [],
                "issues": [{"code": "UNRESOLVED_SOURCE", "instance_edge_path": [{}]}],
            })
            bpy.context.scene["unitypackage_dependency_registry"] = json.dumps({
                "schema_version": 1,
                "dependencies": [{"dependency_type": "PREFAB_RENDERER_MATERIAL",
                                  "status": "MISSING_CONSUMER"}],
            })
        report = scene_import_outcome(bpy.context.scene)
        assert report["overall"] == "PARTIAL", report
        assert report["counts"]["UNRESOLVED_IDENTITY"] == 2, report
        assert report["counts"]["MISSING_DEPENDENCY"] == 0, report
        layout = Layout()
        VAPB_PT_import_outcome.draw(SimpleNamespace(layout=layout),
                                     SimpleNamespace(scene=bpy.context.scene))
        assert any("一部の復元を保留" in line for line in layout.labels), layout.labels
        assert "対象Objectは証拠だけでは特定できません" in "".join(layout.labels), layout.labels
        if mode == "write":
            bpy.ops.wm.save_as_mainfile(filepath=target)
        print("IMPORT_OUTCOME_PROBE_PASS:" + mode)
    finally:
        addon.unregister()


if __name__ == "__main__":
    main()
