# VAPB Core Product Model — 2026-09-28

Status: **USER-AUTHORIZED CORE PRODUCT DEFINITION**

This document records the product-model decision made on 2026-09-28. It is normative for product intent. Where an older design document requires source-geometry identity continuity as a condition of successful export, this document narrows that requirement: source identity remains important for import provenance, dependency recovery, reusable Unity assets, and Unity/VRC state capture, but it is **not** normally required to prove that an exported Mesh is the same logical Mesh as the source Mesh.

## 1. Product problem

VAPB exists to remove this manual workflow:

```text
Unity
→ import avatar/package
→ export FBX
→ Blender
→ edit
→ export FBX
→ Unity
→ manually reassign Materials
→ manually restore Unity/VRC settings
→ repeat repair work
```

The desired workflow is:

```text
UnityPackage(s)
→ VAPB import into Blender
→ ordinary Blender editing
→ VAPB export
→ self-contained UnityPackage
→ Unity import
→ recipe-driven Material / component / VRC-state reconstruction
```

The primary product value is therefore **automation of the return-to-Unity repair/reconstruction work**, not preservation of source Mesh lineage for its own sake.

## 2. Two authorities

VAPB separates two sources of truth.

### 2.1 Blender Final State Authority

At export time, Blender is authoritative for editable 3D state:

- Mesh geometry and topology
- UVs
- normals/tangents where supported
- Armature and Bone structure
- vertex groups and weights
- Shape Keys
- editable Transform / hierarchy
- Material slot structure
- face-to-material-slot assignment

The user may radically change this state. Deleting all imported Meshes and creating a new Cube is a valid workflow.

### 2.2 Unity Semantic State Authority

Unity/VRC-specific state that Blender does not faithfully own is captured at import time and retained as source evidence / recipe data:

- Unity Material asset identity and serialized shader properties
- Texture asset references
- Renderer and component settings needed for restoration
- Avatar Descriptor state
- Animator / controller / clip references
- Expressions / Parameters / Menus
- PhysBone / Collider
- Contact
- Constraints
- Modular Avatar / NDMF and other preservable third-party state
- preservable MonoBehaviour / ScriptableObject serialized state

Blender preview state is never silently promoted to authoritative Unity/VRC state.

## 3. Geometry source lineage is not a normal export requirement

The following chain is **not** required as a normal success condition:

```text
source Unity Mesh identity
→ Blender realization
→ edited Blender Mesh
→ regenerated FBX Mesh
→ proof that the post-import Unity Mesh is the same logical source Mesh
```

VAPB may retain source Mesh identity as provenance and diagnostic evidence, but export must remain possible when the geometry lineage is intentionally severed.

Example:

```text
import Avatar A
→ delete every imported Mesh
→ create Cube
→ UV unwrap
→ assign imported/derived Blender Materials
→ export
→ Unity receives a new FBX containing Cube
```

This is a valid target workflow.

## 4. VAPB Export IDs are transport labels

VAPB uses its own export-time identifiers to connect Blender final state to Unity reconstruction.

Conceptual identifiers include:

```text
VAPB-OBJ-*
VAPB-BONE-*
VAPB-MAT-*
VAPB-TEX-*
VAPB-COMP-*
```

Do not assign an ID to every scalar property. IDs are for independently referenced semantic entities.

Conceptual bridge:

```text
Unity source semantics
        ↕
      VAPB ID
        ↕
Blender final state
        ↓
exported FBX / staged assets
        ↓
Unity post-import objects
```

Source identity and export identity are different domains.

- **Source identity** explains where imported evidence came from.
- **Export identity** identifies the user's current Blender final state for transport and reconstruction.
- **Unity post-import identity** is observed after Unity imports the generated assets.

## 5. Material model

A Unity Material may be converted into an approximate Blender Material for editing and preview.

Example:

```text
Unity Body.mat (GUID AAA)
→ VAPB-MAT-001
→ Blender Body_Preview
```

The Blender node graph does not need to be a reversible representation of the Unity shader.

VAPB retains the Unity-specific Material state separately:

```text
VAPB-MAT-001
├ source Unity Material identity
├ serialized shader/property state
├ Texture references
├ Blender realization
└ export / restore policy
```

The export recipe is based on **current Blender slot usage**.

Example final Blender state:

```text
Cube
slot 0 → Body_Preview  (VAPB-MAT-001)
slot 1 → Face_Preview  (VAPB-MAT-002)
```

Recipe:

```text
VAPB-OBJ-001 / slot 0 → VAPB-MAT-001
VAPB-OBJ-001 / slot 1 → VAPB-MAT-002

VAPB-MAT-001 → Unity Material asset AAA
VAPB-MAT-002 → Unity Material asset BBB
```

The Unity-side Finalizer resolves the post-import target object and assigns the Unity Material assets to the requested slots.

The original source Renderer layout is evidence for import-time reconstruction; it does not override deliberate Blender final-state slot edits.

## 6. Self-contained output package

The exported UnityPackage should normally contain the concrete assets required by the Blender final composition.

Input may be fragmented:

```text
Avatar.unitypackage
Materials.unitypackage
Textures.unitypackage
Clothes.unitypackage
```

Export recomputes reachability from the selected Blender final state and stages the required output:

```text
OutputAvatar.unitypackage
├ Avatar.fbx
├ Avatar.prefab
├ Materials/
├ Textures/
├ VAPB recipe / manifest
└ Unity Finalizer support
```

The normal output must not require re-importing the original Material/Texture packages merely to restore references.

Framework-level dependencies may remain external when appropriate, for example:

- VRChat SDK
- shader frameworks such as lilToon
- Modular Avatar / NDMF

“Self-contained” therefore means self-contained with respect to the selected asset composition, excluding explicitly declared external frameworks.

