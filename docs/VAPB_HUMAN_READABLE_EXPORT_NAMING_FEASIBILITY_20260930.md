# Human-readable export naming feasibility — 2026-09-30

**STATUS: FEASIBLE_WITH_CONSTRAINTS**

Research baseline: `7d21318444c4d422565fe54f373ac1af8444a0ee`.
This is a feasibility checkpoint, not a production implementation. No private
assets were used. All concrete examples refer to **マジュン (Majun)** or generic
synthetic roots/assets. Unity version actually executed: **2022.3.22f1**.

## Intent and authority

People should distinguish Materials from different composition members without
turning their display names into machine identity. The current PRODUCT_SPEC,
Core Product Model, Export Identity Model, Export Architecture Decision, Current
State and Lessons Learned were read at the baseline HEAD, equal to remote HEAD.
Geometry and slot placement remain Blender-authoritative. Reusable Unity assets
retain source identity and serialized semantics; Export IDs remain transport
labels. Original Material/Texture packages must not become output dependencies.

## Observed Unity behavior

Six first-party Material assets share a synthetic standalone Shader and Texture.
The probe changes output pathnames while retaining each original `.meta` and GUID.
Two Materials also receive an explicit, single-field serialized `m_Name` patch.
Fresh Unity imports the **generated UnityPackage**, not source Packages. Assertions
check exact GUID and signed local fileID, every Texture property, Shader identity,
Material bytes, both synthetic Prefabs' original ordered Renderer Material refs,
and the existing product Finalizer twice. Separate fresh runs cover a filename-
only asset and the asset with both filename and internal-name changes as the
Finalizer's selected Material. Both complete with process exit **0**.

| Variation | Output filename | Serialized name | Material.name | ObjectContent text |
| --- | --- | --- | --- | --- |
| File/name relocation only | `Majun_Body__<digest>.mat` | `Body` | `Body` | `Body` |
| Filename kept; internal name patched | `Body.mat` | `SyntheticOther_Body` | `SyntheticOther_Body` | `SyntheticOther_Body` |
| Filename and internal name patched | `Majun_Body__<digest>.mat` | `Majun_Body__<digest>` | `Majun_Body__<digest>` | `Majun_Body__<digest>` |

Thus filename/path changes alone preserve identity and references, but **do not
rename the native Material object**. `m_Name` changes are necessary if the actual
Material.name / public Object Field label must also contain the owner label.
They are serialized state modifications, not verbatim preservation. The probe
updates the existing Recipe's Material byte hash to the explicitly staged bytes;
it does not weaken or bypass the Finalizer's hash check.

Project Browser path/filename information was measured through AssetDatabase;
Object Field text through documented `EditorGUIUtility.ObjectContent`. **Live
Project Browser and Inspector GUI rendering was not observed.** Do not equate
these API observations with screenshot verification of every Editor view/layout.

## Five public synthetic cases

The source Editor captures exact Prefab GUIDs, signed Material IDs and ordered
Renderer slot references. It exports separate `Majun.unitypackage`,
`SyntheticOther.unitypackage`, `Materials.unitypackage` and `Shared.unitypackage`.
The relocation probe additionally uses a first-party aggregate for convenient
staging; it is not a new production owner-inference or reachability implementation.

| Case | Independent source evidence | Result |
| --- | --- | --- |
| 1. Same filename, different GUID | Majun references Material-only `Body.mat`; the other synthetic root references another `Body.mat` | Both GUID/localIDs and ordered slots survive separate output paths. PASS |
| 2. Material-only sibling | The referenced Material GUID is absent from Majun's Package and present in `Materials.unitypackage`; public API confirms Majun's exact Renderer reference | Owner use proven independently of directory/name. PASS |
| 3. Shared asset | Both Prefabs reference the same Material GUID supplied once by `Shared.unitypackage` | One output asset at `Shared/Materials/SharedSkin.mat`; both references retained. PASS |
| 4. Ambiguous label hints | An unreferenced Material has two competing fixture label hints and a Majun-containing source path, but zero verified owner references | Staged at `Unassigned/Materials/Body.mat`; no inferred Majun ownership. PASS |
| 5. Same owner, same name | Multiple distinct Body Material GUIDs are referenced by Majun | All colliding label candidates receive stable GUID-derived suffixes; no first-wins rule. PASS |

The roots are synthetic Renderer-reference fixtures, not qualified VRChat avatars.
The otherwise unassigned asset is deliberately selected for the naming experiment;
this does not authorize production export of all unreachable source assets.

