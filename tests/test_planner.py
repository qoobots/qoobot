"""
tests/test_planner.py — Integration tests for planner module (Sprint 2 → Sprint 3).

Covers:
  1. TrajectoryScorer: scoring, ranking, custom weights
  2. TrajectoryGenerator: multi-strategy generation, fallback
  3. BTComposer: XML parsing, validation, skill registry
  4. HITLManager: timeout auto-select, user selection, cancellation
  5. PlanBuilder: end-to-end plan building with HITL
  6. EventDispatcher: dispatch and queue (without WS)

Run: python tests/test_planner.py
"""

from __future__ import annotations

import asyncio
import sys
import os

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "brain_ai"))

import unittest


# ────────────────────────────────────────────────────────────────────────────
class TestTrajectoryScorer(unittest.TestCase):
    """T2.13-1: Trajectory scoring and ranking."""

    def test_score_single_trajectory(self):
        from brain_ai.domain.motion import Trajectory, TrajectoryStrategy, Waypoint
        from brain_ai.planner.scorer import TrajectoryScorer

        scorer = TrajectoryScorer()
        traj = Trajectory(
            strategy=TrajectoryStrategy.OPTIMAL,
            waypoints=[Waypoint()] * 50,
            collision_free=True,
            duration_sec=5.0,
            path_length_m=1.2,
            manipulability=0.15,
            joint_effort_rms=12.0,
        )
        scores = scorer.score(traj)
        self.assertGreater(scores.composite, 0.0)
        self.assertLessEqual(scores.composite, 1.0)
        self.assertEqual(traj.score, scores.composite)
        print(f"  ✅ Single score: composite={scores.composite:.3f}")

    def test_rank_multiple_trajectories(self):
        from brain_ai.domain.motion import Trajectory, TrajectoryStrategy, Waypoint
        from brain_ai.planner.scorer import TrajectoryScorer

        scorer = TrajectoryScorer()
        trajs = [
            Trajectory(strategy=TrajectoryStrategy.OPTIMAL, waypoints=[Waypoint()] * 30,
                       collision_free=True, duration_sec=3.0, path_length_m=0.8,
                       manipulability=0.2, joint_effort_rms=8.0),
            Trajectory(strategy=TrajectoryStrategy.CONSERVATIVE, waypoints=[Waypoint()] * 60,
                       collision_free=True, duration_sec=8.0, path_length_m=1.5,
                       manipulability=0.1, joint_effort_rms=5.0),
            Trajectory(strategy=TrajectoryStrategy.AGGRESSIVE, waypoints=[Waypoint()] * 20,
                       collision_free=True, duration_sec=2.0, path_length_m=0.6,
                       manipulability=0.05, joint_effort_rms=20.0),
        ]
        ranked = scorer.rank(trajs)
        self.assertEqual(len(ranked), 3)
        # Should be sorted descending by score
        for i in range(len(ranked) - 1):
            self.assertGreaterEqual(ranked[i].score, ranked[i + 1].score,
                                    f"Ranking order wrong at index {i}")
        best = TrajectoryScorer.best(ranked)
        self.assertEqual(best.id, ranked[0].id)
        print(f"  ✅ Ranked 3 trajectories: best={best.label} score={best.score:.3f}")

    def test_custom_weights(self):
        from brain_ai.domain.motion import Trajectory, TrajectoryStrategy, Waypoint
        from brain_ai.planner.scorer import ScoringWeights, TrajectoryScorer

        # Prioritize speed over everything
        speed_weights = ScoringWeights(
            path_length=0.1, duration=0.5, collision_safety=0.1,
            manipulability=0.1, joint_effort=0.1, smoothness=0.05, strategy_bonus=0.05,
        )
        scorer = TrajectoryScorer(weights=speed_weights)

        fast = Trajectory(strategy=TrajectoryStrategy.AGGRESSIVE, waypoints=[Waypoint()] * 15,
                          collision_free=True, duration_sec=1.0, path_length_m=0.5,
                          manipulability=0.05, joint_effort_rms=25.0)
        slow = Trajectory(strategy=TrajectoryStrategy.CONSERVATIVE, waypoints=[Waypoint()] * 80,
                          collision_free=True, duration_sec=10.0, path_length_m=0.3,
                          manipulability=0.3, joint_effort_rms=5.0)
        ranked = scorer.rank([fast, slow])
        self.assertEqual(ranked[0].id, fast.id, "Speed-weighted should prefer fast")
        print(f"  ✅ Speed-weighted ranking: fast={ranked[0].score:.3f} > slow={ranked[1].score:.3f}")

    def test_collision_penalty(self):
        from brain_ai.domain.motion import Trajectory, TrajectoryStrategy, Waypoint
        from brain_ai.planner.scorer import TrajectoryScorer

        scorer = TrajectoryScorer()
        safe = Trajectory(strategy=TrajectoryStrategy.OPTIMAL, waypoints=[Waypoint()] * 30,
                          collision_free=True, duration_sec=5.0, path_length_m=1.0)
        unsafe = Trajectory(strategy=TrajectoryStrategy.OPTIMAL, waypoints=[Waypoint()] * 30,
                            collision_free=False, duration_sec=5.0, path_length_m=1.0)
        safe_score = scorer.score(safe).composite
        unsafe_score = scorer.score(unsafe).composite
        self.assertGreater(safe_score, unsafe_score,
                           "Collision-free should score higher")
        print(f"  ✅ Collision penalty: safe={safe_score:.3f} > unsafe={unsafe_score:.3f}")