### Human-readable output organization (constrained addition, 2026-09-30)

Readable output labels must remain independent of source/Export/post-import
identity. Material assets may keep GUID/fileID and metadata at a new output
path, with references restored by GUID. Owner labels require proven composition
use; genuinely shared assets are staged once, unproved owners remain neutral.
Hybrid folder/filename organization is the constrained basic policy for later
implementation. PRODUCT POLICY = NO-GO: do not modify internal Material
`m_Name` or serialized bytes for naming, and do not offer a synchronization option.
Naming cannot restore a source-geometry-lineage requirement or make original
input packages runtime dependencies. No production naming behavior is added by
this document; see [the research evidence and limits](VAPB_HUMAN_READABLE_EXPORT_NAMING_FEASIBILITY_20260930.md).

### Mandatory hierarchy parity milestone (2026-09-30)

Hierarchy Parity is mandatory **after human-readable Material organization and
before broad Unity/VRC component restoration**. For the same selected composition,
VAPB must preserve the equivalent semantic parent/child structure between Unity
and Blender wherever both applications can represent the same relationship.

Parity covers GameObject-equivalent parent/child relations, Transform chains,
Renderer ownership/attachment, Bone hierarchy, and occurrence multiplicity.
Repeated instances of one source component remain distinct occurrences. The
comparison is semantic: Blender-specific Armature Objects, technical Empties and
other representation helpers may exist, but they must be isolated from the
user-facing semantic hierarchy and may not silently alter its meaning.

Correspondence must be established from GUID/fileID/package/occurrence provenance
and VAPB semantic identity, never from display-name coincidence. Intrinsic
Unity/Blender representation differences are recorded as explicit mappings rather
than silently flattened or replaced with invented hierarchy. Supported parity must
survive Blender save/reopen.

A public synthetic **Majun** hierarchy is the normative example for the first
independent comparison fixture. This milestone must be validated before broad
Avatar Descriptor, Animator, PhysBone, Contact, Constraint or other Unity/VRC
component restoration is treated as a downstream reconstruction target.

```text
Human-readable Material organization
→ Hierarchy Parity
→ broad Unity/VRC component restoration
```

## 7. Finalizer responsibility

The Unity Finalizer is not primarily a source-Mesh identity restoration engine.

Its primary job is:

> **Attach preserved Unity semantics to the Blender-authored final structure after Unity imports the generated assets.**

Typical flow:

1. Observe exact Unity import results for the generated FBX/assets.
2. Resolve VAPB Export IDs to current Unity GameObjects, Renderers, Transforms, Bones, Materials, etc.
3. Apply Material slot bindings from the recipe.
4. Restore supported Unity/VRC component state to the resolved current targets.
5. Report missing, ambiguous, dependency-required, unsupported, or failed restoration without guessing.

The Finalizer must be idempotent where practical and must not rely on display-name coincidence as authoritative identity.

## 8. Source identity still matters

This decision does **not** remove the need for GUID/fileID/package/occurrence analysis.

Source identity remains necessary to:

- reconstruct the correct imported Material and Texture dependencies;
- understand Prefab / Variant / Nested effective state;
- distinguish repeated occurrences during import;
- recover cross-package providers;
- capture Unity/VRC state from the correct source object/component;
- preserve reusable Unity asset identity where useful;
- diagnose ambiguity and broken packages.

The change is narrower:

> **Source geometry identity is evidence for understanding the input, not a mandatory lineage that every newly exported Mesh must inherit.**

## 9. Existing architecture that remains valuable

The following existing work remains useful and should not be discarded:

- UnityPackage parser and RAW source preservation
- package fingerprints, GUIDs, signed local fileIDs
- Prefab / Variant / Nested semantics
- occurrence projection
- cross-package dependency recovery
- Material / Texture provider resolution
- Blender realization
- fail-closed ambiguity handling
- export-time reachability
- deterministic UnityPackage writer
- MRUS/source snapshots
- Unity public-API post-import observation
- Finalizer/rebind infrastructure

These mechanisms are repurposed toward **semantic reattachment to Blender final state**, not toward mandatory preservation of original geometry identity.

## 10. Minimum architecture proof

Two public-safe E2E cases define the first proof of this product model.

### Case A — unchanged round trip

```text
Avatar UnityPackage
→ Blender import
→ no user edit
→ VAPB export
→ fresh Unity import
→ required Material/state reconstruction succeeds
```

### Case B — intentional geometry replacement

```text
Avatar UnityPackage
→ Blender import
→ delete original Meshes
→ create Cube
→ UV unwrap
→ assign Unity-derived Blender Materials
→ VAPB export
→ fresh Unity import
→ generated Cube receives the intended Unity Materials automatically
```

Case B is the critical proof that VAPB reconstruction does not depend on preserving source Mesh identity.

Later tests can extend the same model to Bones, PhysBone, Descriptor, Animator, Contacts, and other supported state.

## 11. Non-goals

VAPB is not required to:

- provide a byte-for-byte reversible UnityPackage transform;
- preserve source Mesh local fileIDs through Blender-generated FBX;
- make Blender a Unity Engine emulator;
- make Blender shader nodes the Unity Material source of truth;
- reconstruct unknown Unity/VRC semantics by guessing;
- bundle every external framework into the output package.

## 12. Product invariant

The core invariant is:

> **Geometry authority = Blender final state.**  
> **Unity/VRC semantic authority = captured source state / recipe.**  
> **VAPB Export IDs bridge the two at export.**  
> **The exported UnityPackage contains the required selected assets and should not normally depend on the original input packages.**

The user-facing success criterion is simple:

> **Remove the manual “Unity → FBX → Blender → FBX → Unity → reassign Materials → restore settings” workflow.**
