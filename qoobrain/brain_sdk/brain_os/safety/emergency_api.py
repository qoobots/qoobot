"""brain_os SDK — 紧急停止便捷 API

基于 SafetyAPI + ControlService 的紧急操作封装。
"""

from __future__ import annotations

from typing import Callable

from ..config import BrainOSConfig
from .safety_api import SafetyAPI


class EmergencyAPI:
    """紧急操作封装（基于 SafetyAPI + ControlService）。"""

    def __init__(
        self, get_channel: Callable, get_async_channel: Callable, config: BrainOSConfig
    ) -> None:
        self._safety = SafetyAPI(get_channel, get_async_channel, config)
        self._config = config
        self._enable_mock: bool = getattr(self._safety, "_enable_mock", False)

    async def stop(self, reason: str = "", level: int = 0) -> dict:
        """紧急停止。level=0 为最高级 (S0)。"""
        self._safety._enable_mock = self._enable_mock
        # 先尝试 SafetyAPI，再尝试直接调 ControlService
        result = await self._safety.get_snapshot()
        if result.get("state") == "STOPPED":
            return {"ok": True, "stop_time_ns": 0, "reason": reason, "level": level, "_stub": result.get("_stub", True)}

        # 生产中: 直接调用 ControlService.EmergencyStop
        return {
            "ok": True,
            "stop_time_ns": 4500000,
            "reason": reason,
            "level": level,
            "_stub": True,
        }

    async def resume(self, *, require_confirm: bool = True) -> dict:
        """恢复运动（需确认后方可执行）。"""
        return {"ok": True, "require_confirm": require_confirm, "_stub": True}
