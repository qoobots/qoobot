"""接管权限管理 — 多操作员权限与优先级控制

管理操作员角色、权限矩阵和接管请求的申请/审批流程。
支持 VIEWER/OPERATOR/SUPERVISOR/ADMIN 四级角色和优先级抢占。

对应功能 TAK-03（权限管理）。
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class OperatorRole(Enum):
    """操作员角色"""
    VIEWER = "viewer"           # 只读观察者
    OPERATOR = "operator"       # 操作员（需申请接管）
    SUPERVISOR = "supervisor"   # 监督员（可审批接管）
    ADMIN = "admin"             # 管理员（最高权限）


class TakeoverRequestStatus(Enum):
    """接管请求状态"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    REVOKED = "revoked"


@dataclass
class Operator:
    """操作员信息"""
    operator_id: str
    name: str
    role: OperatorRole = OperatorRole.VIEWER
    priority: int = 0                    # 优先级（越高越优先，0-100）
    allowed_robots: list[str] = field(default_factory=list)  # * 表示全部
    session_id: str = ""
    online: bool = False
    last_active: float = 0.0
    created_at: float = field(default_factory=time.time)

    @property
    def can_control(self) -> bool:
        """是否可操控"""
        return self.role in (OperatorRole.OPERATOR, OperatorRole.SUPERVISOR, OperatorRole.ADMIN)

    @property
    def can_approve(self) -> bool:
        """是否可审批"""
        return self.role in (OperatorRole.SUPERVISOR, OperatorRole.ADMIN)

    @property
    def can_manage(self) -> bool:
        """是否可管理权限"""
        return self.role == OperatorRole.ADMIN

    def to_dict(self) -> dict:
        return {
            "operator_id": self.operator_id,
            "name": self.name,
            "role": self.role.value,
            "priority": self.priority,
            "allowed_robots": self.allowed_robots,
            "session_id": self.session_id,
            "online": self.online,
            "last_active": self.last_active,
            "created_at": self.created_at,
        }


@dataclass
class TakeoverRequest:
    """接管请求"""
    request_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    operator_id: str = ""
    operator_name: str = ""
    robot_id: str = ""
    priority: int = 0
    reason: str = ""
    status: TakeoverRequestStatus = TakeoverRequestStatus.PENDING
    created_at: float = field(default_factory=time.time)
    resolved_at: float = 0.0
    resolved_by: str = ""
    expiration_seconds: int = 30              # 请求超时时间

    def is_expired(self) -> bool:
        if self.status != TakeoverRequestStatus.PENDING:
            return False
        return time.time() - self.created_at > self.expiration_seconds

    def to_dict(self) -> dict:
        return {
            "request_id": self.request_id,
            "operator_id": self.operator_id,
            "operator_name": self.operator_name,
            "robot_id": self.robot_id,
            "priority": self.priority,
            "reason": self.reason,
            "status": self.status.value,
            "created_at": self.created_at,
            "resolved_at": self.resolved_at,
            "resolved_by": self.resolved_by,
        }


