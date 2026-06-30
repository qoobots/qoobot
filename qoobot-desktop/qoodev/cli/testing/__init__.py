"""单元测试框架 — 技能/服务单元测试，Mock 传感器与执行器。

对标 pytest + unittest.mock 的机器人领域特化测试框架。
"""

import time
import threading
import json
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Mock 传感器
# ---------------------------------------------------------------------------

class MockSensor:
    """传感器 Mock 基类"""

    def __init__(self, name: str = ""):
        self.name = name
        self._data_queue: List[Any] = []
        self._call_count: int = 0
        self._enabled: bool = True

    def reset(self):
        self._data_queue.clear()
        self._call_count = 0

    def inject_data(self, data: Any):
        """注入模拟数据"""
        self._data_queue.append(data)

    def get_data(self) -> Optional[Any]:
        """获取下一帧数据"""
        self._call_count += 1
        if self._data_queue:
            return self._data_queue.pop(0)
        return None


class MockCamera(MockSensor):
    """RGB-D 相机 Mock"""

    def __init__(self, name: str = "camera", width: int = 640, height: int = 480):
        super().__init__(name)
        self.width = width
        self.height = height
        self.fps = 30

    def inject_image(self, rgb: Optional[bytes] = None, depth: Optional[bytes] = None):
        """注入模拟图像"""
        import numpy as np
        if rgb is None:
            rgb = np.random.randint(0, 255, (self.height, self.width, 3), dtype=np.uint8).tobytes()
        if depth is None:
            depth = np.random.randint(0, 65535, (self.height, self.width), dtype=np.uint16).tobytes()
        self.inject_data({"rgb": rgb, "depth": depth, "timestamp": time.time()})

    def get_rgb(self) -> Optional[bytes]:
        data = self.get_data()
        return data["rgb"] if data else None

    def get_depth(self) -> Optional[bytes]:
        data = self.get_data()
        return data["depth"] if data else None


class MockLidar(MockSensor):
    """LiDAR Mock"""

    def __init__(self, name: str = "lidar", num_points: int = 1024):
        super().__init__(name)
        self.num_points = num_points
        self.range_min = 0.1
        self.range_max = 30.0

    def inject_scan(self, points: Optional[List[Tuple[float, float, float]]] = None):
        """注入模拟点云"""
        import random
        if points is None:
            points = [
                (random.uniform(-5, 5), random.uniform(-5, 5), random.uniform(0, 3))
                for _ in range(self.num_points)
            ]
        self.inject_data({"points": points, "timestamp": time.time()})

    def get_points(self) -> Optional[List[Tuple[float, float, float]]]:
        data = self.get_data()
        return data["points"] if data else None


class MockIMU(MockSensor):
    """IMU Mock"""

    def __init__(self, name: str = "imu"):
        super().__init__(name)

    def inject_reading(self, accel: Tuple[float, float, float] = (0, 0, 9.81),
                       gyro: Tuple[float, float, float] = (0, 0, 0)):
        self.inject_data({"accel": accel, "gyro": gyro, "timestamp": time.time()})

    def get_reading(self) -> Optional[Dict]:
        return self.get_data()


class MockMicrophone(MockSensor):
    """麦克风阵列 Mock"""

    def __init__(self, name: str = "microphone", num_channels: int = 4, sample_rate: int = 16000):
        super().__init__(name)
        self.num_channels = num_channels
        self.sample_rate = sample_rate

    def inject_audio(self, samples: Optional[List[float]] = None, duration: float = 0.1):
        """注入模拟音频"""
        import random, math
        if samples is None:
            n = int(self.sample_rate * duration)
            samples = [
                math.sin(2 * math.pi * 440 * i / self.sample_rate) + random.uniform(-0.1, 0.1)
                for i in range(n)
            ]
        self.inject_data({"samples": samples, "sample_rate": self.sample_rate, "timestamp": time.time()})


# ---------------------------------------------------------------------------
# Mock 执行器
# ---------------------------------------------------------------------------

