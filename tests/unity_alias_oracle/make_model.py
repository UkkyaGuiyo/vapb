"""Generate a first-party two-Renderer FBX for a public-safe Unity oracle."""
import sys
from pathlib import Path
import bpy

output = Path(sys.argv[sys.argv.index("--") + 1])
output.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
for label, offset in (("R1", -1.5), ("R2", 1.5)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(offset, 0, 0))
    bpy.context.object.name = label
bpy.ops.export_scene.fbx(filepath=str(output), use_selection=False,
                         add_leaf_bones=False, path_mode="STRIP")
assert output.is_file() and output.stat().st_size > 0
print("SYNTHETIC_FBX_READY")
