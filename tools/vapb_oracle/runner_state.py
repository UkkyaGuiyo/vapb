"""Pure state-machine rules mirrored by the human Unity runner."""

from __future__ import annotations

from collections import defaultdict


def classify_status(*, heartbeat_age: float, progress_age: float,
                    unity_busy: bool, stall_threshold: float = 120.0) -> str:
    if heartbeat_age > stall_threshold:
        return "STALLED"
    if unity_busy:
        return "WAITING_FOR_UNITY"
    if progress_age >= stall_threshold:
        return "STALLED"
    return "RUNNING"


class RetryPolicy:
    def __init__(self, max_retries: int = 1):
        self.max_retries = max(0, max_retries)
        self._counts = defaultdict(int)

    def can_retry(self, package_key: str) -> bool:
        return self._counts[package_key] < self.max_retries

    def record(self, package_key: str) -> None:
        self._counts[package_key] += 1
