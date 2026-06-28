"""
qoodev test distribution — TestFlight-style beta testing distribution for robot skills.

对标：Apple TestFlight + Google Play Internal Testing
提供内测分发、邀请管理、反馈收集、版本控制。
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class DistributionChannel(str, Enum):
    INTERNAL = "internal"  # team only
    ALPHA = "alpha"  # invited testers
    BETA = "beta"  # open beta
    PRODUCTION = "production"  # public release


class TesterRole(str, Enum):
    DEVELOPER = "developer"
    ADMIN = "admin"
    TESTER = "tester"
    REVIEWER = "reviewer"


class BuildStatus(str, Enum):
    UPLOADING = "uploading"
    PROCESSING = "processing"
    READY = "ready"
    TESTING = "testing"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class FeedbackType(str, Enum):
    BUG = "bug"
    FEATURE_REQUEST = "feature_request"
    CRASH = "crash"
    PERFORMANCE = "performance"
    USABILITY = "usability"
    GENERAL = "general"


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class Tester:
    """A registered beta tester."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    email: str = ""
    name: str = ""
    role: TesterRole = TesterRole.TESTER
    devices: List[Dict[str, str]] = field(default_factory=list)
    invited_at: str = ""
    joined_at: str = ""
    status: str = "invited"  # invited / active / inactive

    def __post_init__(self):
        if not self.invited_at:
            self.invited_at = time.strftime("%Y-%m-%dT%H:%M:%S")


@dataclass
class TestBuild:
    """A build distributed for testing."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    skill_id: str = ""
    version: str = "1.0.0-beta.1"
    build_number: int = 1
    channel: DistributionChannel = DistributionChannel.INTERNAL
    status: BuildStatus = BuildStatus.PROCESSING
    release_notes: str = ""
    uploaded_at: str = ""
    expires_at: str = ""
    max_testers: int = 100
    current_testers: int = 0
    installs: int = 0
    crash_count: int = 0
    min_platform_version: str = "1.0.0"
    compatible_platforms: List[str] = field(default_factory=list)
    package_hash: str = ""

    def __post_init__(self):
        if not self.uploaded_at:
            self.uploaded_at = time.strftime("%Y-%m-%dT%H:%M:%S")


@dataclass
class TesterFeedback:
    """Feedback from a tester."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    build_id: str = ""
    tester_id: str = ""
    feedback_type: FeedbackType = FeedbackType.GENERAL
    title: str = ""
    description: str = ""
    severity: str = "medium"  # low / medium / high / critical
    device_info: Dict[str, str] = field(default_factory=dict)
    logs: str = ""
    created_at: str = ""
    resolved: bool = False

    def __post_init__(self):
        if not self.created_at:
            self.created_at = time.strftime("%Y-%m-%dT%H:%M:%S")


# ---------------------------------------------------------------------------
# TestDistributionManager
# ---------------------------------------------------------------------------

