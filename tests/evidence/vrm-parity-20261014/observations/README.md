# Preliminary native observations, 2026-10-14

First-party synthetic data only. These records are authoring-source persistence and G1 generic-glTF observations, **not V0/R0 or Unity restoration**. No private project, purchased mesh, native host path or raw process log is included. Runtime Blend/FBX/GLB/Unity Project/logs remain local and untracked.

| Record | Meaning |
| --- | --- |
| authoring.json | Actual newly authored Blender source capture, not converter expectations |
| reopened.json | Native source capture from a separate Blender process after reopening the saved Blend |
| gltf-observation.json | Native before/after G1 scene capture, including the additional returned mesh; observer's NOT_JUDGED label is historical capture status |
| gltf-header.json | Actual GLB JSON chunk; no binary payload or external URI |
| root-primary-geometry-check.json | Root independent UV-face/corner join and explicit additional-mesh limitation |
| INDEPENDENT_REVIEW.md | Independent saved-array judgment and bounded mutation checks |

Pinned Blender 5.2.1 LTS build `9e2066aef7ef`, bundled glTF generator `Khronos glTF Blender I/O v5.2.40`. Authoring code/fixture and G1 observer are in the parent directory; authoring uses repository `export/fbx_export.py` at base `b18e5e66bbcc0e22e9309ef9744f069b7f94fcbf`. All scripts are first-party GPL-3.0-or-later test code. No third-party exporter algorithm was copied or inspected.

Reproduction is resource-gated, not an instruction to launch against someone else's session. First verify fresh real RAM/process/owner/lease/lock/mutex and obtain an owned session as prescribed by ABC. Run the installed pinned Blender in a new owned background process with factory startup; empty only that process's scene, then execute `../make_fixture.py -- NEW_SOURCE_FOLDER`. The script refuses occupied output or nonempty source scenes. In a separate newly owned process open `NEW_SOURCE_FOLDER/Source.blend`, capture the same native source fields, and compare vertices/faces/UV/face_materials/weights/bone_rest/shapes with authoring.json. This reopen used the same bpy fields as the authoring snapshot, with no save; no general launcher was created.

For G1, in another newly owned process open that exact Source.blend and execute `../gltf_control.py -- NEW_G1_FOLDER`. The observer declares exact export/import options; outputs must be fresh, Source hash unchanged. Compare observed complete UV-face sets to select the primary mesh, not diagnostic names or indices. Keep unmatched scene objects separately unresolved. Corner joining uses unchanged exact UV signatures, position/shape comparisons use world frames, and weights require independent structural bone correspondence. Recomputed tangent equality is not imported-tangent retention. See independent review and linked reports for remaining observation gaps and measured changes.

AI_CLI process totals: authoring 10.3603092 s, source reopen 3.1745649 s, G1 5.4161095 s. These include startup and are not owner timings, UI action counts, installation cost or isolated converter duration. Source SHA256s and actual G1 loss/unknowns are in [ABC](../../../../docs/evidence/vrm-parity-20261014/ABC_COMPARISON_REPORT.md) and [format assessment](../../../../docs/evidence/vrm-parity-20261014/VRM_GLTF_REUSE_ASSESSMENT.md). Detailed SoulFlame research remains gated on actual requested ABC results.
