# Unity Semantic Oracle v0.1

The development-only Oracle observes Unity's normal import result and emits
facts for an independent Blender-side implementation. It is not a runtime
dependency of the add-on and does not extract Unity source code.

## Verified behavior

- Official Unity 2022.3.62f3 batchmode CLI completed the synthetic probe.
- A synthetic nested FBX prefab produced current prefab identities and original
  FBX identities for the same renderer object.
- The observed renderer retained its current material GUID and material slot.
- Public `PrefabUtility` property-modification targets were resolved where
  Unity exposed them; unresolved targets are represented explicitly.
- A private, repo-external package-group run completed through public
  `AssetDatabase.ImportPackage` completion events and produced 8 prefabs,
  1,462 object records, 64 renderer records, and 88 resolved property
  modifications. No commercial JSON is committed.

## Compliance

Unity access method: official Unity Editor CLI (`-batchmode -nographics
-executeMethod`) plus normal public Editor scripting APIs.

UnityMCP: not installed; the official CLI and public APIs were sufficient.

- Documented/public Unity APIs only: PASS
- Unity binary decompilation: NO
- Private/internal Unity implementation copied: NO
- Commercial asset payload committed: 0
- Commercial raw diagnostic committed: 0

The public API boundary is intentional: nested prefab modifications that Unity
does not expose through `GetPropertyModifications` are not reconstructed by
parsing YAML or using internal APIs.
