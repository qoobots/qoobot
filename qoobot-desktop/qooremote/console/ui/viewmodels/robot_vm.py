"""机器人状态 ViewModel

作为 Dashboard 面板和 Core Service 层之间的桥梁，
管理机器人状态的接收、缓存和 UI 绑定。

采用 Qt Signal/Slot 机制驱动 UI 更新。
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QObject, Signal, QTimer

from console.core.models.robot_state import RobotState, RobotMode
from console.core.models.alert import AlertManager
from console.core.signaling.client import ConnectionState


class RobotViewModel(QObject):
    """机器人状态 ViewModel

    职责：
    - 接收 Core 层的状态推送，缓存最新状态
    - 通过 Signal 向 UI 层通知状态变更
    - 管理 UI 刷新定时器（默认 30Hz）
    - 管理告警管理器与 UI 的联动
    """

    # 信号
    state_updated = Signal(RobotState)     # 状态全量更新
    connection_changed = Signal(ConnectionState)  # 连接状态变更
    alerts_changed = Signal()              # 告警变更

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._current_state: Optional[RobotState] = None
        self._connection_state = ConnectionState.DISCONNECTED
        self._alert_manager = AlertManager()

        # UI 刷新定时器 (30Hz)
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(33)
        self._refresh_timer.timeout.connect(self._on_refresh_tick)
        self._refresh_timer.start()

        # 连接告警管理器
        self._alert_manager.add_listener(lambda a: self.alerts_changed.emit())
        self._alert_manager.add_clear_listener(lambda aid: self.alerts_changed.emit())

    @property
    def current_state(self) -> Optional[RobotState]:
        return self._current_state

    @property
    def connection_state(self) -> ConnectionState:
        return self._connection_state

    @property
    def alert_manager(self) -> AlertManager:
        return self._alert_manager

    @property
    def is_connected(self) -> bool:
        return self._connection_state in (
            ConnectionState.CONNECTED,
            ConnectionState.AUTHENTICATED,
            ConnectionState.SESSION_ACTIVE,
        )

    def on_robot_state(self, state: RobotState) -> None:
        """接收来自 Core 层的状态推送"""
        self._current_state = state

        # 处理告警
        for alert in state.alerts:
            self._alert_manager.add_alert(alert)

    def on_connection_state(self, state: ConnectionState) -> None:
        """接收连接状态变更"""
        self._connection_state = state
        self.connection_changed.emit(state)

        if state == ConnectionState.DISCONNECTED:
            self._current_state = None

    def _on_refresh_tick(self) -> None:
        """定时器触发：推送最新状态到 UI"""
        if self._current_state:
            self.state_updated.emit(self._current_state)
