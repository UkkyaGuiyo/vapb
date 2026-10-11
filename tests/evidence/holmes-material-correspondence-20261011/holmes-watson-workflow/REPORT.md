# HOLMES-WATSON workflow setup and bounded dry run

User request dated 2026-10-11 17:43:39 UTC. Scope: configure and actually test one fresh Holmes inference; no new product work. Setup branch `feature/holmes-watson-workflow-20261012`, product base `b0ff93ce5b1a18bd5c399f9566653a9b99962def`. HOLMES-02 product result is separately VERIFIED_IN_SCOPE; its29 changed files were fetched from GitHub and matched Git blobs before this setup began. No ongoing product experiment remains.

## Configuration

Project `.codex/agents/holmes.toml` uses the current official standalone custom-agent schema: name, description and developer_instructions, with supported model/reasoning/sandbox keys. The user requested Extra High at the instruction opening; it takes precedence over the medium example. File settings: GPT-6.1 Sol / xhigh / read-only; approval never and nested agents disabled narrow the role. Local model catalog lists xhigh. Requested/file settings are not actual runtime proof. Global config and existing personal agents unchanged.

AGENTS.md received only an appended bounded HOLMES-WATSON LOOP; preflight.json hashes the previous bytes and verifies the entire original byte prefix remains unchanged. Existing model split, independent SOL/medium code review, Failure Atlas, GitHub save and original/resource/budget protection remain. Three maximum cycles, early stop gates, nonautomatic proposal approval and session restart procedure are explicit. No daemon, scheduler or new management system.

Official sources consulted: [Subagents/custom agents](https://learn.chatgpt.com/docs/agent-configuration/subagents), [configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference). The fetched subagents page documents project standalone TOML and warns that parent live sandbox/approval overrides are reapplied when children spawn. Therefore configured read-only alone is insufficient.

The callable native spawn tool offers task_name/fork_turns/model/reasoning_effort, but exposes no custom-agent type or sandbox selector. Bundled CLI0.162.0-alpha.17.2 help was read; exec offers session sandbox options but no direct custom-agent selector. Starting a separate CLI session would not establish the requested same-session workflow and is not used as a workaround. Actual spawn/read-only verification is pending after setup save.

## Authority and dry-run packet

Existing fixed instruction `docs/holmes-watson-handoff:HOLMES_TO_WATSON.md` was read from GitHub, blob `8b47a2e9624c51ccac1b2b4cf595ef9fa92cea63`. It still says READY HOLMES-20261011-02 and references an older development checkpoint. The newer CHAT_FALLBACK HOLMES-20261012-02 and this workflow request govern; completed IDs are not rerun. No fixed instruction update or merge occurred, so no new instruction-blob mutation was needed.

Select saved HOLMES-02 raw evidence at exact `b0ff93ce5b1a18bd5c399f9566653a9b99962def` for the first dry run: A/B final-native, final-weight, final-export, preservation and negative-checks, plus actual product code and approved PRODUCT_SPEC. Do not provide the prior REPORT/REVIEW/verdict or Watson's inference. First verify real child isolation and read-only policy through exposed runtime metadata. No destructive write probe, permission escalation or application launch. If unavailable, stop BLOCKED without replacing Holmes with Watson self-review. Receive a verifiable result or a precise blocker, then save it and independently check the cited facts. Configuration success does not authorize further product development.

## Current stop and restart point

**BLOCKED_BEFORE_DRY_RUN / LOCAL_ONLY.** Automatic approval review rejected the configuration commit/push: it could not establish direct human authorization for persistent AGENTS/custom-agent workflow changes and publishing the separate workflow branch, distinguishing that scope from the approved HOLMES-02 product work. The rejected shell command did not execute; no configuration commit or push occurred. A read-only request for the parent task's human message returned no turns, so it did not supply the missing authorization evidence. No workaround or indirect execution was attempted.

Explicit human confirmation was requested for the concrete prepared files and normal configuration-branch save/dry run. Until received, the setup is locally preserved and no Holmes dry-run spawn is attempted, consistent with the loop's GitHub-save-failure stop. Existing product result remains saved/readback-verified. Effective custom read-only, custom-role loading, runtime xhigh and dry-run inference are UNVERIFIED/NOT_RUN. No Watson self-review replaces Holmes.

Restart: after explicit authorization, review the prepared diff, normally commit/push these setup files on `feature/holmes-watson-workflow-20261012`, fetch every changed GitHub file at exact SHA, then attempt one fresh native `holmes` spawn. Verify exposed permissions/config loading before analysis; stop BLOCKED if the current native tool/parent overrides cannot honor the read-only role. Do not start a separate CLI session to bypass that limitation. Save the actual result and parent verification; do not continue product development automatically. Configuration/evidence currently remain uncommitted at product base `b0ff93ce5b1a18bd5c399f9566653a9b99962def`.


Authorization continuation: direct human request excerpts for project custom-agent configuration, minimal AGENTS addition, actual dry run and GitHub evidence saving were supplied after the initial refusal. One retry through the original automatic-review path is authorized; no indirect workaround. Until that retry succeeds, configuration persistence and dry-run execution remain pending.
