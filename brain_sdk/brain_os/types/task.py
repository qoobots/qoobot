"""任务分解与技能定义数据类型。

包括子任务、任务 DAG、技能定义等。
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class SkillParameter:
    """技能参数定义。

    Attributes:
        name: 参数名称
        type: 参数类型 (string, float, int, pose, object_id)
        description: 参数说明
        required: 是否必填
        default_value: 默认值
        constraints: 约束条件 ({"min": 0, "max": 100})
    """

    name: str
    type: str = "string"
    description: str = ""
    required: bool = True
    default_value: Any = None
    constraints: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SkillDefinition:
    """技能定义。

    每个技能是机器人可执行的最小操作单元。

    Attributes:
        id: 技能唯一标识
        name: 技能名称 (e.g. "pick", "place", "navigate")
        description: 功能描述
        parameters: 参数定义列表
        preconditions: 前置条件 (自然语言)
        postconditions: 后置条件 (自然语言)
        estimated_duration_sec: 预估执行时间
        risk_level: 风险等级 (0-10)
    """

    id: str = field(default_factory=lambda: f"skill_{uuid.uuid4().hex[:8]}")
    name: str = ""
    description: str = ""
    parameters: List[SkillParameter] = field(default_factory=list)
    preconditions: List[str] = field(default_factory=list)
    postconditions: List[str] = field(default_factory=list)
    estimated_duration_sec: float = 1.0
    risk_level: int = 0


@dataclass
class SubTask:
    """子任务。

    Attributes:
        task_id: 子任务唯一标识
        skill_name: 关联的技能名称
        parameters: 实际参数值
        depends_on: 前置依赖子任务 ID 列表
        priority: 优先级 (低→高)
        timeout_sec: 超时时间
    """

    task_id: str = field(default_factory=lambda: f"sub_{uuid.uuid4().hex[:8]}")
    skill_name: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    depends_on: List[str] = field(default_factory=list)
    priority: int = 5
    timeout_sec: float = 30.0


@dataclass
class TaskDAG:
    """任务有向无环图。

    Attributes:
        id: DAG 唯一标识
        subtasks: 子任务列表 (按拓扑排序)
        metadata: 任务元数据 (复杂度、预估总时长等)
    """

    id: str = field(default_factory=lambda: f"dag_{uuid.uuid4().hex[:8]}")
    subtasks: List[SubTask] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskDecomposition:
    """任务分解结果。

    Attributes:
        intent_id: 关联的意图 ID
        utterance: 原始自然语言指令
        task_dag: 子任务 DAG
        skill_registry: 涉及的技能定义集合
        reasoning: LLM 推理链 (可选，用于调试)
    """

    intent_id: str = ""
    utterance: str = ""
    task_dag: Optional[TaskDAG] = None
    skill_registry: Dict[str, SkillDefinition] = field(default_factory=dict)
    reasoning: str = ""