Two repeated stagings of the same frozen source/Recipe and naming policy produce
**byte-identical packages and paths**. This proves this probe's determinism, not
whole-production-package determinism across newly generated FBX/GUID runs.
Exact-path/different-GUID collision and same-GUID/different-path duplication each
raise before writing. One real gap was also reproduced: current StagingTree
accepts case-only path differences as distinct entries. It was **not repaired**
because production behavior is outside this research task.

## Current architecture and implementation gap

| Layer | Available now | Boundary/gap |
| --- | --- | --- |
| `StagedUnityAsset` | Separate `pathname`, `source_identity`, `export_identity`, operation and payload | Destination locator can differ from source path. Metadata must keep the same GUID. |
| AssetPlan | `desired_export_path`, source path, MOVE/RENAME/MODIFY and preserved-GUID decisions | MOVE/RENAME use preserve-verbatim; MODIFY needs a validated strategy. |
| StagingTree | GUID/meta consistency, exact pathname collisions, unequal duplicate GUID rejection | Same GUID may be added only as an identical canonical entry. Casefold, Unicode and portable filename checks are incomplete. |
| Manifest | Source records and planned destination paths in the generic planner | Current final-state route copies source paths and emits empty source asset/package collections; it has no naming policy or separate name fields. |
| Finalizer | Material GUID + signed localID resolution, Shader/Texture checks and byte-hash gate | Material path is resolved by GUID rather than assumed from its original filename. Changing m_Name requires the correct output byte hash. |

An exact GUID does not alone prove that conflicting providers represent the same
revision. Same-GUID/different-payload or importer metadata must remain a conflict,
not be merged under a Shared label. Canonical provider selection precedes naming.

## Owner evidence hierarchy

1. Selected composition member / root occurrence identity, exact effective
   Renderer-to-Material GUID/localID binding and confirmed provider/revision.
2. Source Prefab/occurrence provenance plus Package identity: identifies the
   evidence namespace and container; does not by itself prove an owner.
3. Explicit user export-label override tied to a machine identity: trusted label,
   not an identity replacement. Current final Blender slot usage decides export
   bindings, including entirely new geometry with no original Mesh lineage.
4. Root/Prefab display name, package filename and parent-directory name: candidate
   human labels only, after the usage relationship is established.
5. Sibling discovery: provider-discovery evidence only. Co-location is never an
   ownership edge. Unproved or competing owner hints use Unassigned/neutral names.

For `Majun/Majun.unitypackage` plus `Materials.unitypackage`, the second package's
Material may receive a Majun label only when exact use by the selected Majun
member is proven. A material-only package cannot establish an owner alone.
For clothing/accessories, retain a proven member identity independently of the
composition owner; an optional `Majun/Coat/Materials/Majun_Coat_Fabric.mat` layout
is a proposal, **not an additional tested clothing fixture**.

## Three naming approaches

| Axis | A: prefix only | B: folders only | C: hybrid |
| --- | --- | --- | --- |
| Example | `Majun_Body.mat` | `Majun/Materials/Body.mat` | `Majun/Materials/Majun_Body.mat` |
| Browser/path readability | Good leaf names, flat clutter | Good while folder context visible | Best context in folders and leaf paths |
| Native object/Inspector label | Still Body unless m_Name patched | Still Body | Still Body unless m_Name patched |
| Same-name collisions | Stable suffix required | Folder helps; same-owner suffix required | Folder plus stable suffix |
| Shared asset | Neutral prefix required | Shared folder is clear | Shared folder, neutral original name |
| Long path risk | Lowest | Moderate | Highest; must cap redundant prefixes/levels |
| Determinism/rename stability | Fixed policy and identity keys | Same | Same; owner-label changes intentionally move path |
| User rename coexistence | Explicit override only | Explicit folder/leaf policy | Explicit override plus separate name-sync policy |
| GUID/reference preservation | PASS for tested Material assets | Same mechanism, specific folder-only form not separately run | PASS for tested Material assets |
| Manifest complexity | Low | Low/moderate | Moderate: original vs chosen labels separated |
| Windows/Unity restrictions | Required | Required | Required; no case-only paths |

## Recommended constrained default

**C: hybrid folder + owner-prefixed filename**, with bounded hierarchy and stable
suffixes only on collisions. Default internal `m_Name` policy is **preserve**.
An explicit name-synchronization option may be offered later for users requiring
owner-visible Material object labels; it must be a typed MODIFY with original
name retained as provenance, every other serialized field preserved, output hash
updated and fresh Unity regression. Never silently claim raw-preserve after patching.

```text
Assets/VAPBExport/Majun/Materials/Majun_Body.mat
Assets/VAPBExport/Majun/Materials/Majun_Face.mat
Assets/VAPBExport/Shared/Materials/SharedSkin.mat
Assets/VAPBExport/Unassigned/Materials/Body.mat
```

