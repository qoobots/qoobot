"""
brain_sim/demo/e2e_demo.py — Sprint 6 T6.2 仿真场景端到端 Demo
================================================================

完整演示流程:
  启动场景 → 感知环境 → 中文指令接收 → 意图解析 → 任务分解
  → BT 生成 → 运动规划 → 轨迹选择 HITL → 执行 → 结果反馈

特性:
  - 零外部依赖 (无 gRPC/ROS2 也可运行)
  - 完整的模拟数据和分步日志
  - 性能计时和报告生成
  - 支持多种演示场景

用法:
  cd brain_sim && python demo/e2e_demo.py [--scenario pick_cup|stack_boxes|inspect_arm|wild_goose]
"""
from __future__ import annotations

import argparse
import json
import logging
import random
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

_PROJ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_PROJ / "brain_ai" / "brain_ai" / "proto_gen"))
sys.path.insert(0, str(_PROJ / "brain_ai"))

from brain_os.cognition import types_pb2 as cog_types
from brain_os.decision import types_pb2 as dec_types

logger = logging.getLogger("e2e_demo")

# ══════════════════════════════════════════════════════════
#  Demo scenarios
# ══════════════════════════════════════════════════════════

SCENARIOS = {
    "pick_cup": {
        "name":    "拿杯子演示",
        "instruction": "把桌上的红色杯子拿给我",
        "description": "机械臂从桌面上拾取红色杯子递给操作员",
        "objects": ["table", "red_cup", "blue_bottle", "box_1", "box_2"],
        "robot_pose": (0.3, 0.0, 0.8),
    },
    "stack_boxes": {
        "name":    "堆叠盒子演示",
        "instruction": "把桌子上的两个盒子叠起来",
        "description": "机械臂依次抓取盒子并堆叠，验证抓取定位",
        "objects": ["table", "box_1", "box_2", "red_cup"],
        "robot_pose": (0.0, 0.3, 0.6),
    },
    "inspect_arm": {
        "name":    "安全检查演示",
        "instruction": "检查机械臂是否处于安全位置",
        "description": "系统检测关节状态、碰撞风险、工作空间安全",
        "objects": ["table"],
        "robot_pose": (0.0, 0.0, 0.3),
    },
    "wild_goose": {
        "name":    "异常输入演示",
        "instruction": "给我变个魔术",
        "description": "演示系统如何处理超出能力范围的指令",
        "objects": ["table"],
        "robot_pose": (0.3, 0.0, 0.8),
    },
}

DEFAULT_JOINT_STATES = {
    "shoulder_pan":  0.00, "shoulder_lift": -0.26,
    "elbow":         1.57, "wrist_1":       -1.31,
    "wrist_2":       0.00, "wrist_3":        0.00,
}

COLLISION_OBJECTS = [
    {"id": "table",  "pos": (0.5, 0.0, 0.0),   "size": (0.8, 0.6, 0.05)},
    {"id": "cup",    "pos": (0.5, 0.1, 0.12),  "size": (0.06, 0.06, 0.10)},
    {"id": "bottle", "pos": (0.5, -0.15, 0.06),"size": (0.05, 0.05, 0.18)},
    {"id": "box_1",  "pos": (0.4, 0.2, 0.03),  "size": (0.10, 0.10, 0.08)},
    {"id": "box_2",  "pos": (0.6, -0.1, 0.03), "size": (0.10, 0.10, 0.08)},
]


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
    warnings: list = field(default_factory=list)
    output: str = ""


