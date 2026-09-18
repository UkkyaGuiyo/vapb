# Shader Behavior Corpus Probe v0.1

This branch contains research-only, generic shader behavior probing. It does
not modify Blender material generation, importer resolution, hierarchy, or UI.

## Evidence model

The probe keeps three evidence classes separate:

- `PUBLIC_API`: Material/Shader property schema and documented render metadata;
- `RENDER_OBSERVATION`: controlled camera, property, texture, or color changes
  measured with deterministic image differences;
- `DERIVED` and `HEURISTIC`: conservative aggregation, never a replacement for
  an observation.

`NOT_OBSERVED` means a relevant public property was inspected and not found.
`NOT_TESTED` means the experiment was not safe or sufficient to evaluate the
behavior. These states must not be merged.

## Generic vocabulary

The initial vocabulary is intentionally small: base color/texture, normal,
height/cavity, metallic/smoothness, alpha, emission, rim/Fresnel, toon lighting,
UV behavior, time animation, view dependence, light dependence, billboard,
vertex deformation, outline, multi-pass, stencil dependence, and unknown
dynamic behavior.

Shader names are never used as semantic detectors. A property-name hint may
produce `PROBABLE`; controlled render evidence is required for stronger claims.

## Preview IR boundary

The future `ShaderPreviewIR v0.1` is a visual projection, not a Unity source of
truth. It should preserve Unity Material/Shader identity and original values
separately from any editable Blender approximation. This branch defines the
research vocabulary only; it does not implement Blender preview nodes.

Private real-package results are stored outside the repository. Only generic
tooling, synthetic fixtures, tests, and this public-safe specification belong
in Git.
