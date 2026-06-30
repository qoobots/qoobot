"""告警列表控件 — 实时显示活跃告警

以列表形式展示当前活跃告警，支持按级别筛选、
告警确认和清除操作。

对应功能 ALT-01（异常事件推送）。
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QBrush
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QSizePolicy,
)

from console.core.models.alert import Alert, AlertLevel, AlertManager


class AlertList(QWidget):
    """告警列表

    实时显示活跃告警，支持：
    - 按级别颜色标注
    - 告警确认
    - 告警清除
    - 严重度统计
    """

    alert_acknowledged = Signal(str)   # alert_id
    alert_cleared = Signal(str)        # alert_id

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # 统计栏
        stats_layout = QHBoxLayout()
        self._total_label = QLabel("告警: 0")
        stats_layout.addWidget(self._total_label)

        self._critical_label = QLabel("")
        self._critical_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
        stats_layout.addWidget(self._critical_label)

        self._error_label = QLabel("")
        self._error_label.setStyleSheet("color: #e67e22;")
        stats_layout.addWidget(self._error_label)

        self._warning_label = QLabel("")
        self._warning_label.setStyleSheet("color: #f1c40f;")
        stats_layout.addWidget(self._warning_label)

        stats_layout.addStretch()
        layout.addLayout(stats_layout)

        # 告警列表
        self._list = QListWidget()
        self._list.setAlternatingRowColors(False)
        self._list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self._list.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self._list)

        # 操作按钮
        btn_layout = QHBoxLayout()

        self._ack_btn = QPushButton("确认")
        self._ack_btn.clicked.connect(self._on_acknowledge)
        self._ack_btn.setFixedWidth(70)
        btn_layout.addWidget(self._ack_btn)

        self._clear_btn = QPushButton("清除")
        self._clear_btn.clicked.connect(self._on_clear)
        self._clear_btn.setFixedWidth(70)
        btn_layout.addWidget(self._clear_btn)

        btn_layout.addStretch()

        self._clear_all_btn = QPushButton("清除全部")
        self._clear_all_btn.clicked.connect(self._on_clear_all)
        self._clear_all_btn.setFixedWidth(80)
        btn_layout.addWidget(self._clear_all_btn)

        layout.addLayout(btn_layout)

    def update_alerts(self, alerts: list[Alert]) -> None:
        """用告警列表刷新显示"""
        self._list.clear()

        critical_count = 0
        error_count = 0
        warning_count = 0

        for alert in alerts:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, alert.id)

            # 文本
            timestamp = datetime.fromtimestamp(alert.timestamp / 1000.0)
            time_str = timestamp.strftime("%H:%M:%S")
            text = f"[{time_str}] {alert.message}"
            if alert.source:
                text += f" ({alert.source})"
            if alert.acknowledged:
                text += " [已确认]"
            item.setText(text)

            # 根据级别设置图标颜色
            level_colors = {
                AlertLevel.CRITICAL: QColor("#e74c3c"),
                AlertLevel.ERROR: QColor("#e67e22"),
                AlertLevel.WARNING: QColor("#f1c40f"),
                AlertLevel.INFO: QColor("#3498db"),
            }
            color = level_colors.get(alert.level, QColor("#90a4ae"))

            # 左边框颜色（通过设置前景色模拟）
            item.setForeground(QBrush(color))

            # 如果已确认，设置半透明
            if alert.acknowledged:
                item.setForeground(QBrush(color.darker(150)))

            self._list.addItem(item)

            if alert.level == AlertLevel.CRITICAL:
                critical_count += 1
            elif alert.level == AlertLevel.ERROR:
                error_count += 1
            elif alert.level == AlertLevel.WARNING:
                warning_count += 1

        # 更新统计标签
        self._total_label.setText(f"告警: {len(alerts)}")
        self._critical_label.setText(
            f"严重: {critical_count}" if critical_count > 0 else ""
        )
        self._error_label.setText(
            f"错误: {error_count}" if error_count > 0 else ""
        )
        self._warning_label.setText(
            f"警告: {warning_count}" if warning_count > 0 else ""
        )

    def _get_selected_alert_id(self) -> Optional[str]:
        """获取当前选中告警 ID"""
        item = self._list.currentItem()
        if item:
            return item.data(Qt.ItemDataRole.UserRole)
        return None

    def _on_item_double_clicked(self, item: QListWidgetItem) -> None:
        """双击确认告警"""
        alert_id = item.data(Qt.ItemDataRole.UserRole)
        if alert_id:
            self.alert_acknowledged.emit(alert_id)

    def _on_acknowledge(self) -> None:
        """确认选中告警"""
        alert_id = self._get_selected_alert_id()
        if alert_id:
            self.alert_acknowledged.emit(alert_id)

    def _on_clear(self) -> None:
        """清除选中告警"""
        alert_id = self._get_selected_alert_id()
        if alert_id:
            self.alert_cleared.emit(alert_id)

    def _on_clear_all(self) -> None:
        """清除所有告警"""
        for i in range(self._list.count()):
            item = self._list.item(i)
            alert_id = item.data(Qt.ItemDataRole.UserRole)
            if alert_id:
                self.alert_cleared.emit(alert_id)
