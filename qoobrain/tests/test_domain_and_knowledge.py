"""
tests/test_domain_and_knowledge.py — Unit tests for domain models and knowledge modules.
"""
from __future__ import annotations

import sys, os
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "brain_ai"))

import time
import unittest


# ────────────────────────────────────────────────────────────────────────────
class TestDomainModels(unittest.TestCase):

    def test_task_lifecycle(self):
        from brain_ai.domain.task import RobotTask, TaskStatus
        t = RobotTask(raw_instruction="拿起红色杯子")
        self.assertEqual(t.status, TaskStatus.PENDING)
        t.start()
        self.assertEqual(t.status, TaskStatus.PLANNING)
        t.execute()
        self.assertEqual(t.status, TaskStatus.EXECUTING)
        t.complete()
        self.assertEqual(t.status, TaskStatus.COMPLETED)
        self.assertTrue(t.is_terminal)
        print(f"  ✅ Task lifecycle: {t.to_dict()['status']}")

    def test_plan_bt_xml(self):
        from brain_ai.domain.plan import ExecutionPlan, BehaviorTree, SkillNode
        tree = BehaviorTree(task_id="t1")
        root = SkillNode(node_type="sequence", skill_name="main")
        root.children.append(SkillNode(node_type="action", skill_name="pick_object",
                                        parameters={"label": "red_cup"}))
        tree.root = root
        xml = tree.to_xml()
        self.assertIn("<BehaviorTree>", xml)
        self.assertIn("pick_object", xml)
        print(f"  ✅ BehaviorTree XML:\n{xml[:120]}")

    def test_scene_graph(self):
        from brain_ai.domain.scene import SceneGraph, DetectedObject, Vec3, Pose6D
        scene = SceneGraph()
        obj = DetectedObject(id="obj_1", label="red_cup", confidence=0.92)
        scene.objects.append(obj)
        found = scene.get_object("red_cup")
        self.assertIsNotNone(found)
        self.assertEqual(found.id, "obj_1")
        print(f"  ✅ SceneGraph.get_object: {found.label}")

    def test_safety_status(self):
        from brain_ai.domain.safety import SafetyStatus, SafetyLevel
        status = SafetyStatus(level=SafetyLevel.S3_NORMAL)
        self.assertTrue(status.is_safe_to_execute)
        status.emergency_stop_active = True
        self.assertFalse(status.is_safe_to_execute)
        print(f"  ✅ SafetyStatus: is_safe_to_execute works correctly")

    def test_motion_trajectory(self):
        from brain_ai.domain.motion import Trajectory, TrajectorySet, TrajectoryStrategy
        t1 = Trajectory(id="t1", strategy=TrajectoryStrategy.OPTIMAL, score=0.9, duration_sec=2.5)
        t2 = Trajectory(id="t2", strategy=TrajectoryStrategy.CONSERVATIVE, score=0.7, duration_sec=4.0)
        ts = TrajectorySet(task_id="task_1", trajectories=[t1, t2])
        best = ts.best()
        self.assertEqual(best.id, "t1")
        sorted_t = ts.sorted_by_score()
        self.assertEqual(sorted_t[0].id, "t1")
        print(f"  ✅ TrajectorySet.best: {best.id} (score={best.score})")

    def test_episode(self):
        from brain_ai.domain.episode import Episode
        ep = Episode(task_id="t1", raw_instruction="拿起红色杯子", success=True)
        d = ep.to_dict()
        self.assertTrue(d["success"])
        ep2 = Episode.from_dict(d)
        self.assertEqual(ep2.task_id, "t1")
        print(f"  ✅ Episode serialization: {ep2.to_dict()['task_id']}")


