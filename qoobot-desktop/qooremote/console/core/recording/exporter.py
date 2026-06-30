"""数据格式导出器 — 录制数据到训练格式的转换

支持导出格式：
- .qoorlog: 原生二进制格式
- .jsonl: JSON Lines（人类可读）
- .h5: HDF5（ML 训练）
- .csv: CSV 表格（Excel 兼容）
- .rosbag: ROS 兼容格式（需 rosbag 库）

对应功能 TCH-03（训练数据导出）。
"""

from __future__ import annotations

import csv
import io
import json
import logging
import struct
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

import numpy as np

from console.core.recording.recorder import RecordingFrame, RecordingMetadata, Recorder

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# 导出格式
# ------------------------------------------------------------------

class ExportFormat(Enum):
    """导出格式"""
    JSONL = "jsonl"
    HDF5 = "h5"
    CSV = "csv"
    QOORLOG = "qoorlog"
    ROSBAG = "rosbag"


@dataclass
class ExportOptions:
    """导出选项"""
    format: ExportFormat = ExportFormat.JSONL
    compress: bool = False
    include_metadata: bool = True
    include_images: bool = False
    frame_stride: int = 1             # 每隔 N 帧导出
    joint_filter: Optional[list[str]] = None  # 仅导出指定关节
    time_range: Optional[tuple[float, float]] = None  # (start, end) 时间范围过滤


@dataclass
class ExportResult:
    """导出结果"""
    format: ExportFormat
    data: bytes | str
    frame_count: int
    file_size_bytes: int
    elapsed_ms: float
    metadata: Optional[RecordingMetadata] = None
    warnings: list[str] = field(default_factory=list)


# ------------------------------------------------------------------
# 导出器
# ------------------------------------------------------------------

