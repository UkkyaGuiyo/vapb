# VAPB Unity Semantic Oracle: Compliant Harvest and Round-Trip Design

## Scope

This design adds a reproducible observation boundary for VAPB. Unity remains
an observation oracle; Blender-side code remains an independent implementation.
The public repository stores schemas, synthetic fixtures, aggregate results,
and tooling. Commercial package payloads, raw Unity JSON, GUID tables, and
machine-specific paths remain outside the repository.

## Access boundary

- Unity 6: use the official Unity MCP when that connector is available. The
  current Codex connector set has no Unity MCP tool, so Unity 6 observations
  are recorded as `UNAVAILABLE_OFFICIAL_MCP` rather than guessed.
- Unity 2022.3: the runner is started by a human inside the normal Unity
  Editor. It uses documented public Editor APIs only. Codex reads the output
  after the human run; Codex does not launch or control this Editor.
- Historical AI-initiated Unity 2022.3 CLI evidence is retained only as
  `LEGACY_REVALIDATION_REQUIRED` and is not treated as current compliant
  evidence.

## Data model

Every observation has separate `observed`, `derived`, and `limitations`
sections. `observed` contains facts read from Unity public APIs. `derived`
contains deterministic calculations made by repository tooling. A report must
never promote a derived result to an observed fact.

The envelope includes schema version, run id, access method, Unity version,
case id, checkpoint state, and sanitization status. Raw local outputs are
written outside the repository. Public summaries contain counts and stable
synthetic case identifiers only.

## Human-runner lifecycle

The Unity 2022.3 Editor window accepts an explicit external output directory,
package paths, and optional prefab filter. A human presses Run. The runner
writes `RUNNING`, one case checkpoint per completed observation, and finally
`COMPLETE` or `FAILED`. A later run resumes only cases whose checkpoint is not
complete. No package path or payload is embedded in committed source.

## Differential loop

The Python diff tool compares sanitized observation envelopes. It reports
added, removed, and changed semantic paths, identity changes, unresolved
references, and unsupported fields. It supports no-op, controlled mutation,
cleanup, reimport, and save/reopen cases without asserting byte identity.

## Automatic candidate investigation

Candidate ranking is evidence-driven: Unity public API realization, renderer
coverage, dependency completeness, and deterministic tie handling are recorded
as observed/derived fields. No filename, object name, GUID order, first
candidate, or all-FBX heuristic is accepted as a semantic rule. Ambiguous
cases remain explicit and are not auto-selected.

## Version matrix

The same case id may be observed in Unity 2022.3 and Unity 6, but results are
compared only through declared semantic fields. Version-specific unsupported
fields are reported, not silently ignored.

## Non-goals

This change does not implement the Blender importer, copy Unity shader code,
decompile Unity, access private Unity internals, or claim a complete real
corpus harvest before the human-gated runs exist.
