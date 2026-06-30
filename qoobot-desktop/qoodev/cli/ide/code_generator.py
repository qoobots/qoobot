"""
Code Generator — v1.6+

Auto-generates QooBot skeleton code from declarative configurations:
- Sensor configuration → perception pipeline code
- Behavior tree JSON → executable skill framework
- Model definition (YAML/ONNX metadata) → training + inference wrapper
- Service spec → C++/Python service skeleton with CMake/pyproject

The generator uses Jinja2 templates and produces production-ready code
that follows QooBot best practices.

Usage:
    from cli.ide import CodeGenerator

    gen = CodeGenerator(project_root)

    # Generate from sensor config
    gen.from_sensor_config("config/sensors.yaml")

    # Generate from behavior tree
    gen.from_behavior_tree("trees/grasp.btree.json")

    # Generate from model definition
    gen.from_model_def("models/detector.yaml")
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import yaml

from jinja2 import Environment, BaseLoader

from rich.console import Console
from rich.panel import Panel
from rich.tree import Tree
from rich.syntax import Syntax

console = Console()
_jinja = Environment(loader=BaseLoader())


# ============================================================================
# Data Models
# ============================================================================

class CodeLanguage(Enum):
    PYTHON = "python"
    CPP = "cpp"
    CMAKE = "cmake"
    YAML = "yaml"


class SensorType(Enum):
    CAMERA_RGB = "camera_rgb"
    CAMERA_DEPTH = "camera_depth"
    CAMERA_RGBD = "camera_rgbd"
    LIDAR_3D = "lidar_3d"
    LIDAR_2D = "lidar_2d"
    IMU = "imu"
    MICROPHONE = "microphone"
    FORCE_TORQUE = "force_torque"
    TOUCH = "touch"
    GPS = "gps"


class BehaviorTreeNodeType(Enum):
    SEQUENCE = "sequence"
    SELECTOR = "selector"
    PARALLEL = "parallel"
    CONDITION = "condition"
    ACTION = "action"
    DECORATOR = "decorator"
    SUBTREE = "subtree"


@dataclass
class SensorConfig:
    """Sensor configuration entry."""
    name: str
    sensor_type: SensorType
    topic: str = ""
    frame_id: str = ""
    frequency_hz: float = 30.0
    resolution: Optional[Tuple[int, int]] = None
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BehaviorTreeNode:
    """Behavior tree node definition."""
    id: str
    node_type: BehaviorTreeNodeType
    name: str = ""
    children: List["BehaviorTreeNode"] = field(default_factory=list)
    params: Dict[str, Any] = field(default_factory=dict)
    condition: str = ""
    action: str = ""


@dataclass
class ModelDef:
    """AI model definition."""
    name: str
    framework: str = "pytorch"  # pytorch | onnx | tensorflow
    task: str = "classification"  # classification | detection | segmentation | regression
    input_shape: List[int] = field(default_factory=lambda: [1, 3, 224, 224])
    output_shape: List[int] = field(default_factory=lambda: [1, 1000])
    precision: str = "fp32"
    backend: str = "auto"  # auto | cpu | gpu | npu


@dataclass
class ServiceSpec:
    """System service specification."""
    name: str
    language: CodeLanguage = CodeLanguage.PYTHON
    frequency_hz: float = 100.0
    inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    config_params: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# Code Generator
# ============================================================================

class CodeGenerator:
    """Generates QooBot project code from declarative configurations.

    Supports generation from:
    - Sensor configuration (YAML)
    - Behavior tree definition (JSON)
    - Model definition (YAML)
    - Service specification (YAML)
    """

    def __init__(self, project_root: Path):
        self.project_root = Path(project_root)
        self._generated: List[Path] = []

    # ── Sensor Config → Perception Code ────────────────────────────────────

    def from_sensor_config(self, config_path: str) -> List[Path]:
        """Generate perception pipeline code from sensor configuration.

        Args:
            config_path: Path to sensor configuration YAML file.

        Returns:
            List of generated file paths.
        """
        config_file = self.project_root / config_path
        if not config_file.exists():
            raise FileNotFoundError(f"Sensor config not found: {config_file}")

        raw = config_file.read_text(encoding="utf-8")
        data = yaml.safe_load(raw)

        sensors: List[SensorConfig] = []
        for s in data.get("sensors", []):
            sensors.append(SensorConfig(
                name=s["name"],
                sensor_type=SensorType(s["type"]),
                topic=s.get("topic", f"/qoobot/{s['name']}"),
                frame_id=s.get("frame_id", s["name"]),
                frequency_hz=s.get("frequency_hz", 30.0),
                resolution=tuple(s["resolution"]) if "resolution" in s else None,
                params=s.get("params", {}),
            ))

        files: List[Path] = []

        # 1. Generate perception pipeline Python module
        pipeline_code = self._generate_perception_pipeline(sensors, data)
        pipeline_path = self.project_root / "src" / "perception" / "pipeline.py"
        pipeline_path.parent.mkdir(parents=True, exist_ok=True)
        pipeline_path.write_text(pipeline_code, encoding="utf-8")
        files.append(pipeline_path)

        # 2. Generate sensor config Python module
        config_code = self._generate_sensor_config_module(sensors, data)
        config_path = self.project_root / "src" / "perception" / "sensor_config.py"
        config_path.write_text(config_code, encoding="utf-8")
        files.append(config_path)

        # 3. Generate __init__.py
        init_path = self.project_root / "src" / "perception" / "__init__.py"
        init_path.write_text(self._TEMPLATE_PERCEPTION_INIT, encoding="utf-8")
        files.append(init_path)

        self._generated.extend(files)
        self._print_summary(files, "Sensor Config → Perception Pipeline")
        return files

    def _generate_perception_pipeline(self, sensors: List[SensorConfig], config: dict) -> str:
        """Generate the perception pipeline code."""
        imports = [
            "import threading",
            "import time",
            "from dataclasses import dataclass, field",
            "from typing import Any, Dict, List, Optional, Tuple",
            "",
            "import numpy as np",
            "from qoobot_sdk.perception import Camera, LiDAR, IMU",
            "from qoobot_sdk.communication import Publisher, Subscriber",
            "from qoobot_sdk.logging import get_logger",
        ]

        sensor_inits = []
        sensor_reads = []
        publishers = []

        for s in sensors:
            var_name = s.name.replace("-", "_").replace(" ", "_")
            if s.sensor_type in (SensorType.CAMERA_RGB, SensorType.CAMERA_DEPTH, SensorType.CAMERA_RGBD):
                sensor_inits.append(f"        self.{var_name} = Camera(\"{s.topic}\")")
                sensor_reads.append(f"        image_{var_name} = self.{var_name}.capture()")
                publishers.append(f"        self.pub_{var_name} = Publisher(\"{s.topic}/processed\", queue_size=1)")
            elif s.sensor_type in (SensorType.LIDAR_3D, SensorType.LIDAR_2D):
                sensor_inits.append(f"        self.{var_name} = LiDAR(\"{s.topic}\")")
                sensor_reads.append(f"        points_{var_name} = self.{var_name}.scan()")
                publishers.append(f"        self.pub_{var_name} = Publisher(\"{s.topic}/processed\", queue_size=1)")
            elif s.sensor_type == SensorType.IMU:
                sensor_inits.append(f"        self.{var_name} = IMU(\"{s.topic}\")")
                sensor_reads.append(f"        imu_{var_name} = self.{var_name}.read()")
                publishers.append(f"        self.pub_{var_name} = Publisher(\"{s.topic}/processed\", queue_size=1)")

        pipeline_name = config.get("name", "perception_pipeline")

        template = """# Auto-generated perception pipeline from sensor config
