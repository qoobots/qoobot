"""Brain OS 安全模块 (Safety)。

提供安全监控与紧急处理能力：
- SafetyAPI     — 安全快照、告警流、速度限幅
- EmergencyAPI  — 紧急停止与恢复
"""

from brain_os.safety.safety_api import SafetyAPI
from brain_os.safety.emergency_api import EmergencyAPI

__all__ = ["SafetyAPI", "EmergencyAPI"]