class MockActuator:
    """执行器 Mock 基类"""

    def __init__(self, name: str = ""):
        self.name = name
        self._command_history: List[Dict] = []
        self._state: Dict = {}
        self._callbacks: Dict[str, Callable] = {}

    def reset(self):
        self._command_history.clear()

    def on_command(self, cmd_type: str, callback: Callable):
        """注册命令回调"""
        self._callbacks[cmd_type] = callback

    def _record_command(self, cmd_type: str, **kwargs):
        entry = {"type": cmd_type, "timestamp": time.time(), **kwargs}
        self._command_history.append(entry)

        if cmd_type in self._callbacks:
            self._callbacks[cmd_type](**kwargs)

    @property
    def command_count(self) -> int:
        return len(self._command_history)

    @property
    def last_command(self) -> Optional[Dict]:
        return self._command_history[-1] if self._command_history else None


class MockJointActuator(MockActuator):
    """关节执行器 Mock"""

    def __init__(self, name: str = "joint_actuator", joint_names: Optional[List[str]] = None):
        super().__init__(name)
        self.joint_names = joint_names or []
        self._positions: Dict[str, float] = {j: 0.0 for j in self.joint_names}
        self._velocities: Dict[str, float] = {j: 0.0 for j in self.joint_names}
        self._torques: Dict[str, float] = {j: 0.0 for j in self.joint_names}

    def set_position_targets(self, targets: Dict[str, float]):
        self._record_command("position", targets=targets)
        for name, pos in targets.items():
            self._positions[name] = pos

    def set_velocity_targets(self, targets: Dict[str, float]):
        self._record_command("velocity", targets=targets)

    def set_torque_targets(self, targets: Dict[str, float]):
        self._record_command("torque", targets=targets)

    def get_positions(self) -> Dict[str, float]:
        return dict(self._positions)


class MockGripper(MockActuator):
    """夹爪 Mock"""

    def __init__(self, name: str = "gripper"):
        super().__init__(name)
        self._position: float = 0.0   # 0=全开, 1=全闭
        self._force: float = 0.0
        self._has_object: bool = False

    def set_position(self, position: float, force: float = 0.0):
        self._record_command("gripper_position", position=position, force=force)
        self._position = position
        self._force = force

    def grasp(self, force: float = 10.0):
        self.set_position(1.0, force)
        self._has_object = True

    def release(self):
        self.set_position(0.0)
        self._has_object = False

    @property
    def position(self) -> float:
        return self._position


class MockMobileBase(MockActuator):
    """移动底盘 Mock"""

    def __init__(self, name: str = "mobile_base"):
        super().__init__(name)
        self._x: float = 0.0
        self._y: float = 0.0
        self._theta: float = 0.0

    def set_velocity(self, linear: float, angular: float):
        self._record_command("velocity", linear=linear, angular=angular)

    def set_pose_target(self, x: float, y: float, theta: float = 0.0):
        self._record_command("pose", x=x, y=y, theta=theta)
        self._x = x
        self._y = y
        self._theta = theta

    @property
    def pose(self) -> Tuple[float, float, float]:
        return (self._x, self._y, self._theta)


# ---------------------------------------------------------------------------
# 测试环境
# ---------------------------------------------------------------------------

