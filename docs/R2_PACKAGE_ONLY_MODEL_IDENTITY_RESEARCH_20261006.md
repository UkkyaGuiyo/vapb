# Package-Only Unity Mesh to FBX Identity Research

Date: 2026-10-06
Project: VAPB
Repository: https://github.com/UkkyaGuiyo/vapb
Branch: `feature/r2-material-slot-reorder`
Inspected repository snapshot: `e0bc8afab41bf57303d59cbcb2ace0149a3d7e71`

## Question and result

Can the Unity serialized `Renderer.m_Mesh` reference in this public synthetic
UnityPackage be joined to the corresponding native FBX Model/Geometry identity
using package contents alone, without adding a Unity import step to the normal
`unitypackage -> Blender` entry flow?

**For this input revision, the automatic join is not proven.** The package gives
the Prefab's Mesh asset GUID and Unity local file ID. The FBX gives its own
Model and Geometry UIDs and their connection. No package evidence inspected
here links those two identifier spaces. FBX names, hierarchy, importer settings,
and the number of Blender candidates remain useful diagnostics, but none is an
authoritative crosswalk for this fixture.

This is not a rule that every user must provide a Unity witness. Keep direct
package import for inputs with an explicit revision-bound map, another verified
package-side identity edge, or an already-supported confirmation route. Only
the unresolved automatic binding stays pending. This follows the product
entry flow in [VAPB Core Product Model](VAPB_CORE_PRODUCT_MODEL_20260928.md):
`UnityPackage(s) -> VAPB import into Blender -> ordinary Blender editing`.

## Fixed input and independently readable identities

The inspected package is the checked-in public fixture
`tests/unity_model_material_probe/fixtures/ThreeSlotSource.unitypackage`.

| Item | Observed value | Evidence class |
|---|---|---|
| UnityPackage SHA-256 | `d6245d25c3cbd513c49b8d2e241b313a752331cd338563becab6eb7c819bfa0c` | Raw archive bytes |
| Prefab Renderer | class 137, local file ID `3728717051629469441` | Raw Prefab YAML |
| Renderer owner | GameObject local file ID `6665729011320497926` | Raw Prefab YAML |
| `m_Mesh` reference | GUID `abcdefabcdefabcdefabcdefabcdefab`, local file ID `3538053534738119282` | Raw Prefab YAML |
| Model asset FBX SHA-256 | `fbe25a43a81a066c443093a0788a05569a4ec54e2d673fe133bffa7f801309c5` | Raw archive payload |
| FBX Model | UID `208084244`, name `Edited Native Skin.001` | Blender 5.2.1 FBX parser, raw FBX |
| FBX Geometry | UID `329684292`, name `Cube.005` | Blender 5.2.1 FBX parser, raw FBX |
| FBX relation | OO connection joining Mesh Geometry `329684292` to Model `208084244` | Raw FBX `Connections` graph |

The package has six pathname records: five file assets and one folder record
without an asset payload. The target Unity Mesh local file ID appears in the raw
Prefab payload. It does not equal either parsed FBX UID. A narrow byte scan of
the FBX found no decimal or hexadecimal text form and no exact signed 64-bit
little- or big-endian encoding of that Unity local file ID. This only excludes
those direct encodings; it does not exclude an undocumented derived mapping.

The FBX `.meta` contains:

```yaml
ModelImporter:
  serializedVersion: 22200
  internalIDToNameTable: []
  externalObjects: {}
  meshes:
    fileIdsGeneration: 2
    sortHierarchyByName: 1
    nodeNameCollisionStrategy: 1
    preserveHierarchy: 0
```

The empty tables supply no row for the target local file ID. The `serializedVersion`
and `fileIdsGeneration` values are recorded as input data only; the official
Unity 2022.3 `ModelImporter` reference inspected for this note does not define a
formula that turns either value into a Mesh local ID or an FBX UID.

## What the official interface establishes

Unity 2022.3 describes a serialized asset reference as an asset GUID plus a
file ID relative to that asset. Its public
[`AssetDatabase.TryGetGUIDAndLocalFileIdentifier`](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/AssetDatabase.TryGetGUIDAndLocalFileIdentifier.html)
API obtains those identifiers from an actual Unity object; the documented
contract does not equate a Model-imported Mesh local ID with an FBX Model or
Geometry UID.

Unity's 2022.3 [`AssetImporter.AddRemap`](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/AssetImporter.AddRemap.html)
maps an imported sub-asset to an external asset of the same type. The
[`SourceAssetIdentifier` constructor](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/AssetImporter.SourceAssetIdentifier-ctor.html)
keys that remap by sub-asset type and name. The
[`GetExternalObjectMap`](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/AssetImporter.GetExternalObjectMap.html)
API returns the importer's external-object remap map. These APIs describe
remapping imported objects; they do not specify a general Mesh-local-file-ID to
FBX-UID algorithm. In the fixed input, `externalObjects` is empty.

