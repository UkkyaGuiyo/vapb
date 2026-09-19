# Unity Access Compliance

## Unity access method

- Unity 2022.3: human-started normal Editor window, `HumanOracleRunnerWindow`,
  documented public Editor APIs.
- Unity 6: official Unity MCP is required; unavailable in the current Codex
  connector set, so no Unity 6 automation was performed.
- UnityMCP installed: no.
- Fallback used: no unofficial fallback; the Unity 6 gate remains explicit.

## Compliance check

- Documented/public Unity APIs only: PASS for the new runner.
- Unity binary decompilation: NO.
- Private/internal Unity implementation copied: NO.
- Commercial asset payload committed: 0.
- Commercial raw diagnostic committed: 0.

Historical AI-initiated Unity 2022.3 CLI experiments are labeled legacy and
require revalidation through the compliant human route.
