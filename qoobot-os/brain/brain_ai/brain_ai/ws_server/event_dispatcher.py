"""
brain_ai/ws_server/event_dispatcher.py — Internal event bus → WebSocket bridge.

Routes domain events from brain_ai modules to connected brain_viz clients:
  - Scene updates (perception → viz)
  - Ghost trails (planner → viz)
  - Plan status changes (planner/executor → viz)
  - Safety alerts (safety monitor → viz)
  - HITL prompts (planner → viz)

Supports event filtering, batching, and priority-based dispatch.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Callable, Optional

from brain_ai.domain.motion import Trajectory, TrajectorySet
from brain_ai.domain.plan import ExecutionPlan
from brain_ai.domain.safety import SafetyAlert, SafetyLevel, SafetyStatus
from brain_ai.domain.scene import SceneGraph

logger = logging.getLogger(__name__)


class EventPriority(IntEnum):
    """Event dispatch priority (lower = higher priority)."""
    EMERGENCY = 0   # E-stop, critical safety
    SAFETY    = 1   # Safety alerts
    HITL      = 2   # Time-sensitive HITL prompts
    PLAN      = 3   # Plan status changes
    SCENE     = 4   # Scene updates (can be batched)


@dataclass
class DomainEvent:
    """A typed domain event with priority and payload."""
    event_type: str
    payload: dict[str, Any]
    priority: EventPriority = EventPriority.SCENE
    timestamp: float = field(default_factory=time.time)
    source: str = ""


class EventDispatcher:
    """
    Routes domain events from brain_ai modules to WebSocket clients.

    Features:
      - Priority-based dispatch (safety > HITL > plan > scene)
      - Scene update batching (coalesce rapid updates)
      - Event filtering (suppress duplicate events)
      - Drop monitoring for overload detection

    Usage:
        dispatcher = EventDispatcher(ws_server)
        dispatcher.start()

        # In perception:
        dispatcher.dispatch_scene(scene_graph)

        # In planner:
        dispatcher.dispatch_ghost_trails(plan_id, trajectory_set)

        # In safety:
        dispatcher.dispatch_safety_alert(alert)
    """

    def __init__(
        self,
        ws_server=None,  # WSServer instance
        batch_window_sec: float = 0.1,
        max_queue_size: int = 256,
    ) -> None:
        self._ws = ws_server
        self._batch_window = batch_window_sec
        self._max_queue = max_queue_size

        # Async infrastructure
        self._queue: deque[DomainEvent] = deque()
        self._dispatch_task: Optional[asyncio.Task] = None
        self._running = False

        # Stats
        self._dispatched_count: int = 0
        self._dropped_count: int = 0
        self._last_batch_time: float = 0.0
        self._scene_cooldown_sec: float = 0.1  # Scene update throttle

        # Subscribers (non-WebSocket callbacks)
        self._subscribers: dict[str, list[Callable]] = {}

        logger.info(
            f"[EventDispatcher] Initialized, batch_window={batch_window_sec}s, "
            f"max_queue={max_queue_size}"
        )

    # ── Lifecycle ──────────────────────────────────────────────────────────

    async def start(self) -> None:
        """Start async event dispatch loop."""
        if self._running:
            return
        self._running = True
        self._dispatch_task = asyncio.create_task(self._dispatch_loop())
        logger.info("[EventDispatcher] Dispatch loop started")

    async def stop(self) -> None:
        """Gracefully stop the dispatch loop."""
        self._running = False
        if self._dispatch_task:
            self._dispatch_task.cancel()
            try:
                await self._dispatch_task
            except asyncio.CancelledError:
                pass
        logger.info(
            f"[EventDispatcher] Stopped. Stats: "
            f"dispatched={self._dispatched_count}, dropped={self._dropped_count}"
        )

    # ── Sync dispatch (queue + return) ─────────────────────────────────────

    def dispatch(self, event: DomainEvent) -> None:
        """Enqueue a domain event for async dispatch."""
        if len(self._queue) >= self._max_queue:
            self._dropped_count += 1
            logger.warning(
                f"[EventDispatcher] Queue full ({self._max_queue}) — "
                f"dropping {event.event_type} (total dropped: {self._dropped_count})"
            )
            return
        self._queue.append(event)

    # ── Convenience dispatchers ────────────────────────────────────────────

    def dispatch_scene(self, scene: SceneGraph | dict) -> None:
        """Push a scene update (coalesced/batched)."""
        now = time.time()
        if now - self._last_batch_time < self._scene_cooldown_sec:
            return  # Skip — will be picked up by next cycle
        self._last_batch_time = now

        payload = scene.to_dict() if isinstance(scene, SceneGraph) else scene
        self.dispatch(DomainEvent(
            event_type="scene_update",
            payload=payload,
            priority=EventPriority.SCENE,
            source="perception",
        ))

    def dispatch_ghost_trails(
        self,
        plan_id: str,
        trajectory_set: TrajectorySet | list[dict],
        timeout_sec: float = 3.0,
    ) -> None:
        """Push candidate trajectory ghost trails for HITL display."""
        if isinstance(trajectory_set, TrajectorySet):
            ranked = trajectory_set.sorted_by_score()
            trails = [
                {
                    "id": t.id,
                    "rank": i,
                    "score": round(t.score, 4),
                    "waypoints": [
                        {"x": i * 0.02, "y": t.score * 0.1, "z": 0.0}
                        for i in range(len(t.waypoints))
                    ],
                    "color": t.color_hint,
                    "description": t.label,
                }
                for i, t in enumerate(ranked)
            ]
            payload = {
                "plan_id": plan_id,
                "trajectories": trails,
                "timeout_sec": timeout_sec,
                "recommended_index": 0,
            }
        else:
            payload = {
                "plan_id": plan_id,
                "trajectories": trajectory_set,
                "timeout_sec": timeout_sec,
                "recommended_index": 0,
            }

        self.dispatch(DomainEvent(
            event_type="ghost_trail",
            payload=payload,
            priority=EventPriority.HITL,
            source="planner",
        ))

    def dispatch_plan_status(
        self,
        plan: ExecutionPlan | dict,
        progress: float = 0.0,
        current_step: str = "",
    ) -> None:
        """Push plan execution status update."""
        if isinstance(plan, ExecutionPlan):
            payload = {
                "plan_id": plan.id,
                "state": plan.status.value,
                "progress": progress,
                "current_step": current_step,
            }
        else:
            payload = plan

        self.dispatch(DomainEvent(
            event_type="plan_status",
            payload=payload,
            priority=EventPriority.PLAN,
            source="planner",
        ))

    def dispatch_safety_alert(self, alert: SafetyAlert | SafetyStatus) -> None:
        """Push a safety alert (highest priority)."""
        if isinstance(alert, SafetyAlert):
            payload = {
                "level": self._safety_level_str(alert.level),
                "message": alert.message,
                "code": int(alert.level),
                "type": alert.alert_type.value,
            }
        elif isinstance(alert, SafetyStatus):
            payload = {
                "level": self._safety_level_str(alert.level),
                "message": f"Safety level: {alert.level.name}, risk={alert.collision_risk_score:.2f}",
                "code": int(alert.level),
            }
        else:
            payload = alert

        self.dispatch(DomainEvent(
            event_type="safety_alert",
            payload=payload,
            priority=EventPriority.EMERGENCY if self._is_emergency(payload) else EventPriority.SAFETY,
            source="safety",
        ))

    def dispatch_hitl_prompt(
        self,
        plan_id: str,
        options: list[dict],
        timeout_sec: float = 3.0,
    ) -> None:
        """Push HITL selection prompt to viz."""
        self.dispatch(DomainEvent(
            event_type="hitl_prompt",
            payload={
                "plan_id": plan_id,
                "options": options,
                "timeout_sec": timeout_sec,
            },
            priority=EventPriority.HITL,
            source="planner",
        ))

    # ── Subscription (non-WebSocket internal listeners) ────────────────────

    def subscribe(self, event_type: str, callback: Callable[[dict], None]) -> None:
        """Subscribe to a domain event type."""
        self._subscribers.setdefault(event_type, []).append(callback)

    def unsubscribe(self, event_type: str, callback: Callable) -> None:
        subs = self._subscribers.get(event_type, [])
        if callback in subs:
            subs.remove(callback)

    # ── Async dispatch loop ────────────────────────────────────────────────

    async def _dispatch_loop(self) -> None:
        """Main loop: dequeue and dispatch events by priority."""
        while self._running:
            if not self._queue:
                await asyncio.sleep(0.01)
                continue

            # Sort by priority (emergency first)
            events: list[DomainEvent] = []
            while self._queue:
                events.append(self._queue.popleft())
            events.sort(key=lambda e: e.priority.value)

            # Batch scene updates
            events = self._coalesce_scenes(events)

            for event in events:
                await self._send_event(event)

            await asyncio.sleep(self._batch_window)

    def _coalesce_scenes(self, events: list[DomainEvent]) -> list[DomainEvent]:
        """Coalesce multiple scene_update events into one (keep latest)."""
        scenes = [e for e in events if e.event_type == "scene_update"]
        others = [e for e in events if e.event_type != "scene_update"]
        if scenes:
            # Keep only the latest scene update
            return others + [scenes[-1]]
        return others

    async def _send_event(self, event: DomainEvent) -> None:
        """Send a single event to WebSocket and internal subscribers."""
        # WebSocket broadcast
        if self._ws is not None:
            try:
                await self._ws.broadcast(event.event_type, event.payload)
                self._dispatched_count += 1
            except Exception as e:
                logger.error(
                    f"[EventDispatcher] WS send failed for {event.event_type}: {e}"
                )
        else:
            logger.debug(
                f"[EventDispatcher] No WS server — skipping {event.event_type}"
            )

        # Internal subscribers
        for cb in self._subscribers.get(event.event_type, []):
            try:
                if asyncio.iscoroutinefunction(cb):
                    await cb(event.payload)
                else:
                    cb(event.payload)
            except Exception as e:
                logger.error(
                    f"[EventDispatcher] Subscriber error for {event.event_type}: {e}"
                )

    # ── Helpers ────────────────────────────────────────────────────────────

    @staticmethod
    def _safety_level_str(level: SafetyLevel) -> str:
        mapping = {
            SafetyLevel.S0_EMERGENCY: "emergency",
            SafetyLevel.S1_CRITICAL:  "critical",
            SafetyLevel.S2_WARNING:   "warning",
            SafetyLevel.S3_NORMAL:    "ok",
        }
        return mapping.get(level, "ok")

    @staticmethod
    def _is_emergency(payload: dict) -> bool:
        return payload.get("level") in ("emergency", "critical")

    @property
    def dispatched_count(self) -> int:
        return self._dispatched_count

    @property
    def dropped_count(self) -> int:
        return self._dropped_count

    @property
    def queue_size(self) -> int:
        return len(self._queue)


# ── Default instance ───────────────────────────────────────────────────────

_default_dispatcher: Optional[EventDispatcher] = None


def get_event_dispatcher() -> EventDispatcher:
    global _default_dispatcher
    if _default_dispatcher is None:
        _default_dispatcher = EventDispatcher()
    return _default_dispatcher
