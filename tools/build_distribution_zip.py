"""Build and validate the installable addon ZIP from a git revision."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import re
import subprocess
import tempfile
import zipfile


PACKAGE_ROOT = "unitypackage_blender_importer"
DOCS = (
    "LICENSE",
    "LICENSES.md",
    "unity_editor/LICENSE",
    "PRODUCT_SPEC.md",
    "ARCHITECTURE.md",
    "TEST_STRATEGY.md",
    "TEST_RESULTS.md",
    "README.md",
    "CHANGELOG.md",
)
EXCLUDED_RUNTIME_PREFIXES = ("tests/", "tools/", "experiment_logs/")
UNITY_EXPORT_SUPPORT = (
    "unity_editor/VapbRealizationMarker.cs",
    "unity_editor/Editor/VapbReferenceFinalizer.cs",
    "unity_editor/Editor/VapbModelSkinFinalizer.cs",
)


def is_runtime_python(path: str) -> bool:
    """Tracked Python is runtime by default; only dev-only trees are excluded."""
    return path.endswith(".py") and not path.startswith(EXCLUDED_RUNTIME_PREFIXES)


def runtime_python_paths(paths: list[str]) -> set[str]:
    return {path for path in paths if is_runtime_python(path)}


def git_files(repo: Path, revision: str) -> list[str]:
    result = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", revision, "--"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    files = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    runtime = sorted(runtime_python_paths(files))
    return runtime + [path for path in (*UNITY_EXPORT_SUPPORT, *DOCS) if path in files]


def revision_sha(repo: Path, revision: str) -> str:
    return subprocess.run(
        ["git", "rev-parse", f"{revision}^{{commit}}"],
        cwd=repo, check=True, capture_output=True, text=True,
    ).stdout.strip()


def branch_name(repo: Path, revision: str) -> str:
    result = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=repo, check=True, capture_output=True, text=True,
    ).stdout.strip()
    if result:
        return result
    if revision.startswith("origin/"):
        return revision.removeprefix("origin/")
    return "detached"


def distribution_filename(repo: Path, revision: str) -> str:
    project = repo.name
    branch = re.sub(r"[^A-Za-z0-9._-]+", "-", branch_name(repo, revision)).strip("-") or "detached"
    return f"{project}_{branch}_{revision_sha(repo, revision)[:7]}.zip"


def build(repo: Path, revision: str, output: Path) -> tuple[str, int]:
    output.parent.mkdir(parents=True, exist_ok=True)
    members = git_files(repo, revision)
    with tempfile.TemporaryDirectory(prefix="unitypackage_archive_") as temp:
        archive = Path(temp) / "addon.zip"
        subprocess.run(
            [
                "git", "archive", "--format=zip", f"--output={archive}",
                f"--prefix={PACKAGE_ROOT}/", revision, "--", *members,
            ],
            cwd=repo,
            check=True,
        )
        output.write_bytes(archive.read_bytes())
    validate_zip(output, members)
    return hashlib.sha256(output.read_bytes()).hexdigest(), len(members)


def validate_zip(path: Path, source_members: list[str]) -> None:
    with zipfile.ZipFile(path) as archive:
        assert archive.testzip() is None
        names = set(archive.namelist())
        assert names
        assert all(name.startswith(f"{PACKAGE_ROOT}/") for name in names)
        source_runtime = runtime_python_paths(source_members)
        zip_runtime = {
            name.removeprefix(f"{PACKAGE_ROOT}/")
            for name in names
            if name.startswith(f"{PACKAGE_ROOT}/") and name.endswith(".py")
        }
        assert source_runtime == zip_runtime, (sorted(source_runtime - zip_runtime), sorted(zip_runtime - source_runtime))
        for member in source_members:
            assert f"{PACKAGE_ROOT}/{member}" in names, member
        assert f"{PACKAGE_ROOT}/preferences.py" in names
        forbidden = (".unitypackage", ".blend", ".fbx", ".pem", ".key")
        assert not [name for name in names if name.lower().endswith(forbidden)]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--revision", default="HEAD")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    repo = args.repo.resolve()
    revision = args.revision
    output = args.output
    if output is None:
        if args.output_dir is None:
            parser.error("one of --output or --output-dir is required")
        output = args.output_dir / distribution_filename(repo, revision)
    digest, count = build(repo, revision, output.resolve())
    print(f"REVISION={revision_sha(repo, revision)}")
    print(f"FILENAME={output.name}")
    print(f"RUNTIME_MEMBERS={count}")
    print(f"SHA256={digest}")


if __name__ == "__main__":
    main()
