"""调试与诊断模块。

提供实时日志流、传感器数据可视化、3D 场景可视化、
变量监控和性能剖析功能。
"""

from __future__ import annotations

import json
import logging
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

import numpy as np

logger = logging.getLogger(__name__)


# ── 日志流 ─────────────────────────────────────────────

class LogLevel(Enum):
    DEBUG = 0
    INFO = 1
    WARN = 2
    ERROR = 3
    FATAL = 4


@dataclass
class LogEntry:
    """结构化日志条目。"""
    timestamp: float
    level: LogLevel
    message: str
    source: str = ""
    context: dict[str, Any] = field(default_factory=dict)


class LogStream:
    """实时日志流管理器。

    支持分级过滤、搜索、历史回溯和时间线视图。
    """

    def __init__(self, max_entries: int = 10000):
        self._buffer: deque[LogEntry] = deque(maxlen=max_entries)
        self._subscribers: list[Callable[[LogEntry], None]] = []
        self._level_filter: Optional[LogLevel] = None
        self._source_filter: Optional[str] = None
        self._search_text: Optional[str] = None

    def emit(
        self, level: LogLevel, message: str,
        source: str = "", **context
    ) -> None:
        """发送一条日志。"""
        entry = LogEntry(
            timestamp=time.time(),
            level=level,
            message=message,
            source=source,
            context=context,
        )
        self._buffer.append(entry)

        # 通知订阅者
        if self._should_emit(entry):
            for cb in self._subscribers:
                try:
                    cb(entry)
                except Exception:
                    pass

    def subscribe(self, callback: Callable[[LogEntry], None]) -> None:
        """订阅日志流。"""
        self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[LogEntry], None]) -> None:
        """取消订阅。"""
        if callback in self._subscribers:
            self._subscribers.remove(callback)

    def set_filter(
        self,
        level: Optional[LogLevel] = None,
        source: Optional[str] = None,
        search: Optional[str] = None,
    ) -> None:
        """设置过滤条件。"""
        self._level_filter = level
        self._source_filter = source
        self._search_text = search

    def get_history(
        self,
        level: Optional[LogLevel] = None,
        source: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 100,
    ) -> list[LogEntry]:
        """获取历史日志。"""
        results = []
        for entry in self._buffer:
            if level and entry.level.value < level.value:
                continue
            if source and source not in entry.source:
                continue
            if search and search.lower() not in entry.message.lower():
                continue
            results.append(entry)
        return results[-limit:]

    def clear(self) -> None:
        """清空日志缓冲区。"""
        self._buffer.clear()

    def to_json_lines(self) -> str:
        """导出为 JSON Lines 格式。"""
        lines = []
        for entry in self._buffer:
            lines.append(json.dumps({
                "timestamp": entry.timestamp,
                "level": entry.level.name,
                "message": entry.message,
                "source": entry.source,
                "context": entry.context,
            }))
        return "\n".join(lines)

    def _should_emit(self, entry: LogEntry) -> bool:
        """检查是否应该发送给订阅者。"""
        if self._level_filter and entry.level.value < self._level_filter.value:
            return False
        if self._source_filter and self._source_filter not in entry.source:
            return False
        if self._search_text and self._search_text.lower() not in entry.message.lower():
            return False
        return True


# ── 传感器数据可视化 ───────────────────────────────────

@dataclass
class SensorFrame:
    """传感器数据帧（带时间戳）。"""
    timestamp: float
    data: Any
    metadata: dict[str, Any] = field(default_factory=dict)


