"""遥控客户端 SDK

提供完整的 Python 遥控客户端，支持：
- WebSocket 信令连接
- 会话创建/接管/交还
- 控制指令发送
- 状态接收与回调
"""

import asyncio
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import urljoin

import aiohttp

from .commands import TeleopCommand, EmergencyStopCommand
from .enums import RobotMode, SessionState, StopType

logger = logging.getLogger("qoodev.teleop")


@dataclass
class TeleopConfig:
    """遥控客户端配置"""
    server_url: str = "http://localhost:8208"       # qoocloud-teleop 地址
    ws_url: str = "ws://localhost:8208/ws/teleop"   # WebSocket 地址
    robot_id: str = ""
    operator_id: str = "operator"
    operator_name: str = "QooDev Operator"
    auth_token: str = ""
    reconnect_interval: float = 3.0
    heartbeat_interval: float = 1.0
    max_reconnect_attempts: int = 10


@dataclass
class TeleopState:
    """遥控客户端运行时状态"""
    session_id: str = ""
    robot_mode: RobotMode = RobotMode.AUTO
    session_state: SessionState = SessionState.DISCONNECTED
    is_connected: bool = False
    latency_ms: int = 0
    command_count: int = 0


class TeleopError(Exception):
    """遥控客户端异常"""
    pass


