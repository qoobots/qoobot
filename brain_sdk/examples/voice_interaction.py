"""brain_os SDK — Python 语音交互示例"""

import asyncio
import sys
import os

# 将 brain_sdk 加入路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from brain_os.client import BrainOSClient
from brain_os.config import BrainOSConfig


async def voice_interaction_demo():
    """
    演示：语音指令 → 意图解析 → 任务分解 → 执行
    """
    config = BrainOSConfig(robot_id="demo_robot")
    client = BrainOSClient(config)

    utterances = [
        "把红色杯子放到桌子右边",
        "导航到厨房",
        "检查货架上的物品",
    ]

    print("=== Brain OS 语音交互演示 ===\n")

    for text in utterances:
        print(f"📢 指令: {text!r}")

        # 1. 解析意图
        intent = await client.cognition.parse_intent(text)
        print(f"   意图类型: {intent['type']} (置信度: {intent['confidence']:.2f})")

        # 2. 获取场景图
        scene = await client.perception.get_scene(include_summary=True)
        if scene.get("summary"):
            print(f"   场景摘要: {scene['summary']}")

        # 3. 分解任务
        plan = await client.cognition.decompose_task(intent)
        print(f"   计划 ID: {plan['plan_id']} ({len(plan['subtasks'])} 步)")

        print()

    client.close()
    print("✅ 演示完成")


if __name__ == "__main__":
    asyncio.run(voice_interaction_demo())
