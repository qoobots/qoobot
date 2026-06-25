"""Brain OS SDK — 端到端任务执行示例

演示完整的 pick-and-place 任务流程：
自然语言指令 → 意图解析 → 场景感知 → 任务分解 → 行为树 → HITL → 轨迹执行
"""

import asyncio
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from brain_os import BrainOSClient


async def main():
    """端到端 pick-and-place 任务。"""

    async with BrainOSClient() as robot:
        start_ms = int(time.time() * 1000)

        # ── 阶段 1: 语音指令 → 意图解析 ──────────────────
        print("=" * 60)
        print("阶段 1: 意图解析")
        intent = await robot.cognition.parse_intent("把红色杯子放到桌上")
        print(f"  指令: 把红色杯子放到桌上")
        print(f"  意图: {intent['type']} (置信度: {intent['confidence']})")
        assert intent["type"] != "UNKNOWN", "意图解析失败"

        # ── 阶段 2: 场景感知 ─────────────────────────────
        print("\n阶段 2: 场景感知")
        scene = await robot.perception.get_scene(include_summary=True)
        targets = await robot.perception.query_objects("cup")
        print(f"  场景物体: {[o['class_label'] for o in scene['objects']]}")
        print(f"  目标物体: {len(targets)} 个杯子")
        target_pose = {"position": {"x": 0.5, "y": 0.2, "z": 0.8}}
        print(f"  目标位姿: {target_pose}")

        # ── 阶段 3: 任务分解 ─────────────────────────────
        print("\n阶段 3: 任务分解")
        plan = await robot.cognition.decompose_task(intent, scene_graph=scene)
        print(f"  计划 ID: {plan['plan_id']}")
        print(f"  推理链: {plan['rationale']}")
        print(f"  子任务数: {len(plan['subtasks'])}")
        for st in plan["subtasks"]:
            deps = st.get("depends_on", [])
            dep_str = f" (依赖: {deps})" if deps else ""
            print(f"    [{st['task_id']}] {st['skill_name']}{dep_str}")

        # ── 阶段 4: 行为树生成 ───────────────────────────
        print("\n阶段 4: 行为树生成")
        tree = await robot.cognition.generate_behavior_tree(
            plan["plan_id"], plan["subtasks"]
        )
        print(f"  行为树 ID: {tree['tree_id']}")
        # Show first 200 chars of XML
        xml_preview = tree["xml_str"].split("\n")[:5]
        for line in xml_preview:
            print(f"  {line}")
        print(f"  ... (共 {len(tree['xml_str'])} 字符)")

        # ── 阶段 5: HITL 人机协同 ─────────────────────────
        print("\n阶段 5: 执行规划 (HITL)")
        result = await robot.decision.execute_plan(tree, require_hitl=True)
        print(f"  状态: {result['state']}")
        if result.get("hitl_event"):
            hitl = result["hitl_event"]
            print(f"  HITL 触发! {len(hitl['candidates'])} 条候选轨迹:")
            for c in hitl["candidates"]:
                marker = " ★推荐" if c["is_recommended"] else ""
                print(f"    [{c['trajectory_id']}] {c['description']} (评分: {c['score']:.2f}){marker}")

            # 生成完整轨迹
            trajs = await robot.decision.generate_trajectories(result["plan_id"], target_pose)
            best = trajs[0] if trajs[0]["is_recommended"] else max(trajs, key=lambda t: t["score"])
            print(f"\n  选择推荐轨迹: {best['trajectory_id']} ({best['description']})")
            select_result = await robot.decision.select_trajectory(
                result["plan_id"], best["trajectory_id"]
            )
            print(f"  选择结果: {'成功' if select_result['ok'] else '失败'}")

        # ── 阶段 6: 安全监控 + 执行 ───────────────────────
        print("\n阶段 6: 安全监控与执行")
        safety = await robot.safety.get_snapshot()
        print(f"  安全状态: {safety['state']}")
        print(f"  速度缩放: {safety['velocity_scale']}")

        if safety["state"] == "NORMAL":
            print("  开夹爪...")
            await robot.control.open_gripper()
            print("  关闭夹爪...")
            await robot.control.close_gripper(max_effort=15.0)

        # ── 阶段 7: 存储情景记忆 ──────────────────────────
        print("\n阶段 7: 存储情景记忆")
        episode_id = await robot.knowledge.store_episode({
            "task_type": intent["type"],
            "plan_id": plan["plan_id"],
            "success": True,
            "duration_sec": (int(time.time() * 1000) - start_ms) / 1000.0,
            "objects": [t["class_label"] for t in targets],
        })
        print(f"  情景已存储: episode_id={episode_id}")

        # ── 阶段 8: 语音反馈 ─────────────────────────────
        print("\n阶段 8: 语音反馈")
        await robot.speech.say("任务完成，杯子已放到桌上")

        # ── 总结 ──────────────────────────────────────────
        elapsed = (int(time.time() * 1000) - start_ms) / 1000.0
        print(f"\n{'=' * 60}")
        print(f"✓ 端到端任务完成! 总耗时: {elapsed:.2f}s")
        print(f"  Mock模式: {bool(intent.get('_stub', False))}")


if __name__ == "__main__":
    asyncio.run(main())
