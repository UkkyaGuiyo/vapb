# HOLMES-20261012-12 - active Shape evaluated deformation

PRODUCT_PROGRESS: no new source capability; the existing owned Shape-return result is now verified as evaluated geometry at its current saved pose, beyond stored buffer equality. This is one new native API measurement, not full GUI/VRC/rendered-client acceptance.

Same protected11 Authored.blend, DeletedShapeGreenOutput.unitypackage and existing11 Variant used directly. No export, Apply/reApply, source/product edit, default reset or pose reset. Blender evaluated_get/to_mesh world capture preserves active[1,0]; actual Unity instance preserves[100,0]. Eight CPs map to26 native vertices using the already-frozen11 exact CP marker correspondence, with current mesh GUID/fileID/FBX bytes and unbaked vertices equal to11. No distance/name matching establishes identity.

Existing contract fixed before measurement: tests/blender_geometry_abcd_compare.py Unityworld->Blenderworld[-x,-z,y], actual BakeMesh(true)+renderer.TransformPoint; POSITION_TOLERANCE3e-5m from tests/geometry_abcd_metrics.py. Existing CPU equation includes current effective single100frame Shape displacement before sum(weight*boneWorld*bindpose*point). Full actual renderer transform retained, including nonuniform scale. Bakefalse captured as existing diagnostic only, not selected as a replacement acceptance criterion.

PASS: Blender evaluated to actual BakeMesh(true) maximum distance4.826228243321671e-7m; CPU effective skin to BakeMesh(true)2.6987150723151616e-7m. Active Shape retained, no reset to force agreement. All originalsourceFBX/Material/meta, editedFBX/meta and existingVariant/meta eight files are byte-exact against pre-Editor baseline and after measurement; protected blend/package hash bindings exact. Product Finalizer hash equals11 native evidence.

Observation corrections retained: initial Blender script aborted beforegeometry on unneeded literalIdentity-pose assumption; actual imported basis error1.6292068494294654e-7, source unchanged. Revised launcher folder substitution accidentally renamed executable, so no process started; restored exact existing basename. Revised observer records actual pose without mutating it. These are observer/precondition errors, not product failures. Native measurement occurred once; normal exit0, ownedchildren absent, Project lock absent and sharedmutex returned. No otherEditor stop/lock deletion.

Blender5.2.1/Unity2022.3.22f1. Source code unchanged, distribution ZIP older unchanged. GUI/VRC/renderedvisual/animation playback/multi-client/otherposes NOT_RUN. Existing body/Shape evaluation only. No purchased/private corpus or raw private logs in Git.

Verification self-review uses existing standard APIs/point metric; no independent product code-review requested because no product change. Prior11 user-requested guard code review KEEP is separately saved at62afe2cce6d98b41352b930499939b3b62a3624f; no repeated review. Primary actualmodel/reasoning unavailable; next fresh12 inference requestedSOL/xhigh only after exactremote readback.

NEXT_ACTION:normal allowedbranch evidence commit/push exactreadback -> one fresh12 inference -> one verified approved nextminimum. Ordinary proof/save does not stop continuousVAPB.

KNOWLEDGE_REPORT (shared Atlas update NOT_SAVED; existing shared checkout read-only ownership):
- Problem: an imported pose was wrongly required to equal a literal Identity matrix before geometry observation.
- Observation: basis differed by1.63e-7 while actual evaluated cross-application geometry matched within4.83e-7m.
- Cause: extra exact-matrix precondition confused import floating precision with the needed saved-pose contract.
- Correction: capture the unchanged actual pose and measure the intended output using a predeclared physical geometry tolerance.
- Reusable rule: do not reset imported state or require exact Identity unless the approved requirement specifically requires it; retain initial failure and input/hash bindings.
- Evidence/limitations: confirmed in one owned static active-Shape case; no universal transform/pose/runtime guarantee.
