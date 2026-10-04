"""FBX import wrapper preserving Blender's native armature/weight/shape-key path."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, Iterable
from uuid import uuid4

import bpy  # type: ignore

from .fbx_receipt import import_with_receipts


def import_fbx(
    path: Path,
    use_custom_props: bool = True,
    source_package_id: str = "",
    source_asset_guid: str = "",
) -> list[bpy.types.Object]:
    before = set(bpy.data.objects)
    def native_import() -> None:
        bpy.ops.import_scene.fbx(
            filepath=str(path),
            use_manual_orientation=False,
            use_custom_normals=True,
            use_image_search=False,
            use_anim=True,
            use_custom_props=use_custom_props,
            ignore_leaf_bones=False,
            automatic_bone_orientation=False,
            use_prepost_rot=True,
        )

    import_with_receipts(path, native_import, source_asset_guid, bpy)
    imported = [obj for obj in bpy.data.objects if obj not in before]
    for obj in imported:
        obj["unity_source_fbx"] = str(path)
        if source_package_id:
            obj["unity_source_package_id"] = source_package_id
    return imported


def import_fbx_files(
    paths: Iterable[Path],
    source_package_id: str = "",
    progress: Callable[[Path, int, int, bool], None] | None = None,
    source_asset_guids: dict[str, str] | None = None,
    file_results: list[dict] | None = None,
) -> list[bpy.types.Object]:
    imported: list[bpy.types.Object] = []
    paths = list(paths)
    for index, path in enumerate(paths, 1):
        status = "FAILED"
        object_count = 0
        source_guid = ""
        try:
            if progress is not None:
                progress(path, index, len(paths), True)
            source_guid = (source_asset_guids or {}).get(str(path.resolve()), "")
            objects = import_fbx(path, source_package_id=source_package_id, source_asset_guid=source_guid)
            object_count = len(objects)
            status = "IMPORTED" if object_count else "NO_OBJECTS"
            imported.extend(objects)
        except (OSError, RuntimeError) as exc:
            print(f"[UnityPackage Importer] FBX import failed: {path}: {exc}")
        finally:
            if file_results is not None:
                file_results.append({
                    "asset_name": path.name,
                    "asset_guid": source_guid,
                    "status": status,
                    "object_count": object_count,
                })
            if progress is not None:
                progress(path, index, len(paths), False)
    return imported


def summarize_fbx_results(file_results: Iterable[dict]) -> dict[str, int]:
    """Summarize successful per-file imports without counting attempted files as imported."""
    results = list(file_results)
    imported_count = sum(item.get("status") == "IMPORTED" for item in results)
    return {
        "total": len(results),
        "imported": imported_count,
        "failed": len(results) - imported_count,
    }


FBX_IMPORT_CONTEXT_SCHEMA_VERSION = 1


def _validated_contexts(value):
    if (not isinstance(value, dict)
            or value.get("schema_version") != FBX_IMPORT_CONTEXT_SCHEMA_VERSION
            or not isinstance(value.get("contexts"), list)):
        raise ValueError("FBX_IMPORT_CONTEXTS_INVALID")
    contexts = value["contexts"]
    seen_ids = set()
    for context in contexts:
        if (not isinstance(context, dict)
                or not isinstance(context.get("context_id"), str) or not context["context_id"]
                or context["context_id"] in seen_ids
                or not isinstance(context.get("source_package_id"), str)
                or not isinstance(context.get("package_sha256"), str)
                or any(type(context.get(key)) is not int or context[key] < 0
                       for key in ("total", "imported", "failed"))
                or context["total"] != context["imported"] + context["failed"]
                or not isinstance(context.get("files"), list)):
            raise ValueError("FBX_IMPORT_CONTEXTS_INVALID")
        seen_ids.add(context["context_id"])
        legacy = context["context_id"] == "legacy"
        if not legacy:
            if len(context["files"]) != context["total"]:
                raise ValueError("FBX_IMPORT_CONTEXTS_INVALID")
        file_imported = 0
        for item in context["files"]:
            if (not isinstance(item, dict)
                    or (not legacy and (not isinstance(item.get("asset_name"), str)
                                        or not isinstance(item.get("asset_guid"), str)))
                    or item.get("status") not in {"IMPORTED", "FAILED", "NO_OBJECTS"}
                    or type(item.get("object_count")) is not int or item["object_count"] < 0):
                raise ValueError("FBX_IMPORT_CONTEXTS_INVALID")
            if ((item["status"] == "IMPORTED") != (item["object_count"] > 0)):
                raise ValueError("FBX_IMPORT_CONTEXTS_INVALID")
            file_imported += item["status"] == "IMPORTED"
        if not legacy and file_imported != context["imported"]:
            raise ValueError("FBX_IMPORT_CONTEXTS_INVALID")
    return contexts


def summarize_fbx_import_contexts(scene) -> tuple[dict[str, int], bool]:
    """Read versioned per-import history; return (aggregate, valid)."""
    if scene.get("unitypackage_fbx_context_invalid") is True:
        return {"total": 0, "imported": 0, "failed": 0}, False
    raw = scene.get("unitypackage_fbx_import_contexts")
    if raw is None:
        total = scene.get("unitypackage_fbx_count", 0)
        imported = scene.get("unitypackage_fbx_imported_count")
        failed = scene.get("unitypackage_fbx_failed_count")
        if type(total) is not int or total < 0:
            return {"total": 0, "imported": 0, "failed": 0}, False
        if imported is None or failed is None:
            imported, failed = (0, total) if total else (0, 0)
        if (type(imported) is not int or type(failed) is not int
                or imported < 0 or failed < 0 or imported > total or failed > total):
            return {"total": 0, "imported": 0, "failed": 0}, False
        if total != imported + failed:
            imported, failed = 0, total
        return {"total": total, "imported": imported, "failed": failed}, True
    try:
        value = json.loads(raw) if isinstance(raw, str) else raw
        contexts = _validated_contexts(value)
    except (TypeError, ValueError):
        return {"total": 0, "imported": 0, "failed": 0}, False
    return {
        "total": sum(item["total"] for item in contexts),
        "imported": sum(item["imported"] for item in contexts),
        "failed": sum(item["failed"] for item in contexts),
    }, True


def record_fbx_import_context(scene, source_package_id: str, package_sha256: str,
                              file_results: Iterable[dict]) -> dict:
    """Append this Package attempt and preserve all earlier per-file outcomes."""
    raw_contexts = scene.get("unitypackage_fbx_import_contexts")
    if raw_contexts is None:
        contexts = []
        legacy_total = scene.get("unitypackage_fbx_count", 0)
        legacy_imported = scene.get("unitypackage_fbx_imported_count")
        legacy_failed = scene.get("unitypackage_fbx_failed_count")
        if (legacy_total != 0 or legacy_imported is not None or legacy_failed is not None):
            if type(legacy_total) is not int or legacy_total < 0:
                scene["unitypackage_fbx_context_invalid"] = True
                raise ValueError("FBX_IMPORT_CONTEXTS_INVALID")
            if legacy_imported is None or legacy_failed is None:
                # Older/incomplete scene metadata cannot prove which attempts
                # succeeded. Preserve the attempt count as unresolved failures.
                legacy_imported, legacy_failed = 0, legacy_total
            if (type(legacy_imported) is not int or type(legacy_failed) is not int
                    or legacy_imported < 0 or legacy_failed < 0
                    or legacy_imported > legacy_total or legacy_failed > legacy_total):
                scene["unitypackage_fbx_context_invalid"] = True
                raise ValueError("FBX_IMPORT_CONTEXTS_INVALID")
            if legacy_total != legacy_imported + legacy_failed:
                legacy_imported, legacy_failed = 0, legacy_total
            raw_files = scene.get("unitypackage_fbx_import_results", "[]")
            try:
                legacy_files = json.loads(raw_files) if isinstance(raw_files, str) else list(raw_files)
            except (TypeError, ValueError) as exc:
                scene["unitypackage_fbx_context_invalid"] = True
                raise ValueError("FBX_IMPORT_CONTEXTS_INVALID") from exc
            if not isinstance(legacy_files, list):
                scene["unitypackage_fbx_context_invalid"] = True
                raise ValueError("FBX_IMPORT_CONTEXTS_INVALID")
            contexts.append({
                "context_id": "legacy",
                "source_package_id": str(scene.get("unitypackage_source_package_id", "")),
                "package_sha256": str(scene.get("unitypackage_package_sha256", "")),
                "total": legacy_total, "imported": legacy_imported,
                "failed": legacy_failed, "files": legacy_files,
            })
    else:
        try:
            raw_value = json.loads(raw_contexts) if isinstance(raw_contexts, str) else raw_contexts
            contexts = _validated_contexts(raw_value)
        except (TypeError, ValueError) as exc:
            scene["unitypackage_fbx_context_invalid"] = True
            raise ValueError("FBX_IMPORT_CONTEXTS_INVALID") from exc

    files = []
    for item in file_results:
        if (not isinstance(item, dict) or not isinstance(item.get("asset_name"), str)
                or not isinstance(item.get("asset_guid", ""), str)
                or item.get("status") not in {"IMPORTED", "FAILED", "NO_OBJECTS"}
                or type(item.get("object_count")) is not int or item["object_count"] < 0):
            scene["unitypackage_fbx_context_invalid"] = True
            raise ValueError("FBX_IMPORT_CONTEXTS_INVALID")
        if ((item["status"] == "IMPORTED") != (item["object_count"] > 0)):
            scene["unitypackage_fbx_context_invalid"] = True
            raise ValueError("FBX_IMPORT_CONTEXTS_INVALID")
        files.append({"asset_name": item["asset_name"], "asset_guid": item.get("asset_guid", ""),
                      "status": item["status"], "object_count": item["object_count"]})

    current = summarize_fbx_results(files)
    context = {
        "context_id": uuid4().hex,
        "source_package_id": source_package_id,
        "package_sha256": package_sha256,
        **current,
        "files": files,
    }
    contexts.append(context)
    value = {"schema_version": FBX_IMPORT_CONTEXT_SCHEMA_VERSION, "contexts": contexts}
    scene["unitypackage_fbx_import_contexts"] = json.dumps(value, sort_keys=True)
    scene["unitypackage_fbx_context_invalid"] = False
    aggregate = {
        key: sum(item[key] for item in contexts)
        for key in ("total", "imported", "failed")
    }
    scene["unitypackage_fbx_count"] = aggregate["total"]
    scene["unitypackage_fbx_imported_count"] = aggregate["imported"]
    scene["unitypackage_fbx_failed_count"] = aggregate["failed"]
    scene["unitypackage_fbx_import_results"] = json.dumps(files, sort_keys=True)
    return context


def apply_import_options(
    imported_objects: Iterable[bpy.types.Object],
    use_armatures: bool = True,
    use_bone_weights: bool = True,
    use_shape_keys: bool = True,
) -> list[bpy.types.Object]:
    """Apply the optional data filters after native FBX import.

    The FBX importer itself does not expose separate switches for all three
    data types in Blender 4.2.  The default path leaves the imported data
    untouched; explicit unchecked options remove only the corresponding data
    from the newly imported objects.
    """
    imported = list(imported_objects)
    mesh_objects = [obj for obj in imported if obj.type == "MESH"]
    if not use_bone_weights:
        for obj in mesh_objects:
            for vertex_group in list(obj.vertex_groups):
                obj.vertex_groups.remove(vertex_group)
            for modifier in list(obj.modifiers):
                if modifier.type == "ARMATURE":
                    obj.modifiers.remove(modifier)
    if not use_shape_keys:
        for obj in mesh_objects:
            if not obj.data.shape_keys:
                continue
            bpy.ops.object.select_all(action="DESELECT")
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
            try:
                bpy.ops.object.shape_key_remove(all=True)
            except RuntimeError as exc:
                print(f"[UnityPackage Importer] Shape Key removal skipped for {obj.name}: {exc}")
    if not use_armatures:
        for obj in imported:
            if obj.type == "ARMATURE":
                bpy.data.objects.remove(obj, do_unlink=True)
        imported = [obj for obj in imported if obj.type != "ARMATURE"]
    return imported
