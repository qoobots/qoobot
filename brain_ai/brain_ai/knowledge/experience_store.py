"""
brain_ai/knowledge/experience_store.py — Persistent episode storage (SQLite-backed).

Stores completed task episodes for retrieval, analysis, and future learning.
"""
from __future__ import annotations

import json
import logging
import os
import sqlite3
from datetime import datetime
from threading import Lock
from typing import Optional

logger = logging.getLogger(__name__)

_DEFAULT_DB_PATH = os.environ.get("BRAIN_AI_DB", "/data/brain_os/episodes.db")


class ExperienceStore:
    """
    SQLite-backed persistent store for task episodes.

    Schema: episodes table with JSON blob for full episode data.
    Allows filtering by robot_id, success, skill_name, date range.
    """

    def __init__(self, db_path: Optional[str] = None) -> None:
        self._db_path = db_path or _DEFAULT_DB_PATH
        self._lock    = Lock()
        self._conn: Optional[sqlite3.Connection] = None
        self._try_init()

    def _try_init(self) -> None:
        try:
            os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
            self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS episodes (
                    id           TEXT PRIMARY KEY,
                    robot_id     TEXT NOT NULL,
                    skill_name   TEXT,
                    success      INTEGER,
                    reward       REAL,
                    created_at   TEXT,
                    data         TEXT NOT NULL
                )
            """)
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_robot ON episodes(robot_id)"
            )
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_skill ON episodes(skill_name)"
            )
            self._conn.commit()
            logger.info(f"ExperienceStore initialized: {self._db_path}")
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"ExperienceStore init failed (in-memory fallback): {exc}")
            self._conn = sqlite3.connect(":memory:", check_same_thread=False)
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS episodes (
                    id TEXT PRIMARY KEY, robot_id TEXT NOT NULL,
                    skill_name TEXT, success INTEGER, reward REAL,
                    created_at TEXT, data TEXT NOT NULL
                )
            """)
            self._conn.commit()

    @property
    def is_available(self) -> bool:
        return self._conn is not None

    # ─── Write ────────────────────────────────────────────────

    def store(self, episode: dict) -> str:
        """Store a serialized episode dict. Returns episode id."""
        eid = episode.get("id", f"ep_{datetime.now().strftime('%Y%m%d%H%M%S%f')}")
        with self._lock:
            self._conn.execute("""
                INSERT OR REPLACE INTO episodes
                  (id, robot_id, skill_name, success, reward, created_at, data)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                eid,
                episode.get("robot_id", ""),
                episode.get("skill_name", ""),
                int(episode.get("success", False)),
                float(episode.get("reward", 0.0)),
                episode.get("created_at", datetime.now().isoformat()),
                json.dumps(episode, ensure_ascii=False),
            ))
            self._conn.commit()
        logger.debug(f"Episode stored: {eid}")
        return eid

    # ─── Read ─────────────────────────────────────────────────

    def get(self, episode_id: str) -> Optional[dict]:
        row = self._conn.execute(
            "SELECT data FROM episodes WHERE id = ?", (episode_id,)
        ).fetchone()
        return json.loads(row[0]) if row else None

    def search(
        self,
        robot_id: Optional[str] = None,
        skill_name: Optional[str] = None,
        success_only: bool = False,
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict]:
        query = "SELECT data FROM episodes WHERE 1=1"
        params: list = []
        if robot_id:
            query += " AND robot_id = ?"
            params.append(robot_id)
        if skill_name:
            query += " AND skill_name = ?"
            params.append(skill_name)
        if success_only:
            query += " AND success = 1"
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params += [limit, offset]

        rows = self._conn.execute(query, params).fetchall()
        return [json.loads(r[0]) for r in rows]

    def count(self) -> int:
        row = self._conn.execute("SELECT COUNT(*) FROM episodes").fetchone()
        return row[0] if row else 0

    def delete(self, episode_id: str) -> bool:
        with self._lock:
            cur = self._conn.execute(
                "DELETE FROM episodes WHERE id = ?", (episode_id,)
            )
            self._conn.commit()
            return cur.rowcount > 0
