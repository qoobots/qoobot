"""连接对话框 — 配置 WebSocket 连接参数

支持字段：机器人 ID、服务器地址、端口、JWT Token、TURN 配置。
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QFormLayout, QHBoxLayout, QLineEdit, QPushButton,
    QSpinBox, QVBoxLayout, QWidget, QGroupBox, QLabel, QCheckBox,
)


class ConnectionDialog(QDialog):
    """连接配置对话框"""

    connect_requested = Signal(dict)  # 连接参数字典

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("连接到机器人")
        self.setMinimumSize(420, 350)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        # 标题
        title = QLabel("🔗 建立遥控连接")
        title.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 8px;")
        layout.addWidget(title)

        # ---- 基本连接参数 ----
        basic_group = QGroupBox("连接参数")
        form = QFormLayout(basic_group)

        self._robot_id = QLineEdit()
        self._robot_id.setPlaceholderText("例如: qoobot-01")
        form.addRow("机器人 ID:", self._robot_id)

        self._host = QLineEdit("qoocloud.local")
        self._host.setPlaceholderText("qoocloud.local")
        form.addRow("服务器地址:", self._host)

        self._port = QSpinBox()
        self._port.setRange(1, 65535)
        self._port.setValue(8443)
        form.addRow("端口:", self._port)

        self._token = QLineEdit()
        self._token.setPlaceholderText("JWT Token...")
        self._token.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("认证 Token:", self._token)

        self._secure_check = QCheckBox("使用 TLS 加密 (wss://)")
        self._secure_check.setChecked(True)
        form.addRow("", self._secure_check)

        layout.addWidget(basic_group)

        # ---- TURN 配置 ----
        turn_group = QGroupBox("TURN 中继 (可选，用于 NAT 穿透)")
        turn_form = QFormLayout(turn_group)

        self._turn_url = QLineEdit()
        self._turn_url.setPlaceholderText("turn:turn.qoocloud.local:3478")
        turn_form.addRow("TURN URL:", self._turn_url)

        self._turn_user = QLineEdit()
        self._turn_user.setPlaceholderText("用户名")
        turn_form.addRow("TURN 用户名:", self._turn_user)

        self._turn_pass = QLineEdit()
        self._turn_pass.setPlaceholderText("密码")
        self._turn_pass.setEchoMode(QLineEdit.EchoMode.Password)
        turn_form.addRow("TURN 密码:", self._turn_pass)

        layout.addWidget(turn_group)

        # ---- 按钮 ----
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        connect_btn = QPushButton("连接")
        connect_btn.setDefault(True)
        connect_btn.setStyleSheet("""
            QPushButton { background-color: #2ecc71; color: white;
                font-weight: bold; padding: 6px 16px; border-radius: 4px; }
            QPushButton:hover { background-color: #27ae60; }
        """)
        connect_btn.clicked.connect(self._on_connect)
        btn_row.addWidget(connect_btn)

        layout.addLayout(btn_row)

    def _on_connect(self) -> None:
        robot_id = self._robot_id.text().strip()
        if not robot_id:
            return

        params = {
            "robot_id": robot_id,
            "host": self._host.text().strip() or "qoocloud.local",
            "port": self._port.value(),
            "token": self._token.text().strip(),
            "tls": self._secure_check.isChecked(),
            "turn_url": self._turn_url.text().strip() or None,
            "turn_username": self._turn_user.text().strip() or None,
            "turn_password": self._turn_pass.text().strip() or None,
        }
        self.connect_requested.emit(params)
        self.accept()
