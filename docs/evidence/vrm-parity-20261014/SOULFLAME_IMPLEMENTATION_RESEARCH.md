# SoulFlame research — acquisition only, r2

2026-10-14 UTC. **Detailed implementation analysis DEFERRED until actual ABC results are saved.** This document records authorized normal preparation only. No source algorithms, DLL decompilation, execution or installation were performed. No third-party source or distribution archive is committed.

## Verified distribution

Official index: <https://cucumberworks.github.io/vpm/index.json>, reached from <https://github.com/CucumberWorks/vpm>.

Package `com.soulflame.vrm-exporter`, version `0.6.1`; ZIP <https://github.com/CucumberWorks/vpm/releases/download/0.6.1/com.soulflame.vrm-exporter-0.6.1.zip>.

| Artifact | SHA256 |
| --- | --- |
| Official ZIP, computed locally and matching index `zipSHA256` | `4700a5e0e445f2248db7fa569b2856ae58be997904a5a6050471195561944fb7` |
| Extracted package.json | `753c15c14092d12ad1a2e5d54be9eb97e9c10f1c6203afdb2416cc960e7cf5d0` |
| LICENSE.md | `767386af8d00fec439346442a9d326f268e635934a5c0cc0571947ee1499f3df` |
| THIRD_PARTY_NOTICES.md | `51274424eebc0dee3478a8b24f057c5f9351e555dfb1d459b287ab964025cbe1` |

Local read-only inventory: 1,069 `.cs` files including bundled dependencies; zero `.dll` files. Count doesn't assert all upstream source is present. Release archive hash is pinned; no SoulFlame source-repository commit identity was established. Package license is MIT, copyright 2026 CucumberWorks. Reuse/redistribution must retain applicable copyright/permission notices and individual dependency notices. No unconditional copying decision is made.

package.json requests Unity `2022.3`, release `22f1`; Mathematics `1.2.6`, modules animation/imageconversion/imgui `1.0.0`, Timeline `1.7.6`. README requires Linear and documents embedded, renamed UniVRM 0.131.2; embedded UniGLTF/VRM license headers were read as MIT. It documents optional supported versions of NDMF, lilToon, Poiyomi and SDK; these are preparation prerequisites rather than measured compatibility. Do not upgrade existing projects or remove existing packages following generic README guidance. NDMF 1.8.0 is documented unsupported. Exact provider versions and permissions must be pinned on the owned project before running B/C.

README documents Play Mode selected-appearance VRM1.0 export and lack of a standalone VRM importer from installing this exporter. Therefore a separately pinned UniVRM import installation is necessary for R return. Compatibility with installed VRM0 converters must be checked without modifying another task's project.

## Other tools, provisional pins

| Tool | Official source | Preparation status |
| --- | --- | --- |
| VAPB | <https://github.com/UkkyaGuiyo/vapb> | Base full SHA in comparison report; GPL-3.0 repository, helper licensing remains per LICENSES.md; runtime artifact not built |
| Blender VRM Add-on | <https://github.com/saturday06/VRM-Addon-for-Blender/releases/tag/v4.10.2> | Official legacy ZIP acquired, no install; tag commit `51aef7c86295d9d98e75511875a27f20f83926d4`; LICENSE_MAIN.txt states MIT OR GPL-3.0-or-later |
| UniVRM Unity import | <https://github.com/vrm-c/UniVRM/releases/tag/v0.131.2> | Candidate 0.131.2 to match writer; official tag commit `a4711bbf8c4d10659d3e5568c2e3d7d595005e51`; standalone artifact/hash/license inventory pending; embedded MIT headers verified only for bundled copies |
| VRChatConverter | <https://github.com/esperecyan/VRMConverterForVRChat> | Optional; exact version, license, dependencies and VRM1 input support unverified; never silently route through VRM0 |
| NDMF VRM exporter | <https://github.com/hkrn/ndmf-vrm-exporter> | Separate implementation/reference, not proven SoulFlame upstream; repository exposes MPL-2.0 license; pin/source analysis deferred |

Blender Add-on archive: <https://github.com/saturday06/VRM-Addon-for-Blender/releases/download/v4.10.2/VRM_Addon_for_Blender-4_10_2.zip>; locally computed SHA256 `c02baf55b83a409fbc01e5c1912d7c8eff2807ce1a23d20eb6c049d1fb1d469c`. This is a recorded local artifact hash, not a claim of matching an independently signed upstream digest. Runtime validation and archive-contained license inventory remain pending.

## Post-ABC questions (all NOT_RESEARCHED)

Trace non-destructive capture ownership and cleanup; material retention/conversion/baking and shader extension handling; dependency detection/version gates; mesh/skin/shape conversion and normalization; serialized data retention vs regeneration; failure recovery/temporary artifact cleanup; cache identity/invalidation and stale-input behavior. For each, pin source revision/hash and specific file/line, distinguish documented claims/static implementation/runtime evidence, and retain failure cases from ABC. No findings are inferred from class names or marketing. Source presence permits later static analysis; no decompilation is necessary for this archive inventory.

Any proposed VAPB integration is a separate design decision with license/attribution review. MIT availability does not erase bundled notices, and MPL reference code has separate obligations. Current acquisition does not authorize shipping copied code.

2026-10-14 11:51 clarification prioritizes extraction/conversion, Primitive-Material association, non-destructive snapshots, performance, identity, safe failures, cache/hash and glTF/VRM transport. Shader/PhysBone approximations are learning subjects, not mandatory ports. Assess a 3D-transport plus existing Unity Manifest/Recipe composite only after measured fidelity, face/material, bones/weights/shapes/identity, non-Humanoid scope, time/actions and dependency maintenance evidence. No detailed algorithms have been read and this prep record does not unlock that gate.
