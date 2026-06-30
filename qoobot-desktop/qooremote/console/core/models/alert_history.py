"""告警历史持久化 — SQLite 存储 + 查询/统计/导出

管理告警的持久化存储，支持按时间/级别/类型查询、
统计分析和多种格式导出。

对应功能 ALT-03（告警历史）。
"""

from __future__ import annotations

import json
import logging
import sqlite3
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from console.core.models.alert import Alert, AlertLevel, AlertType, AlertManager

logger = logging.getLogger(__name__)


@dataclass
class AlertQuery:
    """告警查询参数"""
    start_time: Optional[int] = None     # Unix 毫秒时间戳
    end_time: Optional[int] = None
    levels: Optional[list[AlertLevel]] = None
    types: Optional[list[AlertType]] = None
    acknowledged: Optional[bool] = None   # None=全部, True=已确认, False=未确认
    source: Optional[str] = None
    keyword: Optional[str] = None         # 消息关键词模糊搜索
    limit: int = 100
    offset: int = 0
    order_by: str = "timestamp DESC"


@dataclass
class AlertStatistics:
    """告警统计"""
    total_count: int = 0
    by_level: dict[str, int] = field(default_factory=dict)
    by_type: dict[str, int] = field(default_factory=dict)
    by_source: dict[str, int] = field(default_factory=dict)
    acknowledged_count: int = 0
    unacknowledged_count: int = 0
    time_range: tuple[int, int] = (0, 0)
    avg_ack_time_ms: float = 0.0         # 平均确认耗时

    def to_dict(self) -> dict:
        return {
            "total_count": self.total_count,
            "by_level": self.by_level,
            "by_type": self.by_type,
            "by_source": self.by_source,
            "acknowledged": self.acknowledged_count,
            "unacknowledged": self.unacknowledged_count,
            "time_range": self.time_range,
            "avg_ack_time_ms": self.avg_ack_time_ms,
        }


