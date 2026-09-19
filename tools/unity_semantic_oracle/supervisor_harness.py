"""Non-Unity supervisor state model used by Milestone 2 tests.

The harness deliberately does not start Unity. It validates the durable
supervisor/worker protocol and models fresh-attempt retry/quarantine behavior.
"""

from dataclasses import dataclass, field
from pathlib import Path
import hashlib
import json
import uuid

from .worker_protocol import WorkerRequest, WorkerResult, atomic_json_write, read_json, result_from_dict, validate_request
from .worker_template import check as check_template, prepare as prepare_template


@dataclass
class Attempt:
    worker_id: str
    attempt_id: str
    workspace: Path
    state: str = "CREATED"


@dataclass
class SupervisorHarness:
    root: Path
    template_root: Path
    template_manifest: Path
    run_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    package_states: dict[int, str] = field(default_factory=dict)
    attempts: list[Attempt] = field(default_factory=list)
    active_attempts: dict[int, str] = field(default_factory=dict)
    requests: dict[str, WorkerRequest] = field(default_factory=dict)
    active_worker_id: str | None = None
    human_run_confirmed: bool = False
    run_state: str = "CREATED"

    @property
    def template_hash(self) -> str:
        return json.loads(self.template_manifest.read_text(encoding="utf-8"))["templateHash"]

    def confirm_human_run(self) -> None:
        self.human_run_confirmed = True
        self.run_state = "HUMAN_RUN_CONFIRMED"

    def allocate(self, package_index: int, package_path: Path, template_id: str, template_hash: str) -> tuple[WorkerRequest, Attempt]:
        if not self.human_run_confirmed:
            raise RuntimeError("HUMAN_CONFIRMATION_REQUIRED")
        if self.package_states.get(package_index) == "COMPLETE":
            raise RuntimeError("PACKAGE_ALREADY_TERMINAL")
        if package_index in self.active_attempts:
            raise RuntimeError("PACKAGE_ATTEMPT_ALREADY_ACTIVE")
        if self.active_worker_id is not None:
            raise RuntimeError("WORKER_ALREADY_ACTIVE")
        template_errors = check_template(self.template_root, self.template_manifest)
        if template_errors:
            raise ValueError("TEMPLATE_INVALID:" + ";".join(template_errors))
        if template_hash != self.template_hash:
            raise ValueError("TEMPLATE_HASH_MISMATCH")
        trusted_template_id = json.loads(self.template_manifest.read_text(encoding="utf-8")).get("templateId")
        if template_id != trusted_template_id:
            raise ValueError("TEMPLATE_ID_MISMATCH")
        attempt_number = sum(1 for item in self.attempts if item.worker_id.startswith(f"worker_{package_index:04d}_")) + 1
        worker_id = f"worker_{package_index:04d}_{attempt_number:02d}"
        attempt_id = uuid.uuid4().hex
        workspace = self.root / f"run_{self.run_id}" / worker_id
        package_hash = hashlib.sha256(package_path.read_bytes()).hexdigest()
        request = WorkerRequest(self.run_id, worker_id, package_index, str(package_path), package_hash, template_id, template_hash, "2022.3.62f3", str(workspace), attempt_id=attempt_id, nonce=uuid.uuid4().hex)
        errors = validate_request(request.to_dict())
        if errors: raise ValueError(";".join(errors))
        manifest_copy = workspace.parent / f"{worker_id}.template.json"
        prepare_template(self.template_root, workspace, manifest_copy)
        copied_errors = check_template(workspace, manifest_copy)
        copied_manifest = json.loads(manifest_copy.read_text(encoding="utf-8"))
        if copied_errors or copied_manifest.get("templateId") != trusted_template_id or copied_manifest.get("templateHash") != template_hash:
            raise ValueError("WORKER_TEMPLATE_ATTESTATION_FAILED")
        atomic_json_write(workspace / "worker-request.json", request.to_dict())
        attempt = Attempt(worker_id, attempt_id, workspace, "CREATED")
        self.attempts.append(attempt)
        self.requests[attempt_id] = request
        self.active_attempts[package_index] = attempt_id
        self.active_worker_id = worker_id
        self.run_state = "RUNNING"
        self.package_states[package_index] = "STARTING"
        return request, attempt

    def accept_result(self, request: WorkerRequest, result: WorkerResult) -> None:
        bound_request = self.requests.get(request.attempt_id)
        if bound_request is None or request != bound_request:
            raise ValueError("REQUEST_IDENTITY_MISMATCH")
        active_attempt = next((item for item in self.attempts if item.attempt_id == self.active_attempts.get(bound_request.package_index)), None)
        if active_attempt is None or active_attempt.attempt_id != request.attempt_id or active_attempt.state in {"CRASHED", "FAILED", "TIMED_OUT", "QUARANTINED"}:
            raise ValueError("STALE_OR_QUARANTINED_ATTEMPT")
        errors = result.validate_against(bound_request)
        if errors:
            raise ValueError(";".join(errors))
        attempt = active_attempt
        attempt.state = "COMPLETE"
        self.package_states[bound_request.package_index] = "COMPLETE"
        self.active_attempts.pop(bound_request.package_index, None)

    def accept_result_file(self, request: WorkerRequest, result_path: Path) -> None:
        self.accept_result(request, result_from_dict(read_json(result_path)))

    def quarantine(self, attempt: Attempt, state: str = "CRASHED") -> None:
        if state not in {"FAILED", "CRASHED", "TIMED_OUT"}:
            raise ValueError("INVALID_QUARANTINE_STATE")
        package_index = int(attempt.worker_id.split("_")[1])
        if self.active_attempts.get(package_index) != attempt.attempt_id or self.active_worker_id != attempt.worker_id:
            raise ValueError("STALE_OR_QUARANTINED_ATTEMPT")
        attempt.state = state
        self.package_states[package_index] = state
        self.active_attempts.pop(package_index, None)
        self.active_worker_id = None

    def dispose(self, attempt: Attempt) -> None:
        package_index = int(attempt.worker_id.split("_")[1])
        if attempt.state != "COMPLETE" or self.package_states.get(package_index) != "COMPLETE":
            raise RuntimeError("WORKSPACE_NOT_COMPLETE")
        if self.active_worker_id != attempt.worker_id:
            raise RuntimeError("STALE_OR_DISPOSED_ATTEMPT")
        attempt.state = "DISPOSED"
        self.active_worker_id = None

    def fresh_retry(self, package_index: int) -> bool:
        return any(item.worker_id.startswith(f"worker_{package_index:04d}_02") for item in self.attempts)
