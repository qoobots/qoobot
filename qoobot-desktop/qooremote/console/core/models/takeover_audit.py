"""接管审计 — 操作日志持久化与审计回放

使用 SQLite 持久化存储所有接管相关操作记录，
支持按操作员/时间/操作类型查询、统计分析和导出。

对应功能 TAK-04（接管审计）。
"""

from __future__ import annotations

import json
import logging
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class AuditActionType(Enum):
    """审计操作类型"""
    LOGIN = "login"
    LOGOUT = "logout"
    TAKEOVER_REQUEST = "takeover_request"
    TAKEOVER_APPROVE = "takeover_approve"
    TAKEOVER_REJECT = "takeover_reject"
    TAKEOVER_RELEASE = "takeover_release"
    TAKEOVER_REVOKE = "takeover_revoke"
    MODE_SWITCH = "mode_switch"
    EMERGENCY_STOP = "emergency_stop"
    PERMISSION_CHANGE = "permission_change"
    SESSION_START = "session_start"
    SESSION_END = "session_end"
    OPERATOR_ADD = "operator_add"
    OPERATOR_REMOVE = "operator_remove"
    OPERATOR_UPDATE = "operator_update"


@dataclass
class AuditEntry:
    """审计条目"""
    entry_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: float = field(default_factory=time.time)
    operator_id: str = ""
    operator_name: str = ""
    action_type: AuditActionType = AuditActionType.LOGIN
    robot_id: str = ""
    session_id: str = ""
    details: str = ""           # JSON 格式的额外详情
    result: str = "success"     # success / failure / pending
    ip_address: str = ""
    metadata: str = ""          # 扩展元数据 JSON

    def to_dict(self) -> dict:
        return {
            "entry_id": self.entry_id,
            "timestamp": self.timestamp,
            "operator_id": self.operator_id,
            "operator_name": self.operator_name,
            "action_type": self.action_type.value,
            "robot_id": self.robot_id,
            "session_id": self.session_id,
            "details": self.details,
            "result": self.result,
            "ip_address": self.ip_address,
            "metadata": self.metadata,
        }


@dataclass
class AuditQuery:
    """审计查询参数"""
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    operator_ids: Optional[list[str]] = None
    action_types: Optional[list[AuditActionType]] = None
    robot_id: Optional[str] = None
    session_id: Optional[str] = None
    result: Optional[str] = None
    keyword: Optional[str] = None         # 详情关键词搜索
    limit: int = 100
    offset: int = 0
    order_by: str = "timestamp DESC"


@dataclass
class AuditStatistics:
    """审计统计"""
    total_entries: int = 0
    by_action_type: dict[str, int] = field(default_factory=dict)
    by_operator: dict[str, int] = field(default_factory=dict)
    by_robot: dict[str, int] = field(default_factory=dict)
    by_result: dict[str, int] = field(default_factory=dict)
    time_range: tuple[float, float] = (0.0, 0.0)
    active_operators: int = 0
    total_sessions: int = 0

    def to_dict(self) -> dict:
        return {
            "total_entries": self.total_entries,
            "by_action_type": self.by_action_type,
            "by_operator": self.by_operator,
            "by_robot": self.by_robot,
            "by_result": self.by_result,
            "time_range": self.time_range,
            "active_operators": self.active_operators,
            "total_sessions": self.total_sessions,
        }


