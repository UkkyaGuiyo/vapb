# Unity API Coverage

The 2022.3 runner uses documented public APIs: `AssetDatabase`,
`PrefabUtility`, `GlobalObjectId`, `Renderer`, `MeshFilter`,
`SkinnedMeshRenderer`, `Material`, and `Shader`. The human runner is launched
from the normal Unity Editor window and writes to an external directory.

Unity 6 is not controlled by Codex in this environment because an official
Unity MCP connector is unavailable. No unofficial automation fallback is used.
