# Shader Semantic / Behavior Oracle v0.1

This research tool characterizes Unity Material metadata through public
interfaces and produces a conservative Shader Preview IR. It is isolated from
the Blender importer runtime and is not a shader implementation or a shader
decompiler.

## Evidence boundary

The metadata survey reads only UnityPackage `pathname` and text `asset`
members for `.mat` assets. Texture payloads and shader binaries are not
decoded. Unity observations, when run, must use normal Unity Editor batch
automation and public APIs such as `AssetDatabase`, `Material`, and `Shader`.

The IR distinguishes `DETECTED`, `NOT_OBSERVED`, and `NOT_TESTED`; absence of
a property is not proof that a shader lacks a behavior. Dynamic, view-, light-,
and renderer-dependent behavior remains `NOT_TESTED` unless a controlled Unity
observation proves it.

## Generic behavior vocabulary

The initial IR covers base surface, alpha/cutout, normal, emission,
metallic/smoothness, rim/Fresnel, toon-lighting hints, and UV behavior. The
reserved extension vocabulary is: height/cavity, roughness, matcap,
time-animation, view-dependent, light-dependent, billboard, vertex deformation,
outline, multi-pass, stencil-dependent, custom-geometry assumption, and
unknown-dynamic.

## Private survey

Run the survey with a private output directory outside the repository:

```text
python -m tools.shader_semantic_oracle.survey --root <private-corpus> --output-root <private-diagnostics>
```

The output contains raw local evidence and must never be committed. The
repository may contain only generic tooling, synthetic fixtures, tests, and
privacy-safe aggregate documentation.

## Non-goals

- no Blender production behavior change;
- no private Unity implementation inspection or decompilation;
- no commercial shader/material/texture payloads in Git history;
- no inference that a property-name match reproduces a shader.