# ────────────────────────────────────────────────────────────────────────────
class TestKnowledgeModules(unittest.TestCase):

    def test_ring_buffer(self):
        from brain_ai.knowledge.ring_buffer import RingBuffer
        buf: RingBuffer[int] = RingBuffer(5)
        for i in range(7):
            buf.push(i)
        self.assertEqual(len(buf), 5)
        self.assertEqual(buf.peek_last(2), [5, 6])
        print(f"  ✅ RingBuffer(5): last 2 = {buf.peek_last(2)}")

    def test_working_memory(self):
        from brain_ai.knowledge.working_memory import WorkingMemory
        wm = WorkingMemory()
        wm.set_task("task_1", "把红色杯子放到桌子上")
        wm.update_scene({"objects": [{"label": "red_cup"}]})
        snap = wm.snapshot()
        self.assertEqual(snap["task_id"], "task_1")
        self.assertEqual(snap["scene_object_count"], 1)
        wm.add_turn("user", "把红色杯子放到桌子上")
        wm.add_turn("assistant", "好的，正在执行")
        turns = wm.recent_turns(2)
        self.assertEqual(len(turns), 2)
        print(f"  ✅ WorkingMemory snapshot: {snap}")

    def test_experience_store(self):
        from brain_ai.knowledge.experience_store import ExperienceStore
        store = ExperienceStore(db_path=":memory:")   # use in-memory
        # Patch db_path handling
        store._conn.execute("""
            CREATE TABLE IF NOT EXISTS episodes (
                id TEXT PRIMARY KEY, robot_id TEXT NOT NULL,
                skill_name TEXT, success INTEGER, reward REAL,
                created_at TEXT, data TEXT NOT NULL)
        """)
        store._conn.commit()

        ep = {"id": "ep_001", "robot_id": "r1", "skill_name": "pick_object",
              "success": True, "reward": 1.0, "raw_instruction": "拿起红色杯子"}
        eid = store.store(ep)
        self.assertEqual(eid, "ep_001")
        retrieved = store.get("ep_001")
        self.assertEqual(retrieved["robot_id"], "r1")
        print(f"  ✅ ExperienceStore: stored and retrieved ep_001")

    def test_event_recorder(self):
        from brain_ai.knowledge.event_recorder import EventRecorder, EventCategory
        rec = EventRecorder(buffer_size=20)
        rec.task_started("t1", "拿起杯子")
        rec.safety_alert("COLLISION_IMMINENT", 1, "test alert")
        rec.task_completed("t1", success=True, duration_sec=3.5)
        events = rec.recent(5)
        self.assertEqual(len(events), 3)
        safety_events = rec.filter(category=EventCategory.SAFETY)
        self.assertEqual(len(safety_events), 1)
        print(f"  ✅ EventRecorder: {len(events)} events, 1 safety event")

    def test_timeline_logger(self):
        from brain_ai.knowledge.timeline_logger import TimelineLogger
        log = TimelineLogger(task_id="t1")
        log.log("planning",  "LLM intent parse complete", confidence=0.95)
        log.log("executing", "gRPC pick_object called")
        log.log("completed", "task finished", success=True)
        summary = log.summary()
        self.assertEqual(summary["step_count"], 3)
        self.assertIn("planning", summary["phases"])
        print(f"  ✅ TimelineLogger summary: {summary['step_count']} steps")


# ────────────────────────────────────────────────────────────────────────────
class TestModelRuntime(unittest.TestCase):

    def test_runtime_factory_ds3_unavailable(self):
        """DS3 backend is unavailable when no API key is set."""
        from brain_ai.model_runtime.runtime_factory import RuntimeFactory, BackendType
        factory = RuntimeFactory({"ds3_cloud": {"api_key": ""}})
        with self.assertRaises(RuntimeError):
            factory.get_backend()
        print("  ✅ RuntimeFactory raises when no backend available")

    def test_function_call_parser_intent(self):
        from brain_ai.llm_agent.function_calling import FunctionCallParser
        parser = FunctionCallParser()
        raw = '```json\n{"action": "pick", "target": "red_cup", "source": null, "constraints": ["carefully"], "confidence": 0.92}\n```'
        intent = parser.parse_intent(raw)
        self.assertEqual(intent["action"],  "pick")
        self.assertEqual(intent["target"],  "red_cup")
        self.assertAlmostEqual(intent["confidence"], 0.92, places=2)
        print(f"  ✅ FunctionCallParser.parse_intent: action={intent['action']}")

    def test_function_call_parser_subtasks(self):
        from brain_ai.llm_agent.function_calling import FunctionCallParser
        parser = FunctionCallParser()
        raw = '[{"skill_name":"detect_object","parameters":{"label":"red_cup"},"preconditions":[],"postconditions":["object_detected"],"estimated_duration_sec":2.0}]'
        subtasks = parser.parse_subtasks(raw)
        self.assertEqual(len(subtasks), 1)
        self.assertEqual(subtasks[0]["skill_name"], "detect_object")
        print(f"  ✅ FunctionCallParser.parse_subtasks: {subtasks[0]['skill_name']}")

    def test_function_call_parser_bt_xml(self):
        from brain_ai.llm_agent.function_calling import FunctionCallParser
        parser = FunctionCallParser()
        raw = "Here is the BT:\n<BehaviorTree ID=\"Main\">\n  <Sequence>\n    <Action ID=\"pick_object\" label=\"red_cup\"/>\n  </Sequence>\n</BehaviorTree>"
        xml = parser.parse_bt_xml(raw)
        self.assertIn("<BehaviorTree", xml)
        print(f"  ✅ FunctionCallParser.parse_bt_xml: {xml[:60]}")

    def test_transforms(self):
        from brain_ai.utils.transforms import euler_to_quat, quat_to_euler, distance_3d
        import math
        q = euler_to_quat(0.0, 0.0, math.pi / 2)  # 90° yaw
        rpy = quat_to_euler(q)
        self.assertAlmostEqual(rpy[2], math.pi / 2, places=5)
        d = distance_3d((0.0, 0.0, 0.0), (3.0, 4.0, 0.0))
        self.assertAlmostEqual(d, 5.0, places=5)
        print(f"  ✅ Transforms: quat round-trip yaw={rpy[2]:.4f}, dist={d:.1f}")


# ────────────────────────────────────────────────────────────────────────────

def run_tests():
    suite = unittest.TestLoader().loadTestsFromModule(
        __import__(__name__)
    )
    runner = unittest.TextTestRunner(verbosity=0, failfast=True)
    result = runner.run(suite)
    total  = result.testsRun
    passed = total - len(result.failures) - len(result.errors)
    print(f"\n{'='*50}")
    print(f"Sprint 2 Tests: {passed}/{total} passed")
    if result.failures or result.errors:
        for f in result.failures + result.errors:
            print(f"  FAIL: {f[0]}")
        return False
    print("All tests passed ✅")
    return True


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