# ────────────────────────────────────────────────────────────────────────────
class TestTrajectoryGenerator(unittest.TestCase):
    """T2.13-2: Multi-strategy trajectory generation."""

    def test_generate_with_default_strategies(self):
        from brain_ai.planner.trajectory_gen import TrajectoryGenerator
        from brain_ai.planner.moveit_client import MoveItClient

        gen = TrajectoryGenerator(moveit_client=MoveItClient(use_stub=True))
        ts = gen.generate(
            task_id="task_test_001",
            target_pose=[0.5, 0.2, 0.3, 0.0, 0.0, 0.0, 1.0],
        )
        self.assertGreaterEqual(len(ts.trajectories), 1,
                                "Should generate at least 1 trajectory")
        self.assertIsNotNone(ts.best_id)
        self.assertEqual(ts.task_id, "task_test_001")
        print(f"  ✅ Generated {len(ts.trajectories)} trajectories, best={ts.best_id}")

    def test_fallback_on_empty_strategies(self):
        from brain_ai.planner.trajectory_gen import TrajectoryGenerator
        from brain_ai.planner.moveit_client import MoveItClient
        from brain_ai.domain.motion import TrajectoryStrategy

        gen = TrajectoryGenerator(
            moveit_client=MoveItClient(use_stub=True),
            strategies=[TrajectoryStrategy.ADVERSARIAL],
        )
        ts = gen.generate(
            task_id="task_fallback",
            target_pose=[0.3, -0.1, 0.5, 0.0, 0.0, 0.0, 1.0],
        )
        self.assertGreaterEqual(len(ts.trajectories), 1,
                                "Fallback should produce at least 1 trajectory")
        print(f"  ✅ Fallback generated {len(ts.trajectories)} trajectories")

    def test_single_strategy_generation(self):
        from brain_ai.planner.trajectory_gen import TrajectoryGenerator
        from brain_ai.planner.moveit_client import MoveItClient
        from brain_ai.domain.motion import TrajectoryStrategy

        gen = TrajectoryGenerator(
            moveit_client=MoveItClient(use_stub=True),
            strategies=[TrajectoryStrategy.CONSERVATIVE],
        )
        ts = gen.generate(
            task_id="task_single",
            target_pose=[0.0, 0.0, 0.8, 0.0, 0.0, 0.0, 1.0],
        )
        self.assertEqual(len(ts.trajectories), 1)
        self.assertEqual(ts.trajectories[0].strategy, TrajectoryStrategy.CONSERVATIVE)
        print(f"  ✅ Single strategy: {ts.trajectories[0].strategy.value}")


