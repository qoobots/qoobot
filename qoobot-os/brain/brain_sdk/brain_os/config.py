"""brain_os SDK — 配置管理"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class BrainOSConfig:
    """SDK 全局配置，支持从环境变量或代码初始化。"""

    # ── gRPC 后端地址 ──────────────────────────────────────────────
    grpc_host: str = field(
        default_factory=lambda: os.getenv("BRAIN_OS_GRPC_HOST", "localhost")
    )
    grpc_port: int = field(
        default_factory=lambda: int(os.getenv("BRAIN_OS_GRPC_PORT", "50051"))
    )

    # ── WebSocket 事件流地址 ────────────────────────────────────────
    ws_url: str = field(
        default_factory=lambda: os.getenv("BRAIN_OS_WS_URL", "ws://localhost:8765")
    )

    # ── 安全 / TLS ──────────────────────────────────────────────────
    tls_enabled: bool = field(
        default_factory=lambda: os.getenv("BRAIN_OS_TLS", "false").lower() == "true"
    )
    tls_cert_path: Optional[str] = field(
        default_factory=lambda: os.getenv("BRAIN_OS_TLS_CERT")
    )

    # ── 超时 ────────────────────────────────────────────────────────
    grpc_timeout_sec: float = 10.0
    ws_reconnect_interval_sec: float = 2.0
    hitl_timeout_sec: float = 3.0

    # ── 机器人 ID ────────────────────────────────────────────────────
    robot_id: str = field(
        default_factory=lambda: os.getenv("BRAIN_OS_ROBOT_ID", "robot_01")
    )

    # ── 日志 ────────────────────────────────────────────────────────
    log_level: str = field(
        default_factory=lambda: os.getenv("BRAIN_OS_LOG_LEVEL", "INFO")
    )

    @property
    def grpc_address(self) -> str:
        return f"{self.grpc_host}:{self.grpc_port}"

    @classmethod
    def from_env(cls) -> "BrainOSConfig":
        """从环境变量构建配置（工厂方法）。"""
        return cls()
