"""
brain_ai/knowledge/working_memory.py — Short-term working memory for active task context.

Holds the current task state, recent observations, active plan,
and safety status in a single place accessible to all brain_ai modules.
"""
from __future__ import annotations

import threading
from datetime import datetime
from typing import Any, Optional

from brain_ai.knowledge.ring_buffer import RingBuffer


class WorkingMemory:
    """
    Thread-safe, in-process short-term memory for the current task.

    Stores:
      - current_task_id        : str or None
      - current_instruction    : str
      - current_plan           : dict (serialized ExecutionPlan)
      - current_scene          : dict (serialized SceneGraph)
      - recent_observations    : RingBuffer[dict]  (last N sensor snapshots)
      - safety_status          : dict
      - hitl_pending           : bool
      - conversation_history   : list[dict]  (user/assistant turns)
    """

    def __init__(self, obs_buffer_size: int = 50) -> None:
        self._lock = threading.RLock()

        self.current_task_id:      Optional[str] = None
        self.current_instruction:  str = ""
        self.current_plan:         Optional[dict] = None
        self.current_scene:        Optional[dict] = None
        self.safety_status:        dict = {"level": 3, "emergency_stop_active": False}
        self.hitl_pending:         bool = False
        self.hitl_trajectory_set:  Optional[dict] = None

        self.recent_observations:  RingBuffer[dict] = RingBuffer(obs_buffer_size)
        self.conversation_history: list[dict] = []   # [{role, content, timestamp}]

        self._updated_at: datetime = datetime.now()
        self._extras: dict[str, Any] = {}

    # ─── Task ─────────────────────────────────────────────────

    def set_task(self, task_id: str, instruction: str) -> None:
        with self._lock:
            self.current_task_id     = task_id
            self.current_instruction = instruction
            self.current_plan        = None
            self.hitl_pending        = False
            self._touch()

    def clear_task(self) -> None:
        with self._lock:
            self.current_task_id      = None
            self.current_instruction  = ""
            self.current_plan         = None
            self.hitl_pending         = False
            self.hitl_trajectory_set  = None
            self._touch()

    # ─── Plan ─────────────────────────────────────────────────

    def set_plan(self, plan: dict) -> None:
        with self._lock:
            self.current_plan = plan
            self._touch()

    # ─── Scene ────────────────────────────────────────────────

    def update_scene(self, scene: dict) -> None:
        with self._lock:
            self.current_scene = scene
            self.recent_observations.push({
                "timestamp": datetime.now().isoformat(),
                "scene": scene,
            })
            self._touch()

    # ─── HITL ─────────────────────────────────────────────────

    def set_hitl_pending(self, trajectory_set: dict) -> None:
        with self._lock:
            self.hitl_pending        = True
            self.hitl_trajectory_set = trajectory_set
            self._touch()

    def resolve_hitl(self, trajectory_id: str) -> None:
        with self._lock:
            self.hitl_pending = False
            if self.current_plan:
                self.current_plan["selected_trajectory_id"] = trajectory_id
            self._touch()

    # ─── Conversation ─────────────────────────────────────────

    def add_turn(self, role: str, content: str) -> None:
        with self._lock:
            self.conversation_history.append({
                "role": role,
                "content": content,
                "timestamp": datetime.now().isoformat(),
            })
            # Keep last 20 turns
            if len(self.conversation_history) > 20:
                self.conversation_history = self.conversation_history[-20:]
            self._touch()

    def recent_turns(self, n: int = 5) -> list[dict]:
        with self._lock:
            return self.conversation_history[-n:]

    # ─── Safety ───────────────────────────────────────────────

    def update_safety(self, status: dict) -> None:
        with self._lock:
            self.safety_status = status
            self._touch()

    # ─── Generic extras ───────────────────────────────────────

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._extras[key] = value
            self._touch()

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._extras.get(key, default)

    # ─── Snapshot ─────────────────────────────────────────────

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "task_id":           self.current_task_id,
                "instruction":       self.current_instruction,
                "plan_id":           (self.current_plan or {}).get("id"),
                "hitl_pending":      self.hitl_pending,
                "safety_level":      self.safety_status.get("level", 3),
                "scene_object_count": len((self.current_scene or {}).get("objects", [])),
                "obs_buffer_size":   len(self.recent_observations),
                "updated_at":        self._updated_at.isoformat(),
            }

    def _touch(self) -> None:
        self._updated_at = datetime.now()