class Exporter:
    """录制数据多格式导出器"""

    # Qoorlog 二进制格式魔数
    MAGIC = b"QOOR"
    VERSION = 1

    def __init__(self, options: Optional[ExportOptions] = None) -> None:
        self._options = options or ExportOptions()

    def export(self, frames: list[RecordingFrame],
               metadata: Optional[RecordingMetadata] = None,
               options: Optional[ExportOptions] = None) -> ExportResult:
        """导出录制数据

        Args:
            frames: 录制帧列表
            metadata: 录制元信息
            options: 导出选项

        Returns:
            ExportResult 导出结果
        """
        opts = options or self._options
        start = time.time()

        # 帧过滤
        filtered = self._filter_frames(frames, opts)

        if opts.format == ExportFormat.JSONL:
            data = self._to_jsonl(filtered, metadata, opts)
        elif opts.format == ExportFormat.HDF5:
            data = self._to_hdf5_bytes(filtered, metadata, opts)
        elif opts.format == ExportFormat.CSV:
            data = self._to_csv(filtered, metadata, opts)
        elif opts.format == ExportFormat.QOORLOG:
            data = self._to_qoorlog(filtered, metadata, opts)
        elif opts.format == ExportFormat.ROSBAG:
            data = self._to_rosbag(filtered, metadata, opts)
        else:
            raise ValueError(f"Unsupported export format: {opts.format}")

        elapsed = (time.time() - start) * 1000
        return ExportResult(
            format=opts.format,
            data=data,
            frame_count=len(filtered),
            file_size_bytes=len(data) if isinstance(data, (bytes, str)) else 0,
            elapsed_ms=elapsed,
            metadata=metadata,
        )

    # ---- 各格式导出 ----

    def _to_jsonl(self, frames: list[RecordingFrame],
                  metadata: Optional[RecordingMetadata],
                  opts: ExportOptions) -> str:
        """导出 JSONL 格式"""
        lines = []
        if opts.include_metadata and metadata:
            lines.append(json.dumps({"__meta__": metadata.to_dict()}, ensure_ascii=False))
        for f in frames:
            lines.append(json.dumps(f.to_dict(), ensure_ascii=False))
        return "\n".join(lines)

    def _to_hdf5_bytes(self, frames: list[RecordingFrame],
                       metadata: Optional[RecordingMetadata],
                       opts: ExportOptions) -> bytes:
        """导出 HDF5 格式（转 bytes，方便写入文件）"""
        # 在内存中构建 HDF5 兼容的数据结构
        # 实际写 HDF5 需要 h5py 库，这里返回结构化字典的 json 表示
        if not frames:
            return b""

        n = len(frames)
        joint_names = sorted(frames[0].joint_angles.keys()) if frames[0].joint_angles else []

        data = {
            "version": "1.0",
            "format": "hdf5-dict",
            "frame_count": n,
            "channels": {},
        }

        # 时间戳
        data["channels"]["timestamps"] = [f.timestamp for f in frames]
        data["channels"]["frame_indices"] = [f.frame_index for f in frames]

        # 关节角度
        if joint_names:
            data["channels"]["joint_names"] = joint_names
            data["channels"]["joint_angles"] = [
                [f.joint_angles.get(name, 0.0) for name in joint_names]
                for f in frames
            ]

        # 末端位姿
        ee_poses = [f.end_effector_pose for f in frames if f.end_effector_pose]
        if ee_poses:
            data["channels"]["end_effector_poses"] = ee_poses

        # IMU
        imu_data = [f.imu for f in frames if f.imu]
        if imu_data:
            data["channels"]["imu"] = imu_data

        if metadata and opts.include_metadata:
            data["metadata"] = metadata.to_dict()

        return json.dumps(data, ensure_ascii=False).encode("utf-8")

    def _to_csv(self, frames: list[RecordingFrame],
                metadata: Optional[RecordingMetadata],
                opts: ExportOptions) -> str:
        """导出 CSV 格式"""
        if not frames:
            return ""

        # 收集所有列
        columns = ["frame_index", "timestamp"]
        joint_names = sorted(frames[0].joint_angles.keys()) if frames[0].joint_angles else []
        if joint_names:
            for name in joint_names:
                columns.append(f"joint_{name}")

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=columns)
        writer.writeheader()

        for f in frames:
            row = {"frame_index": f.frame_index, "timestamp": f.timestamp}
            for name in joint_names:
                row[f"joint_{name}"] = f.joint_angles.get(name, "")
            writer.writerow(row)

        return output.getvalue()

    def _to_qoorlog(self, frames: list[RecordingFrame],
                    metadata: Optional[RecordingMetadata],
                    opts: ExportOptions) -> bytes:
        """导出 QooBot 原生二进制格式 .qoorlog

        文件结构:
        ┌─────────────────┐
        │  Header (64B)   │  Magic(4) | Version(4) | FrameCount(8) | ... | MetadataLen(4)
        ├─────────────────┤
        │  JSON Metadata  │  可变长，UTF-8
        ├─────────────────┤
        │  Frame 0        │  Timestamp(8) | Index(4) | NumJoints(2) | JointData...
        │  Frame 1        │  ...
        │  ...            │
        └─────────────────┘
        """
        header = bytearray(64)
        struct.pack_into("4s I Q", header, 0, self.MAGIC, self.VERSION, len(frames))

        meta_json = json.dumps(metadata.to_dict() if metadata else {}).encode("utf-8")
        struct.pack_into("I", header, 52, len(meta_json))

        buf = io.BytesIO()
        buf.write(bytes(header))
        buf.write(meta_json)

        for f in frames:
            # 帧头: timestamp(8) + index(4) + num_joints(2)
            joints = f.joint_angles
            buf.write(struct.pack("d I H", f.timestamp, f.frame_index, len(joints)))
            for name, angle in sorted(joints.items()):
                name_bytes = name.encode("utf-8")
                buf.write(struct.pack("B", len(name_bytes)))
                buf.write(name_bytes)
                buf.write(struct.pack("f", angle))

        return buf.getvalue()

    def _to_rosbag(self, frames: list[RecordingFrame],
                   metadata: Optional[RecordingMetadata],
                   opts: ExportOptions) -> bytes:
        """导出 ROS Bag 兼容格式"""
        # ROS Bag 格式较复杂，此处导出为简化版（兼容 rosbag 库的 Python API）
        data = {
            "format": "rosbag-compat",
            "version": "2.0",
            "metadata": metadata.to_dict() if metadata else {},
            "topics": {
                "/joint_states": {
                    "type": "sensor_msgs/JointState",
                    "messages": [],
                }
            },
        }

        for f in frames:
            msg = {
                "header": {"stamp": {"secs": int(f.timestamp), "nsecs": int((f.timestamp % 1) * 1e9)}},
                "name": list(f.joint_angles.keys()),
                "position": [f.joint_angles.get(n, 0.0) for n in sorted(f.joint_angles)],
                "velocity": [f.joint_velocities.get(n, 0.0) for n in sorted(f.joint_velocities)],
                "effort": [f.joint_torques.get(n, 0.0) for n in sorted(f.joint_torques)],
            }
            data["topics"]["/joint_states"]["messages"].append(msg)

        return json.dumps(data, indent=2).encode("utf-8")

    # ---- 过滤器 ----

    def _filter_frames(self, frames: list[RecordingFrame],
                       opts: ExportOptions) -> list[RecordingFrame]:
        """应用过滤规则"""
        result = []

        for i, f in enumerate(frames):
            # 帧步幅
            if i % opts.frame_stride != 0:
                continue

            # 时间范围
            if opts.time_range:
                t_min, t_max = opts.time_range
                if f.timestamp < t_min or f.timestamp > t_max:
                    continue

            # 关节过滤
            if opts.joint_filter:
                f = RecordingFrame(
                    timestamp=f.timestamp,
                    frame_index=f.frame_index,
                    joint_angles={k: v for k, v in f.joint_angles.items()
                                  if k in opts.joint_filter},
                    joint_velocities={k: v for k, v in f.joint_velocities.items()
                                      if k in opts.joint_filter},
                    joint_torques={k: v for k, v in f.joint_torques.items()
                                   if k in opts.joint_filter},
                    end_effector_pose=f.end_effector_pose,
                    imu=f.imu,
                    force_sensors=f.force_sensors,
                    video_timestamp=f.video_timestamp,
                    markers=f.markers,
                )

            result.append(f)

        return result


# ------------------------------------------------------------------
# 便捷导出函数
# ------------------------------------------------------------------

def export_recording(recorder: Recorder, fmt: ExportFormat,
                     options: Optional[ExportOptions] = None) -> ExportResult:
    """从 Recorder 导出录制数据

    便捷函数，组合 Recorder 和 Exporter。

    Args:
        recorder: 录制器实例
        fmt: 导出格式
        options: 导出选项

    Returns:
        ExportResult
    """
    exporter = Exporter(options)
    return exporter.export(
        frames=recorder.get_frames(),
        metadata=recorder.metadata,
        options=options,
    )
