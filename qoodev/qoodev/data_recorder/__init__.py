"""示教录制 — 遥操作与技能演示的数据录制系统。

.qoodata 格式: 高效的二进制记录格式，存储传感器、控制、状态数据。
支持:
  - 遥操作录制 (手柄/VR/主从)
  - 技能演示录制 (人工执行→训练数据)
  - 数据标注管理
  - 多模态数据同步
"""

import json
import struct
import time
import zlib
import threading
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple, Union
import io


# ---------------------------------------------------------------------------
# .qoodata 二进制格式定义
# ---------------------------------------------------------------------------

class DataType(Enum):
    """数据帧类型"""
    # 传感器
    RGB_IMAGE = 0x01
    DEPTH_IMAGE = 0x02
    LIDAR_SCAN = 0x03
    IMU = 0x04
    JOINT_STATE = 0x05
    # 控制
    JOINT_COMMAND = 0x10
    EE_POSE_COMMAND = 0x11
    GRIPPER_COMMAND = 0x12
    # 元数据
    MARKER = 0x20         # 标注标记
    EPISODE_BOUNDARY = 0x21  # Episode 边界
    TEXT_LOG = 0x22
    # 自定义
    CUSTOM = 0xF0

    def __repr__(self):
        return f"DataType.{self.name}"


# 二进制帧格式:
# ┌──────────┬──────────┬──────────┬───────────┬───────────┬──────────┐
# │ Magic(4) │ Type(2)  │ Size(4)  │ Timestamp │ Seq(4)   │ Payload  │
# │ "QDATA"  │ DataType │ payload  │ (8) float │          │ variable │
# └──────────┴──────────┴──────────┴───────────┴───────────┴──────────┘
FRAME_HEADER_FMT = ">4s H I d I"  # magic, type, size, timestamp, seq
FRAME_HEADER_SIZE = struct.calcsize(FRAME_HEADER_FMT)
FRAME_MAGIC = b"QDAT"


@dataclass
class DataFrame:
    """单帧数据"""
    dtype: DataType
    timestamp: float
    seq: int
    payload: bytes

    def encode(self) -> bytes:
        header = struct.pack(
            FRAME_HEADER_FMT,
            FRAME_MAGIC,
            self.dtype.value,
            len(self.payload),
            self.timestamp,
            self.seq,
        )
        return header + self.payload

    @classmethod
    def decode(cls, data: bytes, offset: int = 0) -> Tuple["DataFrame", int]:
        magic, dtype_val, size, ts, seq = struct.unpack_from(
            FRAME_HEADER_FMT, data, offset
        )
        if magic != FRAME_MAGIC:
            raise ValueError(f"Invalid frame magic: {magic}")

        offset += FRAME_HEADER_SIZE
        payload = data[offset:offset + size]
        offset += size

        return cls(
            dtype=DataType(dtype_val),
            timestamp=ts,
            seq=seq,
            payload=payload,
        ), offset


# ---------------------------------------------------------------------------
# 记录器
# ---------------------------------------------------------------------------

@dataclass
class EpisodeMetadata:
    """Episode 元数据"""
    episode_id: str
    task_name: str = ""
    description: str = ""
    operator: str = ""         # 操作者
    robot_model: str = ""
    scene_name: str = ""
    tags: List[str] = field(default_factory=list)
    start_time: float = 0.0
    end_time: float = 0.0
    frame_count: int = 0
    custom_fields: Dict[str, Any] = field(default_factory=dict)