# ────────────────────────────────────────────────────────────────────────────
class TestBTComposer(unittest.TestCase):
    """T2.13-3: Behavior tree composition and validation."""

    def test_parse_simple_xml(self):
        from brain_ai.planner.bt_composer import BTComposer

        xml = """<BehaviorTree>
    <Sequence name="pick_task">
        <Action name="approach_object" target="red_cup"/>
        <Action name="grasp" force="5"/>
        <Action name="lift" height="0.3"/>
    </Sequence>
</BehaviorTree>"""
        composer = BTComposer()
        bt = composer.compose(xml, task_id="t1")
        self.assertIsNotNone(bt.root)
        self.assertEqual(bt.root.node_type, "Sequence")
        self.assertEqual(len(bt.root.children), 3)
        self.assertEqual(bt.root.children[0].skill_name, "approach_object")
        print(f"  ✅ Parsed BT: root={bt.root.node_type}, skills={len(bt.root.children)}")

    def test_extract_from_markdown_fence(self):
        from brain_ai.planner.bt_composer import BTComposer

        md_text = """Here is the behavior tree:
```xml
<Action name="pick" object="cup"/>
```
That should work."""
        composer = BTComposer()
        bt = composer.compose(md_text)
        self.assertIsNotNone(bt.root)
        self.assertEqual(bt.root.skill_name, "pick")
        print("  ✅ Extracted XML from markdown fence")

    def test_validate_unregistered_skill(self):
        from brain_ai.planner.bt_composer import BTComposer

        composer = BTComposer(skill_registry={"pick_object", "place_object"})
        bt = composer.compose("""
<Sequence name="main">
    <Action name="unknown_skill"/>
</Sequence>""")
        is_valid, warnings = composer.validate(bt)
        self.assertFalse(is_valid)
        self.assertTrue(any("unknown_skill" in w for w in warnings))
        print(f"  ✅ Validation warnings: {len(warnings)}")

    def test_validate_registered_skill(self):
        from brain_ai.planner.bt_composer import BTComposer

        composer = BTComposer(skill_registry={"pick_object", "navigate_to"})
        bt = composer.compose("""
<Sequence name="main">
    <Action name="pick_object" label="cup"/>
    <Action name="navigate_to" x="1.0" y="0.5"/>
</Sequence>""")
        is_valid, warnings = composer.validate(bt)
        self.assertTrue(is_valid, f"Warnings: {warnings}")
        print("  ✅ Valid BT with registered skills")

    def test_register_and_unregister(self):
        from brain_ai.planner.bt_composer import BTComposer

        composer = BTComposer()
        composer.register_skill("my_custom_skill")
        self.assertIn("my_custom_skill", composer._skill_registry)
        composer.unregister_skill("my_custom_skill")
        self.assertNotIn("my_custom_skill", composer._skill_registry)
        print("  ✅ Skill register/unregister")

    def test_banned_skill(self):
        from brain_ai.planner.bt_composer import BTComposer

        composer = BTComposer()
        with self.assertRaises(ValueError):
            composer.register_skill("exec")
        print("  ✅ Banned skill rejected")


