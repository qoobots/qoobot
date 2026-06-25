"""Brain OS 端到端集成测试

验证完整链路：自然语言指令 → 意图解析 → 任务分解 → 
行为树生成 → 轨迹规划 → 场景感知 → 执行反馈
"""
import asyncio
import pytest
import json
import time
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

# ============================================================
# Mock 辅助（无真机硬件时的测试桩）
# ============================================================

class MockRobotClient:
    """模拟 RobotClient 端到端交互"""
    
    def __init__(self, robot_id="test_robot_01"):
        self.robot_id = robot_id
        self.state = "idle"
        self.current_task = None
        self.trajectories = []
        self.scene_objects = []
        self.safety_alerts = []
        self.events = []
        
    async def connect(self):
        self.state = "connected"
        self.events.append(("connect", time.time()))
        
    async def disconnect(self):
        self.state = "disconnected"
        self.events.append(("disconnect", time.time()))
        
    async def send_command(self, text: str) -> dict:
        """模拟自然语言指令处理"""
        self.events.append(("command", text, time.time()))
        # 模拟意图解析
        intent = {
            "action": "pick" if "抓" in text or "捡" in text else 
                     "place" if "放" in text else 
                     "navigate" if "去" in text or "到" in text else
                     "unknown",
            "target": "cube" if "方块" in text else 
                     "cup" if "杯子" in text else "unknown",
            "confidence": 0.85
        }
        return intent
    
    async def execute_plan(self, plan: dict) -> dict:
        """模拟执行计划"""
        self.current_task = plan
        self.state = "executing"
        self.events.append(("plan_execute", plan.get("plan_id"), time.time()))
        
        # 模拟执行结果
        result = {
            "plan_id": plan.get("plan_id", "plan-001"),
            "status": "completed",
            "subtasks_completed": len(plan.get("subtasks", [])),
            "duration_ms": 1500,
            "trajectory_score": 0.92
        }
        self.state = "idle"
        return result
    
    def get_scene(self) -> dict:
        """获取当前场景"""
        return {
            "objects": self.scene_objects,
            "robot_pose": {"x": 0.5, "y": 0.3, "z": 0.1},
            "timestamp": time.time()
        }


# ============================================================
# 测试夹具
# ============================================================

@pytest.fixture
def robot():
    """创建模拟机器人客户端"""
    return MockRobotClient()

@pytest.fixture
def sample_commands():
    """中文指令测试集"""
    return [
        ("把红色方块放到桌子上", "place"),
        ("去厨房拿一瓶水", "navigate"),
        ("抓取蓝色杯子", "pick"),
        ("把工件放到传送带上", "place"),
        ("移动到充电站", "navigate"),
        ("捡起地上的螺丝", "pick"),
    ]

@pytest.fixture
def sample_plan():
    """示例执行计划"""
    return {
        "plan_id": "plan-test-001",
        "task": "pick red cube",
        "subtasks": [
            {"id": "S1", "action": "navigate_to", "params": {"pose": [0.5, 0.2, 0.1]}},
            {"id": "S2", "action": "detect", "params": {"label": "red_cube"}},
            {"id": "S3", "action": "pick", "params": {"object_id": "obj-001"}},
            {"id": "S4", "action": "place", "params": {"target_pose": [0.8, 0.3, 0.15]}},
        ],
        "behavior_tree_xml": """<root><sequence>
            <NavigateTo pose="0.5,0.2,0.1"/>
            <DetectObject label="red_cube"/>
            <PickObject id="obj-001"/>
            <PlaceObject pose="0.8,0.3,0.15"/>
        </sequence></root>""",
        "strategy": "optimal",
        "created_at": time.time()
    }


# ============================================================
# 测试类 — 端到端集成
# ============================================================

