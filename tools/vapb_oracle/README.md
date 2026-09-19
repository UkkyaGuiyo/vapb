# VAPB Oracle Tooling

This package validates sanitized Unity observation envelopes, creates aggregate
safe summaries, keeps external resumable checkpoints, and produces deterministic
semantic diffs. It never launches Unity and never reads commercial payloads.

```text
python -m unittest tests.test_vapb_oracle
```

The Unity 2022.3 human runner is under
`tools/unity_semantic_oracle/Assets/Editor/HumanOracleRunnerWindow.cs`.
Unity 6 output requires an official Unity MCP connector; no such connector is
available in the current Codex tool set.
