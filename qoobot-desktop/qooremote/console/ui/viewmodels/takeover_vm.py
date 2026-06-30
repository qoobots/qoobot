"""接管 ViewModel — TAK-03 权限管理 + TAK-04 接管审计

桥接 TakeoverPermissionManager 和 TakeoverAuditService 到 UI 层，
管理操作员权限、接管请求审批和审计日志查询。

对应功能 TAK-03（权限管理）、TAK-04（接管审计）。
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Optional

from PySide6.QtCore import QObject, Signal

from console.core.models.takeover_permission import (
    OperatorRole,
    TakeoverRequestStatus,
    Operator,
    TakeoverRequest,
    TakeoverPermissionManager,
)
from console.core.models.takeover_audit import (
    AuditActionType,
    AuditEntry,
    AuditQuery,
    AuditStatistics,
    TakeoverAuditStore,
    TakeoverAuditService,
)

logger = logging.getLogger(__name__)


class TakeoverViewModel(QObject):
    """接管 ViewModel

    统一管理权限（TAK-03）和审计（TAK-04）的业务逻辑。
    """

    # 权限管理信号
    operators_updated = Signal(list)              # list[dict] — 操作员列表更新
    requests_updated = Signal(list)               # list[dict] — 接管请求列表更新
    permission_changed = Signal(str)              # 权限变更消息

    # 接管请求信号
    takeover_requested = Signal(str, str, str)    # operator_id, robot_id, reason
    takeover_approved = Signal(str)               # request_id
    takeover_rejected = Signal(str)               # request_id
    control_released = Signal(str, str)           # operator_id, robot_id

    # 审计信号
    audit_query_completed = Signal(list)          # list[dict] — 审计查询结果
    audit_statistics_updated = Signal(object)     # AuditStatistics
    audit_export_completed = Signal(str, int)     # filepath, count

    # 通用信号
    error_occurred = Signal(str)
    status_message = Signal(str)

    def __init__(self, audit_store: Optional[TakeoverAuditStore] = None,
                 parent: Optional[QObject] = None) -> None:
        super().__init__(parent)

        # 核心服务
        self._perm_mgr = TakeoverPermissionManager()
        self._audit_service = TakeoverAuditService(audit_store)

        # 当前操作员（简化：单一操作员模式）
        self._current_operator: Optional[Operator] = None

        # 注册回调
        self._perm_mgr.set_callbacks(
            on_request_created=self._on_request_created,
            on_request_resolved=self._on_request_resolved,
            on_operator_changed=self._on_operator_changed,
            on_control_transferred=self._on_control_transferred,
        )

        # 初始数据
        self._init_demo_data()

    # ------------------------------------------------------------------
    # 属性
    # ------------------------------------------------------------------

    @property
    def perm_manager(self) -> TakeoverPermissionManager:
        return self._perm_mgr

    @property
    def audit_service(self) -> TakeoverAuditService:
        return self._audit_service

    @property
    def current_operator(self) -> Optional[Operator]:
        return self._current_operator

    @property
    def current_operator_id(self) -> str:
        return self._current_operator.operator_id if self._current_operator else ""

    # ------------------------------------------------------------------
    # 操作员管理 (TAK-03)
    # ------------------------------------------------------------------

    def login(self, operator_id: str) -> bool:
        """操作员登录"""
        op = self._perm_mgr.set_operator_online(operator_id, True)
        if op is None:
            self.error_occurred.emit(f"操作员 {operator_id} 不存在")
            return False
        self._current_operator = op

        self._audit_service.record_login(
            operator_id, op.name, details=f"角色: {op.role.value}"
        )
        self.status_message.emit(f"操作员 {op.name} 已登录 ({op.role.value})")
        self._refresh_operators()
        return True

    def logout(self) -> bool:
        """操作员登出"""
        if self._current_operator is None:
            return False
        op = self._current_operator
        self._perm_mgr.set_operator_online(op.operator_id, False)

        self._audit_service.record_logout(op.operator_id, op.name)
        self._current_operator = None
        self._refresh_operators()
        self.status_message.emit(f"操作员 {op.name} 已登出")
        return True

    def add_operator(self, name: str, role: str = "viewer",
                     priority: int = 0) -> Optional[dict]:
        """添加操作员"""
        try:
            r = OperatorRole(role)
        except ValueError:
            self.error_occurred.emit(f"无效角色: {role}")
            return None

        op = self._perm_mgr.add_operator(name, r, priority)
        self._audit_service.record_operator_change(
            self.current_operator_id, self._current_operator.name if self._current_operator else "system",
            "add", details=f"添加操作员: {name} ({role})", robot_id=""
        )
        self._refresh_operators()
        return op.to_dict()

    def remove_operator(self, operator_id: str) -> bool:
        """移除操作员"""
        ok = self._perm_mgr.remove_operator(operator_id)
        if ok:
            self._audit_service.record_operator_change(
                self.current_operator_id, self._current_operator.name if self._current_operator else "system",
                "remove", details=f"移除操作员: {operator_id}"
            )
            self._refresh_operators()
        return ok

    def update_operator(self, operator_id: str, **kwargs) -> bool:
        """更新操作员属性"""
        op = self._perm_mgr.update_operator(operator_id, **kwargs)
        if op:
            self._audit_service.record_operator_change(
                self.current_operator_id, self._current_operator.name if self._current_operator else "system",
                "update", details=f"更新操作员: {operator_id} {kwargs}"
            )
            self._refresh_operators()
            return True
        return False

    # ------------------------------------------------------------------
    # 接管请求管理 (TAK-03)
    # ------------------------------------------------------------------

    def request_takeover(self, robot_id: str, reason: str = "") -> Optional[str]:
        """申请接管机器人"""
        if self._current_operator is None:
            self.error_occurred.emit("请先登录")
            return None

        # 检查是否可以立即接管
        can_takeover, msg = self._perm_mgr.can_takeover_now(
            self._current_operator.operator_id, robot_id
        )

        req = self._perm_mgr.create_request(
            self._current_operator.operator_id, robot_id, reason
        )

        if req is None:
            # 直接接管成功
            self._audit_service.record_takeover(
                self._current_operator.operator_id, self._current_operator.name,
                "request", robot_id=robot_id, result="success",
                details=f"直接接管 (优先级: {self._current_operator.priority})"
            )
            self.status_message.emit(f"已接管机器人 {robot_id}")
            self.takeover_requested.emit(
                self._current_operator.operator_id, robot_id, reason
            )
            self._refresh_requests()
            return None

        # 需要审批
        self._audit_service.record_takeover(
            self._current_operator.operator_id, self._current_operator.name,
            "request", robot_id=robot_id, result="pending",
            details=f"等待审批: {reason}"
        )
        self.status_message.emit(f"接管请求已发送 (ID: {req.request_id})")
        self._refresh_requests()
        return req.request_id

    def approve_takeover(self, request_id: str) -> bool:
        """审批接管请求"""
        if self._current_operator is None:
            self.error_occurred.emit("请先登录")
            return False

        ok = self._perm_mgr.approve_request(request_id, self._current_operator.operator_id)
        if ok:
            self._audit_service.record_takeover(
                self._current_operator.operator_id, self._current_operator.name,
                "approve", details=f"审批通过: {request_id}", result="success"
            )
            self._refresh_requests()
            self.takeover_approved.emit(request_id)
        return ok

    def reject_takeover(self, request_id: str, reason: str = "") -> bool:
        """拒绝接管请求"""
        if self._current_operator is None:
            self.error_occurred.emit("请先登录")
            return False

        ok = self._perm_mgr.reject_request(
            request_id, self._current_operator.operator_id, reason
        )
        if ok:
            self._audit_service.record_takeover(
                self._current_operator.operator_id, self._current_operator.name,
                "reject", details=f"拒绝: {request_id} ({reason})", result="success"
            )
            self._refresh_requests()
            self.takeover_rejected.emit(request_id)
        return ok

    def release_control(self, robot_id: str) -> bool:
        """释放控制权"""
        if self._current_operator is None:
            return False
        ok = self._perm_mgr.release_control(self._current_operator.operator_id, robot_id)
        if ok:
            self._audit_service.record_takeover(
                self._current_operator.operator_id, self._current_operator.name,
                "release", robot_id=robot_id, result="success"
            )
            self._refresh_operators()
            self.control_released.emit(self._current_operator.operator_id, robot_id)
        return ok

    def record_emergency(self, reason: str = "operator") -> None:
        """记录紧急制动审计"""
        if self._current_operator:
            self._audit_service.record_emergency(
                self._current_operator.operator_id,
                self._current_operator.name,
                details=reason,
            )

    def record_mode_switch(self, from_mode: str, to_mode: str) -> None:
        """记录模式切换审计"""
        if self._current_operator:
            self._audit_service.record_mode_switch(
                self._current_operator.operator_id,
                self._current_operator.name,
                details=f"{from_mode} → {to_mode}",
            )

    # ------------------------------------------------------------------
    # 审计查询 (TAK-04)
    # ------------------------------------------------------------------

    def query_audit(self, params: dict) -> None:
        """查询审计日志"""
        try:
            results = self._audit_service.query(
                start_time=params.get("start_time"),
                end_time=params.get("end_time"),
                operator_ids=params.get("operator_ids"),
                action_types=params.get("action_types"),
                robot_id=params.get("robot_id"),
                session_id=params.get("session_id"),
                result=params.get("result"),
                keyword=params.get("keyword"),
                limit=params.get("limit", 200),
                offset=params.get("offset", 0),
            )
            self.audit_query_completed.emit(results)

            # 更新统计
            stats = self._audit_service.get_statistics(
                start_time=params.get("start_time"),
                end_time=params.get("end_time"),
            )
            self.audit_statistics_updated.emit(stats)

        except Exception as e:
            logger.error("Audit query failed: %s", e)
            self.error_occurred.emit(str(e))

    def refresh_audit(self) -> None:
        """刷新审计列表"""
        try:
            results = self._audit_service.get_recent(limit=100)
            self.audit_query_completed.emit(results)

            stats = self._audit_service.get_statistics()
            self.audit_statistics_updated.emit(stats)

        except Exception as e:
            self.error_occurred.emit(str(e))

    def export_audit(self, filepath: str, fmt: str = "json") -> None:
        """导出审计日志"""
        try:
            count = self._audit_service.export(filepath, fmt)
            self.audit_export_completed.emit(filepath, count)
            logger.info("Exported %d audit entries to %s", count, filepath)
        except Exception as e:
            logger.error("Audit export failed: %s", e)
            self.error_occurred.emit(str(e))

    # ------------------------------------------------------------------
    # 统计
    # ------------------------------------------------------------------

    def get_permission_stats(self) -> dict:
        """获取权限统计"""
        return self._perm_mgr.get_statistics()

    def get_audit_stats(self) -> AuditStatistics:
        """获取审计统计"""
        return self._audit_service.get_statistics()

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    def _init_demo_data(self) -> None:
        """初始化演示操作员"""
        self._perm_mgr.add_operator("管理员", OperatorRole.ADMIN, priority=100)
        self._perm_mgr.add_operator("监督员A", OperatorRole.SUPERVISOR, priority=80)
        self._perm_mgr.add_operator("操作员B", OperatorRole.OPERATOR, priority=50)
        self._perm_mgr.add_operator("观察者C", OperatorRole.VIEWER, priority=10)

        # 设置管理员在线
        admin_ops = [op for op in self._perm_mgr.operators if op.role == OperatorRole.ADMIN]
        if admin_ops:
            self._perm_mgr.set_operator_online(admin_ops[0].operator_id, True)

    def _refresh_operators(self) -> None:
        """刷新操作员列表"""
        ops = [op.to_dict() for op in self._perm_mgr.operators]
        self.operators_updated.emit(ops)

    def _refresh_requests(self) -> None:
        """刷新接管请求列表"""
        reqs = [req.to_dict() for req in self._perm_mgr.pending_requests]
        self.requests_updated.emit(reqs)

    def _on_request_created(self, req: TakeoverRequest) -> None:
        """接管请求创建回调"""
        self._refresh_requests()
        self.permission_changed.emit(
            f"新接管请求: {req.operator_name} → {req.robot_id}"
        )

    def _on_request_resolved(self, req: TakeoverRequest) -> None:
        """接管请求解决回调"""
        self._refresh_requests()
        self.permission_changed.emit(
            f"接管请求 {req.request_id}: {req.status.value}"
        )

    def _on_operator_changed(self, action: str, op: Operator) -> None:
        """操作员变更回调"""
        self._refresh_operators()

    def _on_control_transferred(self, previous_id: Optional[str],
                                new_id: str, robot_id: str) -> None:
        """控制权转移回调"""
        prev_name = ""
        if previous_id:
            prev_op = self._perm_mgr.get_operator(previous_id)
            prev_name = prev_op.name if prev_op else previous_id
        new_op = self._perm_mgr.get_operator(new_id)
        new_name = new_op.name if new_op else new_id

        self.permission_changed.emit(
            f"控制权转移: {prev_name or '无'} → {new_name} ({robot_id})"
        )
        self._refresh_operators()

    # ------------------------------------------------------------------
    # 清理
    # ------------------------------------------------------------------

    def cleanup(self) -> None:
        """清理资源"""
        if self._current_operator:
            self.logout()
        self._audit_service.close()
