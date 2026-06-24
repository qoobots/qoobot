"""SDK 客户端测试 — BrainOSClient 初始化、命名空间、上下文管理器。"""

import sys
import os
import asyncio
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "brain_sdk"))

from brain_os import BrainOSClient, BrainOSConfig, BrainOSError


class TestBrainOSConfig(unittest.TestCase):
    """配置管理测试。"""

    def test_default_config(self):
        config = BrainOSConfig()
        self.assertEqual(config.grpc_host, "localhost")
        self.assertEqual(config.grpc_port, 50051)
        self.assertEqual(config.robot_id, "robot_01")
        self.assertEqual(config.grpc_address, "localhost:50051")

    def test_custom_config(self):
        config = BrainOSConfig(
            grpc_host="192.168.1.100",
            grpc_port=9090,
            robot_id="test_bot",
            grpc_timeout_sec=30.0,
        )
        self.assertEqual(config.grpc_host, "192.168.1.100")
        self.assertEqual(config.grpc_address, "192.168.1.100:9090")
        self.assertEqual(config.robot_id, "test_bot")
        self.assertEqual(config.grpc_timeout_sec, 30.0)

    def test_from_env(self):
        config = BrainOSConfig.from_env()
        self.assertIsInstance(config, BrainOSConfig)

    def test_tls_config(self):
        config = BrainOSConfig(tls_enabled=True, tls_cert_path="/tmp/cert.pem")
        self.assertTrue(config.tls_enabled)
        self.assertEqual(config.tls_cert_path, "/tmp/cert.pem")


class TestBrainOSClient(unittest.TestCase):
    """客户端初始化与接口测试。"""

    def test_client_init(self):
        client = BrainOSClient()
        self.assertIsNotNone(client.config)
        self.assertEqual(client.config.robot_id, "robot_01")
        client.close()

    def test_client_custom_config(self):
        config = BrainOSConfig(robot_id="my_robot", grpc_host="10.0.0.1")
        client = BrainOSClient(config)
        self.assertEqual(client.config.robot_id, "my_robot")
        client.close()

    def test_client_repr(self):
        client = BrainOSClient()
        r = repr(client)
        self.assertIn("BrainOSClient", r)
        self.assertIn("localhost", r)
        client.close()

    def test_client_config_property(self):
        client = BrainOSClient()
        self.assertIsInstance(client.config, BrainOSConfig)
        client.close()


class TestNamespaces(unittest.TestCase):
    """命名空间接口存在性测试。"""

    def setUp(self):
        self.client = BrainOSClient()

    def tearDown(self):
        self.client.close()

    def test_cognition_namespace(self):
        ns = self.client.cognition
        self.assertTrue(callable(ns.parse_intent))
        self.assertTrue(callable(ns.decompose_task))
        self.assertTrue(callable(ns.generate_behavior_tree))

    def test_decision_namespace(self):
        ns = self.client.decision
        self.assertTrue(callable(ns.execute_plan))
        self.assertTrue(callable(ns.generate_trajectories))
        self.assertTrue(callable(ns.select_trajectory))
        self.assertTrue(callable(ns.cancel_plan))

    def test_perception_namespace(self):
        ns = self.client.perception
        self.assertTrue(callable(ns.get_scene))
        self.assertTrue(callable(ns.query_objects))
        self.assertTrue(callable(ns.get_localization))

    def test_control_namespace(self):
        ns = self.client.control
        self.assertTrue(callable(ns.execute_trajectory))
        self.assertTrue(callable(ns.emergency_stop))
        self.assertTrue(callable(ns.open_gripper))
        self.assertTrue(callable(ns.close_gripper))
        self.assertTrue(callable(ns.move_joints))
        self.assertTrue(callable(ns.move_to_pose))
        self.assertTrue(callable(ns.get_state))

    def test_safety_namespace(self):
        ns = self.client.safety
        self.assertTrue(callable(ns.get_snapshot))
        self.assertTrue(callable(ns.set_velocity_scale))

    def test_knowledge_namespace(self):
        ns = self.client.knowledge
        self.assertTrue(callable(ns.search))
        self.assertTrue(callable(ns.search_episodes))
        self.assertTrue(callable(ns.store_episode))

    def test_speech_namespace(self):
        ns = self.client.speech
        self.assertTrue(callable(ns.recognize_speech))
        self.assertTrue(callable(ns.synthesize_speech))
        self.assertTrue(callable(ns.say))
        self.assertTrue(callable(ns.voice_command))
        self.assertTrue(callable(ns.listen_for_wake_word))

    def test_control_direct_property(self):
        direct = self.client.control.direct
        self.assertIsNotNone(direct)
        self.assertTrue(callable(direct.move_joints))
        self.assertTrue(callable(direct.move_to_pose))
        self.assertTrue(callable(direct.get_state))


