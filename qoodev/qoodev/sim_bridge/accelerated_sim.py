"""
加速仿真 — 超实时仿真（>1x 实时），批量并行训练

支持 headless 模式、批量场景并行、GPU 加速物理计算。
v1.7: 集成 SimManager 后端，实现真实物理仿真加速。
"""

from __future__ import annotations

import logging
import time
import threading
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)


@dataclass
class AcceleratedSimConfig:
    speedup_factor: float = 10.0     # 目标加速倍率（>1 超实时）
    headless: bool = True            # 无渲染模式
    num_workers: int = 4             # 并行工作线程
    physics_substeps: int = 10       # 物理子步
    gpu_physics: bool = False        # GPU 加速物理
    batch_scenes: int = 1            # 批量场景数
    deterministic: bool = True       # 确定性仿真
    backend: str = "mujoco"          # 仿真后端: mujoco, isaac_sim


@dataclass
class SimWorkerResult:
    worker_id: int
    scene_id: int
    steps_completed: int
    wall_time_sec: float
    sim_time_sec: float
    effective_speedup: float
    metrics: Dict = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)


class AcceleratedSimulation:
    """加速仿真管理器 — 支持真实后端集成或纯模拟模式。"""

    def __init__(self, config: Optional[AcceleratedSimConfig] = None):
        self.config = config or AcceleratedSimConfig()
        self._workers: Dict[int, threading.Thread] = {}
        self._results: List[SimWorkerResult] = []
        self._running = False
        self._lock = threading.Lock()
        self._backends: Dict[int, Any] = {}  # worker_id -> SimManager
        self._has_real_backend = False

    def _try_init_backend(self, worker_id: int, scene_config: Dict) -> Optional[Any]:
        """尝试初始化真实仿真后端；失败则返回 None（降级为模拟模式）。"""
        try:
            from qoodev.sim_bridge.interface import SimConfig
            from qoodev.sim_bridge.manager import SimManager
            from qoodev.sim_bridge.scene_loader import SceneLoader

            sim_cfg = SimConfig(
                backend=self.config.backend,
                headless=self.config.headless,
                time_step=0.005,
                real_time=False,  # 超实时模式不锁实时
            )
            mgr = SimManager(sim_cfg)
            mgr.initialize()

            # 加载场景
            scene_name = scene_config.get("scene", "empty")
            loader = SceneLoader()
            try:
                sim_scene = loader.load(scene_name)
                mgr.load_scene(sim_scene)
            except Exception:
                # 场景加载失败时创建空场景
                from qoodev.sim_bridge.interface import SimScene
                sim_scene = SimScene(name="batch_worker", description="Batch simulation scene")
                mgr.load_scene(sim_scene)

            mgr.start()
            self._has_real_backend = True
            logger.info(f"Worker {worker_id}: real backend ({self.config.backend}) initialized")
            return mgr
        except ImportError as e:
            logger.info(f"Worker {worker_id}: backend not available ({e}), using simulation mode")
            return None
        except Exception as e:
            logger.warning(f"Worker {worker_id}: backend init failed ({e}), falling back to simulation")
            return None

    def run_batch(self, scene_configs: List[Dict], total_steps: int,
                  step_callback: Optional[Callable] = None) -> List[SimWorkerResult]:
        """批量并行运行多个仿真场景。

        Args:
            scene_configs: 场景配置列表，每项包含 scene/scene_path 等
            total_steps: 每个场景运行的总步数
            step_callback: 每步回调 (worker_id, scene_id, step, sim_time) -> None

        Returns:
            所有 worker 的结果列表
        """
        self._running = True
        self._results = []

        with ThreadPoolExecutor(max_workers=self.config.num_workers) as executor:
            futures = []
            for i, scene_cfg in enumerate(scene_configs):
                future = executor.submit(
                    self._run_scene,
                    worker_id=i % self.config.num_workers,
                    scene_id=i,
                    scene_config=scene_cfg,
                    total_steps=total_steps,
                    callback=step_callback,
                )
                futures.append(future)

            for future in as_completed(futures):
                try:
                    result = future.result(timeout=600)
                    with self._lock:
                        self._results.append(result)
                except Exception as e:
                    logger.error(f"Scene worker failed: {e}")

        self._running = False
        return self._results

    def _run_scene(self, worker_id: int, scene_id: int, scene_config: Dict,
                   total_steps: int, callback: Optional[Callable] = None) -> SimWorkerResult:
        """运行单个仿真场景（优先使用真实后端）。"""
        result = SimWorkerResult(
            worker_id=worker_id,
            scene_id=scene_id,
            steps_completed=0,
            wall_time_sec=0.0,
            sim_time_sec=0.0,
            effective_speedup=0.0,
        )

        dt = 0.005  # 物理步长
        wall_start = time.time()

        # 尝试获取真实后端
        backend = self._try_init_backend(worker_id, scene_config)

        try:
            if backend is not None:
                result = self._run_with_backend(backend, worker_id, scene_id,
                                                 total_steps, dt, wall_start, callback, result)
            else:
                result = self._run_simulated(worker_id, scene_id, scene_config,
                                              total_steps, dt, wall_start, callback, result)
        except Exception as e:
            result.errors.append(str(e))
            logger.error(f"Scene {scene_id} worker {worker_id} error: {e}")
        finally:
            if backend is not None:
                try:
                    backend.shutdown()
                except Exception:
                    pass

        result.wall_time_sec = time.time() - wall_start
        result.sim_time_sec = total_steps * dt
        result.effective_speedup = result.sim_time_sec / max(result.wall_time_sec, 1e-6)

        logger.info(f"Scene {scene_id}: {result.effective_speedup:.1f}x speedup "
                    f"({'backend' if backend else 'simulated'}, "
                    f"{result.steps_completed} steps in {result.wall_time_sec:.2f}s)")

        return result

    def _run_with_backend(self, backend, worker_id: int, scene_id: int,
                           total_steps: int, dt: float, wall_start: float,
                           callback: Optional[Callable], result: SimWorkerResult) -> SimWorkerResult:
        """使用真实仿真后端运行。"""
        step_start = time.time()
        for step in range(total_steps):
            # 执行物理步进（可能包含多个子步）
            for _ in range(self.config.physics_substeps):
                backend.step_once()

            sim_time = step * dt
            result.steps_completed += 1

            if callback:
                callback(worker_id, scene_id, step, sim_time)

            # 收集指标（每100步采样一次）
            if step % 100 == 0 and backend.backend:
                try:
                    stats = backend.backend.get_stats()
                    result.metrics[f"step_{step}"] = {
                        "real_time_factor": stats.real_time_factor,
                        "step_time_ms": stats.step_time_ms,
                    }
                except Exception:
                    pass

        # 收集后端统计
        try:
            if backend.backend:
                stats = backend.backend.get_stats()
                result.metrics["final"] = {
                    "total_time": stats.total_time,
                    "total_steps": stats.total_steps,
                    "real_time_factor": stats.real_time_factor,
                }
        except Exception:
            pass

        return result

    def _run_simulated(self, worker_id: int, scene_id: int, scene_config: Dict,
                        total_steps: int, dt: float, wall_start: float,
                        callback: Optional[Callable], result: SimWorkerResult) -> SimWorkerResult:
        """使用模拟模式运行（无真实后端时的降级方案）。"""
        for step in range(total_steps):
            sim_time = step * dt * self.config.speedup_factor

            if callback:
                callback(worker_id, scene_id, step, sim_time)

            result.steps_completed += 1

            # 自适应休眠以控制加速比
            target_wall_time = sim_time / self.config.speedup_factor
            elapsed = time.time() - wall_start
            if elapsed < target_wall_time and not self.config.headless:
                time.sleep(target_wall_time - elapsed)

        result.metrics["mode"] = "simulated"
        return result

    def run_single(self, scene_config: Dict, total_steps: int,
                   step_callback: Optional[Callable] = None) -> SimWorkerResult:
        """运行单个场景（便捷方法）。"""
        results = self.run_batch([scene_config], total_steps, step_callback)
        return results[0] if results else SimWorkerResult(
            worker_id=0, scene_id=0,
            steps_completed=0, wall_time_sec=0, sim_time_sec=0,
            effective_speedup=0, errors=["No results"],
        )

    def get_summary(self) -> Dict:
        """获取批量仿真摘要。"""
        if not self._results:
            return {"total_scenes": 0, "total_steps": 0, "errors": ["No results"]}

        total_steps = sum(r.steps_completed for r in self._results)
        total_wall = sum(r.wall_time_sec for r in self._results)
        total_sim = sum(r.sim_time_sec for r in self._results)
        all_errors = [e for r in self._results for e in r.errors]
        modes = [r.metrics.get("mode", "backend") for r in self._results]

        return {
            "total_scenes": len(self._results),
            "total_steps": total_steps,
            "total_wall_time_sec": total_wall,
            "total_sim_time_sec": total_sim,
            "overall_speedup": total_sim / max(total_wall, 1e-6),
            "has_real_backend": self._has_real_backend,
            "modes": modes,
            "errors": all_errors,
        }

    def is_using_real_backend(self) -> bool:
        """检查是否有真实后端在工作。"""
        return self._has_real_backend
