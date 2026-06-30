"""
qoodev usage statistics — skill install count, activity, rating analytics dashboard.

对标：App Store Connect Analytics + Google Play Console
提供安装量统计、活跃度分析、评分趋势、留存率。
"""

from __future__ import annotations

import json
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class TimeGranularity(str, Enum):
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class MetricType(str, Enum):
    INSTALLS = "installs"
    UNINSTALLS = "uninstalls"
    ACTIVE_USERS = "active_users"
    SESSIONS = "sessions"
    ERRORS = "errors"
    RATING = "rating"
    REVENUE = "revenue"


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class MetricPoint:
    """A single data point in time series."""
    timestamp: str
    metric: MetricType
    value: float
    skill_id: str = ""
    dimensions: Dict[str, str] = field(default_factory=dict)


@dataclass
class SkillStats:
    """Aggregated statistics for a single skill."""
    skill_id: str
    skill_name: str = ""
    total_installs: int = 0
    total_uninstalls: int = 0
    current_installs: int = 0
    active_users_7d: int = 0
    active_users_30d: int = 0
    total_sessions: int = 0
    avg_session_duration_s: float = 0.0
    error_count: int = 0
    avg_rating: float = 0.0
    rating_count: int = 0
    rating_distribution: Dict[int, int] = field(default_factory=lambda: {1: 0, 2: 0, 3: 0, 4: 0, 5: 0})
    retention_7d_pct: float = 0.0
    retention_30d_pct: float = 0.0
    top_platforms: List[Tuple[str, int]] = field(default_factory=list)
    daily_installs: List[Tuple[str, int]] = field(default_factory=list)


