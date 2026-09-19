"""Deterministic model of the isolated-run cleanup finalization gate."""

from dataclasses import dataclass


@dataclass
class CleanupGate:
    required_ticks: int = 3
    state: str = "RUNNING"
    stable_ticks: int = 0
    finalized: bool = False

    def observe_output(self) -> None:
        if self.state == "RUNNING":
            self.state = "WAITING_FOR_CLEANUP"
            self.stable_ticks = 0

    def tick(self, *, compiling: bool, updating: bool, clean: bool) -> bool:
        if self.state != "WAITING_FOR_CLEANUP" or self.finalized:
            return self.finalized
        if compiling or updating or not clean:
            self.stable_ticks = 0
            return False
        self.stable_ticks += 1
        if self.stable_ticks >= self.required_ticks:
            self.finalized = True
            self.state = "RUN_COMPLETE"
        return self.finalized
