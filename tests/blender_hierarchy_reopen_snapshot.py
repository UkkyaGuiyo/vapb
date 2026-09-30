"""Observe a reopened Scene using the same exact-input native comparator schema.

CLI: BLEND BASELINE_SNAPSHOT PACKAGE WITNESS SOURCE PUBLIC CONTROLS OUTPUT.
Baseline records normal Import; it supplies only asset locators, never live state.
"""
import hashlib
import json
from pathlib import Path
import sys

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from unitypackage_blender_importer.tests.blender_hierarchy_snapshot import snapshot
from unitypackage_blender_importer.tests.unity_hierarchy_probe.native_skin_observation import observe_native_skin


def main():
    blend, baseline_path, package, witness, source, public, controls, output = sys.argv[sys.argv.index('--')+1:]
    baseline = json.loads(Path(baseline_path).read_text())
    sha = hashlib.sha256(Path(package).read_bytes()).hexdigest()
    if baseline['package_sha256'] != sha or baseline['import_result'] != ['FINISHED']:
        raise ValueError('BASELINE_REVISION_OR_IMPORT_MISMATCH')
    bpy.ops.wm.open_mainfile(filepath=blend)
    observed = snapshot(sha, baseline['assets'], {'FINISHED'})
    observed['native_skin'] = observe_native_skin(bpy.context, package, witness, source, public, controls, pose_controls=True)
    Path(output).write_text(json.dumps(observed, indent=2), encoding='utf-8')
    print('HIERARCHY_REOPEN_SNAPSHOT_PASS')


if __name__ == '__main__':
    main()