class AlertHistoryStore:
    """告警历史持久化存储

    使用 SQLite 存储告警记录，支持 CRUD + 查询/统计。

    对应功能 ALT-03（告警历史）。
    """

    def __init__(self, db_path: str = "") -> None:
        if not db_path:
            db_path = str(Path.home() / ".qoobot" / "qooremote" / "alerts.db")
        self._db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn: Optional[sqlite3.Connection] = None
        self._init_db()

    def _init_db(self) -> None:
        """初始化数据库与表结构"""
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id TEXT PRIMARY KEY,
                level TEXT NOT NULL,
                type TEXT NOT NULL,
                message TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                acknowledged INTEGER NOT NULL DEFAULT 0,
                acknowledged_at INTEGER DEFAULT 0,
                source TEXT DEFAULT '',
                robot_id TEXT DEFAULT '',
                session_id TEXT DEFAULT ''
            )
        """)
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_alerts_timestamp ON alerts(timestamp)
        """)
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_alerts_level ON alerts(level)
        """)
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_alerts_type ON alerts(type)
        """)
        self._conn.commit()

    def insert_alert(self, alert: Alert, robot_id: str = "",
                     session_id: str = "") -> None:
        """插入单条告警"""
        self._conn.execute("""
            INSERT OR REPLACE INTO alerts
            (id, level, type, message, timestamp, acknowledged, acknowledged_at, source, robot_id, session_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            alert.id,
            alert.level.value,
            alert.type.value,
            alert.message,
            alert.timestamp,
            1 if alert.acknowledged else 0,
            alert.acknowledged_at,
            alert.source,
            robot_id,
            session_id,
        ))
        self._conn.commit()

    def insert_alerts(self, alerts: list[Alert], robot_id: str = "",
                      session_id: str = "") -> None:
        """批量插入告警"""
        data = [
            (a.id, a.level.value, a.type.value, a.message, a.timestamp,
             1 if a.acknowledged else 0, a.acknowledged_at, a.source,
             robot_id, session_id)
            for a in alerts
        ]
        self._conn.executemany("""
            INSERT OR REPLACE INTO alerts
            (id, level, type, message, timestamp, acknowledged, acknowledged_at, source, robot_id, session_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, data)
        self._conn.commit()

    def acknowledge_alert(self, alert_id: str) -> bool:
        """确认告警"""
        now = int(time.time() * 1000)
        cursor = self._conn.execute(
            "UPDATE alerts SET acknowledged=1, acknowledged_at=? WHERE id=? AND acknowledged=0",
            (now, alert_id)
        )
        self._conn.commit()
        return cursor.rowcount > 0

    def delete_alert(self, alert_id: str) -> bool:
        cursor = self._conn.execute("DELETE FROM alerts WHERE id=?", (alert_id,))
        self._conn.commit()
        return cursor.rowcount > 0

    def delete_old_alerts(self, before_timestamp: int) -> int:
        """删除指定时间之前的告警"""
        cursor = self._conn.execute(
            "DELETE FROM alerts WHERE timestamp < ?", (before_timestamp,)
        )
        self._conn.commit()
        return cursor.rowcount

    def query(self, query: AlertQuery) -> list[dict]:
        """查询告警"""
        where_parts: list[str] = []
        params: list = []

        if query.start_time is not None:
            where_parts.append("timestamp >= ?")
            params.append(query.start_time)
        if query.end_time is not None:
            where_parts.append("timestamp <= ?")
            params.append(query.end_time)
        if query.levels:
            placeholders = ",".join("?" * len(query.levels))
            where_parts.append(f"level IN ({placeholders})")
            params.extend(l.value for l in query.levels)
        if query.types:
            placeholders = ",".join("?" * len(query.types))
            where_parts.append(f"type IN ({placeholders})")
            params.extend(t.value for t in query.types)
        if query.acknowledged is not None:
            where_parts.append("acknowledged = ?")
            params.append(1 if query.acknowledged else 0)
        if query.source:
            where_parts.append("source = ?")
            params.append(query.source)
        if query.keyword:
            where_parts.append("message LIKE ?")
            params.append(f"%{query.keyword}%")

        where_clause = " AND ".join(where_parts) if where_parts else "1=1"
        sql = f"""
            SELECT * FROM alerts WHERE {where_clause}
            ORDER BY {query.order_by}
            LIMIT ? OFFSET ?
        """
        params.extend([query.limit, query.offset])

        cursor = self._conn.execute(sql, params)
        return [dict(r) for r in cursor.fetchall()]

    def count(self, query: Optional[AlertQuery] = None) -> int:
        """计数"""
        if query is None:
            cursor = self._conn.execute("SELECT COUNT(*) FROM alerts")
            return cursor.fetchone()[0]

        where_parts: list[str] = []
        params: list = []
        # (简化：使用 query 的条件)
        if query.start_time is not None:
            where_parts.append("timestamp >= ?"); params.append(query.start_time)
        if query.end_time is not None:
            where_parts.append("timestamp <= ?"); params.append(query.end_time)
        if query.levels:
            placeholders = ",".join("?" * len(query.levels))
            where_parts.append(f"level IN ({placeholders})")
            params.extend(l.value for l in query.levels)
        if query.acknowledged is not None:
            where_parts.append("acknowledged = ?")
            params.append(1 if query.acknowledged else 0)

        where_clause = " AND ".join(where_parts) if where_parts else "1=1"
        cursor = self._conn.execute(f"SELECT COUNT(*) FROM alerts WHERE {where_clause}", params)
        return cursor.fetchone()[0]

    def get_statistics(self, start_time: Optional[int] = None,
                       end_time: Optional[int] = None) -> AlertStatistics:
        """获取统计信息"""
        stats = AlertStatistics()

        where = "1=1"
        params: list = []
        if start_time is not None:
            where += " AND timestamp >= ?"
            params.append(start_time)
        if end_time is not None:
            where += " AND timestamp <= ?"
            params.append(end_time)

        # 总数
        cursor = self._conn.execute(f"SELECT COUNT(*) FROM alerts WHERE {where}", params)
        stats.total_count = cursor.fetchone()[0]

        # 按级别
        cursor = self._conn.execute(f"SELECT level, COUNT(*) FROM alerts WHERE {where} GROUP BY level", params)
        for row in cursor:
            stats.by_level[row[0]] = row[1]

        # 按类型
        cursor = self._conn.execute(f"SELECT type, COUNT(*) FROM alerts WHERE {where} GROUP BY type", params)
        for row in cursor:
            stats.by_type[row[0]] = row[1]

        # 按来源
        cursor = self._conn.execute(f"SELECT source, COUNT(*) FROM alerts WHERE {where} AND source != '' GROUP BY source", params)
        for row in cursor:
            stats.by_source[row[0]] = row[1]

        # 确认统计
        cursor = self._conn.execute(
            f"SELECT COUNT(*) FROM alerts WHERE {where} AND acknowledged=1", params)
        stats.acknowledged_count = cursor.fetchone()[0]
        stats.unacknowledged_count = stats.total_count - stats.acknowledged_count

        # 时间范围
        cursor = self._conn.execute(f"SELECT MIN(timestamp), MAX(timestamp) FROM alerts WHERE {where}", params)
        row = cursor.fetchone()
        if row[0] is not None:
            stats.time_range = (row[0], row[1])

        # 平均确认耗时
        cursor = self._conn.execute(
            f"SELECT AVG(acknowledged_at - timestamp) FROM alerts WHERE {where} AND acknowledged=1", params)
        row = cursor.fetchone()
        if row[0] is not None:
            stats.avg_ack_time_ms = row[0]

        return stats

    def import_from_manager(self, manager: AlertManager, robot_id: str = "",
                            session_id: str = "") -> int:
        """从 AlertManager 批量导入（内存→DB 同步）"""
        alerts = manager.history
        self.insert_alerts(alerts, robot_id, session_id)
        return len(alerts)

    def export_json(self, filepath: str, query: Optional[AlertQuery] = None) -> int:
        """导出为 JSON 文件"""
        query = query or AlertQuery(limit=10000)
        alerts = self.query(query)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(alerts, f, ensure_ascii=False, indent=2, default=str)
        return len(alerts)

    def export_csv(self, filepath: str, query: Optional[AlertQuery] = None) -> int:
        """导出为 CSV 文件"""
        import csv
        query = query or AlertQuery(limit=10000)
        alerts = self.query(query)
        if not alerts:
            return 0
        with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=alerts[0].keys())
            writer.writeheader()
            writer.writerows(alerts)
        return len(alerts)

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None


