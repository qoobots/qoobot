"""Brain OS gRPC/Protobuf 自动生成代码。

通过 proto_gen 包统一导出所有 gRPC stub 和 protobuf 消息类型，
屏蔽内部路径差异。

Usage:
    from brain_os.proto_gen import CognitionServiceStub
    from brain_os.proto_gen.types import ParseIntentRequest
"""

# Re-export all gRPC service stubs from flat namespace
from brain_os.proto_gen.brain_os.cognition.service_pb2_grpc import (
    CognitionServiceStub,
    CognitionServiceServicer,
)
from brain_os.proto_gen.brain_os.decision.service_pb2_grpc import (
    DecisionServiceStub,
    DecisionServiceServicer,
)
from brain_os.proto_gen.brain_os.perception.service_pb2_grpc import (
    PerceptionServiceStub,
    PerceptionServiceServicer,
)
from brain_os.proto_gen.brain_os.control.service_pb2_grpc import (
    ControlServiceStub,
    ControlServiceServicer,
)
from brain_os.proto_gen.brain_os.safety.service_pb2_grpc import (
    SafetyServiceStub,
    SafetyServiceServicer,
)
from brain_os.proto_gen.brain_os.knowledge.service_pb2_grpc import (
    KnowledgeServiceStub,
    KnowledgeServiceServicer,
)

__all__ = [
    "CognitionServiceStub",
    "CognitionServiceServicer",
    "DecisionServiceStub",
    "DecisionServiceServicer",
    "PerceptionServiceStub",
    "PerceptionServiceServicer",
    "ControlServiceStub",
    "ControlServiceServicer",
    "SafetyServiceStub",
    "SafetyServiceServicer",
    "KnowledgeServiceStub",
    "KnowledgeServiceServicer",
]
