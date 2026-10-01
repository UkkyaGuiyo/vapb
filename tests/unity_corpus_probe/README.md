# Independent corpus source observation

Copy `Editor` into `Assets/CorpusProbe/Editor` of a fresh private Unity project.
The isolated Editor assembly references built-in Unity APIs only.

Run Unity with `-batchmode -nographics -projectPath <private-project>`
`-executeMethod VapbCorpusSourceCapture.Run --vapb-context <context.json>`
`--vapb-result <result.json> -logFile <private-log>`. Do not pass `-quit`:
package callbacks and domain reloads finish before the probe exits.

Context JSON contains `package_paths` (absolute paths, dependency packages in
the required import order followed by the tested package), `prefab_guids`
(the exact distinct imported prefab root GUIDs to observe), and optional
`timeout_seconds` (default 300). The caller supplies the population; the probe
never scans arbitrary project folders or infers root selections from names.

The private result reports persistent public-API GUID/local identities,
GlobalObjectIds, nested instance roots, corresponding source chains, renderer
occurrences, skin bones/root, material identities, shape counts and missing
scripts. Array order preserves actual Unity bone/material slots, and is never
used to infer identity. Missing references are null. No binding or export is
performed. Population completeness means all requested prefab roots loaded;
it does not certify caller population coverage or any Blender correspondence.
Incomplete or failed capture uses `-1` for unproven aggregate counts. Compile
failures after package import are `BLOCKED/ENVIRONMENT_FAILURE`, not zero skins.
Package callbacks are accepted only for the current requested package basename.
After synchronous refresh the probe waits for idle Editor updates and requested
assets to exist (up to ten seconds) before declaring population completeness.
The caller must also classify startup compilation/Editor process failures when
Unity cannot invoke the helper and no result is written. Private logs and result
files must remain outside Git.

The helper appends private lifecycle observations beside its result as
`<result-stem>.lifecycle.jsonl`, including package callbacks before filtering,
assembly reload events and a heartbeat every thirty seconds. Callback names
track import invocation only. They do not establish asset or occurrence identity.

Callback invocation comparison removes only a known `.unitypackage` suffix;
it preserves dotted version labels in an already extensionless callback name.
Compile `CallbackNameRegression.cs` together with
`Editor/VapbCorpusPackageCallback.cs` for seven pure C# controls requiring no
Unity dependencies, including stale and unrelated callbacks.

For a source archive whose native package-import capture is not proven, the
independent Oracle can instead observe exact source assets staged by
`tests/stage_corpus_source_assets.py`. This is a harness route, not a VAPB import
dependency or production Output workaround. The adapter requires exact original
package hashes, a fresh private project and conflict-free GUID/path/meta records.
It copies all assets, including scripts, and verifies each asset/meta file.

The generated context explicitly selects `EXACT_ASSET_EXTRACTION_CAPTURE`,
requires its project/package/file/root staging lock and retains
`native_import_status=NOT_PASS`. The source helper validates the lock read-only,
skips ImportPackage and Refresh, and reports packages_imported=0 separately
from packages_extracted. Changed source hashes or staged asset/meta bytes reject
capture. Unity's automatic startup import may itself rewrite meta files; those
changes remain an explicit unproven staging result, not silently accepted.
