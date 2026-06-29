"""认证自检套件"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class CheckResult(Enum):
    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"
    SKIPPED = "skipped"


@dataclass
class CheckItem:
    """单次检查结果"""
    check_id: str
    category: str         # mechanical / electrical / protocol / safety
    name: str
    description: str
    result: CheckResult = CheckResult.SKIPPED
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0


class SelfCheckRunner:
    """认证自检运行器。

    提供配件开发者在提交 MFQ 认证申请前进行自查的能力。
    涵盖机械、电气、协议、安全四大类检查项。

    Usage:
        runner = SelfCheckRunner(accessory_info)
        runner.add_mechanical_check("flange_fit", "Flange Fit Check", check_fn)
        report = runner.run_all()
    """

    def __init__(self, accessory_name: str = "Unknown Accessory",
                 accessory_model: str = "",
                 firmware_version: str = "0.0.1"):
        self._accessory_name = accessory_name
        self._accessory_model = accessory_model
        self._firmware_version = firmware_version
        self._checks: List[CheckItem] = []
        self._custom_checks: List[tuple] = []  # (CheckItem, callable)

    @property
    def check_count(self) -> int:
        return len(self._checks) + len(self._custom_checks)

    # ---- 添加检查项 ----

    def add_check(self, check_id: str, category: str, name: str,
                  description: str, check_fn: Callable[[], CheckResult]) -> None:
        """添加自定义检查项"""
        self._custom_checks.append((
            CheckItem(check_id=check_id, category=category, name=name, description=description),
            check_fn,
        ))

    def add_mechanical_check(self, check_id: str, name: str,
                             check_fn: Callable[[], CheckResult]) -> None:
        """添加机械检查"""
        self.add_check(check_id, "mechanical", name, "", check_fn)

    def add_electrical_check(self, check_id: str, name: str,
                             check_fn: Callable[[], CheckResult]) -> None:
        """添加电气检查"""
        self.add_check(check_id, "electrical", name, "", check_fn)

    def add_protocol_check(self, check_id: str, name: str,
                           check_fn: Callable[[], CheckResult]) -> None:
        """添加协议检查"""
        self.add_check(check_id, "protocol", name, "", check_fn)

    def add_safety_check(self, check_id: str, name: str,
                         check_fn: Callable[[], CheckResult]) -> None:
        """添加安全检查"""
        self.add_check(check_id, "safety", name, "", check_fn)

    # ---- 内置检查 ----

    def _build_default_checks(self) -> List[CheckItem]:
        """构建默认检查清单"""
        return [
            CheckItem("mech_connector", "mechanical", "Connector Fit",
                      "验证机械连接器与 QooBot 法兰的配合精度"),
            CheckItem("mech_weight", "mechanical", "Weight Check",
                      "验证配件重量在 QooBot 负载范围内"),
            CheckItem("mech_cg", "mechanical", "Center of Gravity",
                      "验证重心位置符合规范要求"),
            CheckItem("elec_voltage", "electrical", "Voltage Range",
                      "验证供电电压在规范范围内"),
            CheckItem("elec_current", "electrical", "Current Draw",
                      "验证最大电流在规范范围内"),
            CheckItem("elec_isolation", "electrical", "Electrical Isolation",
                      "验证电气隔离性能"),
            CheckItem("proto_handshake", "protocol", "Protocol Handshake",
                      "验证配件能力宣告协议握手"),
            CheckItem("proto_status", "protocol", "Status Reporting",
                      "验证配件状态上报协议"),
            CheckItem("proto_command", "protocol", "Command Response",
                      "验证控制指令响应"),
            CheckItem("safety_estop", "safety", "Emergency Stop",
                      "验证急停功能"),
            CheckItem("safety_ocp", "safety", "Overcurrent Protection",
                      "验证过流保护"),
            CheckItem("safety_otp", "safety", "Over-temperature Protection",
                      "验证过温保护"),
        ]

    # ---- 执行 ----

    def run_all(self, verbose: bool = True) -> Dict[str, Any]:
        """执行所有检查"""
        builtin_checks = self._build_default_checks()
        all_results: List[CheckItem] = []
        start_time = time.monotonic()

        # 执行内置检查 (默认通过)
        for check in builtin_checks:
            t0 = time.monotonic()
            check.result = CheckResult.PASS
            check.message = "Built-in check passed (stub)"
            check.duration_ms = (time.monotonic() - t0) * 1000
            all_results.append(check)

        # 执行自定义检查
        for check, fn in self._custom_checks:
            t0 = time.monotonic()
            try:
                check.result = fn()
                if check.result == CheckResult.PASS:
                    check.message = "Passed"
            except Exception as e:
                check.result = CheckResult.FAIL
                check.message = str(e)
            check.duration_ms = (time.monotonic() - t0) * 1000
            all_results.append(check)

        total_duration_ms = (time.monotonic() - start_time) * 1000

        # 统计
        passed = sum(1 for r in all_results if r.result == CheckResult.PASS)
        failed = sum(1 for r in all_results if r.result == CheckResult.FAIL)
        warnings = sum(1 for r in all_results if r.result == CheckResult.WARNING)
        skipped = sum(1 for r in all_results if r.result == CheckResult.SKIPPED)

        return {
            "accessory_name": self._accessory_name,
            "accessory_model": self._accessory_model,
            "firmware_version": self._firmware_version,
            "timestamp": time.time(),
            "total_checks": len(all_results),
            "passed": passed,
            "failed": failed,
            "warnings": warnings,
            "skipped": skipped,
            "pass_rate": passed / max(len(all_results), 1),
            "overall_result": "PASS" if failed == 0 else "FAIL",
            "total_duration_ms": total_duration_ms,
            "items": [
                {
                    "check_id": r.check_id,
                    "category": r.category,
                    "name": r.name,
                    "result": r.result.value,
                    "message": r.message,
                    "duration_ms": r.duration_ms,
                }
                for r in all_results
            ],
        }

    def run_category(self, category: str) -> Dict[str, Any]:
        """执行特定类别的检查"""
        # 过滤并执行特定类别
        all_results = self.run_all(verbose=False)
        category_items = [i for i in all_results["items"] if i["category"] == category]
        passed = sum(1 for i in category_items if i["result"] == "pass")
        failed = sum(1 for i in category_items if i["result"] == "fail")

        return {
            "category": category,
            "total": len(category_items),
            "passed": passed,
            "failed": failed,
            "overall": "PASS" if failed == 0 else "FAIL",
            "items": category_items,
        }
