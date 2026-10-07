"""Fail-closed loading of a selected source checkout into an embedded interpreter."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


def _cached_names(package_name: str) -> list[str]:
    prefix = package_name + "."
    return sorted(name for name in sys.modules
                  if name == package_name or name.startswith(prefix))


def load_source_package(root: Path, package_name: str = "unitypackage_blender_importer"):
    """Load a package only when neither its root nor descendants are already cached."""
    cached = _cached_names(package_name)
    if cached:
        raise ImportError("refusing cached package namespace: " + ", ".join(cached))

    package_file = root.resolve() / "__init__.py"
    if not package_file.is_file():
        raise FileNotFoundError(f"selected source root has no __init__.py: {package_file}")
    spec = importlib.util.spec_from_file_location(
        package_name, package_file, submodule_search_locations=[str(package_file.parent)])
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot create source spec for {package_file}")
    package = importlib.util.module_from_spec(spec)
    sys.modules[package_name] = package
    try:
        spec.loader.exec_module(package)
        selected_root = package_file.parent.resolve()
        for name in _cached_names(package_name):
            module = sys.modules[name]
            origin = getattr(module, "__file__", None)
            if not origin:
                raise ImportError(f"loaded source module has no file origin: {name}")
            module_path = Path(origin).resolve()
            if not module_path.is_relative_to(selected_root):
                raise ImportError(f"loaded source module escaped selected root: {name} ({module_path})")
        if Path(package.__file__).resolve() != package_file.resolve():
            raise ImportError("loaded package root differs from selected source file")
        return package
    except BaseException:
        for name in _cached_names(package_name):
            sys.modules.pop(name, None)
        raise
