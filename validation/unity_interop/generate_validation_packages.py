"""Build the synthetic Unity interoperability packages and expected manifest."""

from __future__ import annotations

import argparse
import base64
import json
from pathlib import Path

from unitypackage_blender_importer.export.package_writer import UnityPackageWriter
from unitypackage_blender_importer.export.staging import StagedUnityAsset, StagingTree


FBX_GUID = "1" * 32
TEXTURE_A_GUID = "2" * 32
TEXTURE_B_GUID = "3" * 32
MATERIAL_A_GUID = "4" * 32
MATERIAL_B_GUID = "5" * 32
MATERIAL_C_GUID = "6" * 32
PREFAB_GUID = "7" * 32
FOLDER_GUID = "8" * 32
BINARY_GUID = "9" * 32
PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=")


def meta(guid: str, *, folder: bool = False) -> bytes:
    return f"fileFormatVersion: 2\nguid: {guid}\nfolderAsset: {'yes' if folder else 'no'}\n".encode("ascii")


def material(guid: str, texture_guid: str) -> bytes:
    return (f"%YAML 1.1\n--- !u!21 &2100000\nMaterial:\n  m_Name: Synthetic_{guid[:4]}\n"
            f"  m_Shader: {{fileID: 46, guid: 0000000000000000f000000000000000, type: 0}}\n"
            "  m_SavedProperties:\n    m_TexEnvs:\n    - _MainTex:\n"
            f"        m_Texture: {{fileID: 2800000, guid: {texture_guid}, type: 3}}\n").encode("ascii")


def prefab() -> bytes:
    return ("%YAML 1.1\n--- !u!1 &100\nGameObject:\n  m_Name: VAPBValidationRoot\n"
            "--- !u!4 &101\nTransform:\n  m_GameObject: {fileID: 100}\n  m_Father: {fileID: 0}\n"
            "--- !u!137 &102\nSkinnedMeshRenderer:\n  m_GameObject: {fileID: 100}\n"
            f"  m_Mesh: {{fileID: 4300000, guid: {FBX_GUID}, type: 3}}\n"
            f"  m_Materials:\n  - {{fileID: 2100000, guid: {MATERIAL_A_GUID}, type: 2}}\n").encode("ascii")


def build_tree(fbx_bytes: bytes) -> StagingTree:
    entries = [
        StagedUnityAsset(FBX_GUID, "Assets/VAPBValidation/VAPBValidation.fbx", fbx_bytes, meta(FBX_GUID), asset_type="Model"),
        StagedUnityAsset(TEXTURE_A_GUID, "Assets/VAPBValidation/TextureA.png", PNG, meta(TEXTURE_A_GUID), asset_type="Texture2D"),
        StagedUnityAsset(TEXTURE_B_GUID, "Assets/VAPBValidation/TextureB.png", PNG[::-1], meta(TEXTURE_B_GUID), asset_type="Texture2D"),
        StagedUnityAsset(MATERIAL_A_GUID, "Assets/VAPBValidation/MaterialA.mat", material(MATERIAL_A_GUID, TEXTURE_A_GUID), meta(MATERIAL_A_GUID), asset_type="Material"),
        StagedUnityAsset(MATERIAL_B_GUID, "Assets/VAPBValidation/MaterialB.mat", material(MATERIAL_B_GUID, TEXTURE_B_GUID), meta(MATERIAL_B_GUID), asset_type="Material"),
        StagedUnityAsset(MATERIAL_C_GUID, "Assets/VAPBValidation/MaterialC_Patched.mat", material(MATERIAL_C_GUID, TEXTURE_B_GUID), meta(MATERIAL_C_GUID), asset_type="Material"),
        StagedUnityAsset(PREFAB_GUID, "Assets/VAPBValidation/VAPBValidation.prefab", prefab(), meta(PREFAB_GUID), asset_type="Prefab"),
        StagedUnityAsset(FOLDER_GUID, "Assets/VAPBValidation", b"", meta(FOLDER_GUID, folder=True), asset_type="Folder"),
        StagedUnityAsset(BINARY_GUID, "Assets/VAPBValidation/Preserved.bytes", b"\x00\x01synthetic\xff", meta(BINARY_GUID), asset_type="Binary"),
    ]
    return StagingTree(entries)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fbx", type=Path, required=True)
    parser.add_argument("--mutation-fbx", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    fbx_bytes = args.fbx.read_bytes()
    mutation_bytes = args.mutation_fbx.read_bytes()
    args.output.mkdir(parents=True, exist_ok=True)
    writer = UnityPackageWriter()
    for name, payload in (("VAPBValidation_baseline.unitypackage", fbx_bytes), ("VAPBValidation_vertex_mutation.unitypackage", mutation_bytes)):
        destination = args.output / name
        if destination.exists():
            destination.unlink()
        writer.write(build_tree(payload), destination)
    manifest = {
        "schema": "vapb-unity-interoperability-validation-1",
        "source_guid": FBX_GUID,
        "cases": [
            {"case_id": "RAW_PACKAGE_COMPATIBILITY", "expected": ["GUID_DIRECTORY", "ASSET", "ASSET_META", "PATHNAME", "UTF8", "FOLDER_META", "BINARY_BYTES"]},
            {"case_id": "MATERIAL_DEPENDENCY", "expected": {"MaterialA": TEXTURE_A_GUID, "MaterialB": TEXTURE_B_GUID, "MaterialC_Patched": TEXTURE_B_GUID}},
            {"case_id": "MODEL_BASELINE", "expected": ["ARMATURE", "MESH", "WEIGHTS", "UV", "NORMALS", "SHAPE_KEY", "MATERIAL_SLOTS"]},
            {"case_id": "FBX_MUTATION_MATRIX", "variants": ["BASELINE", "VERTEX_POSITION_CHANGE", "TOPOLOGY_CHANGE", "MESH_RENAME", "HIERARCHY_CHANGE", "BONE_RENAME", "BONE_ADD", "BONE_REMOVE", "BLENDSHAPE_ADD", "BLENDSHAPE_RENAME", "BLENDSHAPE_REMOVE", "MATERIAL_SLOT_CHANGE", "DUPLICATE_MESH_NAME"]},
        ],
        "identity_fields": ["asset_guid", "serialized_local_file_id", "model_subasset_file_id", "prefab_occurrence_id", "runtime_instance_id"],
        "packages": ["VAPBValidation_baseline.unitypackage", "VAPBValidation_vertex_mutation.unitypackage"],
    }
    (args.output / "validation_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"GENERATED={args.output}")


if __name__ == "__main__":
    main()
