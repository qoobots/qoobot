"""信令客户端 — WebSocket 连接管理与消息收发

实现与 qoocloud 之间的 WebSocket 信令通道：
- 连接建立/断开/重连
- JWT Token 认证
- 机器人发现与选择
- 会话管理
- 心跳保活
- 消息收发与分发

对应功能：CON-01 (WebSocket 信令通道)
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum, auto

from console.core.signaling.heartbeat import HeartbeatManager
from console.core.signaling.messages import MessageType, SignalingMessage

logger = logging.getLogger(__name__)


class ConnectionState(Enum):
    """连接状态"""
    DISCONNECTED = auto()
    CONNECTING = auto()
    CONNECTED = auto()
    AUTHENTICATED = auto()
    SESSION_ACTIVE = auto()
    RECONNECTING = auto()


@dataclass
class ConnectionConfig:
    """连接配置"""
    url: str = "wss://cloud.qoobot.dev/signaling"
    token: str = ""
    robot_id: str = ""
    reconnect_max_attempts: int = 10
    reconnect_base_delay: float = 1.0      # 基础重连延迟 (秒)
    reconnect_max_delay: float = 30.0       # 最大重连延迟 (秒)
    heartbeat_interval: float = 5.0         # 心跳间隔 (秒)
    heartbeat_timeout: float = 15.0         # 心跳超时 (秒)


class SignalingClient:
    """WebSocket 信令客户端

    管理与 qoocloud 之间的 WebSocket 信令连接，提供：
    - 异步连接/断开/重连
    - JWT 认证流程
    - 机器人发现与选择
    - 会话建立与销毁
    - 消息收发与回调分发
    - 集成心跳管理器
    """

    def __init__(self, config: ConnectionConfig | None = None) -> None:
        self._config = config or ConnectionConfig()
        self._ws: "asyncio.Queue | None" = None  # type: ignore  # Placeholder for actual WebSocket
        self._state: ConnectionState = ConnectionState.DISCONNECTED
        self._robot_id: str = ""
        self._session_id: str = ""
        self._sequence: int = 0
        self._reconnect_attempt: int = 0
        self._reconnect_task: asyncio.Task | None = None

        # 消息处理器注册表
        self._handlers: dict[MessageType, list[Callable]] = {}
        self._message_handler: Callable | None = None

        # 心跳管理
        self._heartbeat = HeartbeatManager(
            interval_seconds=self._config.heartbeat_interval,
            timeout_seconds=self._config.heartbeat_timeout,
        )
        self._heartbeat.set_send_callback(self._send_heartbeat)
        self._heartbeat.set_disconnect_callback(self._on_heartbeat_lost)

        # 回调
        self._on_state_changed: Callable | None = None
        self._on_robot_state: Callable | None = None
        self._on_alert: Callable | None = None
        self._on_error: Callable | None = None

    # ------------------------------------------------------------------
    # 公共属性
    # ------------------------------------------------------------------

    @property
    def state(self) -> ConnectionState:
        return self._state

    @property
    def is_connected(self) -> bool:
        return self._state in (ConnectionState.CONNECTED,
                               ConnectionState.AUTHENTICATED,
                               ConnectionState.SESSION_ACTIVE)

    @property
    def latency_ms(self) -> float:
        return self._heartbeat.latency_ms

    @property
    def robot_id(self) -> str:
        return self._robot_id

    @property
    def session_id(self) -> str:
        return self._session_id

    # ------------------------------------------------------------------
    # 回调注册
    # ------------------------------------------------------------------

    def on_state_changed(self, callback: Callable) -> None:
        """注册状态变更回调"""
        self._on_state_changed = callback

    def on_robot_state(self, callback: Callable) -> None:
        """注册机器人状态回调"""
        self._on_robot_state = callback

    def on_alert(self, callback: Callable) -> None:
        """注册告警回调"""
        self._on_alert = callback

    def on_error(self, callback: Callable) -> None:
        """注册错误回调"""
        self._on_error = callback

    def register_handler(self, msg_type: MessageType, handler: Callable) -> None:
        """注册消息类型处理器"""
        if msg_type not in self._handlers:
            self._handlers[msg_type] = []
        self._handlers[msg_type].append(handler)

    # ------------------------------------------------------------------
    # 连接管理
    # ------------------------------------------------------------------

    async def connect(self) -> bool:
        """建立 WebSocket 连接并完成认证。

        Returns:
            True 表示连接认证成功。
        """
        self._set_state(ConnectionState.CONNECTING)
        logger.info("Connecting to %s", self._config.url)

        try:
            # WebSocket 连接（实际实现中替换为 websockets 库）
            # self._ws = await websockets.connect(self._config.url)
            # 当前为 stub 实现，标记已连接
            self._set_state(ConnectionState.CONNECTED)

            # 认证
            if not await self._authenticate():
                return False

            # 选择机器人
            if self._config.robot_id:
                if not await self.select_robot(self._config.robot_id):
                    logger.warning("Failed to select robot: %s", self._config.robot_id)
                    return False

            # 启动心跳
            await self._heartbeat.start()
            self._set_state(ConnectionState.SESSION_ACTIVE)

            # 启动消息接收循环
            # asyncio.create_task(self._receive_loop())

            logger.info("Connected and authenticated (robot=%s)", self._config.robot_id)
            return True

        except Exception:
            logger.exception("Connection failed")
            self._set_state(ConnectionState.DISCONNECTED)
            return False

    async def disconnect(self) -> None:
        """断开连接"""
        logger.info("Disconnecting...")
        self._reconnect_attempt = self._config.reconnect_max_attempts  # 阻止重连

        await self._heartbeat.stop()

        # 发送会话关闭消息
        if self._session_id:
            try:
                await self._send_message(
                    SignalingMessage(type=MessageType.SESSION_CLOSE)
                )
            except Exception:
                pass

        self._set_state(ConnectionState.DISCONNECTED)
        self._session_id = ""
        logger.info("Disconnected")

    async def select_robot(self, robot_id: str) -> bool:
        """选择要遥控的机器人"""
        self._robot_id = robot_id
        msg = SignalingMessage.select_robot(robot_id)
        await self._send_message(msg)
        # 实际实现中等待 SELECT_ROBOT_RESPONSE
        return True

    async def send_command(self, cmd_type: MessageType, payload: dict) -> None:
        """发送控制指令"""
        msg = SignalingMessage(
            type=cmd_type,
            payload=payload,
            sequence=self._next_sequence(),
        )
        await self._send_message(msg)

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    def _set_state(self, state: ConnectionState) -> None:
        """更新连接状态并触发回调"""
        old_state = self._state
        self._state = state
        if old_state != state and self._on_state_changed:
            try:
                self._on_state_changed(state, old_state)
            except Exception:
                logger.exception("State change callback failed")

    def _next_sequence(self) -> int:
        self._sequence += 1
        return self._sequence

    async def _authenticate(self) -> bool:
        """JWT 认证流程"""
        msg = SignalingMessage.auth(self._config.token)
        await self._send_message(msg)
        # 实际实现中等待 AUTH_RESPONSE
        self._set_state(ConnectionState.AUTHENTICATED)
        return True

    async def _send_message(self, message: SignalingMessage) -> None:
        """发送信令消息（stub 实现）"""
        # 实际实现: await self._ws.send(message.to_json())
        logger.debug("SEND %s", message.type.value)

    async def _send_heartbeat(self, sequence: int) -> None:
        """发送心跳包"""
        msg = SignalingMessage(
            type=MessageType.HEARTBEAT,
            payload={"seq": sequence},
        )
        await self._send_message(msg)

    async def _on_heartbeat_lost(self) -> None:
        """心跳丢失处理"""
        logger.warning("Heartbeat lost, triggering reconnect")
        await self._reconnect()

    async def _reconnect(self) -> None:
        """自动重连"""
        if self._reconnect_attempt >= self._config.reconnect_max_attempts:
            logger.error("Max reconnect attempts reached")
            self._set_state(ConnectionState.DISCONNECTED)
            return

        self._set_state(ConnectionState.RECONNECTING)
        delay = min(
            self._config.reconnect_base_delay * (2 ** self._reconnect_attempt),
            self._config.reconnect_max_delay,
        )
        logger.info("Reconnecting in %.1fs (attempt %d/%d)",
                     delay, self._reconnect_attempt + 1,
                     self._config.reconnect_max_attempts)

        await asyncio.sleep(delay)
        self._reconnect_attempt += 1

        try:
            await self.connect()
            if self.is_connected:
                self._reconnect_attempt = 0
                return
        except Exception:
            logger.exception("Reconnect attempt failed")

        # 继续重连
        asyncio.create_task(self._reconnect())

    async def _receive_loop(self) -> None:
        """消息接收循环（stub 实现）"""
        # 实际实现:
        # async for raw_message in self._ws:
        #     msg = SignalingMessage.from_json(raw_message)
        #     await self._dispatch(msg)
        pass

    async def _dispatch(self, message: SignalingMessage) -> None:
        """分发消息到处理器"""
        # 调用类型注册的处理器
        handlers = self._handlers.get(message.type, [])
        for handler in handlers:
            try:
                handler(message)
            except Exception:
                logger.exception("Handler failed for %s", message.type)

        # 路由到指定回调
        if message.type == MessageType.ROBOT_STATE and self._on_robot_state:
            self._on_robot_state(message.payload)
        elif message.type == MessageType.ALERT and self._on_alert:
            self._on_alert(message.payload)
        elif message.type == MessageType.ERROR and self._on_error:
            self._on_error(message.payload)