The official [`ModelImporter` API](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/ModelImporter.html)
documents import settings and external-object remapping but does not document
`fileIdsGeneration` or `internalIDToNameTable` as a crosswalk to FBX object UIDs.
The Unity 2022.3 managed reference source declares
`MakeLocalFileIDWithHash(int persistentTypeId, string name, long offset)` and
`MakeInternalID(int persistentTypeId, string name)` as native `extern` methods
in [`AssetImporter.bindings.cs`](https://github.com/Unity-Technologies/UnityCsReference/blob/2022.3/Editor/Mono/AssetPipeline/AssetImporter.bindings.cs#L110-L115).
That is a concrete lead that importer IDs may involve type, name, and offset,
but the managed reference does not provide the native implementation, the FBX
Mesh call inputs, or a documented relation to `fileIdsGeneration`. Treating
those method names as a reproducible ID formula would be speculation.

Unity also documents that
[`OnPostprocessModel`](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/AssetPostprocessor.OnPostprocessModel.html)
can modify imported GameObjects and Meshes before the final Prefab is created,
and that [`preserveHierarchy`](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/ModelImporter-preserveHierarchy.html)
changes whether an explicit Prefab root is created. These are reasons to treat
matching names or paths as cues requiring validation, not a version-independent
identity contract.

## Candidate evidence routes

| Candidate route | What it can establish | Result for this package |
|---|---|---|
| Revision-bound explicit map from Unity local Mesh ID to FBX Model/Geometry UID | A source identity edge if tied to exact FBX/meta hashes, with documented producer/schema and each row validated against the raw FBX graph; automatic occurrence binding also needs owner, instance context, and native-receipt validation | No matching map or sidecar was found; the only repository witness sidecar targets a different FBX SHA and renderer class, so it cannot be reused |
| Non-empty `internalIDToNameTable` plus FBX names | Potential file-ID/name evidence; still needs an independently validated name-to-FBX-UID rule, duplicate handling, rename handling, and proof for the exact importer/version | Table is empty; no join can be attempted |
| `externalObjects` | Importer remaps from identified imported sub-assets to same-typed external assets | Empty here; even when present, a remap target is not automatically an FBX UID crosswalk |
| `fileIdsGeneration` and importer settings | Reproduction inputs if a documented and versioned ID-generation algorithm becomes available | Values are present, but no public formula or complete inputs were found |
| FBX UID/name/hierarchy/Geometry graph | Native FBX object identity and internal Model-to-Geometry edges | Establishes the FBX half only; does not identify which Unity local file ID selects it |
| GUID + FBX SHA + one native candidate | A constrained candidate set | The existing [synthetic cardinality negative control](https://github.com/UkkyaGuiyo/vapb/commit/e0bc8afab41bf57303d59cbcb2ace0149a3d7e71) demonstrates that this candidate rule cannot distinguish the requested Mesh local file ID; it does not observe Unity resolving the altered reference. The production bridge reports `WITNESS_MISSING` for both inputs |
| Explicit user confirmation | A distinct `USER_CONFIRMED` binding route, not automatic identity derivation | Already tested for this fixture and confirmed to persist across a separate Blender process; see [T0 confirmation and reopen evidence](R2_ROUNDTRIP_T0A_CONFIRMATION_PROBE_20261006.md) |

The existing T0 evidence remains bounded: strict no-edit automatic import is
**FAIL** for this fixture, and export validation is **BLOCKED** behind that
failed gate. The explicitly confirmed route is a separate result and must not
be relabeled as a strict no-edit pass. No Unity witness has been made a
mandatory product prerequisite.

## Narrow next branch

No further cardinality-only test is useful for this fixture. The synthetic
negative control shows that the singleton candidate rule cannot distinguish
the requested local file ID; it does not establish that Unity resolves the
altered reference to a different sub-asset. The fixed package contains no
alternative explicit map.

Keep the importer-algorithm branch **PENDING** until one of these produces
checkable evidence:

1. A public package/producer format includes an exact-hash mapping from the
   serialized Unity Mesh local ID to a raw FBX Model/Geometry identity; or
2. A versioned ID-generation rule and all required inputs are available and
   pass against multiple independently identified revisions, including
   duplicate names/hierarchy and a negative case.

If the isolated Unity slot later becomes available, one bounded oracle run can
record the actual Mesh sub-assets, `TryGetGUIDAndLocalFileIdentifier` values,
names/types, importer settings, and the exact FBX revision. A list of Mesh IDs
and names alone cannot establish their FBX UID correspondence; each proposed
pairing must be independently validated against the FBX graph or another
authoritative source. That run would test candidate rules; it would not add a
Unity pre-step to normal VAPB imports. The Unity slot was not used for this
note.

## Scope and limitations

- Static raw-package inventory plus Blender 5.2.1's FBX parser; no Unity Editor
  launch, no Blender import mutation, and no product-code change.
- The prior persistent-receipt and explicit-confirmation evidence is cited from
  its separate T0 run, not reproduced by this static inventory.
- This establishes a missing authoritative edge in this fixture and the
  evidence inspected. It does not prove that every Unity-free mapping scheme
  is impossible or that every UnityPackage needs a witness.
- Package-only import remains the intended product entry. An unresolved
  identity branch must remain explicitly partial/unbound until its own evidence
  route is established.
