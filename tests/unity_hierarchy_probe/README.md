# Independent semantic hierarchy Oracle — phase 1 checkpoint

Status: **PARTIAL**. Unity observation is verified; Unity ↔ Blender parity is
**UNVERIFIED**. No production behavior was changed.

Use a new, isolated Unity 2022.3.22f1 project with standard Unity modules.
Copy `Editor/VapbHierarchyOracle.cs` to its `Assets/Editor/` directory.
Generate `Assets/VapbHierarchy/Model.fbx` using Blender 5.2.1:

```text
VAPB_HIERARCHY_MODEL=<isolated project>/Assets/VapbHierarchy/Model.fbx
blender --background --factory-startup --python-exit-code 1 --python tests/blender_hierarchy_oracle_fixture.py
VAPB_HIERARCHY_OUTPUT=<evidence directory outside repository>
Unity -batchmode -nographics -projectPath <isolated project> -executeMethod VapbHierarchyOracle.Run -logFile <evidence directory>/unity.log
```

Environment variables must be set in the invoking shell. The Unity probe creates
or replaces `Assets/VapbHierarchy/Accessory.prefab` and `Majun.prefab`; run it only
in the isolated synthetic project. It writes `unity_oracle.json` and exports the
corresponding `Majun.unitypackage`. Failure explicitly exits Unity with code 1.

## Observed baseline, 2026-09-30

- Blender fixture generation: exit 0, `VAPB_HIERARCHY_FIXTURE_PASS`.
- Unity Editor version: 2022.3.22f1; actual Editor compilation and execution PASS.
- Unity execution: exit 0, `VAPB_HIERARCHY_ORACLE_PASS`.
- Semantic nodes: 12; parent edges: 11; Renderer owners: 1.
- Skin bones: 2; rootBone present; repeated accessory instances: 2.
- Repeated instances share exact source GUID/localID and have distinct instance
  handles and Transform GlobalObjectIds.
- The fixture includes Head/Face/Hair, two nested accessory instances and an
  attachment under the second Bone. It contains a Model root named Armature
  **and** the FBX Rig child; both are Unity semantic Transforms. This accounts
  for the additional node relative to the eleven-node illustrative hierarchy.

The skin model is unpacked before creating the synthetic prefab so children can
be rearranged using public APIs. Its Mesh remains an FBX subasset reference;
its prefab GameObjects/Bones do not claim an inherited FBX GameObject source
chain. The accessory instances retain their actual source/instance relations.
Names are diagnostic labels, not correspondence keys. Skin bone order is
observed from `SkinnedMeshRenderer.bones`, not inferred from names.

Recorded `unity_oracle.json` is direct public-API output, independent of VAPB
parsers/projection. It includes GUID/signed localID/GlobalObjectId, parent
Transform references, source chains, ordered ancestor instance handles,
Renderer owner/Mesh/rootBone/ordered bones, local TRS and world matrices.
Matrix arrays use Unity Matrix4x4's single-index order (column-major).

Generated public synthetic artifacts remain outside Git. SHA-256 for this run:

| Artifact | SHA-256 |
| --- | --- |
| Majun.unitypackage | `358df2fed2c0b00825c3aacde8f78f8d9027e0b55bf3855a96c4f2ccc6a22098` |
| Model.fbx | `0bbe404623f074ff08666416aa3525346df62ad62691285e17b3b154bd0a9ce3` |

Re-running generation creates a new revision/IDs. Always compare the Oracle
against its own exported package, never a previous Oracle against regenerated
input. Recorded IDs are entirely synthetic. No private corpus was used.

## Remaining acceptance work

Next action: normally import this exact exported package into Blender and
capture occurrence/receipt-based semantic state before any production change.
Then build the independent comparator, obtain baseline RED/GREEN, investigate
any divergence, and verify rename/save/reopen and negative controls.

Blender node/edge/Renderer/Bone/technical-helper counts, parity enum counts,
placement/local/world agreement, save/reopen, negative controls and full Python
regressions are **NOT RUN** for this mission. Earlier 438-test evidence belongs
to the unchanged predecessor and is not a fresh hierarchy acceptance run.
No axis/unit model was changed. Geometry regression need remains undecided
until a concrete production fix is identified. Broad Unity/VRC restoration,
Release/ZIP and private validation were not started.

The phase 1 checkpoint was selected to preserve the requested 15+ credit
reserve from the observed 18.2968137500 opening balance. In-session usage is
not reflected reliably by that balance; unchanged balance is not proof of zero
spend. Only the required read-only scope reviewer was delegated (PASS).
