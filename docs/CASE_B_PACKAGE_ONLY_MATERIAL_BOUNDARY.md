# Case B: package-only model Material boundary (2026-09-27)

This is a sanitized finding from local commercial data. No asset, path, raw
log, screenshot, GUID, or fileID from that corpus is included. It does not
claim full Avatar fidelity or VRChat round-trip success.

## Decision

**Package-only proof for the two model-source base Material rows: NOT PROVEN.**
The source FBX proves each target Mesh's local Material connection and slot,
but the Package does not provide an authoritative join from its
Unity-generated Renderer/Material subasset IDs to the FBX Model/Material UIDs.
Do not assign these rows by name, suffix, order, appearance, or a single
remaining candidate. This is a boundary for this source revision and the
permitted evidence, not a claim that package-only reconstruction can never
be developed.

The two affected Prefab occurrences each contain **one explicit serialized
Material override reference**. A disposable Unity 2022.3.22f1 Oracle project
confirmed that each reference equals its expanded Prefab Renderer
`sharedMaterials[0]`. Thus the effective Prefab Material reference is present
in the Package. The missing package-only proof is the bridge from that source
Renderer to the correct native FBX Object. Before the B-QA-002 repair, a
separate unresolved override also marked both projected rows `UNKNOWN`,
withholding those explicit references even with the optional model witness.
That unrelated invalidation is now removed; the package-only identity gap
remains.

## Evidence classification

| Evidence | Class | Finding |
| --- | --- | --- |
| Source Package and split provider inventory | PROVEN | The source Package has 2 FBXs, 8 Prefabs, and no `.mat` asset; the separate provider has 58 `.mat` assets. |
| Raw FBX graph for the two target models | PROVEN | Each FBX Model has one Material connection and a single `LayerElementMaterial` local index (`AllSame`, `IndexToDirect`). This proves local FBX structure only. |
| Both source ModelImporter `.meta` files | PROVEN | `externalObjects` is `{}` and `internalIDToNameTable` is `[]`. No provider Material GUID token occurs in the source FBX or its meta. |
| Target Prefab modifications | PROVEN | Each selected occurrence has one Material GUID and signed local fileID override pointing to an asset in the provider Package. |
| Unity public API after importing both Packages | PROVEN, Unity-only | All 8 Prefabs loaded. For both target Renderer occurrences, the expanded `sharedMaterials[0]` identity equals the serialized override. The source ModelImporter external-object map has zero entries. |
| Unity public API on the original-revision model | PROVEN, Unity-only | Both original Renderers have generated internal Material subassets with the source FBX GUID and nonzero local fileIDs. Those Material fileIDs do not equal the raw FBX Material UIDs and occur in neither model meta nor relevant Prefab text. |
| VAPB projection before B-QA-002 repair | PROVEN | Two model-source rows had one explicit Material reference each, yet were `UNKNOWN`; one unrelated `UNRESOLVED_OVERRIDE` targeted the same model asset but neither of these two Renderer IDs. Their native slots retained FBX Materials without Unity Material provenance. |
| Reconstructing Unity's generated subasset IDs from this Package alone | UNKNOWN | No documented package field or verified package-only algorithm establishes the required join. Absence from the inspected fields is not a mathematical impossibility proof. |
| Joining by Material name, `.001`, basename, order, visual match, or candidate count | REJECTED | These are diagnostic cues, not authoritative identity. Unity's documented Material search can use naming, but that does not satisfy this product's identity requirement. |
| A uniquely connected FBX Material implies a unique external Unity Material | REJECTED | The FBX edge identifies an internal FBX Material, while the external GUID and Unity-generated subasset fileID are separate identities. |
| A future public-API Material identity witness could bridge the gap | INFERRED | Such a sidecar would need an exact-revision, independently validated Material-subasset-to-FBX-Material identity proof. The current optional model witness does **not** carry or assert that Material mapping. |