class TeleopClient:
    """QooBot 遥控操作客户端

    Usage:
        client = TeleopClient(TeleopConfig(robot_id="qoobot-01"))
        await client.connect()
        await client.request_takeover()
        # 发送指令...
        await client.request_handover()
        await client.disconnect()
    """

    def __init__(self, config: TeleopConfig):
        self.config = config
        self.state = TeleopState()
        self._ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self._session: Optional[aiohttp.ClientSession] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._receive_task: Optional[asyncio.Task] = None
        self._running = False
        self._sequence = 0

        # 回调
        self._state_callbacks: List[Callable[[dict], None]] = []
        self._sensor_callbacks: List[Callable[[dict], None]] = []
        self._event_callbacks: List[Callable[[str, dict], None]] = []

    # ========== 连接管理 ==========

    async def connect(self, media_types: List[str] = None) -> bool:
        """建立遥控会话并连接 WebSocket"""
        if media_types is None:
            media_types = ["VIDEO", "AUDIO", "DATA"]

        self._session = aiohttp.ClientSession()

        # 1. REST 创建会话
        try:
            async with self._session.post(
                urljoin(self.config.server_url, "/api/v1/sessions"),
                json={
                    "robot_id": self.config.robot_id,
                    "operator_id": self.config.operator_id,
                    "operator_name": self.config.operator_name,
                    "auth_token": self.config.auth_token,
                    "media_types": media_types
                }
            ) as resp:
                if resp.status != 200:
                    raise TeleopError(f"Create session failed: HTTP {resp.status}")
                data = await resp.json()
                if data.get("code") != 0:
                    raise TeleopError(f"Create session failed: {data.get('message')}")
                self.state.session_id = data["data"]["session_id"]
                self.state.session_state = SessionState(data["data"]["session_status"])
        except aiohttp.ClientError as e:
            raise TeleopError(f"Cannot connect to server: {e}")

        # 2. WebSocket 连接
        ws_url = f"{self.config.ws_url}/{self.state.session_id}"
        self._ws = await self._session.ws_connect(ws_url)
        self.state.is_connected = True
        self.state.session_state = SessionState.CONNECTED
        self._running = True

        # 3. 启动后台任务
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        self._receive_task = asyncio.create_task(self._receive_loop())

        logger.info(f"TeleopClient connected: session={self.state.session_id}")
        return True

    async def disconnect(self) -> None:
        """断开遥控会话"""
        self._running = False

        # 先交还控制权
        if self.state.robot_mode == RobotMode.TELEOP:
            await self.request_handover()

        # 停止后台任务
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
        if self._receive_task:
            self._receive_task.cancel()

        # 关闭 WebSocket
        if self._ws and not self._ws.closed:
            await self._ws.close()

        # 关闭 HTTP 会话
        if self._session:
            await self._session.close()

        self.state.is_connected = False
        self.state.session_state = SessionState.DISCONNECTED
        logger.info("TeleopClient disconnected")

    # ========== 控制模式 ==========

    async def request_takeover(self) -> bool:
        """请求接管控制权"""
        if self.state.session_state != SessionState.CONNECTED:
            raise TeleopError("Not in CONNECTED state")

        async with self._session.post(
            urljoin(self.config.server_url, f"/api/v1/sessions/{self.state.session_id}/takeover")
        ) as resp:
            data = await resp.json()
            if data.get("code") != 0:
                raise TeleopError(f"Takeover failed: {data.get('message')}")

        self.state.robot_mode = RobotMode.TELEOP
        self.state.session_state = SessionState.TELEOP_ACTIVE
        logger.info("Takeover granted")
        return True

    async def request_handover(self) -> bool:
        """请求交还控制权"""
        async with self._session.post(
            urljoin(self.config.server_url, f"/api/v1/sessions/{self.state.session_id}/release")
        ) as resp:
            data = await resp.json()
            if data.get("code") != 0:
                raise TeleopError(f"Handover failed: {data.get('message')}")

        self.state.robot_mode = RobotMode.AUTO
        self.state.session_state = SessionState.CONNECTED
        logger.info("Handover completed")
        return True

    # ========== 控制指令 ==========

    async def send_command(self, command: TeleopCommand) -> None:
        """发送全身运动遥控指令"""
        if self.state.robot_mode != RobotMode.TELEOP:
            raise TeleopError("Not in TELEOP mode")

        command.session_id = self.state.session_id
        command.sequence = self._sequence
        self._sequence += 1

        await self._ws_send({
            "type": "control.fullbody",
            "payload": command.to_dict()
        })
        self.state.command_count += 1

    async def emergency_stop(self, reason: str = "Operator triggered") -> None:
        """触发紧急停止"""
        await self._ws_send({
            "type": "teleop.emergency_stop",
            "payload": {"reason": reason}
        })
        logger.warning(f"Emergency stop: {reason}")

    async def send_heartbeat(self) -> None:
        """发送心跳包"""
        await self._ws_send({
            "type": "heartbeat",
            "timestamp": int(time.time() * 1000)
        })

    # ========== 回调注册 ==========

    def on_state_update(self, callback: Callable[[dict], None]) -> None:
        """注册状态更新回调"""
        self._state_callbacks.append(callback)

    def on_sensor_data(self, callback: Callable[[dict], None]) -> None:
        """注册传感器数据回调"""
        self._sensor_callbacks.append(callback)

    def on_event(self, callback: Callable[[str, dict], None]) -> None:
        """注册事件回调"""
        self._event_callbacks.append(callback)

    # ========== 内部方法 ==========

    async def _ws_send(self, message: dict) -> None:
        if self._ws and not self._ws.closed:
            await self._ws.send_json(message)

    async def _heartbeat_loop(self) -> None:
        """心跳发送循环"""
        while self._running:
            try:
                await asyncio.sleep(self.config.heartbeat_interval)
                if self._ws and not self._ws.closed:
                    await self.send_heartbeat()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")

    async def _receive_loop(self) -> None:
        """消息接收循环"""
        while self._running:
            try:
                msg = await self._ws.receive()
                if msg.type == aiohttp.WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    await self._handle_message(data)
                elif msg.type == aiohttp.WSMsgType.CLOSED:
                    logger.warning("WebSocket closed by server")
                    self._running = False
                    break
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    logger.error(f"WebSocket error: {self._ws.exception()}")
                    break
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Receive error: {e}")

    async def _handle_message(self, msg: dict) -> None:
        """处理接收到的消息"""
        msg_type = msg.get("type", "")

        if msg_type == "robot.status":
            payload = msg.get("payload", {})
            self.state.latency_ms = payload.get("system", {}).get("network_latency_ms", 0)
            for cb in self._state_callbacks:
                try:
                    cb(payload)
                except Exception as e:
                    logger.error(f"State callback error: {e}")

        elif msg_type == "robot.sensor":
            payload = msg.get("payload", {})
            for cb in self._sensor_callbacks:
                try:
                    cb(payload)
                except Exception as e:
                    logger.error(f"Sensor callback error: {e}")

        elif msg_type in ("session.update", "session.event"):
            for cb in self._event_callbacks:
                try:
                    cb(msg_type, msg.get("payload", {}))
                except Exception as e:
                    logger.error(f"Event callback error: {e}")
