# Package Composition Automatic Mode

Automatic mode plans the package as a composition; it does not select one
"main" Prefab. Candidate analysis produces editable members, helper metadata,
and reusable FBX representations.

## Rules

- Body variants, outfits, accessories, and structurally supported unknown
  visual members are all retained.
- Provider-only materials/textures and visual-free helpers are not top-level
  editable members. A helper is preserved as metadata and may become an
  anchor when a relationship requires it.
- A representation is keyed by package-scoped FBX identity. Native FBX import
  is scheduled once per representation; member realizations use separate
  Blender Objects while sharing source Mesh/Armature datablocks. Effective
  Renderer material state is stored with OBJECT-linked material slots, so a
  material override never mutates a sibling member's Mesh table.
- Prefab Variants are resolved from effective state, not from whether a raw
  YAML file happens to contain a Renderer document. Multiline target refs,
  source GUID/fileID identity, and unknown modification payload are preserved
  for round-trip-aware diagnostics.
- Missing visual dependencies remain a dependency-resolution result. They are
  not converted into an archive-order or filename-based choice.
- Automatic requires a chooser only for ambiguous providers or another
  genuinely incompatible identity interpretation. Multiple compatible bodies
  and outfits do not require a chooser.

The planner is implemented by `PrefabCandidateAnalyzer.compose`. The legacy
`PrefabSelection` remains for explicit single-Prefab UI compatibility and
`RAW_FBX`; it is not the Automatic composition decision.

## Blender layout

Generated objects are grouped under a package collection with `Members` and
`Shared` children. Each editable member receives its own child collection and
stores package/member identity as custom properties. Shared representations
are reused at the datablock level; member-specific material overrides are
applied to the member realization. A synthetic wrapper uses the unique
Transform root name when available and a neutral prefab asset name for
multiple roots; it never uses an arbitrary first serialized child.

No product name, GUID value, filename, or archive order is used as a rule.