Unity documents [`GetExternalObjectMap`](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/AssetImporter.GetExternalObjectMap.html)
as the importer remap map, and
[`TryGetGUIDAndLocalFileIdentifier`](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/AssetDatabase.TryGetGUIDAndLocalFileIdentifier.html)
as the public way to observe Unity-generated asset IDs. Unity's
[`materialName`](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/ModelImporter-materialName.html)
setting can drive a name search; VAPB does not promote that search to
identity authority.

## User-facing support boundary

- Package-only Import remains automatic where serialized Renderer, Mesh,
  occurrence, and Material identity are complete and unique.
- For a binary model whose generated Renderer/Mesh IDs are absent from Package
  evidence, the optional **exact-revision model witness** can bridge those IDs
  to native FBX Objects. Unity is not a required dependency for other Imports.
- The existing witness does not prove an FBX internal Material UID to Unity
  Material subasset ID mapping. When no serialized override can be safely
  bound, keep the base Material unresolved and explain the need for manual
  confirmation or a future exact-revision Material identity witness.
- Here the two effective Prefab overrides are serialized. With an exact model
  witness they now bind to their native Object slots despite the unrelated
  unresolved override. Without that witness, the source Renderer-to-native
  Object identity remains unproven and the binding stays withheld.

## Installed-ZIP QA

The exact runtime from `901cc9ad7ea169a629ce50abfda27de209be29b8`
was built by the repository distribution builder, installed into isolated
Blender 5.2.1 user resources, enabled, used for private Import, saved, closed,
and reopened in a new Blender process. Local screenshots and `.blend` files
remain outside Git.

| Scenario | Import and reopen observation |
| --- | --- |
| Case B, no witness | 125 Mesh Objects; 141 actual Material slots, zero with Unity Material GUID or image node; one unresolved model source. A visible garment cohort had 0/7 and 0/14 slots with image nodes. |
| Case B, exact model witness | 112 Material slots with Unity GUID and 105 with image nodes; the same visible garment cohorts had 7/7 and 14/14 image nodes. Two model-source rows and their native slots remain unresolved. |
| Case B, direct visual check | The two isolated target Meshes rendered solid white with their saved Materials. In an **unsaved temporary scene**, assigning the two Unity-confirmed serialized Materials made the render visibly textured. The saved QA `.blend` and private originals were not modified by that comparison. |
| Case A normal control, no witness | 103 Mesh Objects; 147/148 slots with Unity Material GUID and 144 image nodes, unchanged after reopen. The single remaining slot was not classified as a regression. |

The actual Blender window, Outliner, and Material Properties were captured
locally. Case B had 2,110 Empty Objects and one `GameObject_`-style placeholder;
no literal `\\u` escape name was counted. Whether every Empty is useful is
not proven by counts alone. All 63 visible Material image paths existed after
reopen and their pixels could be read. The Material Preview still showed
magenta surfaces after 60 seconds, while an isolated offline render of a
garment appeared dark. The cause of the preview discrepancy remains unknown;
it is not evidence of missing image files.

## Exploratory QA findings at the original `901cc9a` checkpoint

| Bug ID / severity | Steps | Expected | Observed | Reproducibility / evidence | Suspected subsystem | Production data modified |
| --- | --- | --- | --- | --- | --- | --- |
| B-QA-001 / High | Install ZIP cleanly; Import split source and provider without witness; save and reopen. | Bind Materials where identity is proven; explain unresolved identity and the required user action elsewhere. | Visible garment cohort remained without texture/provenance, despite provider assets being present. | 1/1 fresh Import and 1/1 new-process reopen; private aggregate report and local visual inspection. | Binary model occurrence identity and Import guidance. | No |
| B-QA-002 / High | Repeat with exact model witness; inspect the two model-source rows and save/reopen. | Explicit, independently proven overrides bind if the target is safe; otherwise show a specific unresolved reason. | Both serialized references match the Unity Oracle, but both rows remain `UNKNOWN` after an unrelated unresolved override and their native slots remain white. | 1/1 fresh Import and 1/1 new-process reopen; private projection, public-API Oracle, and unsaved visual comparison. | Occurrence projection's override invalidation and material dependency planning. | No |
| B-QA-003 / Medium, root cause unknown | Open the saved witness-assisted scene in Blender 5.2.1 Material Preview; wait 60 seconds. | Material Preview reflects the available image-backed Materials. | Some surfaces stayed magenta despite 63/63 referenced image paths existing and readable pixels; an isolated garment offline render was not magenta. | 2 GUI captures in an isolated installation, including a 60-second warm-up; local images only. | Viewport Material Preview or material-node presentation; unproven. | No |

