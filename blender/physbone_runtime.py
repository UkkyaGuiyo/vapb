"""Interactive Blender bridge for the disposable PhysBone preview solver.

The controller owns only preview state.  Unity serialized snapshots remain on
the imported prefab roots and are never edited by this module.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from time import perf_counter
from typing import Any, Callable, Iterable

from .physbone_preview import PhysBonePreviewSolver, PhysBonePreviewState

try:  # Blender is optional for the pure controller tests.
    import bpy  # type: ignore
    from mathutils import Vector  # type: ignore
except ImportError:  # pragma: no cover
    bpy = None
    Vector = None


PREVIEW_IDLE = "STOPPED"
PREVIEW_RUNNING = "RUNNING"
PREVIEW_NO_MATCHES = "NO_MATCHES"
PREVIEW_ERROR = "ERROR"


@dataclass
class PreviewChain:
    adapter: Any
    root_name: str
    bone_count: int
    collider_count: int
    match_confidence: str = "EXACT"
    state: PhysBonePreviewState | None = None


class PhysicsPreviewController:
    """Main-thread timer controller with injectable adapters for testing."""

    def __init__(
        self,
        discover: Callable[[Any], Iterable[PreviewChain]],
        *,
        timer_register: Callable[..., Any],
        timer_unregister: Callable[[Callable[..., Any]], Any],
        timer_is_registered: Callable[[Callable[..., Any]], bool] | None = None,
        clock: Callable[[], float] = perf_counter,
        solver: PhysBonePreviewSolver | None = None,
    ) -> None:
        self.discover = discover
        self.timer_register = timer_register
        self.timer_unregister = timer_unregister
        self.timer_is_registered = timer_is_registered
        self.clock = clock
        self.solver = solver or PhysBonePreviewSolver()
        self.running = False
        self.scene: Any = None
        self.chains: list[PreviewChain] = []
        self.unmatched = 0
        self.last_error = ""
        self._last_time = 0.0
        self._in_update = False
        self._timer_callback = self._timer_tick

    @property
    def detected_count(self) -> int:
        return len(self.chains) + self.unmatched

    @property
    def matched_count(self) -> int:
        return len(self.chains)

    @property
    def status(self) -> str:
        if self.last_error:
            return PREVIEW_ERROR
        if self.running and not self.chains:
            return PREVIEW_NO_MATCHES
        return PREVIEW_RUNNING if self.running else PREVIEW_IDLE

    def enable(self, scene: Any) -> str:
        if self.running:
            return self.status
        self.last_error = ""
        self.scene = scene
        try:
            self.chains = list(self.discover(scene))
            self.unmatched = int(scene.get("vapb_physbone_unmatched", 0)) if hasattr(scene, "get") else 0
            for chain in self.chains:
                chain.state = chain.adapter.create_state(self.solver)
            self.running = True
            self._last_time = self.clock()
            if not self._is_registered():
                self.timer_register(self._timer_callback, first_interval=1.0 / 60.0)
            return self.status
        except Exception as exc:  # keep UI recoverable; no source mutation
            self.last_error = str(exc)
            self.running = False
            self._unregister_timer()
            return self.status

    def disable(self) -> str:
        if not self.running and not self._is_registered():
            return self.status
        self.running = False
        self._unregister_timer()
        for chain in self.chains:
            try:
                chain.adapter.restore_preview_pose()
            except Exception:
                pass
        self._in_update = False
        return self.status

    def reset(self) -> None:
        for chain in self.chains:
            chain.state = chain.adapter.create_state(self.solver)
        self._last_time = self.clock()

    def _is_registered(self) -> bool:
        if self.timer_is_registered is not None:
            return bool(self.timer_is_registered(self._timer_callback))
        return False

    def _unregister_timer(self) -> None:
        if self._is_registered():
            self.timer_unregister(self._timer_callback)

    def _timer_tick(self) -> float | None:
        if not self.running or self._in_update:
            return None if not self.running else 1.0 / 60.0
        self._in_update = True
        try:
            now = self.clock()
            dt = now - self._last_time
            self._last_time = now
            props = getattr(self.scene, "vapb_physics_preview", None)
            strength = float(getattr(props, "strength", 1.0))
            gravity_scale = float(getattr(props, "gravity_scale", 1.0))
            for chain in self.chains:
                if chain.state is None:
                    continue
                parent_position = chain.adapter.parent_position()
                self.solver.step(
                    chain.state,
                    parent_position,
                    dt,
                    strength=strength,
                    gravity_scale=gravity_scale,
                    enabled=True,
                )
                chain.adapter.apply_positions(chain.state.positions)
            return 1.0 / 60.0 if self.running else None
        except Exception as exc:
            self.last_error = str(exc)
            self.disable()
            return None
        finally:
            self._in_update = False


def _snapshot_records(root: Any) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    try:
        payload = json.loads(root.get("unity_physbone_source_json", "{}"))
    except (TypeError, ValueError):
        return [], []
    return payload.get("physbones", []), payload.get("colliders", [])


class _PoseBoneAdapter:
    def __init__(self, armature: Any, bones: list[Any]) -> None:
        self.armature = armature
        self.bones = bones
        self._original = []
        for bone in bones[1:]:
            self._original.append((bone, bone.rotation_mode, bone.rotation_quaternion.copy()))

    def _positions(self) -> tuple[Any, ...]:
        return tuple(self.armature.matrix_world @ bone.head for bone in self.bones)

    def create_state(self, solver: PhysBonePreviewSolver) -> PhysBonePreviewState:
        positions = self._positions()
        return solver.create_state(tuple(tuple(float(v) for v in point) for point in positions))

    def parent_position(self) -> tuple[float, float, float]:
        point = self.armature.matrix_world @ self.bones[0].head
        return tuple(float(v) for v in point)

    def apply_positions(self, positions: tuple[tuple[float, float, float], ...]) -> None:
        if Vector is None:
            return
        for index in range(1, len(self.bones)):
            bone = self.bones[index]
            rest_direction = self.bones[index].bone.tail_local - self.bones[index].bone.head_local
            target = Vector(positions[index]) - Vector(positions[index - 1])
            if rest_direction.length <= 1e-8 or target.length <= 1e-8:
                continue
            bone.rotation_mode = "QUATERNION"
            bone.rotation_quaternion = rest_direction.rotation_difference(target)

    def restore_preview_pose(self) -> None:
        for bone, mode, rotation in self._original:
            bone.rotation_mode = mode
            bone.rotation_quaternion = rotation


def discover_blender_chains(scene: Any) -> list[PreviewChain]:
    """Discover only identity-backed chains; never guess by bone name alone."""
    if bpy is None:
        return []
    result: list[PreviewChain] = []
    detected = 0
    for root in scene.objects:
        if not root.get("unity_physbone_source_json"):
            continue
        physbones, colliders = _snapshot_records(root)
        source_package_id = str(root.get("unity_source_package_id", ""))
        try:
            identities = json.loads(root.get("unity_prefab_bone_identities", "{}"))
        except (TypeError, ValueError):
            identities = {}
        for record in physbones:
            detected += 1
            identity = identities.get(str(record.get("root_game_object_file_id", "")))
            if not identity or not identity.get("bone_name"):
                continue
            candidates = []
            for armature in scene.objects:
                if armature.type != "ARMATURE":
                    continue
                if source_package_id and str(armature.get("unity_source_package_id", "")) != source_package_id:
                    continue
                data_bone = armature.data.bones.get(identity["bone_name"])
                pose_bone = armature.pose.bones.get(identity["bone_name"])
                if (
                    data_bone is not None
                    and pose_bone is not None
                    and str(data_bone.get("unity_prefab_file_id", ""))
                    == str(record.get("root_game_object_file_id", ""))
                ):
                    candidates.append((armature, pose_bone))
            if len(candidates) != 1:
                continue
            armature, root_bone = candidates[0]
            chain = [root_bone]
            current = root_bone
            while True:
                children = list(current.children)
                if len(children) != 1:
                    break
                current = children[0]
                chain.append(current)
            if len(chain) < 2:
                continue
            collider_count = len(record.get("collider_file_ids", ()))
            result.append(PreviewChain(_PoseBoneAdapter(armature, chain), root_bone.name, len(chain), collider_count))
    scene["vapb_physbone_unmatched"] = max(0, detected - len(result))
    scene["vapb_physbone_detected"] = detected
    return result


_CONTROLLER: PhysicsPreviewController | None = None


def get_controller() -> PhysicsPreviewController:
    global _CONTROLLER
    if _CONTROLLER is None:
        if bpy is None:
            raise RuntimeError("Blender runtime is unavailable")
        _CONTROLLER = PhysicsPreviewController(
            discover_blender_chains,
            timer_register=bpy.app.timers.register,
            timer_unregister=bpy.app.timers.unregister,
            timer_is_registered=bpy.app.timers.is_registered,
        )
    return _CONTROLLER


def shutdown() -> None:
    if _CONTROLLER is not None:
        _CONTROLLER.disable()


__all__ = [
    "PREVIEW_IDLE", "PREVIEW_RUNNING", "PREVIEW_NO_MATCHES", "PREVIEW_ERROR",
    "PreviewChain", "PhysicsPreviewController", "discover_blender_chains",
    "get_controller", "shutdown",
]