# Source: {{ config_path }}
# Generated by qoodev CodeGenerator

{{ imports | join('\\n') }}


@dataclass
class PerceptionFrame:
    \"\"\"Single perception frame containing all sensor data.\"\"\"
    timestamp: float = 0.0
    frame_id: int = 0
    {% for s in sensors %}
    {{ s.name }}: Any = None
    {% endfor %}


class {{ pipeline_name | capitalize }}:
    \"\"\"Perception pipeline for {{ pipeline_name }}.
    
    Processes data from {{ sensors | length }} sensor(s) at configurable frequency.
    \"\"\"

    def __init__(self, frequency_hz: float = 30.0):
        self.logger = get_logger(__name__)
        self.frequency_hz = frequency_hz
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._frame_id = 0

        # Initialize sensors
{{ sensor_inits | join('\\n') }}

        # Initialize publishers
{{ publishers | join('\\n') }}

        # Callbacks
        self._callbacks: List[callable] = []

    def start(self) -> None:
        \"\"\"Start the perception pipeline.\"\"\"
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        self.logger.info(f\"Perception pipeline started at {self.frequency_hz} Hz\")

    def stop(self) -> None:
        \"\"\"Stop the perception pipeline.\"\"\"
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        self.logger.info(\"Perception pipeline stopped\")

    def add_callback(self, callback: callable) -> None:
        \"\"\"Add a callback for each perception frame.\"\"\"
        self._callbacks.append(callback)

    def _run_loop(self) -> None:
        \"\"\"Main perception loop.\"\"\"
        period = 1.0 / self.frequency_hz

        while self._running:
            t_start = time.perf_counter()

            # Capture all sensors
            frame = PerceptionFrame(
                timestamp=time.time(),
                frame_id=self._frame_id,
            )
{{ sensor_reads | join('\\n') }}

            # Assign sensor data to frame
            {% for s in sensors %}
            frame.{{ s.name }} = {{ s.name }}
            {% endfor %}

            # Invoke callbacks
            for cb in self._callbacks:
                try:
                    cb(frame)
                except Exception as e:
                    self.logger.error(f\"Callback error: {e}\")

            self._frame_id += 1

            # Maintain frequency
            elapsed = time.perf_counter() - t_start
            sleep_time = period - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    def get_latest_frame(self) -> Optional[PerceptionFrame]:
        \"\"\"Get the most recent perception frame (non-blocking).\"\"\"
        # For simplicity, return None — implement buffer in production
        return None
"""

        return _jinja.from_string(template).render(
            config_path="sensors.yaml",
            imports=imports,
            sensors=[{"name": s.name.replace("-", "_").replace(" ", "_")} for s in sensors],
            pipeline_name=pipeline_name,
            sensor_inits=sensor_inits,
            sensor_reads=sensor_reads,
            publishers=publishers,
        )

    def _generate_sensor_config_module(self, sensors: List[SensorConfig], config: dict) -> str:
        """Generate sensor configuration module."""
        sensor_defs = []
        for s in sensors:
            sensor_defs.append(f"""    SensorConfig(
        name="{s.name}",
        sensor_type=SensorType.{s.sensor_type.value.upper()},
        topic="{s.topic}",
        frame_id="{s.frame_id}",
        frequency_hz={s.frequency_hz},
        resolution={s.resolution},
        params={s.params},
    ),""")

        template = """# Auto-generated sensor configuration
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class SensorType(Enum):
    CAMERA_RGB = "camera_rgb"
    CAMERA_DEPTH = "camera_depth"
    CAMERA_RGBD = "camera_rgbd"
    LIDAR_3D = "lidar_3d"
    LIDAR_2D = "lidar_2d"
    IMU = "imu"
    MICROPHONE = "microphone"
    FORCE_TORQUE = "force_torque"
    TOUCH = "touch"
    GPS = "gps"


@dataclass
class SensorConfig:
    name: str
    sensor_type: SensorType
    topic: str = ""
    frame_id: str = ""
    frequency_hz: float = 30.0
    resolution: Optional[Tuple[int, int]] = None
    params: Dict[str, Any] = field(default_factory=dict)


# Sensor configurations
SENSORS = [
{{ sensor_defs | join('\\n') }}
]


def get_sensor(name: str) -> Optional[SensorConfig]:
    \"\"\"Get a sensor by name.\"\"\"
    for s in SENSORS:
        if s.name == name:
            return s
    return None


def get_sensors_by_type(sensor_type: SensorType) -> List[SensorConfig]:
    \"\"\"Get all sensors of a given type.\"\"\"
    return [s for s in SENSORS if s.sensor_type == sensor_type]
"""

        return _jinja.from_string(template).render(sensor_defs=sensor_defs)

    _TEMPLATE_PERCEPTION_INIT = '''"""Perception pipeline — auto-generated by qoodev CodeGenerator."""

from .pipeline import {{ pipeline_name | capitalize }}, PerceptionFrame
from .sensor_config import SENSORS, SensorConfig, SensorType, get_sensor, get_sensors_by_type

__all__ = [
    "{{ pipeline_name | capitalize }}",
    "PerceptionFrame",
    "SENSORS",
    "SensorConfig",
    "SensorType",
    "get_sensor",
    "get_sensors_by_type",
]
'''

    # ── Behavior Tree → Executable Skill ───────────────────────────────────

    def from_behavior_tree(self, tree_path: str) -> List[Path]:
        """Generate executable skill code from a behavior tree definition.

        Args:
            tree_path: Path to behavior tree JSON file.

        Returns:
            List of generated file paths.
        """
        tree_file = self.project_root / tree_path
        if not tree_file.exists():
            raise FileNotFoundError(f"Behavior tree not found: {tree_file}")

        raw = tree_file.read_text(encoding="utf-8")
        tree_data = json.loads(raw)

        root_node = self._parse_bt_node(tree_data.get("root", tree_data))
        skill_name = tree_data.get("name", "generated_skill")

        files: List[Path] = []

        # 1. Generate skill Python module
        skill_code = self._generate_skill_from_bt(root_node, skill_name)
        skill_dir = self.project_root / "src" / skill_name
        skill_dir.mkdir(parents=True, exist_ok=True)
        skill_path = skill_dir / "skill.py"
        skill_path.write_text(skill_code, encoding="utf-8")
        files.append(skill_path)

        # 2. Generate __init__.py
        init_path = skill_dir / "__init__.py"
        init_path.write_text(f'"""Auto-generated skill: {skill_name}"""\n\nfrom .skill import {skill_name.capitalize()}Skill\n', encoding="utf-8")
        files.append(init_path)

        self._generated.extend(files)
        self._print_summary(files, "Behavior Tree → Skill Code")
        return files

    def _parse_bt_node(self, data: dict) -> BehaviorTreeNode:
        """Recursively parse a behavior tree node from JSON."""
        children = [self._parse_bt_node(c) for c in data.get("children", [])]
        return BehaviorTreeNode(
            id=data.get("id", ""),
            node_type=BehaviorTreeNodeType(data.get("type", "action")),
            name=data.get("name", data.get("id", "")),
            children=children,
            params=data.get("params", {}),
            condition=data.get("condition", ""),
            action=data.get("action", ""),
        )

    def _generate_skill_from_bt(self, root: BehaviorTreeNode, skill_name: str) -> str:
        """Generate Python skill code from behavior tree."""
        method_name = skill_name.replace("-", "_").replace(" ", "_")
        class_name = f"{method_name.capitalize()}Skill"

        # Generate node methods
        node_methods = self._generate_node_methods(root)

        template = '''"""Auto-generated skill from behavior tree.
Source: {{ tree_path }}
Generated by qoodev CodeGenerator
"""

import time
from enum import Enum
from typing import Any, Dict, Optional

from qoobot_sdk.skill import QooSkill
from qoobot_sdk.logging import get_logger


class BTStatus(Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    RUNNING = "running"


class {{ class_name }}(QooSkill):
    \"\"\"Behavior tree skill: {{ skill_name }}\"\"\"

    def __init__(self):
        super().__init__(
            name="{{ skill_name }}",
            version="0.1.0",
        )
        self.logger = get_logger(__name__)
        self._node_status: Dict[str, BTStatus] = {}

    def setup(self) -> None:
        \"\"\"Initialize skill.\"\"\"
        self.logger.info(f"{{ skill_name }} skill initialized")

    def run(self) -> None:
        \"\"\"Main skill loop — execute behavior tree.\"\"\"
        self.logger.info(f"{{ skill_name }} skill running")

        while self.running:
            status = self._tick_{{ root_id }}()
            if status != BTStatus.RUNNING:
                self.logger.info(f"Behavior tree completed: {status.value}")
            self.sleep(0.01)

    def cleanup(self) -> None:
        \"\"\"Cleanup resources.\"\"\"
        self.logger.info(f"{{ skill_name }} skill stopped")

    # ── Behavior Tree Node Methods ──

{{ node_methods }}
'''

        return _jinja.from_string(template).render(
            tree_path="behavior_tree.json",
            skill_name=skill_name,
            class_name=class_name,
            root_id=root.id,
            node_methods=node_methods,
        )

    def _generate_node_methods(self, node: BehaviorTreeNode, depth: int = 0) -> str:
        """Recursively generate methods for behavior tree nodes."""
        lines = []
        indent = "    "

        if node.node_type == BehaviorTreeNodeType.SEQUENCE:
            child_calls = "\n".join(
                f"{indent}        status = self._tick_{child.id}()\n"
                f"{indent}        if status != BTStatus.SUCCESS:\n"
                f"{indent}            return status"
                for child in node.children
            )
            lines.append(f"""{indent}def _tick_{node.id}(self) -> BTStatus:
{indent}    \"\"\"Sequence node: {node.name}\"\"\"
{child_calls}
{indent}    return BTStatus.SUCCESS
""")
        elif node.node_type == BehaviorTreeNodeType.SELECTOR:
            child_calls = "\n".join(
                f"{indent}        status = self._tick_{child.id}()\n"
                f"{indent}        if status != BTStatus.FAILURE:\n"
                f"{indent}            return status"
                for child in node.children
            )
            lines.append(f"""{indent}def _tick_{node.id}(self) -> BTStatus:
{indent}    \"\"\"Selector node: {node.name}\"\"\"
{child_calls}
{indent}    return BTStatus.FAILURE
""")
        elif node.node_type == BehaviorTreeNodeType.PARALLEL:
            child_calls = "\n".join(
                f"{indent}        self._tick_{child.id}()"
                for child in node.children
            )
            lines.append(f"""{indent}def _tick_{node.id}(self) -> BTStatus:
{indent}    \"\"\"Parallel node: {node.name}\"\"\"
{child_calls}
{indent}    return BTStatus.SUCCESS
""")
        elif node.node_type == BehaviorTreeNodeType.CONDITION:
            condition = node.condition or "True"
            lines.append(f"""{indent}def _tick_{node.id}(self) -> BTStatus:
{indent}    \"\"\"Condition node: {node.name}\"\"\"
{indent}    if {condition}:
{indent}        return BTStatus.SUCCESS
{indent}    return BTStatus.FAILURE
""")
        elif node.node_type == BehaviorTreeNodeType.ACTION:
            action = node.action or "pass"
            lines.append(f"""{indent}def _tick_{node.id}(self) -> BTStatus:
{indent}    \"\"\"Action node: {node.name}\"\"\"
{indent}    {action}
{indent}    return BTStatus.SUCCESS
""")
        elif node.node_type == BehaviorTreeNodeType.DECORATOR:
            child_call = f"{indent}    return self._tick_{node.children[0].id}()" if node.children else f"{indent}    return BTStatus.SUCCESS"
            lines.append(f"""{indent}def _tick_{node.id}(self) -> BTStatus:
{indent}    \"\"\"Decorator node: {node.name}\"\"\"
{child_call}
""")

        # Recurse into children
        for child in node.children:
            lines.append(self._generate_node_methods(child, depth + 1))

        return "\n".join(lines)

    # ── Model Definition → Training + Inference Wrapper ─────────────────────

    def from_model_def(self, model_path: str) -> List[Path]:
        """Generate training + inference wrapper from model definition.

        Args:
            model_path: Path to model definition YAML.

        Returns:
            List of generated file paths.
        """
        model_file = self.project_root / model_path
        if not model_file.exists():
            raise FileNotFoundError(f"Model definition not found: {model_file}")

        raw = model_file.read_text(encoding="utf-8")
        data = yaml.safe_load(raw)

        model = ModelDef(
            name=data.get("name", "model"),
            framework=data.get("framework", "pytorch"),
            task=data.get("task", "classification"),
            input_shape=data.get("input_shape", [1, 3, 224, 224]),
            output_shape=data.get("output_shape", [1, 1000]),
            precision=data.get("precision", "fp32"),
            backend=data.get("backend", "auto"),
        )

        files: List[Path] = []

        # 1. Model architecture
        arch_code = self._generate_model_arch(model)
        model_dir = self.project_root / "src" / model.name
        model_dir.mkdir(parents=True, exist_ok=True)
        arch_path = model_dir / "model.py"
        arch_path.write_text(arch_code, encoding="utf-8")
        files.append(arch_path)

        # 2. Training script
        train_code = self._generate_train_script(model)
        train_path = model_dir / "train.py"
        train_path.write_text(train_code, encoding="utf-8")
        files.append(train_path)

        # 3. Inference wrapper
        infer_code = self._generate_inference_wrapper(model)
        infer_path = model_dir / "inference.py"
        infer_path.write_text(infer_code, encoding="utf-8")
        files.append(infer_path)

        # 4. __init__.py
        init_path = model_dir / "__init__.py"
        init_path.write_text(f'"""Auto-generated model: {model.name}"""\n\nfrom .model import {model.name.capitalize()}\nfrom .inference import InferenceWrapper\n', encoding="utf-8")
        files.append(init_path)

        self._generated.extend(files)
        self._print_summary(files, "Model Definition → Training + Inference")
        return files

    def _generate_model_arch(self, model: ModelDef) -> str:
        """Generate model architecture code."""
        template = '''"""Auto-generated model architecture.
Model: {{ name }} | Task: {{ task }} | Framework: {{ framework }}
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


class {{ class_name }}(nn.Module):
    \"\"\"{{ name }} — {{ task }} model.

    Input: {{ input_shape }}
    Output: {{ output_shape }}
    Precision: {{ precision }}
    \"\"\"

    def __init__(self, num_classes: int = {{ num_classes }}):
        super().__init__()

        # Backbone
        self.backbone = nn.Sequential(
            nn.Conv2d({{ in_channels }}, 64, kernel_size=7, stride=2, padding=3, bias=False),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=3, stride=2, padding=1),

            nn.Conv2d(64, 128, kernel_size=3, stride=2, padding=1, bias=False),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),

            nn.Conv2d(128, 256, kernel_size=3, stride=2, padding=1, bias=False),
            nn.BatchNorm2d(256),
            nn.ReLU(inplace=True),

            nn.Conv2d(256, 512, kernel_size=3, stride=2, padding=1, bias=False),
            nn.BatchNorm2d(512),
            nn.ReLU(inplace=True),

            nn.AdaptiveAvgPool2d((1, 1)),
        )

        # Head
        self.head = nn.Sequential(
            nn.Flatten(),
            nn.Linear(512, 256),
            nn.ReLU(inplace=True),
            nn.Dropout(0.2),
            nn.Linear(256, num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        \"\"\"Forward pass.

        Args:
            x: Input tensor of shape {{ input_shape }}

        Returns:
            Output tensor of shape (B, num_classes)
        \"\"\"
        features = self.backbone(x)
        output = self.head(features)
        return output


def create_model(num_classes: int = {{ num_classes }}, pretrained: bool = False) -> {{ class_name }}:
    \"\"\"Factory function for {{ name }} model.\"\"\"
    model = {{ class_name }}(num_classes=num_classes)
    if pretrained:
        # TODO: Load pretrained weights
        pass
    return model
'''

        in_channels = model.input_shape[1] if len(model.input_shape) > 1 else 3
        num_classes = model.output_shape[-1] if model.output_shape else 1000

        return _jinja.from_string(template).render(
            name=model.name,
            class_name=model.name.capitalize(),
            task=model.task,
            framework=model.framework,
            input_shape=model.input_shape,
            output_shape=model.output_shape,
            precision=model.precision,
            in_channels=in_channels,
            num_classes=num_classes,
        )

    def _generate_train_script(self, model: ModelDef) -> str:
        """Generate training script."""
        template = '''"""Auto-generated training script for {{ name }}."""

import argparse
from pathlib import Path

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from torch.cuda.amp import GradScaler, autocast

from .model import create_model


def train(
    data_dir: str,
    output_dir: str = "./output",
    batch_size: int = 32,
    epochs: int = 100,
    lr: float = 0.001,
    num_classes: int = {{ num_classes }},
    device: str = "cuda",
    use_amp: bool = True,
) -> None:
    \"\"\"Train the {{ name }} model.

    Args:
        data_dir: Path to training data directory
        output_dir: Path to save checkpoints
        batch_size: Training batch size
        epochs: Number of training epochs
        lr: Learning rate
        num_classes: Number of output classes
        device: Device to train on (cuda/cpu)
        use_amp: Use automatic mixed precision
    \"\"\"
    device = torch.device(device if torch.cuda.is_available() else "cpu")
    print(f"Training on: {device}")

    # Create model
    model = create_model(num_classes=num_classes)
    model = model.to(device)

    # Loss, optimizer, scheduler
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
    scaler = GradScaler(enabled=use_amp)

    # TODO: Load your dataset here
    # train_loader = DataLoader(YourDataset(data_dir, train=True), batch_size=batch_size, shuffle=True)
    # val_loader = DataLoader(YourDataset(data_dir, train=False), batch_size=batch_size)

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    best_acc = 0.0

    for epoch in range(epochs):
        model.train()
        train_loss = 0.0

        # Training loop
        # for batch_idx, (data, target) in enumerate(train_loader):
        #     data, target = data.to(device), target.to(device)
        #
        #     optimizer.zero_grad()
        #
        #     with autocast(enabled=use_amp):
        #         output = model(data)
        #         loss = criterion(output, target)
        #
        #     scaler.scale(loss).backward()
        #     scaler.step(optimizer)
        #     scaler.update()
        #
        #     train_loss += loss.item()

        scheduler.step()

        # Save checkpoint
        if (epoch + 1) % 10 == 0:
            checkpoint_path = output_path / f"checkpoint_epoch_{epoch+1}.pth"
            torch.save({
                "epoch": epoch + 1,
                "model_state_dict": model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "scheduler_state_dict": scheduler.state_dict(),
            }, checkpoint_path)
            print(f"Saved checkpoint: {checkpoint_path}")

    # Save final model
    final_path = output_path / "model_final.pth"
    torch.save(model.state_dict(), final_path)
    print(f"Training complete! Model saved to: {final_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train {{ name }}")
    parser.add_argument("--data-dir", type=str, required=True, help="Training data directory")
    parser.add_argument("--output-dir", type=str, default="./output", help="Output directory")
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--lr", type=float, default=0.001)
    parser.add_argument("--num-classes", type=int, default={{ num_classes }})
    parser.add_argument("--device", type=str, default="cuda")
    parser.add_argument("--no-amp", action="store_true", help="Disable AMP")
    args = parser.parse_args()

    train(
        data_dir=args.data_dir,
        output_dir=args.output_dir,
        batch_size=args.batch_size,
        epochs=args.epochs,
        lr=args.lr,
        num_classes=args.num_classes,
        device=args.device,
        use_amp=not args.no_amp,
    )
'''

        num_classes = model.output_shape[-1] if model.output_shape else 1000

        return _jinja.from_string(template).render(
            name=model.name,
            num_classes=num_classes,
        )

    def _generate_inference_wrapper(self, model: ModelDef) -> str:
        """Generate inference wrapper code."""
        template = '''"""Auto-generated inference wrapper for {{ name }}."""

from pathlib import Path
from typing import Optional, Tuple

import numpy as np
import torch

from .model import create_model


class InferenceWrapper:
    \"\"\"Inference wrapper for {{ name }} model.

    Supports:
    - PyTorch native inference
    - qoocore .qoomodel inference (via qoocore compiler bridge)
    - Batch inference
    - Performance timing
    \"\"\"

    def __init__(
        self,
        model_path: Optional[str] = None,
        num_classes: int = {{ num_classes }},
        device: str = "cuda",
        precision: str = "{{ precision }}",
    ):
        self.device = torch.device(device if torch.cuda.is_available() else "cpu")
        self.num_classes = num_classes
        self.precision = precision

        # Load model
        self.model = create_model(num_classes=num_classes)
        if model_path:
            self.model.load_state_dict(torch.load(model_path, map_location=self.device))
        self.model = self.model.to(self.device)
        self.model.eval()

        # Precision
        if precision == "fp16" and self.device.type == "cuda":
            self.model = self.model.half()

    @torch.no_grad()
    def infer(self, input_tensor: torch.Tensor) -> torch.Tensor:
        \"\"\"Single inference.

        Args:
            input_tensor: Input tensor of shape {{ input_shape }}

        Returns:
            Output tensor
        \"\"\"
        input_tensor = input_tensor.to(self.device)
        if self.precision == "fp16" and self.device.type == "cuda":
            input_tensor = input_tensor.half()

        output = self.model(input_tensor)
        return output.cpu()

    @torch.no_grad()
    def infer_batch(self, input_batch: torch.Tensor) -> torch.Tensor:
        \"\"\"Batch inference.

        Args:
            input_batch: Input tensor of shape (B, C, H, W)

        Returns:
            Output tensor of shape (B, num_classes)
        \"\"\"
        input_batch = input_batch.to(self.device)
        if self.precision == "fp16" and self.device.type == "cuda":
            input_batch = input_batch.half()

        output = self.model(input_batch)
        return output.cpu()

    def preprocess(self, image: np.ndarray) -> torch.Tensor:
        \"\"\"Preprocess a numpy image for inference.

        Args:
            image: numpy array of shape (H, W, C) in range [0, 255]

        Returns:
            Preprocessed tensor of shape (1, C, H, W)
        \"\"\"
        import torchvision.transforms as T

        transform = T.Compose([
            T.ToPILImage(),
            T.Resize(({{ input_h }}, {{ input_w }})),
            T.ToTensor(),
            T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])

        tensor = transform(image).unsqueeze(0)
        return tensor

    def compile_to_qoomodel(self, output_path: str, sample_input: Optional[torch.Tensor] = None) -> Path:
        \"\"\"Compile model to .qoomodel format using qoocore compiler bridge.

        Args:
            output_path: Output .qoomodel path
            sample_input: Sample input for tracing

        Returns:
            Path to compiled .qoomodel
        \"\"\"
        from cli.compiler import CompilerBridge

        if sample_input is None:
            sample_input = torch.randn({{ input_shape }})

        bridge = CompilerBridge()
        result = bridge.compile(
            model=self.model,
            sample_input=sample_input,
            output_path=output_path,
            precision=self.precision,
        )
        return Path(output_path)
'''

        input_h = model.input_shape[2] if len(model.input_shape) > 2 else 224
        input_w = model.input_shape[3] if len(model.input_shape) > 3 else 224
        num_classes = model.output_shape[-1] if model.output_shape else 1000

        return _jinja.from_string(template).render(
            name=model.name,
            input_shape=model.input_shape,
            input_h=input_h,
            input_w=input_w,
            num_classes=num_classes,
            precision=model.precision,
        )

    # ── Service Spec → Service Skeleton ────────────────────────────────────

    def from_service_spec(self, spec_path: str) -> List[Path]:
        """Generate service skeleton from service specification.

        Args:
            spec_path: Path to service specification YAML.

        Returns:
            List of generated file paths.
        """
        spec_file = self.project_root / spec_path
        if not spec_file.exists():
            raise FileNotFoundError(f"Service spec not found: {spec_file}")

        raw = spec_file.read_text(encoding="utf-8")
        data = yaml.safe_load(raw)

        spec = ServiceSpec(
            name=data.get("name", "service"),
            language=CodeLanguage(data.get("language", "python")),
            frequency_hz=data.get("frequency_hz", 100.0),
            inputs=data.get("inputs", []),
            outputs=data.get("outputs", []),
            dependencies=data.get("dependencies", []),
            config_params=data.get("config_params", {}),
        )

        files: List[Path] = []

        if spec.language == CodeLanguage.PYTHON:
            files.extend(self._generate_python_service(spec))
        elif spec.language == CodeLanguage.CPP:
            files.extend(self._generate_cpp_service(spec))

        self._generated.extend(files)
        self._print_summary(files, "Service Spec → Service Skeleton")
        return files

    def _generate_python_service(self, spec: ServiceSpec) -> List[Path]:
        """Generate Python service skeleton."""
        service_dir = self.project_root / "src" / spec.name
        service_dir.mkdir(parents=True, exist_ok=True)

        files: List[Path] = []

        # Main service file
        service_code = self._render_python_service(spec)
        svc_path = service_dir / f"{spec.name}.py"
        svc_path.write_text(service_code, encoding="utf-8")
        files.append(svc_path)

        # __init__.py
        init_path = service_dir / "__init__.py"
        init_path.write_text(f'"""Auto-generated service: {spec.name}"""\n\nfrom .{spec.name} import {spec.name.capitalize()}Service\n', encoding="utf-8")
        files.append(init_path)

        # config.yaml
        config_path = service_dir / "config.yaml"
        config_content = yaml.dump({
            "name": spec.name,
            "frequency_hz": spec.frequency_hz,
            "inputs": spec.inputs,
            "outputs": spec.outputs,
            "params": spec.config_params,
        }, default_flow_style=False)
        config_path.write_text(config_content, encoding="utf-8")
        files.append(config_path)

        return files

    def _render_python_service(self, spec: ServiceSpec) -> str:
        """Render Python service template."""
        input_inits = "\n".join(
            f"        self.{inp}_sub = Subscriber(\"/qoobot/{inp}\")"
            for inp in spec.inputs
        )
        output_inits = "\n".join(
            f"        self.{out}_pub = Publisher(\"/qoobot/{out}\")"
            for out in spec.outputs
        )

        template = '''"""Auto-generated service: {{ name }} ({{ frequency_hz }} Hz)"""

import threading
import time
from typing import Any, Dict, Optional

from qoobot_sdk.skill import QooSkill
from qoobot_sdk.communication import Publisher, Subscriber
from qoobot_sdk.logging import get_logger


class {{ class_name }}Service(QooSkill):
    \"\"\"{{ name }} system service.

    Frequency: {{ frequency_hz }} Hz
    {% if inputs %}Inputs: {{ inputs | join(', ') }}{% endif %}
    {% if outputs %}Outputs: {{ outputs | join(', ') }}{% endif %}
    \"\"\"

    def __init__(self):
        super().__init__(
            name="{{ name }}",
            version="0.1.0",
        )
        self.logger = get_logger(__name__)
        self._running = False

    def setup(self) -> None:
        \"\"\"Initialize service resources.\"\"\"
        # Input subscribers
{{ input_inits }}

        # Output publishers
{{ output_inits }}

        self.logger.info(f"{{ name }} service initialized at {{ frequency_hz }} Hz")

    def run(self) -> None:
        \"\"\"Main service loop.\"\"\"
        self._running = True
        period = 1.0 / {{ frequency_hz }}

        self.logger.info(f"{{ name }} service started")

        while self._running:
            t_start = time.perf_counter()

            # TODO: Implement service logic
            # 1. Read inputs
            # 2. Process
            # 3. Publish outputs

            elapsed = time.perf_counter() - t_start
            sleep_time = period - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    def cleanup(self) -> None:
        \"\"\"Cleanup service resources.\"\"\"
        self._running = False
        self.logger.info(f"{{ name }} service stopped")

    def get_config(self) -> Dict[str, Any]:
        \"\"\"Get service configuration.\"\"\"
        return {
            "name": "{{ name }}",
            "frequency_hz": {{ frequency_hz }},
            "inputs": {{ inputs }},
            "outputs": {{ outputs }},
        }
'''

        return _jinja.from_string(template).render(
            name=spec.name,
            class_name=spec.name.capitalize(),
            frequency_hz=spec.frequency_hz,
            inputs=spec.inputs,
            outputs=spec.outputs,
            input_inits=input_inits,
            output_inits=output_inits,
        )

    def _generate_cpp_service(self, spec: ServiceSpec) -> List[Path]:
        """Generate C++ service skeleton."""
        service_dir = self.project_root / "src" / spec.name
        service_dir.mkdir(parents=True, exist_ok=True)

        files: List[Path] = []

        # CMakeLists.txt
        cmake_code = self._render_cmake(spec)
        cmake_path = service_dir / "CMakeLists.txt"
        cmake_path.write_text(cmake_code, encoding="utf-8")
        files.append(cmake_path)

        # Header file
        header_code = self._render_cpp_header(spec)
        header_path = service_dir / f"{spec.name}.h"
        header_path.write_text(header_code, encoding="utf-8")
        files.append(header_path)

        # Source file
        source_code = self._render_cpp_source(spec)
        source_path = service_dir / f"{spec.name}.cpp"
        source_path.write_text(source_code, encoding="utf-8")
        files.append(source_path)

        return files

    def _render_cmake(self, spec: ServiceSpec) -> str:
        template = """# Auto-generated CMakeLists.txt for {{ name }} service
cmake_minimum_required(VERSION 3.20)
project({{ name }} VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(qoobot REQUIRED)
{% for dep in dependencies %}
find_package({{ dep }} REQUIRED)
{% endfor %}

add_library({{ name }}
    {{ name }}.cpp
    {{ name }}.h
)

target_include_directories({{ name }} PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}>
    $<INSTALL_INTERFACE:include>
)

target_link_libraries({{ name }} PUBLIC
    qoobot::qoobot
{% for dep in dependencies %}
    {{ dep }}::{{ dep }}
{% endfor %}
)

target_compile_options({{ name }} PRIVATE
    -Wall -Wextra -Wpedantic
    -Wno-unused-parameter
)
"""
        return _jinja.from_string(template).render(
            name=spec.name,
            dependencies=spec.dependencies,
        )

    def _render_cpp_header(self, spec: ServiceSpec) -> str:
        template = """// Auto-generated header for {{ name }} service
#pragma once

#include <qoobot/qoobot.h>
#include <memory>
#include <chrono>
#include <thread>
#include <atomic>

namespace qoobot {

class {{ class_name }}Service : public QooService {
public:
    {{ class_name }}Service();
    ~{{ class_name }}Service() override;

    bool init() override;
    void run() override;
    void cleanup() override;

    double frequency() const { return {{ frequency_hz }}; }

private:
    void processInputs();
    void publishOutputs();

    std::atomic<bool> running_{false};
    std::unique_ptr<std::thread> worker_thread_;

{% for inp in inputs %}
    std::unique_ptr<Subscriber> {{ inp }}_sub_;
{% endfor %}
{% for out in outputs %}
    std::unique_ptr<Publisher> {{ out }}_pub_;
{% endfor %}
};

} // namespace qoobot
"""
        return _jinja.from_string(template).render(
            name=spec.name,
            class_name=spec.name.capitalize(),
            frequency_hz=spec.frequency_hz,
            inputs=spec.inputs,
            outputs=spec.outputs,
        )

    def _render_cpp_source(self, spec: ServiceSpec) -> str:
        template = """// Auto-generated source for {{ name }} service

#include "{{ name }}.h"

#include <qoobot/logging.h>

using namespace std::chrono_literals;

namespace qoobot {

{{ class_name }}Service::{{ class_name }}Service()
    : QooService("{{ name }}") {}

{{ class_name }}Service::~{{ class_name }}Service() {
    cleanup();
}

bool {{ class_name }}Service::init() {
    QOOBOT_LOG_INFO("Initializing {{ name }} service");

{% for inp in inputs %}
    {{ inp }}_sub_ = std::make_unique<Subscriber>("/qoobot/{{ inp }}");
{% endfor %}
{% for out in outputs %}
    {{ out }}_pub_ = std::make_unique<Publisher>("/qoobot/{{ out }}");
{% endfor %}

    QOOBOT_LOG_INFO("{{ name }} service initialized at {} Hz", frequency());
    return true;
}

void {{ class_name }}Service::run() {
    QOOBOT_LOG_INFO("{{ name }} service started");

    running_ = true;
    worker_thread_ = std::make_unique<std::thread>([this]() {
        auto period = std::chrono::microseconds(
            static_cast<int>(1e6 / frequency())
        );

        while (running_) {
            auto t_start = std::chrono::high_resolution_clock::now();

            processInputs();
            // TODO: Implement service logic
            publishOutputs();

            auto elapsed = std::chrono::high_resolution_clock::now() - t_start;
            if (elapsed < period) {
                std::this_thread::sleep_for(period - elapsed);
            }
        }
    });

    worker_thread_->join();
}

void {{ class_name }}Service::processInputs() {
{% if inputs %}
    // Read from subscribers
{% else %}
    // No inputs configured
{% endif %}
}

void {{ class_name }}Service::publishOutputs() {
{% if outputs %}
    // Publish to output topics
{% else %}
    // No outputs configured
{% endif %}
}

void {{ class_name }}Service::cleanup() {
    running_ = false;
    if (worker_thread_ && worker_thread_->joinable()) {
        worker_thread_->join();
    }
    QOOBOT_LOG_INFO("{{ name }} service stopped");
}

} // namespace qoobot

REGISTER_QOO_SERVICE(qoobot::{{ class_name }}Service)
"""
        return _jinja.from_string(template).render(
            name=spec.name,
            class_name=spec.name.capitalize(),
            frequency_hz=spec.frequency_hz,
            inputs=spec.inputs,
            outputs=spec.outputs,
        )

    # ── Helpers ─────────────────────────────────────────────────────────────

    def _print_summary(self, files: List[Path], title: str) -> None:
        """Print generation summary."""
        tree = Tree(f"[bold green]✓[/bold green] {title}")
        for f in files:
            tree.add(f"[dim]{f.relative_to(self.project_root)}[/dim]")
        console.print(Panel(tree, border_style="green"))