class TestCognitionAPI(unittest.TestCase):
    """认知 API Mock 模式测试。"""

    def test_parse_intent_mock(self):
        """Mock 模式下意图解析返回预期结构。"""
        async def _test():
            client = BrainOSClient()
            intent = await client.cognition.parse_intent("打开红色杯子")
            client.close()
            self.assertIn("type", intent)
            self.assertIn("confidence", intent)
            self.assertIn("raw_text", intent)
            self.assertTrue(intent["_stub"])
            return intent

        result = asyncio.run(_test())
        self.assertEqual(result["type"], "PICK")

    def test_decompose_task_mock(self):
        """Mock 模式下任务分解返回子任务列表。"""
        async def _test():
            client = BrainOSClient()
            result = await client.cognition.decompose_task({"type": "PICK"})
            client.close()
            self.assertIn("plan_id", result)
            self.assertIn("subtasks", result)
            self.assertIn("rationale", result)
            self.assertTrue(len(result["subtasks"]) >= 1)
            self.assertTrue(result["_stub"])
            return result

        result = asyncio.run(_test())
        self.assertGreater(len(result["subtasks"]), 0)

    def test_generate_behavior_tree_mock(self):
        """Mock 模式下行为树生成返回 XML。"""
        async def _test():
            client = BrainOSClient()
            bt = await client.cognition.generate_behavior_tree("plan_01", [])
            client.close()
            self.assertIn("tree_id", bt)
            self.assertIn("xml_str", bt)
            self.assertIn("BTCPP_format", bt["xml_str"])
            self.assertTrue(bt["_stub"])
            return bt

        bt = asyncio.run(_test())
        self.assertIn("BehaviorTree", bt["xml_str"])


class TestPerceptionAPI(unittest.TestCase):
    """感知 API Mock 模式测试。"""

    def test_get_scene_mock(self):
        async def _test():
            client = BrainOSClient()
            scene = await client.perception.get_scene(include_summary=True)
            client.close()
            self.assertIn("objects", scene)
            self.assertIn("relations", scene)
            self.assertIn("summary", scene)
            self.assertTrue(scene["_stub"])
            self.assertGreater(len(scene["objects"]), 0)
            return scene

        scene = asyncio.run(_test())
        self.assertIn("cup", [o["class_label"] for o in scene["objects"]])

    def test_query_objects_mock(self):
        async def _test():
            client = BrainOSClient()
            objects = await client.perception.query_objects("cup", min_conf=0.5)
            client.close()
            self.assertGreater(len(objects), 0)
            for o in objects:
                self.assertEqual(o["class_label"], "cup")
                self.assertTrue(o["_stub"])
            return objects

        objects = asyncio.run(_test())
        self.assertGreater(len(objects), 0)

    def test_query_objects_filter_confidence(self):
        async def _test():
            client = BrainOSClient()
            objects = await client.perception.query_objects("cup", min_conf=0.95)
            client.close()
            for o in objects:
                self.assertGreaterEqual(o["confidence"], 0.95)
            return objects

        asyncio.run(_test())

    def test_get_localization_mock(self):
        async def _test():
            client = BrainOSClient()
            loc = await client.perception.get_localization()
            client.close()
            self.assertIn("pose", loc)
            self.assertTrue(loc["_stub"])
            return loc

        loc = asyncio.run(_test())
        self.assertIn("position", loc["pose"])


