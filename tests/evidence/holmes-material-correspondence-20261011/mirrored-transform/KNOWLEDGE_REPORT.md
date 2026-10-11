# KNOWLEDGE_REPORT — negative determinant and rendered face orientation

Atlas remains explicitly read-only; this candidate is not claimed saved to the shared Atlas. Existing basis/scale, matrix-versus-world and graphics-device lessons were consulted. Search existing winding/determinant lessons before saving; merge if the cause is already covered.

Problem: classifying a reflected object as inside-out from the sign of world-space triangle cross versus outward normal can produce a false defect diagnosis.

Observation: one native static rectangular-box case with negative Object scale, positive nonuniform magnitudes and rotation preserved world corner positions, Material identity and inverse-transpose normals. The actual negative native Renderer determinant made raw world cross dot outward normal approximately -1. A known Cull Back Shader on an unchanged-Mesh/Transform observation-only clone rendered all outside face-center views and culled all inside views on a real graphics backend.

Cause: `cross(Ma,Mb)=det(M)*inverseTranspose(M)*cross(a,b)`. Geometric edge cross is a pseudovector; the outward shading normal uses inverse transpose. Negative determinant changes their raw sign relationship. Draw winding/culling may compensate independently of the stored index stream.

Correction: freeze world positions, inverse-transpose normal expectations, object/basis determinants and tolerances before observing the target. Record native matrix determinant/index order; assess determinant-aware mesh parity separately from actual raster front/back. Test the effective side with standard Renderer/Camera rendering, known culling, real graphics and original assets unchanged. Do not infer render PASS from analytic parity.

Reusable rule: a raw cross sign or 2D projected winding sign alone is insufficient to diagnose face inversion under negative transforms. Separate outward normal, local index orientation, actual Transform determinant, effective front-face policy and observed culling. Report observation Shader results separately from product Material appearance.

Evidence level: confirmed bounded native static case, Blender5.2.1 LTS/Unity2022.3.22f1/Direct3D11; exact six-face coverage and four captured-data rejection controls. No product correction was needed. Graphics-enabled batch mode exercised real Camera.Render/ReadPixels; Null graphics was excluded.

Limitations: one negative-axis static object without hierarchy, Skin, ShapeKeys or modifiers. No general guarantee for arbitrary pipelines/shaders, custom draw commands, instancing, additional reflection combinations or source Material appearance. Shader/camera probe does not prove whole-product fidelity.
