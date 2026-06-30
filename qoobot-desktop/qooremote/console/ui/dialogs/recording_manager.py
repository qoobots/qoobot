"""录制管理对话框 — 录制文件浏览/删除/导出"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QHeaderView, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget, QMessageBox,
)


class RecordingManagerDialog(QDialog):
    """录制文件管理对话框"""

    export_requested = Signal(str, str)   # session_id, format

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("录制文件管理")
        self.setMinimumSize(600, 380)
        self._recordings: list[dict] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        title = QLabel("📁 录制文件列表")
        title.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(title)

        # 表格
        self._table = QTableWidget()
        self._table.setColumnCount(6)
        self._table.setHorizontalHeaderLabels([
            "会话 ID", "机器人", "操作员", "开始时间", "帧数", "格式"
        ])
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self._table)

        # 按钮行
        btn_row = QHBoxLayout()

        self._export_jsonl_btn = QPushButton("导出 JSONL")
        self._export_jsonl_btn.clicked.connect(lambda: self._on_export("jsonl"))
        btn_row.addWidget(self._export_jsonl_btn)

        self._export_h5_btn = QPushButton("导出 HDF5")
        self._export_h5_btn.clicked.connect(lambda: self._on_export("h5"))
        btn_row.addWidget(self._export_h5_btn)

        self._export_csv_btn = QPushButton("导出 CSV")
        self._export_csv_btn.clicked.connect(lambda: self._on_export("csv"))
        btn_row.addWidget(self._export_csv_btn)

        btn_row.addStretch()

        self._delete_btn = QPushButton("删除")
        self._delete_btn.setStyleSheet("QPushButton { color: #e74c3c; }")
        self._delete_btn.clicked.connect(self._on_delete)
        btn_row.addWidget(self._delete_btn)

        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)

        layout.addLayout(btn_row)

    def load_recordings(self, recordings: list[dict]) -> None:
        """加载录制列表

        Args:
            recordings: [{"session_id":..., "robot_id":..., ...}, ...]
        """
        self._recordings = recordings
        self._table.setRowCount(len(recordings))
        for row, rec in enumerate(recordings):
            self._table.setItem(row, 0, QTableWidgetItem(rec.get("session_id", "")))
            self._table.setItem(row, 1, QTableWidgetItem(rec.get("robot_id", "")))
            self._table.setItem(row, 2, QTableWidgetItem(rec.get("operator", "")))
            self._table.setItem(row, 3, QTableWidgetItem(
                str(rec.get("start_time", ""))[:19]
            ))
            self._table.setItem(row, 4, QTableWidgetItem(str(rec.get("total_frames", 0))))
            self._table.setItem(row, 5, QTableWidgetItem(rec.get("mode", "")))

    def _on_export(self, fmt: str) -> None:
        row = self._table.currentRow()
        if row < 0 or row >= len(self._recordings):
            QMessageBox.warning(self, "提示", "请先选择一条录制记录")
            return
        session_id = self._recordings[row].get("session_id", "")
        if session_id:
            self.export_requested.emit(session_id, fmt)

    def _on_delete(self) -> None:
        row = self._table.currentRow()
        if row < 0:
            return
        session_id = self._recordings[row].get("session_id", "")
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除录制会话 {session_id} 吗？此操作不可撤销。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._table.removeRow(row)
            del self._recordings[row]