class SensorVisualizer:
    """传感器数据可视化器。

    管理传感器数据缓冲区，提供时序查询和统计。
    """

    def __init__(self, max_frames: int = 1000):
        self._buffers: dict[str, deque[SensorFrame]] = {}
        self._max_frames = max_frames
        self._subscribers: dict[str, list[Callable]] = {}

    def push(self, sensor_name: str, data: Any, metadata: dict = None) -> None:
        """推送一帧传感器数据。"""
        if sensor_name not in self._buffers:
            self._buffers[sensor_name] = deque(maxlen=self._max_frames)

        frame = SensorFrame(
            timestamp=time.time(),
            data=data,
            metadata=metadata or {},
        )
        self._buffers[sensor_name].append(frame)

        # 通知订阅者
        for cb in self._subscribers.get(sensor_name, []):
            try:
                cb(frame)
            except Exception:
                pass

    def subscribe(self, sensor_name: str, callback: Callable) -> None:
        """订阅传感器数据更新。"""
        if sensor_name not in self._subscribers:
            self._subscribers[sensor_name] = []
        self._subscribers[sensor_name].append(callback)

    def get_latest(self, sensor_name: str) -> Optional[SensorFrame]:
        """获取最新数据帧。"""
        buf = self._buffers.get(sensor_name)
        if buf:
            return buf[-1]
        return None

    def get_history(
        self, sensor_name: str, limit: int = 100
    ) -> list[SensorFrame]:
        """获取历史数据帧。"""
        buf = self._buffers.get(sensor_name)
        if buf:
            return list(buf)[-limit:]
        return []

    def get_stats(self, sensor_name: str) -> dict[str, Any]:
        """获取传感器数据统计。"""
        buf = self._buffers.get(sensor_name)
        if not buf:
            return {"count": 0}

        data_list = [f.data for f in buf if isinstance(f.data, np.ndarray)]
        if not data_list:
            return {"count": len(buf)}

        stacked = np.stack(data_list)
        return {
            "count": len(buf),
            "shape": stacked.shape,
            "min": float(stacked.min()),
            "max": float(stacked.max()),
            "mean": float(stacked.mean()),
            "std": float(stacked.std()),
            "rate_hz": len(buf) / (buf[-1].timestamp - buf[0].timestamp)
            if len(buf) > 1 and (buf[-1].timestamp - buf[0].timestamp) > 0
            else 0,
        }


# ── 3D 场景可视化 ──────────────────────────────────────

@dataclass
class Pose3D:
    """3D 位姿。"""
    position: tuple[float, float, float] = (0.0, 0.0, 0.0)
    rotation: tuple[float, float, float, float] = (1.0, 0.0, 0.0, 0.0)  # quaternion


@dataclass
class JointState:
    """关节状态。"""
    name: str
    position: float = 0.0
    velocity: float = 0.0
    torque: float = 0.0


@dataclass
class RobotState:
    """机器人完整状态。"""
    name: str
    base_pose: Pose3D = field(default_factory=Pose3D)
    joints: dict[str, JointState] = field(default_factory=dict)
    timestamp: float = 0.0


