"""心跳管理 — WebSocket 连接保活与延迟测量"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class HeartbeatStats:
    """心跳统计"""
    latency_ms: float = 0.0           # 当前延迟 (ms)
    avg_latency_ms: float = 0.0       # 平均延迟 (ms)
    min_latency_ms: float = 9999.0    # 最小延迟 (ms)
    max_latency_ms: float = 0.0       # 最大延迟 (ms)
    sent_count: int = 0               # 已发送心跳数
    received_count: int = 0           # 已收到心跳回复数
    missed_count: int = 0             # 丢失心跳数

    def record(self, latency_ms: float) -> None:
        """记录一次心跳往返延迟"""
        self.latency_ms = latency_ms
        self.received_count += 1
        if self.received_count == 1:
            self.avg_latency_ms = latency_ms
        else:
            self.avg_latency_ms = (self.avg_latency_ms * 0.7 + latency_ms * 0.3)
        self.min_latency_ms = min(self.min_latency_ms, latency_ms)
        self.max_latency_ms = max(self.max_latency_ms, latency_ms)


class HeartbeatManager:
    """心跳管理器

    负责定期发送心跳包、接收 ACK、计算延迟、
    检测连接中断并触发重连。

    功能对应 CON-03（连接健康检测）。
    """

    def __init__(
        self,
        interval_seconds: float = 5.0,
        timeout_seconds: float = 15.0,
        max_missed: int = 3,
    ) -> None:
        """
        Args:
            interval_seconds: 心跳发送间隔 (秒)
            timeout_seconds: 单个心跳超时时间 (秒)
            max_missed: 连续丢失心跳阈值，超过则判定断开
        """
        self._interval = interval_seconds
        self._timeout = timeout_seconds
        self._max_missed = max_missed
        self._stats = HeartbeatStats()
        self._running = False
        self._task: asyncio.Task | None = None
        self._send_callback: callable | None = None  # type: ignore
        self._recv_callback: callable | None = None  # type: ignore
        self._disconnect_callback: callable | None = None  # type: ignore
        self._pending_timestamps: dict[int, float] = {}
        self._consecutive_missed = 0

    @property
    def stats(self) -> HeartbeatStats:
        return self._stats

    @property
    def latency_ms(self) -> float:
        return self._stats.latency_ms

    @property
    def is_healthy(self) -> bool:
        """连接是否健康（延迟 < 500ms 且无连续丢失）"""
        return (
            self._stats.latency_ms < 500.0
            and self._consecutive_missed < self._max_missed
        )

    def set_send_callback(self, callback: callable) -> None:  # type: ignore
        """设置心跳发送回调（用于发送 WebSocket 消息）"""
        self._send_callback = callback

    def set_disconnect_callback(self, callback: callable) -> None:  # type: ignore
        """设置断线回调"""
        self._disconnect_callback = callback

    async def start(self) -> None:
        """启动心跳循环"""
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("Heartbeat manager started (interval=%.1fs, timeout=%.1fs)",
                     self._interval, self._timeout)

    async def stop(self) -> None:
        """停止心跳循环"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("Heartbeat manager stopped")

    def on_heartbeat_ack(self, sequence: int) -> None:
        """收到心跳 ACK"""
        send_time = self._pending_timestamps.pop(sequence, None)
        if send_time is None:
            return
        latency_ms = (time.monotonic() - send_time) * 1000.0
        self._stats.record(latency_ms)
        self._consecutive_missed = 0
        logger.debug("Heartbeat ack seq=%d latency=%.1fms", sequence, latency_ms)

    async def _loop(self) -> None:
        """心跳主循环"""
        sequence = 0
        while self._running:
            sequence += 1
            self._stats.sent_count += 1

            # 记录发送时间用于延迟计算
            send_time = time.monotonic()
            self._pending_timestamps[sequence] = send_time

            # 通过回调发送心跳
            if self._send_callback:
                try:
                    await self._send_callback(sequence)
                except Exception:
                    logger.exception("Heartbeat send failed")
                    self._consecutive_missed += 1
            else:
                self._consecutive_missed += 1

            # 等待心跳间隔
            await asyncio.sleep(self._interval)

            # 清理超时的未响应心跳
            now = time.monotonic()
            for seq, t in list(self._pending_timestamps.items()):
                if now - t > self._timeout:
                    self._pending_timestamps.pop(seq, None)
                    self._consecutive_missed += 1
                    self._stats.missed_count += 1

            # 检查是否断线
            if self._consecutive_missed >= self._max_missed:
                logger.warning("Connection lost: %d consecutive heartbeats missed",
                               self._consecutive_missed)
                if self._disconnect_callback:
                    try:
                        await self._disconnect_callback()
                    except Exception:
                        logger.exception("Disconnect callback failed")
                return

            # 限制 pending 大小
            if len(self._pending_timestamps) > 100:
                oldest = min(self._pending_timestamps.keys())
                self._pending_timestamps.pop(oldest, None)
