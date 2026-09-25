# Unity interoperability validation corpus

This directory contains only synthetic/public-safe validation inputs. It is
not a replacement for the canonical `VAPBFullSemanticOracle.cs`.

The generated packages exercise:

- raw UnityPackage layout, UTF-8 pathnames, folder metadata, and binary bytes;
- material texture references and a controlled A-to-B GUID patch;
- a Blender-generated baseline FBX and a vertex-change reimport package using
  the same source GUID;
- an expected-semantics manifest that keeps Asset GUID, local fileID, prefab
  occurrence identity, and Unity runtime identity separate.

Generate the artifacts from the repository root:

```powershell
python validation/unity_interop/generate_validation_packages.py `
  --fbx validation/unity_interop/artifacts/VAPBValidation.fbx `
  --mutation-fbx validation/unity_interop/artifacts/VAPBValidation_vertex.fbx `
  --output validation/unity_interop/artifacts
```

The Blender FBX probe is run separately with Blender 5.2.x:

```text
[private command or output omitted; narrative finding retained]
```
& '<LOCAL_PATH> Foundation\Blender 5.2\blender.exe' `
  --factory-startup --background `
  --python validation/unity_interop/blender_import_probe.py -- `
  validation/unity_interop/artifacts/VAPBValidation_baseline.unitypackage
```
```

Unity human gate, after the artifacts exist:

1. Open the existing Unity 2022.3 Oracle project.
2. Import `VAPBValidation_baseline.unitypackage`.
3. Run `Tools > VAPB > Export Full Semantic Snapshot`.
4. Replace/reimport with `VAPBValidation_vertex_mutation.unitypackage`.
5. Run the same canonical menu again.

Codex compares the resulting snapshot directories offline. Do not edit the
generated assets, inspect commercial data, or create another Oracle runner.
