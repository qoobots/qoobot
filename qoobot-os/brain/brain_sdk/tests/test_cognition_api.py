"""SDK 认知模块测试 — 意图解析 + 任务分解 + 行为树。"""

import sys
import os
import asyncio
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "brain_sdk"))


class TestIntentAPI(unittest.TestCase):
    """意图解析 API 测试。"""

    def test_parse_pick_command(self):
        async def _test():
            from brain_os import BrainOSClient
            client = BrainOSClient()
            result = await client.cognition.parse_intent("拿起红色杯子")
            client.close()
            self.assertEqual(result["type"], "PICK")
            self.assertGreater(result["confidence"], 0.5)
            self.assertTrue(result["_stub"])

        asyncio.run(_test())

    def test_parse_place_command(self):
        async def _test():
            from brain_os import BrainOSClient
            client = BrainOSClient()
            result = await client.cognition.parse_intent("把瓶子放到桌上")
            client.close()
            self.assertIsNotNone(result["type"])
            self.assertEqual(result["raw_text"], "把瓶子放到桌上")

        asyncio.run(_test())

    def test_parse_with_language(self):
        async def _test():
            from brain_os import BrainOSClient
            client = BrainOSClient()
            result = await client.cognition.parse_intent("grab the red cup", language="en-US")
            client.close()
            self.assertIn("language", result)
            self.assertEqual(result["raw_text"], "grab the red cup")

        asyncio.run(_test())

    def test_parse_empty_utterance(self):
        async def _test():
            from brain_os import BrainOSClient
            client = BrainOSClient()
            result = await client.cognition.parse_intent("")
            client.close()
            self.assertIn("type", result)
            self.assertTrue(result["_stub"])

        asyncio.run(_test())


class TestTaskAPI(unittest.TestCase):
    """任务分解与行为树 API 测试。"""

    def test_decompose_basic(self):
        async def _test():
            from brain_os import BrainOSClient
            client = BrainOSClient()
            intent = {"type": "PICK", "confidence": 0.9, "params": {"object": "cup"}}
            result = await client.cognition.decompose_task(intent)
            client.close()
            self.assertIn("plan_id", result)
            self.assertIsInstance(result["subtasks"], list)
            self.assertGreater(len(result["subtasks"]), 0)
            # 验证子任务结构
            for st in result["subtasks"]:
                self.assertIn("task_id", st)
                self.assertIn("skill_name", st)
                self.assertIn("parameters", st)
                self.assertIn("depends_on", st)

        asyncio.run(_test())

    def test_decompose_with_scene(self):
        async def _test():
            from brain_os import BrainOSClient
            client = BrainOSClient()
            intent = {"type": "PICK_AND_PLACE", "confidence": 0.85}
            scene = {
                "objects": [{"object_id": "o1", "class_label": "cup"}],
                "relations": [],
            }
            result = await client.cognition.decompose_task(intent, scene_graph=scene)
            client.close()
            self.assertTrue(result["_stub"])

        asyncio.run(_test())

    def test_generate_bt_valid_xml(self):
        async def _test():
            from brain_os import BrainOSClient
            client = BrainOSClient()
            subtasks = [
                {"task_id": "st_01", "skill_name": "NavigateTo", "parameters": {}, "depends_on": []},
                {"task_id": "st_02", "skill_name": "Pick", "parameters": {"target": "cup"}, "depends_on": ["st_01"]},
            ]
            bt = await client.cognition.generate_behavior_tree("plan_test", subtasks)
            client.close()
            # 验证 XML 基本结构
            self.assertIn("BTCPP_format", bt["xml_str"])
            self.assertIn("BehaviorTree", bt["xml_str"])
            self.assertIn("NavigateTo", bt["xml_str"])
            self.assertIn("Pick", bt["xml_str"])

        asyncio.run(_test())

    def test_generate_bt_tree_id(self):
        async def _test():
            from brain_os import BrainOSClient
            client = BrainOSClient()
            bt = await client.cognition.generate_behavior_tree("plan_abc123", [])
            client.close()
            self.assertEqual(bt["tree_id"], "bt_plan_abc123")

        asyncio.run(_test())


class TestSceneAPI(unittest.TestCase):
    """场景 API 测试。"""

    def test_get_scene_structure(self):
        async def _test():
            from brain_os import BrainOSClient
            client = BrainOSClient()
            scene = await client.perception.get_scene()
            client.close()
            self.assertIsInstance(scene["objects"], list)
            for obj in scene["objects"]:
                self.assertIn("object_id", obj)
                self.assertIn("class_label", obj)
                self.assertIn("confidence", obj)

        asyncio.run(_test())

    def test_query_all_objects(self):
        async def _test():
            from brain_os import BrainOSClient
            client = BrainOSClient()
            objects = await client.perception.query_objects()
            client.close()
            self.assertIsInstance(objects, list)
            self.assertGreater(len(objects), 0)

        asyncio.run(_test())

    def test_query_filter_confidence(self):
        async def _test():
            from brain_os import BrainOSClient
            client = BrainOSClient()
            all_objects = await client.perception.query_objects(min_conf=0.0)
            strict_objects = await client.perception.query_objects(min_conf=0.95)
            client.close()
            self.assertGreaterEqual(len(all_objects), len(strict_objects))

        asyncio.run(_test())

    def test_get_localization_pose(self):
        async def _test():
            from brain_os import BrainOSClient
            client = BrainOSClient()
            loc = await client.perception.get_localization()
            client.close()
            self.assertIn("position", loc["pose"])
            self.assertIn("orientation", loc["pose"])
            self.assertIn("x", loc["pose"]["position"])
            self.assertIn("w", loc["pose"]["orientation"])

        asyncio.run(_test())