class TakeoverAuditStore:
    """接管审计持久化存储

    使用 SQLite 存储所有接管相关操作记录，
    支持 CRUD、索引查询和统计分析。

    对应功能 TAK-04（接管审计）。
    """

    TABLE_DDL = """
        CREATE TABLE IF NOT EXISTS audit_log (
            entry_id TEXT PRIMARY KEY,
            timestamp REAL NOT NULL,
            operator_id TEXT NOT NULL DEFAULT '',
            operator_name TEXT NOT NULL DEFAULT '',
            action_type TEXT NOT NULL,
            robot_id TEXT NOT NULL DEFAULT '',
            session_id TEXT NOT NULL DEFAULT '',
            details TEXT NOT NULL DEFAULT '',
            result TEXT NOT NULL DEFAULT 'success',
            ip_address TEXT NOT NULL DEFAULT '',
            metadata TEXT NOT NULL DEFAULT ''
        )
    """

    def __init__(self, db_path: str = "") -> None:
        if not db_path:
            db_path = str(Path.home() / ".qoobot" / "qooremote" / "takeover_audit.db")
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
        self._conn.execute(self.TABLE_DDL)

        # 创建索引
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_audit_operator ON audit_log(operator_id)",
            "CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_log(action_type)",
            "CREATE INDEX IF NOT EXISTS idx_audit_robot ON audit_log(robot_id)",
            "CREATE INDEX IF NOT EXISTS idx_audit_session ON audit_log(session_id)",
            "CREATE INDEX IF NOT EXISTS idx_audit_result ON audit_log(result)",
        ]
        for idx_sql in indexes:
            self._conn.execute(idx_sql)
        self._conn.commit()

    def write_entry(self, entry: AuditEntry) -> None:
        """写入单条审计记录"""
        self._conn.execute("""
            INSERT OR REPLACE INTO audit_log
            (entry_id, timestamp, operator_id, operator_name, action_type,
             robot_id, session_id, details, result, ip_address, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            entry.entry_id,
            entry.timestamp,
            entry.operator_id,
            entry.operator_name,
            entry.action_type.value,
            entry.robot_id,
            entry.session_id,
            entry.details,
            entry.result,
            entry.ip_address,
            entry.metadata,
        ))
        self._conn.commit()

    def write_entries(self, entries: list[AuditEntry]) -> None:
        """批量写入审计记录"""
        data = [
            (e.entry_id, e.timestamp, e.operator_id, e.operator_name,
             e.action_type.value, e.robot_id, e.session_id,
             e.details, e.result, e.ip_address, e.metadata)
            for e in entries
        ]
        self._conn.executemany("""
            INSERT OR REPLACE INTO audit_log
            (entry_id, timestamp, operator_id, operator_name, action_type,
             robot_id, session_id, details, result, ip_address, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, data)
        self._conn.commit()

    def query(self, query: AuditQuery) -> list[dict]:
        """查询审计记录"""
        where_parts: list[str] = []
        params: list = []

        if query.start_time is not None:
            where_parts.append("timestamp >= ?")
            params.append(query.start_time)
        if query.end_time is not None:
            where_parts.append("timestamp <= ?")
            params.append(query.end_time)
        if query.operator_ids:
            placeholders = ",".join("?" * len(query.operator_ids))
            where_parts.append(f"operator_id IN ({placeholders})")
            params.extend(query.operator_ids)
        if query.action_types:
            placeholders = ",".join("?" * len(query.action_types))
            where_parts.append(f"action_type IN ({placeholders})")
            params.extend(at.value for at in query.action_types)
        if query.robot_id:
            where_parts.append("robot_id = ?")
            params.append(query.robot_id)
        if query.session_id:
            where_parts.append("session_id = ?")
            params.append(query.session_id)
        if query.result:
            where_parts.append("result = ?")
            params.append(query.result)
        if query.keyword:
            where_parts.append("details LIKE ?")
            params.append(f"%{query.keyword}%")

        where_clause = " AND ".join(where_parts) if where_parts else "1=1"
        sql = f"""
            SELECT * FROM audit_log WHERE {where_clause}
            ORDER BY {query.order_by}
            LIMIT ? OFFSET ?
        """
        params.extend([query.limit, query.offset])

        cursor = self._conn.execute(sql, params)
        return [dict(r) for r in cursor.fetchall()]

    def count(self, query: Optional[AuditQuery] = None) -> int:
        """计数"""
        if query is None:
            cursor = self._conn.execute("SELECT COUNT(*) FROM audit_log")
            return cursor.fetchone()[0]
        # 简化计数
        where_parts: list[str] = []
        params: list = []
        if query.start_time is not None:
            where_parts.append("timestamp >= ?"); params.append(query.start_time)
        if query.end_time is not None:
            where_parts.append("timestamp <= ?"); params.append(query.end_time)
        if query.action_types:
            placeholders = ",".join("?" * len(query.action_types))
            where_parts.append(f"action_type IN ({placeholders})")
            params.extend(at.value for at in query.action_types)
        where_clause = " AND ".join(where_parts) if where_parts else "1=1"
        cursor = self._conn.execute(f"SELECT COUNT(*) FROM audit_log WHERE {where_clause}", params)
        return cursor.fetchone()[0]

    def get_statistics(self, start_time: Optional[float] = None,
                       end_time: Optional[float] = None) -> AuditStatistics:
        """获取统计信息"""
        stats = AuditStatistics()

        where = "1=1"
        params: list = []
        if start_time is not None:
            where += " AND timestamp >= ?"
            params.append(start_time)
        if end_time is not None:
            where += " AND timestamp <= ?"
            params.append(end_time)

        # 总数
        cursor = self._conn.execute(f"SELECT COUNT(*) FROM audit_log WHERE {where}", params)
        stats.total_entries = cursor.fetchone()[0]

        # 按操作类型
        cursor = self._conn.execute(
            f"SELECT action_type, COUNT(*) FROM audit_log WHERE {where} GROUP BY action_type", params)
        for row in cursor:
            stats.by_action_type[row[0]] = row[1]

        # 按操作员
        cursor = self._conn.execute(
            f"SELECT operator_name, COUNT(*) FROM audit_log WHERE {where} AND operator_name != '' GROUP BY operator_name", params)
        for row in cursor:
            stats.by_operator[row[0]] = row[1]

        # 按机器人
        cursor = self._conn.execute(
            f"SELECT robot_id, COUNT(*) FROM audit_log WHERE {where} AND robot_id != '' GROUP BY robot_id", params)
        for row in cursor:
            stats.by_robot[row[0]] = row[1]

        # 按结果
        cursor = self._conn.execute(
            f"SELECT result, COUNT(*) FROM audit_log WHERE {where} GROUP BY result", params)
        for row in cursor:
            stats.by_result[row[0]] = row[1]

        # 时间范围
        cursor = self._conn.execute(
            f"SELECT MIN(timestamp), MAX(timestamp) FROM audit_log WHERE {where}", params)
        row = cursor.fetchone()
        if row[0] is not None:
            stats.time_range = (row[0], row[1])

        # 活跃操作员数
        cursor = self._conn.execute(
            f"SELECT COUNT(DISTINCT operator_id) FROM audit_log WHERE {where}", params)
        stats.active_operators = cursor.fetchone()[0]

        # 会话数
        cursor = self._conn.execute(
            f"SELECT COUNT(DISTINCT session_id) FROM audit_log WHERE {where} AND session_id != ''", params)
        stats.total_sessions = cursor.fetchone()[0]

        return stats

    def delete_old_entries(self, before_timestamp: float) -> int:
        """删除指定时间之前的记录"""
        cursor = self._conn.execute(
            "DELETE FROM audit_log WHERE timestamp < ?", (before_timestamp,)
        )
        self._conn.commit()
        return cursor.rowcount

    def get_recent(self, limit: int = 50) -> list[dict]:
        """获取最近的审计记录"""
        return self.query(AuditQuery(limit=limit))

    def get_by_operator(self, operator_id: str, limit: int = 100) -> list[dict]:
        """获取指定操作员的审计记录"""
        return self.query(AuditQuery(operator_ids=[operator_id], limit=limit))

    def export_json(self, filepath: str, query: Optional[AuditQuery] = None) -> int:
        """导出为 JSON 文件"""
        query = query or AuditQuery(limit=10000)
        entries = self.query(query)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(entries, f, ensure_ascii=False, indent=2, default=str)
        return len(entries)

    def export_csv(self, filepath: str, query: Optional[AuditQuery] = None) -> int:
        """导出为 CSV 文件"""
        import csv
        query = query or AuditQuery(limit=10000)
        entries = self.query(query)
        if not entries:
            return 0
        with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=entries[0].keys())
            writer.writeheader()
            writer.writerows(entries)
        return len(entries)

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None