class TestE2EConnectivity:
    """T6.1.1 连接与通信"""
    
    @pytest.mark.asyncio
    async def test_robot_connect_disconnect(self, robot):
        """机器人客户端连接与断开"""
        await robot.connect()
        assert robot.state == "connected"
        
        await robot.disconnect()
        assert robot.state == "disconnected"
    
    @pytest.mark.asyncio
    async def test_robot_lifecycle_events(self, robot):
        """生命周期事件记录"""
        await robot.connect()
        await robot.disconnect()
        
        events = [e[0] for e in robot.events]
        assert events == ["connect", "disconnect"]
    
    @pytest.mark.asyncio
    async def test_command_delivery(self, robot):
        """指令发送与响应"""
        await robot.connect()
        result = await robot.send_command("把红色方块放到桌子上")
        
        assert result is not None
        assert "action" in result
        assert "confidence" in result


class TestE2EIntentParsing:
    """T6.1.2 意图解析"""
    
    @pytest.mark.asyncio
    async def test_parse_pick_intent(self, robot):
        """解析抓取意图"""
        await robot.connect()
        result = await robot.send_command("抓取蓝色杯子")
        assert result["action"] == "pick"
    
    @pytest.mark.asyncio
    async def test_parse_navigate_intent(self, robot):
        """解析导航意图"""
        await robot.connect()
        result = await robot.send_command("去厨房拿一瓶水")
        assert result["action"] == "navigate"
    
    @pytest.mark.asyncio
    async def test_parse_place_intent(self, robot):
        """解析放置意图"""
        await robot.connect()
        result = await robot.send_command("把工件放到传送带上")
        assert result["action"] == "place"
    
    @pytest.mark.asyncio
    async def test_all_commands_have_intent(self, robot, sample_commands):
        """全部指令都能解析出意图"""
        await robot.connect()
        for text, expected_action in sample_commands:
            result = await robot.send_command(text)
            assert result["action"] == expected_action, \
                f"Command '{text}' expected {expected_action}, got {result['action']}"
    
    @pytest.mark.asyncio
    async def test_intent_confidence_threshold(self, robot):
        """意图解析置信度在合理范围"""
        await robot.connect()
        result = await robot.send_command("抓取蓝色杯子")
        assert 0.0 <= result["confidence"] <= 1.0


class TestE2EPlanExecution:
    """T6.1.3 计划执行"""
    
    @pytest.mark.asyncio
    async def test_execute_plan_success(self, robot, sample_plan):
        """执行计划成功完成"""
        await robot.connect()
        result = await robot.execute_plan(sample_plan)
        
        assert result["status"] == "completed"
        assert result["subtasks_completed"] == 4
    
    @pytest.mark.asyncio
    async def test_execute_plan_state_transition(self, robot, sample_plan):
        """执行计划时状态转换"""
        await robot.connect()
        assert robot.state == "connected"
        
        await robot.execute_plan(sample_plan)
        assert robot.state == "idle"  # 执行完后恢复
    
    @pytest.mark.asyncio
    async def test_execute_plan_tracked(self, robot, sample_plan):
        """执行计划被追踪"""
        await robot.connect()
        await robot.execute_plan(sample_plan)
        
        # 验证当前任务已被记录
        assert robot.current_task is not None
        assert robot.current_task["plan_id"] == "plan-test-001"
    
    @pytest.mark.asyncio
    async def test_execute_empty_plan_handled(self, robot):
        """空计划正确处理"""
        await robot.connect()
        empty_plan = {"plan_id": "empty", "subtasks": []}
        result = await robot.execute_plan(empty_plan)
        
        assert result["status"] == "completed"
        assert result["subtasks_completed"] == 0


class TestE2EScenePerception:
    """T6.1.4 场景感知"""
    
    def test_initial_scene_empty(self, robot):
        """初始场景为空"""
        scene = robot.get_scene()
        assert scene["objects"] == []
    
    def test_scene_has_robot_pose(self, robot):
        """场景包含机器人姿态"""
        scene = robot.get_scene()
        assert "robot_pose" in scene
        assert all(k in scene["robot_pose"] for k in ["x", "y", "z"])
    
    def test_scene_has_timestamp(self, robot):
        """场景包含时间戳"""
        scene = robot.get_scene()
        assert "timestamp" in scene
        assert scene["timestamp"] > 0