@dataclass
class TestScenario:
    """测试场景 — 传感器和执行器的组合"""
    name: str
    description: str = ""

    # 传感器
    cameras: Dict[str, MockCamera] = field(default_factory=dict)
    lidars: Dict[str, MockLidar] = field(default_factory=dict)
    imus: Dict[str, MockIMU] = field(default_factory=dict)
    microphones: Dict[str, MockMicrophone] = field(default_factory=dict)

    # 执行器
    joint_actuators: Dict[str, MockJointActuator] = field(default_factory=dict)
    grippers: Dict[str, MockGripper] = field(default_factory=dict)
    mobile_bases: Dict[str, MockMobileBase] = field(default_factory=dict)

    def add_camera(self, name: str = "camera", **kwargs) -> MockCamera:
        cam = MockCamera(name, **kwargs)
        self.cameras[name] = cam
        return cam

    def add_lidar(self, name: str = "lidar", **kwargs) -> MockLidar:
        lidar = MockLidar(name, **kwargs)
        self.lidars[name] = lidar
        return lidar

    def add_imu(self, name: str = "imu") -> MockIMU:
        imu = MockIMU(name)
        self.imus[name] = imu
        return imu

    def add_joint_actuator(self, name: str = "arm", joint_names: Optional[List[str]] = None) -> MockJointActuator:
        act = MockJointActuator(name, joint_names)
        self.joint_actuators[name] = act
        return act

    def add_gripper(self, name: str = "gripper") -> MockGripper:
        grip = MockGripper(name)
        self.grippers[name] = grip
        return grip

    def add_mobile_base(self, name: str = "base") -> MockMobileBase:
        base = MockMobileBase(name)
        self.mobile_bases[name] = base
        return base

    def reset_all(self):
        """重置所有 Mock"""
        for cam in self.cameras.values():
            cam.reset()
        for lidar in self.lidars.values():
            lidar.reset()
        for imu in self.imus.values():
            imu.reset()
        for act in self.joint_actuators.values():
            act.reset()
        for grip in self.grippers.values():
            grip.reset()
        for base in self.mobile_bases.values():
            base.reset()


# ---------------------------------------------------------------------------
# 测试运行器
# ---------------------------------------------------------------------------

class TestResult(Enum):
    PASS = auto()
    FAIL = auto()
    ERROR = auto()
    SKIP = auto()


@dataclass
class TestCase:
    """测试用例"""
    name: str
    func: Callable
    description: str = ""
    timeout: float = 30.0
    tags: List[str] = field(default_factory=list)


class SkillTestRunner:
    """技能测试运行器"""

    def __init__(self, scenario: Optional[TestScenario] = None):
        self.scenario = scenario or TestScenario(name="default")
        self._tests: List[TestCase] = []
        self._results: Dict[str, Dict] = {}
        self._hooks: Dict[str, List[Callable]] = defaultdict(list)

    def register(self, name: str, description: str = "", timeout: float = 30.0, tags: Optional[List[str]] = None):
        """注册测试用例 (装饰器)"""
        def decorator(func: Callable):
            self._tests.append(TestCase(
                name=name,
                func=func,
                description=description,
                timeout=timeout,
                tags=tags or [],
            ))
            return func
        return decorator

    def before_each(self, func: Callable):
        self._hooks["before_each"].append(func)
        return func

    def after_each(self, func: Callable):
        self._hooks["after_each"].append(func)
        return func

    def run_all(self, tags: Optional[List[str]] = None) -> Dict[str, Dict]:
        """运行所有测试"""
        tests = self._tests
        if tags:
            tests = [t for t in tests if any(tag in t.tags for tag in tags)]

        print(f"\n{'='*60}")
        print(f"Running {len(tests)} test(s)")
        print(f"{'='*60}\n")

        for test in tests:
            self._run_one(test)

        self._print_summary()
        return self._results

    def _run_one(self, test: TestCase):
        """运行单个测试"""
        print(f"  ▶ {test.name} ... ", end="", flush=True)

        # before_each hooks
        for hook in self._hooks["before_each"]:
            try:
                hook()
            except Exception as e:
                print(f"HOOK ERROR: {e}")
                self._results[test.name] = {
                    "status": TestResult.ERROR,
                    "error": f"before_each hook: {e}",
                }
                return

        # 运行测试
        self.scenario.reset_all()
        start_time = time.time()

        try:
            # 超时控制
            result = [None]
            exception = [None]

            def _run():
                try:
                    result[0] = test.func(self.scenario)
                except Exception as e:
                    exception[0] = e

            thread = threading.Thread(target=_run, daemon=True)
            thread.start()
            thread.join(timeout=test.timeout)

            elapsed = time.time() - start_time

            if thread.is_alive():
                print(f"⏱ TIMEOUT ({elapsed:.1f}s)")
                self._results[test.name] = {
                    "status": TestResult.ERROR,
                    "error": f"Timeout after {test.timeout}s",
                    "duration": elapsed,
                }
                return

            if exception[0]:
                import traceback
                print(f"❌ FAIL ({elapsed:.1f}s)")
                print(f"     {exception[0]}")
                self._results[test.name] = {
                    "status": TestResult.FAIL,
                    "error": str(exception[0]),
                    "traceback": traceback.format_exc(),
                    "duration": elapsed,
                }
            else:
                print(f"✅ PASS ({elapsed:.1f}s)")
                self._results[test.name] = {
                    "status": TestResult.PASS,
                    "duration": elapsed,
                }

        finally:
            # after_each hooks
            for hook in self._hooks["after_each"]:
                try:
                    hook()
                except Exception:
                    pass

    def _print_summary(self):
        """打印测试摘要"""
        passed = sum(1 for r in self._results.values() if r["status"] == TestResult.PASS)
        failed = sum(1 for r in self._results.values() if r["status"] == TestResult.FAIL)
        errors = sum(1 for r in self._results.values() if r["status"] == TestResult.ERROR)
        total = len(self._results)

        print(f"\n{'='*60}")
        print(f"Results: {passed} passed, {failed} failed, {errors} errors ({total} total)")
        print(f"{'='*60}\n")

        if failed > 0 or errors > 0:
            print("Failures:")
            for name, result in self._results.items():
                if result["status"] in (TestResult.FAIL, TestResult.ERROR):
                    print(f"  ❌ {name}")
                    print(f"     {result.get('error', 'Unknown error')}")