class TakeoverAuditService:
    """接管审计服务

    提供高级审计接口，供 ViewModel 层使用。
    负责记录所有接管操作，支持查询、统计和导出。

    对应功能 TAK-04（接管审计）。
    """

    def __init__(self, store: Optional[TakeoverAuditStore] = None) -> None:
        self._store = store or TakeoverAuditStore()

    @property
    def store(self) -> TakeoverAuditStore:
        return self._store

    def record(self, operator_id: str, operator_name: str,
               action_type: AuditActionType, **kwargs) -> AuditEntry:
        """记录一条审计日志"""
        entry = AuditEntry(
            timestamp=time.time(),
            operator_id=operator_id,
            operator_name=operator_name,
            action_type=action_type,
            robot_id=kwargs.get("robot_id", ""),
            session_id=kwargs.get("session_id", ""),
            details=kwargs.get("details", ""),
            result=kwargs.get("result", "success"),
            ip_address=kwargs.get("ip_address", ""),
            metadata=kwargs.get("metadata", ""),
        )
        self._store.write_entry(entry)
        return entry

    def record_login(self, operator_id: str, operator_name: str, **kwargs) -> AuditEntry:
        return self.record(operator_id, operator_name, AuditActionType.LOGIN, **kwargs)

    def record_logout(self, operator_id: str, operator_name: str, **kwargs) -> AuditEntry:
        return self.record(operator_id, operator_name, AuditActionType.LOGOUT, **kwargs)

    def record_takeover(self, operator_id: str, operator_name: str,
                        action: str, **kwargs) -> AuditEntry:
        """记录接管操作（请求/审批/拒绝/释放）"""
        action_map = {
            "request": AuditActionType.TAKEOVER_REQUEST,
            "approve": AuditActionType.TAKEOVER_APPROVE,
            "reject": AuditActionType.TAKEOVER_REJECT,
            "release": AuditActionType.TAKEOVER_RELEASE,
            "revoke": AuditActionType.TAKEOVER_REVOKE,
        }
        at = action_map.get(action, AuditActionType.TAKEOVER_REQUEST)
        return self.record(operator_id, operator_name, at, **kwargs)

    def record_emergency(self, operator_id: str, operator_name: str, **kwargs) -> AuditEntry:
        return self.record(operator_id, operator_name, AuditActionType.EMERGENCY_STOP, **kwargs)

    def record_mode_switch(self, operator_id: str, operator_name: str, **kwargs) -> AuditEntry:
        return self.record(operator_id, operator_name, AuditActionType.MODE_SWITCH, **kwargs)

    def record_permission_change(self, operator_id: str, operator_name: str, **kwargs) -> AuditEntry:
        return self.record(operator_id, operator_name, AuditActionType.PERMISSION_CHANGE, **kwargs)

    def record_operator_change(self, operator_id: str, operator_name: str,
                               action: str, **kwargs) -> AuditEntry:
        action_map = {
            "add": AuditActionType.OPERATOR_ADD,
            "remove": AuditActionType.OPERATOR_REMOVE,
            "update": AuditActionType.OPERATOR_UPDATE,
        }
        at = action_map.get(action, AuditActionType.OPERATOR_ADD)
        return self.record(operator_id, operator_name, at, **kwargs)

    def query(self, **kwargs) -> list[dict]:
        """便捷查询"""
        q = AuditQuery(
            start_time=kwargs.get("start_time"),
            end_time=kwargs.get("end_time"),
            operator_ids=kwargs.get("operator_ids"),
            action_types=kwargs.get("action_types"),
            robot_id=kwargs.get("robot_id"),
            session_id=kwargs.get("session_id"),
            result=kwargs.get("result"),
            keyword=kwargs.get("keyword"),
            limit=kwargs.get("limit", 100),
            offset=kwargs.get("offset", 0),
        )
        return self._store.query(q)

    def get_recent(self, limit: int = 50) -> list[dict]:
        return self._store.get_recent(limit)

    def get_statistics(self, start_time: Optional[float] = None,
                       end_time: Optional[float] = None) -> AuditStatistics:
        return self._store.get_statistics(start_time, end_time)

    def export(self, filepath: str, fmt: str = "json",
               query: Optional[AuditQuery] = None) -> int:
        if fmt.lower() == "csv":
            return self._store.export_csv(filepath, query)
        return self._store.export_json(filepath, query)

    def cleanup_old(self, days: int = 90) -> int:
        """清理 N 天前的审计记录"""
        cutoff = time.time() - days * 86400
        return self._store.delete_old_entries(cutoff)

    def close(self) -> None:
        self._store.close()