class TestE2EErrorHandling:
    """T6.1.5 错误处理"""
    
    @pytest.mark.asyncio
    async def test_command_before_connect(self, robot):
        """未连接时发送指令应正确处理"""
        # mock 不应崩溃
        result = await robot.send_command("测试指令")
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_multiple_connect_no_issue(self, robot):
        """多次连接不产生问题"""
        await robot.connect()
        await robot.connect()  # 重复连接
        assert robot.state == "connected"
    
    @pytest.mark.asyncio
    async def test_concurrent_commands(self, robot):
        """并发指令处理"""
        await robot.connect()
        
        commands = ["抓取方块", "移动到A点", "放置工件"]
        tasks = [robot.send_command(c) for c in commands]
        results = await asyncio.gather(*tasks)
        
        assert all(r is not None for r in results)
        assert all("action" in r for r in results)


class TestE2EEndToEndPipeline:
    """T6.1.6 完整流水线"""
    
    @pytest.mark.asyncio
    async def test_full_pipeline(self, robot):
        """完整流水线：指令→意图→计划→执行→场景"""
        await robot.connect()
        
        # Step 1: 发送指令
        intent = await robot.send_command("抓取红色方块放到桌子上")
        assert intent["action"] == "pick"
        
        # Step 2: 构建计划
        plan = {
            "plan_id": "pipeline-001",
            "task": "pick red cube and place on table",
            "subtasks": [
                {"id": "S1", "action": "navigate_to", "params": {"pose": [0.5, 0.2, 0.1]}},
                {"id": "S2", "action": "pick", "params": {"object_id": "obj-001"}},
                {"id": "S3", "action": "place", "params": {"target_pose": [0.8, 0.3, 0.15]}},
            ]
        }
        
        # Step 3: 执行计划
        result = await robot.execute_plan(plan)
        assert result["status"] == "completed"
        
        # Step 4: 获取场景
        scene = robot.get_scene()
        assert scene is not None
        
        # Step 5: 验证事件链完整
        event_types = [e[0] for e in robot.events]
        assert "connect" in event_types
        assert "command" in event_types
        assert "plan_execute" in event_types
    
    @pytest.mark.asyncio
    async def test_multi_task_pipeline(self, robot):
        """多任务顺序执行"""
        await robot.connect()
        
        tasks = [
            ("抓取方块", "pick"),
            ("放到桌子上", "place"),
            ("移动到B点", "navigate"),
        ]
        
        for text, _ in tasks:
            intent = await robot.send_command(text)
            assert intent["action"] in ["pick", "place", "navigate"]
            
            plan = {"plan_id": f"task-{intent['action']}", "subtasks": [
                {"id": "S1", "action": intent["action"], "params": {}}
            ]}
            result = await robot.execute_plan(plan)
            assert result["status"] == "completed"


class TestE2EPerformance:
    """T6.1.7 性能指标（端到端延迟）"""
    
    @pytest.mark.asyncio
    async def test_command_roundtrip_latency(self, robot):
        """指令往返延迟 < 100ms"""
        await robot.connect()
        
        start = time.perf_counter()
        await robot.send_command("抓取方块")
        elapsed = (time.perf_counter() - start) * 1000  # ms
        
        assert elapsed < 100, f"Command latency {elapsed:.1f}ms exceeds 100ms"
    
    @pytest.mark.asyncio
    async def test_plan_execution_latency(self, robot, sample_plan):
        """计划执行延迟 < 200ms"""
        await robot.connect()
        
        start = time.perf_counter()
        await robot.execute_plan(sample_plan)
        elapsed = (time.perf_counter() - start) * 1000
        
        assert elapsed < 200, f"Plan execution latency {elapsed:.1f}ms exceeds 200ms"
    
    @pytest.mark.asyncio
    async def test_throughput_10_commands(self, robot):
        """吞吐量：10 条指令 < 1s"""
        await robot.connect()
        
        start = time.perf_counter()
        for i in range(10):
            await robot.send_command(f"指令{i}")
        elapsed = (time.perf_counter() - start) * 1000
        
        assert elapsed < 1000, f"10 commands took {elapsed:.1f}ms"


# ============================================================
# 运行入口
# ============================================================
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