# ────────────────────────────────────────────────────────────────────────────
class TestHITLManager(unittest.TestCase):
    """T2.13-4: HITL selection manager (async)."""

    def test_timeout_auto_select(self):
        from brain_ai.domain.motion import Trajectory, TrajectorySet, TrajectoryStrategy, Waypoint
        from brain_ai.domain.plan import ExecutionPlan
        from brain_ai.planner.hitl_manager import HITLManager, HITLState

        plan = ExecutionPlan(task_id="t1")
        trajs = [
            Trajectory(id="traj_a", strategy=TrajectoryStrategy.OPTIMAL,
                       waypoints=[Waypoint()] * 20, score=0.9,
                       label="最优", color_hint="#00ccff"),
            Trajectory(id="traj_b", strategy=TrajectoryStrategy.CONSERVATIVE,
                       waypoints=[Waypoint()] * 40, score=0.7,
                       label="安全", color_hint="#00ff88"),
        ]
        ts = TrajectorySet(task_id="t1", trajectories=trajs, best_id="traj_a")

        mgr = HITLManager(ws_server=None, default_timeout_sec=0.1)

        async def run():
            return await mgr.start_selection(plan=plan, trajectory_set=ts, timeout_sec=0.1)

        result = asyncio.get_event_loop().run_until_complete(run())
        self.assertEqual(result.state, HITLState.TIMED_OUT)
        self.assertFalse(result.selected_by_user)
        self.assertEqual(result.selected_trajectory_id, "traj_a")
        self.assertEqual(result.options_count, 2)
        print(f"  ✅ HITL timeout: selected={result.selected_trajectory_id} (auto)")

    def test_user_selection(self):
        from brain_ai.domain.motion import Trajectory, TrajectorySet, TrajectoryStrategy, Waypoint
        from brain_ai.domain.plan import ExecutionPlan
        from brain_ai.planner.hitl_manager import HITLManager, HITLState

        plan = ExecutionPlan(task_id="t2")
        trajs = [
            Trajectory(id="traj_x", strategy=TrajectoryStrategy.OPTIMAL,
                       waypoints=[Waypoint()] * 20, score=0.6, label="X"),
            Trajectory(id="traj_y", strategy=TrajectoryStrategy.CONSERVATIVE,
                       waypoints=[Waypoint()] * 40, score=0.9, label="Y"),
        ]
        ts = TrajectorySet(task_id="t2", trajectories=trajs, best_id="traj_y")
        mgr = HITLManager(ws_server=None, default_timeout_sec=5.0)

        async def run():
            task = asyncio.ensure_future(
                mgr.start_selection(plan=plan, trajectory_set=ts, timeout_sec=10.0)
            )
            # Simulate user clicking traj_x after 50ms
            await asyncio.sleep(0.05)
            session_id = mgr.active_session_ids[0] if mgr.active_session_ids else None
            if session_id:
                mgr.select_trajectory(session_id, "traj_x")
            return await task

        result = asyncio.get_event_loop().run_until_complete(run())
        self.assertEqual(result.state, HITLState.SELECTED)
        self.assertTrue(result.selected_by_user)
        self.assertEqual(result.selected_trajectory_id, "traj_x")
        print(f"  ✅ HITL user selection: selected={result.selected_trajectory_id}")

    def test_invalid_trajectory_rejected(self):
        from brain_ai.domain.motion import Trajectory, TrajectorySet, TrajectoryStrategy, Waypoint
        from brain_ai.planner.hitl_manager import HITLManager

        plan = type('obj', (object,), {'id': 't99'})()
        trajs = [Trajectory(id="valid_id", strategy=TrajectoryStrategy.OPTIMAL,
                            waypoints=[Waypoint()] * 10, score=1.0)]
        ts = TrajectorySet(task_id="t99", trajectories=trajs)
        mgr = HITLManager(ws_server=None)

        async def run():
            return await mgr.start_selection(plan=plan, trajectory_set=ts, timeout_sec=0.3)

        # First get a session going
        session_id = None

        async def run_with_select():
            nonlocal session_id
            task = asyncio.ensure_future(
                mgr.start_selection(plan=plan, trajectory_set=ts, timeout_sec=0.3)
            )
            await asyncio.sleep(0.01)
            sids = mgr.active_session_ids
            if sids:
                session_id = sids[0]
                ok = mgr.select_trajectory(session_id, "nonexistent")
                self.assertFalse(ok, "Invalid trajectory should be rejected")
            return await task

        result = asyncio.get_event_loop().run_until_complete(run_with_select())
        # Should have timed out since invalid selection was rejected
        self.assertIsNotNone(result)
        print("  ✅ Invalid trajectory ID rejected")

    def test_cancel_session(self):
        from brain_ai.domain.motion import Trajectory, TrajectorySet, TrajectoryStrategy, Waypoint
        from brain_ai.domain.plan import ExecutionPlan
        from brain_ai.planner.hitl_manager import HITLManager, HITLState

        plan = ExecutionPlan(task_id="t_cancel")
        trajs = [Trajectory(id="t1", strategy=TrajectoryStrategy.OPTIMAL,
                            waypoints=[Waypoint()] * 10, score=0.5)]
        ts = TrajectorySet(task_id="t_cancel", trajectories=trajs)
        mgr = HITLManager(ws_server=None)

        async def run():
            task = asyncio.ensure_future(
                mgr.start_selection(plan=plan, trajectory_set=ts, timeout_sec=5.0)
            )
            await asyncio.sleep(0.02)
            sids = mgr.active_session_ids
            self.assertTrue(len(sids) > 0)
            mgr.cancel(sids[0])
            result = await task
            self.assertEqual(result.state, HITLState.CANCELLED)
            return result

        result = asyncio.get_event_loop().run_until_complete(run())
        self.assertEqual(result.state, HITLState.CANCELLED)
        print("  ✅ HITL session cancelled")


