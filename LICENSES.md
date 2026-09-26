# License scope and source provenance

The project owner selected the following licenses for VAPB first-party source, including the first-party historical versions retained in this repository.

| Scope | License |
| --- | --- |
| Blender Add-on, Python code, tests and documentation, except the directory below | GPL-3.0-or-later; see root `LICENSE` |
| Independent Unity C# helpers and associated first-party material under `unity_editor/` | MIT; see `unity_editor/LICENSE` |

The Blender Add-on is licensed under GNU GPL version 3 or, at your option, any later version. Its entry point has an SPDX identifier. The root license is the complete GPL version 3 text; this document specifies the or-later grant and directory exception.

The Unity helpers use System and documented UnityEngine/UnityEditor APIs. They do not load or copy Blender Python code. The bridge exchanges serialized data, FBX and a manifest between separate applications. Code/history review found no copied Blender GPL implementation or vendored third-party implementation in these helpers. The owner confirmed that the legacy Material Restore helper was newly implemented with AI assistance for this project before its first Git commit; its earlier development history is not present in Git. This is the recorded provenance evidence, not a claim of a formal legal opinion or a universal absence-of-copy proof.

Each Unity helper carries the complete MIT notice so that the first-party C# source copied into a generated UnityPackage retains its permission and copyright notice. The root GPL grant does not replace that MIT grant.

## External software and asset data

Blender, Unity, VRChat SDK, their installed import/export tools and optional development MCP tools retain their own licenses and are not relicensed or vendored by this declaration. VAPB calls installed Blender FBX APIs and documented Unity public APIs; it does not include Unity implementation source or a VRChat SDK copy. Public shader identifiers and serialized field names are compatibility references, not bundled shader implementation source.

No commercial/private avatar, texture, UnityPackage or raw identity table is distributed here. These source-code licenses do not grant rights to third-party assets processed by VAPB. Imported/exported asset data remains subject to its original rights; the generated first-party Unity helpers retain their MIT notice.

No additional copied third-party implementation or attribution requirement was identified in the code/history audit. Existing third-party copyright and license notices, where present, must be retained. If new provenance evidence identifies a copied or inseparable GPL-derived helper, stop treating that portion as independently MIT until its rights are resolved.
