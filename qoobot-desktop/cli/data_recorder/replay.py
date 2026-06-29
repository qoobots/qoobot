"""回放调试引擎 — 记录/回放传感器+控制数据，离线复现问题。

支持:
  - 传感器数据回放
  - 控制数据回放
  - 逐帧步进
  - 时间缩放 (慢放/快放)
  - 条件断点
  - 数据查询
"""

import time
import threading
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional, Set, Tuple
from collections import defaultdict

from . import DataReader, DataType, DataFrame, DataRecorder, EpisodeMetadata


# ---------------------------------------------------------------------------
# 回放引擎
# ---------------------------------------------------------------------------

class PlaybackState(Enum):
    STOPPED = auto()
    PLAYING = auto()
    PAUSED = auto()
    STEPPING = auto()       # 单步执行
    SEEKING = auto()        # 跳转中


@dataclass
class PlaybackPosition:
    """回放位置"""
    frame_index: int = 0
    timestamp: float = 0.0
    frame: Optional[DataFrame] = None


@dataclass
class Breakpoint:
    """条件断点"""
    id: str
    condition: str = ""             # Python 表达式: "frame.dtype == DataType.MARKER"
    enabled: bool = True
    hit_count: int = 0
    max_hits: int = 0               # 0 = 无限
    type_filter: Optional[DataType] = None
    marker_label: Optional[str] = None
    time_range: Optional[Tuple[float, float]] = None

    def evaluate(self, frame: DataFrame, context: Dict) -> bool:
        """评估断点条件"""
        if not self.enabled:
            return False

        if self.type_filter and frame.dtype != self.type_filter:
            return False

        if self.marker_label and frame.dtype == DataType.MARKER:
            import json
            marker = json.loads(frame.payload)
            if marker.get("label") != self.marker_label:
                return False

        if self.time_range:
            t_min, t_max = self.time_range
            if not (t_min <= frame.timestamp <= t_max):
                return False

        if self.max_hits > 0 and self.hit_count >= self.max_hits:
            return False

        if self.condition:
            try:
                ctx = {**context, "frame": frame}
                result = eval(self.condition, {"__builtins__": {}}, ctx)
                return bool(result)
            except Exception:
                return False

        return True


