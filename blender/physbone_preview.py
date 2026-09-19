"""Small dependency-free approximate secondary-motion solver.

This module is intentionally independent from Blender RNA.  A future UI bridge
can feed pose-bone positions into it without mixing disposable preview state
with preserved Unity PhysBone source data.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from typing import Iterable


Vec3 = tuple[float, float, float]


def _add(a: Vec3, b: Vec3) -> Vec3:
    return tuple(x + y for x, y in zip(a, b))  # type: ignore[return-value]


def _sub(a: Vec3, b: Vec3) -> Vec3:
    return tuple(x - y for x, y in zip(a, b))  # type: ignore[return-value]


def _mul(a: Vec3, value: float) -> Vec3:
    return tuple(x * value for x in a)  # type: ignore[return-value]


def _length(a: Vec3) -> float:
    return sqrt(sum(value * value for value in a))


def _normalize(a: Vec3) -> Vec3:
    length = _length(a)
    return (0.0, 1.0, 0.0) if length <= 1e-9 else _mul(a, 1.0 / length)


@dataclass
class PhysBonePreviewState:
    rest_positions: tuple[Vec3, ...]
    positions: tuple[Vec3, ...]
    velocities: tuple[Vec3, ...]
    last_dt: float = 0.0


class PhysBonePreviewSolver:
    """Stable, clamped Verlet-like chain solver for preview only."""

    def __init__(self, *, max_dt: float = 1.0 / 20.0, spring: float = 18.0, damping: float = 7.0):
        self.max_dt = max_dt
        self.spring = spring
        self.damping = damping

    def create_state(self, rest_positions: Iterable[Vec3]) -> PhysBonePreviewState:
        rest = tuple(tuple(float(v) for v in point) for point in rest_positions)
        return PhysBonePreviewState(rest, rest, tuple((0.0, 0.0, 0.0) for _ in rest))

    def reset(self, state: PhysBonePreviewState) -> PhysBonePreviewState:
        state.positions = state.rest_positions
        state.velocities = tuple((0.0, 0.0, 0.0) for _ in state.rest_positions)
        state.last_dt = 0.0
        return state

    def step(
        self,
        state: PhysBonePreviewState,
        parent_position: Vec3,
        dt: float,
        *,
        strength: float = 1.0,
        gravity_scale: float = 1.0,
        enabled: bool = True,
    ) -> PhysBonePreviewState:
        if not enabled or len(state.positions) < 2:
            return state
        if dt <= 0.0 or dt > self.max_dt * 4.0:
            self.reset(state)
            return state
        dt = min(dt, self.max_dt)
        positions = list(state.positions)
        velocities = list(state.velocities)
        root_offset = _sub(parent_position, state.rest_positions[0])
        positions[0] = parent_position
        velocities[0] = (0.0, 0.0, 0.0)
        for index in range(1, len(positions)):
            rest = _add(state.rest_positions[index], root_offset)
            target = _add(rest, (0.0, -0.35 * gravity_scale * (index * dt), 0.0))
            acceleration = _add(_mul(_sub(target, positions[index]), self.spring * strength), (0.0, -gravity_scale, 0.0))
            velocities[index] = _mul(_add(velocities[index], _mul(acceleration, dt)), max(0.0, 1.0 - self.damping * dt))
            positions[index] = _add(positions[index], _mul(velocities[index], dt))
            parent = positions[index - 1]
            rest_length = _length(_sub(state.rest_positions[index], state.rest_positions[index - 1]))
            positions[index] = _add(parent, _mul(_normalize(_sub(positions[index], parent)), rest_length))
        state.positions = tuple(positions)
        state.velocities = tuple(velocities)
        state.last_dt = dt
        return state


__all__ = ["PhysBonePreviewState", "PhysBonePreviewSolver"]