class E2EDemo:
    """Simulates full brain_os pipeline with realistic mock data."""

    SEP = "─" * 68
    DBL = "═" * 68

    def __init__(self, scenario: str = "pick_cup", enable_timing: bool = True):
        self.scenario = SCENARIOS.get(scenario, SCENARIOS["pick_cup"])
        self.enable_timing = enable_timing
        self.plan_id = f"demo_{scenario}_{int(time.time())}"
        self.t0 = time.perf_counter()

    def ts(self) -> float:
        """Elapsed ms since demo start."""
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
    def _info(key: str, val: str):
        print(f"     {key:<20s} : {val}")

    @staticmethod
    def _latency(ms: float):
        print(f"     {'耗时':<20s} : {ms:.1f} ms")

    # ── Pipeline stages ────────────────────────────────────

    def stage_0_startup(self) -> dict:
        self._banner(f"Brain OS 端到端演示 — {self.scenario['name']}", "=")
        self._info("场景", self.scenario["description"])
        self._info("指令", self.scenario["instruction"])
        print()

        stages = {}

        self._step(0, "系统初始化")
        time.sleep(0.05)

        # Simulate service startup
        print("     Starting brain_ai gRPC services...")
        print("     ├─ CognitionService    :50052  [OK]")
        print("     ├─ DecisionService     :50052  [OK]")
        print("     ├─ KnowledgeService    :50052  [OK]")
        print("     └─ PerceptionService   :50052  [OK]")
        print("     Starting ROS2 bridge...")
        print("     ├─ JointStates topic           [OK]")
        print("     ├─ SceneGraph topic            [OK]")
        print("     └─ SafetyAlerts topic          [OK]")
        print("     Loading model runtime...")
        print("     └─ Qwen2.5-7B (mock)           [OK]")
        stages["startup_ms"] = self.ts()
        self._ok(f"系统就绪 ({stages['startup_ms']:.0f} ms)")
        return stages

    def stage_1_scene_setup(self) -> dict:
        self._step(1, "场景初始化")
        time.sleep(0.03)
        stages = {}

        print("     Loading Gazebo world: tabletop...")
        print("     Spawning environment objects:")
        for obj in COLLISION_OBJECTS:
            p = obj["pos"]
            print(f"       └─ {obj['id']:<10s} @ ({p[0]:.2f}, {p[1]:.2f}, {p[2]:.2f})")
        print("     Setting robot initial pose...")
        rp = self.scenario["robot_pose"]
        print(f"       └─ kinova_gen3 @ ({rp[0]:.2f}, {rp[1]:.2f}, {rp[2]:.2f})")

        # Simulate joint state publication
        print("     Publishing joint states:")
        for j, v in DEFAULT_JOINT_STATES.items():
            print(f"       └─ {j:<18s} = {v:+.2f} rad")

        stages["scene_setup_ms"] = self.ts()
        self._ok(f"场景就绪 ({stages['scene_setup_ms']:.0f} ms)")
        return stages

    def stage_2_perception(self) -> dict:
        self._step(2, "环境感知")
        time.sleep(0.05)
        stages = {}

        print("     [PerceptionService] Requesting scene graph...")
        # Mock detected objects
        detections = [
            {"label": "table",     "conf": 0.98, "bbox": (0.1, 0.8, -0.3, 0.3)},
            {"label": "cup",       "conf": 0.92, "bbox": (0.45, 0.55, 0.08, 0.18)},
            {"label": "bottle",    "conf": 0.88, "bbox": (0.47, 0.55, -0.20, -0.10)},
            {"label": "box",       "conf": 0.85, "bbox": (0.35, 0.45, 0.15, 0.25)},
            {"label": "box",       "conf": 0.81, "bbox": (0.55, 0.65, -0.15, -0.05)},
        ]

        for d in detections:
            bb = d["bbox"]
            p_str = f"YOLO {d['label']:<8s} conf={d['conf']:.0%} @ [{bb[0]:.2f},{bb[2]:.2f}]"
            prefix = "  ✅ " if d["conf"] > 0.85 else "  ⚠️ "
            print(f"       {prefix}{p_str}")

        # ORB-SLAM3 localization
        print("     [ORB-SLAM3] Robot localization:")
        print(f"       ├─ Position : ({self.scenario['robot_pose'][0]:.3f}, "
              f"{self.scenario['robot_pose'][1]:.3f}, "
              f"{self.scenario['robot_pose'][2]:.3f})")
        print("       └─ Tracking quality: GOOD (148/200 features)")

        # Safety check
        print("     [SafetyMonitor] Collision distance scan:")
        safe = sum(1 for d in detections if d["conf"] > 0.5)
        print(f"       └─ {safe} objects in workspace, min distance: 0.32m [SAFE]")

        stages["perception_ms"] = self.ts()
        self._ok(f"感知完成 ({stages['perception_ms']:.0f} ms)")
        return stages

    def stage_3_cognition(self, report: DemoReport) -> dict:
        self._step(3, "认知引擎")
        stages = {}

        # 3a: ParseIntent
        print("     [CognitionService] ParseIntent...")
        intent = cog_types.Intent()
        intent.language = "zh-CN"
        intent.confidence = 0.88

        inst = self.scenario["instruction"]
        if "杯子" in inst:
            intent.type = cog_types.INTENT_PICK
            intent.raw_text = inst
        elif "盒子" in inst and "叠" in inst:
            intent.type = cog_types.INTENT_SEQUENCE
            intent.raw_text = inst
        elif "检查" in inst or "安全" in inst:
            intent.type = cog_types.INTENT_INSPECT
            intent.raw_text = inst
        elif "魔术" in inst:
            intent.type = cog_types.INTENT_UNKNOWN
            intent.confidence = 0.12
            intent.raw_text = inst
        else:
            intent.type = cog_types.INTENT_PICK
            intent.raw_text = inst

        intent_type_name = cog_types.IntentType.Name(intent.type)
        print(f"       ├─ Type      : {intent_type_name}")
        print(f"       ├─ Confidence: {intent.confidence:.0%}")
        print(f"       └─ Raw text  : {intent.raw_text}")

        stages["parse_intent_ms"] = self.ts()
        self._ok(f"意图解析完成 ({stages['parse_intent_ms']:.0f} ms)")

        # Low-confidence → warn
        if intent.confidence < 0.3:
            self._warn(f"置信度过低 ({intent.confidence:.0%})，将请求人工确认")
            report.warnings.append(f"low_confidence={intent.confidence:.0%}")

        # 3b: DecomposeTask
        print("     [CognitionService] DecomposeTask...")
        time.sleep(0.02)
        subtasks = self._generate_subtasks(intent)
        print(f"       └─ {len(subtasks)} subtasks generated:")
        for i, st in enumerate(subtasks):
            deps = list(st.depends_on)
            dep_str = f" → waits for [{', '.join(deps)}]" if deps else ""
            print(f"          [{i+1}] {st.skill_name:<22s} (id={st.task_id}){dep_str}")

        stages["decompose_ms"] = self.ts()
        self._ok(f"任务分解完成 ({stages['decompose_ms']:.0f} ms)")

        # 3c: GenerateBehaviorTree
        print("     [CognitionService] GenerateBehaviorTree...")
        time.sleep(0.03)
        tree_id = f"bt_{int(time.time())}"
        bt_xml = self._build_bt_xml(tree_id, subtasks)
        print(f"       ├─ Tree ID  : {tree_id}")
        print(f"       └─ XML      : {len(bt_xml)} chars")
        # Show abbreviated BT structure
        for line in bt_xml.splitlines():
            line = line.strip()
            if line and line[0] == "<":
                print(f"          {line}")

        stages["generate_bt_ms"] = self.ts()
        self._ok(f"行为树生成完成 ({stages['generate_bt_ms']:.0f} ms)")

        report.output = bt_xml
        return stages

    def stage_4_decision(self) -> dict:
        self._step(4, "运动规划")
        stages = {}

        print("     [DecisionService] GenerateTrajectories...")
        time.sleep(0.05)

        strategies = ["STOMP (safe)", "STOMP (fast)", "STOMP (min-jerk)"]
        trajectories = []
        for i in range(3):
            traj = dec_types.Trajectory()
            traj.trajectory_id = f"traj_{i}"
            traj.robot_id = "kinova_gen3"
            traj.score = 0.92 - i * 0.12
            traj.duration_sec = 2.1 + i * 0.4
            traj.is_recommended = (i == 0)
            traj.description = strategies[i]
            trajectories.append(traj)

        for t in trajectories:
            rec = " ★ 推荐" if t.is_recommended else ""
            print(f"       ├─ {t.trajectory_id:<10s} score={t.score:.2f}"
                  f" dur={t.duration_sec:.1f}s [{t.description}]{rec}")

        stages["generate_traj_ms"] = self.ts()
        self._ok(f"轨迹生成完成 ({stages['generate_traj_ms']:.0f} ms)")

        # HITL selection
        print("     [HITL] 选择最优轨迹 (自动)...")
        time.sleep(0.01)
        best = trajectories[0]
        print(f"       └─ 已选择: {best.trajectory_id} (score={best.score:.2f}, "
              f"推荐轨迹, 无碰撞)")

        stages["hitl_select_ms"] = self.ts()
        self._ok(f"HITL 确认完成 ({stages['hitl_select_ms']:.0f} ms)")
        return stages

    def stage_5_execution(self) -> dict:
        self._step(5, "执行与反馈")
        stages = {}

        print("     [ControlClient] 执行轨迹 traj_0...")
        time.sleep(0.08)

        # Simulate moving through waypoints
        waypoints = [
            (0.30, 0.00, 0.50), (0.35, 0.05, 0.30),
            (0.45, 0.08, 0.18), (0.50, 0.10, 0.12),
        ]
        for i, wp in enumerate(waypoints):
            progress = (i + 1) / len(waypoints) * 100
            bar = "▓" * (i + 1) + "░" * (len(waypoints) - i - 1)
            print(f"       [{bar}] waypoint {i+1}/{len(waypoints)} "
                  f"→ ({wp[0]:.2f}, {wp[1]:.2f}, {wp[2]:.2f})  [{progress:.0f}%]")

        # Gripper action
        if self.scenario["instruction"] and "检查" not in self.scenario["instruction"]:
            print("       [Gripper] Close → grip target object")
            print("       [Gripper] Move up → lifting phase")
            print("       [Gripper] Open → release object at handover")

        print("     [SafetyMonitor] Continuous collision check:")
        print("       ├─ t=0.5s: min distance=0.45m  [OK]")
        print("       ├─ t=1.2s: min distance=0.32m  [OK]")
        print("       └─ t=2.1s: min distance=0.38m  [OK]")

        stages["execution_ms"] = self.ts()
        self._ok(f"执行完成 ({stages['execution_ms']:.0f} ms)")
        return stages

    def stage_6_teardown(self) -> dict:
        self._step(6, "清理与报告")
        stages = {}

        print("     [WebSocket] Pushing final status to brain_viz...")
        print("       ├─ plan_status: SUCCEEDED")
        print("       ├─ ghost_trail: trajectory rendered")
        print("       └─ scene_update: final state broadcast")
        print("     Canceling plan...")
        print("       └─ plan_id released, resources freed")

        stages["teardown_ms"] = self.ts()
        self._ok(f"清理完成 ({stages['teardown_ms']:.0f} ms)")
        return stages

    # ── Mock data generators ───────────────────────────────

    def _generate_subtasks(self, intent: cog_types.Intent) -> list:
        """Generate realistic subtasks based on intent type."""
        intent_name = cog_types.IntentType.Name(intent.type)

        if intent_name == "INTENT_PICK":
            return [
                cog_types.SubTask(
                    task_id="st_01", skill_name="navigate_to_table",
                    depends_on=[], priority=1.0,
                ),
                cog_types.SubTask(
                    task_id="st_02", skill_name="detect_object",
                    depends_on=["st_01"], priority=0.9,
                ),
                cog_types.SubTask(
                    task_id="st_03", skill_name="plan_grasp",
                    depends_on=["st_02"], priority=0.85,
                ),
                cog_types.SubTask(
                    task_id="st_04", skill_name="pick_object",
                    depends_on=["st_03"], priority=0.8,
                ),
                cog_types.SubTask(
                    task_id="st_05", skill_name="place_at_handover",
                    depends_on=["st_04"], priority=0.7,
                ),
            ]
        elif intent_name == "INTENT_SEQUENCE":
            return [
                cog_types.SubTask(
                    task_id="st_01", skill_name="detect_boxes",
                    depends_on=[], priority=1.0,
                ),
                cog_types.SubTask(
                    task_id="st_02", skill_name="pick_box_1",
                    depends_on=["st_01"], priority=0.9,
                ),
                cog_types.SubTask(
                    task_id="st_03", skill_name="place_box_1_on_target",
                    depends_on=["st_02"], priority=0.8,
                ),
                cog_types.SubTask(
                    task_id="st_04", skill_name="pick_box_2",
                    depends_on=["st_03"], priority=0.7,
                ),
                cog_types.SubTask(
                    task_id="st_05", skill_name="stack_box_2_on_box_1",
                    depends_on=["st_04"], priority=0.6,
                ),
            ]
        elif intent_name == "INTENT_INSPECT":
            return [
                cog_types.SubTask(
                    task_id="st_01", skill_name="check_joint_limits",
                    depends_on=[], priority=1.0,
                ),
                cog_types.SubTask(
                    task_id="st_02", skill_name="scan_collision_volume",
                    depends_on=[], priority=0.9,
                ),
                cog_types.SubTask(
                    task_id="st_03", skill_name="verify_safety_zone",
                    depends_on=["st_01", "st_02"], priority=0.8,
                ),
                cog_types.SubTask(
                    task_id="st_04", skill_name="report_status",
                    depends_on=["st_03"], priority=0.7,
                ),
            ]
        else:  # INTENT_UNKNOWN
            return [
                cog_types.SubTask(
                    task_id="st_01", skill_name="request_clarification",
                    depends_on=[], priority=0.3,
                ),
            ]

    @staticmethod
    def _build_bt_xml(tree_id: str, subtasks: list) -> str:
        """Build a mock BehaviorTree XML."""
        lines = [
            '<?xml version="1.0"?>',
            '<root BTCPP_format="4">',
            f'  <BehaviorTree ID="{tree_id}">',
            '    <Sequence name="main_pipeline">',
        ]
        for st in subtasks:
            name = st.skill_name.replace("_", " ")
            params_str = f' target="{st.task_id}"'
            lines.append(f'      <{st.skill_name}{params_str}/>')
        lines.extend([
            '    </Sequence>',
            '  </BehaviorTree>',
            '</root>',
        ])
        return "\n".join(lines)

    # ── Main runner ────────────────────────────────────────

    def run(self) -> DemoReport:
        """Execute full demo pipeline and return report."""
        report = DemoReport(
            scenario=self.scenario["name"],
            instruction=self.scenario["instruction"],
            success=False,
            total_ms=0,
        )

        try:
            all_stages = {}

            # Stage 0: Startup
            all_stages.update(self.stage_0_startup())

            # Stage 1: Scene setup
            all_stages.update(self.stage_1_scene_setup())

            # Stage 2: Perception
            all_stages.update(self.stage_2_perception())

            # Stage 3: Cognition
            all_stages.update(self.stage_3_cognition(report))

            # Stage 4: Decision + HITL
            all_stages.update(self.stage_4_decision())

            # Stage 5: Execution
            all_stages.update(self.stage_5_execution())

            # Stage 6: Teardown
            all_stages.update(self.stage_6_teardown())

            report.stages = all_stages
            report.success = True

        except Exception as e:
            logger.exception("Demo pipeline error: %s", e)
            report.warnings.append(f"exception: {e}")

        report.total_ms = self.ts()

        # ── Final report ────────────────────────────────────
        self._banner("Demo Report", "=")
        status = "✅ SUCCESS" if report.success else "❌ FAILED"
        print(f"  Status     : {status}")
        print(f"  Scenario   : {report.scenario}")
        print(f"  Instruction: {report.instruction}")
        print(f"  Total time : {report.total_ms:.0f} ms")
        print(f"\n  Stage breakdown:")
        stage_order = [
            "startup_ms", "scene_setup_ms", "perception_ms",
            "parse_intent_ms", "decompose_ms", "generate_bt_ms",
            "generate_traj_ms", "hitl_select_ms",
            "execution_ms", "teardown_ms",
        ]
        stage_labels = {
            "startup_ms":       "系统初始化",
            "scene_setup_ms":   "场景初始化",
            "perception_ms":    "环境感知",
            "parse_intent_ms":  "意图解析",
            "decompose_ms":     "任务分解",
            "generate_bt_ms":   "行为树生成",
            "generate_traj_ms": "运动规划",
            "hitl_select_ms":   "HITL 确认",
            "execution_ms":     "轨迹执行",
            "teardown_ms":      "清理收尾",
        }

        for key in stage_order:
            if key in report.stages:
                label = stage_labels.get(key, key)
                ms = report.stages[key]
                bar_len = max(1, int(ms / max(1, report.total_ms) * 30))
                bar = "█" * min(bar_len, 30)
                print(f"    {label:<12s} {bar:<30s} {ms:8.1f} ms")

        if report.warnings:
            print(f"\n  Warnings ({len(report.warnings)}):")
            for w in report.warnings:
                print(f"    ⚠️  {w}")

        print(f"\n{'─' * 68}")
        print("  Demo complete. Generated output: brain_sim/demo_output/")
        print(f"{'─' * 68}\n")

        return report


# ── Entry point ────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Brain OS 端到端仿真 Demo")
    parser.add_argument(
        "--scenario", choices=list(SCENARIOS.keys()),
        default="pick_cup", help="演示场景 (default: pick_cup)",
    )
    parser.add_argument(
        "--no-timing", action="store_true",
        help="不显示详细计时",
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
        demo = E2EDemo(scenario=scenario, enable_timing=not args.no_timing)
        report = demo.run()
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
                "warnings": r.warnings,
            })
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        print(f"📄 Report saved to: {args.output}")

    return 0 if all(r.success for r in reports) else 1


if __name__ == "__main__":
    sys.exit(main())