class TestDecisionAPI(unittest.TestCase):
    """决策 API 测试。"""

    def test_execute_plan_with_hitl(self):
        async def _test():
            from brain_os import BrainOSClient
            client = BrainOSClient()
            tree = {"tree_id": "bt_test", "xml_str": "<root></root>"}
            result = await client.decision.execute_plan(tree, require_hitl=True)
            client.close()
            self.assertEqual(result["state"], "WAITING_HITL")
            self.assertIsNotNone(result["hitl_event"])
            self.assertIn("candidates", result["hitl_event"])
            self.assertGreaterEqual(len(result["hitl_event"]["candidates"]), 1)

        asyncio.run(_test())

    def test_execute_plan_without_hitl(self):
        async def _test():
            from brain_os import BrainOSClient
            client = BrainOSClient()
            tree = {"tree_id": "bt_test", "xml_str": "<root></root>"}
            result = await client.decision.execute_plan(tree, require_hitl=False)
            client.close()
            self.assertEqual(result["state"], "EXECUTING")

        asyncio.run(_test())

    def test_cancel_plan(self):
        async def _test():
            from brain_os import BrainOSClient
            client = BrainOSClient()
            result = await client.decision.cancel_plan("plan_123", reason="user abort")
            client.close()
            self.assertTrue(result["ok"])

        asyncio.run(_test())


class TestControlAPI(unittest.TestCase):
    """控制 API 测试。"""

    def test_emergency_stop(self):
        async def _test():
            from brain_os import BrainOSClient
            client = BrainOSClient()
            result = await client.control.emergency_stop(reason="test", level=0)
            client.close()
            self.assertTrue(result["ok"])
            self.assertTrue(result["_stub"])

        asyncio.run(_test())

    def test_gripper_open_close(self):
        async def _test():
            from brain_os import BrainOSClient
            client = BrainOSClient()
            open_result = await client.control.open_gripper()
            close_result = await client.control.close_gripper()
            client.close()
            self.assertTrue(open_result["ok"])
            self.assertTrue(close_result["ok"])

        asyncio.run(_test())


class TestSafetyAPI(unittest.TestCase):
    """安全 API 测试。"""

    def test_get_snapshot(self):
        async def _test():
            from brain_os import BrainOSClient
            client = BrainOSClient()
            snap = await client.safety.get_snapshot()
            client.close()
            self.assertIn("state", snap)
            self.assertIn("active_alarms", snap)
            self.assertIn("velocity_scale", snap)
            self.assertIn("min_obstacle_dist", snap)
            self.assertEqual(snap["state"], "NORMAL")

        asyncio.run(_test())

    def test_set_velocity_scale(self):
        async def _test():
            from brain_os import BrainOSClient
            client = BrainOSClient()
            # Normal
            result = await client.safety.set_velocity_scale(0.5, reason="test")
            client.close()
            self.assertTrue(result["ok"])
            self.assertEqual(result["applied_scale"], 0.5)

        asyncio.run(_test())


class TestKnowledgeAPI(unittest.TestCase):
    """知识 API 测试。"""

    def test_search_knowledge(self):
        async def _test():
            from brain_os import BrainOSClient
            client = BrainOSClient()
            results = await client.knowledge.search("how to pick glass")
            client.close()
            self.assertIsInstance(results, list)
            self.assertGreater(len(results), 0)
            self.assertIn("entry_id", results[0])

        asyncio.run(_test())

    def test_store_episode(self):
        async def _test():
            from brain_os import BrainOSClient
            client = BrainOSClient()
            eid = await client.knowledge.store_episode({"task_type": "pick", "success": True})
            client.close()
            self.assertIsInstance(eid, str)
            self.assertGreater(len(eid), 0)

        asyncio.run(_test())


class TestSpeechAPI(unittest.TestCase):
    """语音 API 测试。"""

    def test_synthesize_speech(self):
        async def _test():
            from brain_os import BrainOSClient
            client = BrainOSClient()
            audio = await client.speech.synthesize_speech("你好世界")
            client.close()
            self.assertIsNotNone(audio)

        asyncio.run(_test())

    def test_listen_wake_word(self):
        async def _test():
            from brain_os import BrainOSClient
            client = BrainOSClient()
            detected = await client.speech.listen_for_wake_word(timeout_sec=1.0)
            client.close()
            self.assertIsInstance(detected, bool)

        asyncio.run(_test())


if __name__ == "__main__":
    unittest.main()