## B-QA-002 focused repair and QA

The proven cause was the `project_occurrences` branch for a Material override
whose source Renderer GUID/fileID matched **zero** child records. It changed
every child record's `material_status` to `UNKNOWN`, including independent
Renderers with exact overrides. The witness dependency planner then skipped
both. The repair marks only matching records unknown; a missing target still
emits `UNRESOLVED_OVERRIDE` and gains no Material dependency. An invalid
Material reference for a matching Renderer still marks that Renderer unknown.
No name, order, or candidate-count match was added.

A public synthetic model with three Renderer occurrences reproduced the old
failure: two valid overrides and one invalid Renderer Material reference were
all `UNKNOWN` after another unmatched override on the same model source.
This was observed RED before the change. Afterward, the first two were
`PARTIAL` with exact serialized overrides, the third remained `UNKNOWN`, and
the unmatched override remained an issue. Wrong Renderer ID, Material ID,
package, source revision, and ambiguous native candidate controls did not
produce an unintended binding. In Blender 5.2.1, the two valid dependencies
bound separate actual Object Material slots; the third stayed empty after
save, process exit, reopen, and re-resolution.

With the repaired code and exact model witness, private Case B yielded 112
previously bound dependencies plus the two target model-source dependencies:
**114/114 BOUND and 114/114 actual Object-slot identity matches** after
Import, save/reopen in a fresh Blender process, and another resolve. Both
target slots had image nodes. The unrelated `UNRESOLVED_OVERRIDE` count
remained one. The exact-code installed ZIP had 114 Unity-GUID slots and 107
image-node slots across 141 Mesh Material slots, up from 112 and 105 at the
original checkpoint. Object and Mesh counts stayed 2,247 and 125 under the
same installed-ZIP QA path. A local render of the two saved target slots
showed texture detail instead of the previous solid white result. The actual
Blender GUI opened the ZIP-generated `.blend` and showed the target Material
Properties and Outliner; its Material Preview was still compiling shaders at
capture time, so full preview stability is not claimed.

The normal Case A control retained 147/148 Unity-GUID Material slots and 144
image-node slots after a fresh installed-ZIP Import and new-process reopen.
Full public Python suite: 363 PASS; `compileall` PASS; focused integration,
model-instance, group-import, effective-member Material, late Object-slot,
and the new three-Renderer Blender probe PASS. Private assets, identity lists,
screenshots, and raw logs remain outside Git.

An exploratory comparison found a separate dependency-registry status drift:
after reopening and explicitly re-resolving, `MATERIAL_TEXTURE` entries marked
BOUND fell from 243 to 102 in both the prior Alpha scene and the repaired
scene; 141 entries became UNRESOLVED. The three non-witness Material
`MISSING_CONSUMER` entries were also present in both scenes. The 114 witnessed
Object-slot bindings and the 107 image-node slots on Mesh Objects remained
intact in the repaired scene. **B-QA-004 / Medium, root cause unknown:** reopen
the installed-ZIP Case B scene and explicitly re-resolve dependencies;
expected stable dependency status, observed the same texture-status drift in
old and new revisions (1/1 of each). Evidence is a private aggregate count;
suspected subsystem is texture dependency re-resolution. No original asset
was modified. This is tracked separately from B-QA-002.

**Next action:** Investigate B-QA-001's no-witness Import guidance so users
can identify the unresolved model identity and the exact action required,
while keeping automatic binding fail-closed.
