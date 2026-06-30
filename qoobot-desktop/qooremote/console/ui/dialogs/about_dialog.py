"""关于对话框 — 版本/许可证/致谢信息"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QLabel, QPushButton, QVBoxLayout, QWidget


class AboutDialog(QDialog):
    """关于对话框"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("关于 QooRemote")
        self.setFixedSize(380, 280)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(10)

        title = QLabel("QooRemote")
        title.setStyleSheet("font-size: 22px; font-weight: bold;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("远程机器人监控遥控控制台")
        subtitle.setStyleSheet("font-size: 13px; color: #888;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        layout.addSpacing(8)

        info_lines = [
            "版本: v0.3.0 (Control)",
            "平台: Python + PySide6",
            "协议: WebSocket + WebRTC",
            "许可证: Apache License 2.0",
            "",
            "© 2026 QooBot Project",
        ]
        for line in info_lines:
            lbl = QLabel(line)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet("color: #aaa; font-size: 11px;" if line else "")
            layout.addWidget(lbl)

        layout.addSpacing(12)

        close_btn = QPushButton("确定")
        close_btn.clicked.connect(self.accept)
        close_btn.setFixedWidth(100)
        btn_layout = QVBoxLayout()
        btn_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)
