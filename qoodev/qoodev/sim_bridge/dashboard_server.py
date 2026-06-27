"""Web Dashboard 后端服务器。

通过 WebSocket 向 Web Dashboard 推送实时仿真数据：
- 场景状态更新 (3D 可视化)
- 实时日志流
- 传感器数据统计
- 性能剖析数据
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)


class DashboardServer:
    """WebSocket 服务器，桥接仿真数据到 Web Dashboard。

    Usage:
        server = DashboardServer(sim_manager, port=8090)
        await server.start()
        # ... 仿真运行 ...
        await server.stop()
    """

    def __init__(
        self,
        sim_manager,
        port: int = 8090,
        scene_update_rate: float = 30.0,
    ):
        self._sim_manager = sim_manager
        self._port = port
        self._scene_update_rate = scene_update_rate
        self._clients: set = set()
        self._server = None
        self._running = False
        self._tasks: list[asyncio.Task] = []

        # 数据缓冲
        self._log_stream = sim_manager.backend.log_stream if hasattr(
            sim_manager.backend, 'log_stream'
        ) else None

    async def start(self) -> None:
        """启动 WebSocket 服务器。"""
        try:
            import websockets
        except ImportError:
            logger.error(
                "websockets 未安装。请运行: pip install websockets"
            )
            return

        self._running = True
        self._server = await websockets.serve(
            self._handle_client,
            "0.0.0.0",
            self._port,
        )
        logger.info(f"Dashboard WebSocket 服务器已启动: ws://0.0.0.0:{self._port}")

        # 启动数据推送任务
        self._tasks.append(asyncio.create_task(self._broadcast_scene()))
        self._tasks.append(asyncio.create_task(self._broadcast_stats()))
        self._tasks.append(asyncio.create_task(self._broadcast_logs()))

    async def stop(self) -> None:
        """停止服务器。"""
        self._running = False

        for task in self._tasks:
            task.cancel()
        self._tasks.clear()

        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None

        logger.info("Dashboard 服务器已停止")

    async def _handle_client(self, websocket) -> None:
        """处理客户端连接。"""
        self._clients.add(websocket)
        client_id = id(websocket)
        logger.info(f"Dashboard 客户端已连接: {client_id} (共 {len(self._clients)} 个)")

        try:
            # 发送当前状态
            await websocket.send(json.dumps({
                "type": "sim_state",
                "state": self._sim_manager.backend.state.name
                if self._sim_manager.backend else "STOPPED",
            }))

            # 接收客户端消息
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self._handle_message(websocket, data)
                except json.JSONDecodeError:
                    pass

        except Exception:
            pass
        finally:
            self._clients.discard(websocket)
            logger.info(f"Dashboard 客户端已断开: {client_id} (共 {len(self._clients)} 个)")

    async def _handle_message(self, websocket, data: dict) -> None:
        """处理客户端消息。"""
        msg_type = data.get("type", "")

        if msg_type == "command":
            cmd = data.get("command", "")
            if cmd == "pause":
                self._sim_manager.pause()
            elif cmd == "resume":
                self._sim_manager.resume()
            elif cmd == "stop":
                self._sim_manager.stop()
            elif cmd == "reset":
                if self._sim_manager.backend:
                    self._sim_manager.backend.reset()

            await websocket.send(json.dumps({
                "type": "sim_state",
                "state": self._sim_manager.backend.state.name
                if self._sim_manager.backend else "STOPPED",
            }))

    async def _broadcast_scene(self) -> None:
        """周期性广播场景状态。"""
        interval = 1.0 / self._scene_update_rate
        while self._running:
            try:
                if self._clients and self._sim_manager.backend:
                    snapshot = self._build_scene_snapshot()
                    msg = json.dumps({
                        "type": "scene_update",
                        "snapshot": snapshot,
                    })
                    await self._broadcast(msg)
            except Exception:
                logger.exception("场景广播异常")
            await asyncio.sleep(interval)

    async def _broadcast_stats(self) -> None:
        """周期性广播仿真统计。"""
        while self._running:
            try:
                if self._clients and self._sim_manager.backend:
                    stats = self._sim_manager.backend.get_stats()
                    msg = json.dumps({
                        "type": "sim_stats",
                        "sim_time": stats.total_time,
                        "total_steps": stats.total_steps,
                        "real_time_factor": stats.real_time_factor,
                        "step_time_ms": stats.step_time_ms,
                        "physics_time_ms": stats.physics_time_ms,
                        "render_time_ms": stats.render_time_ms,
                    })
                    await self._broadcast(msg)
            except Exception:
                pass
            await asyncio.sleep(0.5)

    async def _broadcast_logs(self) -> None:
        """周期性广播日志。"""
        if self._log_stream is None:
            return

        last_idx = 0
        while self._running:
            try:
                if self._clients:
                    history = self._log_stream.get_history(limit=50)
                    if len(history) > last_idx:
                        for entry in history[last_idx:]:
                            msg = json.dumps({
                                "type": "log",
                                "timestamp": entry.timestamp,
                                "level": entry.level.name,
                                "message": entry.message,
                                "source": entry.source,
                            })
                            await self._broadcast(msg)
                        last_idx = len(history)
            except Exception:
                pass
            await asyncio.sleep(0.5)

    async def _broadcast(self, message: str) -> None:
        """向所有客户端广播消息。"""
        if not self._clients:
            return
        disconnected = set()
        for client in self._clients:
            try:
                await client.send(message)
            except Exception:
                disconnected.add(client)
        self._clients -= disconnected

    def _build_scene_snapshot(self) -> dict:
        """构建场景快照。"""
        backend = self._sim_manager.backend
        if backend is None:
            return {"timestamp": time.time(), "robots": {}, "objects": {}}

        snapshot = {
            "timestamp": time.time(),
            "robots": {},
            "objects": {},
        }

        if self._sim_manager.scene:
            for robot in self._sim_manager.scene.robots:
                try:
                    pos, quat = backend.get_robot_pose(robot.name)
                    js = backend.get_joint_states(robot.name)
                    snapshot["robots"][robot.name] = {
                        "basePose": {
                            "position": pos.tolist() if hasattr(pos, 'tolist') else list(pos),
                            "rotation": quat.tolist() if hasattr(quat, 'tolist') else list(quat),
                        },
                        "joints": js.get("positions", {}),
                        "timestamp": js.get("timestamp", 0),
                    }
                except Exception:
                    pass

            for obj in self._sim_manager.scene.objects:
                try:
                    pos, quat = backend.get_object_pose(obj["name"])
                    snapshot["objects"][obj["name"]] = {
                        "position": pos.tolist() if hasattr(pos, 'tolist') else list(pos),
                        "rotation": quat.tolist() if hasattr(quat, 'tolist') else list(quat),
                    }
                except Exception:
                    pass

        return snapshot