@dataclass
class DashboardStats:
    """Overall analytics dashboard."""
    total_skills: int = 0
    total_installs: int = 0
    total_active_users: int = 0
    total_sessions: int = 0
    total_errors: int = 0
    avg_rating: float = 0.0
    top_skills: List[Tuple[str, int]] = field(default_factory=list)
    skill_stats: Dict[str, SkillStats] = field(default_factory=dict)
    installs_trend: List[Tuple[str, int]] = field(default_factory=list)
    active_users_trend: List[Tuple[str, int]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# UsageTracker
# ---------------------------------------------------------------------------

class UsageTracker:
    """Track and analyze skill usage statistics.

    Usage::

        tracker = UsageTracker()
        tracker.record_install("pick_and_place", platform="linux-x86_64")
        tracker.record_session("pick_and_place", duration_s=120.5)
        tracker.record_rating("pick_and_place", rating=5)
        stats = tracker.get_skill_stats("pick_and_place")
    """

    def __init__(self, data_dir: Optional[Path] = None):
        self._data_dir = data_dir or Path.home() / ".qoodev" / "usage_stats"
        self._data_dir.mkdir(parents=True, exist_ok=True)

        self._metrics: List[MetricPoint] = []
        self._ratings: Dict[str, List[int]] = defaultdict(list)
        self._installs: Dict[str, Dict[str, Any]] = defaultdict(dict)  # user_id → install info
        self._sessions: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

        self._load()

    # -- persistence ---------------------------------------------------------

    def _load(self) -> None:
        metrics_path = self._data_dir / "metrics.jsonl"
        if metrics_path.exists():
            for line in metrics_path.read_text().splitlines():
                if line.strip():
                    try:
                        data = json.loads(line)
                        self._metrics.append(MetricPoint(**data))
                    except Exception:
                        pass

        ratings_path = self._data_dir / "ratings.json"
        if ratings_path.exists():
            self._ratings = defaultdict(list, json.loads(ratings_path.read_text()))

    def _save_metric(self, point: MetricPoint) -> None:
        with open(self._data_dir / "metrics.jsonl", "a") as f:
            f.write(json.dumps({
                "timestamp": point.timestamp,
                "metric": point.metric.value,
                "value": point.value,
                "skill_id": point.skill_id,
                "dimensions": point.dimensions,
            }) + "\n")

    def _save_ratings(self) -> None:
        (self._data_dir / "ratings.json").write_text(json.dumps(dict(self._ratings)))

    # -- recording -----------------------------------------------------------

    def record_install(self, skill_id: str, user_id: str = "anonymous", platform: str = "unknown", version: str = "") -> None:
        now = time.strftime("%Y-%m-%dT%H:%M:%S")
        point = MetricPoint(timestamp=now, metric=MetricType.INSTALLS, value=1, skill_id=skill_id,
                           dimensions={"platform": platform, "version": version})
        self._metrics.append(point)
        self._save_metric(point)

        self._installs[skill_id][user_id] = {"installed_at": now, "platform": platform, "version": version}

    def record_uninstall(self, skill_id: str, user_id: str = "anonymous") -> None:
        now = time.strftime("%Y-%m-%dT%H:%M:%S")
        point = MetricPoint(timestamp=now, metric=MetricType.UNINSTALLS, value=1, skill_id=skill_id)
        self._metrics.append(point)
        self._save_metric(point)

        self._installs[skill_id].pop(user_id, None)

    def record_session(self, skill_id: str, user_id: str = "anonymous", duration_s: float = 0.0) -> None:
        now = time.strftime("%Y-%m-%dT%H:%M:%S")
        point = MetricPoint(timestamp=now, metric=MetricType.SESSIONS, value=1, skill_id=skill_id,
                           dimensions={"user_id": user_id})
        self._metrics.append(point)
        self._save_metric(point)

        self._sessions[skill_id].append({"user_id": user_id, "timestamp": now, "duration_s": duration_s})

    def record_active_user(self, skill_id: str, user_id: str = "anonymous") -> None:
        now = time.strftime("%Y-%m-%dT%H:%M:%S")
        point = MetricPoint(timestamp=now, metric=MetricType.ACTIVE_USERS, value=1, skill_id=skill_id,
                           dimensions={"user_id": user_id})
        self._metrics.append(point)
        self._save_metric(point)

    def record_error(self, skill_id: str, error_type: str = "unknown") -> None:
        now = time.strftime("%Y-%m-%dT%H:%M:%S")
        point = MetricPoint(timestamp=now, metric=MetricType.ERRORS, value=1, skill_id=skill_id,
                           dimensions={"error_type": error_type})
        self._metrics.append(point)
        self._save_metric(point)

    def record_rating(self, skill_id: str, rating: int, user_id: str = "anonymous") -> None:
        """Record a user rating (1–5)."""
        rating = max(1, min(5, rating))
        self._ratings[skill_id].append(rating)
        self._save_ratings()

        now = time.strftime("%Y-%m-%dT%H:%M:%S")
        point = MetricPoint(timestamp=now, metric=MetricType.RATING, value=rating, skill_id=skill_id,
                           dimensions={"user_id": user_id})
        self._metrics.append(point)
        self._save_metric(point)

    # -- querying ------------------------------------------------------------

    def get_skill_stats(self, skill_id: str) -> SkillStats:
        """Get aggregated stats for a skill."""
        stats = SkillStats(skill_id=skill_id)

        # installs
        install_points = [p for p in self._metrics if p.skill_id == skill_id and p.metric == MetricType.INSTALLS]
        uninstall_points = [p for p in self._metrics if p.skill_id == skill_id and p.metric == MetricType.UNINSTALLS]
        stats.total_installs = len(install_points)
        stats.total_uninstalls = len(uninstall_points)
        stats.current_installs = stats.total_installs - stats.total_uninstalls

        # sessions
        session_points = [p for p in self._metrics if p.skill_id == skill_id and p.metric == MetricType.SESSIONS]
        stats.total_sessions = len(session_points)

        session_durations = [s["duration_s"] for s in self._sessions.get(skill_id, []) if s["duration_s"] > 0]
        stats.avg_session_duration_s = sum(session_durations) / len(session_durations) if session_durations else 0

        # errors
        error_points = [p for p in self._metrics if p.skill_id == skill_id and p.metric == MetricType.ERRORS]
        stats.error_count = len(error_points)

        # active users (7d / 30d)
        now = time.time()
        active_7d: set = set()
        active_30d: set = set()

        for p in self._metrics:
            if p.skill_id != skill_id or p.metric != MetricType.ACTIVE_USERS:
                continue
            try:
                ts = time.mktime(time.strptime(p.timestamp, "%Y-%m-%dT%H:%M:%S"))
                if now - ts <= 7 * 86400:
                    active_7d.add(p.dimensions.get("user_id", ""))
                if now - ts <= 30 * 86400:
                    active_30d.add(p.dimensions.get("user_id", ""))
            except Exception:
                pass

        stats.active_users_7d = len(active_7d)
        stats.active_users_30d = len(active_30d)

        # ratings
        ratings = self._ratings.get(skill_id, [])
        stats.rating_count = len(ratings)
        stats.avg_rating = sum(ratings) / len(ratings) if ratings else 0
        for r in ratings:
            stats.rating_distribution[r] = stats.rating_distribution.get(r, 0) + 1

        # platforms
        platform_counts: Dict[str, int] = defaultdict(int)
        for p in install_points:
            platform_counts[p.dimensions.get("platform", "unknown")] += 1
        stats.top_platforms = sorted(platform_counts.items(), key=lambda x: x[1], reverse=True)

        # daily installs trend
        daily: Dict[str, int] = defaultdict(int)
        for p in install_points:
            day = p.timestamp[:10]
            daily[day] += 1
        stats.daily_installs = sorted(daily.items())

        # retention
        if stats.total_installs > 0:
            stats.retention_7d_pct = stats.active_users_7d / stats.total_installs * 100
            stats.retention_30d_pct = stats.active_users_30d / stats.total_installs * 100

        return stats

    def get_dashboard(self) -> DashboardStats:
        """Get overall analytics dashboard."""
        dash = DashboardStats()

        # collect all skill IDs
        skill_ids = set(p.skill_id for p in self._metrics if p.skill_id)
        dash.total_skills = len(skill_ids)

        for sid in skill_ids:
            s = self.get_skill_stats(sid)
            dash.skill_stats[sid] = s

            dash.total_installs += s.total_installs
            dash.total_active_users += s.active_users_30d
            dash.total_sessions += s.total_sessions
            dash.total_errors += s.error_count

        # average rating
        all_ratings = [r for ratings in self._ratings.values() for r in ratings]
        dash.avg_rating = sum(all_ratings) / len(all_ratings) if all_ratings else 0

        # top skills by installs
        dash.top_skills = sorted(
            [(sid, s.total_installs) for sid, s in dash.skill_stats.items()],
            key=lambda x: x[1], reverse=True,
        )[:10]

        # installs trend (all skills)
        daily_total: Dict[str, int] = defaultdict(int)
        for p in self._metrics:
            if p.metric == MetricType.INSTALLS:
                daily_total[p.timestamp[:10]] += 1
        dash.installs_trend = sorted(daily_total.items())

        # active users trend
        daily_active: Dict[str, int] = defaultdict(int)
        for p in self._metrics:
            if p.metric == MetricType.ACTIVE_USERS:
                daily_active[p.timestamp[:10]] += 1
        dash.active_users_trend = sorted(daily_active.items())

        return dash

    def generate_report(self, skill_id: Optional[str] = None) -> str:
        """Generate Markdown analytics report."""
        if skill_id:
            stats = self.get_skill_stats(skill_id)
            return self._skill_report_md(stats)

        dash = self.get_dashboard()
        return self._dashboard_report_md(dash)

    def _skill_report_md(self, stats: SkillStats) -> str:
        lines = [
            f"# Skill Analytics: {stats.skill_name or stats.skill_id}",
            "",
            "## Overview",
            f"- **Total Installs**: {stats.total_installs}",
            f"- **Current Installs**: {stats.current_installs}",
            f"- **Active Users (7d)**: {stats.active_users_7d}",
            f"- **Active Users (30d)**: {stats.active_users_30d}",
            f"- **Total Sessions**: {stats.total_sessions}",
            f"- **Avg Session Duration**: {stats.avg_session_duration_s:.1f}s",
            f"- **Error Count**: {stats.error_count}",
            "",
            "## Ratings",
            f"- **Average**: {'⭐' * int(stats.avg_rating)} ({stats.avg_rating:.1f}/5)",
            f"- **Total Ratings**: {stats.rating_count}",
            "",
            "| Rating | Count |",
            "|--------|-------|",
        ]
        for r in range(5, 0, -1):
            lines.append(f"| {'⭐' * r} | {stats.rating_distribution.get(r, 0)} |")

        lines.extend([
            "",
            "## Retention",
            f"- **7-Day**: {stats.retention_7d_pct:.1f}%",
            f"- **30-Day**: {stats.retention_30d_pct:.1f}%",
            "",
            "## Top Platforms",
        ])
        for plat, count in stats.top_platforms:
            lines.append(f"- {plat}: {count} installs")

        return "\n".join(lines)

    def _dashboard_report_md(self, dash: DashboardStats) -> str:
        lines = [
            "# QooBot Usage Analytics Dashboard",
            "",
            "## Overview",
            f"- **Total Skills**: {dash.total_skills}",
            f"- **Total Installs**: {dash.total_installs}",
            f"- **Active Users (30d)**: {dash.total_active_users}",
            f"- **Total Sessions**: {dash.total_sessions}",
            f"- **Total Errors**: {dash.total_errors}",
            f"- **Average Rating**: {'⭐' * int(dash.avg_rating)} ({dash.avg_rating:.1f}/5)",
            "",
            "## Top Skills",
            "",
            "| Skill | Installs |",
            "|-------|----------|",
        ]
        for sid, count in dash.top_skills:
            lines.append(f"| {sid} | {count} |")

        return "\n".join(lines)

    def export_json(self, path: Path) -> None:
        """Export all stats as JSON."""
        dash = self.get_dashboard()
        data = {
            "overview": {
                "total_skills": dash.total_skills,
                "total_installs": dash.total_installs,
                "total_active_users": dash.total_active_users,
                "total_sessions": dash.total_sessions,
                "total_errors": dash.total_errors,
                "avg_rating": dash.avg_rating,
            },
            "top_skills": [{"skill_id": sid, "installs": count} for sid, count in dash.top_skills],
            "skills": {
                sid: {
                    "total_installs": s.total_installs,
                    "current_installs": s.current_installs,
                    "active_users_7d": s.active_users_7d,
                    "active_users_30d": s.active_users_30d,
                    "total_sessions": s.total_sessions,
                    "avg_rating": s.avg_rating,
                    "rating_count": s.rating_count,
                    "rating_distribution": s.rating_distribution,
                    "retention_7d_pct": s.retention_7d_pct,
                    "retention_30d_pct": s.retention_30d_pct,
                }
                for sid, s in dash.skill_stats.items()
            },
            "installs_trend": [{"date": d, "count": c} for d, c in dash.installs_trend],
            "active_users_trend": [{"date": d, "count": c} for d, c in dash.active_users_trend],
        }
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
