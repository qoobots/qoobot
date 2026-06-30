"""告警历史 ViewModel — 连接 AlertHistoryService 与 UI

提供告警查询、统计、导出的 MVVM 桥接。

对应功能 ALT-03（告警历史）。
"""

from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtCore import QObject, Signal

from console.core.models.alert import AlertLevel, AlertManager
from console.core.models.alert_history import (
    AlertHistoryService, AlertHistoryStore, AlertQuery, AlertStatistics,
)

logger = logging.getLogger(__name__)


class AlertHistoryViewModel(QObject):
    """告警历史 ViewModel

    管理告警历史数据的查询、统计、导出。
    """

    # 数据信号
    query_completed = Signal(list)              # 查询完成 (alert_dicts)
    statistics_updated = Signal(object)         # 统计更新 (AlertStatistics)
    export_completed = Signal(str, int)          # 导出完成 (filepath, count)
    error_occurred = Signal(str)                # 错误信息

    def __init__(self, store: Optional[AlertHistoryStore] = None,
                 parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._service = AlertHistoryService(store)
        self._last_query: Optional[AlertQuery] = None
        self._alert_manager: Optional[AlertManager] = None

    @property
    def service(self) -> AlertHistoryService:
        return self._service

    def bind_alert_manager(self, manager: AlertManager) -> None:
        """绑定 AlertManager（用于同步数据）"""
        self._alert_manager = manager

    def sync_current(self, robot_id: str = "", session_id: str = "") -> None:
        """将当前 AlertManager 的状态同步到数据库"""
        if self._alert_manager:
            count = self._service.sync_alerts(
                self._alert_manager, robot_id, session_id
            )
            logger.info("Synced %d alerts to history store", count)

    def query(self, params: dict) -> None:
        """执行查询"""
        try:
            q = AlertQuery(
                start_time=params.get("start_time"),
                end_time=params.get("end_time"),
                levels=params.get("levels"),
                types=params.get("types"),
                acknowledged=params.get("acknowledged"),
                keyword=params.get("keyword"),
                limit=params.get("limit", 200),
                offset=params.get("offset", 0),
            )
            self._last_query = q
            results = self._service.store.query(q)
            self.query_completed.emit(results)

            # 同时更新统计
            stats = self._service.get_statistics(
                start_time=params.get("start_time"),
                end_time=params.get("end_time"),
            )
            self.statistics_updated.emit(stats)

        except Exception as e:
            logger.error("Query failed: %s", e)
            self.error_occurred.emit(str(e))

    def refresh(self) -> None:
        """刷新当前查询"""
        if self._last_query:
            try:
                results = self._service.store.query(self._last_query)
                self.query_completed.emit(results)
            except Exception as e:
                self.error_occurred.emit(str(e))
        else:
            self.query({})

    def acknowledge(self, alert_id: str) -> None:
        """确认告警"""
        try:
            self._service.store.acknowledge_alert(alert_id)
            self.refresh()
        except Exception as e:
            self.error_occurred.emit(str(e))

    def export(self, filepath: str, fmt: str = "json") -> None:
        """导出告警"""
        try:
            count = self._service.export(filepath, fmt, self._last_query)
            self.export_completed.emit(filepath, count)
            logger.info("Exported %d alerts to %s", count, filepath)
        except Exception as e:
            logger.error("Export failed: %s", e)
            self.error_occurred.emit(str(e))

    def get_statistics(self, start_time: Optional[int] = None,
                       end_time: Optional[int] = None) -> AlertStatistics:
        """获取统计信息"""
        return self._service.get_statistics(start_time, end_time)

    def cleanup(self) -> None:
        """清理资源"""
        self._service.close()
