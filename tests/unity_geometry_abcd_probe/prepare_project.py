# SPDX-License-Identifier: GPL-3.0-or-later
"""Copy a proven public CP control into a NEW external Unity project."""
import argparse
import json
from pathlib import Path
import shutil


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("control", type=Path)
    parser.add_argument("project", type=Path)
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[2]
    project = args.project.resolve()
    if project.exists() or project == repo or repo in project.parents:
        raise SystemExit("NEW_EXTERNAL_PROJECT_REQUIRED")
    for folder in ("Assets/Editor", "Assets/VapbGeometry", "Packages", "ProjectSettings"):
        (project / folder).mkdir(parents=True, exist_ok=True)
    for name in ("Source.fbx", "Source.fbx.meta", "Stamped.fbx", "ControlPointManifest.json"):
        shutil.copy2(args.control / name, project / name)
    shutil.copy2(Path(__file__).parent / "Editor/VapbGeometryAbcd.cs", project / "Assets/Editor")
    shutil.copy2(args.control / "Source.fbx", project / "Assets/VapbGeometry/Model.fbx")
    shutil.copy2(args.control / "Source.fbx.meta", project / "Assets/VapbGeometry/Model.fbx.meta")
    dependencies = {"com.unity.formats.fbx": "5.1.1", "com.unity.modules.animation": "1.0.0", "com.unity.modules.jsonserialize": "1.0.0"}
    (project / "Packages/manifest.json").write_text(json.dumps({"dependencies": dependencies}), encoding="utf-8")
    (project / "ProjectSettings/ProjectVersion.txt").write_text("m_EditorVersion: 2022.3.22f1\n", encoding="utf-8")
    print("PUBLIC_ABCD_PROJECT_PREPARED")


if __name__ == "__main__":
    main()
