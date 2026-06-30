"""关节状态表控件 — 实时显示所有关节的状态数据

以表格形式展示多关节的位置/速度/力矩/温度/电流，
支持颜色编码（正常/警告/错误）和排序。

对应功能 DASH-04（关节状态面板）。
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QBrush
from PySide6.QtWidgets import (
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from console.core.models.joint_state import JointState, JointStatus
from console.core.utils.units import rad_to_deg


class JointTable(QWidget):
    """关节状态表格

    以 QTableWidget 展示所有关节的实时数据，
    表头：名称 | 位置(°) | 速度(°/s) | 力矩(Nm) | 温度(°C) | 电流(A) | 状态
    """

    COLUMNS = [
        ("名称", 100),
        ("位置°", 70),
        ("速度°/s", 70),
        ("力矩 Nm", 70),
        ("温度°C", 65),
        ("电流 A", 60),
        ("状态", 60),
    ]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._table = QTableWidget()
        self._table.setColumnCount(len(self.COLUMNS))
        self._table.setHorizontalHeaderLabels([c[0] for c in self.COLUMNS])

        # 表头设置
        header = self._table.horizontalHeader()
        for i, (_, width) in enumerate(self.COLUMNS):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Fixed)
            self._table.setColumnWidth(i, width)
        header.setStretchLastSection(True)

        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(False)

        layout.addWidget(self._table)
        self.setMinimumHeight(200)

    def update_joints(self, joints: list[JointState]) -> None:
        """更新关节列表数据"""
        self._table.setRowCount(len(joints))

        for row, joint in enumerate(joints):
            # 名称
            self._set_item(row, 0, joint.name)

            # 位置 (弧度转角度)
            deg_value = rad_to_deg(joint.position_rad)
            self._set_item(row, 1, f"{deg_value:.2f}")

            # 速度
            deg_v = rad_to_deg(joint.velocity_rad_s)
            self._set_item(row, 2, f"{deg_v:.2f}")

            # 力矩
            self._set_item(row, 3, f"{joint.torque_nm:.2f}")

            # 温度
            temp_color = None
            if joint.temperature_celsius > 70:
                temp_color = QColor("#e74c3c")
            elif joint.temperature_celsius > 50:
                temp_color = QColor("#f39c12")
            self._set_item(row, 4, f"{joint.temperature_celsius:.1f}", temp_color)

            # 电流
            self._set_item(row, 5, f"{joint.current_amps:.2f}")

            # 状态
            status_colors = {
                JointStatus.NORMAL: QColor("#2ecc71"),
                JointStatus.WARNING: QColor("#f39c12"),
                JointStatus.ERROR: QColor("#e74c3c"),
                JointStatus.DISABLED: QColor("#718093"),
                JointStatus.CALIBRATING: QColor("#3498db"),
            }
            color = status_colors.get(joint.status, QColor("#90a4ae"))
            self._set_item(row, 6, joint.status.value, color)

            # 行背景色（根据状态）
            if joint.status == JointStatus.ERROR:
                for col in range(len(self.COLUMNS)):
                    item = self._table.item(row, col)
                    if item:
                        item.setBackground(QBrush(QColor("#2a1515")))

    def _set_item(
        self, row: int, col: int, text: str, color: Optional[QColor] = None
    ) -> None:
        """设置表格单元格"""
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        if color:
            item.setForeground(QBrush(color))
        self._table.setItem(row, col, item)
