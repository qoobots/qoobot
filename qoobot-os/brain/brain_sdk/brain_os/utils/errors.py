"""brain_os SDK — 错误类型"""

from __future__ import annotations


class BrainOSError(Exception):
    """SDK 基础异常。"""
    pass


class ConnectionError(BrainOSError):
    """gRPC 连接失败。"""
    pass


class TimeoutError(BrainOSError):
    """请求超时。"""
    pass


class AuthenticationError(BrainOSError):
    """认证失败。"""
    pass


class RobotNotReadyError(BrainOSError):
    """机器人未就绪（安全停止或初始化中）。"""
    pass


class InvalidRequestError(BrainOSError):
    """请求参数无效。"""
    pass


class HITLTimeoutError(BrainOSError):
    """HITL 超时（自动执行推荐方案）。"""
    pass
