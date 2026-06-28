"""
qoodev migration guide generator — ROS 1/2 → QooBot and NVIDIA Isaac → QooBot migration.

对标：ROS Migration Guide + NVIDIA Isaac Migration
提供自动化迁移检查、代码转换建议、兼容性对比。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class MigrationSource(str, Enum):
    ROS1 = "ros1"
    ROS2 = "ros2"
    NVIDIA_ISAAC = "nvidia_isaac"
    CUSTOM = "custom"


class ChangeType(str, Enum):
    RENAME = "rename"
    API_CHANGE = "api_change"
    ARCHITECTURE = "architecture"
    CONFIG = "config"
    BUILD_SYSTEM = "build_system"
    REMOVED = "removed"
    NEW_CONCEPT = "new_concept"


class MigrationStatus(str, Enum):
    MIGRATED = "migrated"
    PARTIAL = "partial"
    NOT_MIGRATED = "not_migrated"
    N_A = "n/a"


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class MigrationMapping:
    """Map a source API/pattern to QooBot equivalent."""
    source: str
    target: str
    change_type: ChangeType
    description: str = ""
    code_before: str = ""
    code_after: str = ""
    automated: bool = False
    notes: str = ""


@dataclass
class MigrationChecklist:
    """A migration checklist item."""
    category: str
    item: str
    status: MigrationStatus = MigrationStatus.NOT_MIGRATED
    source: MigrationSource = MigrationSource.ROS2
    notes: str = ""


@dataclass
class MigrationReport:
    """Full migration report."""
    source: MigrationSource
    mappings: List[MigrationMapping] = field(default_factory=list)
    checklist: List[MigrationChecklist] = field(default_factory=list)
    migrated_count: int = 0
    total_count: int = 0


# ---------------------------------------------------------------------------
# Migration mappings database
# ---------------------------------------------------------------------------

class MigrationDatabase:
    """Pre-defined migration mappings for common frameworks."""

    # -- ROS 1 → QooBot ----------------------------------------------------

    ROS1_MAPPINGS: List[MigrationMapping] = [
        MigrationMapping("roscpp::NodeHandle", "qoocore::Node",
                         ChangeType.RENAME, "ROS NodeHandle → QooBot Node",
                         "ros::NodeHandle nh;", "auto node = qoocore::Node::create(\"my_node\");"),
        MigrationMapping("ros::Publisher", "qoocore::Publisher",
                         ChangeType.RENAME, "ROS Publisher → QooBot Publisher",
                         "ros::Publisher pub = nh.advertise<std_msgs::String>(\"topic\", 10);",
                         "auto pub = node->create_publisher<std_msgs::String>(\"topic\", 10);"),
        MigrationMapping("ros::Subscriber", "qoocore::Subscriber",
                         ChangeType.RENAME, "ROS Subscriber → QooBot Subscriber",
                         "ros::Subscriber sub = nh.subscribe(\"topic\", 10, callback);",
                         "auto sub = node->create_subscription<std_msgs::String>(\"topic\", 10, callback);"),
        MigrationMapping("ros::spin()", "qoocore::executor::spin(node)",
                         ChangeType.API_CHANGE, "Event loop"),
        MigrationMapping("ros::Rate", "qoocore::Rate",
                         ChangeType.RENAME, "Loop rate control",
                         "ros::Rate rate(10.0); rate.sleep();",
                         "qoocore::Rate rate(10.0); rate.sleep();"),
        MigrationMapping("ros::Time", "qoocore::Time",
                         ChangeType.RENAME, "Time utilities"),
        MigrationMapping("roscpp/ros.h", "qoocore/qoocore.h",
                         ChangeType.RENAME, "Main header include"),
        MigrationMapping("catkin_make / catkin build", "qoobot build",
                         ChangeType.BUILD_SYSTEM, "Build system",
                         automated=False),
        MigrationMapping("package.xml", "qoobot.toml",
                         ChangeType.CONFIG, "Package metadata",
                         automated=False),
        MigrationMapping("CMakeLists.txt (catkin)", "CMakeLists.txt (qoobot)",
                         ChangeType.BUILD_SYSTEM, "CMake configuration"),
        MigrationMapping("roslaunch", "qoo launch",
                         ChangeType.API_CHANGE, "Launch system",
                         "roslaunch my_pkg my_launch.launch",
                         "qoo launch my_pkg:my_launch"),
        MigrationMapping("rosbag", "qoo record / qoo replay",
                         ChangeType.API_CHANGE, "Data recording",
                         "rosbag record -a", "qoo record --all"),
        MigrationMapping("rviz", "qoodev dashboard",
                         ChangeType.ARCHITECTURE, "Visualization",
                         automated=False),
        MigrationMapping("tf / tf2", "qoocore::TransformTree",
                         ChangeType.API_CHANGE, "Transform system",
                         automated=False),
        MigrationMapping("actionlib", "qoocore::ActionServer / ActionClient",
                         ChangeType.API_CHANGE, "Action interface"),
        MigrationMapping("dynamic_reconfigure", "qoocore::ParameterService",
                         ChangeType.API_CHANGE, "Dynamic parameters"),
        MigrationMapping("nodelet", "qoocore::ComposableNode",
                         ChangeType.API_CHANGE, "Node composition"),
        MigrationMapping("ros::ServiceServer", "qoocore::Service",
                         ChangeType.RENAME, "Service server"),
        MigrationMapping("ros::ServiceClient", "qoocore::ServiceClient",
                         ChangeType.RENAME, "Service client"),
        MigrationMapping("ros::param", "qoocore::ParameterService",
                         ChangeType.API_CHANGE, "Parameter server"),
    ]

    # -- ROS 2 → QooBot ----------------------------------------------------

    ROS2_MAPPINGS: List[MigrationMapping] = [
        MigrationMapping("rclcpp::Node", "qoocore::Node",
                         ChangeType.RENAME, "Node class"),
        MigrationMapping("rclpy.node.Node", "qoobot_sdk.Node",
                         ChangeType.RENAME, "Python Node class"),
        MigrationMapping("ament_cmake", "qoobot build",
                         ChangeType.BUILD_SYSTEM, "Build tool"),
        MigrationMapping("colcon build", "qoobot build",
                         ChangeType.BUILD_SYSTEM, "Build command"),
        MigrationMapping("rclcpp::executors::MultiThreadedExecutor", "qoocore::executor::MultiThreadedExecutor",
                         ChangeType.RENAME, "Multi-threaded executor"),
        MigrationMapping("rclcpp::CallbackGroup", "qoocore::CallbackGroup",
                         ChangeType.RENAME, "Callback groups"),
        MigrationMapping("rmw", "qoocore::middleware",
                         ChangeType.ARCHITECTURE, "Middleware layer"),
        MigrationMapping("ros2 bag", "qoo record / qoo replay",
                         ChangeType.API_CHANGE, "Data recording"),
        MigrationMapping("ros2 launch", "qoo launch",
                         ChangeType.API_CHANGE, "Launch system"),
        MigrationMapping("ros2 topic/ros2 service", "qoo topic / qoo service",
                         ChangeType.API_CHANGE, "CLI tools"),
        MigrationMapping("rclcpp::spin(node)", "qoocore::executor::spin(node)",
                         ChangeType.RENAME, "Spin function"),
    ]

    # -- NVIDIA Isaac → QooBot --------------------------------------------

    ISAAC_MAPPINGS: List[MigrationMapping] = [
        MigrationMapping("isaac::alice::Codelet", "qoocore::Skill",
                         ChangeType.ARCHITECTURE, "Codelet → Skill",
                         "class MyCodelet : public isaac::alice::Codelet {",
                         "class MySkill : public qoocore::Skill {",
                         automated=False),
        MigrationMapping("isaac::alice::Message", "qoocore::Message",
                         ChangeType.RENAME, "Message passing"),
        MigrationMapping("isaac::sight", "qoodev dashboard",
                         ChangeType.ARCHITECTURE, "Visualization (Sight → Dashboard)"),
        MigrationMapping("isaac::navigation", "qoobody::navigation",
                         ChangeType.RENAME, "Navigation module"),
        MigrationMapping("isaac::perception", "qoobrain::perception",
                         ChangeType.RENAME, "Perception module"),
        MigrationMapping("isaac::manipulation", "qoobody::manipulation",
                         ChangeType.RENAME, "Manipulation module"),
        MigrationMapping("bazel build", "qoobot build",
                         ChangeType.BUILD_SYSTEM, "Build system"),
        MigrationMapping("isaac_graph", "qoo launch",
                         ChangeType.ARCHITECTURE, "Application graph → launch"),
        MigrationMapping("Pose2/Pose3", "qoocore::SE2 / qoocore::SE3",
                         ChangeType.RENAME, "Pose representation"),
        MigrationMapping("Composite Atlas", "qoocore::DynamicBatcher",
                         ChangeType.ARCHITECTURE, "Batching system"),
        MigrationMapping("GXF (Graph eXecution Format)", "qoocore::Graph",
                         ChangeType.ARCHITECTURE, "Execution graph"),
        MigrationMapping("NITROS (Isaac Transport for ROS)", "qoocore::middleware",
                         ChangeType.ARCHITECTURE, "Transport layer"),
    ]

    @classmethod
    def get_mappings(cls, source: MigrationSource) -> List[MigrationMapping]:
        if source == MigrationSource.ROS1:
            return cls.ROS1_MAPPINGS
        elif source == MigrationSource.ROS2:
            return cls.ROS2_MAPPINGS
        elif source == MigrationSource.NVIDIA_ISAAC:
            return cls.ISAAC_MAPPINGS
        return []


# ---------------------------------------------------------------------------
# MigrationAnalyzer
# ---------------------------------------------------------------------------

class MigrationAnalyzer:
    """Analyze source code and generate migration reports.

    Usage::

        analyzer = MigrationAnalyzer(MigrationSource.ROS1)
        report = analyzer.analyze_project(Path("my_ros_pkg"))
        analyzer.generate_guide(report, Path("MIGRATION.md"))
    """

    def __init__(self, source: MigrationSource):
        self.source = source
        self._mappings = MigrationDatabase.get_mappings(source)
        self._pattern_map: Dict[re.Pattern, MigrationMapping] = {}

        # compile regex patterns for each mapping
        for m in self._mappings:
            pattern = re.escape(m.source)
            self._pattern_map[re.compile(pattern, re.IGNORECASE)] = m

    def analyze_file(self, file_path: Path) -> List[Tuple[int, str, MigrationMapping]]:
        """Find migration-relevant patterns in a single file."""
        findings: List[Tuple[int, str, MigrationMapping]] = []

        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return findings

        for line_no, line in enumerate(content.splitlines(), 1):
            for pattern, mapping in self._pattern_map.items():
                if pattern.search(line):
                    findings.append((line_no, line.strip(), mapping))

        return findings

    def analyze_project(self, project_path: Path) -> MigrationReport:
        """Analyze entire project for migration needs."""
        report = MigrationReport(source=self.source, mappings=list(self._mappings))

        source_extensions = {".py", ".cpp", ".h", ".hpp", ".c", ".cc", ".cxx", ".xml", ".launch", ".cfg", ".yaml", ".yml", ".toml"}

        all_findings: Dict[str, Set[str]] = {}
        for ext in source_extensions:
            for f in project_path.rglob(f"*{ext}"):
                if any(part.startswith(".") for part in f.parts):
                    continue
                findings = self.analyze_file(f)
                for line_no, line, mapping in all_findings:
                    all_findings.setdefault(mapping.source, set()).add(str(f))

        # build checklist
        checklist_items = [
            ("Build System", "Build system configuration", MigrationStatus.NOT_MIGRATED),
            ("Build System", "Package metadata file", MigrationStatus.NOT_MIGRATED),
            ("Messages", "Message definitions", MigrationStatus.NOT_MIGRATED),
            ("Services", "Service definitions", MigrationStatus.NOT_MIGRATED),
            ("Launch", "Launch/application files", MigrationStatus.NOT_MIGRATED),
            ("Nodes", "Node/Codelet implementations", MigrationStatus.NOT_MIGRATED),
            ("Publishers", "Publisher declarations", MigrationStatus.NOT_MIGRATED),
            ("Subscribers", "Subscriber declarations", MigrationStatus.NOT_MIGRATED),
            ("Parameters", "Parameter configuration", MigrationStatus.NOT_MIGRATED),
            ("Visualization", "Visualization/RVIZ config", MigrationStatus.NOT_MIGRATED),
            ("Tests", "Test infrastructure", MigrationStatus.NOT_MIGRATED),
            ("Documentation", "README and docs", MigrationStatus.NOT_MIGRATED),
        ]

        for category, item, status in checklist_items:
            report.checklist.append(MigrationChecklist(category=category, item=item, status=status, source=self.source))

        report.total_count = len(report.checklist)
        report.migrated_count = sum(1 for c in report.checklist if c.status == MigrationStatus.MIGRATED)

        return report

    # -- guide generation ---------------------------------------------------

    def generate_guide(self, report: MigrationReport, output_path: Path) -> None:
        """Generate a comprehensive migration guide markdown file."""
        lines = self._build_guide_markdown(report)
        output_path.write_text("\n".join(lines), encoding="utf-8")

    def _build_guide_markdown(self, report: MigrationReport) -> List[str]:
        source_name = {
            MigrationSource.ROS1: "ROS 1",
            MigrationSource.ROS2: "ROS 2",
            MigrationSource.NVIDIA_ISAAC: "NVIDIA Isaac",
        }.get(self.source, str(self.source.value))

        lines = [
            f"# {source_name} → QooBot Migration Guide",
            "",
            f"> Auto-generated by qoodev migration analyzer",
            f"> Source: {self.source.value}",
            "",
            "## Overview",
            "",
            f"This guide helps you migrate your {source_name} project to QooBot.",
            "QooBot provides a modern, high-performance robotics framework with built-in",
            "AI acceleration, cloud-native architecture, and developer tooling.",
            "",
            "## Migration Checklist",
            "",
            "| Category | Item | Status | Notes |",
            "|----------|------|--------|-------|",
        ]

        for item in report.checklist:
            status_icon = {"migrated": "✅", "partial": "🔄", "not_migrated": "⬜", "n/a": "➖"}[item.status.value]
            lines.append(f"| {item.category} | {item.item} | {status_icon} {item.status.value} | |")

        lines.extend([
            "",
            "## API Migration Table",
            "",
            "| Source API | QooBot API | Change Type | Auto? |",
            "|------------|------------|-------------|-------|",
        ])

        for m in self._mappings:
            auto = "✅" if m.automated else "🔧"
            lines.append(f"| `{m.source}` | `{m.target}` | {m.change_type.value} | {auto} |")

        lines.extend([
            "",
            "## Code Migration Examples",
            "",
        ])

        for m in self._mappings:
            if m.code_before and m.code_after:
                lines.extend([
                    f"### {m.source} → {m.target}",
                    "",
                    f"**{m.description}**",
                    "",
                    "```cpp",
                    f"// Before ({source_name}):",
                    m.code_before,
                    "",
                    f"// After (QooBot):",
                    m.code_after,
                    "```",
                    "",
                ])

        lines.extend([
            "## Architecture Differences",
            "",
            "### Communication",
            f"- **{source_name}**: Topic-based pub/sub with DDS/TCPROS",
            "- **QooBot**: Topic-based pub/sub with pluggable middleware (DDS/Zenoh/Shared Memory)",
            "",
            "### Build System",
            f"- **{source_name}**: catkin/colcon/bazel",
            "- **QooBot**: Unified `qoobot build` with CMake + Python backend",
            "",
            "### Node Model",
            f"- **{source_name}**: Single-threaded or multi-threaded executor",
            "- **QooBot**: Composable nodes with automatic batching + DSP offload",
            "",
            "### AI Integration",
            f"- **{source_name}**: External libraries (TensorRT, ONNX)",
            "- **QooBot**: Built-in qoocore inference engine with BEV/LLM/VLM support",
            "",
            "## Quick Start",
            "",
            "```bash",
            "# Install QooBot",
            "pip install qoobot",
            "",
            "# Create new project",
            "qoo init --from-{source} my_project".format(source=self.source.value.replace("_", "-")),
            "",
            "# Build",
            "qoobot build",
            "",
            "# Run",
            "qoo launch my_project:main",
            "```",
            "",
            "## Need Help?",
            "",
            "- Documentation: https://docs.qoobot.dev",
            "- Community: https://community.qoobot.dev",
            "- Migration Support: migration@qoobot.dev",
        ])

        return lines

    # -- automated conversion -----------------------------------------------

    def apply_automated_migrations(self, file_path: Path, dry_run: bool = True) -> List[str]:
        """Apply automated find-and-replace migrations."""
        changes: List[str] = []
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return changes

        new_content = content
        for mapping in self._mappings:
            if not mapping.automated:
                continue
            if mapping.source in new_content:
                new_content = new_content.replace(mapping.source, mapping.target)
                changes.append(f"{mapping.source} → {mapping.target}")

        if not dry_run and changes:
            file_path.write_text(new_content, encoding="utf-8")

        return changes
