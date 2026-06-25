"""
brain_ai/planner/hitl_manager.py — Human-In-The-Loop trajectory selection manager.

Handles the full HITL lifecycle:
  1. Push trajectory options + ghost trails → brain_viz via WebSocket
  2. Start 3-second countdown timer
  3. If user selects before timeout → apply selection
  4. If timeout → auto-select best (highest scored) trajectory
  5. Notify downstream that selection is complete

Thread-safe for use with WebSocket callbacks and planner coroutines.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

from brain_ai.domain.motion import Trajectory, TrajectorySet
from brain_ai.domain.plan import ExecutionPlan

logger = logging.getLogger(__name__)


class HITLState(str, Enum):
    """HITL selection workflow states."""
    IDLE      = "IDLE"
    PROMPTING = "PROMPTING"    # Options pushed, waiting for response
    SELECTED  = "SELECTED"     # User or auto-selected
    TIMED_OUT = "TIMED_OUT"    # Countdown expired, auto-selected
    CANCELLED = "CANCELLED"    # Cancelled by operator


@dataclass
class HITLResult:
    """Result of a HITL selection cycle."""
    session_id: str
    plan_id: str
    selected_trajectory_id: str
    state: HITLState
    selected_by_user: bool
    elapsed_sec: float
    timeout_sec: float
    options_count: int


class HITLManager:
    """
    Human-In-The-Loop trajectory selection manager.

    Usage:
        mgr = HITLManager(ws_server)

        # Start a HITL session
        result = await mgr.start_selection(
            plan=execution_plan,
            trajectory_set=trajectory_set,
            timeout_sec=3.0,
            on_selected=handle_selection,
        )
    """

    def __init__(
        self,
        ws_server=None,        # WSServer instance (optional for testing)
        default_timeout_sec: float = 3.0,
    ) -> None:
        self._ws_server = ws_server
        self._default_timeout = default_timeout_sec

        # Active HITL sessions
        self._active: dict[str, _HITLSession] = {}
        self._selection_callbacks: dict[str, asyncio.Future] = {}

        logger.info(
            f"[HITLManager] Initialized, default_timeout={default_timeout_sec}s"
        )

    # ── Public API ─────────────────────────────────────────────────────────

    async def start_selection(
        self,
        plan: ExecutionPlan,
        trajectory_set: TrajectorySet,
        timeout_sec: Optional[float] = None,
        on_selected: Optional[Callable[[HITLResult], None]] = None,
    ) -> HITLResult:
        """
        Begin a HITL trajectory selection cycle.

        Pushes options to brain_viz, starts countdown, returns when resolved.

        Args:
            plan:              The execution plan being considered
            trajectory_set:    Candidate trajectories with scores
            timeout_sec:       Override default countdown (default 3.0)
            on_selected:       Optional callback on selection

        Returns:
            HITLResult with selected trajectory info
        """
        timeout = timeout_sec or self._default_timeout
        session_id = str(uuid.uuid4())[:8]

        session = _HITLSession(
            session_id=session_id,
            plan_id=plan.id,
            trajectory_set=trajectory_set,
            timeout_sec=timeout,
        )
        self._active[session_id] = session

        # Push options to brain_viz
        await self._push_options(session)

        # Create future for selection resolution
        future: asyncio.Future = asyncio.get_event_loop().create_future()
        self._selection_callbacks[session_id] = future

        logger.info(
            f"[HITLManager] HITL session {session_id} started for plan {plan.id}, "
            f"{len(trajectory_set.trajectories)} options, {timeout}s timeout"
        )

        try:
            # Wait with timeout
            result = await asyncio.wait_for(future, timeout=timeout)
            if on_selected:
                on_selected(result)
            return result
        except asyncio.TimeoutError:
            # Auto-select best
            return self._auto_select(session, on_selected)
        finally:
            self._selection_callbacks.pop(session_id, None)
            self._active.pop(session_id, None)

    def select_trajectory(self, session_id: str, trajectory_id: str) -> bool:
        """
        Called from WebSocket handler when user selects a trajectory.

        Returns True if the selection was successfully applied.
        """
        session = self._active.get(session_id)
        if session is None:
            logger.warning(
                f"[HITLManager] Unknown HITL session: {session_id}"
            )
            return False

        # Verify trajectory exists in options
        valid_ids = {t.id for t in session.trajectory_set.trajectories}
        if trajectory_id not in valid_ids:
            logger.warning(
                f"[HITLManager] Invalid trajectory {trajectory_id} for "
                f"session {session_id}"
            )
            return False

        session.selected_id = trajectory_id
        session.state = HITLState.SELECTED

        result = HITLResult(
            session_id=session_id,
            plan_id=session.plan_id,
            selected_trajectory_id=trajectory_id,
            state=HITLState.SELECTED,
            selected_by_user=True,
            elapsed_sec=time.time() - session.start_time,
            timeout_sec=session.timeout_sec,
            options_count=len(session.trajectory_set.trajectories),
        )

        # Resolve the future
        future = self._selection_callbacks.get(session_id)
        if future and not future.done():
            future.set_result(result)

        logger.info(
            f"[HITLManager] User selected trajectory {trajectory_id} "
            f"for session {session_id}"
        )
        return True

    def cancel(self, session_id: str) -> bool:
        """Cancel an active HITL session."""
        session = self._active.get(session_id)
        if session is None:
            return False
        session.state = HITLState.CANCELLED
        future = self._selection_callbacks.get(session_id)
        if future and not future.done():
            future.set_result(HITLResult(
                session_id=session_id,
                plan_id=session.plan_id,
                selected_trajectory_id="",
                state=HITLState.CANCELLED,
                selected_by_user=False,
                elapsed_sec=time.time() - session.start_time,
                timeout_sec=session.timeout_sec,
                options_count=0,
            ))
        logger.info(f"[HITLManager] HITL session {session_id} cancelled")
        return True

    # ── Internal ───────────────────────────────────────────────────────────

    async def _push_options(self, session: _HITLSession) -> None:
        """Push trajectory options to brain_viz via WebSocket."""
        if self._ws_server is None:
            logger.debug("[HITLManager] No WS server — skipping push")
            return

        ts = session.trajectory_set
        ranked = ts.sorted_by_score()

        # Build options for hitl_prompt
        options = [
            {
                "id": t.id,
                "label": t.label or f"选项 {i + 1}",
                "description": (
                    f"路径长度: {t.path_length_m:.2f}m, "
                    f"耗时: {t.duration_sec:.1f}s, "
                    f"评分: {t.score:.2f}"
                ),
                "score": round(t.score, 4),
            }
            for i, t in enumerate(ranked)
        ]

        await self._ws_server.send_hitl_prompt(
            plan_id=session.plan_id,
            options=options,
            timeout_sec=session.timeout_sec,
        )

        # Build ghost trails
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
                "description": t.label or f"策略{i + 1}",
            }
            for i, t in enumerate(ranked)
        ]

        await self._ws_server.send_ghost_trails(
            plan_id=session.plan_id,
            trajectories=trails,
            timeout_sec=session.timeout_sec,
            recommended_index=0,
        )

    def _auto_select(
        self,
        session: _HITLSession,
        on_selected: Optional[Callable[[HITLResult], None]] = None,
    ) -> HITLResult:
        """Auto-select the best trajectory on timeout."""
        ts = session.trajectory_set
        best_traj = ts.best()
        best_id = best_traj.id if best_traj else ""

        session.state = HITLState.TIMED_OUT
        result = HITLResult(
            session_id=session.session_id,
            plan_id=session.plan_id,
            selected_trajectory_id=best_id,
            state=HITLState.TIMED_OUT,
            selected_by_user=False,
            elapsed_sec=session.timeout_sec,
            timeout_sec=session.timeout_sec,
            options_count=len(ts.trajectories),
        )

        logger.info(
            f"[HITLManager] Auto-selected trajectory {best_id} "
            f"(timeout {session.timeout_sec}s) for session {session.session_id}"
        )

        if on_selected:
            on_selected(result)

        return result

    # ── Properties ─────────────────────────────────────────────────────────

    @property
    def active_sessions(self) -> int:
        return len(self._active)

    @property
    def active_session_ids(self) -> list[str]:
        return list(self._active.keys())


@dataclass
class _HITLSession:
    """Internal state for an active HITL session."""
    session_id: str
    plan_id: str
    trajectory_set: TrajectorySet
    timeout_sec: float
    state: HITLState = HITLState.PROMPTING
    selected_id: Optional[str] = None
    start_time: float = field(default_factory=time.time)
