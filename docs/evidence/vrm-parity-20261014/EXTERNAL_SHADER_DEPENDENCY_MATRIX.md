# External shader dependencies — test contract, not measured acceptance

Owner's 2026-10-14 12:29 clarification supplements [ABC](ABC_COMPARISON_REPORT.md). Missing external Shader implementation in an input UnityPackage must not by itself prevent an otherwise editable VAPB import. Keep original Material asset/meta bytes, GUID/signed fileID, `m_Shader`, serialized properties, texture references/settings and dependency declarations. Blender approximation never supplies restoration truth. A surviving reference is not preserved content of an absent asset.

## Dependency state vocabulary

| State | Meaning | Required evidence |
| --- | --- | --- |
| A | In input Package | Exact entry/content/meta and scoped identity |
| B | In destination Unity | AssetDatabase resolution, actual material/shader object and provider/version; Package Manager providers included |
| C | Declared external, unverified | Needed provider and unresolved version/identity reason visible |
| D | Absent | Checked input/target scope and required missing dependency |
| E | Same name, identity unproved | No name-based substitute; preserve ambiguity |

A/B are locations, not compatibility guarantees. GUID equality does not prove version/property/rendering compatibility. Validate actual Shader type, needed property names/types, serialized values, texture/native Material references, edited slots and immutable face correspondence. Do not auto-install SDK/shaders or mutate settings to make a test pass. Reject unresolved/ambiguous restoration with the required dependency and reason, while allowing edit-capable input where the missing dependency does not obstruct editing.

## B1–B5 conditions

| Condition | Package Shader | Destination Shader | Expected evaluation boundary | lilToon | Poiyomi |
| --- | --- | --- | --- | --- | --- |
| B1 | Present, pinned identity/version | Resolved matching provider | Prove bytes/refs/properties + face/slot restoration | NOT_MEASURED | NOT_MEASURED |
| B2, important normal case | Absent; reference/declaration retained | Already installed matching provider | Editable import and resolved native restore; no claim absent Shader bytes were preserved | NOT_MEASURED | NOT_MEASURED |
| B3 | Absent | Absent | Editing need not fail solely for Shader absence; restoration unresolved/refused with needed provider | NOT_MEASURED | NOT_MEASURED |
| B4 | Reference identity fixed | Same-name, different GUID | No replacement by name; unresolved identity rejected | NOT_MEASURED | NOT_MEASURED |
| B5 | Reference identity fixed | Same GUID/other identity evidence but different version | Check properties and behavior scope; identity equality alone insufficient | NOT_MEASURED | NOT_MEASURED |

For each case separately record SOURCE_PRESERVED, IDENTITY_RESOLVED, UNITY_RESTORED, exact Material/Shader GUID-fileID, texture/provider state, all face/slot correspondence, native source/return material refs and asset/meta hashes. Safe refusal is distinct from successful restoration. Real lilToon/Poiyomi measurements need licensed actual providers and exact versions; a first-party same-name synthetic shader is only a synthetic identity/control test, never a representative provider result.

## Current evidence and limits

The preliminary authored Blender/glTF case has diagnostic materials only. The owned Unity source setup helper explicitly creates original first-party Standard materials; it is compiled but not executed. This is neither a missing-shader fallback nor B1/B2 lilToon/Poiyomi acceptance. No representative providers have been installed or assumed present. The new comparison Project is currently a minimal source-eligibility skeleton without SDK; it is not presented as the normal SDK-preinstalled avatar return environment. SDK must remain a declared destination dependency, never bundled in output. lilToon, Poiyomi, MA and NDMF remain explicit external providers subject to verification and authorized setup.

No product import guard was changed and no dependency was substituted. An observed missing-Shader editing failure, if later measured, requires a focused correction proposal; this contract alone is not proof of a current defect.
