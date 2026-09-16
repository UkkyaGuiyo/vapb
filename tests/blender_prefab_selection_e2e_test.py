"""Blender-runtime regression for the dynamic Prefab selection handoff."""

from __future__ import annotations

import io
from pathlib import Path
import sys
import tarfile
import tempfile
from unittest.mock import patch

import bpy


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def add(archive, name: str, data: bytes) -> None:
    info = tarfile.TarInfo(name)
    info.size = len(data)
    archive.addfile(info, io.BytesIO(data))


def make_three_prefab_package(path: Path) -> None:
    with tarfile.open(path, "w:gz") as archive:
        for index, name in enumerate(("PrefabA", "PrefabB", "PrefabC")):
            guid = f"{index + 1:032x}"
            add(archive, f"{guid}/asset", b"%YAML 1.1\n")
            add(archive, f"{guid}/pathname", f"Assets/{name}.prefab".encode())
            add(archive, f"{guid}/asset.meta", f"guid: {guid}\n".encode())


def main() -> None:
    addon = __import__("unitypackage_blender_importer")
    addon.register()
    from unitypackage_blender_importer.operators import import_unitypackage as module
    from unitypackage_blender_importer.unity.package_reader import UnityPackageReader

    with tempfile.TemporaryDirectory(prefix="prefab_selection_") as temp:
        package = Path(temp) / "ThreePrefabs.unitypackage"
        make_three_prefab_package(package)
        index = UnityPackageReader(package).build_index()
        prefab_paths = [Path(record.unity_path) for record in index.records.values()]
        assert [path.name for path in prefab_paths] == ["PrefabA.prefab", "PrefabB.prefab", "PrefabC.prefab"]

        class PreparedOperator:
            def __init__(self):
                self._prefab_paths = prefab_paths
                self._prefab_items = [("AUTO", "Automatic", "", 0)] + [
                    (f"PREFAB_{i}", path.name, str(path), i + 1)
                    for i, path in enumerate(prefab_paths)
                ]
                self._selected_prefab_choice = None
                self.prefab_choice = "AUTO"
                self._sibling_discovery = None

            def _selected_prefab(self, paths):
                choice = self._selected_prefab_choice or self.prefab_choice
                if choice.startswith("PREFAB_"):
                    return paths[int(choice.split("_", 1)[1])]
                return paths[0]

            def _discover_selected_visual_dependencies(self):
                pass

        operator = PreparedOperator()
        operator._prefab_items = [("AUTO", "Automatic", "", 0)] + [
            (f"PREFAB_{i}", path.name, str(path), i + 1)
            for i, path in enumerate(prefab_paths)
        ]
        session_id = "synthetic-prefab-selection"
        module._PREPARED_SESSIONS[session_id] = module._PreparedSession(session_id, operator, 0.0)
        selector_proxy = type("SelectorProxy", (), {"session_id": session_id})()
        items = module._session_prefab_items(selector_proxy, None)
        assert [item[0] for item in items] == ["AUTO", "PREFAB_0", "PREFAB_1", "PREFAB_2"]
        with patch.object(module, "_schedule_prepared_session") as schedule:
            result = bpy.ops.import_scene.unitypackage_prefab(
                "EXEC_DEFAULT", session_id=session_id, prefab_choice="PREFAB_1"
            )
            assert result == {"FINISHED"}, result
        assert operator._selected_prefab_choice == "PREFAB_1"
        assert operator._selected_prefab(operator._prefab_paths) == Path("Assets/PrefabB.prefab")
        schedule.assert_called_once_with(session_id, show_dialog=False)
        module._PREPARED_SESSIONS.pop(session_id, None)

    addon.unregister()
    print("PREFAB_SELECTION_FOREGROUND_E2E_OK")


if __name__ == "__main__":
    main()
