# Real Package Shader Probe Lifecycle v0.1

This research-only controller hardens real UnityPackage shader probing without
changing Blender importer behavior.

## Root cause

The previous flow coupled package import, callback continuation, material
enumeration, and rendering to one Unity process and in-memory static state. A
real package did reach Unity's asset pipeline, including FBX and Material
imports, but the expected continuation did not produce the result JSON. The
callback was treated as the only continuation signal and the process depended
on `-quit`; this made a domain reload or callback/lifecycle boundary
indistinguishable from an import failure.

## New flow

The controller uses two disposable Unity launches:

1. Import phase: request `AssetDatabase.ImportPackage`, persist durable state,
   observe Material assets and compilation state, and require three stable
   editor update frames before writing `IMPORT_STABLE`.
2. Probe phase: relaunch the same project, load `IMPORT_STABLE`, enumerate
   Materials/Shaders through public APIs, perform a GPU render and controlled
   color perturbation, persist results, and exit cleanly.

Callbacks are logged as evidence but are not the success condition. If assets
are present and stable without a callback, the state is classified as
`IMPORT_CALLBACK_MISSING_BUT_ASSETS_PRESENT`.

## Durable states and timeout categories

States include `NEW`, `IMPORT_REQUESTED`, `ASSETS_OBSERVED`,
`COMPILATION_PENDING`, `IMPORT_STABLE`, `PROBE_STARTED`, `PROBE_COMPLETE`, and
`FAILED`. Phase categories include import process, callback, asset discovery,
compilation, editor stabilization, and probe timeouts.

## Boundary

The code uses only documented Unity Editor APIs: `AssetDatabase`,
`EditorApplication`, `AssemblyReloadEvents`, `Material`, `Shader`, `Camera`,
`RenderTexture`, and `Texture2D`. It does not inspect or copy Unity internals,
decompile binaries, or modify the Blender addon runtime.
