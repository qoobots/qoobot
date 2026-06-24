"""领域实体测试"""
import pytest
from brain_ai.domain.entities import (
    Task, TaskStatus, Intent, SceneGraph, Object3D, Plan,
    Trajectory, TrajectoryStrategy, Waypoint, JointState, SafetyLevel
)


class TestTask:
    def test_create_task(self):
        intent = Intent(action="pick", target="cube")
        task = Task(id="T001", intent=intent)
        assert task.id == "T001"
        assert task.status == TaskStatus.PENDING

    def test_task_lifecycle(self):
        intent = Intent(action="pick", target="cube")
        task = Task(id="T002", intent=intent)
        task.status = TaskStatus.PLANNING
        assert task.status == TaskStatus.PLANNING
        task.status = TaskStatus.EXECUTING
        assert task.status == TaskStatus.EXECUTING
        task.status = TaskStatus.COMPLETED
        assert task.status == TaskStatus.COMPLETED

    def test_task_with_subtasks(self):
        intent = Intent(action="pick_place", target="cube")
        s1 = Task(id="S1", intent=Intent(action="navigate", target="table"))
        s2 = Task(id="S2", intent=Intent(action="pick", target="cube"))
        task = Task(id="T003", intent=intent, subtasks=[s1, s2])
        assert len(task.subtasks) == 2
        assert task.subtasks[0].id == "S1"

    def test_task_to_dict(self):
        intent = Intent(action="pick", target="cube")
        task = Task(id="T004", intent=intent)
        d = task.model_dump()
        assert d["id"] == "T004"


class TestIntent:
    def test_intent_creation(self):
        intent = Intent(action="pick", target="red_cube")
        assert intent.action == "pick"
        assert intent.target == "red_cube"

    def test_intent_with_constraints(self):
        intent = Intent(action="pick", target="cup", constraints=["gently", "fast"])
        assert "gently" in intent.constraints

    def test_intent_confidence(self):
        intent = Intent(action="navigate", target="kitchen", confidence=0.95)
        assert intent.confidence == 0.95


class TestSceneGraph:
    def test_scene_graph_empty(self):
        sg = SceneGraph()
        assert len(sg.objects) == 0
        assert len(sg.robot_pose) == 7

    def test_scene_graph_with_objects(self):
        obj = Object3D(id="obj-001", label="cube", centroid=[0.5, 0.3, 0.05], confidence=0.95)
        sg = SceneGraph(objects=[obj])
        assert len(sg.objects) == 1
        assert sg.objects[0].label == "cube"

    def test_object3d_creation(self):
        obj = Object3D(id="obj-001", label="red_cube", confidence=0.95)
        assert obj.label == "red_cube"
        assert obj.confidence == 0.95


class TestTrajectory:
    def test_trajectory_creation(self):
        wp1 = Waypoint(x=0.5, y=0.3, z=0.1)
        wp2 = Waypoint(x=0.8, y=0.3, z=0.15)
        traj = Trajectory(id="T1", strategy=TrajectoryStrategy.OPTIMAL, waypoints=[wp1, wp2], score=0.94)
        assert traj.id == "T1"
        assert len(traj.waypoints) == 2
        assert traj.score == 0.94

    def test_waypoint_creation(self):
        wp = Waypoint(x=0.5, y=0.3, z=0.1)
        assert wp.x == 0.5
        assert wp.z == 0.1


class TestJointState:
    def test_joint_state_empty(self):
        js = JointState()
        assert js.names == []

    def test_joint_state_with_data(self):
        js = JointState(
            names=["joint_1", "joint_2"],
            positions=[0.1, 0.2],
            velocities=[0.01, 0.02]
        )
        assert len(js.names) == 2
        assert js.positions[0] == 0.1