class TestDistributionManager:
    """Manage TestFlight-style beta testing for robot skills.

    Usage::

        manager = TestDistributionManager()
        build = manager.create_build("pick_and_place", "1.2.0-beta.1")
        manager.invite_testers(build.id, ["tester1@example.com", "tester2@example.com"])
        manager.promote_to_beta(build.id)
    """

    def __init__(self, data_dir: Optional[Path] = None):
        self._data_dir = data_dir or Path.home() / ".qoodev" / "test_distribution"
        self._data_dir.mkdir(parents=True, exist_ok=True)

        self._builds: Dict[str, TestBuild] = {}
        self._testers: Dict[str, Tester] = {}
        self._feedback: Dict[str, List[TesterFeedback]] = defaultdict(list)
        self._invitations: Dict[str, List[str]] = defaultdict(list)  # build_id → tester_ids

        self._load()

    # -- persistence ---------------------------------------------------------

    def _load(self) -> None:
        builds_path = self._data_dir / "builds.json"
        testers_path = self._data_dir / "testers.json"
        feedback_path = self._data_dir / "feedback.json"

        if builds_path.exists():
            data = json.loads(builds_path.read_text())
            for item in data:
                build = TestBuild(**item)
                self._builds[build.id] = build

        if testers_path.exists():
            data = json.loads(testers_path.read_text())
            for item in data:
                tester = Tester(**item)
                self._testers[tester.id] = tester

        if feedback_path.exists():
            data = json.loads(feedback_path.read_text())
            for build_id, items in data.items():
                self._feedback[build_id] = [TesterFeedback(**item) for item in items]

    def _save(self) -> None:
        builds_data = [self._build_to_dict(b) for b in self._builds.values()]
        testers_data = [self._tester_to_dict(t) for t in self._testers.values()]
        feedback_data = {bid: [self._feedback_to_dict(f) for f in items] for bid, items in self._feedback.items()}

        (self._data_dir / "builds.json").write_text(json.dumps(builds_data, indent=2))
        (self._data_dir / "testers.json").write_text(json.dumps(testers_data, indent=2))
        (self._data_dir / "feedback.json").write_text(json.dumps(feedback_data, indent=2))

    @staticmethod
    def _build_to_dict(b: TestBuild) -> Dict[str, Any]:
        return {
            "id": b.id, "skill_id": b.skill_id, "version": b.version,
            "build_number": b.build_number, "channel": b.channel.value,
            "status": b.status.value, "release_notes": b.release_notes,
            "uploaded_at": b.uploaded_at, "expires_at": b.expires_at,
            "max_testers": b.max_testers, "current_testers": b.current_testers,
            "installs": b.installs, "crash_count": b.crash_count,
            "min_platform_version": b.min_platform_version,
            "compatible_platforms": b.compatible_platforms,
            "package_hash": b.package_hash,
        }

    @staticmethod
    def _tester_to_dict(t: Tester) -> Dict[str, Any]:
        return {
            "id": t.id, "email": t.email, "name": t.name,
            "role": t.role.value, "devices": t.devices,
            "invited_at": t.invited_at, "joined_at": t.joined_at, "status": t.status,
        }

    @staticmethod
    def _feedback_to_dict(f: TesterFeedback) -> Dict[str, Any]:
        return {
            "id": f.id, "build_id": f.build_id, "tester_id": f.tester_id,
            "feedback_type": f.feedback_type.value, "title": f.title,
            "description": f.description, "severity": f.severity,
            "device_info": f.device_info, "created_at": f.created_at, "resolved": f.resolved,
        }

    # -- build management ----------------------------------------------------

    def create_build(
        self,
        skill_id: str,
        version: str,
        release_notes: str = "",
        channel: DistributionChannel = DistributionChannel.INTERNAL,
        max_testers: int = 100,
        expires_days: int = 90,
        compatible_platforms: Optional[List[str]] = None,
    ) -> TestBuild:
        build = TestBuild(
            skill_id=skill_id,
            version=version,
            release_notes=release_notes,
            channel=channel,
            max_testers=max_testers,
            compatible_platforms=compatible_platforms or ["linux-x86_64", "linux-aarch64"],
        )
        build.expires_at = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(time.time() + expires_days * 86400))
        build.build_number = self._next_build_number(skill_id)

        self._builds[build.id] = build
        self._save()
        return build

    def _next_build_number(self, skill_id: str) -> int:
        existing = [b.build_number for b in self._builds.values() if b.skill_id == skill_id]
        return max(existing) + 1 if existing else 1

    def get_build(self, build_id: str) -> Optional[TestBuild]:
        return self._builds.get(build_id)

    def list_builds(self, skill_id: Optional[str] = None, channel: Optional[DistributionChannel] = None) -> List[TestBuild]:
        builds = list(self._builds.values())
        if skill_id:
            builds = [b for b in builds if b.skill_id == skill_id]
        if channel:
            builds = [b for b in builds if b.channel == channel]
        return sorted(builds, key=lambda b: b.uploaded_at, reverse=True)

    def update_build_status(self, build_id: str, status: BuildStatus) -> None:
        build = self._builds.get(build_id)
        if build:
            build.status = status
            self._save()

    def promote_channel(self, build_id: str, new_channel: DistributionChannel) -> bool:
        """Promote a build to a wider distribution channel."""
        build = self._builds.get(build_id)
        if not build:
            return False

        channel_order = {
            DistributionChannel.INTERNAL: 0,
            DistributionChannel.ALPHA: 1,
            DistributionChannel.BETA: 2,
            DistributionChannel.PRODUCTION: 3,
        }

        if channel_order.get(new_channel, -1) <= channel_order.get(build.channel, -1):
            return False

        build.channel = new_channel
        self._save()
        return True

    # -- tester management ---------------------------------------------------

    def add_tester(self, email: str, name: str = "", role: TesterRole = TesterRole.TESTER) -> Tester:
        existing = self._find_tester_by_email(email)
        if existing:
            return existing

        tester = Tester(email=email, name=name, role=role)
        self._testers[tester.id] = tester
        self._save()
        return tester

    def invite_testers(self, build_id: str, emails: List[str]) -> List[str]:
        """Invite testers to a specific build."""
        build = self._builds.get(build_id)
        if not build:
            return []

        invited = []
        for email in emails:
            tester = self.add_tester(email)
            if build_id not in self._invitations:
                self._invitations[build_id] = []
            if tester.id not in self._invitations[build_id]:
                self._invitations[build_id].append(tester.id)
                build.current_testers += 1
                invited.append(tester.id)

        self._save()
        return invited

    def remove_tester(self, build_id: str, tester_id: str) -> None:
        if build_id in self._invitations and tester_id in self._invitations[build_id]:
            self._invitations[build_id].remove(tester_id)
            build = self._builds.get(build_id)
            if build:
                build.current_testers = max(0, build.current_testers - 1)
            self._save()

    def list_testers(self, build_id: Optional[str] = None) -> List[Tester]:
        if build_id:
            tester_ids = self._invitations.get(build_id, [])
            return [self._testers[tid] for tid in tester_ids if tid in self._testers]
        return list(self._testers.values())

    def _find_tester_by_email(self, email: str) -> Optional[Tester]:
        for t in self._testers.values():
            if t.email.lower() == email.lower():
                return t
        return None

    # -- feedback management -------------------------------------------------

    def submit_feedback(
        self,
        build_id: str,
        tester_id: str,
        feedback_type: FeedbackType,
        title: str,
        description: str,
        severity: str = "medium",
        device_info: Optional[Dict[str, str]] = None,
        logs: str = "",
    ) -> TesterFeedback:
        fb = TesterFeedback(
            build_id=build_id,
            tester_id=tester_id,
            feedback_type=feedback_type,
            title=title,
            description=description,
            severity=severity,
            device_info=device_info or {},
            logs=logs,
        )

        if build_id not in self._feedback:
            self._feedback[build_id] = []
        self._feedback[build_id].append(fb)

        # auto-increment crash count
        if feedback_type == FeedbackType.CRASH:
            build = self._builds.get(build_id)
            if build:
                build.crash_count += 1

        self._save()
        return fb

    def list_feedback(
        self,
        build_id: Optional[str] = None,
        feedback_type: Optional[FeedbackType] = None,
        resolved: Optional[bool] = None,
    ) -> List[TesterFeedback]:
        all_feedback: List[TesterFeedback] = []
        for bid, items in self._feedback.items():
            if build_id and bid != build_id:
                continue
            all_feedback.extend(items)

        if feedback_type:
            all_feedback = [f for f in all_feedback if f.feedback_type == feedback_type]
        if resolved is not None:
            all_feedback = [f for f in all_feedback if f.resolved == resolved]

        return sorted(all_feedback, key=lambda f: f.created_at, reverse=True)

    def resolve_feedback(self, feedback_id: str) -> bool:
        for items in self._feedback.values():
            for f in items:
                if f.id == feedback_id:
                    f.resolved = True
                    self._save()
                    return True
        return False

    # -- statistics ----------------------------------------------------------

    def get_build_stats(self, build_id: str) -> Dict[str, Any]:
        build = self._builds.get(build_id)
        if not build:
            return {}

        feedback_list = self._feedback.get(build_id, [])
        feedback_by_type: Dict[str, int] = defaultdict(int)
        for f in feedback_list:
            feedback_by_type[f.feedback_type.value] += 1

        return {
            "build_id": build.id,
            "version": build.version,
            "channel": build.channel.value,
            "status": build.status.value,
            "total_testers": build.current_testers,
            "total_installs": build.installs,
            "crash_count": build.crash_count,
            "feedback_count": len(feedback_list),
            "unresolved_feedback": sum(1 for f in feedback_list if not f.resolved),
            "feedback_by_type": dict(feedback_by_type),
            "crash_rate": build.crash_count / max(build.installs, 1) * 100,
            "expires_at": build.expires_at,
        }

    def get_overview_stats(self, skill_id: Optional[str] = None) -> Dict[str, Any]:
        builds = self.list_builds(skill_id=skill_id)

        total_testers = len(set(
            tid for bid in self._invitations
            for tid in self._invitations[bid]
            if (not skill_id or any(b.skill_id == skill_id for b in [self._builds.get(bid)] if b))
        ))

        total_feedback = sum(
            len(items) for bid, items in self._feedback.items()
            if not skill_id or (bid in self._builds and self._builds[bid].skill_id == skill_id)
        )

        return {
            "total_builds": len(builds),
            "active_builds": sum(1 for b in builds if b.status in (BuildStatus.TESTING, BuildStatus.READY)),
            "total_testers": total_testers,
            "total_feedback": total_feedback,
            "total_crashes": sum(b.crash_count for b in builds),
            "channels": {
                ch.value: sum(1 for b in builds if b.channel == ch)
                for ch in DistributionChannel
            },
        }