class SceneVisualizer:
    """3D 场景状态管理器。

    维护场景中所有物体的位姿和机器人状态，
    供前端 3D 渲染使用。
    """

    def __init__(self):
        self._robot_states: dict[str, RobotState] = {}
        self._object_poses: dict[str, Pose3D] = {}
        self._point_clouds: dict[str, np.ndarray] = {}
        self._update_callbacks: list[Callable] = []
        self._update_rate_hz: float = 30.0
        self._last_update: float = 0.0
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def update_robot(self, name: str, state: RobotState) -> None:
        """更新机器人状态。"""
        self._robot_states[name] = state

    def update_object(self, name: str, pose: Pose3D) -> None:
        """更新物体位姿。"""
        self._object_poses[name] = pose

    def update_point_cloud(self, name: str, points: np.ndarray) -> None:
        """更新点云数据。"""
        self._point_clouds[name] = points

    def get_scene_snapshot(self) -> dict[str, Any]:
        """获取场景完整快照。"""
        return {
            "timestamp": time.time(),
            "robots": {
                name: {
                    "base_pose": {
                        "position": list(state.base_pose.position),
                        "rotation": list(state.base_pose.rotation),
                    },
                    "joints": {
                        jn: {
                            "position": js.position,
                            "velocity": js.velocity,
                            "torque": js.torque,
                        }
                        for jn, js in state.joints.items()
                    },
                    "timestamp": state.timestamp,
                }
                for name, state in self._robot_states.items()
            },
            "objects": {
                name: {
                    "position": list(pose.position),
                    "rotation": list(pose.rotation),
                }
                for name, pose in self._object_poses.items()
            },
            "point_clouds": {
                name: {
                    "count": len(pc),
                    "bounds": {
                        "min": list(pc.min(axis=0)),
                        "max": list(pc.max(axis=0)),
                    },
                }
                for name, pc in self._point_clouds.items()
            },
        }

    def on_update(self, callback: Callable) -> None:
        """注册场景更新回调。"""
        self._update_callbacks.append(callback)

    def start_streaming(self, rate_hz: float = 30.0) -> None:
        """开始周期性推送场景状态。"""
        self._update_rate_hz = rate_hz
        self._running = True
        self._thread = threading.Thread(
            target=self._stream_loop, daemon=True, name="scene-viz"
        )
        self._thread.start()

    def stop_streaming(self) -> None:
        """停止推送。"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)

    def _stream_loop(self) -> None:
        """场景状态推送循环。"""
        interval = 1.0 / self._update_rate_hz
        while self._running:
            now = time.time()
            if now - self._last_update >= interval:
                snapshot = self.get_scene_snapshot()
                for cb in self._update_callbacks:
                    try:
                        cb(snapshot)
                    except Exception:
                        pass
                self._last_update = now
            time.sleep(0.001)


# ── 变量监控 ───────────────────────────────────────────

class VariableMonitor:
    """运行时变量监控器。

    跟踪指定变量的值变化，支持历史记录和阈值告警。
    """

    def __init__(self, max_history: int = 1000):
        self._variables: dict[str, deque[tuple[float, Any]]] = {}
        self._max_history = max_history
        self._thresholds: dict[str, tuple[float, float]] = {}
        self._alert_callbacks: list[Callable] = []

    def track(self, name: str, value: Any) -> None:
        """记录变量值。"""
        if name not in self._variables:
            self._variables[name] = deque(maxlen=self._max_history)
        self._variables[name].append((time.time(), value))

        # 阈值检查
        self._check_threshold(name, value)

    def set_threshold(
        self, name: str, low: Optional[float] = None, high: Optional[float] = None
    ) -> None:
        """设置变量阈值。"""
        self._thresholds[name] = (low, high)

    def get_history(self, name: str, limit: int = 100) -> list[tuple[float, Any]]:
        """获取变量历史。"""
        buf = self._variables.get(name)
        if buf:
            return list(buf)[-limit:]
        return []

    def get_latest(self, name: str) -> Optional[Any]:
        """获取最新值。"""
        buf = self._variables.get(name)
        if buf:
            return buf[-1][1]
        return None

    def on_alert(self, callback: Callable) -> None:
        """注册告警回调。"""
        self._alert_callbacks.append(callback)

    def list_variables(self) -> list[str]:
        """列出所有跟踪变量。"""
        return list(self._variables.keys())

    def _check_threshold(self, name: str, value: Any) -> None:
        """检查变量是否超过阈值。"""
        if name not in self._thresholds:
            return
        low, high = self._thresholds[name]
        try:
            fval = float(value)
            if low is not None and fval < low:
                self._alert(name, fval, "low", low)
            if high is not None and fval > high:
                self._alert(name, fval, "high", high)
        except (TypeError, ValueError):
            pass

    def _alert(
        self, name: str, value: float, direction: str, threshold: float
    ) -> None:
        """触发告警。"""
        msg = f"[ALERT] {name}={value:.4f} 超过{direction}阈值 {threshold:.4f}"
        logger.warning(msg)
        for cb in self._alert_callbacks:
            try:
                cb(name, value, direction, threshold)
            except Exception:
                pass


# ── 性能剖析 ───────────────────────────────────────────

@dataclass
class LatencyRecord:
    """延迟记录。"""
    stage: str          # 阶段名称: perception / planning / control
    start_time: float
    end_time: float
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def duration_ms(self) -> float:
        return (self.end_time - self.start_time) * 1000


class Profiler:
    """端到端性能剖析器。

    跟踪感知→规划→控制的完整链路延迟。
    """

    def __init__(self, max_records: int = 10000):
        self._records: deque[LatencyRecord] = deque(maxlen=max_records)
        self._current_traces: dict[str, float] = {}  # trace_id -> start_time

    def start_trace(self, trace_id: str) -> None:
        """开始追踪一个阶段。"""
        self._current_traces[trace_id] = time.time()

    def end_trace(
        self, trace_id: str, stage: str = "", **metadata
    ) -> Optional[LatencyRecord]:
        """结束追踪一个阶段。"""
        start = self._current_traces.pop(trace_id, None)
        if start is None:
            return None

        record = LatencyRecord(
            stage=stage or trace_id,
            start_time=start,
            end_time=time.time(),
            metadata=metadata,
        )
        self._records.append(record)
        return record

    def get_stats(self) -> dict[str, Any]:
        """获取延迟统计。"""
        if not self._records:
            return {}

        by_stage: dict[str, list[float]] = {}
        for r in self._records:
            if r.stage not in by_stage:
                by_stage[r.stage] = []
            by_stage[r.stage].append(r.duration_ms)

        stats = {}
        for stage, durations in by_stage.items():
            arr = np.array(durations)
            stats[stage] = {
                "count": len(arr),
                "mean_ms": float(arr.mean()),
                "std_ms": float(arr.std()),
                "min_ms": float(arr.min()),
                "max_ms": float(arr.max()),
                "p50_ms": float(np.percentile(arr, 50)),
                "p95_ms": float(np.percentile(arr, 95)),
                "p99_ms": float(np.percentile(arr, 99)),
            }

        return stats

    def get_recent(self, limit: int = 100) -> list[LatencyRecord]:
        """获取最近的延迟记录。"""
        return list(self._records)[-limit:]

    def clear(self) -> None:
        """清空记录。"""
        self._records.clear()
        self._current_traces.clear()
