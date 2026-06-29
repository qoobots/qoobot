"""
brain_ai/ws_server/ws_handler.py — WebSocket server for brain_viz communication.

Pushes real-time events to all connected brain_viz clients:
  - scene_update:    SceneGraph snapshot (objects, robot pose)
  - ghost_trail:     Candidate trajectory options for HITL
  - plan_status:     Plan execution progress
  - safety_alert:    Safety level changes
  - hitl_prompt:     HITL selection request (with countdown)

Message format (both directions):
    {"type": "<event_type>", "payload": {...}}

Incoming messages from brain_viz:
  - hitl_select:     {"type": "hitl_select", "payload": {"plan_id": "...", "trajectory_id": "..."}}
  - emergency_stop:  {"type": "emergency_stop", "payload": {"robot_id": "..."}}
  - heartbeat:       {"type": "heartbeat", "payload": {}}
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Callable
from typing import Any

import websockets
import websockets.server

logger = logging.getLogger(__name__)

# Typed event payloads (documented here for brain_viz integration)
# scene_update:
#   objects: list[{id, label, pose:{pos:{x,y,z}, rot:{x,y,z,w}}, color}]
#   robot_pose: {pos:{x,y,z}, rot:{x,y,z,w}}
#   timestamp: float
#
# ghost_trail:
#   plan_id: str
#   trajectories: list[{id, rank, score, waypoints:[{x,y,z}], color, description}]
#   timeout_sec: float
#   recommended_index: int
#
# plan_status:
#   plan_id: str
#   state: str  (IDLE|PLANNING|WAITING_HITL|EXECUTING|SUCCEEDED|FAILED|CANCELLED)
#   progress: float  [0.0, 1.0]
#   current_step: str
#
# safety_alert:
#   level: str  (ok|warning|critical|emergency)
#   message: str
#   code: int
#
# hitl_prompt:
#   plan_id: str
#   options: list[{id, label, description, score}]
#   timeout_sec: float


class WSServer:
    """WebSocket server for real-time push to brain_viz."""

    def __init__(self, host: str = "0.0.0.0", port: int = 8765):
        self._host = host
        self._port = port
        self._clients: set[websockets.server.WebSocketServerProtocol] = set()
        self._incoming_handlers: dict[str, list[Callable]] = {}
        self._server: websockets.server.WebSocketServer | None = None

        logger.info(f"[WSServer] Initialized — will listen on {host}:{port}")

    # ── Server lifecycle ───────────────────────────────────────────────────

    async def start(self) -> None:
        """Start WebSocket server (non-blocking, runs as background task)."""
        self._server = await websockets.server.serve(
            self._connection_handler,
            self._host,
            self._port,
            ping_interval=20,
            ping_timeout=20,
        )
        logger.info(f"[WSServer] Listening on ws://{self._host}:{self._port}")

    async def stop(self) -> None:
        """Gracefully stop the server."""
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            logger.info("[WSServer] Stopped.")

    # ── Internal connection handler ────────────────────────────────────────

    async def _connection_handler(
        self,
        websocket: websockets.server.WebSocketServerProtocol,
    ) -> None:
        """Handle lifecycle of a single brain_viz connection."""
        client_id = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        self._clients.add(websocket)
        logger.info(f"[WSServer] Client connected: {client_id} "
                    f"(total: {len(self._clients)})")

        try:
            async for raw in websocket:
                await self._dispatch_incoming(websocket, raw)
        except websockets.exceptions.ConnectionClosed as e:
            logger.info(f"[WSServer] Client disconnected: {client_id} "
                        f"(code={e.code})")
        finally:
            self._clients.discard(websocket)
            logger.info(f"[WSServer] Clients remaining: {len(self._clients)}")

    async def _dispatch_incoming(
        self,
        websocket: websockets.server.WebSocketServerProtocol,
        raw: str | bytes,
    ) -> None:
        """Dispatch an incoming message from brain_viz to registered handlers."""
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning(f"[WSServer] Received non-JSON message: {raw!r}")
            return

        event_type = msg.get("type", "")
        payload = msg.get("payload", {})

        handlers = self._incoming_handlers.get(event_type, [])
        if not handlers:
            logger.debug(f"[WSServer] No handler for event: {event_type}")
            return

        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(payload, websocket)
                else:
                    handler(payload, websocket)
            except Exception as e:
                logger.exception(f"[WSServer] Handler error for '{event_type}': {e}")

    # ── Broadcast / Send helpers ───────────────────────────────────────────

    async def broadcast(self, event_type: str, payload: dict[str, Any]) -> None:
        """Broadcast a message to all connected brain_viz clients."""
        if not self._clients:
            logger.debug(f"[WSServer] No clients — skipping broadcast: {event_type}")
            return

        message = json.dumps(
            {"type": event_type, "payload": payload},
            default=str,
            ensure_ascii=False,
        )
        disconnected = set()
        for client in self._clients:
            try:
                await client.send(message)
            except websockets.exceptions.ConnectionClosed:
                disconnected.add(client)

        self._clients -= disconnected
        logger.debug(f"[WSServer] Broadcast '{event_type}' → "
                     f"{len(self._clients)} clients")

    # ── Domain event publishers ────────────────────────────────────────────

    async def send_scene_update(
        self,
        objects: list[dict],
        robot_pose: dict,
        timestamp: float | None = None,
    ) -> None:
        """Push a scene graph snapshot to brain_viz."""
        import time
        await self.broadcast("scene_update", {
            "objects": objects,
            "robot_pose": robot_pose,
            "timestamp": timestamp or time.time(),
        })

    async def send_ghost_trails(
        self,
        plan_id: str,
        trajectories: list[dict],
        timeout_sec: float = 6.0,
        recommended_index: int = 0,
    ) -> None:
        """Push candidate trajectory Ghost Trails for HITL selection."""
        await self.broadcast("ghost_trail", {
            "plan_id": plan_id,
            "trajectories": trajectories,
            "timeout_sec": timeout_sec,
            "recommended_index": recommended_index,
        })

    async def send_plan_status(
        self,
        plan_id: str,
        state: str,
        progress: float = 0.0,
        current_step: str = "",
    ) -> None:
        """Push plan execution status update."""
        await self.broadcast("plan_status", {
            "plan_id": plan_id,
            "state": state,
            "progress": progress,
            "current_step": current_step,
        })

    async def send_safety_alert(
        self,
        level: str,
        message: str,
        code: int = 0,
    ) -> None:
        """Push a safety alert (level: ok|warning|critical|emergency)."""
        await self.broadcast("safety_alert", {
            "level": level,
            "message": message,
            "code": code,
        })

    async def send_hitl_prompt(
        self,
        plan_id: str,
        options: list[dict],
        timeout_sec: float = 6.0,
    ) -> None:
        """Push a HITL selection prompt to brain_viz."""
        await self.broadcast("hitl_prompt", {
            "plan_id": plan_id,
            "options": options,
            "timeout_sec": timeout_sec,
        })

    # ── Incoming event subscription ────────────────────────────────────────

    def on(self, event_type: str, handler: Callable) -> None:
        """Register a handler for incoming messages from brain_viz.

        Args:
            event_type: e.g. "hitl_select", "emergency_stop"
            handler:    callable(payload: dict, websocket)
                        may be async
        """
        self._incoming_handlers.setdefault(event_type, []).append(handler)
        logger.debug(f"[WSServer] Registered handler for '{event_type}'")

    def off(self, event_type: str, handler: Callable) -> None:
        """Unregister a handler."""
        handlers = self._incoming_handlers.get(event_type, [])
        if handler in handlers:
            handlers.remove(handler)

    # ── Properties ──────────────────────────────────────────────────────────

    @property
    def client_count(self) -> int:
        return len(self._clients)


# ── Default shared instance ────────────────────────────────────────────────

_default_ws_server: WSServer | None = None


def get_ws_server() -> WSServer:
    """Get or create the default WSServer singleton."""
    global _default_ws_server
    if _default_ws_server is None:
        _default_ws_server = WSServer()
    return _default_ws_server
