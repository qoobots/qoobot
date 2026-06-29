"""规划与执行数据类型。

包括计划、行为树、执行步骤、HITL 选项等。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

from brain_os.types.enums import PlanState


class PlanPhase(Enum):
    """计划执行阶段。"""

    IDLE = "idle"
    COGNITION = "cognition"
    PLANNING = "planning"
    HITL = "hitl"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class BehaviorTreeNode:
    """行为树节点。

    Attributes:
        id: 节点唯一标识
        type: 节点类型 (Sequence, Fallback, Action, Condition, Decorator, Parallel)
        name: 节点名称 (操作名)
        parameters: 节点参数
        children: 子节点 ID 列表
        blackboard_keys: 使用的黑板键
    """

    id: str = ""
    type: str = ""
    name: str = ""
    parameters: Dict[str, str] = field(default_factory=dict)
    children: List[str] = field(default_factory=list)
    blackboard_keys: List[str] = field(default_factory=list)


@dataclass
class BehaviorTree:
    """行为树。

    Attributes:
        id: 行为树唯一标识
        plan_id: 所属计划 ID
        root_id: 根节点 ID
        nodes: 节点列表
        xml: BT XML 字符串 (可序列化/加载)
    """

    id: str = ""
    plan_id: str = ""
    root_id: str = ""
    nodes: List[BehaviorTreeNode] = field(default_factory=list)
    xml: str = ""


@dataclass
class ExecutionStep:
    """执行步骤快照。

    Attributes:
        step_index: 步骤序号
        node_id: 执行的 BT 节点 ID
        status: 节点状态 (SUCCESS, FAILURE, RUNNING)
        timestamp_ms: 时间戳
        message: 人类可读描述
    """

    step_index: int = 0
    node_id: str = ""
    status: str = ""
    timestamp_ms: int = 0
    message: str = ""


@dataclass
class ExecutionResult:
    """执行结果。

    Attributes:
        plan_id: 计划 ID
        state: 最终状态
        steps: 执行步骤时间线
        total_duration_sec: 总耗时
        error_message: 错误描述 (失败时)
    """

    plan_id: str = ""
    state: PlanState = PlanState.IDLE
    steps: List[ExecutionStep] = field(default_factory=list)
    total_duration_sec: float = 0.0
    error_message: str = ""


@dataclass
class HITLOption:
    """人机协同选项。

    Attributes:
        option_id: 选项唯一标识
        description: 选项描述 (人类可读)
        trajectory_id: 关联的轨迹 ID
        score: 综合评分 (0-100)
        dimensions: 多维度评分 {"safety": 90, "speed": 70, ...}
    """

    option_id: str = ""
    description: str = ""
    trajectory_id: str = ""
    score: float = 0.0
    dimensions: Dict[str, float] = field(default_factory=dict)


@dataclass
class HITLCriteria:
    """HITL 触发条件。

    Attributes:
        min_confidence: 置信度低于此值触发 HITL
        max_risk_score: 风险评分高于此值触发 HITL
        require_approval: 始终需要审批的操作列表
        timeout_sec: HITL 等待超时
    """

    min_confidence: float = 0.8
    max_risk_score: float = 5.0
    require_approval: List[str] = field(default_factory=list)
    timeout_sec: float = 30.0


@dataclass
class Plan:
    """执行计划。

    Attributes:
        id: 计划唯一标识
        intent_id: 关联的意图 ID
        tree: 行为树
        phase: 当前执行阶段
        state: 计划状态
        hitl_options: HITL 选项列表 (需要人工决策时)
        created_at_ms: 创建时间戳
    """

    id: str = ""
    intent_id: str = ""
    tree: Optional[BehaviorTree] = None
    phase: PlanPhase = PlanPhase.IDLE
    state: PlanState = PlanState.IDLE
    hitl_options: List[HITLOption] = field(default_factory=list)
    created_at_ms: int = 0
