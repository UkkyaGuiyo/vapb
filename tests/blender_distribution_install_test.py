"""Install, enable and disable a ZIP through Blender with isolated user paths."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tempfile

import bpy


def install_in_isolated_child(archive_path: Path) -> None:
    import addon_utils

    scripts = Path(os.environ['BLENDER_USER_SCRIPTS']).resolve()
    config = Path(os.environ['BLENDER_USER_CONFIG']).resolve()
    assert Path(bpy.utils.user_resource('SCRIPTS')).resolve() == scripts
    assert Path(bpy.utils.user_resource('CONFIG')).resolve() == config
    assert not (config / 'userpref.blend').exists()
    module = 'unitypackage_blender_importer'
    assert module not in sys.modules
    assert module not in bpy.context.preferences.addons
    assert bpy.ops.preferences.addon_install(filepath=str(archive_path), overwrite=False) == {'FINISHED'}
    assert bpy.ops.preferences.addon_enable(module=module) == {'FINISHED'}
    addon = sys.modules[module]
    assert Path(addon.__file__).resolve().is_relative_to(scripts)
    assert addon.PREFERENCES_CLASSES
    assert module in bpy.context.preferences.addons
    assert addon_utils.check(module) == (True, True)
    assert bpy.ops.preferences.addon_disable(module=module) == {'FINISHED'}
    assert module not in bpy.context.preferences.addons
    assert addon_utils.check(module) == (False, False)
    assert not (config / 'userpref.blend').exists()
    print('DIST_BLENDER_STANDARD_INSTALL_ENABLE_DISABLE_OK')


def main() -> None:
    if "--" not in sys.argv:
        raise SystemExit("usage: blender ... --python blender_distribution_install_test.py -- ZIP")
    archive_path = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
    assert archive_path.is_file()
    if '--isolated-child' in sys.argv[sys.argv.index('--') + 2:]:
        install_in_isolated_child(archive_path)
        return
    with tempfile.TemporaryDirectory(prefix="unitypackage_install_") as temp:
        install_root = Path(temp)
        env = os.environ.copy()
        for suffix in ('CONFIG', 'SCRIPTS', 'DATAFILES', 'EXTENSIONS'):
            isolated = install_root / suffix.lower()
            isolated.mkdir()
            env['BLENDER_USER_' + suffix] = str(isolated)
        env['BLENDER_USER_RESOURCES'] = str(install_root)
        env.pop('PYTHONPATH', None)
        subprocess.run([
            bpy.app.binary_path, '--background', '--factory-startup', '--disable-autoexec',
            '--python-exit-code', '1', '--python', str(Path(__file__).resolve()),
            '--', str(archive_path), '--isolated-child',
        ], cwd=install_root, env=env, check=True)


main()
