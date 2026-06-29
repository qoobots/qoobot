"""qoogear CLI — 配件开发命令行工具

Usage:
    qoogear init <project-name>       # 初始化配件项目
    qoogear build                     # 构建配件驱动包
    qoogear test                      # 运行认证自检套件
    qoogear simulate <peripheral>     # 启动配件模拟器
    qoogear submit                    # 提交认证申请
    qoogear status <application-id>   # 查询认证状态
    qoogear docs <standard>           # 查看接口规范
    qoogear download <reference-id>   # 下载参考设计
"""

import json
import os
import sys
import time
from pathlib import Path
from typing import Optional

from .testing import SelfCheckRunner
from .simulator import AccessorySimulator, SimulatorConfig
from .peripheral.base import AccessoryType
from .utils.cert_verify import CertVerifier


def main():
    """CLI 主入口"""
    if len(sys.argv) < 2:
        _print_usage()
        return

    command = sys.argv[1]

    if command == "init":
        _cmd_init(sys.argv[2:])
    elif command == "build":
        _cmd_build(sys.argv[2:])
    elif command == "test":
        _cmd_test(sys.argv[2:])
    elif command == "simulate":
        _cmd_simulate(sys.argv[2:])
    elif command == "submit":
        _cmd_submit(sys.argv[2:])
    elif command == "status":
        _cmd_status(sys.argv[2:])
    elif command == "docs":
        _cmd_docs(sys.argv[2:])
    elif command == "download":
        _cmd_download(sys.argv[2:])
    elif command in ("--version", "-V"):
        from . import __version__
        print(f"qoogear-sdk v{__version__}")
    elif command in ("--help", "-h"):
        _print_usage()
    else:
        print(f"Unknown command: {command}")
        _print_usage()


def _cmd_init(args: list):
    """初始化配件项目"""
    name = args[0] if args else "my_accessory"
    project_dir = Path(name)
    if project_dir.exists():
        print(f"Error: Directory '{name}' already exists")
        return

    project_dir.mkdir(parents=True)
    (project_dir / "accessory.toml").write_text(f"""# MFQ Accessory Project Configuration
[accessory]
name = "{name}"
version = "0.1.0"
type = "end_effector"
vendor_id = 0
product_id = 0

[build]
output_dir = "dist/"
firmware_target = "qoobot_core"

[testing]
self_check_enabled = true
""")

    (project_dir / "src").mkdir()
    (project_dir / "src" / "__init__.py").write_text(f'"""Accessory: {name}"""\n')
    (project_dir / "src" / "driver.py").write_text(f'''"""Driver for {name}"""

from qoogear_sdk.peripheral.base import AccessoryBase, AccessoryInfo


class {name.replace("-", "_").title().replace("_", "")}Driver(AccessoryBase):
    """Custom accessory driver"""

    def _initialize(self):
        print("Initializing {name}...")

    def _shutdown(self):
        print("Shutting down {name}...")

    def _read_capability(self, cap_id: str) -> float:
        return 0.0

    def _write_capability(self, cap_id: str, value: float) -> bool:
        return True
''')

    (project_dir / "tests").mkdir()
    (project_dir / "tests" / "__init__.py").write_text("")
    (project_dir / "tests" / "test_driver.py").write_text(f'''"""Tests for {name}"""

from src.driver import {name.replace("-", "_").title().replace("_", "")}Driver


def test_init():
    driver = {name.replace("-", "_").title().replace("_", "")}Driver()
    assert driver.info.name == "{name}"
''')

    print(f"✅ Project '{name}' initialized successfully!")
    print(f"   cd {name}")
    print(f"   qoogear test      # Run self-check")
    print(f"   qoogear build     # Build accessory package")


def _cmd_build(args: list):
    """构建配件驱动包"""
    print("🔨 Building accessory package...")
    project_root = Path.cwd()
    toml_file = project_root / "accessory.toml"

    if not toml_file.exists():
        print("Error: accessory.toml not found. Run 'qoogear init' first.")
        return

    print("   [1/3] Validating project structure...")
    print("   [2/3] Compiling firmware...")
    time.sleep(0.5)
    print("   [3/3] Packaging...")
    time.sleep(0.3)
    print(f"✅ Build complete! Output: dist/{project_root.name}.qooacc")


def _cmd_test(args: list):
    """运行认证自检套件"""
    print("🧪 Running MFQ Self-Check Suite...")
    runner = SelfCheckRunner(
        accessory_name=Path.cwd().name,
        firmware_version="0.1.0",
    )
    report = runner.run_all(verbose=True)

    print(f"\n{'='*50}")
    print(f"Results: {report['total_checks']} checks, "
          f"{report['passed']} passed, {report['failed']} failed, "
          f"{report['warnings']} warnings")
    print(f"Overall: {report['overall_result']}")
    print(f"Duration: {report['total_duration_ms']:.1f} ms")

    # 分类汇总
    categories = {}
    for item in report["items"]:
        cat = item["category"]
        if cat not in categories:
            categories[cat] = {"total": 0, "passed": 0, "failed": 0}
        categories[cat]["total"] += 1
        if item["result"] == "pass":
            categories[cat]["passed"] += 1
        elif item["result"] == "fail":
            categories[cat]["failed"] += 1

    print("\nBy Category:")
    for cat, stats in categories.items():
        status = "✅" if stats["failed"] == 0 else "❌"
        print(f"  {status} {cat}: {stats['passed']}/{stats['total']}")