# ---------------------------------------------------------------------------
# 仿真回归测试
# ---------------------------------------------------------------------------

class RegressionTestSuite:
    """仿真回归测试套件 — 预设场景批量测试"""

    def __init__(self, name: str = "regression"):
        self.name = name
        self._scenarios: Dict[str, TestScenario] = {}
        self._results: Dict[str, Dict] = {}

    def add_scenario(self, scenario: TestScenario):
        self._scenarios[scenario.name] = scenario

    def run_all(self) -> Dict[str, Dict]:
        """运行所有场景的回归测试"""
        print(f"\n📊 Regression Suite: {self.name}")
        print(f"   Scenarios: {len(self._scenarios)}")

        for name, scenario in self._scenarios.items():
            runner = SkillTestRunner(scenario)
            # 这里可以自动发现并注册测试...
            results = runner.run_all()
            self._results[name] = {
                "passed": sum(1 for r in results.values() if r["status"] == TestResult.PASS),
                "failed": sum(1 for r in results.values() if r["status"] == TestResult.FAIL),
                "total": len(results),
            }

        return self._results


# ---------------------------------------------------------------------------
# 便捷工厂
# ---------------------------------------------------------------------------

def create_home_scenario() -> TestScenario:
    """创建家居场景测试环境"""
    scenario = TestScenario(
        name="home",
        description="家居环境测试场景 — 双轮移动底盘 + 6-DOF 机械臂 + 夹爪"
    )
    scenario.add_camera("head_camera", width=640, height=480)
    scenario.add_camera("wrist_camera", width=320, height=240)
    scenario.add_lidar("front_lidar", num_points=2048)
    scenario.add_imu("base_imu")
    scenario.add_mobile_base("base")
    scenario.add_joint_actuator("arm", ["shoulder_pan", "shoulder_lift", "elbow", "wrist_1", "wrist_2", "wrist_3"])
    scenario.add_gripper("gripper")
    return scenario


def create_factory_scenario() -> TestScenario:
    """创建工厂场景测试环境"""
    scenario = TestScenario(
        name="factory",
        description="工厂环境测试场景 — 移动平台 + 双机械臂"
    )
    scenario.add_camera("overhead_camera", width=1280, height=720)
    scenario.add_camera("left_wrist_camera", width=640, height=480)
    scenario.add_camera("right_wrist_camera", width=640, height=480)
    scenario.add_lidar("safety_lidar", num_points=4096)
    scenario.add_mobile_base("base")
    scenario.add_joint_actuator("left_arm", [f"left_joint_{i}" for i in range(1, 7)])
    scenario.add_joint_actuator("right_arm", [f"right_joint_{i}" for i in range(1, 7)])
    scenario.add_gripper("left_gripper")
    scenario.add_gripper("right_gripper")
    return scenario
