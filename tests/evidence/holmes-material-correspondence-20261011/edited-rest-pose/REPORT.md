# One posed edited-rest geometry

Project VAPB; HOLMES-20261012-16; branch feature/holmes-edited-rest-pose-20261012; basefc0da039f4a82f4fb76b5b7e59cf74add6cea67f.

BUILT: pose verification only, no product change. Reused exactly the saved13blend used by15 and the saved15linkedVariant. In Blender memory only, childUID529385132/parent44496282 receives basisZ rotation0.45rad. NativeUnity uses a temporary Variant instance and the same UID through frozen15 marker/source mapping. Actual Blender child worlddelta is converted through the existing global axis basis and originalRenderer/editedRenderer frame relation, then applied as checked localTRS. No export, Apply, Scene/Prefab save, clip creation, retargeting or repeat review.

Measured nonzero deformation: Blender0.4139510754017116m, Unity0.41395121812820435m. Blender evaluated8CP vs actualBakeMesh(true)26vertices maximum7.275674114068569e-07m; CPU vs Bake2.842839421323384e-07m, within existing frozen3e-5m. This exercises edited joint/rest deformation; it is not AnimationClip playback or a general Pose converter. LocalTRS reconstruction error5.960464477539063e-8 is diagnostic, not new production tolerance. Native mesh/GUID-fileID/CPmap/weights/sourcehelper/package linkage matches15. All93 preexisting Project/input/Variant/meta/Material/blend/package files retain hashes; temporary Unity objects/mesh destroyed and Blender memory discarded.

Observer failure retained: initial C# local worlddelta name collided with the reused Shape stream local (CS0136); measurement never ran. PID5196 exited1 with no children but a residual lock. Confirmed ownPID absent and lock readable with exclusive read access; no lock was deleted and no other Editor stopped. Only local variable renamed. Successful PID11136 start2026-10-12T06:20:50.2745241Z, exit2026-10-12T06:20:58.2896600Z, normal0; release2026-10-12T06:20:58.4602273Z, children/lock absent/sharedmutex released. All private original/corrected scripts/process/logs retained, public correction distinguishes compile failure from product behavior.

NOT_YET: GUI/VRC/renderedvisual, Animation/rest clips, extra poses, wholeproduct, distributionZIP current source. Existing formal Action and component gates unchanged.
NEXT_MINIMUM: saved evidence/exactremote readback -> fresh16 independent inference -> one alreadyapproved product action, preserve completed native/inference/review IDs.
Model: primary effective model/reasoning unavailable; policyLUNA/low. Completed15 fresh inference requestedSOL/xhigh/effectiveunknown; no independent product code review needed for unchanged16.
