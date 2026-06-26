"""仿真管理器。

管理多个仿真后端实例，提供统一的启停接口。
"""

import logging
import threading
import time
from pathlib import Path
from typing import Optional, Type

from .interface import (
    SimBackend,
    SimConfig,
    SimControlCommand,
    SimScene,
    SimSensorData,
    SimState,
)

logger = logging.getLogger(__name__)

# 后端注册表
_BACKEND_REGISTRY: dict[str, Type[SimBackend]] = {}


def register_backend(name: str, backend_cls: Type[SimBackend]) -> None:
    """注册仿真后端。"""
    _BACKEND_REGISTRY[name] = backend_cls
    logger.info(f"注册仿真后端: {name} -> {backend_cls.__name__}")


def get_backend(name: str) -> Optional[Type[SimBackend]]:
    """获取注册的后端类。"""
    return _BACKEND_REGISTRY.get(name)


def list_backends() -> list[str]:
    """列出所有已注册的后端。"""
    return list(_BACKEND_REGISTRY.keys())


class SimManager:
    """仿真管理器 — 统一的仿真生命周期入口。

    Usage:
        manager = SimManager(SimConfig(backend="mujoco"))
        manager.initialize()
        manager.load_scene(scene)
        manager.start()
        # ... 运行循环 ...
        manager.stop()
        manager.shutdown()
    """

    def __init__(self, config: SimConfig):
        self.config = config
        self._backend: Optional[SimBackend] = None
        self._thread: Optional[threading.Thread] = None
        self._running = threading.Event()
        self._sensor_callbacks: list[callable] = []
        self._step_callbacks: list[callable] = []

    def initialize(self) -> None:
        """初始化仿真后端。"""
        backend_cls = get_backend(self.config.backend)
        if backend_cls is None:
            # 尝试延迟导入
            if self.config.backend == "mujoco":
                from .muJoCo_backend import MuJoCoBackend  # noqa: F811
                backend_cls = MuJoCoBackend
            elif self.config.backend == "isaac_sim":
                from .isaac_sim_backend import IsaacSimBackend  # noqa: F811
                backend_cls = IsaacSimBackend
            else:
                raise ValueError(f"未知的仿真后端: {self.config.backend}。"
                                 f"可用: {list_backends()}")

        self._backend = backend_cls(self.config)
        self._backend.initialize()
        logger.info(f"仿真后端初始化完成: {self.config.backend}")

    def load_scene(self, scene: SimScene) -> None:
        """加载仿真场景。"""
        if self._backend is None:
            raise RuntimeError("请先调用 initialize()")
        self._backend.load_scene(scene)
        logger.info(f"场景加载完成: {scene.name}")

    def start(self) -> None:
        """启动仿真主循环（独立线程）。"""
        if self._backend is None:
            raise RuntimeError("请先调用 initialize()")
        self._running.set()
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="sim-loop")
        self._thread.start()
        logger.info("仿真主循环已启动")

    def stop(self) -> None:
        """停止仿真主循环。"""
        self._running.clear()
        if self._thread is not None:
            self._thread.join(timeout=5.0)
            self._thread = None
        logger.info("仿真主循环已停止")

    def pause(self) -> None:
        """暂停仿真。"""
        if self._backend:
            self._backend.pause()

    def resume(self) -> None:
        """恢复仿真。"""
        if self._backend:
            self._backend.resume()

    def shutdown(self) -> None:
        """关闭仿真。"""
        self.stop()
        if self._backend:
            self._backend.shutdown()
            self._backend = None
        logger.info("仿真管理器已关闭")

    def step_once(self) -> None:
        """手动推进单步。"""
        if self._backend and self._backend.is_ready:
            self._backend.step()
            self._notify_step()

    def apply_control(self, command: SimControlCommand) -> None:
        """发送控制指令。"""
        if self._backend:
            self._backend.apply_control(command)

    def get_sensor_data(self, sensor_name: str = "") -> Optional[SimSensorData]:
        """获取传感器数据。"""
        if self._backend is None:
            return None
        if sensor_name:
            return self._backend.get_sensor_data(sensor_name)
        data = self._backend.get_all_sensor_data()
        return data[0] if data else None

    def on_sensor_data(self, callback: callable) -> None:
        """注册传感器数据回调。"""
        self._sensor_callbacks.append(callback)

    def on_step(self, callback: callable) -> None:
        """注册步进回调。"""
        self._step_callbacks.append(callback)

    def render(self, camera_name: str = ""):
        """渲染一帧图像。"""
        if self._backend:
            return self._backend.render(camera_name)
        return None

    @property
    def state(self) -> SimState:
        if self._backend:
            return self._backend.state
        return SimState.UNINITIALIZED

    @property
    def backend(self) -> Optional[SimBackend]:
        return self._backend

    # ── 内部 ──────────────────────────────────────────

    def _run_loop(self) -> None:
        """仿真主循环（在独立线程中运行）。"""
        last_time = time.perf_counter()
        target_dt = self.config.time_step if self.config.real_time else 0

        while self._running.is_set():
            loop_start = time.perf_counter()

            try:
                if self._backend and self._backend.is_ready:
                    self._backend.step()
                    self._notify_step()

                    # 通知传感器数据
                    for cb in self._sensor_callbacks:
                        try:
                            cb(self._backend.get_all_sensor_data())
                        except Exception:
                            logger.exception("传感器回调异常")

            except Exception:
                logger.exception("仿真步进异常")
                break

            # 实时模式等待
            if target_dt > 0:
                elapsed = time.perf_counter() - loop_start
                sleep_time = target_dt - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)

    def _notify_step(self) -> None:
        """通知步进回调。"""
        for cb in self._step_callbacks:
            try:
                cb()
            except Exception:
                logger.exception("步进回调异常")
