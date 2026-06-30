"""接管面板 — 权限管理 + 接管审计

集成 TAK-03（权限管理）和 TAK-04（接管审计）两个功能区域，
提供操作员管理、接管请求审批、审计日志查询和导出。

对应功能 TAK-03（权限管理）、TAK-04（接管审计）。
"""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QComboBox, QLineEdit,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QTabWidget, QGroupBox, QDateEdit, QCheckBox,
    QMessageBox, QFileDialog, QSpinBox,
)


class TakeoverPanel(QWidget):
    """接管面板 — 集成权限管理与审计

    内部包含两个子标签页：
    - 🔐 权限管理：操作员列表、角色配置、接管请求队列
    - 📋 接管审计：操作日志查询、统计、导出
    """

    # 权限管理信号
    operator_add_requested = Signal(str, str, int)     # name, role, priority
    operator_remove_requested = Signal(str)             # operator_id
    operator_update_requested = Signal(str, str, str)   # operator_id, field, value
    takeover_requested = Signal(str, str)               # robot_id, reason
    takeover_approve_requested = Signal(str)            # request_id
    takeover_reject_requested = Signal(str, str)        # request_id, reason
    control_release_requested = Signal(str)             # robot_id
    login_requested = Signal(str)                       # operator_id
    logout_requested = Signal()                         # (none)

    # 审计信号
    audit_query_requested = Signal(dict)
    audit_export_requested = Signal(str, str)           # filepath, format
    audit_refresh_requested = Signal()

    # 紧急制动/模式切换审计
    emergency_record_requested = Signal(str)            # reason
    mode_switch_record_requested = Signal(str, str)     # from_mode, to_mode

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(4)

        self._tabs = QTabWidget()
        self._tabs.setObjectName("takeoverSubTabs")

        # 权限管理子面板
        self._perm_widget = self._create_permission_tab()
        self._tabs.addTab(self._perm_widget, "🔐 权限管理")

        # 审计子面板
        self._audit_widget = self._create_audit_tab()
        self._tabs.addTab(self._audit_widget, "📋 接管审计")

        main_layout.addWidget(self._tabs)

    # ==================================================================
    # 权限管理子面板 (TAK-03)
    # ==================================================================

    def _create_permission_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        # --- 当前登录 ---
        login_group = QGroupBox("当前操作员")
        login_layout = QHBoxLayout(login_group)

        self._operator_combo = QComboBox()
        self._operator_combo.setMinimumWidth(150)
        login_layout.addWidget(QLabel("选择操作员:"))
        login_layout.addWidget(self._operator_combo)

        self._login_btn = QPushButton("登录")
        self._login_btn.clicked.connect(self._on_login)
        login_layout.addWidget(self._login_btn)

        self._logout_btn = QPushButton("登出")
        self._logout_btn.setEnabled(False)
        self._logout_btn.clicked.connect(lambda: self.logout_requested.emit())
        login_layout.addWidget(self._logout_btn)

        self._login_status = QLabel("未登录")
        self._login_status.setStyleSheet("color: #95a5a6;")
        login_layout.addWidget(self._login_status)

        login_layout.addStretch()
        layout.addWidget(login_group)

        # --- 操作员列表 + 接管请求（水平分割） ---
        content_layout = QHBoxLayout()

        # 左侧：操作员列表
        left_widget = QGroupBox("操作员列表")
        left_layout = QVBoxLayout(left_widget)

        self._operator_table = QTableWidget()
        self._operator_table.setColumnCount(5)
        self._operator_table.setHorizontalHeaderLabels([
            "ID", "名称", "角色", "优先级", "状态"
        ])
        self._operator_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._operator_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._operator_table.setAlternatingRowColors(True)
        self._operator_table.verticalHeader().setVisible(False)
        self._operator_table.setMaximumHeight(250)
        self._operator_table.setStyleSheet("""
            QTableWidget { background-color: #1a1a2e; color: #ddd; gridline-color: #333; }
            QTableWidget::item { padding: 3px; }
            QTableWidget::item:selected { background-color: #2c3e50; }
            QHeaderView::section { background-color: #16213e; color: #3498db; padding: 3px; border: none; }
        """)
        left_layout.addWidget(self._operator_table)

        # 操作员管理按钮
        op_btn_layout = QHBoxLayout()

        self._add_op_name = QLineEdit()
        self._add_op_name.setPlaceholderText("操作员名称")
        op_btn_layout.addWidget(self._add_op_name)

        self._add_op_role = QComboBox()
        self._add_op_role.addItems(["viewer", "operator", "supervisor", "admin"])
        self._add_op_role.setCurrentText("viewer")
        op_btn_layout.addWidget(self._add_op_role)

        self._add_op_priority = QSpinBox()
        self._add_op_priority.setRange(0, 100)
        self._add_op_priority.setValue(0)
        self._add_op_priority.setToolTip("优先级 (0-100)")
        op_btn_layout.addWidget(self._add_op_priority)

        self._add_op_btn = QPushButton("➕ 添加")
        self._add_op_btn.clicked.connect(self._on_add_operator)
        op_btn_layout.addWidget(self._add_op_btn)

        self._remove_op_btn = QPushButton("➖ 移除")
        self._remove_op_btn.clicked.connect(self._on_remove_operator)
        op_btn_layout.addWidget(self._remove_op_btn)

        left_layout.addLayout(op_btn_layout)
        content_layout.addWidget(left_widget)  # removed stretch factor

        # 右侧：接管请求
        right_widget = QGroupBox("接管请求队列")
        right_layout = QVBoxLayout(right_widget)

        # 接管操作
        takeover_op_layout = QHBoxLayout()
        self._robot_id_input = QLineEdit()
        self._robot_id_input.setPlaceholderText("机器人ID")
        takeover_op_layout.addWidget(QLabel("目标:"))
        takeover_op_layout.addWidget(self._robot_id_input)

        self._takeover_reason = QLineEdit()
        self._takeover_reason.setPlaceholderText("接管原因")
        takeover_op_layout.addWidget(self._takeover_reason)

        self._takeover_btn = QPushButton("📥 申请接管")
        self._takeover_btn.clicked.connect(self._on_request_takeover)
        takeover_op_layout.addWidget(self._takeover_btn)

        right_layout.addLayout(takeover_op_layout)

        # 释放控制
        self._release_btn = QPushButton("🔓 释放控制")
        self._release_btn.clicked.connect(self._on_release_control)
        right_layout.addWidget(self._release_btn)

        # 请求表格
        self._request_table = QTableWidget()
        self._request_table.setColumnCount(6)
        self._request_table.setHorizontalHeaderLabels([
            "请求ID", "操作员", "机器人", "优先级", "原因", "操作"
        ])
        self._request_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self._request_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._request_table.setAlternatingRowColors(True)
        self._request_table.verticalHeader().setVisible(False)
        self._request_table.setStyleSheet("""
            QTableWidget { background-color: #1a1a2e; color: #ddd; gridline-color: #333; }
            QTableWidget::item { padding: 3px; }
            QTableWidget::item:selected { background-color: #2c3e50; }
            QHeaderView::section { background-color: #16213e; color: #e67e22; padding: 3px; border: none; }
        """)
        right_layout.addWidget(self._request_table)

        # 审批按钮
        approve_layout = QHBoxLayout()
        self._approve_btn = QPushButton("✅ 审批通过")
        self._approve_btn.clicked.connect(self._on_approve)
        approve_layout.addWidget(self._approve_btn)

        self._reject_btn = QPushButton("❌ 拒绝")
        self._reject_btn.clicked.connect(self._on_reject)
        approve_layout.addWidget(self._reject_btn)

        self._reject_reason = QLineEdit()
        self._reject_reason.setPlaceholderText("拒绝原因")
        approve_layout.addWidget(self._reject_reason)

        right_layout.addLayout(approve_layout)
        content_layout.addWidget(right_widget)

        layout.addLayout(content_layout)

        # 统计信息
        self._perm_stats_label = QLabel("操作员: 0 | 在线: 0 | 待审批: 0")
        self._perm_stats_label.setStyleSheet("color: #95a5a6; font-size: 11px;")
        layout.addWidget(self._perm_stats_label)

        return w

    # ==================================================================
    # 审计子面板 (TAK-04)
    # ==================================================================

    def _create_audit_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        # 筛选栏
        filter_group = QGroupBox("筛选条件")
        filter_layout = QGridLayout(filter_group)
        filter_layout.setSpacing(4)

        # 时间范围
        filter_layout.addWidget(QLabel("开始:"), 0, 0)
        self._audit_start_date = QDateEdit()
        self._audit_start_date.setCalendarPopup(True)
        self._audit_start_date.setDisplayFormat("yyyy-MM-dd")
        filter_layout.addWidget(self._audit_start_date, 0, 1)

        filter_layout.addWidget(QLabel("结束:"), 0, 2)
        self._audit_end_date = QDateEdit()
        self._audit_end_date.setCalendarPopup(True)
        self._audit_end_date.setDisplayFormat("yyyy-MM-dd")
        filter_layout.addWidget(self._audit_end_date, 0, 3)

        # 操作类型
        filter_layout.addWidget(QLabel("操作类型:"), 1, 0)
        self._audit_type_combo = QComboBox()
        self._audit_type_combo.addItems([
            "全部",
            "login", "logout",
            "takeover_request", "takeover_approve", "takeover_reject",
            "takeover_release", "takeover_revoke",
            "mode_switch", "emergency_stop",
            "permission_change",
            "operator_add", "operator_remove", "operator_update",
        ])
        filter_layout.addWidget(self._audit_type_combo, 1, 1)

        # 关键词
        filter_layout.addWidget(QLabel("详情搜索:"), 1, 2)
        self._audit_keyword = QLineEdit()
        self._audit_keyword.setPlaceholderText("搜索审计详情...")
        filter_layout.addWidget(self._audit_keyword, 1, 3)

        # 按钮
        btn_layout = QHBoxLayout()
        self._audit_query_btn = QPushButton("🔍 查询")
        self._audit_query_btn.clicked.connect(self._on_audit_query)
        btn_layout.addWidget(self._audit_query_btn)

        self._audit_refresh_btn = QPushButton("🔄 刷新")
        self._audit_refresh_btn.clicked.connect(
            lambda: self.audit_refresh_requested.emit()
        )
        btn_layout.addWidget(self._audit_refresh_btn)

        self._audit_export_json = QPushButton("📄 导出 JSON")
        self._audit_export_json.clicked.connect(lambda: self._on_audit_export("json"))
        btn_layout.addWidget(self._audit_export_json)

        self._audit_export_csv = QPushButton("📊 导出 CSV")
        self._audit_export_csv.clicked.connect(lambda: self._on_audit_export("csv"))
        btn_layout.addWidget(self._audit_export_csv)

        btn_layout.addStretch()
        filter_layout.addLayout(btn_layout, 2, 0, 1, 4)
        layout.addWidget(filter_group)

        # 统计概览
        stats_group = QGroupBox("审计统计")
        stats_layout = QHBoxLayout(stats_group)

        self._audit_total = QLabel("总记录: 0")
        self._audit_total.setStyleSheet("font-size: 12px; font-weight: bold; color: #3498db;")
        stats_layout.addWidget(self._audit_total)

        self._audit_operators = QLabel("活跃操作员: 0")
        self._audit_operators.setStyleSheet("color: #2ecc71;")
        stats_layout.addWidget(self._audit_operators)

        self._audit_sessions = QLabel("会话数: 0")
        self._audit_sessions.setStyleSheet("color: #f39c12;")
        stats_layout.addWidget(self._audit_sessions)

        self._audit_takeovers = QLabel("接管操作: 0")
        self._audit_takeovers.setStyleSheet("color: #e74c3c;")
        stats_layout.addWidget(self._audit_takeovers)

        stats_layout.addStretch()
        layout.addWidget(stats_group)

        # 审计表格
        self._audit_table = QTableWidget()
        self._audit_table.setColumnCount(7)
        self._audit_table.setHorizontalHeaderLabels([
            "记录ID", "时间", "操作员", "操作类型", "机器人", "详情", "结果"
        ])
        self._audit_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        self._audit_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._audit_table.setAlternatingRowColors(True)
        self._audit_table.verticalHeader().setVisible(False)
        self._audit_table.setStyleSheet("""
            QTableWidget { background-color: #1a1a2e; color: #ddd; gridline-color: #333; }
            QTableWidget::item { padding: 3px; }
            QTableWidget::item:selected { background-color: #2c3e50; }
            QHeaderView::section { background-color: #16213e; color: #3498db; padding: 3px; border: none; }
        """)
        layout.addWidget(self._audit_table)

        # 分页
        page_layout = QHBoxLayout()
        self._audit_page_label = QLabel("显示 0 条记录")
        self._audit_page_label.setStyleSheet("color: #95a5a6;")
        page_layout.addStretch()
        page_layout.addWidget(self._audit_page_label)
        page_layout.addStretch()
        layout.addLayout(page_layout)

        return w

    # ==================================================================
    # 权限管理：槽函数
    # ==================================================================

    def _on_login(self) -> None:
        op_id = self._operator_combo.currentData()
        if op_id:
            self.login_requested.emit(op_id)

    def _on_add_operator(self) -> None:
        name = self._add_op_name.text().strip()
        if not name:
            QMessageBox.warning(self, "提示", "请输入操作员名称")
            return
        role = self._add_op_role.currentText()
        priority = self._add_op_priority.value()
        self.operator_add_requested.emit(name, role, priority)
        self._add_op_name.clear()

    def _on_remove_operator(self) -> None:
        row = self._operator_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "提示", "请先选择要移除的操作员")
            return
        op_id = self._operator_table.item(row, 0).text()
        reply = QMessageBox.question(
            self, "确认", f"确定要移除操作员 {op_id} 吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.operator_remove_requested.emit(op_id)

    def _on_request_takeover(self) -> None:
        robot_id = self._robot_id_input.text().strip()
        if not robot_id:
            QMessageBox.warning(self, "提示", "请输入机器人ID")
            return
        reason = self._takeover_reason.text().strip()
        self.takeover_requested.emit(robot_id, reason)

    def _on_release_control(self) -> None:
        robot_id = self._robot_id_input.text().strip()
        if not robot_id:
            QMessageBox.warning(self, "提示", "请输入要释放的机器人ID")
            return
        self.control_release_requested.emit(robot_id)

    def _on_approve(self) -> None:
        row = self._request_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "提示", "请先选择要审批的请求")
            return
        req_id = self._request_table.item(row, 0).text()
        self.takeover_approve_requested.emit(req_id)

    def _on_reject(self) -> None:
        row = self._request_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "提示", "请先选择要拒绝的请求")
            return
        req_id = self._request_table.item(row, 0).text()
        reason = self._reject_reason.text().strip()
        self.takeover_reject_requested.emit(req_id, reason)

    # ==================================================================
    # 审计：槽函数
    # ==================================================================

    def _on_audit_query(self) -> None:
        params: dict = {}

        start_dt = self._audit_start_date.dateTime().toPython()
        end_dt = self._audit_end_date.dateTime().toPython()
        if start_dt:
            params["start_time"] = start_dt.timestamp()
        if end_dt:
            from datetime import timedelta
            params["end_time"] = (end_dt + timedelta(days=1)).timestamp()

        type_text = self._audit_type_combo.currentText()
        if type_text != "全部":
            from console.core.models.takeover_audit import AuditActionType
            params["action_types"] = [AuditActionType(type_text)]

        kw = self._audit_keyword.text().strip()
        if kw:
            params["keyword"] = kw

        params["limit"] = 200
        self.audit_query_requested.emit(params)

    def _on_audit_export(self, fmt: str) -> None:
        filepath, _ = QFileDialog.getSaveFileName(
            self, f"导出审计日志 ({fmt.upper()})",
            f"takeover_audit.{fmt}",
            f"{fmt.upper()} Files (*.{fmt})"
        )
        if filepath:
            self.audit_export_requested.emit(filepath, fmt)

    # ==================================================================
    # 数据更新接口（由 ViewModel 调用）
    # ==================================================================

    def update_operators(self, operators: list[dict]) -> None:
        """更新操作员列表"""
        self._operator_combo.clear()
        self._operator_table.setRowCount(len(operators))

        for row, op in enumerate(operators):
            # Combo
            self._operator_combo.addItem(
                f"{op['name']} [{op['role']}]", op['operator_id']
            )

            # Table
            self._operator_table.setItem(row, 0, QTableWidgetItem(op.get("operator_id", "")))

            name_item = QTableWidgetItem(op.get("name", ""))
            self._operator_table.setItem(row, 1, name_item)

            role = op.get("role", "viewer")
            role_item = QTableWidgetItem(role.upper())
            role_colors = {
                "admin": QColor("#e74c3c"),
                "supervisor": QColor("#e67e22"),
                "operator": QColor("#3498db"),
                "viewer": QColor("#95a5a6"),
            }
            role_item.setForeground(role_colors.get(role, QColor("#ddd")))
            role_item.setFont(QFont("sans-serif", 9, QFont.Weight.Bold))
            self._operator_table.setItem(row, 2, role_item)

            self._operator_table.setItem(row, 3, QTableWidgetItem(str(op.get("priority", 0))))

            online = op.get("online", False)
            status_item = QTableWidgetItem("🟢 在线" if online else "⚫ 离线")
            status_item.setForeground(QColor("#2ecc71") if online else QColor("#95a5a6"))
            self._operator_table.setItem(row, 4, status_item)

    def update_requests(self, requests: list[dict]) -> None:
        """更新接管请求列表"""
        self._request_table.setRowCount(len(requests))

        for row, req in enumerate(requests):
            req_id_item = QTableWidgetItem(req.get("request_id", "")[:8])
            req_id_item.setFont(QFont("monospace", 9))
            self._request_table.setItem(row, 0, req_id_item)

            self._request_table.setItem(row, 1, QTableWidgetItem(req.get("operator_name", "")))
            self._request_table.setItem(row, 2, QTableWidgetItem(req.get("robot_id", "")))
            self._request_table.setItem(row, 3, QTableWidgetItem(str(req.get("priority", 0))))

            reason = req.get("reason", "") or "-"
            self._request_table.setItem(row, 4, QTableWidgetItem(reason))

            # 操作按钮占位
            self._request_table.setItem(row, 5, QTableWidgetItem("待审批"))

    def update_login_status(self, logged_in: bool, operator_name: str = "") -> None:
        """更新登录状态"""
        self._login_btn.setEnabled(not logged_in)
        self._logout_btn.setEnabled(logged_in)
        if logged_in:
            self._login_status.setText(f"✅ 已登录: {operator_name}")
            self._login_status.setStyleSheet("color: #2ecc71; font-weight: bold;")
        else:
            self._login_status.setText("未登录")
            self._login_status.setStyleSheet("color: #95a5a6;")

    def update_permission_stats(self, stats: dict) -> None:
        """更新权限统计"""
        total = stats.get("total_operators", 0)
        online = stats.get("online_operators", 0)
        pending = stats.get("pending_requests", 0)
        self._perm_stats_label.setText(
            f"操作员: {total} | 在线: {online} | 待审批: {pending}"
        )

    def populate_audit_table(self, entries: list[dict]) -> None:
        """填充审计表格"""
        self._audit_table.setRowCount(len(entries))
        self._audit_page_label.setText(f"显示 {len(entries)} 条记录")

        for row, entry in enumerate(entries):
            # 记录ID
            eid = entry.get("entry_id", "")[:8]
            item = QTableWidgetItem(eid)
            item.setFont(QFont("monospace", 8))
            self._audit_table.setItem(row, 0, item)

            # 时间
            ts = entry.get("timestamp", 0)
            time_str = ""
            if ts:
                try:
                    dt = datetime.fromtimestamp(ts)
                    time_str = dt.strftime("%Y-%m-%d %H:%M:%S")
                except (ValueError, OSError):
                    time_str = str(ts)
            self._audit_table.setItem(row, 1, QTableWidgetItem(time_str))

            # 操作员
            self._audit_table.setItem(row, 2, QTableWidgetItem(
                entry.get("operator_name", entry.get("operator_id", ""))
            ))

            # 操作类型（带颜色）
            action = entry.get("action_type", "")
            action_item = QTableWidgetItem(action)
            action_colors = {
                "login": QColor("#2ecc71"),
                "logout": QColor("#95a5a6"),
                "takeover_request": QColor("#3498db"),
                "takeover_approve": QColor("#2ecc71"),
                "takeover_reject": QColor("#e74c3c"),
                "takeover_release": QColor("#f39c12"),
                "emergency_stop": QColor("#e74c3c"),
                "mode_switch": QColor("#f1c40f"),
            }
            action_item.setForeground(action_colors.get(action, QColor("#ddd")))
            self._audit_table.setItem(row, 3, action_item)

            # 机器人
            self._audit_table.setItem(row, 4, QTableWidgetItem(entry.get("robot_id", "")))

            # 详情
            self._audit_table.setItem(row, 5, QTableWidgetItem(entry.get("details", "")))

            # 结果
            result = entry.get("result", "success")
            result_item = QTableWidgetItem(result)
            result_item.setForeground(
                QColor("#2ecc71") if result == "success" else
                QColor("#f1c40f") if result == "pending" else QColor("#e74c3c")
            )
            self._audit_table.setItem(row, 6, result_item)

    def update_audit_statistics(self, stats: dict) -> None:
        """更新审计统计"""
        self._audit_total.setText(f"总记录: {stats.get('total_entries', 0)}")
        self._audit_operators.setText(f"活跃操作员: {stats.get('active_operators', 0)}")
        self._audit_sessions.setText(f"会话数: {stats.get('total_sessions', 0)}")

        # 接管操作统计
        by_action = stats.get("by_action_type", {})
        takeover_count = sum(
            by_action.get(k, 0) for k in (
                "takeover_request", "takeover_approve", "takeover_reject",
                "takeover_release", "takeover_revoke",
            )
        )
        self._audit_takeovers.setText(f"接管操作: {takeover_count}")
