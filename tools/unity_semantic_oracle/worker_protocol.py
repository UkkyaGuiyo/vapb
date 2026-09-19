"""Public-safe durable protocol primitives for one-package worker attempts."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import hashlib
import json
import os
import stat
import tempfile
import re
from typing import Any


PROTOCOL_VERSION = "1"
TERMINAL_STATES = {"COMPLETE", "FAILED", "TIMED_OUT", "CRASHED"}
REQUEST_KEYS = {"run_id", "worker_id", "package_index", "package_path", "package_sha256", "template_id", "template_hash", "unity_version", "output_directory", "prefab_filter", "protocol_version", "attempt_id", "nonce"}
RESULT_KEYS = {"run_id", "worker_id", "package_index", "package_sha256", "template_id", "template_hash", "unity_version", "observation_context", "state", "observation_path", "protocol_version", "attempt_id", "nonce", "isolation_verified"}
ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
SHA256_PATTERN = re.compile(r"^[0-9a-fA-F]{64}$")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_json_write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_name, path)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)


def write_once_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary_name, path)
        except FileExistsError as exc:
            raise FileExistsError(f"IMMUTABLE_OUTPUT_ALREADY_EXISTS:{path}") from exc
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"MALFORMED_JSON:{path}") from exc
    if not isinstance(value, dict):
        raise ValueError("JSON_ROOT_NOT_OBJECT")
    return value


def _contained(path: Path, root: Path) -> bool:
    try:
        if _has_reparse_component(path) or _has_reparse_component(root):
            return False
        resolved_path = path.resolve()
        resolved_root = root.resolve()
        resolved_path.relative_to(resolved_root)
        current = resolved_root
        for component in resolved_path.relative_to(resolved_root).parts:
            current /= component
            if current.is_symlink():
                return False
        return True
    except (OSError, RuntimeError, ValueError):
        return False


def _valid_id(value: Any) -> bool:
    return isinstance(value, str) and bool(ID_PATTERN.fullmatch(value))


def _valid_sha(value: Any) -> bool:
    return isinstance(value, str) and bool(SHA256_PATTERN.fullmatch(value))


def _valid_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value)


def _has_reparse_component(path: Path) -> bool:
    absolute = Path(os.path.abspath(path))
    candidates = [absolute, *absolute.parents]
    for candidate in candidates:
        try:
            info = os.stat(candidate, follow_symlinks=False)
        except OSError:
            continue
        if candidate.is_symlink() or bool(getattr(info, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)):
            return True
    return False


@dataclass(frozen=True)
class WorkerRequest:
    run_id: str
    worker_id: str
    package_index: int
    package_path: str
    package_sha256: str
    template_id: str
    template_hash: str
    unity_version: str
    output_directory: str
    prefab_filter: str = ""
    protocol_version: str = PROTOCOL_VERSION
    attempt_id: str = ""
    nonce: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class WorkerResult:
    run_id: str
    worker_id: str
    package_index: int
    package_sha256: str
    template_id: str
    template_hash: str
    unity_version: str
    observation_context: str
    state: str
    observation_path: str
    protocol_version: str = PROTOCOL_VERSION
    attempt_id: str = ""
    nonce: str = ""
    isolation_verified: bool = False

    def validate_against(self, request: WorkerRequest) -> list[str]:
        errors = []
        for field in ("run_id", "worker_id", "package_index", "package_sha256", "template_id", "template_hash", "unity_version", "attempt_id", "nonce", "protocol_version"):
            if getattr(self, field) != getattr(request, field):
                errors.append(f"IDENTITY_MISMATCH:{field}")
        if self.state != "COMPLETE":
            errors.append("WORKER_NOT_COMPLETE")
        if self.observation_context != "ISOLATED_PACKAGE":
            errors.append("OBSERVATION_NOT_ISOLATED")
        if not self.isolation_verified:
            errors.append("ISOLATION_UNVERIFIED")
        observation = Path(self.observation_path) if self.observation_path else None
        if observation is None:
            errors.append("OBSERVATION_PATH_MISSING")
        elif not _contained(observation, Path(request.output_directory)):
            errors.append("OBSERVATION_PATH_ESCAPE")
        elif observation.resolve() != (Path(request.output_directory) / "observation.json").resolve():
            errors.append("OBSERVATION_PATH_UNEXPECTED")
        elif not observation.is_file():
            errors.append("OBSERVATION_FILE_MISSING")
        else:
            try:
                read_json(observation)
            except ValueError:
                errors.append("OBSERVATION_JSON_INVALID")
        if not _valid_id(self.run_id) or not _valid_id(self.worker_id) or not _valid_id(self.template_id) or not _valid_id(self.attempt_id) or not _valid_id(self.nonce):
            errors.append("IDENTITY_FORMAT_INVALID")
        if not _valid_sha(self.package_sha256) or not _valid_sha(self.template_hash):
            errors.append("HASH_FORMAT_INVALID")
        return errors


def validate_request(value: dict[str, Any]) -> list[str]:
    errors = [f"REQUEST_UNKNOWN_FIELD:{key}" for key in value if key not in REQUEST_KEYS]
    required = ("run_id", "worker_id", "package_index", "package_path", "package_sha256", "template_id", "template_hash", "unity_version", "output_directory", "attempt_id", "nonce")
    errors.extend(f"REQUEST_FIELD_MISSING:{key}" for key in required if not value.get(key))
    for key in ("package_path", "unity_version", "output_directory"):
        if key in value and not _valid_text(value[key]):
            errors.append(f"REQUEST_TEXT_INVALID:{key}")
    for key in ("run_id", "worker_id", "template_id", "attempt_id", "nonce"):
        if key in value and not _valid_id(value[key]): errors.append(f"IDENTITY_FORMAT_INVALID:{key}")
    for key in ("package_sha256", "template_hash"):
        if key in value and not _valid_sha(value[key]): errors.append(f"HASH_FORMAT_INVALID:{key}")
    if value.get("protocol_version") != PROTOCOL_VERSION:
        errors.append("PROTOCOL_VERSION_MISMATCH")
    if value.get("unity_version") != "2022.3.62f3":
        errors.append("WORKER_VERSION_MISMATCH")
    if isinstance(value.get("package_index"), bool) or not isinstance(value.get("package_index"), int) or value.get("package_index", 0) < 1:
        errors.append("PACKAGE_INDEX_INVALID")
    if _valid_text(value.get("output_directory")):
        try:
            output = Path(value["output_directory"])
            if not output.is_absolute() or ".." in output.parts:
                errors.append("OUTPUT_DIRECTORY_INVALID")
        except (OSError, RuntimeError, ValueError):
            errors.append("OUTPUT_DIRECTORY_INVALID")
    else:
        errors.append("OUTPUT_DIRECTORY_INVALID")
    if "prefab_filter" in value and not isinstance(value["prefab_filter"], str):
        errors.append("REQUEST_TEXT_INVALID:prefab_filter")
    return errors


def request_from_dict(value: dict[str, Any]) -> WorkerRequest:
    errors = validate_request(value)
    if errors:
        raise ValueError(";".join(errors))
    fields = ("run_id", "worker_id", "package_index", "package_path", "package_sha256", "template_id", "template_hash", "unity_version", "output_directory", "prefab_filter", "protocol_version", "attempt_id", "nonce")
    return WorkerRequest(**{key: value.get(key, "") for key in fields})


def result_from_dict(value: dict[str, Any]) -> WorkerResult:
    required = ("run_id", "worker_id", "package_index", "package_sha256", "template_id", "template_hash", "unity_version", "observation_context", "state", "observation_path", "protocol_version", "attempt_id", "nonce", "isolation_verified")
    errors = [f"RESULT_UNKNOWN_FIELD:{key}" for key in value if key not in RESULT_KEYS]
    errors.extend(f"RESULT_FIELD_MISSING:{key}" for key in required if key not in value)
    if errors:
        raise ValueError(";".join(errors))
    if isinstance(value.get("package_index"), bool) or not isinstance(value.get("package_index"), int):
        errors.append("PACKAGE_INDEX_INVALID")
    if not isinstance(value.get("isolation_verified"), bool):
        errors.append("ISOLATION_FLAG_INVALID")
    for key in ("run_id", "worker_id", "package_sha256", "template_id", "template_hash", "unity_version", "observation_context", "state", "observation_path", "protocol_version", "attempt_id", "nonce"):
        if not _valid_text(value.get(key)):
            errors.append(f"RESULT_TEXT_INVALID:{key}")
    if errors:
        raise ValueError(";".join(errors))
    return WorkerResult(**{key: value[key] for key in required})
