"""Public Blender regression for class1001 Model source extraction and placement."""

from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from unitypackage_blender_importer.tests.blender_cross_package_dependency_test import make_fbx, package


MODEL = "a" * 32
UNRELATED = "b" * 32
ROOT = "1" * 32
NESTED = "2" * 32


def prefab(source: str, ids: tuple[int, ...], *, override: bool = False) -> bytes:
    return ("%YAML 1.1\n" + "".join(
        f"""--- !u!1001 &{instance_id}
PrefabInstance:
  m_SourcePrefab: {{fileID: 100100000, guid: {source}, type: 3}}
  m_Modification:
    m_TransformParent: {{fileID: 0}}
{f'''    m_Modifications:
    - target: {{fileID: -20, guid: {source}, type: 3}}
      propertyPath: m_Materials.Array.data[0]
      value:
      objectReference: {{fileID: 0}}
''' if override else ''}
""" for instance_id in ids
    )).encode()


def run_case(folder: Path, *, nested: bool, auto: bool = False, direct_renderer: bool = False) -> None:
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    source_fbx = make_fbx()
    root_prefab = prefab(NESTED if nested else MODEL, (701,) if nested else (701, 702),
                         override=not nested)
    if direct_renderer:
        root_prefab += f"""--- !u!1 &10
GameObject:
  m_Name: Direct
  m_Component:
  - component: {{fileID: 20}}
  - component: {{fileID: 30}}
--- !u!33 &30
MeshFilter:
  m_GameObject: {{fileID: 10}}
  m_Mesh: {{fileID: 4300000, guid: {MODEL},
    type: 3}}
--- !u!23 &20
MeshRenderer:
  m_GameObject: {{fileID: 10}}
""".encode()
    records = [(ROOT, "Assets/Root.prefab", root_prefab)]
    if nested:
        records.append((NESTED, "Assets/Nested.prefab", prefab(MODEL, (801,))))
    records.extend([
        (MODEL, "Assets/Chosen.fbx", source_fbx),
        (UNRELATED, "Assets/Unrelated.fbx", source_fbx),
    ])
    source = folder / ("DirectAndModel.unitypackage" if direct_renderer else "Both.unitypackage" if auto else "Nested.unitypackage" if nested else "Direct.unitypackage")
    package(source, records)
    result = bpy.ops.import_scene.unitypackage(
        filepath=str(source), import_mode="RECONSTRUCT",
        prefab_choice="AUTO" if auto else "PREFAB_1" if nested else "PREFAB_0",
        keep_extracted=False,
    )
    assert result == {"FINISHED"}, result
    scene = bpy.context.scene
    assert scene["unitypackage_fbx_count"] == 1, scene["unitypackage_fbx_count"]
    copies = [obj for obj in bpy.data.objects if obj.type == "MESH" and obj.get("_vapb_model_instance_edge_path")]
    expected = 2 if auto or not nested else 1
    assert len(copies) == expected, (nested, len(copies))
    paths = [json.loads(obj["_vapb_model_instance_edge_path"]) for obj in copies]
    assert len({tuple(step["prefab_instance_file_id"] for step in path) for path in paths}) == expected
    assert sorted(len(path) for path in paths) == ([1, 2] if auto else [2] if nested else [1, 1])
    assert all(obj.parent and obj.parent.get("_vapb_model_instance_edge_path") for obj in copies)
    assert all(not obj.hide_get() for obj in copies)
    assert all(not obj.hide_render for obj in copies)
    assert all(obj.get("_vapb_fbx_source_asset_guid") == MODEL for obj in copies)
    templates = [obj for obj in bpy.data.objects if obj.type == "MESH" and obj.get("_vapb_fbx_source_asset_guid") == MODEL and not obj.get("_vapb_model_instance_edge_path")]
    assert len(templates) == (2 if direct_renderer else 1)
    assert sum(obj.hide_get() and obj.hide_render for obj in templates) == 1
    if direct_renderer:
        assert sum(not obj.hide_get() and not obj.hide_render for obj in templates) == 1


def main() -> None:
    import unitypackage_blender_importer as addon
    addon.register()
    try:
        with tempfile.TemporaryDirectory(prefix="vapb_model_instance_") as temporary:
            folder = Path(temporary)
            run_case(folder, nested=False)
            run_case(folder, nested=True)
            run_case(folder, nested=True, auto=True)
            run_case(folder, nested=False, direct_renderer=True)
    finally:
        addon.unregister()
    print("MODEL_INSTANCE_CORE_OK")


if __name__ == "__main__":
    main()
