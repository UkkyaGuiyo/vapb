# HOLMES-20261011-06: replacement Cube with four Unity Materials

ID HOLMES-20261011-06 / READY. Instruction source
**CHAT_FALLBACK_NOT_SAVED_TO_GITHUB**; no GitHub issuing commit.
Project VAPB, repository UkkyaGuiyo/vapb. Start branch
`feature/holmes-fresh-consumer-bootstrap-20261011`, SHA
`6c810a2bcaa9cf1589f5ddd596c2877fbe0a8f09`; isolated work branch
`feature/holmes-replacement-multimaterial-20261011`.
Actual runtime source/evidence result:
[dcda2f0c954d54ced5c7df0d2425dc73fecd4be5](https://github.com/UkkyaGuiyo/vapb/commit/dcda2f0c954d54ced5c7df0d2425dc73fecd4be5).
Global AGENTS actual reread SHA256:
`9BE8886133EEE50F5E24A5A183AF086EACDFEE41EBCF3D5AB0510907D34D6918`.
No HOLMES05 runtime or previous result review was rerun.

**VERIFIED_IN_SCOPE. H-A is supported for this bounded static Cube:** original
Mesh identity is unnecessary when final geometry and exact Unity Material recipe
identity are supplied. H-B dependency/refusal/misassignment was not observed in
this case. This is not a guarantee for arbitrary Avatars, Skin, components,
shaders, separate edited Variants or complete VAPB delivery.

## Source, editing and persistence

Actual Blender **5.2.1 LTS**, Unity **2022.3.22f1**.
The owned original OrderedSix package SHA256 is
`5492475a7231ba21d6f4c20308e2db84865df7e08770aa5c4bd9fd84f7064dcf`.
Normal VAPB RECONSTRUCT Import retains four canonical Unity Material datablocks
with exact package/GUID/signed fileID/provider bytes. Display names and old Mesh
slot membership are not Material identity evidence.

Within the expressly authorized working copy, both imported Mesh objects and
their Mesh datablocks were removed. Original package/files were not deleted.
A native Blender Cube primitive was created with standard UVs: six quads, eight
corners, no modifiers, no Skin, no parent. Its Object and Mesh custom-property
keys are empty before save, after reopen and after export. No old ModelUID,
GeometryUID, Mesh receipt, Renderer binding or source Mesh identity was copied.
See [replace.json](replace.json), [export.json](export.json).

Slots are R2, R0, R3, R1. Actual geometric normals and corner positions identify
the faces. Every Material has signed fileID `2100000` and the exact input-package
provider. The final saved Blender geometry is the truth:

| Geometric face | Material | Actual Unity Material GUID |
|---|---|---|
| +X | R0 | afd253dd071f7e5469e24392cdbf181c |
| -X | R1 | 70c1cb3bd3a723141a677eca237e252c |
| +Y, -Y | R2 | 242d369718abeb942873ec054737cf94 |
| +Z, -Z | R3 | 4d7af3be41387054c9f86b68e180d9e7 |

After save and normal exit, a separate Blender process reopened the blend and
verified equal six-face corners/normals/UV/Material refs, slots and transform.
The standard **VAPB UnityPackage (Blender final state)** operator
`export_scene.vapb_final_state_unitypackage` produced a new output. No switch to
the source-bound Mesh/Skin/Variant export route was made.

## Output transport and fresh Unity

Output package SHA256:
`ff8e0afc476227bbbbbf6ea161af3f2fa99a6bcf163787c7b1528b39790c6060`.
Generated FBX SHA256:
`032bf7a86f09db81fa48302a620dbb0a950b46916c301bbc261b6492ec80d053`.
Manifest SHA256:
`2d943cd105f61e100ad453995d5d69369574018dc349371efdd2be2b71ace069`.
The new `BUILD_EXPORTED_STATIC_V2` task carries a fresh Export Object ID,
four Export Material IDs, exact Unity GUID/fileID records and provider hashes.
[transport.json](transport.json) proves the Export Object ID in serialized FBX
and each serialized Material ID's exact recipe reference. Only the fresh Export
Object ID is transported as a VAPB Model custom property; no old Mesh receipt.
Original Material and .meta bytes are unchanged in the new package.

Owned fresh Unity Project initially had only one observation script, ProjectVersion
and four installed built-in module dependencies. No VAPB consumer/assets/cache
were preinstalled. See [prepared-initial-state.json](prepared-initial-state.json),
[initial.json](initial.json). The generated package alone entered via normal
ImportPackage. [events.json](events.json) separately records A Import start,
C completed compilation (Editor/runtime assemblies, errors 0), D reload,
B import-completed callback, E actual packaged Finalizer availability.

Existing packaged **`VapbFinalStateFinalizer.Apply`** was invoked explicitly and
returned true / `COMPLETE`. The observer never assigns any Material. The product
sets the new generated model's material-name/file-scale importer policy and
reimports it before resolving its carried identities. Consequently this new
model's .meta changes as designed; preserved source Material/meta are unchanged.
No original importer metadata or package C# was replaced.

The newly generated ordinary Prefab was absent before Apply. Actual Mesh GUID
`553e3f716f8d4021ac505801bb799770`, signed fileID `4493585093827132993`;
Prefab GUID `7ee928f828220b7409489b71b516a1d3`, fileID `3516536429446027305`;
Renderer fileID `412833565258211858`. Manifest and Finalizer script GUID/fileIDs
are captured in [native.json](native.json).

## Independent face comparison

Every actual native submesh topology/index/baseVertex stream, Mesh vertex/normal/UV
and Renderer Material GUID/fileID was captured. [judge_replacement.py](judge_replacement.py)
uses new Cube planes and corners rather than face ordinals, labels, old FBX face
UIDs or unique UV signatures. Raw FBX local corners exactly equal Blender Cube
corners. Native common mesh-local corners are explicitly
`(-x/fileScale, y/fileScale, z/fileScale)`, with captured fileScale
`0.009999999776482582`, bakeAxisConversion false and useFileScale true.
This is a bounded diagnostic frame, not a material-fitted axis permutation or a
world/physical-transform fidelity claim.

All native common corners exactly equal the cube's ±1 corners. Each native face
has a unique geometric source plane. Existing exact corner/edge coverage is
reused on each plane's 2D geometric projection: two triangles cover each quad,
four exterior edges occur once, one internal diagonal occurs twice with opposite
directions. Missing/duplicate triangles are rejected. Both FBX and Unity contain
12 triangles; all six faces carry the intended actual GUID/fileID.
Four Material-array entries alone are not the proof. See [judgment.json](judgment.json).

Projected local winding is FBX +1 and Unity -1. Oriented/culling/render fidelity
and full position/world-transform comparison remain NOT_RUN. UVs were captured
but were not used as mandatory face correspondence information.
Repeat explicit Apply returned true, left Prefab bytes unchanged and preserved
actual Material/Mesh references. A Unity normal reopen was not requested for06
and was not run; Blender normal reopen was run as requested.

## Failure, preservation and resources

First failed stage **BLENDER_PROVENANCE**, from the observer's incorrect assertion
that RECONSTRUCT exposes exactly one Mesh. The diagnostic traceback established
two imported Mesh objects. Both initial attempts stopped before replacement or
export. [first-observer-failure.json](first-observer-failure.json) preserves the
failure and the bounded observation correction. This was not a product defect:
the correction removed all Meshes only in the authorized working copy and selected
retained canonical Materials by exact package/GUID/fileID. No product fix,
guard weakening, speculative Material assignment or new regression was needed.

All native processes exited normally with code 0. Initial/diagnostic Blender
process exit 0 does not turn their captured FAIL results into PASS. Successful
replacement Blender PID24732 ran 12:57:56–12:57:59 UTC; separate reopen/export
PID15900 ran 12:58:19–12:58:22. Unity PID26856 ran
13:00:25.9913483–13:00:40.1615141 UTC, actual free RAM before launch 5.1183 GiB.
[run-summary.json](run-summary.json) records actual times, process/source hashes,
RAM, normal exits and ownership. Existing shared mutex/process/lease/RAM/lock gates
were retained, with the explicitly owned new off-pool Project and no fixed-root
lease claimed for a different Project. No other Editor stop or lock deletion.

At 13:01:22.3706675 UTC: process census no conflict, mutex available and probe
released, pool all FREE, own Project lock absent, RAM 5.3522 GiB. Resources returned.
All 12 frozen original hashes match. Product source and all old tracked evidence
remain unchanged from the base; original Scenes/settings were never edited.
No purchased/private assets, user paths, credentials or raw logs are published.
Public Capture.cs uses LF line endings; its contents equal the executed private
observer after line-ending normalization. The actual executed observer byte hash
is retained in the initial inventory and run-summary; its private source was not
changed for publication.

Actual product source SHA256:

- final_state_package.py: `8413dffbcb0c6de8a1e81ff6351b0198e5cfaa51c864c261dccdd2f31710dd59`
- VapbFinalStateFinalizer.cs: `b75c6a0e36be8e50c3f687bb289be58319b30852be7b91096e2e7a5c542bae11`
- VapbImportAssistant.cs: `236f6c7edecf4bf5e2971253db60628a628ada11d21d7153c20c2075e6fd47ad`

Primary actual model/reasoning settings unavailable; not inferred from AGENTS.
The independent new06 result review uses GPT-6.1 SOL / medium.
Last formal usage check: remaining94%; stop threshold <=5% remains applicable.
Independent new06 result review: **KEEP / VERIFIED_IN_SCOPE**, no blocking gap.
See [REVIEW.md](REVIEW.md). No product repair or additional native experiment is
warranted. Next minimum: report this bounded replacement result to the parent;
there is no remaining06 measurement blocker. Broader product scopes remain
unverified as listed above. An anonymized observer-precondition lesson is retained
in [KNOWLEDGE_REPORT.md](KNOWLEDGE_REPORT.md); shared Atlas remained read-only.