# ────────────────────────────────────────────────────────────────────────────
class TestPlanBuilder(unittest.TestCase):
    """T2.13-5: End-to-end plan builder."""

    def test_build_plan_with_bt_and_trajectory(self):
        from brain_ai.domain.task import RobotTask
        from brain_ai.domain.plan import PlanStatus
        from brain_ai.planner.plan_builder import PlanBuilder
        from brain_ai.planner.moveit_client import MoveItClient
        from brain_ai.planner.trajectory_gen import TrajectoryGenerator

        task = RobotTask(raw_instruction="拿起杯子")
        task.start()

        bt_xml = """<Sequence name="pick_cup">
    <Action name="approach" target="cup"/>
    <Action name="grasp"/>
    <Action name="lift" height="0.2"/>
</Sequence>"""

        builder = PlanBuilder(
            trajectory_gen=TrajectoryGenerator(
                moveit_client=MoveItClient(use_stub=True),
                strategies=None,  # Use defaults
            ),
            enable_hitl=False,
        )

        plan = builder.build(
            task=task,
            bt_xml=bt_xml,
            target_pose=[0.5, 0.0, 0.3, 0.0, 0.0, 0.0, 1.0],
        )

        self.assertIsNotNone(plan.behavior_tree)
        self.assertIsNotNone(plan.behavior_tree.root)
        self.assertGreater(len(plan.trajectory_ids), 0)
        self.assertEqual(plan.task_id, task.id)
        print(f"  ✅ Built plan: {len(plan.trajectory_ids)} trajectories, "
              f"status={plan.status.value}, risk={plan.risk_score:.2f}")

    def test_build_without_trajectory(self):
        from brain_ai.domain.task import RobotTask
        from brain_ai.domain.plan import PlanStatus
        from brain_ai.planner.plan_builder import PlanBuilder

        task = RobotTask(raw_instruction="扫描环境")
        builder = PlanBuilder(enable_hitl=False)
        plan = builder.build(task=task)
        self.assertEqual(plan.task_id, task.id)
        self.assertEqual(plan.status, PlanStatus.READY)
        self.assertEqual(len(plan.trajectory_ids), 0)
        print("  ✅ Build without trajectory: plan ready")

    def test_risk_estimation(self):
        from brain_ai.domain.task import RobotTask, TaskPriority
        from brain_ai.domain.plan import PlanStatus
        from brain_ai.planner.plan_builder import PlanBuilder

        complex_task = RobotTask(raw_instruction="复杂任务", priority=TaskPriority.URGENT)
        # Add many subtasks to increase risk
        from brain_ai.domain.task import SubTask
        for i in range(10):
            complex_task.subtasks.append(SubTask(skill_name=f"step_{i}"))

        builder = PlanBuilder(enable_hitl=False)
        plan = builder.build(task=complex_task, scene_context={"object_count": 15})
        self.assertGreater(plan.risk_score, 0.1)
        print(f"  ✅ Risk estimation: risk={plan.risk_score:.2f}")

    def test_single_trajectory_auto_select(self):
        from brain_ai.domain.task import RobotTask
        from brain_ai.domain.plan import PlanStatus
        from brain_ai.planner.plan_builder import PlanBuilder
        from brain_ai.planner.moveit_client import MoveItClient
        from brain_ai.planner.trajectory_gen import TrajectoryGenerator
        from brain_ai.domain.motion import TrajectoryStrategy

        task = RobotTask(raw_instruction="单轨迹任务")
        builder = PlanBuilder(
            trajectory_gen=TrajectoryGenerator(
                moveit_client=MoveItClient(use_stub=True),
                strategies=[TrajectoryStrategy.OPTIMAL],
            ),
            enable_hitl=False,
        )
        plan = builder.build(
            task=task,
            target_pose=[0.0, 0.0, 0.5, 0.0, 0.0, 0.0, 1.0],
        )
        self.assertEqual(plan.status, PlanStatus.READY)
        self.assertIsNotNone(plan.selected_trajectory_id)
        print(f"  ✅ Single trajectory auto-select: {plan.selected_trajectory_id}")


