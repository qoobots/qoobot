"""仪表盘面板 — 集成所有监控控件

整合 StatusCard（CPU/内存/磁盘/温度）、BatteryGauge（电量）、
JointTable（关节状态）、SensorChart（传感器曲线）、AlertList（告警）
为一个可滚动的仪表盘视图。

对应功能：DASH-01, DASH-02, DASH-03, DASH-04, ALT-01
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QGroupBox,
    QGridLayout,
    QScrollArea,
    QVBoxLayout,
    QWidget,
    QSizePolicy,
)

from console.core.models.robot_state import RobotState
from console.core.models.alert import Alert, AlertManager
from console.ui.widgets.status_card import StatusCard, StatusCardData
from console.ui.widgets.battery_gauge import BatteryDetailPanel
from console.ui.widgets.joint_table import JointTable
from console.ui.widgets.sensor_chart import SensorChart
from console.ui.widgets.alert_list import AlertList
from console.ui.widgets.connection_indicator import ConnectionIndicator
from console.ui.widgets.emergency_button import EmergencyButton
from console.core.utils.units import bytes_to_human


class DashPanel(QScrollArea):
    """仪表盘面板

    集成所有实时监控控件，以可滚动的网格布局呈现。
    主窗口通过 set_dashboard_widget() 将此面板嵌入中央区域。
    """

    def __init__(self, alert_manager: AlertManager | None = None,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._alert_manager = alert_manager or AlertManager()

        # 内容容器
        content = QWidget()
        content.setObjectName("dashPanelContent")
        self._main_layout = QVBoxLayout(content)
        self._main_layout.setContentsMargins(8, 8, 8, 8)
        self._main_layout.setSpacing(8)

        # 系统状态区
        self._status_group = QGroupBox("系统状态")
        self._status_grid = QGridLayout(self._status_group)
        self._status_grid.setSpacing(8)

        self._cpu_card = StatusCard("CPU 使用率")
        self._memory_card = StatusCard("内存使用")
        self._disk_card = StatusCard("磁盘使用")
        self._temp_card = StatusCard("SoC 温度")
        self._uptime_card = StatusCard("运行时间")

        self._status_grid.addWidget(self._cpu_card, 0, 0)
        self._status_grid.addWidget(self._memory_card, 0, 1)
        self._status_grid.addWidget(self._disk_card, 1, 0)
        self._status_grid.addWidget(self._temp_card, 1, 1)

        self._main_layout.addWidget(self._status_group)

        # 电池 + 连接状态区
        power_conn_layout = QGridLayout()
        power_conn_layout.setSpacing(8)

        self._battery_panel = BatteryDetailPanel()
        power_conn_layout.addWidget(self._battery_panel, 0, 0)

        # 连接指示器
        conn_widget = QWidget()
        conn_layout = QVBoxLayout(conn_widget)
        self._connection_indicator = ConnectionIndicator()
        conn_layout.addWidget(self._connection_indicator, alignment=Qt.AlignmentFlag.AlignCenter)

        # 紧急制动按钮
        self._emergency_btn = EmergencyButton()
        conn_layout.addWidget(self._emergency_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        power_conn_layout.addWidget(conn_widget, 0, 1)

        self._main_layout.addLayout(power_conn_layout)

        # 关节状态区
        self._joint_group = QGroupBox("关节状态")
        joint_layout = QVBoxLayout(self._joint_group)
        self._joint_table = JointTable()
        joint_layout.addWidget(self._joint_table)
        self._main_layout.addWidget(self._joint_group)

        # 传感器曲线区
        self._sensor_group = QGroupBox("传感器数据")
        sensor_layout = QVBoxLayout(self._sensor_group)
        self._sensor_chart = SensorChart()
        sensor_layout.addWidget(self._sensor_chart)
        self._main_layout.addWidget(self._sensor_group)

        # 告警列表区
        self._alert_group = QGroupBox("告警通知")
        alert_layout = QVBoxLayout(self._alert_group)
        self._alert_list = AlertList()
        self._alert_list.alert_acknowledged.connect(self._alert_manager.acknowledge_alert)
        self._alert_list.alert_cleared.connect(self._alert_manager.clear_alert)
        alert_layout.addWidget(self._alert_list)
        self._main_layout.addWidget(self._alert_group)

        # 弹性占位
        self._main_layout.addStretch()

        self.setWidget(content)

    # ------------------------------------------------------------------
    # 公共属性
    # ------------------------------------------------------------------

    @property
    def emergency_button(self) -> EmergencyButton:
        return self._emergency_btn

    @property
    def alert_list(self) -> AlertList:
        return self._alert_list

    @property
    def connection_indicator(self) -> ConnectionIndicator:
        return self._connection_indicator

    @property
    def alert_manager(self) -> AlertManager:
        return self._alert_manager

    # ------------------------------------------------------------------
    # 数据更新接口
    # ------------------------------------------------------------------

    def update_robot_state(self, state: RobotState) -> None:
        """用 RobotState 全量刷新面板"""
        # 系统状态
        status = state.status

        # CPU
        cpu_pct = status.cpu_percent
        cpu_status = "error" if cpu_pct > 90 else ("warning" if cpu_pct > 70 else "normal")
        self._cpu_card.update_data(StatusCardData(
            title="CPU 使用率", value=f"{cpu_pct:.1f}", value_unit="%",
            percentage=cpu_pct, sub_text=f"{cpu_pct:.0f}% 占用", status=cpu_status,
        ))

        # 内存
        mem_pct = (status.memory_used_mb / status.memory_total_mb * 100) if status.memory_total_mb > 0 else 0
        mem_status = "error" if mem_pct > 90 else ("warning" if mem_pct > 70 else "normal")
        self._memory_card.update_data(StatusCardData(
            title="内存使用", value=f"{status.memory_used_mb / 1024:.1f}",
            value_unit="GB", percentage=mem_pct,
            sub_text=f"{bytes_to_human(int(status.memory_used_mb * 1024 * 1024))} / "
                     f"{bytes_to_human(int(status.memory_total_mb * 1024 * 1024))}",
            status=mem_status,
        ))

        # 磁盘
        disk_pct = (status.disk_used_gb / status.disk_total_gb * 100) if status.disk_total_gb > 0 else 0
        disk_status = "error" if disk_pct > 90 else ("warning" if disk_pct > 70 else "normal")
        self._disk_card.update_data(StatusCardData(
            title="磁盘使用", value=f"{status.disk_used_gb:.1f}", value_unit="GB",
            percentage=disk_pct, sub_text=f"{status.disk_used_gb:.1f} / {status.disk_total_gb:.0f} GB",
            status=disk_status,
        ))

        # 温度
        soc_temp = status.temperature.soc
        temp_status = "error" if soc_temp > 85 else ("warning" if soc_temp > 70 else "normal")
        self._temp_card.update_data(StatusCardData(
            title="SoC 温度", value=f"{soc_temp:.1f}", value_unit="°C",
            percentage=min(soc_temp / 100 * 100, 100),
            sub_text=f"环境 {status.temperature.ambient:.1f}°C",
            status=temp_status,
        ))

        # 电池
        power = state.power
        self._battery_panel.update_power_info(
            power.battery_percent, power.charging, power.voltage,
            power.current_amps, power.power_watts, power.estimated_runtime_minutes,
        )

        # 关节
        self._joint_table.update_joints(state.joints)

        # 传感器
        self._sensor_chart.update_imu(state.imu)
        self._sensor_chart.update_forces(state.forces)

        # 告警
        for alert in state.alerts:
            self._alert_manager.add_alert(alert)
        self._alert_list.update_alerts(self._alert_manager.active_alerts)

    def update_alerts(self) -> None:
        """刷新告警列表"""
        self._alert_list.update_alerts(self._alert_manager.active_alerts)
