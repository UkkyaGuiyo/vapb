"""Late texture arrival must use the same normalized tint as initial build."""

import json
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from unitypackage_blender_importer.blender.dependency_resolver import _bind_texture


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    material = bpy.data.materials.new("SyntheticTintedMaterial")
    material.use_nodes = True
    material["unity_material_guid"] = "a" * 32
    material["unity_source_package_id"] = "synthetic-package"
    material["unity_normalized"] = json.dumps({"base_color": [0.2, 0.4, 0.6, 1.0]})
    material["unity_props"] = json.dumps({"colors": {"_BaseColor": [0.2, 0.4, 0.6, 1.0]}})
    image = bpy.data.images.new("SyntheticTexture", width=1, height=1)
    image["unity_guid"] = "b" * 32
    record = {
        "consumer_asset_guid": "a" * 32,
        "consumer_package_id": "synthetic-package",
        "texture_label": "Base Color",
        "texture_ref": {"property_name": "_MainTex", "guid": "b" * 32},
    }
    assert _bind_texture(record, image)
    mix = material.node_tree.nodes.get(f"Unity Base Color Mix {material.name}")
    assert mix is not None
    actual = tuple(mix.inputs[1].default_value)
    assert all(abs(a - b) < 1e-6 for a, b in zip(actual, (0.2, 0.4, 0.6, 1.0))), actual
    print("LATE_TEXTURE_TINT=PASS")


if __name__ == "__main__":
    main()
