"""SDK 场景与直接控制 API 测试。"""

import sys
import os
import asyncio
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "brain_sdk"))


class TestDirectController(unittest.TestCase):
    """直接控制器测试。"""

    def test_get_state(self):
        async def _test():
            from brain_os import BrainOSClient
            client = BrainOSClient()
            state = await client.control.get_state()
            client.close()
            self.assertIsNotNone(state.joints)
            self.assertIsNotNone(state.ee_pose)
            self.assertEqual(state.motion_status.value, "idle")
            self.assertFalse(state.is_emergency_stopped)
            self.assertGreater(len(state.joints), 0)

        asyncio.run(_test())

    def test_move_joints(self):
        async def _test():
            from brain_os import BrainOSClient
            client = BrainOSClient()
            success = await client.control.move_joints(
                {"joint_1": 0.5, "joint_2": -0.3},
                velocity_scale=0.3,
                timeout_sec=1.0,
            )
            client.close()
            self.assertTrue(success)

        asyncio.run(_test())

    def test_move_to_pose(self):
        async def _test():
            from brain_os import BrainOSClient
            from brain_os.control.direct_control import CartesianPose
            client = BrainOSClient()
            pose = CartesianPose(x=0.5, y=0.1, z=0.8)
            success = await client.control.move_to_pose(pose, velocity_scale=0.5)
            client.close()
            self.assertTrue(success)

        asyncio.run(_test())

    def test_get_joint_state(self):
        async def _test():
            from brain_os import BrainOSClient
            client = BrainOSClient()
            state = await client.control.direct.get_joint_state("joint_1")
            client.close()
            if state is not None:
                self.assertEqual(state.name, "joint_1")

        asyncio.run(_test())

    def test_get_ee_pose(self):
        async def _test():
            from brain_os import BrainOSClient
            client = BrainOSClient()
            pose = await client.control.direct.get_ee_pose()
            client.close()
            self.assertIsNotNone(pose)

        asyncio.run(_test())


class TestCartesianPose(unittest.TestCase):
    """位姿测试。"""

    def test_to_pose(self):
        from brain_os.control.direct_control import CartesianPose
        cp = CartesianPose(x=1.0, y=2.0, z=3.0, roll=0.1, pitch=0.2, yaw=0.3)
        pose = cp.to_pose()
        self.assertEqual(pose.position.x, 1.0)
        self.assertEqual(pose.position.y, 2.0)
        self.assertEqual(pose.position.z, 3.0)


class TestRobotState(unittest.TestCase):
    """机器人状态测试。"""

    def test_default_state(self):
        from brain_os.control.direct_control import RobotState
        state = RobotState()
        self.assertEqual(len(state.joints), 0)
        self.assertIsNone(state.ee_pose)
        self.assertFalse(state.is_emergency_stopped)


class TestStreamPlanStatus(unittest.TestCase):
    """流式状态测试。"""

    def test_stream_status_yields(self):
        async def _test():
            from brain_os import BrainOSClient
            client = BrainOSClient()
            updates = []
            async for update in client.decision._plan.stream_status("plan_test"):
                updates.append(update)
            client.close()
            self.assertGreater(len(updates), 0)
            # 最后一个状态应该是 SUCCEEDED
            self.assertEqual(updates[-1]["state"], "SUCCEEDED")
            self.assertAlmostEqual(updates[-1]["progress"], 1.0)

        asyncio.run(_test())


class TestMockFallback(unittest.TestCase):
    """Mock fallback 一致性测试。"""

    def test_all_api_stub_marker(self):
        """所有 mock 响应都应携带 _stub: True 标记。"""
        async def _test():
            from brain_os import BrainOSClient
            client = BrainOSClient()

            # 认知
            intent = await client.cognition.parse_intent("test")
            self.assertTrue(intent["_stub"])

            plan = await client.cognition.decompose_task({"type": "TEST"})
            self.assertTrue(plan["_stub"])

            bt = await client.cognition.generate_behavior_tree("p1", [])
            self.assertTrue(bt["_stub"])

            # 决策
            exec_result = await client.decision.execute_plan(bt, require_hitl=True)
            self.assertTrue(exec_result["_stub"])

            cancel = await client.decision.cancel_plan("p1")
            self.assertTrue(cancel["_stub"])

            # 感知
            scene = await client.perception.get_scene()
            self.assertTrue(scene["_stub"])

            loc = await client.perception.get_localization()
            self.assertTrue(loc["_stub"])

            # 安全
            snap = await client.safety.get_snapshot()
            self.assertTrue(snap["_stub"])

            # 知识
            results = await client.knowledge.search("test")
            self.assertTrue(results[0]["_stub"])

            client.close()

        asyncio.run(_test())

    def test_context_manager(self):
        """BrainOSClient 支持上下文管理器。"""
        from brain_os import BrainOSClient
        with BrainOSClient() as client:
            self.assertIsNotNone(client.config)
        # After __exit__, client should be cleaned


if __name__ == "__main__":
    unittest.main()