Shared: group only proved identical logical assets/revisions, stage once; carry
all use bindings and choose a neutral label. Ambiguous owner: do not pick the
first candidate, source package filename or nearest directory. Remain neutral.

Collision: normalize/validate components, compare prospective destinations with
portable casefold/Unicode policy, group the whole collision set before allocation,
then suffix **every** colliding member from canonical asset identity (probe uses
eight SHA-256 hex characters of GUID). If suffixes collide, extend deterministically
or reject. Do not alter GUID, merge by name, or use insertion-order `.001`/copy/new.
Owner folder-label collisions need the same identity-based separation.

User rename: keep original Unity name, current Blender display name, owner label
and chosen output label distinct. Auto-generated Blender suffixes are not proof
of intentional rename. Default uses the original Unity name plus proven owner
label; explicit export-label override wins. Store proposed `original_name`,
`blender_display_name`, `owner_label`, `desired_export_name`, `original_path`,
`desired_export_path` separately in later design; **no schema implementation here**.

## Risks and exact later implementation boundary

- Restrict an initial implementation to source-backed `.mat` main assets and
  proven selected composition use. Imported FBX subassets and every asset type
  are not covered by this study's fileID stability result.
- Add a pure export-organization policy after identity/provider resolution and
  before staging; do not put owner/name fallback into the resolver or Finalizer.
- Preserve .meta/import settings. Path changes are MOVE/RENAME with unchanged
  payload. Optional m_Name sync is a separately validated MODIFY.
- Reject reserved Windows names/chars, trailing dots/spaces, case-only collisions,
  unsafe Unicode normalization collisions and over-budget paths. The budget must
  account for the actual destination project prefix; do not assert a universal
  260-character Unity limit or silently enable OS long-path settings.
- Existing-project imports where the same GUID already occupies another path,
  imported model subassets, GUI list/grid/Inspector variants, Japanese/Unicode
  names, very long names, suffix-digest collisions and user-rename persistence
  require further tests. They were not claimed from fresh-project results.
- Package names/directory labels, whole-avatar qualification and all asset-type
  organization are not automatically proven by the synthetic usage graph.

Before production: add owner-positive/negative and shared-revision tests, same-
name/casefold/Unicode/reserved-name/path-length tests, input-order permutation and
repeat/rename tests, optional m_Name-only patch/hash-gate negatives, normal Blender
export/save/reopen, fresh Unity exact identity/slot/property comparison, and
nonempty destination GUID collision handling. Observe actual GUI labels before
claiming complete Project Browser/Inspector readability.

## Reproduction and retained evidence

Use only the existing first-party non-Standard synthetic output as the seed:
`tests/blender_material_return_phase2_test.py -- <unused scratch> green` under
Blender's background runner with `--python-exit-code 1`. Its `NONSTANDARD_GATE`
output is the research seed, not a private avatar package.

Create separate source/fresh Unity 2022.3.22f1 projects with normal ProjectSettings
and Packages. Copy only `VapbNamingStudyProbe.cs` into each `Assets/Editor`.
From repository root:

```text
python tests/naming_study_package.py stage <synthetic seed Output.unitypackage> <source project>
Unity -batchmode -nographics -projectPath <source project> -executeMethod VapbNamingStudyProbe.Prepare -logFile <external log>
python tests/naming_study_package.py relocate <source project> <fresh project> 2
Unity -batchmode -nographics -projectPath <fresh project> -executeMethod VapbNamingStudyProbe.Run -logFile <external log>
```

Index 0 selects the filename-only Material for Finalizer; index 2 selects the
filename-plus-internal-name variant. Each requires a genuinely fresh project.
Repeat relocation with the same index into a separate external directory and
compare package bytes. `SourceEvidence.json`, `Expected.json`, `Observed.json`
and generated packages/logs stay outside Git; scripts and this sanitized record
are sufficient to regenerate public evidence. Initial throwaway staging had a
RawAsset/StagedUnityAsset type mismatch; it was corrected in the research script,
not production. Its incomplete fresh-project run was aborted and a new project
was used for the successful import.

## Primary references

- [Unity 2022.3 Asset Metadata](https://docs.unity3d.com/2022.3/Documentation/Manual/AssetMetadata.html): GUID references and retaining metadata when moving assets.
- [Windows file/path naming rules](https://learn.microsoft.com/en-us/windows/win32/fileio/naming-a-file): component restrictions and reserved names.
- [Current staging](../export/staging.py), [asset planning](../export/asset_plan.py), [Finalizer](../unity_editor/Editor/VapbFinalStateFinalizer.cs).

The observed results are specific to the executed Unity version and synthetic
standalone Material/Shader/Texture assets; documentation complements the runtime
proof and does not substitute for it.