class DataRecorder:
    """数据记录器 — 线程安全的二进制录制"""

    def __init__(self, output_path: Path, chunk_size: int = 1024 * 1024):
        self.output_path = Path(output_path)
        self.chunk_size = chunk_size
        self._file: Optional[io.BufferedWriter] = None
        self._seq: int = 0
        self._lock = threading.Lock()
        self._start_time: float = 0.0
        self._frame_count: int = 0
        self._chunk_index: int = 0
        self._chunk_written: int = 0
        self._metadata: Optional[EpisodeMetadata] = None
        self._closed: bool = False

    def open(self, metadata: EpisodeMetadata):
        """开始录制"""
        self._metadata = metadata
        self._start_time = time.time()
        self._seq = 0
        self._frame_count = 0
        self._chunk_index = 0

        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self._file = open(self._get_chunk_path(0), "wb")

        # 写入文件头
        header = {
            "format": "qoodata-v1",
            "episode": {
                "id": metadata.episode_id,
                "task": metadata.task_name,
                "description": metadata.description,
                "operator": metadata.operator,
                "robot": metadata.robot_model,
                "scene": metadata.scene_name,
                "tags": metadata.tags,
            },
            "created": datetime.utcnow().isoformat(),
            "chunk_size": self.chunk_size,
        }
        header_json = json.dumps(header, indent=2).encode("utf-8")
        header_len = struct.pack(">I", len(header_json))

        self._file.write(b"QDATAFILE\x01")  # 文件魔数 + 版本
        self._file.write(header_len)
        self._file.write(header_json)

    def _get_chunk_path(self, index: int) -> Path:
        stem = self.output_path.stem
        if index == 0:
            return self.output_path
        return self.output_path.parent / f"{stem}.{index:03d}"

    def record_frame(self, dtype: DataType, payload: bytes):
        """记录一帧数据 (线程安全)"""
        with self._lock:
            if self._closed:
                raise RuntimeError("Recorder is closed")

            ts = time.time()
            frame = DataFrame(
                dtype=dtype,
                timestamp=ts - self._start_time,
                seq=self._seq,
                payload=payload,
            )

            data = frame.encode()
            self._file.write(data)
            self._seq += 1
            self._frame_count += 1
            self._chunk_written += len(data)

            # 分片
            if self._chunk_written >= self.chunk_size:
                self._file.close()
                self._chunk_index += 1
                self._chunk_written = 0
                self._file = open(self._get_chunk_path(self._chunk_index), "wb")

    def record_marker(self, label: str, data: Optional[Dict] = None):
        """记录标注标记"""
        payload = json.dumps({
            "label": label,
            "data": data or {},
            "timestamp": time.time() - self._start_time,
        }).encode("utf-8")
        self.record_frame(DataType.MARKER, payload)

    def record_episode_boundary(self, is_start: bool = True):
        """记录 Episode 边界"""
        payload = struct.pack(">?", is_start)
        self.record_frame(DataType.EPISODE_BOUNDARY, payload)

    def record_text_log(self, level: str, message: str):
        """记录文本日志"""
        payload = json.dumps({"level": level, "message": message}).encode("utf-8")
        self.record_frame(DataType.TEXT_LOG, payload)

    # ---- 传感器便捷方法 ----

    def record_rgb_image(self, image_bytes: bytes, width: int, height: int, encoding: str = "jpeg"):
        header = json.dumps({"w": width, "h": height, "enc": encoding}).encode("utf-8")
        self.record_frame(DataType.RGB_IMAGE, struct.pack(">I", len(header)) + header + image_bytes)

    def record_depth_image(self, depth_bytes: bytes, width: int, height: int):
        header = json.dumps({"w": width, "h": height, "fmt": "uint16"}).encode("utf-8")
        self.record_frame(DataType.DEPTH_IMAGE, struct.pack(">I", len(header)) + header + depth_bytes)

    def record_lidar_scan(self, points: List[Tuple[float, float, float]], intensities: Optional[List[float]] = None):
        data = bytearray()
        data.extend(struct.pack(">I", len(points)))
        for i, (x, y, z) in enumerate(points):
            intensity = intensities[i] if intensities else 0.0
            data.extend(struct.pack(">ffff", x, y, z, intensity))
        self.record_frame(DataType.LIDAR_SCAN, bytes(data))

    def record_imu(self, accel: Tuple[float, float, float], gyro: Tuple[float, float, float]):
        payload = struct.pack(">ffffff", *accel, *gyro)
        self.record_frame(DataType.IMU, payload)

    def record_joint_state(self, names: List[str], positions: List[float], velocities: Optional[List[float]] = None):
        data = json.dumps({
            "names": names,
            "positions": positions,
            "velocities": velocities or [0.0] * len(positions),
        }).encode("utf-8")
        self.record_frame(DataType.JOINT_STATE, data)

    # ---- 控制便捷方法 ----

    def record_joint_command(self, names: List[str], targets: List[float]):
        data = json.dumps({"names": names, "targets": targets}).encode("utf-8")
        self.record_frame(DataType.JOINT_COMMAND, data)

    def record_ee_pose_command(self, position: Tuple[float, float, float], orientation: Tuple[float, float, float, float]):
        payload = struct.pack(">fffffff", *position, *orientation)
        self.record_frame(DataType.EE_POSE_COMMAND, payload)

    def record_gripper_command(self, position: float, force: float = 0.0):
        payload = struct.pack(">ff", position, force)
        self.record_frame(DataType.GRIPPER_COMMAND, payload)

    def close(self):
        """停止录制"""
        with self._lock:
            if self._closed:
                return

            if self._metadata:
                self._metadata.end_time = time.time() - self._start_time
                self._metadata.frame_count = self._frame_count

                # 写入索引
                index = {
                    "episode": {
                        "id": self._metadata.episode_id,
                        "task": self._metadata.task_name,
                        "frame_count": self._frame_count,
                        "duration": self._metadata.end_time,
                        "chunks": self._chunk_index + 1,
                    }
                }
                index_json = json.dumps(index).encode("utf-8")
                index_len = struct.pack(">I", len(index_json))
                self._file.write(b"QDATINDEX\x01")
                self._file.write(index_len)
                self._file.write(index_json)

            self._file.close()
            self._closed = True

            print(f"✅ Recording saved: {self.output_path}")
            print(f"   Frames:  {self._frame_count}")
            print(f"   Duration: {self._metadata.end_time:.2f}s")
            print(f"   Chunks:  {self._chunk_index + 1}")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


