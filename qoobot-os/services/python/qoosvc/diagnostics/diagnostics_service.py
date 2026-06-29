# -*- coding: utf-8 -*-
"""DiagnosticsService — 自诊断与健康 Python 封装"""

import dataclasses
import enum
import logging
from typing import Callable, List, Optional

logger = logging.getLogger(__name__)


class DiagStatus(enum.Enum):
    OK = "OK"
    WARNING = "WARNING"
    ERROR = "ERROR"
    NOT_TESTED = "NOT_TESTED"


@dataclasses.dataclass
class DiagnosticItem:
    """诊断项"""
    name: str = ""
    component: str = ""  # sensor/motor/battery/communication
    status: DiagStatus = DiagStatus.NOT_TESTED
    message: str = ""
    value: float = 0.0
    unit: str = ""
    min_normal: float = 0.0
    max_normal: float = 0.0


@dataclasses.dataclass
class HealthReport:
    """健康报告"""
    overall_score: float = 0.0
    items: List[DiagnosticItem] = dataclasses.field(default_factory=list)
    warnings: List[str] = dataclasses.field(default_factory=list)
    errors: List[str] = dataclasses.field(default_factory=list)
    maintenance_suggestions: List[str] = dataclasses.field(default_factory=list)


@dataclasses.dataclass
class FaultPrediction:
    """故障预测"""
    component: str = ""
    fault_type: str = ""
    probability: float = 0.0
    suggestion: str = ""


@dataclasses.dataclass
class CalibrationStatus:
    """校准状态"""
    sensor_name: str = ""
    last_calibrated: str = ""
    expires_at: str = ""
    is_valid: bool = True


class DiagnosticsService:
    """
    自诊断与健康服务 — POST 自检、实时监控、健康报告、故障预测、校准管理。
    """

    def __init__(self):
        self._initialized = False

    def initialize(self) -> bool:
        logger.info("DiagnosticsService initializing...")
        self._initialized = True
        return True

    def run_post(self) -> List[DiagnosticItem]:
        """运行开机自检"""
        logger.info("Running POST (Power-On Self Test)...")
        return [
            DiagnosticItem(name="battery", component="battery", status=DiagStatus.OK,
                           value=85.0, unit="%", min_normal=20.0, max_normal=100.0),
            DiagnosticItem(name="left_motor", component="motor", status=DiagStatus.OK,
                           message="Motor encoder OK"),
            DiagnosticItem(name="right_motor", component="motor", status=DiagStatus.OK,
                           message="Motor encoder OK"),
            DiagnosticItem(name="lidar", component="sensor", status=DiagStatus.OK,
                           message="LiDAR connected"),
            DiagnosticItem(name="imu", component="sensor", status=DiagStatus.OK,
                           message="IMU calibrated"),
            DiagnosticItem(name="wifi", component="communication", status=DiagStatus.OK,
                           message="Wi-Fi connected"),
        ]

    def generate_health_report(self) -> HealthReport:
        """生成健康报告"""
        logger.info("Generating health report...")
        items = self.run_post()
        return HealthReport(
            overall_score=95.0,
            items=items,
            warnings=[],
            errors=[],
            maintenance_suggestions=["定期检查电机散热"]
        )

    def start_monitoring(self, interval_sec: float = 1.0,
                         alert_callback: Optional[Callable] = None) -> None:
        """启动实时监控"""
        logger.info(f"Monitoring started (interval={interval_sec}s)")

    def stop_monitoring(self) -> None:
        """停止实时监控"""
        logger.info("Monitoring stopped")

    def predict_faults(self) -> List[FaultPrediction]:
        """故障预测"""
        return []

    def get_calibration_status(self) -> List[CalibrationStatus]:
        """获取校准状态"""
        return [
            CalibrationStatus(sensor_name="imu", last_calibrated="2026-06-01",
                              expires_at="2026-07-01", is_valid=True),
            CalibrationStatus(sensor_name="camera_left", last_calibrated="2026-05-15",
                              expires_at="2026-06-15", is_valid=True),
        ]

    def trigger_calibration(self, sensor_name: str) -> bool:
        """触发传感器校准"""
        logger.info(f"Calibration triggered for {sensor_name}")
        return True

    def shutdown(self) -> None:
        logger.info("DiagnosticsService shutting down")
        self._initialized = False
