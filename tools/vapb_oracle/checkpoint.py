"""Atomic, resumable external checkpoint state."""

from __future__ import annotations

import json
import os
from enum import Enum
from pathlib import Path
from typing import Any


class RunState(str, Enum):
    RUNNING = "RUNNING"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


class CheckpointStore:
    def __init__(self, path: Path):
        self.path = Path(path)

    def _read(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"state": RunState.RUNNING.value, "cases": {}}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _write(self, payload: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temporary, self.path)

    def start(self, case_ids: list[str]) -> None:
        current = self._read()
        cases = current.setdefault("cases", {})
        for case_id in case_ids:
            cases.setdefault(case_id, {"state": "PENDING"})
        current["state"] = RunState.RUNNING.value
        self._write(current)

    def state(self) -> RunState:
        return RunState(self._read().get("state", RunState.RUNNING.value))

    def pending_cases(self) -> list[str]:
        return [case_id for case_id, data in self._read().get("cases", {}).items()
                if data.get("state") != "COMPLETE"]

    def complete_case(self, case_id: str, result: dict[str, Any]) -> None:
        current = self._read()
        current.setdefault("cases", {})[case_id] = {"state": "COMPLETE", "result": result}
        self._write(current)

    def finish(self, state: RunState, error: str | None = None) -> None:
        current = self._read()
        current["state"] = state.value
        if error:
            current["error"] = error
        self._write(current)