# ---------------------------------------------------------------------------
# 读取器 / 回放
# ---------------------------------------------------------------------------

class DataReader:
    """数据读取器 — 流式读取 .qoodata 文件"""

    def __init__(self, data_path: Path):
        self.data_path = Path(data_path)
        self._file: Optional[io.BufferedReader] = None
        self._metadata: Dict = {}
        self._episode_index: Dict = {}

    def open(self):
        self._file = open(self.data_path, "rb")

        # 读取文件头
        magic = self._file.read(11)
        if magic != b"QDATAFILE\x01":
            raise ValueError(f"Invalid file format: {magic}")

        header_len = struct.unpack(">I", self._file.read(4))[0]
        header_json = self._file.read(header_len)
        self._metadata = json.loads(header_json)

    def frames(self) -> Iterator[DataFrame]:
        """迭代所有帧"""
        if self._file is None:
            self.open()

        self._file.seek(0)
        # 跳过文件头
        magic = self._file.read(11)
        header_len = struct.unpack(">I", self._file.read(4))[0]
        self._file.seek(header_len, 1)  # 跳过 header JSON

        while True:
            header_data = self._file.read(FRAME_HEADER_SIZE)
            if len(header_data) < FRAME_HEADER_SIZE:
                # 可能遇到索引尾
                break

            magic, dtype_val, size, ts, seq = struct.unpack(
                FRAME_HEADER_FMT, header_data
            )
            if magic != FRAME_MAGIC:
                # 可能是索引段
                break

            payload = self._file.read(size)
            if len(payload) < size:
                break

            yield DataFrame(
                dtype=DataType(dtype_val),
                timestamp=ts,
                seq=seq,
                payload=payload,
            )

    def frames_by_type(self, dtype: DataType) -> Iterator[DataFrame]:
        """按类型过滤帧"""
        for frame in self.frames():
            if frame.dtype == dtype:
                yield frame

    def markers(self) -> Iterator[Dict]:
        """迭代所有标记"""
        for frame in self.frames_by_type(DataType.MARKER):
            yield json.loads(frame.payload)

    def get_stats(self) -> Dict:
        """获取数据统计"""
        stats = {
            "total_frames": 0,
            "duration": 0.0,
            "by_type": {},
            "markers": [],
        }

        last_ts = 0.0
        for frame in self.frames():
            stats["total_frames"] += 1
            type_name = frame.dtype.name
            stats["by_type"][type_name] = stats["by_type"].get(type_name, 0) + 1

            if frame.timestamp > last_ts:
                last_ts = frame.timestamp

            if frame.dtype == DataType.MARKER:
                stats["markers"].append(json.loads(frame.payload))

        stats["duration"] = last_ts
        stats["avg_fps"] = stats["total_frames"] / max(last_ts, 0.001)

        return stats

    def close(self):
        if self._file:
            self._file.close()

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, *args):
        self.close()


# ---------------------------------------------------------------------------
# 遥操作录制器
# ---------------------------------------------------------------------------

class TeleoperationRecorder:
    """遥操作录制器 — 键盘/手柄/VR/主从操控录制"""

    def __init__(self, recorder: DataRecorder):
        self.recorder = recorder
        self._last_joint_state: Optional[Tuple[List[str], List[float]]] = None
        self._last_ee_pose: Optional[Tuple[Tuple, Tuple]] = None

    def record_joint_command(self, joint_names: List[str], targets: List[float]):
        self.recorder.record_joint_command(joint_names, targets)

    def record_ee_pose(self, pos: Tuple[float, float, float], quat: Tuple[float, float, float, float]):
        self.recorder.record_ee_pose_command(pos, quat)
        self._last_ee_pose = (pos, quat)

    def record_gripper(self, position: float, force: float = 0.0):
        self.recorder.record_gripper_command(position, force)

    def add_marker(self, label: str, **kwargs):
        """添加标注标记 (如 'grasp_start', 'release', 'collision')"""
        self.recorder.record_marker(label, kwargs)

    def start_episode(self, name: str = ""):
        self.recorder.record_episode_boundary(True)
        if name:
            self.recorder.record_marker(f"episode:{name}")

    def end_episode(self):
        self.recorder.record_episode_boundary(False)


