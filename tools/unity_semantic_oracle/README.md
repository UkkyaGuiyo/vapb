# Unity Semantic Oracle v0.1

Development-only Unity 2022.3.62f3 probe. It uses public Unity Editor APIs to
emit observed Prefab, Renderer, mesh, material, GlobalObjectId, and property
modification data as JSON. It is not included in the Blender add-on runtime.

Batch usage:

```text
[private command or output omitted; narrative finding retained]
```

The JSON deliberately encodes Unity local file IDs as decimal strings.

## Access and scope

This probe is development-only and is not imported by the Blender add-on. It
uses the Unity 2022.3 Editor CLI and documented public Editor APIs only:
`AssetDatabase`, `PrefabUtility`, `GlobalObjectId`,
`TryGetGUIDAndLocalFileIdentifier`, `Renderer`, `MeshFilter`,
`SkinnedMeshRenderer`, `Material`, and `Shader`. `AssetDatabase.ImportPackage`
completion events are awaited before probing a package group. UnityMCP was not
installed or used because the official CLI and public Editor scripting API were
sufficient.

`BatchImportAndProbe` accepts a semicolon-separated `<PRIVATE_WORKSPACE>_PACKAGES`
list and an optional `<PRIVATE_WORKSPACE>_PREFAB_FILTER`. Real package probing must
run in a disposable project and set `<PRIVATE_WORKSPACE>_EXTERNAL_PROJECT=1`; the
probe rejects package imports without that flag and rejects output paths inside
the Unity project. Real package output belongs in a private diagnostics
directory outside the repository. The committed golden file is independently
generated synthetic data only.

For each instantiated prefab object the probe records both the current prefab
source identity and the original source identity returned by
`PrefabUtility.GetCorrespondingObjectFromOriginalSource`. This is the public
API observation needed to distinguish a prefab component from its original FBX
component. Nested prefab property modifications that Unity does not expose via
the public `GetPropertyModifications` result remain absent; the probe does not
parse YAML or inspect Unity internals to fill that gap.

Compliance: no Unity binary decompilation, private/internal implementation
copying, reflection, or reverse-engineering is used. Commercial assets are
private local diagnostics only and are not committed.
