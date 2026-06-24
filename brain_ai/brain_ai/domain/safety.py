"""
brain_ai/domain/safety.py — Safety status and alert domain model.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import IntEnum, Enum


class SafetyLevel(IntEnum):
    """Four-level safety hierarchy (S0 = critical, S3 = normal)."""
    S0_EMERGENCY = 0    # Immediate E-stop
    S1_CRITICAL  = 1    # < 50 ms response
    S2_WARNING   = 2    # < 200 ms response
    S3_NORMAL    = 3    # Nominal operation


class AlertType(str, Enum):
    COLLISION_IMMINENT    = "COLLISION_IMMINENT"
    JOINT_LIMIT_EXCEEDED  = "JOINT_LIMIT_EXCEEDED"
    VELOCITY_LIMIT        = "VELOCITY_LIMIT"
    FORCE_TORQUE_LIMIT    = "FORCE_TORQUE_LIMIT"
    WORKSPACE_BOUNDARY    = "WORKSPACE_BOUNDARY"
    HUMAN_PROXIMITY       = "HUMAN_PROXIMITY"
    SENSOR_FAILURE        = "SENSOR_FAILURE"
    SOFTWARE_FAULT        = "SOFTWARE_FAULT"
    MANUAL_ESTOP          = "MANUAL_ESTOP"


@dataclass
class SafetyAlert:
    """A single safety event."""
    alert_type: AlertType = AlertType.SOFTWARE_FAULT
    level: SafetyLevel = SafetyLevel.S3_NORMAL
    message: str = ""
    source: str = ""                     # e.g. "safety_monitor", "hal_interface"
    timestamp: datetime = field(default_factory=datetime.now)
    data: dict = field(default_factory=dict)   # Extra context (joint_id, force, etc.)
    acknowledged: bool = False

    def to_dict(self) -> dict:
        return {
            "type": self.alert_type.value,
            "level": int(self.level),
            "message": self.message,
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
            "acknowledged": self.acknowledged,
        }


@dataclass
class SafetyStatus:
    """Snapshot of robot safety state at a point in time."""
    level: SafetyLevel = SafetyLevel.S3_NORMAL
    emergency_stop_active: bool = False
    active_alerts: list[SafetyAlert] = field(default_factory=list)
    collision_risk_score: float = 0.0    # 0.0 = safe, 1.0 = imminent
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def is_safe_to_execute(self) -> bool:
        return (
            not self.emergency_stop_active
            and self.level >= SafetyLevel.S2_WARNING
            and self.collision_risk_score < 0.8
        )

    def highest_alert(self) -> SafetyLevel:
        if not self.active_alerts:
            return SafetyLevel.S3_NORMAL
        return min(a.level for a in self.active_alerts)

    def to_dict(self) -> dict:
        return {
            "level": int(self.level),
            "emergency_stop_active": self.emergency_stop_active,
            "active_alert_count": len(self.active_alerts),
            "collision_risk_score": round(self.collision_risk_score, 4),
            "is_safe_to_execute": self.is_safe_to_execute,
        }


@dataclass
class SafetyConfig:
    """Safety thresholds loaded from config."""
    max_joint_velocity_rad_s: float = 1.5
    max_end_effector_speed_m_s: float = 0.3
    min_human_distance_m: float = 0.5
    max_collision_risk_threshold: float = 0.7
    estop_response_time_ms: float = 5.0
    enable_force_torque_check: bool = True
