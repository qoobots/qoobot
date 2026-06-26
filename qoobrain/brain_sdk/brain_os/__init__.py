"""Brain OS Python SDK.

人形机器人操作系统 Python SDK — 自然语言指令到机器人执行的完整工具链。

Quickstart:
    from brain_os import BrainOSClient

    async with BrainOSClient() as robot:
        result = await robot.cognition.parse_intent("把红色杯子放到桌上")
        print(result.intent)

Core API:
    BrainOSClient         — 统一客户端入口 (上下文管理器)
    BrainOSConfig         — 连接与运行时配置

Exceptions:
    BrainOSError          — 基础异常
    ConnectionError       — gRPC 连接失败
    TimeoutError          — 请求超时
    RobotNotReadyError    — 机器人未就绪
"""

from brain_os.client import BrainOSClient
from brain_os.config import BrainOSConfig
from brain_os.connection import GrpcConnection, AsyncGrpcConnection
from brain_os.utils.errors import (
    BrainOSError,
    ConnectionError,
    TimeoutError,
    AuthenticationError,
    RobotNotReadyError,
    InvalidRequestError,
    HITLTimeoutError,
)
from brain_os.utils.async_helpers import with_timeout, retry, collect_stream

__all__ = [
    "BrainOSClient",
    "BrainOSConfig",
    "GrpcConnection",
    "AsyncGrpcConnection",
    "BrainOSError",
    "ConnectionError",
    "TimeoutError",
    "AuthenticationError",
    "RobotNotReadyError",
    "InvalidRequestError",
    "HITLTimeoutError",
    "with_timeout",
    "retry",
    "collect_stream",
]

__version__ = "0.1.0"