# ────────────────────────────────────────────────────────────────────────────
class TestEventDispatcher(unittest.TestCase):
    """T2.13-6: Event dispatcher queue and coalescing."""

    def test_dispatch_and_queue(self):
        from brain_ai.ws_server.event_dispatcher import EventDispatcher, EventPriority, DomainEvent

        dispatcher = EventDispatcher(ws_server=None, max_queue_size=100)
        self.assertEqual(dispatcher.queue_size, 0)

        dispatcher.dispatch(DomainEvent(
            event_type="plan_status",
            payload={"plan_id": "p1", "state": "EXECUTING"},
            priority=EventPriority.PLAN,
        ))
        self.assertEqual(dispatcher.queue_size, 1)
        dispatcher.dispatch(DomainEvent(
            event_type="safety_alert",
            payload={"level": "warning", "message": "joint limit"},
            priority=EventPriority.SAFETY,
        ))
        self.assertEqual(dispatcher.queue_size, 2)
        print(f"  ✅ Queue size: {dispatcher.queue_size}")

    def test_scene_coalescing(self):
        from brain_ai.ws_server.event_dispatcher import EventDispatcher, EventPriority, DomainEvent

        dispatcher = EventDispatcher(ws_server=None)
        dispatcher.dispatch(DomainEvent(
            event_type="scene_update",
            payload={"objects": [{"id": "a"}]},
            priority=EventPriority.SCENE,
        ))
        dispatcher.dispatch(DomainEvent(
            event_type="scene_update",
            payload={"objects": [{"id": "b"}]},
            priority=EventPriority.SCENE,
        ))
        dispatcher.dispatch(DomainEvent(
            event_type="plan_status",
            payload={"plan_id": "p1"},
            priority=EventPriority.PLAN,
        ))

        # Coalesce: 2 scenes + 1 plan → keep latest scene + plan = 2
        events = list(dispatcher._queue)
        coalesced = dispatcher._coalesce_scenes(events)
        self.assertEqual(len(coalesced), 2,
                         "Coalesced should have 1 plan + 1 scene = 2")
        print(f"  ✅ Coalesced {len(events)} → {len(coalesced)} events")

    def test_safety_priority_ordering(self):
        from brain_ai.ws_server.event_dispatcher import EventDispatcher, EventPriority, DomainEvent

        dispatcher = EventDispatcher(ws_server=None)
        dispatcher.dispatch(DomainEvent(
            event_type="scene_update",
            payload={},
            priority=EventPriority.SCENE,
        ))
        dispatcher.dispatch(DomainEvent(
            event_type="safety_alert",
            payload={"level": "emergency"},
            priority=EventPriority.EMERGENCY,
        ))
        dispatcher.dispatch(DomainEvent(
            event_type="plan_status",
            payload={},
            priority=EventPriority.PLAN,
        ))

        events = sorted(dispatcher._queue, key=lambda e: e.priority.value)
        # Emergency (0) < Plan (3) < Scene (4)
        self.assertEqual(events[0].event_type, "safety_alert",
                         "Emergency should be first")
        print(f"  ✅ Priority order: {[e.event_type for e in events]}")

    def test_drop_on_full_queue(self):
        from brain_ai.ws_server.event_dispatcher import EventDispatcher, EventPriority, DomainEvent

        dispatcher = EventDispatcher(ws_server=None, max_queue_size=3)
        for i in range(5):
            dispatcher.dispatch(DomainEvent(
                event_type="test",
                payload={"i": i},
                priority=EventPriority.SCENE,
            ))
        self.assertEqual(dispatcher.queue_size, 3)
        self.assertEqual(dispatcher.dropped_count, 2)
        print(f"  ✅ Dropped {dispatcher.dropped_count} events on full queue")

    def test_event_subscription(self):
        from brain_ai.ws_server.event_dispatcher import EventDispatcher, EventPriority, DomainEvent

        dispatcher = EventDispatcher(ws_server=None)
        received = []

        def handler(payload):
            received.append(payload.get("msg"))

        dispatcher.subscribe("test_event", handler)
        dispatcher.dispatch(DomainEvent(
            event_type="test_event",
            payload={"msg": "hello"},
            priority=EventPriority.PLAN,
        ))
        # Dispatch loop not running, so subscribers won't fire until _send_event
        # But we can verify subscription exists
        self.assertIn("test_event", dispatcher._subscribers)
        self.assertIn(handler, dispatcher._subscribers["test_event"])
        print("  ✅ Event subscription registered")