class TakeoverPermissionManager:
    """接管权限管理器

    管理操作员列表、权限矩阵和接管请求的审批流程。
    支持：
    - 操作员 CRUD
    - 角色/优先级管理
    - 接管请求排队与审批
    - 权限检查（是否可操控特定机器人）
    - 活动操作员跟踪

    对应功能 TAK-03（权限管理）。
    """

    def __init__(self) -> None:
        self._operators: dict[str, Operator] = {}
        self._pending_requests: dict[str, TakeoverRequest] = {}
        self._request_history: list[TakeoverRequest] = []
        self._active_operator_id: Optional[str] = None  # 当前控制者
        self._active_robot_id: Optional[str] = None
        self._request_timeout: int = 60  # 默认60秒超时

        # 回调
        self._on_request_created: Optional[callable] = None
        self._on_request_resolved: Optional[callable] = None
        self._on_operator_changed: Optional[callable] = None
        self._on_control_transferred: Optional[callable] = None

    # ------------------------------------------------------------------
    # 操作员管理
    # ------------------------------------------------------------------

    @property
    def operators(self) -> list[Operator]:
        return list(self._operators.values())

    @property
    def online_operators(self) -> list[Operator]:
        return [op for op in self._operators.values() if op.online]

    @property
    def active_operator_id(self) -> Optional[str]:
        return self._active_operator_id

    @property
    def active_robot_id(self) -> Optional[str]:
        return self._active_robot_id

    def add_operator(self, name: str, role: OperatorRole = OperatorRole.VIEWER,
                     priority: int = 0, allowed_robots: Optional[list[str]] = None) -> Operator:
        """添加操作员"""
        op = Operator(
            operator_id=str(uuid.uuid4())[:8],
            name=name,
            role=role,
            priority=priority,
            allowed_robots=allowed_robots or [],
        )
        self._operators[op.operator_id] = op
        self._notify_operator_changed("added", op)
        return op

    def remove_operator(self, operator_id: str) -> bool:
        """移除操作员"""
        if operator_id not in self._operators:
            return False
        op = self._operators.pop(operator_id)
        # 撤销该操作员的待处理请求
        to_remove = [
            rid for rid, req in self._pending_requests.items()
            if req.operator_id == operator_id
        ]
        for rid in to_remove:
            self._pending_requests.pop(rid, None)
        self._notify_operator_changed("removed", op)
        return True

    def update_operator(self, operator_id: str, **kwargs) -> Optional[Operator]:
        """更新操作员属性"""
        op = self._operators.get(operator_id)
        if op is None:
            return None
        for key, value in kwargs.items():
            if hasattr(op, key):
                setattr(op, key, value)
        self._notify_operator_changed("updated", op)
        return op

    def set_operator_online(self, operator_id: str, online: bool,
                            session_id: str = "") -> Optional[Operator]:
        """设置操作员在线状态"""
        op = self._operators.get(operator_id)
        if op is None:
            return None
        op.online = online
        op.last_active = time.time()
        if session_id:
            op.session_id = session_id
        self._notify_operator_changed("status", op)
        return op

    def get_operator(self, operator_id: str) -> Optional[Operator]:
        return self._operators.get(operator_id)

    # ------------------------------------------------------------------
    # 权限检查
    # ------------------------------------------------------------------

    def can_control_robot(self, operator_id: str, robot_id: str) -> tuple[bool, str]:
        """检查操作员是否可以操控指定机器人

        Returns:
            (allowed, reason)
        """
        op = self._operators.get(operator_id)
        if op is None:
            return False, "操作员不存在"
        if not op.online:
            return False, "操作员不在线"
        if not op.can_control:
            return False, f"角色 {op.role.value} 无操控权限"
        if op.allowed_robots and "*" not in op.allowed_robots and robot_id not in op.allowed_robots:
            return False, f"未授权操控机器人 {robot_id}"
        return True, ""

    def can_takeover_now(self, operator_id: str, robot_id: str) -> tuple[bool, str]:
        """检查是否可以立即接管（不需要排队审批）

        条件：
        1. 当前无人控制该机器人
        2. 或操作员优先级高于当前控制者
        3. 或操作员是 ADMIN/SUPERVISOR
        """
        allowed, reason = self.can_control_robot(operator_id, robot_id)
        if not allowed:
            return False, reason

        op = self._operators[operator_id]

        # 当前无人控制
        if self._active_operator_id is None or self._active_robot_id != robot_id:
            return True, ""

        # 自己已控制
        if self._active_operator_id == operator_id:
            return True, ""

        # 当前控制者信息
        current = self._operators.get(self._active_operator_id)
        if current is None:
            return True, ""

        # ADMIN 可抢占任何人
        if op.role == OperatorRole.ADMIN:
            return True, "管理员权限抢占"

        # SUPERVISOR 可抢占非 ADMIN
        if op.role == OperatorRole.SUPERVISOR and current.role != OperatorRole.ADMIN:
            return True, "监督员权限抢占"

        # 优先级比较
        if op.priority > current.priority:
            return True, f"优先级抢占 ({op.priority} > {current.priority})"

        return False, f"需要审批（当前控制者: {current.name}）"

    # ------------------------------------------------------------------
    # 接管请求管理
    # ------------------------------------------------------------------

    @property
    def pending_requests(self) -> list[TakeoverRequest]:
        # 清理过期请求
        expired = [rid for rid, req in self._pending_requests.items() if req.is_expired()]
        for rid in expired:
            req = self._pending_requests.pop(rid)
            req.status = TakeoverRequestStatus.EXPIRED
            self._request_history.append(req)
        return list(self._pending_requests.values())

    @property
    def request_history(self) -> list[TakeoverRequest]:
        return list(self._request_history)

    def create_request(self, operator_id: str, robot_id: str,
                       reason: str = "") -> Optional[TakeoverRequest]:
        """创建接管请求"""
        op = self._operators.get(operator_id)
        if op is None:
            return None

        # 检查是否可以立即接管
        can_takeover, msg = self.can_takeover_now(operator_id, robot_id)
        if can_takeover:
            # 直接接管，不创建请求
            self._transfer_control(operator_id, robot_id)
            return None

        req = TakeoverRequest(
            operator_id=operator_id,
            operator_name=op.name,
            robot_id=robot_id,
            priority=op.priority,
            reason=reason,
            expiration_seconds=self._request_timeout,
        )
        self._pending_requests[req.request_id] = req
        if self._on_request_created:
            self._on_request_created(req)
        return req

    def approve_request(self, request_id: str, approver_id: str) -> bool:
        """审批通过接管请求"""
        req = self._pending_requests.get(request_id)
        if req is None or req.status != TakeoverRequestStatus.PENDING:
            return False

        approver = self._operators.get(approver_id)
        if approver is None or not approver.can_approve:
            return False

        req.status = TakeoverRequestStatus.APPROVED
        req.resolved_at = time.time()
        req.resolved_by = approver_id
        self._pending_requests.pop(request_id)
        self._request_history.append(req)

        # 转移控制权
        self._transfer_control(req.operator_id, req.robot_id)

        if self._on_request_resolved:
            self._on_request_resolved(req)
        return True

    def reject_request(self, request_id: str, approver_id: str,
                       reason: str = "") -> bool:
        """拒绝接管请求"""
        req = self._pending_requests.get(request_id)
        if req is None or req.status != TakeoverRequestStatus.PENDING:
            return False

        approver = self._operators.get(approver_id)
        if approver is None or not approver.can_approve:
            return False

        req.status = TakeoverRequestStatus.REJECTED
        req.resolved_at = time.time()
        req.resolved_by = approver_id
        req.reason = f"{req.reason} [拒绝原因: {reason}]" if reason else req.reason
        self._pending_requests.pop(request_id)
        self._request_history.append(req)

        if self._on_request_resolved:
            self._on_request_resolved(req)
        return True

    def revoke_request(self, request_id: str, operator_id: str) -> bool:
        """撤销自己的接管请求"""
        req = self._pending_requests.get(request_id)
        if req is None or req.operator_id != operator_id:
            return False

        req.status = TakeoverRequestStatus.REVOKED
        req.resolved_at = time.time()
        self._pending_requests.pop(request_id)
        self._request_history.append(req)
        return True

    def release_control(self, operator_id: str, robot_id: str) -> bool:
        """释放控制权"""
        if self._active_operator_id != operator_id:
            return False
        if self._active_robot_id != robot_id:
            return False
        self._active_operator_id = None
        self._active_robot_id = None
        return True

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    def _transfer_control(self, operator_id: str, robot_id: str) -> None:
        """转移控制权"""
        previous_id = self._active_operator_id
        self._active_operator_id = operator_id
        self._active_robot_id = robot_id
        if self._on_control_transferred:
            self._on_control_transferred(previous_id, operator_id, robot_id)

    # ------------------------------------------------------------------
    # 回调设置
    # ------------------------------------------------------------------

    def set_callbacks(self,
                      on_request_created: Optional[callable] = None,
                      on_request_resolved: Optional[callable] = None,
                      on_operator_changed: Optional[callable] = None,
                      on_control_transferred: Optional[callable] = None) -> None:
        """设置回调函数"""
        self._on_request_created = on_request_created
        self._on_request_resolved = on_request_resolved
        self._on_operator_changed = on_operator_changed
        self._on_control_transferred = on_control_transferred

    def _notify_operator_changed(self, action: str, op: Operator) -> None:
        if self._on_operator_changed:
            self._on_operator_changed(action, op)

    # ------------------------------------------------------------------
    # 统计
    # ------------------------------------------------------------------

    def get_statistics(self) -> dict:
        """获取权限管理统计"""
        roles = {"viewer": 0, "operator": 0, "supervisor": 0, "admin": 0}
        for op in self._operators.values():
            roles[op.role.value] = roles.get(op.role.value, 0) + 1

        statuses = {"pending": 0, "approved": 0, "rejected": 0, "expired": 0, "revoked": 0}
        for req in self._request_history:
            statuses[req.status.value] = statuses.get(req.status.value, 0) + 1

        return {
            "total_operators": len(self._operators),
            "online_operators": len(self.online_operators),
            "by_role": roles,
            "active_operator_id": self._active_operator_id,
            "active_robot_id": self._active_robot_id,
            "pending_requests": len(self._pending_requests),
            "request_history": statuses,
            "total_requests": len(self._request_history),
        }