class PlaybackEngine:
    """回放引擎 — 控制 .qoodata 回放"""

    def __init__(self, data_path: Path):
        self.data_path = Path(data_path)
        self.reader = DataReader(data_path)
        self._state = PlaybackState.STOPPED
        self._position = PlaybackPosition()
        self._speed: float = 1.0
        self._loop: bool = False
        self._breakpoints: Dict[str, Breakpoint] = {}
        self._callbacks: Dict[str, List[Callable]] = defaultdict(list)
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        # 帧缓存 (预加载所有帧索引)
        self._frame_index: List[Tuple[int, DataType, float]] = []  # (offset, dtype, timestamp)
        self._frame_data: Optional[bytes] = None
        self._build_index()

    def _build_index(self):
        """构建帧索引以支持随机访问"""
        self.reader.open()
        self._frame_data = self.reader.data_path.read_bytes()
        offset = 0

        # 跳过文件头
        if self._frame_data[:11] != b"QDATAFILE\x01":
            raise ValueError("Invalid data file")
        offset += 11
        header_len = struct.unpack(">I", self._frame_data[offset:offset + 4])[0]
        offset += 4 + header_len

        from . import FRAME_HEADER_SIZE, FRAME_HEADER_FMT, FRAME_MAGIC
        import struct as _struct

        while offset + FRAME_HEADER_SIZE <= len(self._frame_data):
            magic, dtype_val, size, ts, seq = _struct.unpack_from(
                FRAME_HEADER_FMT, self._frame_data, offset
            )
            if magic != FRAME_MAGIC:
                break

            self._frame_index.append((offset, DataType(dtype_val), ts))
            offset += FRAME_HEADER_SIZE + size

    @property
    def state(self) -> PlaybackState:
        return self._state

    @property
    def position(self) -> PlaybackPosition:
        return self._position

    @property
    def total_frames(self) -> int:
        return len(self._frame_index)

    @property
    def duration(self) -> float:
        if not self._frame_index:
            return 0.0
        return self._frame_index[-1][2]

    # ---- 播放控制 ----

    def play(self, speed: float = 1.0):
        """开始/恢复回放"""
        self._speed = speed
        if self._state == PlaybackState.PAUSED:
            self._state = PlaybackState.PLAYING
            return

        self._state = PlaybackState.PLAYING
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._playback_loop, daemon=True)
        self._thread.start()

    def pause(self):
        """暂停回放"""
        self._state = PlaybackState.PAUSED

    def stop(self):
        """停止回放"""
        self._state = PlaybackState.STOPPED
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2)

    def step_forward(self, n: int = 1):
        """前进 n 帧"""
        self._state = PlaybackState.STEPPING
        for _ in range(n):
            if self._position.frame_index >= self.total_frames:
                if self._loop:
                    self._position.frame_index = 0
                else:
                    break
            self._advance_one_frame()

    def step_backward(self, n: int = 1):
        """后退 n 帧"""
        self._state = PlaybackState.STEPPING
        self._position.frame_index = max(0, self._position.frame_index - n)
        self._load_frame_at(self._position.frame_index)

    def seek(self, frame_index: Optional[int] = None, timestamp: Optional[float] = None):
        """跳转到指定位置"""
        self._state = PlaybackState.SEEKING

        if frame_index is not None:
            self._position.frame_index = max(0, min(frame_index, self.total_frames - 1))
        elif timestamp is not None:
            # 二分查找最接近的时间戳
            lo, hi = 0, self.total_frames - 1
            while lo < hi:
                mid = (lo + hi) // 2
                if self._frame_index[mid][2] < timestamp:
                    lo = mid + 1
                else:
                    hi = mid
            self._position.frame_index = lo

        self._load_frame_at(self._position.frame_index)

    def set_speed(self, speed: float):
        """设置播放速度 (1.0=正常, 0.5=半速, 2.0=双倍速)"""
        self._speed = max(0.01, speed)

    def set_loop(self, loop: bool):
        self._loop = loop

    # ---- 断点 ----

    def add_breakpoint(self, bp: Breakpoint) -> str:
        self._breakpoints[bp.id] = bp
        return bp.id

    def remove_breakpoint(self, bp_id: str):
        self._breakpoints.pop(bp_id, None)

    def list_breakpoints(self) -> List[Breakpoint]:
        return list(self._breakpoints.values())

    # ---- 回调 ----

    def on(self, event: str, callback: Callable):
        """注册事件回调"""
        self._callbacks[event].append(callback)

    def off(self, event: str, callback: Callable):
        if callback in self._callbacks[event]:
            self._callbacks[event].remove(callback)

    def _emit(self, event: str, **kwargs):
        for cb in self._callbacks.get(event, []):
            try:
                cb(**kwargs)
            except Exception as e:
                print(f"Callback error [{event}]: {e}")

    # ---- 内部 ----

    def _playback_loop(self):
        """回放主循环"""
        while not self._stop_event.is_set():
            if self._state != PlaybackState.PLAYING:
                time.sleep(0.01)
                continue

            if self._position.frame_index >= self.total_frames:
                if self._loop:
                    self._position.frame_index = 0
                else:
                    self._state = PlaybackState.STOPPED
                    self._emit("playback_end")
                    break

            # 检查断点
            _, dtype, ts = self._frame_index[self._position.frame_index]
            frame = self._position.frame
            if frame:
                for bp in self._breakpoints.values():
                    if bp.evaluate(frame, {"timestamp": ts, "dtype": dtype}):
                        bp.hit_count += 1
                        self._state = PlaybackState.PAUSED
                        self._emit("breakpoint_hit", breakpoint=bp, frame=frame)
                        break

            if self._state != PlaybackState.PLAYING:
                continue

            self._advance_one_frame()

            # 根据速度计算等待时间
            if self._position.frame_index < self.total_frames:
                next_ts = self._frame_index[self._position.frame_index][2]
                sleep_time = (next_ts - self._position.timestamp) / self._speed
                if sleep_time > 0:
                    self._stop_event.wait(timeout=min(sleep_time, 0.1))

    def _advance_one_frame(self):
        """前进一帧"""
        if self._position.frame_index < self.total_frames:
            self._load_frame_at(self._position.frame_index)
            self._emit("frame", frame=self._position.frame, position=self._position)
            self._position.frame_index += 1

    def _load_frame_at(self, index: int):
        """加载指定索引的帧"""
        from . import DataFrame as DF, FRAME_HEADER_SIZE, FRAME_HEADER_FMT, FRAME_MAGIC
        import struct as _struct

        offset, dtype, ts = self._frame_index[index]
        magic, _, size, _, seq = _struct.unpack_from(
            FRAME_HEADER_FMT, self._frame_data, offset
        )
        payload_offset = offset + FRAME_HEADER_SIZE
        payload = self._frame_data[payload_offset:payload_offset + size]

        self._position = PlaybackPosition(
            frame_index=index,
            timestamp=ts,
            frame=DF(dtype=dtype, timestamp=ts, seq=seq, payload=payload),
        )

    def close(self):
        self.stop()
        self.reader.close()


