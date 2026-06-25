"""Brain OS SDK — 最小连接示例

演示最基本的连接、感知和认知流程。
"""

import asyncio
import sys
import os

# Add the SDK to path for development
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from brain_os import BrainOSClient, BrainOSConfig


async def main():
    """最小可运行示例 — 连接、感知场景、解析意图。"""

    # 初始化客户端 (使用默认配置 localhost:50051)
    config = BrainOSConfig.from_env()
    print(f"Connecting to Brain OS @ {config.grpc_address} ...")

    async with BrainOSClient(config) as robot:
        print(f"Connected. Robot ID: {config.robot_id}")

        # ── 步骤 1: 感知场景 ─────────────────────────────
        print("\n>>> 感知场景")
        scene = await robot.perception.get_scene(include_summary=True)
        print(f"  场景中有 {len(scene['objects'])} 个物体")
        for obj in scene["objects"]:
            print(f"    - {obj['class_label']} (confidence={obj['confidence']})")
        if scene.get("summary"):
            print(f"  摘要: {scene['summary']}")

        # ── 步骤 2: 查询特定目标 ─────────────────────────
        print("\n>>> 查询目标")
        cups = await robot.perception.query_objects("cup", min_conf=0.5)
        print(f"  找到 {len(cups)} 个杯子: {[c['object_id'] for c in cups]}")

        # ── 步骤 3: 解析意图 ─────────────────────────────
        print("\n>>> 解析意图")
        intent = await robot.cognition.parse_intent("把桌上的红色杯子放到厨房柜子上")
        print(f"  意图类型: {intent['type']}")
        print(f"  置信度: {intent['confidence']}")
        print(f"  参数: {intent['params']}")

        # ── 步骤 4: 检查安全状态 ─────────────────────────
        print("\n>>> 安全状态")
        safety = await robot.safety.get_snapshot()
        print(f"  状态: {safety['state']}")
        print(f"  速度缩放: {safety['velocity_scale']}")
        print(f"  最近障碍物距离: {safety['min_obstacle_dist']}m")

        # ── 步骤 5: 语音播报 ─────────────────────────────
        print("\n>>> 语音播报")
        await robot.speech.say("初始化完成，随时待命")

        print("\n✓ 示例完成!")


if __name__ == "__main__":
    asyncio.run(main())