class AlertHistoryService:
    """告警历史服务 — 连接 AlertManager 与历史持久化

    提供高级查询和统计接口，供 ViewModel 层使用。

    对应功能 ALT-03（告警历史）。
    """

    def __init__(self, store: Optional[AlertHistoryStore] = None) -> None:
        self._store = store or AlertHistoryStore()

    @property
    def store(self) -> AlertHistoryStore:
        return self._store

    def sync_alerts(self, manager: AlertManager, robot_id: str = "",
                    session_id: str = "") -> int:
        """将 AlertManager 的当前状态同步到持久化存储"""
        return self._store.import_from_manager(manager, robot_id, session_id)

    def query_alerts(self, **kwargs) -> list[dict]:
        """便捷查询

        Kwargs:
            start_time, end_time: int
            levels: list[AlertLevel]
            types: list[AlertType]
            acknowledged: bool
            keyword: str
            limit: int (default 100)
            offset: int (default 0)
        """
        q = AlertQuery(
            start_time=kwargs.get("start_time"),
            end_time=kwargs.get("end_time"),
            levels=kwargs.get("levels"),
            types=kwargs.get("types"),
            acknowledged=kwargs.get("acknowledged"),
            keyword=kwargs.get("keyword"),
            limit=kwargs.get("limit", 100),
            offset=kwargs.get("offset", 0),
        )
        return self._store.query(q)

    def get_recent(self, limit: int = 50) -> list[dict]:
        """获取最近 N 条告警"""
        return self._store.query(AlertQuery(limit=limit))

    def get_critical_unacknowledged(self) -> list[dict]:
        """获取未确认的严重告警"""
        return self._store.query(AlertQuery(
            levels=[AlertLevel.CRITICAL],
            acknowledged=False,
            limit=100,
        ))

    def get_statistics(self, start_time: Optional[int] = None,
                       end_time: Optional[int] = None) -> AlertStatistics:
        return self._store.get_statistics(start_time, end_time)

    def export(self, filepath: str, fmt: str = "json",
               query: Optional[AlertQuery] = None) -> int:
        """导出告警历史"""
        if fmt.lower() == "csv":
            return self._store.export_csv(filepath, query)
        return self._store.export_json(filepath, query)

    def close(self) -> None:
        self._store.close()
