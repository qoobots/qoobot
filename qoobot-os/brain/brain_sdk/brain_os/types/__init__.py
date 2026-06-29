"""Brain OS 公共数据类型。

包括空间几何类型、场景描述类型、运动规划类型、任务分解类型等。
"""

from brain_os.types.common import (
    Vector3,
    Quaternion,
    Pose,
    BoundingBox3D,
    RobotInfo,
    StatusResult,
)
from brain_os.types.enums import (
    StatusCode,
    IntentType,
    TaskStatus,
    PlanState,
    AlarmLevel,
    SafetyState,
)
from brain_os.types.scene import (
    SceneGraph,
    Object3D,
    SemanticLabel,
    SpatialRelation,
    SceneQuery,
    SceneQueryResult,
)
from brain_os.types.motion import (
    JointState,
    JointLimits,
    TrajectoryPoint,
    Trajectory,
    MotionCommand,
    MotionStatus,
    GripperCommand,
    CartesianPath,
)
from brain_os.types.plan import (
    Plan,
    PlanPhase,
    BehaviorTreeNode,
    BehaviorTree,
    ExecutionStep,
    ExecutionResult,
    HITLOption,
    HITLCriteria,
)
from brain_os.types.task import (
    SubTask,
    TaskDAG,
    SkillDefinition,
    SkillParameter,
    TaskDecomposition,
)

__all__ = [
    # common
    "Vector3",
    "Quaternion",
    "Pose",
    "BoundingBox3D",
    "RobotInfo",
    "StatusResult",
    # enums
    "StatusCode",
    "IntentType",
    "TaskStatus",
    "PlanState",
    "AlarmLevel",
    "SafetyState",
    # scene
    "SceneGraph",
    "Object3D",
    "SemanticLabel",
    "SpatialRelation",
    "SceneQuery",
    "SceneQueryResult",
    # motion
    "JointState",
    "JointLimits",
    "TrajectoryPoint",
    "Trajectory",
    "MotionCommand",
    "MotionStatus",
    "GripperCommand",
    "CartesianPath",
    # plan
    "Plan",
    "PlanPhase",
    "BehaviorTreeNode",
    "BehaviorTree",
    "ExecutionStep",
    "ExecutionResult",
    "HITLOption",
    "HITLCriteria",
    # task
    "SubTask",
    "TaskDAG",
    "SkillDefinition",
    "SkillParameter",
    "TaskDecomposition",
]