# ---------------------------------------------------------------------------
# 演示录制器
# ---------------------------------------------------------------------------

class SkillDemonstrationRecorder:
    """技能演示录制器 — 人工执行→训练数据"""

    def __init__(self, recorder: DataRecorder):
        self.recorder = recorder
        self._success: Optional[bool] = None
        self._score: float = 0.0

    def record_observation(self, rgb: Optional[bytes] = None, depth: Optional[bytes] = None,
                           lidar: Optional[List] = None, imu: Optional[Tuple] = None,
                           joint_state: Optional[Tuple] = None, img_w: int = 640, img_h: int = 480):
        """记录完整观测"""
        if rgb:
            self.recorder.record_rgb_image(rgb, img_w, img_h)
        if depth:
            self.recorder.record_depth_image(depth, img_w, img_h)
        if lidar:
            self.recorder.record_lidar_scan(lidar)
        if imu:
            self.recorder.record_imu(*imu)
        if joint_state:
            names, positions = joint_state
            self.recorder.record_joint_state(names, positions)

    def record_action(self, joint_targets: Optional[Tuple[List[str], List[float]]] = None,
                      ee_pose: Optional[Tuple[Tuple, Tuple]] = None,
                      gripper: Optional[Tuple[float, float]] = None):
        """记录动作"""
        if joint_targets:
            names, targets = joint_targets
            self.recorder.record_joint_command(names, targets)
        if ee_pose:
            self.recorder.record_ee_pose_command(*ee_pose)
        if gripper:
            self.recorder.record_gripper_command(*gripper)

    def mark_success(self, score: float = 1.0):
        self._success = True
        self._score = score
        self.recorder.record_marker("task_success", {"score": score})

    def mark_failure(self, reason: str = ""):
        self._success = False
        self._score = 0.0
        self.recorder.record_marker("task_failure", {"reason": reason})

    def mark_subtask(self, name: str, status: str = "completed"):
        self.recorder.record_marker(f"subtask:{name}", {"status": status})


# ---------------------------------------------------------------------------
# 数据导出
# ---------------------------------------------------------------------------

class DataExporter:
    """数据导出 — 转换为常见格式"""

    @staticmethod
    def to_jsonl(data_path: Path, output_path: Path, include_types: Optional[List[DataType]] = None):
        """导出为 JSONL 格式"""
        reader = DataReader(data_path)
        reader.open()

        with open(output_path, "w", encoding="utf-8") as f:
            for frame in reader.frames():
                if include_types and frame.dtype not in include_types:
                    continue
                entry = {
                    "type": frame.dtype.name,
                    "timestamp": frame.timestamp,
                    "seq": frame.seq,
                }

                if frame.dtype == DataType.MARKER:
                    entry["data"] = json.loads(frame.payload)
                elif frame.dtype == DataType.TEXT_LOG:
                    entry["data"] = json.loads(frame.payload)
                elif frame.dtype in (DataType.RGB_IMAGE, DataType.DEPTH_IMAGE):
                    header_len = struct.unpack(">I", frame.payload[:4])[0]
                    header = json.loads(frame.payload[4:4 + header_len])
                    entry["header"] = header
                    entry["size"] = len(frame.payload) - 4 - header_len
                elif frame.dtype == DataType.IMU:
                    vals = struct.unpack(">ffffff", frame.payload)
                    entry["accel"] = vals[:3]
                    entry["gyro"] = vals[3:]

                f.write(json.dumps(entry) + "\n")

        reader.close()
        print(f"✅ Exported JSONL: {output_path}")

    @staticmethod
    def to_hdf5(data_path: Path, output_path: Path):
        """导出为 HDF5 格式 (需 h5py)"""
        try:
            import h5py
        except ImportError:
            print("❌ h5py required: pip install h5py")
            return

        reader = DataReader(data_path)
        reader.open()

        with h5py.File(output_path, "w") as h5:
            # 按类型分组
            groups: Dict[str, List] = {}
            for frame in reader.frames():
                type_name = frame.dtype.name.lower()
                if type_name not in groups:
                    groups[type_name] = []
                groups[type_name].append((frame.timestamp, frame.payload))

            for type_name, items in groups.items():
                grp = h5.create_group(type_name)
                timestamps = [item[0] for item in items]
                payloads = [item[1] for item in items]
                grp.create_dataset("timestamp", data=timestamps)
                grp.create_dataset("payload", data=payloads, dtype=h5py.vlen_dtype(bytes))

        reader.close()
        print(f"✅ Exported HDF5: {output_path}")
