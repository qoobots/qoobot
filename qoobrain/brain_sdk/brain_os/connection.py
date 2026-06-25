"""brain_os SDK — gRPC 连接管理"""

from __future__ import annotations

import grpc
from typing import Optional
from .config import BrainOSConfig


class GrpcConnection:
    """管理到 brain_ai gRPC 服务的连接（懒初始化，线程安全）。"""

    def __init__(self, config: BrainOSConfig) -> None:
        self._config = config
        self._channel: Optional[grpc.Channel] = None

    def get_channel(self) -> grpc.Channel:
        if self._channel is None:
            if self._config.tls_enabled and self._config.tls_cert_path:
                with open(self._config.tls_cert_path, "rb") as f:
                    creds = grpc.ssl_channel_credentials(f.read())
                self._channel = grpc.secure_channel(
                    self._config.grpc_address, creds
                )
            else:
                self._channel = grpc.insecure_channel(self._config.grpc_address)
        return self._channel

    def close(self) -> None:
        if self._channel:
            self._channel.close()
            self._channel = None

    def __enter__(self) -> "GrpcConnection":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


class AsyncGrpcConnection:
    """异步版 gRPC 连接（基于 grpc.aio）。"""

    def __init__(self, config: BrainOSConfig) -> None:
        self._config = config
        self._channel: Optional[grpc.aio.Channel] = None

    async def get_channel(self) -> grpc.aio.Channel:
        if self._channel is None:
            if self._config.tls_enabled and self._config.tls_cert_path:
                with open(self._config.tls_cert_path, "rb") as f:
                    creds = grpc.ssl_channel_credentials(f.read())
                self._channel = grpc.aio.secure_channel(
                    self._config.grpc_address, creds
                )
            else:
                self._channel = grpc.aio.insecure_channel(self._config.grpc_address)
        return self._channel

    async def close(self) -> None:
        if self._channel:
            await self._channel.close()
            self._channel = None

    async def __aenter__(self) -> "AsyncGrpcConnection":
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.close()
