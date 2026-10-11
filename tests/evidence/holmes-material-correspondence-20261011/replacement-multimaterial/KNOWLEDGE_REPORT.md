# KNOWLEDGE_REPORT

Shared Failure Atlas access is restricted to read-only in this task; this
anonymized candidate has not been synced or saved to that Atlas.

Problem: a package-reconstruction observation assumed exactly one imported Mesh
and stopped before an authorized full geometry replacement.
Observation: one owned synthetic import produced both source/technical and
composition Mesh objects. Canonical Unity Materials existed independently of
the imported Mesh slot placeholders.
Cause: the observation conflated scene Mesh count/slot population with asset
identity and the selected composition.
Correction: in the explicitly authorized disposable full-replacement copy,
remove all imported Mesh objects/data and select retained Materials using exact
package/GUID/signed fileID/provider evidence. Keep original files untouched.
Reusable rule: do not infer missing Materials or composition membership from
total scene Mesh count or old slot population alone.
Evidence level: reproduced observer precondition failure and successful bounded
replacement/export/native return; no product defect was established.
Limitations: this does not authorize deleting meshes in arbitrary scenes or
guessing Material providers, and does not generalize to multi-object Skin.
