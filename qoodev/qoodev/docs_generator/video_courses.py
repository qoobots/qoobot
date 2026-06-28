"""
qoodev video course generator — official video tutorial series and skill development series.

对标：Udacity Robotics Nanodegree + ROS Industrial Training
提供课程大纲生成、代码示例嵌入、练习场景生成。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class CourseLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class LessonType(str, Enum):
    THEORY = "theory"  # concept explanation
    DEMO = "demo"  # live demonstration
    CODING = "coding"  # hands-on coding
    EXERCISE = "exercise"  # practice exercise
    PROJECT = "project"  # capstone project
    REVIEW = "review"  # review & Q&A


class ContentFormat(str, Enum):
    VIDEO = "video"
    INTERACTIVE = "interactive"
    NOTEBOOK = "notebook"
    SIMULATION = "simulation"


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class LessonSegment:
    """A segment within a lesson."""
    title: str
    duration_min: float
    content: str = ""
    segment_type: LessonType = LessonType.THEORY
    code_snippets: List[str] = field(default_factory=list)
    key_points: List[str] = field(default_factory=list)
    quiz_questions: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class Lesson:
    """A single lesson in a course."""
    id: str
    title: str
    description: str = ""
    duration_min: float = 0.0
    level: CourseLevel = CourseLevel.BEGINNER
    lesson_type: LessonType = LessonType.THEORY
    segments: List[LessonSegment] = field(default_factory=list)
    prerequisites: List[str] = field(default_factory=list)
    learning_objectives: List[str] = field(default_factory=list)
    resources: List[Dict[str, str]] = field(default_factory=list)
    exercises: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class Course:
    """A complete video course."""
    id: str
    title: str
    description: str = ""
    level: CourseLevel = CourseLevel.BEGINNER
    total_duration_hours: float = 0.0
    lessons: List[Lesson] = field(default_factory=list)
    target_audience: str = ""
    tags: List[str] = field(default_factory=list)
    author: str = "QooBot Team"


# ---------------------------------------------------------------------------
# Pre-defined course curricula
# ---------------------------------------------------------------------------

class CourseCatalog:
    """Pre-defined course curricula."""

    QOOBOT_101_BEGINNER = Course(
        id="qoobot-101",
        title="QooBot 101: Getting Started with Robot Development",
        description="Master the fundamentals of QooBot — from installation to your first autonomous robot skill.",
        level=CourseLevel.BEGINNER,
        target_audience="New robotics developers, ROS users migrating to QooBot",
        tags=["beginner", "fundamentals", "getting-started"],
        lessons=[
            Lesson("01", "Introduction to QooBot", "Overview of the QooBot ecosystem and architecture.", 15,
                   segments=[
                       LessonSegment("What is QooBot?", 5, "High-level overview of the QooBot platform"),
                       LessonSegment("Ecosystem Tour", 5, "Walkthrough of qoobrain, qoobody, qoocore, qoodev"),
                       LessonSegment("Installation", 5, "Step-by-step installation guide", segment_type=LessonType.DEMO),
                   ],
                   learning_objectives=["Understand QooBot architecture", "Install QooBot successfully"]),
            Lesson("02", "Your First QooBot Project", "Create and run your first project.", 20,
                   segments=[
                       LessonSegment("Project Scaffolding", 5, "Using qoo init to create projects", segment_type=LessonType.DEMO),
                       LessonSegment("Hello Robot", 10, "Write a simple robot control program", segment_type=LessonType.CODING,
                                    code_snippets=[
                                        "qoo init my_first_robot",
                                        "# my_first_robot/skills/hello_robot.py",
                                        "from qoobot_sdk import Skill",
                                        "class HelloRobot(Skill):",
                                        "    def on_start(self):",
                                        "        self.logger.info('Hello, QooBot!')",
                                    ]),
                       LessonSegment("Running in Simulation", 5, "Launch and test in MuJoCo", segment_type=LessonType.DEMO),
                   ],
                   learning_objectives=["Create a project", "Write a simple skill", "Run in simulation"]),
            Lesson("03", "Understanding Skills", "Deep dive into the Skill framework.", 25,
                   prerequisites=["02"],
                   segments=[
                       LessonSegment("Skill Lifecycle", 8, "on_start, on_stop, on_pause, on_resume"),
                       LessonSegment("Sensor Access", 8, "Reading camera, LiDAR, IMU data", segment_type=LessonType.CODING),
                       LessonSegment("Actuator Control", 9, "Controlling motors, grippers, mobile base", segment_type=LessonType.CODING),
                   ],
                   learning_objectives=["Understand skill lifecycle", "Read sensor data", "Control actuators"]),
            Lesson("04", "Simulation Environment", "Master the simulation tools.", 20,
                   prerequisites=["02"],
                   segments=[
                       LessonSegment("Scene Selection", 6, "Loading factory/warehouse/home scenes"),
                       LessonSegment("Sensor Configuration", 7, "Configuring virtual sensors"),
                       LessonSegment("Multi-Robot Setup", 7, "Running multiple robots in one scene", segment_type=LessonType.DEMO),
                   ]),
            Lesson("05", "Debugging & Visualization", "Debug skills with qoodev tools.", 20,
                   prerequisites=["03"],
                   segments=[
                       LessonSegment("Real-time Logging", 5, "Using the log dashboard"),
                       LessonSegment("Variable Monitor", 5, "Inspecting runtime variables"),
                       LessonSegment("3D Scene View", 5, "Visualizing robot state in 3D"),
                       LessonSegment("Replay Debugging", 5, "Recording and replaying sessions", segment_type=LessonType.EXERCISE),
                   ]),
            Lesson("06", "Capstone: Pick-and-Place", "Build a complete pick-and-place skill.", 30,
                   prerequisites=["03", "04", "05"],
                   lesson_type=LessonType.PROJECT,
                   segments=[
                       LessonSegment("Task Planning", 8, "Design the pick-and-place workflow"),
                       LessonSegment("Perception Pipeline", 8, "Object detection and pose estimation", segment_type=LessonType.CODING),
                       LessonSegment("Motion Planning", 7, "Trajectory generation and execution"),
                       LessonSegment("Testing & Evaluation", 7, "Run regression tests, measure success rate"),
                   ],
                   learning_objectives=["Build end-to-end skill", "Integrate perception and control", "Evaluate performance"]),
        ],
    )

    QOOBOT_201_INTERMEDIATE = Course(
        id="qoobot-201",
        title="QooBot 201: Advanced Robot Skills",
        description="Deepen your skills with BEV perception, behavior trees, and multi-robot coordination.",
        level=CourseLevel.INTERMEDIATE,
        target_audience="Developers who completed QooBot 101 or have equivalent experience",
        tags=["intermediate", "perception", "behavior-trees", "multi-robot"],
        lessons=[
            Lesson("01", "BEV Perception", "Bird's-Eye-View perception for autonomous driving.", 30,
                   level=CourseLevel.INTERMEDIATE,
                   segments=[
                       LessonSegment("BEV Theory", 8, "Understanding LSS, cross-attention, and IPM methods"),
                       LessonSegment("Camera Calibration", 7, "Multi-camera extrinsic calibration"),
                       LessonSegment("BEV Pipeline Code", 10, "Implementing BEV transform", segment_type=LessonType.CODING,
                                    code_snippets=[
                                        "from qoocore.operators import bev_ops",
                                        "bev = bev_ops.lss_transform(images, intrinsics, extrinsics)",
                                    ]),
                       LessonSegment("Temporal Fusion", 5, "Fusing BEV features across time"),
                   ]),
            Lesson("02", "Behavior Trees", "Visual behavior tree design and debugging.", 25,
                   segments=[
                       LessonSegment("BT Fundamentals", 6, "Sequence, Fallback, Parallel, Decorator nodes"),
                       LessonSegment("Visual Editor", 5, "Using the behavior tree editor", segment_type=LessonType.DEMO),
                       LessonSegment("Custom Nodes", 7, "Writing custom condition and action nodes", segment_type=LessonType.CODING),
                       LessonSegment("BT Debugging", 7, "Node status highlighting, breakpoints, history"),
                   ]),
            Lesson("03", "Multi-Robot Coordination", "Coordinating multiple robots.", 25,
                   segments=[
                       LessonSegment("Coordination Patterns", 7, "Leader-follower, auction, swarm"),
                       LessonSegment("Task Assignment", 6, "Distributed task allocation"),
                       LessonSegment("Collision Avoidance", 6, "Multi-robot collision prevention"),
                       LessonSegment("Multi-Robot Simulation", 6, "Running multi-robot scenarios", segment_type=LessonType.DEMO),
                   ]),
            Lesson("04", "Model Optimization", "Optimizing models for edge deployment.", 25,
                   segments=[
                       LessonSegment("Quantization", 6, "FP32 → INT8 quantization with qoocore"),
                       LessonSegment("Model Compilation", 7, "Using qoo compile for model optimization"),
                       LessonSegment("DSP Offloading", 6, "Offloading inference to Hexagon/CEVA DSP"),
                       LessonSegment("Benchmarking", 6, "Measuring latency, power, and accuracy"),
                   ]),
            Lesson("05", "Capstone: Warehouse Robot", "Full warehouse automation system.", 35,
                   lesson_type=LessonType.PROJECT,
                   segments=[
                       LessonSegment("System Design", 8, "Architecture for warehouse automation"),
                       LessonSegment("Perception", 8, "Shelf detection, obstacle avoidance", segment_type=LessonType.CODING),
                       LessonSegment("Planning", 8, "Multi-robot path planning"),
                       LessonSegment("Integration & Test", 11, "End-to-end testing, performance analysis"),
                   ]),
        ],
    )

    QOOBOT_301_ADVANCED = Course(
        id="qoobot-301",
        title="QooBot 301: Production Robot Systems",
        description="Deploy production-grade robot systems with federated learning, cloud integration, and CI/CD.",
        level=CourseLevel.ADVANCED,
        target_audience="Experienced developers building production systems",
        tags=["advanced", "production", "federated-learning", "cloud", "ci-cd"],
        lessons=[
            Lesson("01", "Federated Learning", "Privacy-preserving distributed model training.", 30,
                   level=CourseLevel.ADVANCED,
                   segments=[
                       LessonSegment("FL Concepts", 7, "FedAvg, differential privacy, secure aggregation"),
                       LessonSegment("Setting Up FL", 7, "Configuring federated learning cluster"),
                       LessonSegment("Training Loop", 8, "Local training + global aggregation", segment_type=LessonType.CODING),
                       LessonSegment("Privacy Budget", 8, "Managing (ε,δ)-differential privacy budget"),
                   ]),
            Lesson("02", "Cloud Integration", "Hybrid cloud-edge deployment.", 25,
                   segments=[
                       LessonSegment("Architecture", 6, "Local/Cloud/Hybrid inference modes"),
                       LessonSegment("REST/gRPC API", 6, "Building and consuming robot APIs"),
                       LessonSegment("Cloud Deployment", 7, "Deploying services to cloud", segment_type=LessonType.DEMO),
                       LessonSegment("Monitoring", 6, "Cloud-based fleet monitoring"),
                   ]),
            Lesson("03", "CI/CD Pipeline", "Automated testing and deployment.", 20,
                   segments=[
                       LessonSegment("GitHub Actions Setup", 5, "Configuring CI for robot projects"),
                       LessonSegment("Simulation Tests", 5, "Regression testing in simulation"),
                       LessonSegment("Hardware-in-Loop", 5, "HIL testing setup"),
                       LessonSegment("Deployment Automation", 5, "Automated release pipeline", segment_type=LessonType.DEMO),
                   ]),
            Lesson("04", "Security & Compliance", "Robot security best practices.", 25,
                   segments=[
                       LessonSegment("TEE Runtime", 7, "TrustZone/SGX secure execution"),
                       LessonSegment("Code Signing", 6, "Skill signing with qooauth certificates"),
                       LessonSegment("Privacy Labels", 6, "Privacy labeling for skills"),
                       LessonSegment("Compliance Testing", 6, "Running compliance checks"),
                   ]),
            Lesson("05", "Capstone: Fleet Management", "Multi-robot fleet management system.", 40,
                   lesson_type=LessonType.PROJECT,
                   segments=[
                       LessonSegment("System Architecture", 8, "Designing fleet management backend"),
                       LessonSegment("Fleet Dashboard", 8, "Real-time fleet monitoring dashboard", segment_type=LessonType.CODING),
                       LessonSegment("Federated Training", 8, "Federated model updates across fleet"),
                       LessonSegment("OTA Updates", 8, "Over-the-air skill and model updates"),
                       LessonSegment("Production Launch", 8, "Final deployment and monitoring"),
                   ]),
        ],
    )

    @classmethod
    def all_courses(cls) -> List[Course]:
        return [cls.QOOBOT_101_BEGINNER, cls.QOOBOT_201_INTERMEDIATE, cls.QOOBOT_301_ADVANCED]


# ---------------------------------------------------------------------------
# CourseGenerator
# ---------------------------------------------------------------------------

class CourseGenerator:
    """Generate course materials in various formats.

    Usage::

        gen = CourseGenerator()
        gen.generate_syllabus(CourseCatalog.QOOBOT_101_BEGINNER, Path("syllabus.md"))
        gen.generate_jupyter_notebook(CourseCatalog.QOOBOT_101_BEGINNER.lessons[1], Path("lesson02.ipynb"))
    """

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or Path("qoodev_courses")

    def generate_syllabus(self, course: Course, output_path: Optional[Path] = None) -> str:
        """Generate course syllabus in Markdown."""
        lines = [
            f"# {course.title}",
            f"*{course.description}*",
            "",
            f"**Level**: {course.level.value}  ",
            f"**Audience**: {course.target_audience}  ",
            f"**Duration**: ~{course.total_duration_hours or sum(l.duration_min for l in course.lessons) / 60:.1f} hours  ",
            f"**Tags**: {', '.join(course.tags)}",
            "",
            "## Syllabus",
            "",
            "| # | Lesson | Duration | Type |",
            "|---|--------|----------|------|",
        ]

        for lesson in course.lessons:
            lines.append(f"| {lesson.id} | {lesson.title} | {lesson.duration_min} min | {lesson.lesson_type.value} |")

        lines.append("")
        lines.append("## Lesson Details")
        lines.append("")

        for lesson in course.lessons:
            lines.extend([
                f"### Lesson {lesson.id}: {lesson.title}",
                "",
                f"{lesson.description}",
                "",
                f"**Duration**: {lesson.duration_min} min  ",
                f"**Type**: {lesson.lesson_type.value}",
                "",
            ])

            if lesson.learning_objectives:
                lines.append("**Learning Objectives**:")
                for obj in lesson.learning_objectives:
                    lines.append(f"- {obj}")
                lines.append("")

            if lesson.prerequisites:
                lines.append("**Prerequisites**: " + ", ".join(f"Lesson {p}" for p in lesson.prerequisites))
                lines.append("")

            if lesson.segments:
                lines.append("**Segments**:")
                for seg in lesson.segments:
                    lines.append(f"- [{seg.duration_min} min] {seg.title} ({seg.segment_type.value})")
                lines.append("")

            if lesson.exercises:
                lines.append("**Exercises**:")
                for ex in lesson.exercises:
                    lines.append(f"- {ex.get('title', 'Exercise')}")
                lines.append("")

        result = "\n".join(lines)
        if output_path:
            output_path.write_text(result, encoding="utf-8")
        return result

    def generate_lesson_script(self, lesson: Lesson, output_path: Optional[Path] = None) -> str:
        """Generate a detailed lesson script / speaker notes."""
        lines = [
            f"# Lesson {lesson.id}: {lesson.title}",
            f"*Duration: {lesson.duration_min} minutes*",
            "",
            "## Speaker Notes",
            "",
        ]

        for i, seg in enumerate(lesson.segments, 1):
            lines.extend([
                f"### Segment {i}: {seg.title} ({seg.duration_min} min)",
                "",
                f"**[{seg.segment_type.value.upper()}]**",
                "",
                seg.content or f"*Content placeholder for: {seg.title}*",
                "",
            ])

            if seg.key_points:
                lines.append("**Key Points**:")
                for pt in seg.key_points:
                    lines.append(f"- {pt}")
                lines.append("")

            if seg.code_snippets:
                lines.append("**Code Snippets**:")
                lines.append("")
                for snippet in seg.code_snippets:
                    lines.append("```python")
                    lines.append(snippet)
                    lines.append("```")
                    lines.append("")

            if seg.quiz_questions:
                lines.append("**Checkpoint Questions**:")
                for q in seg.quiz_questions:
                    lines.append(f"- Q: {q.get('question', '')}")
                    lines.append(f"  A: {q.get('answer', '')}")
                lines.append("")

        result = "\n".join(lines)
        if output_path:
            output_path.write_text(result, encoding="utf-8")
        return result

    def generate_exercise_notebook(self, lesson: Lesson, output_path: Optional[Path] = None) -> str:
        """Generate a Jupyter notebook JSON for the lesson."""
        cells = []

        # title cell
        cells.append({
            "cell_type": "markdown",
            "metadata": {},
            "source": [f"# Exercise: {lesson.title}", "", lesson.description],
        })

        for obj in lesson.learning_objectives:
            cells.append({
                "cell_type": "markdown",
                "metadata": {},
                "source": [f"- {obj}"],
            })

        # code cells from segments
        for seg in lesson.segments:
            if seg.code_snippets:
                cells.append({
                    "cell_type": "markdown",
                    "metadata": {},
                    "source": [f"## {seg.title}"],
                })
                for snippet in seg.code_snippets:
                    cells.append({
                        "cell_type": "code",
                        "execution_count": None,
                        "metadata": {},
                        "outputs": [],
                        "source": snippet.split("\n"),
                    })

        notebook = {
            "cells": cells,
            "metadata": {
                "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                "language_info": {"name": "python", "version": "3.10.0"},
            },
            "nbformat": 4,
            "nbformat_minor": 5,
        }

        result = json.dumps(notebook, indent=2)
        if output_path:
            output_path.write_text(result, encoding="utf-8")
        return result

    def generate_course_json(self, course: Course, output_path: Optional[Path] = None) -> str:
        """Export course structure as JSON for LMS integration."""
        data = {
            "id": course.id,
            "title": course.title,
            "description": course.description,
            "level": course.level.value,
            "total_duration_hours": course.total_duration_hours or sum(l.duration_min for l in course.lessons) / 60,
            "target_audience": course.target_audience,
            "tags": course.tags,
            "author": course.author,
            "lessons": [
                {
                    "id": l.id,
                    "title": l.title,
                    "description": l.description,
                    "duration_min": l.duration_min,
                    "level": l.level.value,
                    "lesson_type": l.lesson_type.value,
                    "prerequisites": l.prerequisites,
                    "learning_objectives": l.learning_objectives,
                    "segments": [
                        {
                            "title": s.title,
                            "duration_min": s.duration_min,
                            "segment_type": s.segment_type.value,
                            "key_points": s.key_points,
                        }
                        for s in l.segments
                    ],
                }
                for l in course.lessons
            ],
        }

        result = json.dumps(data, indent=2)
        if output_path:
            output_path.write_text(result, encoding="utf-8")
        return result


# ---------------------------------------------------------------------------
# Skill Development Series
# ---------------------------------------------------------------------------

SKILL_DEVELOPMENT_SERIES = [
    {
        "series": "Perception Skills",
        "episodes": [
            {"title": "Object Detection Pipeline", "duration_min": 25, "level": "intermediate"},
            {"title": "Semantic Segmentation", "duration_min": 25, "level": "intermediate"},
            {"title": "3D Point Cloud Processing", "duration_min": 30, "level": "advanced"},
            {"title": "Multi-Sensor Fusion", "duration_min": 30, "level": "advanced"},
            {"title": "BEV Perception for Autonomous Driving", "duration_min": 35, "level": "advanced"},
        ],
    },
    {
        "series": "Manipulation Skills",
        "episodes": [
            {"title": "Grasp Planning Basics", "duration_min": 20, "level": "beginner"},
            {"title": "Motion Planning with RRT", "duration_min": 25, "level": "intermediate"},
            {"title": "Force-Controlled Assembly", "duration_min": 30, "level": "advanced"},
            {"title": "Dual-Arm Coordination", "duration_min": 30, "level": "advanced"},
            {"title": "Imitation Learning for Manipulation", "duration_min": 35, "level": "expert"},
        ],
    },
    {
        "series": "Navigation Skills",
        "episodes": [
            {"title": "SLAM Fundamentals", "duration_min": 25, "level": "beginner"},
            {"title": "Path Planning Algorithms", "duration_min": 25, "level": "intermediate"},
            {"title": "Dynamic Obstacle Avoidance", "duration_min": 20, "level": "intermediate"},
            {"title": "Multi-Floor Navigation", "duration_min": 25, "level": "advanced"},
            {"title": "Fleet Coordination", "duration_min": 30, "level": "advanced"},
        ],
    },
]
