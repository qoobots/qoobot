"""brain_os SDK — 异步工具函数"""

from __future__ import annotations

import asyncio
from typing import AsyncIterator, TypeVar, Callable, Any

T = TypeVar("T")


async def with_timeout(coro, timeout_sec: float):
    """给协程加超时包装。"""
    return await asyncio.wait_for(coro, timeout=timeout_sec)


async def retry(
    coro_factory: Callable[[], Any],
    *,
    max_attempts: int = 3,
    delay_sec: float = 0.5,
    exceptions: tuple = (Exception,),
):
    """
    带重试的协程执行器。

    Args:
        coro_factory: 每次调用返回新协程的工厂函数（lambda: stub.Call(req)）
        max_attempts: 最大重试次数
        delay_sec:    重试间隔（指数退避）
        exceptions:   触发重试的异常类型
    """
    last_exc: Exception | None = None
    for attempt in range(max_attempts):
        try:
            return await coro_factory()
        except exceptions as exc:
            last_exc = exc
            if attempt < max_attempts - 1:
                await asyncio.sleep(delay_sec * (2 ** attempt))
    raise last_exc  # type: ignore[misc]


async def collect_stream(stream: AsyncIterator[T]) -> list[T]:
    """将异步流收集为列表（调试用）。"""
    return [item async for item in stream]
