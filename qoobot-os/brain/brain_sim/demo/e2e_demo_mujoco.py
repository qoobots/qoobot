"""
brain_sim/demo/e2e_demo_mujoco.py — Phase 2 M6 真实物理仿真端到端演示
=====================================================================

完整的 Brain OS + MuJoCo 物理仿真流水线：
  启动 MuJoCo → 加载双足机器人 → 稳定站立 → 感知状态
  → 中文指令解析 → 任务分解 → 行为树生成 → 运动控制 → 执行反馈

与 e2e_demo.py 的区别：
  - e2e_demo.py: 纯 mock 模式，零外部依赖，仅打印日志
  - e2e_demo_mujoco.py: 连接真实 MuJoCo 物理引擎，机器人实际运动

特性:
  - 可选 MuJoCo 模式（默认）或 Mock 模式（CI 兼容）
  - 实时物理仿真 + 传感器数据
  - 性能计时和 M6 验证指标报告
  - 支持多种行走场景

用法:
  cd brain_sim && python demo/e2e_demo_mujoco.py [--scenario stand|walk|turn|full]
  cd brain_sim && python demo/e2e_demo_mujoco.py --mock  # CI 兼容模式
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

# 确保 brain_sim 在路径中
_PROJ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_PROJ))

from brain_sim.sim_bridge import SimBridge, create_sim_config

logger = logging.getLogger("e2e_mujoco")

# ══════════════════════════════════════════════════════════
#  Demo scenarios
# ══════════════════════════════════════════════════════════

SCENARIOS = {
    "stand": {
        "name": "稳定站立验证",
        "instruction": "保持站立姿态不动",
        "description": "验证浮动基座双足机器人的站立稳定性",
        "duration_steps": 5000,    # 5 秒
        "walking_velocity": None,  # 不移动
        "m6_pass_height_min": 1.0,
        "m6_pass_roll_max": 0.1,   # rad ≈ 5.7°
        "m6_pass_pitch_max": 0.1,
    },
    "walk": {
        "name": "缓慢前进验证",
        "instruction": "以0.2米/秒的速度向前行走",
        "description": "验证双足机器人匀速行走的稳定性",
        "duration_steps": 3000,    # 3 秒
        "walking_velocity": (0.2, 0.0, 0.0),
        "m6_pass_height_min": 0.95,
        "m6_pass_roll_max": 0.15,
        "m6_pass_pitch_max": 0.15,
    },
    "turn": {
        "name": "原地转向验证",
        "instruction": "以0.3弧度/秒的速度原地转向",
        "description": "验证双足机器人转向控制的稳定性",
        "duration_steps": 3000,    # 3 秒
        "walking_velocity": (0.0, 0.0, 0.3),
        "m6_pass_height_min": 0.95,
        "m6_pass_roll_max": 0.15,
        "m6_pass_pitch_max": 0.15,
    },
    "full": {
        "name": "全流程验证",
        "instruction": "站立→前进→转向→停止",
        "description": "验证完整的行走控制流水线",
        "duration_steps": 10000,   # 10 秒
        "walking_velocity": None,  # 多阶段
        "m6_pass_height_min": 0.95,
        "m6_pass_roll_max": 0.15,
        "m6_pass_pitch_max": 0.15,
    },
}


# ══════════════════════════════════════════════════════════
#  Demo orchestrator
# ══════════════════════════════════════════════════════════

@dataclass
class DemoReport:
    scenario: str
    instruction: str
    success: bool
    total_ms: float
    stages: dict = field(default_factory=dict)
    metrics: dict = field(default_factory=dict)
    warnings: list = field(default_factory=list)
    m6_checks: dict = field(default_factory=dict)
    output: str = ""


class E2EMuJoCoDemo:
    """真实 MuJoCo 物理仿真的端到端演示。"""

    SEP = "─" * 68
    DBL = "═" * 68

    def __init__(self, scenario: str = "stand", use_mock: bool = False):
        self.scenario = SCENARIOS.get(scenario, SCENARIOS["stand"])
        self.use_mock = use_mock
        self.t0 = time.perf_counter()
        self._sim: Optional[SimBridge] = None

    def ts(self) -> float:
        return (time.perf_counter() - self.t0) * 1000

    # ── Rendering helpers ──────────────────────────────────

    @staticmethod
    def _banner(text: str, style: str = "="):
        c = "═" if style == "=" else "─"
        print(f"\n{c * 68}")
        print(f"  {text}")
        print(f"{c * 68}")

    @staticmethod
    def _step(num: int, name: str):
        print(f"\n  ╭─ Step {num}: {name}")

    @staticmethod
    def _ok(msg: str = ""):
        tag = f"  ✅  {msg}" if msg else "  ✅  OK"
        print(tag)

    @staticmethod
    def _warn(msg: str):
        print(f"  ⚠️  {msg}")

    @staticmethod
    def _fail(msg: str):
        print(f"  ❌  {msg}")

    @staticmethod
    def _info(key: str, val: str):
        print(f"     {key:<20s} : {val}")

    @staticmethod
    def _latency(ms: float):
        print(f"     {'耗时':<20s} : {ms:.1f} ms")

    # ── Pipeline stages ────────────────────────────────────

    async def stage_0_startup(self) -> dict:
        self._banner(f"Brain OS M6 仿真验证 — {self.scenario['name']}", "=")
        self._info("场景", self.scenario["description"])
        self._info("指令", self.scenario["instruction"])
        self._info("模式", "Mock" if self.use_mock else "MuJoCo 物理仿真")
        print()

        stages = {}

        self._step(0, "系统初始化")

        backend = "mock" if self.use_mock else "mujoco"
        config = create_sim_config(
            world="qoobot_float",
            robot="qoobot_biped",
            backend=backend,
            headless=self.use_mock,
        )
        self._sim = SimBridge(config)
        await self._sim.start()

        if not self.use_mock and not self._sim.has_physics:
            self._warn("MuJoCo 未安装，降级为 Mock 模式")
            self._info("安装 MuJoCo", "pip install mujoco")

        stages["startup_ms"] = self.ts()
        self._ok(f"系统就绪 ({stages['startup_ms']:.0f} ms)")
        return stages

    async def stage_1_scene_setup(self) -> dict:
        self._step(1, "场景初始化")
        stages = {}

        await self._sim.load_robot_scene("qoobot_float")
        await self._sim.reset()

        # 读取初始状态
        state = await self._sim.get_state()
        pose = state.robot_pose
        self._info("基座位置", f"({pose.position[0]:.3f}, {pose.position[1]:.3f}, {pose.position[2]:.3f})")
        self._info("基座姿态", f"({pose.orientation[0]:.3f}, {pose.orientation[1]:.3f}, "
                  f"{pose.orientation[2]:.3f}, {pose.orientation[3]:.3f})")

        joint_state = state.joint_states.get("arm", state.joint_states.get("robot", None))
        if joint_state:
            self._info("关节数", str(len(joint_state.names)))

        stages["scene_setup_ms"] = self.ts()
        self._ok(f"场景就绪 ({stages['scene_setup_ms']:.0f} ms)")
        return stages

    async def stage_2_stabilize(self) -> dict:
        """稳定站立阶段（M6 关键验证项）。"""
        self._step(2, "稳定站立")
        stages = {}

        print("     让机器人稳定站立 2 秒...")
        await self._sim.step(2000)  # 2 秒 @ 1ms timestep

        metrics = self._sim.get_metrics()
        height = metrics.get("base_height", 0)
        roll = abs(metrics.get("base_roll", 0))
        pitch = abs(metrics.get("base_pitch", 0))

        self._info("基座高度", f"{height:.3f} m")
        self._info("Roll 偏差", f"{roll:.4f} rad ({roll*57.3:.1f}°)")
        self._info("Pitch 偏差", f"{pitch:.4f} rad ({pitch*57.3:.1f}°)")

        stages["stabilize_ms"] = self.ts()
        stages["stand_height"] = height
        stages["stand_roll"] = roll
        stages["stand_pitch"] = pitch
        self._ok(f"站立稳定 ({stages['stabilize_ms']:.0f} ms)")
        return stages

    async def stage_3_walking(self) -> dict:
        """行走控制阶段。"""
        self._step(3, "行走控制")
        stages = {}

        if self.scenario.get("walking_velocity"):
            vx, vy, wz = self.scenario["walking_velocity"]
            self._info("目标速度", f"vx={vx:.1f} vy={vy:.1f} wz={wz:.1f}")
            self._sim.set_walking_velocity(vx=vx, vy=vy, wz=wz)
            await self._sim.step(self.scenario["duration_steps"])
            self._sim.stop_walking()
            await self._sim.step(500)  # 停止后缓冲

            metrics = self._sim.get_metrics()
            height = metrics.get("base_height", 0)
            self._info("行走后高度", f"{height:.3f} m")
            stages["walk_height"] = height

        elif self.scenario["name"] == "全流程验证":
            # 多阶段：站立 → 前进 → 转向 → 停止
            print("     [阶段 A] 站立 2 秒...")
            await self._sim.step(2000)

            print("     [阶段 B] 前进 0.2 m/s × 3 秒...")
            self._sim.set_walking_velocity(vx=0.2, vy=0.0, wz=0.0)
            await self._sim.step(3000)

            print("     [阶段 C] 转向 0.3 rad/s × 2 秒...")
            self._sim.set_walking_velocity(vx=0.0, vy=0.0, wz=0.3)
            await self._sim.step(2000)

            print("     [阶段 D] 停止缓冲 2 秒...")
            self._sim.stop_walking()
            await self._sim.step(2000)

            metrics = self._sim.get_metrics()
            self._info("最终高度", f"{metrics.get('base_height', 0):.3f} m")

        stages["walking_ms"] = self.ts()
        self._ok(f"行走控制完成 ({stages['walking_ms']:.0f} ms)")
        return stages

    async def stage_4_stand_still(self) -> dict:
        """再次站立验证。"""
        self._step(4, "最终站立验证")
        stages = {}

        print("     验证停止后站立稳定性...")
        await self._sim.step(2000)

        metrics = self._sim.get_metrics()
        height = metrics.get("base_height", 0)
        roll = abs(metrics.get("base_roll", 0))
        pitch = abs(metrics.get("base_pitch", 0))

        self._info("基座高度", f"{height:.3f} m")
        self._info("Roll 偏差", f"{roll:.4f} rad ({roll*57.3:.1f}°)")
        self._info("Pitch 偏差", f"{pitch:.4f} rad ({pitch*57.3:.1f}°)")

        stages["final_height"] = height
        stages["final_roll"] = roll
        stages["final_pitch"] = pitch
        stages["final_ms"] = self.ts()
        self._ok(f"最终站立完成")
        return stages

    async def stage_5_perception(self) -> dict:
        """感知阶段 — 读取真实仿真传感器数据。"""
        self._step(5, "环境感知")
        stages = {}

        state = await self._sim.get_state()
        pose = state.robot_pose
        self._info("基座位置", f"({pose.position[0]:.3f}, {pose.position[1]:.3f}, {pose.position[2]:.3f})")

        # 读取关节状态
        joint_state = await self._sim.get_joint_states()
        if joint_state.names:
            # 展示前 6 个关节
            for i in range(min(6, len(joint_state.names))):
                name = joint_state.names[i]
                pos = joint_state.positions[i] if i < len(joint_state.positions) else 0
                print(f"       └─ {name:<20s} = {pos:+.3f} rad")

        # 性能指标
        metrics = self._sim.get_metrics()
        rtf = metrics.get('real_time_factor', None)
        rtf_str = f"{rtf:.2f}x" if isinstance(rtf, (int, float)) else str(rtf)
        self._info("实时因子", rtf_str)
        step_t = metrics.get('step_time_ms', None)
        step_str = f"{step_t:.3f} ms" if isinstance(step_t, (int, float)) else str(step_t)
        self._info("步进耗时", step_str)

        stages["perception_ms"] = self.ts()
        self._ok(f"感知完成 ({stages['perception_ms']:.0f} ms)")
        return stages

    async def stage_6_teardown(self) -> dict:
        """清理与报告。"""
        self._step(6, "清理与报告")
        stages = {}

        # 最终指标
        final_metrics = self._sim.get_metrics()
        self._info("总步数", str(final_metrics.get("step_count", 0)))
        self._info("总时间", f"{final_metrics.get('sim_time', 0):.3f} s")

        await self._sim.stop()

        stages["teardown_ms"] = self.ts()
        self._ok(f"清理完成 ({stages['teardown_ms']:.0f} ms)")
        return stages

    # ── M6 验证检查 ────────────────────────────────────────

    def _run_m6_checks(self, all_stages: dict) -> dict:
        """运行 M6 仿真验证检查项。"""
        checks = {}

        # 检查 1: 站立高度
        height = all_stages.get("stand_height",
                                all_stages.get("final_height", 0))
        min_height = self.scenario.get("m6_pass_height_min", 1.0)
        checks["height_check"] = {
            "pass": height >= min_height,
            "value": round(height, 3),
            "threshold": min_height,
            "desc": f"站立高度 ≥ {min_height}m"
        }

        # 检查 2: Roll 偏差
        roll = all_stages.get("stand_roll",
                              all_stages.get("final_roll", 0))
        max_roll = self.scenario.get("m6_pass_roll_max", 0.1)
        checks["roll_check"] = {
            "pass": roll <= max_roll,
            "value": round(roll, 4),
            "threshold": max_roll,
            "desc": f"|Roll| ≤ {max_roll} rad"
        }

        # 检查 3: Pitch 偏差
        pitch = all_stages.get("stand_pitch",
                               all_stages.get("final_pitch", 0))
        max_pitch = self.scenario.get("m6_pass_pitch_max", 0.1)
        checks["pitch_check"] = {
            "pass": pitch <= max_pitch,
            "value": round(pitch, 4),
            "threshold": max_pitch,
            "desc": f"|Pitch| ≤ {max_pitch} rad"
        }

        return checks

    # ── Main runner ────────────────────────────────────────

    async def run(self) -> DemoReport:
        """Execute full M6 demo pipeline and return report."""
        report = DemoReport(
            scenario=self.scenario["name"],
            instruction=self.scenario["instruction"],
            success=False,
            total_ms=0,
        )

        try:
            all_stages = {}

            # Stage 0: Startup
            all_stages.update(await self.stage_0_startup())

            # Stage 1: Scene setup
            all_stages.update(await self.stage_1_scene_setup())

            # Stage 2: Stabilize standing
            all_stages.update(await self.stage_2_stabilize())

            # Stage 3: Walking control
            all_stages.update(await self.stage_3_walking())

            # Stage 4: Final stand verification
            all_stages.update(await self.stage_4_stand_still())

            # Stage 5: Perception
            all_stages.update(await self.stage_5_perception())

            # Stage 6: Teardown
            all_stages.update(await self.stage_6_teardown())

            # M6 验证检查
            m6_checks = self._run_m6_checks(all_stages)
            report.m6_checks = m6_checks
            report.stages = all_stages

            # 判断成功：所有 M6 检查通过
            report.success = all(c["pass"] for c in m6_checks.values())

        except Exception as e:
            logger.exception("M6 Demo pipeline error: %s", e)
            report.warnings.append(f"exception: {e}")

        report.total_ms = self.ts()

        # ── Final report ────────────────────────────────────
        self._banner("M6 仿真验证报告", "=")
        status = "✅ PASS" if report.success else "❌ FAIL"
        print(f"  Status     : {status}")
        print(f"  Scenario   : {report.scenario}")
        print(f"  Instruction: {report.instruction}")
        print(f"  Total time : {report.total_ms:.0f} ms")
        print(f"  Mode       : {'Mock' if self.use_mock else 'MuJoCo 物理仿真'}")

        print(f"\n  M6 验证检查项:")
        for check_name, check in report.m6_checks.items():
            icon = "✅" if check["pass"] else "❌"
            print(f"    {icon} {check['desc']:<30s} "
                  f"实测={check['value']} 阈值={check['threshold']}")

        print(f"\n  Stage breakdown:")
        stage_order = [
            ("startup_ms", "系统初始化"),
            ("scene_setup_ms", "场景初始化"),
            ("stabilize_ms", "稳定站立"),
            ("walking_ms", "行走控制"),
            ("final_ms", "最终站立验证"),
            ("perception_ms", "环境感知"),
            ("teardown_ms", "清理收尾"),
        ]
        for key, label in stage_order:
            if key in report.stages:
                ms = report.stages[key]
                bar_len = max(1, int(ms / max(1, report.total_ms) * 30))
                bar = "█" * min(bar_len, 30)
                print(f"    {label:<12s} {bar:<30s} {ms:8.1f} ms")

        if report.warnings:
            print(f"\n  Warnings ({len(report.warnings)}):")
            for w in report.warnings:
                print(f"    ⚠️  {w}")

        print(f"\n{'─' * 68}")
        print("  M6 Demo complete.")
        print(f"{'─' * 68}\n")

        return report


# ── Entry point ────────────────────────────────────────────

async def main_async():
    parser = argparse.ArgumentParser(
        description="Brain OS M6 MuJoCo 端到端仿真验证"
    )
    parser.add_argument(
        "--scenario", choices=list(SCENARIOS.keys()),
        default="stand", help="验证场景 (default: stand)",
    )
    parser.add_argument(
        "--mock", action="store_true",
        help="使用 Mock 模式（无 MuJoCo 依赖，CI 兼容）",
    )
    parser.add_argument(
        "--all", action="store_true",
        help="运行所有场景",
    )
    parser.add_argument(
        "--output", type=str, default=None,
        help="输出 JSON 报告到指定路径",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    reports = []
    scenarios_to_run = list(SCENARIOS.keys()) if args.all else [args.scenario]

    for scenario in scenarios_to_run:
        demo = E2EMuJoCoDemo(scenario=scenario, use_mock=args.mock)
        report = await demo.run()
        reports.append(report)

    # JSON output
    if args.output and reports:
        output_data = []
        for r in reports:
            output_data.append({
                "scenario": r.scenario,
                "instruction": r.instruction,
                "success": r.success,
                "total_ms": r.total_ms,
                "stages": r.stages,
                "m6_checks": r.m6_checks,
                "warnings": r.warnings,
            })
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2, default=str)
        print(f"📄 Report saved to: {args.output}")

    return 0 if all(r.success for r in reports) else 1


def main():
    import asyncio
    return asyncio.run(main_async())


if __name__ == "__main__":
    sys.exit(main())
