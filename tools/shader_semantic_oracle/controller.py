"""Two-phase disposable Unity controller for real-package research probes."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path

from .lifecycle import FailureCategory


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def run_unity(unity: Path, project: Path, method: str, environment: dict[str, str], log: Path, timeout: int) -> tuple[int | None, str | None]:
    env = os.environ.copy()
    env.update(environment)
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("w", encoding="utf-8") as stream:
        process = subprocess.Popen([str(unity), "-batchmode", "-projectPath", str(project), "-executeMethod", method, "-logFile", str(log)], env=env, stdout=stream, stderr=subprocess.STDOUT)
        try:
            return process.wait(timeout=timeout), None
        except subprocess.TimeoutExpired:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            return None, FailureCategory.IMPORT_PROCESS_TIMEOUT.value


def run_session(unity: Path, project: Path, package: Path, state_path: Path, result_path: Path, render_path: Path, logs: Path, minimum_assets: int, import_timeout: int, probe_timeout: int) -> dict:
    state = {"package": str(package), "minimumAssets": minimum_assets, "status": "NEW", "events": []}
    _write(state_path, state)
    import_env = {
        "UNITY_SHADER_ORACLE_PHASE": "import",
        "UNITY_SHADER_ORACLE_PACKAGE": str(package),
        "UNITY_SHADER_ORACLE_STATE": str(state_path),
        "UNITY_SHADER_ORACLE_MIN_ASSETS": str(minimum_assets),
    }
    code, timeout = run_unity(unity, project, "ShaderSemanticOracle.LifecycleProbe.Batch", import_env, logs / "import.log", import_timeout)
    state = _read(state_path)
    if timeout:
        state["status"] = "FAILED"
        state["failureCategory"] = timeout
        _write(state_path, state)
        return state
    if state.get("status") != "IMPORT_STABLE":
        state["status"] = "FAILED"
        state["failureCategory"] = state.get("failureCategory") or FailureCategory.ASSET_DISCOVERY_TIMEOUT.value
        _write(state_path, state)
        return state
    probe_env = {
        "UNITY_SHADER_ORACLE_PHASE": "probe",
        "UNITY_SHADER_ORACLE_STATE": str(state_path),
        "UNITY_SHADER_ORACLE_RESULT": str(result_path),
        "UNITY_SHADER_ORACLE_RENDER_OUTPUT": str(render_path),
    }
    code, timeout = run_unity(unity, project, "ShaderSemanticOracle.LifecycleProbe.Batch", probe_env, logs / "probe.log", probe_timeout)
    state = _read(state_path)
    if timeout:
        state["status"] = "FAILED"
        state["failureCategory"] = FailureCategory.PROBE_TIMEOUT.value
    elif state.get("status") != "PROBE_COMPLETE":
        state["status"] = "FAILED"
        state["failureCategory"] = state.get("failureCategory") or FailureCategory.PROBE_TIMEOUT.value
    _write(state_path, state)
    return state


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--unity", type=Path, required=True)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--render", type=Path, required=True)
    parser.add_argument("--logs", type=Path, required=True)
    parser.add_argument("--minimum-assets", type=int, default=1)
    parser.add_argument("--import-timeout", type=int, default=180)
    parser.add_argument("--probe-timeout", type=int, default=120)
    args = parser.parse_args()
    print(json.dumps(run_session(args.unity, args.project, args.package, args.state, args.result, args.render, args.logs, args.minimum_assets, args.import_timeout, args.probe_timeout), ensure_ascii=False))


if __name__ == "__main__":
    main()
