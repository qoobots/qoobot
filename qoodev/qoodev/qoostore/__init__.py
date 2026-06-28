"""
qoostore Market Integration — Skill submission and discovery API client.

Provides an interface for submitting skills to the qoostore marketplace,
managing metadata, and handling the review workflow.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
import enum
import json
import hashlib
import zipfile


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class SkillCategory(enum.Enum):
    NAVIGATION = "navigation"
    MANIPULATION = "manipulation"
    PERCEPTION = "perception"
    INTERACTION = "interaction"
    UTILITY = "utility"
    SIMULATION = "simulation"


class ReviewStatus(enum.Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    PUBLISHED = "published"
    DEPRECATED = "deprecated"


class PrivacyLevel(enum.Enum):
    PUBLIC = "public"
    UNLISTED = "unlisted"
    PRIVATE = "private"


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

@dataclass
class SkillMetadata:
    """Metadata for a skill submission to qoostore."""

    name: str
    version: str
    author: str
    description: str

    # Classification
    category: SkillCategory = SkillCategory.UTILITY
    tags: List[str] = field(default_factory=list)
    robot_models: List[str] = field(default_factory=lambda: ["qoobot_v1"])

    # Dependencies
    python_version: str = ">=3.11"
    dependencies: Dict[str, str] = field(default_factory=dict)
    qoobot_sdk_version: str = ">=1.0.0"

    # Media
    icon_path: Optional[str] = None
    screenshots: List[str] = field(default_factory=list)
    demo_video_url: Optional[str] = None

    # Distribution
    privacy: PrivacyLevel = PrivacyLevel.PUBLIC
    license: str = "MIT"
    homepage: str = ""
    repository: str = ""
    documentation: str = ""

    # Quality
    test_coverage: float = 0.0
    performance_benchmark: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "author": self.author,
            "description": self.description,
            "category": self.category.value,
            "tags": self.tags,
            "robot_models": self.robot_models,
            "python_version": self.python_version,
            "dependencies": self.dependencies,
            "qoobot_sdk_version": self.qoobot_sdk_version,
            "privacy": self.privacy.value,
            "license": self.license,
            "homepage": self.homepage,
            "repository": self.repository,
            "documentation": self.documentation,
            "test_coverage": self.test_coverage,
        }


@dataclass
class SubmissionResult:
    """Result of a skill submission to qoostore."""

    success: bool
    submission_id: str = ""
    status: ReviewStatus = ReviewStatus.DRAFT
    message: str = ""
    review_url: str = ""
    errors: List[str] = field(default_factory=list)


@dataclass
class MarketSkill:
    """A skill listed on the qoostore marketplace."""

    skill_id: str
    name: str
    version: str
    author: str
    description: str
    category: SkillCategory
    downloads: int = 0
    rating: float = 0.0
    reviews_count: int = 0
    updated_at: str = ""
    package_url: str = ""


# ---------------------------------------------------------------------------
# qoostore Client
# ---------------------------------------------------------------------------

class qoostoreClient:
    """Client for interacting with the qoostore marketplace.

    Provides skill submission, search, and management APIs.

    Usage:
        client = qoostoreClient(api_key="qea_xxx")
        client.authenticate()
        result = client.submit_skill("dist/my-skill-1.0.0.qooskills")
    """

    BASE_URL = "https://api.qoostore.qoobot.ai/v1"

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        self.api_key = api_key
        self.base_url = base_url or self.BASE_URL
        self._authenticated = False
        self._session_token: Optional[str] = None

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    def authenticate(self) -> bool:
        """Authenticate with the qoostore API."""
        if not self.api_key:
            return False
        # In production: POST /auth/token
        self._authenticated = True
        self._session_token = "session_placeholder"
        return True

    # ------------------------------------------------------------------
    # Skill Submission
    # ------------------------------------------------------------------

    def submit_skill(
        self,
        package_path: Path,
        metadata: Optional[SkillMetadata] = None,
        changelog: str = "",
    ) -> SubmissionResult:
        """Submit a skill package to the marketplace.

        Args:
            package_path: Path to .qooskills package file
            metadata: Skill metadata (extracted from package if None)
            changelog: Version changelog

        Returns:
            SubmissionResult with submission status
        """
        if not package_path.exists():
            return SubmissionResult(
                success=False,
                message=f"Package not found: {package_path}",
            )

        # Validate package
        validation = self.validate_package(package_path)
        if not validation["valid"]:
            return SubmissionResult(
                success=False,
                message="Package validation failed",
                errors=validation["errors"],
            )

        # Extract or use provided metadata
        if metadata is None:
            metadata = self._extract_metadata(package_path)

        # In production: POST /skills/submit
        submission_id = hashlib.sha256(
            f"{metadata.name}:{metadata.version}:{datetime.now().isoformat()}".encode()
        ).hexdigest()[:12]

        return SubmissionResult(
            success=True,
            submission_id=submission_id,
            status=ReviewStatus.SUBMITTED,
            message="Skill submitted for review",
            review_url=f"https://qoostore.qoobot.ai/skills/{submission_id}/review",
        )

    def get_submission_status(self, submission_id: str) -> SubmissionResult:
        """Check the review status of a submission."""
        # In production: GET /skills/submissions/{submission_id}
        return SubmissionResult(
            success=True,
            submission_id=submission_id,
            status=ReviewStatus.IN_REVIEW,
            message="Skill is under review",
        )

    def withdraw_submission(self, submission_id: str) -> SubmissionResult:
        """Withdraw a pending submission."""
        return SubmissionResult(
            success=True,
            submission_id=submission_id,
            status=ReviewStatus.DRAFT,
            message="Submission withdrawn",
        )

    # ------------------------------------------------------------------
    # Package Validation
    # ------------------------------------------------------------------

    def validate_package(self, package_path: Path) -> Dict[str, Any]:
        """Validate a .qooskills package for marketplace requirements."""
        errors = []

        if not zipfile.is_zipfile(package_path):
            errors.append("Not a valid ZIP file")

        try:
            with zipfile.ZipFile(package_path, "r") as zf:
                names = zf.namelist()

                # Check required files
                if "manifest.json" not in names:
                    errors.append("Missing manifest.json")
                else:
                    manifest = json.loads(zf.read("manifest.json"))
                    required_fields = ["name", "version", "author", "description"]
                    for field in required_fields:
                        if field not in manifest:
                            errors.append(f"manifest.json missing '{field}'")

                if "src/" not in "".join(names):
                    errors.append("Missing src/ directory")

                # Check file size limits
                total_size = sum(info.file_size for info in zf.infolist())
                max_size = 500 * 1024 * 1024  # 500 MB
                if total_size > max_size:
                    errors.append(f"Package size {total_size / 1024 / 1024:.1f}MB exceeds {max_size / 1024 / 1024:.0f}MB limit")

        except (zipfile.BadZipFile, json.JSONDecodeError) as e:
            errors.append(str(e))

        return {
            "valid": len(errors) == 0,
            "errors": errors,
        }

    def _extract_metadata(self, package_path: Path) -> SkillMetadata:
        """Extract metadata from a .qooskills package."""
        with zipfile.ZipFile(package_path, "r") as zf:
            manifest = json.loads(zf.read("manifest.json"))
            return SkillMetadata(
                name=manifest.get("name", ""),
                version=manifest.get("version", "0.1.0"),
                author=manifest.get("author", "unknown"),
                description=manifest.get("description", ""),
                tags=manifest.get("tags", []),
                dependencies=manifest.get("dependencies", {}),
            )

    # ------------------------------------------------------------------
    # Skill Discovery
    # ------------------------------------------------------------------

    def search_skills(
        self,
        query: str = "",
        category: Optional[SkillCategory] = None,
        tags: Optional[List[str]] = None,
        sort_by: str = "downloads",
        limit: int = 20,
        offset: int = 0,
    ) -> List[MarketSkill]:
        """Search for skills on the marketplace."""
        # In production: GET /skills/search
        return []

    def get_skill(self, skill_id: str) -> Optional[MarketSkill]:
        """Get detailed information about a skill."""
        # In production: GET /skills/{skill_id}
        return None

    def get_popular_skills(self, limit: int = 10) -> List[MarketSkill]:
        """Get most popular skills."""
        # In production: GET /skills/popular
        return []

    def get_user_skills(self, author: str) -> List[MarketSkill]:
        """Get all skills by an author."""
        # In production: GET /skills?author={author}
        return []

    # ------------------------------------------------------------------
    # Download & Install
    # ------------------------------------------------------------------

    def download_skill(self, skill_id: str, output_dir: Path) -> Optional[Path]:
        """Download a skill package from the marketplace."""
        # In production: GET /skills/{skill_id}/download
        output_path = output_dir / f"{skill_id}.qooskills"
        return output_path

    def install_skill(self, skill_id: str, project_dir: Path) -> bool:
        """Download and install a skill into a project."""
        downloaded = self.download_skill(skill_id, project_dir / ".qoobot" / "skills")
        if not downloaded:
            return False
        # In production: extract and register skill
        return True


# ---------------------------------------------------------------------------
# CLI Integration Helper
# ---------------------------------------------------------------------------

def create_qoostore_client(
    api_key: Optional[str] = None,
    config_path: Optional[Path] = None,
) -> qoostoreClient:
    """Create a qoostoreClient from config or environment.

    Priority:
    1. Explicit api_key parameter
    2. qoostore_API_KEY environment variable
    3. qoo.toml project config
    """
    import os

    if api_key:
        return qoostoreClient(api_key=api_key)

    env_key = os.environ.get("qoostore_API_KEY")
    if env_key:
        return qoostoreClient(api_key=env_key)

    # Try config file
    if config_path and config_path.exists():
        try:
            import tomllib
            config = tomllib.loads(config_path.read_text())
            eco_config = config.get("qoostore", {})
            if "api_key" in eco_config:
                return qoostoreClient(api_key=eco_config["api_key"])
        except Exception:
            pass

    return qoostoreClient()
