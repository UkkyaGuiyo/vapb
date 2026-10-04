"""Exercise authoritative ModelImporter material mappings in Blender."""

from __future__ import annotations

import tempfile
from pathlib import Path

import bpy

from unitypackage_blender_importer.blender.material_builder import apply_materials_by_name
from unitypackage_blender_importer.unity.asset_database import AssetDatabase


def run_case(meta_text: str, expected_replacement: bool) -> None:
    with tempfile.TemporaryDirectory(prefix="vapb_material_mapping_") as temp:
        root = Path(temp)
        source_fbx = root / "Model.fbx"
        source_fbx.write_bytes(b"synthetic")
        Path(str(source_fbx) + ".meta").write_text(meta_text, encoding="utf-8")

        mesh = bpy.data.meshes.new("SyntheticMesh")
        source_material = bpy.data.materials.new("Body")
        candidate_material = bpy.data.materials.new("Body.001")
        candidate_material["unity_material_guid"] = "a" * 32
        mesh.materials.append(source_material)
        obj = bpy.data.objects.new("SyntheticObject", mesh)
        bpy.context.scene.collection.objects.link(obj)
        obj["unity_source_fbx"] = str(source_fbx)
        db = AssetDatabase(root)

        try:
            apply_materials_by_name([obj], [candidate_material], asset_db=db)
            replaced = mesh.materials[0] is candidate_material
            assert replaced is expected_replacement, (
                f"expected_replacement={expected_replacement}, got={replaced}"
            )
            if not expected_replacement:
                assert mesh.materials[0] is source_material, "source FBX slot was not preserved"
        finally:
            bpy.data.objects.remove(obj, do_unlink=True)
            bpy.data.meshes.remove(mesh)
            bpy.data.materials.remove(source_material)
            bpy.data.materials.remove(candidate_material)


def main() -> None:
    explicit_missing = """externalObjects:
  - first:
      type: 23
      assembly: UnityEngine.CoreModule
      name: Body
    second: {fileID: 2100000, guid: 77777777777777777777777777777777, type: 2}
"""
    run_case(explicit_missing, expected_replacement=False)
    run_case("externalObjects: []\n", expected_replacement=True)
    print("MATERIAL_MAPPING_AUTHORITY_PASS explicit_missing_guid=preserved unmatched_name=fallback")


if __name__ == "__main__":
    main()
