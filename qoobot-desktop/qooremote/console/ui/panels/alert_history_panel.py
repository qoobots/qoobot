"""告警历史面板 — 告警查询/统计/导出

提供告警历史记录的表格展示、按条件筛选、统计概览、一键导出。

对应功能 ALT-03（告警历史）。
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QComboBox,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QDateEdit, QCheckBox, QLineEdit,
    QSplitter, QGroupBox, QGridLayout,
    QMessageBox, QFileDialog,
)


class AlertHistoryPanel(QWidget):
    """告警历史面板

    提供：
    - 顶部筛选栏（时间范围/级别/类型/关键词）
    - 统计概览卡片
    - 告警表格（分页）
    - 导出按钮
    """

    # 信号
    query_requested = Signal(dict)      # 查询请求 {start, end, levels, types, keyword}
    export_requested = Signal(str, str)  # 导出 (filepath, format)
    acknowledge_requested = Signal(str)  # 确认告警 (alert_id)
    refresh_requested = Signal()         # 刷新

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(6)

        # ---- 筛选栏 ----
        filter_group = QGroupBox("筛选条件")
        filter_layout = QGridLayout(filter_group)
        filter_layout.setSpacing(4)

        # 时间范围
        filter_layout.addWidget(QLabel("开始:"), 0, 0)
        self._start_date = QDateEdit()
        self._start_date.setCalendarPopup(True)
        self._start_date.setDisplayFormat("yyyy-MM-dd")
        filter_layout.addWidget(self._start_date, 0, 1)

        filter_layout.addWidget(QLabel("结束:"), 0, 2)
        self._end_date = QDateEdit()
        self._end_date.setCalendarPopup(True)
        self._end_date.setDisplayFormat("yyyy-MM-dd")
        filter_layout.addWidget(self._end_date, 0, 3)

        # 告警级别
        filter_layout.addWidget(QLabel("级别:"), 1, 0)
        self._level_combo = QComboBox()
        self._level_combo.addItems(["全部", "CRITICAL", "ERROR", "WARNING", "INFO"])
        filter_layout.addWidget(self._level_combo, 1, 1)

        # 关键词
        filter_layout.addWidget(QLabel("关键词:"), 1, 2)
        self._keyword_input = QLineEdit()
        self._keyword_input.setPlaceholderText("搜索告警消息...")
        filter_layout.addWidget(self._keyword_input, 1, 3)

        # 已确认过滤
        self._ack_checkbox = QCheckBox("仅显示未确认")
        filter_layout.addWidget(self._ack_checkbox, 1, 4)

        # 查询/刷新按钮
        btn_layout = QHBoxLayout()
        self._query_btn = QPushButton("🔍 查询")
        self._query_btn.clicked.connect(self._on_query)
        btn_layout.addWidget(self._query_btn)

        self._refresh_btn = QPushButton("🔄 刷新")
        self._refresh_btn.clicked.connect(lambda: self.refresh_requested.emit())
        btn_layout.addWidget(self._refresh_btn)

        self._export_json_btn = QPushButton("📄 导出 JSON")
        self._export_json_btn.clicked.connect(lambda: self._on_export("json"))
        btn_layout.addWidget(self._export_json_btn)

        self._export_csv_btn = QPushButton("📊 导出 CSV")
        self._export_csv_btn.clicked.connect(lambda: self._on_export("csv"))
        btn_layout.addWidget(self._export_csv_btn)

        btn_layout.addStretch()
        filter_layout.addLayout(btn_layout, 2, 0, 1, 5)
        main_layout.addWidget(filter_group)

        # ---- 统计概览 ----
        stats_group = QGroupBox("统计概览")
        stats_layout = QGridLayout(stats_group)
        stats_layout.setSpacing(6)

        self._total_label = QLabel("总数: 0")
        self._total_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #3498db;")
        stats_layout.addWidget(self._total_label, 0, 0)

        self._critical_label = QLabel("严重: 0")
        self._critical_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
        stats_layout.addWidget(self._critical_label, 0, 1)

        self._error_label = QLabel("错误: 0")
        self._error_label.setStyleSheet("color: #e67e22;")
        stats_layout.addWidget(self._error_label, 0, 2)

        self._warning_label = QLabel("警告: 0")
        self._warning_label.setStyleSheet("color: #f1c40f;")
        stats_layout.addWidget(self._warning_label, 0, 3)

        self._unack_label = QLabel("未确认: 0")
        self._unack_label.setStyleSheet("color: #95a5a6;")
        stats_layout.addWidget(self._unack_label, 0, 4)

        main_layout.addWidget(stats_group)

        # ---- 告警表格 ----
        self._table = QTableWidget()
        self._table.setColumnCount(7)
        self._table.setHorizontalHeaderLabels([
            "告警ID", "级别", "类型", "消息", "时间", "来源", "状态"
        ])
        self._table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setStyleSheet("""
            QTableWidget { background-color: #1a1a2e; color: #ddd; gridline-color: #333; }
            QTableWidget::item { padding: 4px; }
            QTableWidget::item:selected { background-color: #2c3e50; }
            QHeaderView::section { background-color: #16213e; color: #3498db; padding: 4px; border: none; }
        """)
        main_layout.addWidget(self._table)

        # ---- 分页 ----
        page_layout = QHBoxLayout()
        self._page_label = QLabel("第 1 页")
        page_layout.addStretch()
        page_layout.addWidget(self._page_label)
        page_layout.addStretch()
        main_layout.addLayout(page_layout)

    def _on_query(self) -> None:
        """触发查询"""
        params: dict = {}

        # 时间范围
        start_dt = self._start_date.dateTime().toPython()
        end_dt = self._end_date.dateTime().toPython()
        if start_dt:
            params["start_time"] = int(start_dt.timestamp() * 1000)
        if end_dt:
            params["end_time"] = int(end_dt.replace(hour=23, minute=59, second=59).timestamp() * 1000)

        # 级别
        level_text = self._level_combo.currentText()
        if level_text != "全部":
            from console.core.models.alert import AlertLevel
            params["levels"] = [AlertLevel(level_text.lower())]

        # 关键词
        kw = self._keyword_input.text().strip()
        if kw:
            params["keyword"] = kw

        # 确认状态
        if self._ack_checkbox.isChecked():
            params["acknowledged"] = False

        self.query_requested.emit(params)

    def _on_export(self, fmt: str) -> None:
        """触发导出"""
        filepath, _ = QFileDialog.getSaveFileName(
            self, f"导出告警历史 ({fmt.upper()})",
            f"alerts_export.{fmt}",
            f"{fmt.upper()} Files (*.{fmt})"
        )
        if filepath:
            self.export_requested.emit(filepath, fmt)

    def update_statistics(self, stats: dict) -> None:
        """更新统计概览"""
        self._total_label.setText(f"总数: {stats.get('total_count', 0)}")
        self._critical_label.setText(f"严重: {stats.get('by_level', {}).get('critical', 0)}")
        self._error_label.setText(f"错误: {stats.get('by_level', {}).get('error', 0)}")
        self._warning_label.setText(f"警告: {stats.get('by_level', {}).get('warning', 0)}")
        self._unack_label.setText(f"未确认: {stats.get('unacknowledged', 0)}")

    def populate_table(self, alerts: list[dict]) -> None:
        """填充表格数据"""
        self._table.setRowCount(len(alerts))

        for row, alert in enumerate(alerts):
            # ID
            item = QTableWidgetItem(alert.get("id", "")[:12])
            item.setFont(QFont("monospace", 9))
            self._table.setItem(row, 0, item)

            # 级别（带颜色）
            level = alert.get("level", "info")
            level_item = QTableWidgetItem(level.upper())
            level_colors = {
                "critical": QColor("#e74c3c"), "error": QColor("#e67e22"),
                "warning": QColor("#f1c40f"), "info": QColor("#3498db"),
            }
            level_item.setForeground(level_colors.get(level, QColor("#ddd")))
            level_item.setFont(QFont("sans-serif", 9, QFont.Weight.Bold))
            self._table.setItem(row, 1, level_item)

            # 类型
            self._table.setItem(row, 2, QTableWidgetItem(alert.get("type", "")))

            # 消息
            self._table.setItem(row, 3, QTableWidgetItem(alert.get("message", "")))

            # 时间
            ts = alert.get("timestamp", 0)
            time_str = ""
            if ts:
                dt = datetime.fromtimestamp(ts / 1000.0)
                time_str = dt.strftime("%Y-%m-%d %H:%M:%S")
            self._table.setItem(row, 4, QTableWidgetItem(time_str))

            # 来源
            self._table.setItem(row, 5, QTableWidgetItem(alert.get("source", "")))

            # 状态
            ack = alert.get("acknowledged", True)
            status = "✅ 已确认" if ack else "⚠ 待确认"
            status_item = QTableWidgetItem(status)
            if not ack:
                status_item.setForeground(QColor("#f1c40f"))
            self._table.setItem(row, 6, status_item)
