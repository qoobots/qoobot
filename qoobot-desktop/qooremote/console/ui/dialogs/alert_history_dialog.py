"""告警历史对话框 — 弹窗式告警历史浏览器

支持完整查询、筛选、统计和导出功能。

对应功能 ALT-03（告警历史）。
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QComboBox,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QDateEdit, QCheckBox, QLineEdit,
    QGroupBox, QGridLayout, QSplitter,
)

from console.core.models.alert_history import AlertHistoryService, AlertStatistics


class AlertHistoryDialog(QDialog):
    """告警历史对话框

    弹窗式告警历史管理界面，适合独立操作场景。
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("告警历史")
        self.resize(900, 650)
        self.setMinimumSize(700, 500)

        self._service = AlertHistoryService()
        self._last_query_params: dict = {}

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(8)

        # 筛选栏
        filter_group = QGroupBox("筛选条件")
        filter_layout = QGridLayout(filter_group)
        filter_layout.setSpacing(4)

        filter_layout.addWidget(QLabel("开始:"), 0, 0)
        self._start_date = QDateEdit()
        self._start_date.setCalendarPopup(True)
        filter_layout.addWidget(self._start_date, 0, 1)

        filter_layout.addWidget(QLabel("结束:"), 0, 2)
        self._end_date = QDateEdit()
        self._end_date.setCalendarPopup(True)
        filter_layout.addWidget(self._end_date, 0, 3)

        filter_layout.addWidget(QLabel("级别:"), 1, 0)
        self._level_combo = QComboBox()
        self._level_combo.addItems(["全部", "CRITICAL", "ERROR", "WARNING", "INFO"])
        filter_layout.addWidget(self._level_combo, 1, 1)

        filter_layout.addWidget(QLabel("关键词:"), 1, 2)
        self._keyword_input = QLineEdit()
        self._keyword_input.setPlaceholderText("搜索...")
        filter_layout.addWidget(self._keyword_input, 1, 3)

        self._ack_checkbox = QCheckBox("仅未确认")
        filter_layout.addWidget(self._ack_checkbox, 1, 4)

        main_layout.addWidget(filter_group)

        # 操作栏
        btn_layout = QHBoxLayout()
        self._query_btn = QPushButton("🔍 查询")
        self._query_btn.clicked.connect(self._on_query)
        btn_layout.addWidget(self._query_btn)

        self._refresh_btn = QPushButton("🔄 刷新")
        self._refresh_btn.clicked.connect(self._on_query)
        btn_layout.addWidget(self._refresh_btn)

        btn_layout.addStretch()

        self._export_json_btn = QPushButton("导出 JSON")
        self._export_json_btn.clicked.connect(lambda: self._on_export("json"))
        btn_layout.addWidget(self._export_json_btn)

        self._export_csv_btn = QPushButton("导出 CSV")
        self._export_csv_btn.clicked.connect(lambda: self._on_export("csv"))
        btn_layout.addWidget(self._export_csv_btn)

        self._close_btn = QPushButton("关闭")
        self._close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self._close_btn)

        main_layout.addLayout(btn_layout)

        # 表格
        self._table = QTableWidget()
        self._table.setColumnCount(7)
        self._table.setHorizontalHeaderLabels([
            "ID", "级别", "类型", "消息", "时间", "来源", "状态"
        ])
        self._table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setStyleSheet("""
            QTableWidget { background-color: #2b2b3d; color: #eee; gridline-color: #444; }
            QTableWidget::item { padding: 4px; }
            QHeaderView::section { background-color: #1e1e30; color: #3498db; padding: 4px; }
        """)
        main_layout.addWidget(self._table)

        # 统计栏
        self._stat_label = QLabel("就绪")
        self._stat_label.setStyleSheet("color: #888; padding: 4px;")
        main_layout.addWidget(self._stat_label)

    def _on_query(self) -> None:
        """执行查询"""
        params: dict = {}

        from datetime import datetime
        st = self._start_date.dateTime().toPython()
        et = self._end_date.dateTime().toPython()
        if st:
            params["start_time"] = int(datetime.combine(st, datetime.min.time()).timestamp() * 1000)
        if et:
            params["end_time"] = int(datetime.combine(et, datetime.max.time()).timestamp() * 1000)

        level_text = self._level_combo.currentText()
        if level_text != "全部":
            from console.core.models.alert import AlertLevel
            params["levels"] = [AlertLevel(level_text.lower())]

        kw = self._keyword_input.text().strip()
        if kw:
            params["keyword"] = kw

        if self._ack_checkbox.isChecked():
            params["acknowledged"] = False

        params["limit"] = 500
        self._last_query_params = params

        try:
            results = self._service.query_alerts(**params)
            self._populate_table(results)

            stats = self._service.get_statistics(
                start_time=params.get("start_time"),
                end_time=params.get("end_time"),
            )
            self._update_stat_label(stats, len(results))
        except Exception as e:
            self._stat_label.setText(f"查询失败: {e}")

    def _populate_table(self, alerts: list[dict]) -> None:
        """填充表格"""
        self._table.setRowCount(len(alerts))

        level_colors = {
            "critical": "#e74c3c", "error": "#e67e22",
            "warning": "#f1c40f", "info": "#3498db",
        }

        for row, a in enumerate(alerts):
            self._table.setItem(row, 0, QTableWidgetItem(str(a.get("id", ""))[:12]))
            level = a.get("level", "info")
            item = QTableWidgetItem(level.upper())
            from PySide6.QtGui import QColor, QFont
            item.setForeground(QColor(level_colors.get(level, "#ddd")))
            item.setFont(QFont("", -1, QFont.Weight.Bold))
            self._table.setItem(row, 1, item)
            self._table.setItem(row, 2, QTableWidgetItem(str(a.get("type", ""))))
            self._table.setItem(row, 3, QTableWidgetItem(str(a.get("message", ""))))

            ts = a.get("timestamp", 0)
            time_str = ""
            if ts:
                from datetime import datetime
                dt = datetime.fromtimestamp(ts / 1000.0)
                time_str = dt.strftime("%Y-%m-%d %H:%M:%S")
            self._table.setItem(row, 4, QTableWidgetItem(time_str))
            self._table.setItem(row, 5, QTableWidgetItem(str(a.get("source", ""))))
            self._table.setItem(row, 6, QTableWidgetItem(
                "已确认" if a.get("acknowledged") else "待确认"
            ))

    def _update_stat_label(self, stats: AlertStatistics, shown: int) -> None:
        """更新统计标签"""
        parts = [
            f"共 {stats.total_count} 条",
            f"严重: {stats.by_level.get('critical', 0)}",
            f"未确认: {stats.unacknowledged_count}",
            f"显示: {shown}",
        ]
        self._stat_label.setText(" | ".join(parts))

    def _on_export(self, fmt: str) -> None:
        """导出"""
        from PySide6.QtWidgets import QFileDialog
        filepath, _ = QFileDialog.getSaveFileName(
            self, f"导出 ({fmt.upper()})",
            f"alerts_export.{fmt}",
        )
        if filepath:
            try:
                count = self._service.export(filepath, fmt)
                self._stat_label.setText(f"已导出 {count} 条 → {filepath}")
            except Exception as e:
                self._stat_label.setText(f"导出失败: {e}")

    def closeEvent(self, event) -> None:
        self._service.close()
        super().closeEvent(event)