# ---------------------------------------------------------------------------
# 回放会话管理器
# ---------------------------------------------------------------------------

class ReplaySession:
    """回放会话 — 管理多次回放、对比分析"""

    def __init__(self, name: str = ""):
        self.name = name
        self.engines: Dict[str, PlaybackEngine] = {}
        self.active_engine: Optional[str] = None

    def load(self, key: str, data_path: Path) -> PlaybackEngine:
        engine = PlaybackEngine(data_path)
        self.engines[key] = engine
        return engine

    def activate(self, key: str):
        if key not in self.engines:
            raise KeyError(f"No engine: {key}")
        self.active_engine = key

    @property
    def active(self) -> Optional[PlaybackEngine]:
        if self.active_engine:
            return self.engines.get(self.active_engine)
        return None

    def compare_stats(self) -> Dict[str, Dict]:
        """对比多个回放的统计信息"""
        result = {}
        for key, engine in self.engines.items():
            result[key] = {
                "total_frames": engine.total_frames,
                "duration": engine.duration,
                "avg_fps": engine.total_frames / max(engine.duration, 0.001),
            }
        return result

    def close_all(self):
        for engine in self.engines.values():
            engine.close()


# ---------------------------------------------------------------------------
# 条件断点工厂
# ---------------------------------------------------------------------------

class BreakpointFactory:
    """断点工厂 — 常用断点模板"""

    @staticmethod
    def at_marker(label: str, bp_id: Optional[str] = None) -> Breakpoint:
        return Breakpoint(
            id=bp_id or f"marker:{label}",
            marker_label=label,
        )

    @staticmethod
    def at_frame_type(dtype: DataType, bp_id: Optional[str] = None) -> Breakpoint:
        return Breakpoint(
            id=bp_id or f"type:{dtype.name}",
            type_filter=dtype,
        )

    @staticmethod
    def at_time(timestamp: float, bp_id: Optional[str] = None) -> Breakpoint:
        return Breakpoint(
            id=bp_id or f"time:{timestamp:.2f}",
            time_range=(timestamp, timestamp + 0.01),
        )

    @staticmethod
    def at_condition(condition: str, bp_id: Optional[str] = None) -> Breakpoint:
        return Breakpoint(
            id=bp_id or f"cond:{condition[:20]}",
            condition=condition,
        )

    @staticmethod
    def at_frame_index(index: int, bp_id: Optional[str] = None) -> Breakpoint:
        return Breakpoint(
            id=bp_id or f"frame:{index}",
            condition=f"frame.seq == {index}",
        )