class TestTypes(unittest.TestCase):
    """数据类型实例化测试。"""

    def test_vector3(self):
        from brain_os.types import Vector3, Quaternion, Pose
        v = Vector3(x=1.0, y=2.0, z=3.0)
        self.assertEqual(v.x, 1.0)
        p = Pose(position=v, orientation=Quaternion(x=0, y=0, z=0, w=1))
        self.assertIsNotNone(p.position)

    def test_scene_graph(self):
        from brain_os.types import SceneGraph, Object3D, SemanticLabel
        g = SceneGraph()
        self.assertEqual(len(g.objects), 0)
        obj = Object3D(label=SemanticLabel(category="cup", confidence=0.9))
        g.objects.append(obj)
        self.assertEqual(len(g.objects), 1)

    def test_plan_types(self):
        from brain_os.types import Plan, BehaviorTreeNode, BehaviorTree, HITLOption
        node = BehaviorTreeNode(id="n1", type="Action", name="Pick")
        self.assertEqual(node.name, "Pick")
        opt = HITLOption(option_id="h1", score=85.0)
        self.assertEqual(opt.score, 85.0)

    def test_task_types(self):
        from brain_os.types import SubTask, SkillDefinition, TaskDAG
        st = SubTask(skill_name="Pick", parameters={"target": "cup"})
        self.assertEqual(st.skill_name, "Pick")
        dag = TaskDAG(subtasks=[st])
        self.assertEqual(len(dag.subtasks), 1)

    def test_motion_types(self):
        from brain_os.types import JointState, JointLimits, MotionCommand
        limits = JointLimits(lower=-3.14, upper=3.14, max_velocity=2.0)
        js = JointState(name="joint_1", position=0.5, limits=limits)
        self.assertEqual(js.name, "joint_1")
        self.assertEqual(js.limits.max_velocity, 2.0)

    def test_enums(self):
        from brain_os.types import IntentType, TaskStatus, AlarmLevel
        self.assertIsNotNone(IntentType.PICK)
        self.assertIsNotNone(TaskStatus.PENDING)
        self.assertIsNotNone(AlarmLevel.S0_CRITICAL)


class TestUtils(unittest.TestCase):
    """工具模块测试。"""

    def test_errors(self):
        from brain_os import (
            BrainOSError, ConnectionError, TimeoutError,
            RobotNotReadyError, InvalidRequestError,
        )
        # All are Exception subclasses
        for cls in [BrainOSError, ConnectionError, TimeoutError,
                     RobotNotReadyError, InvalidRequestError]:
            self.assertTrue(issubclass(cls, Exception))

    def test_async_helpers(self):
        from brain_os import with_timeout, retry, collect_stream
        self.assertTrue(callable(with_timeout))
        self.assertTrue(callable(retry))
        self.assertTrue(callable(collect_stream))

    def test_retry_decorator(self):
        """重试函数在最终失败时抛出异常。"""
        from brain_os import retry, BrainOSError

        async def _test():
            call_count = [0]

            async def failing():
                call_count[0] += 1
                raise BrainOSError("always fails")

            with self.assertRaises(BrainOSError):
                await retry(
                    failing, max_attempts=3, delay_sec=0.01,
                    exceptions=(BrainOSError,)
                )
            self.assertEqual(call_count[0], 3)

        asyncio.run(_test())

    def test_with_timeout(self):
        """超时包装在超时时抛出异常。"""
        from brain_os import with_timeout

        async def _test():
            async def slow():
                await asyncio.sleep(0.5)
                return "done"

            with self.assertRaises(asyncio.TimeoutError):
                await with_timeout(slow(), 0.05)

        asyncio.run(_test())


if __name__ == "__main__":
    unittest.main()