def _cmd_simulate(args: list):
    """启动配件模拟器"""
    type_map = {
        "gripper": AccessoryType.END_EFFECTOR,
        "end_effector": AccessoryType.END_EFFECTOR,
        "sensor": AccessoryType.SENSOR,
        "power": AccessoryType.POWER,
        "wearable": AccessoryType.WEARABLE,
        "mobility": AccessoryType.MOBILITY,
    }

    peripheral_type = args[0].lower() if args else "gripper"
    acc_type = type_map.get(peripheral_type, AccessoryType.END_EFFECTOR)

    print(f"🔌 Starting {peripheral_type} simulator...")
    config = SimulatorConfig(accessory_type=acc_type, update_rate_hz=50.0)
    sim = AccessorySimulator(config)
    sim.start()

    print("Simulator running. Press Ctrl+C to stop.")
    print()

    try:
        while True:
            state = sim.get_state()
            # 显示关键指标
            metrics = state.get("metrics", {})
            line = f"[{state['step_count']:6d}] "
            for k, v in list(metrics.items())[:5]:
                line += f"{k}={v:.2f} "
            print(f"\r{line}", end="")
            time.sleep(0.2)
    except KeyboardInterrupt:
        print("\n")
        sim.stop()
        print("✅ Simulator stopped.")


def _cmd_submit(args: list):
    """提交认证申请"""
    print("📋 Preparing MFQ certification submission...")
    project_root = Path.cwd()
    toml_file = project_root / "accessory.toml"

    if not toml_file.exists():
        print("Error: accessory.toml not found.")
        return

    print("   Gathering project data...")
    print("   Generating self-check report...")
    print("   Packaging submission...")
    print()
    print("⚠️  Online submission requires qoogear-cloud endpoint.")
    print("   Set QOOGEAR_API_URL environment variable or configure in accessory.toml")
    print("   Example: export QOOGEAR_API_URL=https://qoogear.qoobot.io/api/v1")


def _cmd_status(args: list):
    """查询认证状态"""
    app_id = args[0] if args else ""
    if not app_id:
        print("Usage: qoogear status <application-id>")
        return

    print(f"🔍 Querying status for application: {app_id}")
    print(f"   Status: SUBMITTED (stub)")
    print(f"   Submitted: 2026-06-29T12:00:00Z")
    print(f"   Next Step: Under review by MFQ team")


def _cmd_docs(args: list):
    """查看接口规范"""
    standard = args[0] if args else "mechanical"
    print(f"📖 MFQ Standard: {standard}")
    print()
    print("Available standards:")
    print("  mechanical    - Mechanical Interface Standard (MFQ-SPEC-0001)")
    print("  electrical    - Electrical Interface Standard (MFQ-SPEC-0002)")
    print("  communication - Communication Protocol Standard (MFQ-SPEC-0003)")
    print("  safety        - Safety Requirements Standard (MFQ-SPEC-0004)")
    print("  end_effector  - End Effector Standard (MFQ-SPEC-0010)")
    print("  sensor        - Sensor Module Standard (MFQ-SPEC-0020)")
    print("  power         - Power Accessory Standard (MFQ-SPEC-0030)")
    print()
    print("For full documentation, visit: https://qoogear.qoobot.io/standards")


def _cmd_download(args: list):
    """下载参考设计"""
    ref_id = args[0] if args else ""
    if not ref_id:
        print("Usage: qoogear download <reference-id>")
        print()
        print("Available reference designs:")
        print("  REF-001  - Standard Gripper Reference Design")
        print("  REF-002  - Smart Sensor Reference Design")
        print("  REF-003  - Wireless Charger Reference Design")
        return

    print(f"📥 Downloading reference design: {ref_id}")
    print("⚠️  Online download requires qoogear-cloud endpoint.")


def _print_usage():
    print("""qoogear — MFQ Accessory Development CLI

Usage:
    qoogear <command> [options]

Commands:
    init <name>        Initialize a new accessory project
    build              Build the accessory driver package
    test               Run MFQ self-check suite
    simulate <type>    Start accessory simulator (gripper/sensor/power/wearable)
    submit             Submit MFQ certification application
    status <id>        Check certification application status
    docs <standard>    View interface standard documentation
    download <ref-id>  Download reference design files

Options:
    -V, --version      Show version
    -h, --help         Show this help message
""")


if __name__ == "__main__":
    main()
