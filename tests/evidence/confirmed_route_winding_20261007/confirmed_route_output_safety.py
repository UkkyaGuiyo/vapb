import os
from pathlib import Path


def canonical_path(path):
    """Normalize an output/input path, resolving existing parents and symlinks."""
    return os.path.normcase(str(Path(path).expanduser().resolve(strict=False)))


def validate_output_path(output_path, input_paths):
    output = Path(output_path)
    output_key = canonical_path(output)
    for input_path in input_paths:
        if input_path and canonical_path(input_path) == output_key:
            raise ValueError('OUTPUT_PATH_ALIASES_INPUT')
    return output


def resolve_product_package_root(repo_root):
    """Accept either a normal clone root or a checkout named unitypackage_blender_importer."""
    root = Path(repo_root).expanduser().resolve()
    candidate = root
    if not (candidate / '__init__.py').is_file():
        candidate = root / 'unitypackage_blender_importer'
    required = (candidate / '__init__.py', candidate / 'blender' / 'fbx_receipt.py',
                candidate / 'blender' / 'renderer_binding.py')
    if not all(path.is_file() for path in required):
        raise ValueError('PRODUCT_REPOSITORY_LAYOUT_INVALID')
    return candidate


def write_text_exclusive(output_path, content):
    """Create a new UTF-8 result file; fail rather than replacing an existing file."""
    with Path(output_path).open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(content)
