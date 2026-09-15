# BUG-003 Material and Texture Visual Construction Fix

## Goal and root cause

Restore a visible base texture signal in Blender Material Preview while preserving explicit material and texture references. The prior material node graph did not carry the sampled base texture through the final surface path. The correction connected Image Texture, the color operation, Principled BSDF Base Color, and Material Output Surface with an explicit UV input.

## Validation evidence

- Python unit tests: 41 passed.
- Blender 5.2.1 synthetic integration: passed, including the explicit UV link assertion.
- Real-package import: passed. Aggregate scene counts were 113 objects, 103 meshes, 4 armatures, and 40 shape keys.
- The imported scene contained 53 material datablocks, including 48 textured materials. All 48 textured materials had a linked Image Texture, Base Color, Surface, and explicit UV path.
- Fifteen material identities and 147 material-slot bindings were checked; texture identity mismatches were zero and binding signatures matched 147/147.

Asset names, GUIDs, local paths, and identity rows from the private validation package are deliberately omitted from the public history.