# ────────────────────────────────────────────────────────────────────────────
class TestStrategyModules(unittest.TestCase):
    """T2.13-7: Strategy factory and parameter presets."""

    def test_all_strategy_presets(self):
        from brain_ai.planner.strategy_enum import StrategyName, get_strategy_config

        for name in StrategyName:
            cfg = get_strategy_config(name)
            self.assertIsNotNone(cfg)
            self.assertEqual(cfg.name, name)
            self.assertGreater(cfg.max_velocity_scale, 0)
            self.assertGreater(cfg.planning_time_sec, 0)
            print(f"  ✅ Strategy {name.value}: vel={cfg.max_velocity_scale}, "
                  f"clearance={cfg.clearance_m}m")

    def test_strategy_factory(self):
        from brain_ai.planner.strategies import create_strategy, STRATEGY_REGISTRY
        from brain_ai.planner.strategy_enum import StrategyName

        strat = create_strategy(StrategyName.OPTIMAL)
        result = strat.plan(
            start_joints=[0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            target_pose=[0.5, 0.0, 0.3, 0.0, 0.0, 0.0, 1.0],
        )
        self.assertTrue(result.success)
        self.assertIsNotNone(result.trajectory_waypoints)
        self.assertGreater(len(result.trajectory_waypoints), 0)
        print(f"  ✅ {strat.name.value} strategy: {len(result.trajectory_waypoints)} waypoints")

    def test_all_strategies_produce_trajectories(self):
        from brain_ai.planner.strategies import create_strategy
        from brain_ai.planner.strategy_enum import StrategyName

        for name in StrategyName:
            strat = create_strategy(name)
            result = strat.plan(
                start_joints=[0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                target_pose=[0.4, 0.1, 0.4, 0.0, 0.0, 0.0, 1.0],
            )
            self.assertTrue(result.success, f"Strategy {name.value} failed")
            print(f"  ✅ {name.value}: {len(result.trajectory_waypoints)} waypoints, "
                  f"{result.planning_time_ms:.1f}ms")


# ────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("brain_ai/planner — Integration Tests")
    print("=" * 60)
    unittest.main(verbosity=2)
