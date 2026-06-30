"""插件基类 — 设备驱动插件接口

所有设备驱动插件（手柄/动捕/VR）均继承此基类。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional


class PluginState(Enum):
    """插件状态"""
    UNLOADED = "unloaded"
    LOADED = "loaded"
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"
    STOPPED = "stopped"


@dataclass
class PluginInfo:
    """插件元信息"""
    name: str
    version: str = "0.1.0"
    author: str = ""
    description: str = ""
    plugin_type: str = "generic"  # gamepad / mocap / vr / custom

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "version": self.version,
            "author": self.author,
            "description": self.description,
            "type": self.plugin_type,
        }


# ------------------------------------------------------------------
# 插件基类
# ------------------------------------------------------------------

class BasePlugin(ABC):
    """设备驱动插件基类

    所有外部设备驱动（手柄、动捕、VR）均需实现此接口。

    生命周期: load() → init() → start() → [运行] → stop() → unload()
    """

    def __init__(self) -> None:
        self._state = PluginState.UNLOADED
        self._info = PluginInfo(name=self.__class__.__name__)

        # 回调
        self.on_state_change: Optional[Callable[[PluginState], None]] = None
        self.on_data: Optional[Callable[[Any], None]] = None

    @property
    def state(self) -> PluginState:
        return self._state

    @property
    def info(self) -> PluginInfo:
        return self._info

    @property
    def is_running(self) -> bool:
        return self._state == PluginState.RUNNING

    # ---- 生命周期 ----

    def load(self) -> bool:
        """加载插件 — 检查依赖和配置"""
        try:
            result = self._on_load()
            self._transition_to(PluginState.LOADED) if result else None
            return result
        except Exception as e:
            self._transition_to(PluginState.ERROR)
            return False

    def init(self) -> bool:
        """初始化插件 — 打开设备连接"""
        try:
            result = self._on_init()
            self._transition_to(PluginState.INITIALIZING) if result else None
            return result
        except Exception as e:
            self._transition_to(PluginState.ERROR)
            return False

    def start(self) -> bool:
        """启动数据采集"""
        try:
            result = self._on_start()
            self._transition_to(PluginState.RUNNING) if result else None
            return result
        except Exception as e:
            self._transition_to(PluginState.ERROR)
            return False

    def pause(self) -> None:
        """暂停数据采集"""
        self._on_pause()
        self._transition_to(PluginState.PAUSED)

    def resume(self) -> None:
        """恢复数据采集"""
        self._on_resume()
        self._transition_to(PluginState.RUNNING)

    def stop(self) -> None:
        """停止插件"""
        self._on_stop()
        self._transition_to(PluginState.STOPPED)

    def unload(self) -> None:
        """卸载插件"""
        self._on_unload()
        self._transition_to(PluginState.UNLOADED)

    # ---- 子类需实现的抽象方法 ----

    @abstractmethod
    def _on_load(self) -> bool:
        """加载时的初始化检查"""
        ...

    @abstractmethod
    def _on_init(self) -> bool:
        """设备初始化/连接"""
        ...

    @abstractmethod
    def _on_start(self) -> bool:
        """启动数据采集"""
        ...

    @abstractmethod
    def _on_stop(self) -> None:
        """停止数据采集"""
        ...

    def _on_pause(self) -> None:
        """暂停数据采集（可选）"""
        pass

    def _on_resume(self) -> None:
        """恢复数据采集（可选）"""
        pass

    def _on_unload(self) -> None:
        """卸载时清理资源"""
        pass

    # ---- 内部 ----

    def _transition_to(self, state: PluginState) -> None:
        old = self._state
        self._state = state
        if old != state and self.on_state_change:
            self.on_state_change(state)


# ------------------------------------------------------------------
# 插件管理器
# ------------------------------------------------------------------

class PluginManager:
    """插件管理器 — 发现/加载/生命周期管理"""

    def __init__(self) -> None:
        self._plugins: dict[str, BasePlugin] = {}

    @property
    def plugins(self) -> dict[str, BasePlugin]:
        return dict(self._plugins)

    @property
    def running_plugins(self) -> list[BasePlugin]:
        return [p for p in self._plugins.values() if p.is_running]

    def register(self, plugin: BasePlugin) -> None:
        """注册插件"""
        self._plugins[plugin.info.name] = plugin

    def unregister(self, name: str) -> None:
        """注销插件"""
        plugin = self._plugins.pop(name, None)
        if plugin and plugin.is_running:
            plugin.stop()
            plugin.unload()

    def get(self, name: str) -> Optional[BasePlugin]:
        return self._plugins.get(name)

    def start_all(self) -> None:
        """启动所有已注册插件"""
        for plugin in self._plugins.values():
            if plugin.state == PluginState.LOADED:
                plugin.init()
                plugin.start()

    def stop_all(self) -> None:
        """停止所有运行中的插件"""
        for plugin in self._plugins.values():
            if plugin.is_running:
                plugin.stop()
