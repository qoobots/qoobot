"""brain_os SDK — HITL 模式演示"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from brain_os.client import BrainOSClient
from brain_os.config import BrainOSConfig


async def hitl_demo():
    """
    演示 HITL（人在回路）轨迹选择流程：
    1. 解析指令
    2. 生成行为树
    3. 发起执行（触发 HITL）
    4. 展示候选轨迹
    5. 人类选择（模拟）
    6. 继续执行
    """
    config = BrainOSConfig(robot_id="demo_robot", hitl_timeout_sec=3.0)
    client = BrainOSClient(config)

    print("=== HITL 模式演示 ===\n")
    utterance = "把桌上的红色杯子移到架子上"
    print(f"📢 指令: {utterance!r}\n")

    # 1. 意图解析
    intent = await client.cognition.parse_intent(utterance)
    print(f"✅ 意图: {intent['type']}")

    # 2. 任务分解
    plan = await client.cognition.decompose_task(intent)
    print(f"✅ 计划: {len(plan['subtasks'])} 步")

    # 3. 生成行为树
    bt = await client.cognition.generate_behavior_tree(plan["plan_id"], plan["subtasks"])
    print(f"✅ 行为树: {bt['tree_id']}")

    # 4. 发起执行（require_hitl=True）
    result = await client.decision.execute_plan(bt, require_hitl=True)
    print(f"\n状态: {result['state']}")

    # 5. 展示候选轨迹
    if result.get("hitl_event"):
        hitl = result["hitl_event"]
        print(f"\n⏱️ 请在 {hitl['timeout_sec']:.1f}s 内选择轨迹:\n")
        for i, traj in enumerate(hitl["candidates"]):
            marker = "★" if traj["is_recommended"] else " "
            print(
                f"  [{i+1}] {marker} {traj['description']}"
                f"  (得分: {traj['score']:.2f}, 时长: {traj.get('duration_sec', '?')}s)"
            )

        # 6. 模拟选择（选第 2 条）
        selected_id = hitl["candidates"][1]["trajectory_id"]
        print(f"\n👤 用户选择: 轨迹 2 ({selected_id})")
        sel_result = await client.decision.select_trajectory(hitl["plan_id"], selected_id)
        print(f"✅ 确认: {sel_result['selected']}")

    client.close()
    print("\n✅ HITL 演示完成")


if __name__ == "__main__":
    asyncio.run(hitl_demo())
