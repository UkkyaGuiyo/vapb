"""Build and validate the installable addon ZIP from a git revision."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import subprocess
import tempfile
import zipfile


PACKAGE_ROOT = "unitypackage_blender_importer"
DOCS = (
    "PRODUCT_SPEC.md",
    "ARCHITECTURE.md",
    "TEST_STRATEGY.md",
    "TEST_RESULTS.md",
    "README.md",
    "CHANGELOG.md",
)


def git_files(repo: Path, revision: str) -> list[str]:
    result = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", revision, "--"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    files = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    runtime = [
        path for path in files
        if path.endswith(".py") and (
            "/" not in path
            or path.startswith(("blender/", "operators/", "ui/", "unity/"))
        )
    ]
    return runtime + [path for path in DOCS if path in files]


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
        for member in source_members:
            assert f"{PACKAGE_ROOT}/{member}" in names, member
        assert f"{PACKAGE_ROOT}/preferences.py" in names
        forbidden = (".unitypackage", ".blend", ".fbx", ".pem", ".key")
        assert not [name for name in names if name.lower().endswith(forbidden)]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--revision", default="HEAD")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    digest, count = build(args.repo.resolve(), args.revision, args.output.resolve())
    print(f"RUNTIME_MEMBERS={count}")
    print(f"SHA256={digest}")


if __name__ == "__main__":
    main()
