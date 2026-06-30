"""
Domain Randomization — v1.6+

Sim2Real transfer via domain randomization for QooBot simulation.
Randomizes visual and physical simulation parameters to train
policies that generalize to the real world.

Features:
- Lighting randomization (color, intensity, direction, shadows)
- Texture randomization (color, roughness, metallic, patterns)
- Physics randomization (mass, friction, damping, inertia)
- Sensor noise injection (camera, LiDAR, IMU)
- Scene randomization (object positions, distractors, backgrounds)
- Curriculum learning (progressive difficulty)
- Domain parameter scheduling

Usage:
    from cli.domain_randomization import DomainRandomizer

    dr = DomainRandomizer(sim_backend)
    dr.randomize_lighting()
    dr.randomize_textures()
    dr.randomize_physics()
    dr.step()
"""

from __future__ import annotations

import json
import random
import time
from collections import defaultdict
from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np
import yaml

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree
from rich.live import Live
from rich.text import Text

console = Console()


# ============================================================================
# Data Models
# ============================================================================

class RandomizationCategory(Enum):
    LIGHTING = "lighting"
    TEXTURE = "texture"
    PHYSICS = "physics"
    SENSOR_NOISE = "sensor_noise"
    SCENE = "scene"
    CAMERA = "camera"


class DistributionType(Enum):
    UNIFORM = "uniform"
    NORMAL = "normal"
    LOG_NORMAL = "log_normal"
    CHOICE = "choice"
    BETA = "beta"


class DifficultyLevel(Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    EXTREME = "extreme"


@dataclass
class DomainParameter:
    """A single domain randomization parameter."""
    name: str
    category: RandomizationCategory
    distribution: DistributionType = DistributionType.UNIFORM
    min_value: float = 0.0
    max_value: float = 1.0
    mean: float = 0.0
    std: float = 1.0
    choices: List[Any] = field(default_factory=list)
    alpha: float = 2.0  # Beta distribution
    beta: float = 2.0
    current_value: float = 0.0

    def sample(self, rng: np.random.RandomState) -> float:
        """Sample a value from the parameter's distribution."""
        if self.distribution == DistributionType.UNIFORM:
            return float(rng.uniform(self.min_value, self.max_value))
        elif self.distribution == DistributionType.NORMAL:
            return float(rng.normal(self.mean, self.std))
        elif self.distribution == DistributionType.LOG_NORMAL:
            return float(rng.lognormal(self.mean, self.std))
        elif self.distribution == DistributionType.CHOICE:
            return random.choice(self.choices) if self.choices else self.min_value
        elif self.distribution == DistributionType.BETA:
            return float(rng.beta(self.alpha, self.beta) * (self.max_value - self.min_value) + self.min_value)
        return self.min_value

    def scale_for_difficulty(self, difficulty: DifficultyLevel) -> Tuple[float, float]:
        """Scale parameter range based on difficulty."""
        difficulty_scales = {
            DifficultyLevel.EASY: 0.25,
            DifficultyLevel.MEDIUM: 0.5,
            DifficultyLevel.HARD: 0.75,
            DifficultyLevel.EXTREME: 1.0,
        }
        scale = difficulty_scales.get(difficulty, 0.5)
        center = (self.min_value + self.max_value) / 2
        half_range = (self.max_value - self.min_value) / 2 * scale
        return (center - half_range, center + half_range)


@dataclass
class DomainConfig:
    """Complete domain randomization configuration."""
    name: str = "default"
    seed: int = 42
    difficulty: DifficultyLevel = DifficultyLevel.MEDIUM

    # Parameters by category
    lighting_params: List[DomainParameter] = field(default_factory=list)
    texture_params: List[DomainParameter] = field(default_factory=list)
    physics_params: List[DomainParameter] = field(default_factory=list)
    sensor_params: List[DomainParameter] = field(default_factory=list)
    scene_params: List[DomainParameter] = field(default_factory=list)
    camera_params: List[DomainParameter] = field(default_factory=list)

    # Curriculum
    curriculum_enabled: bool = False
    curriculum_episodes_per_level: int = 100

    @property
    def all_params(self) -> List[DomainParameter]:
        return (
            self.lighting_params + self.texture_params + self.physics_params +
            self.sensor_params + self.scene_params + self.camera_params
        )


@dataclass
class RandomizationState:
    """Current randomization state for a single episode."""
    episode: int = 0
    difficulty: DifficultyLevel = DifficultyLevel.MEDIUM
    param_values: Dict[str, float] = field(default_factory=dict)
    timestamp: float = 0.0


# ============================================================================
# Preset Configurations
# ============================================================================

def _create_default_lighting_params() -> List[DomainParameter]:
    """Create default lighting randomization parameters."""
    return [
        DomainParameter("light_intensity", RandomizationCategory.LIGHTING,
                         DistributionType.UNIFORM, 0.3, 3.0),
        DomainParameter("light_color_temp", RandomizationCategory.LIGHTING,
                         DistributionType.UNIFORM, 2000, 10000),
        DomainParameter("light_direction_azimuth", RandomizationCategory.LIGHTING,
                         DistributionType.UNIFORM, 0, 360),
        DomainParameter("light_direction_elevation", RandomizationCategory.LIGHTING,
                         DistributionType.UNIFORM, 10, 80),
        DomainParameter("shadow_softness", RandomizationCategory.LIGHTING,
                         DistributionType.UNIFORM, 0.0, 1.0),
        DomainParameter("ambient_occlusion", RandomizationCategory.LIGHTING,
                         DistributionType.UNIFORM, 0.0, 1.0),
        DomainParameter("num_lights", RandomizationCategory.LIGHTING,
                         DistributionType.CHOICE, choices=[1, 2, 3, 4]),
    ]


def _create_default_texture_params() -> List[DomainParameter]:
    """Create default texture randomization parameters."""
    return [
        DomainParameter("color_hue_shift", RandomizationCategory.TEXTURE,
                         DistributionType.UNIFORM, -0.1, 0.1),
        DomainParameter("color_saturation", RandomizationCategory.TEXTURE,
                         DistributionType.UNIFORM, 0.5, 2.0),
        DomainParameter("color_brightness", RandomizationCategory.TEXTURE,
                         DistributionType.UNIFORM, 0.5, 1.5),
        DomainParameter("color_contrast", RandomizationCategory.TEXTURE,
                         DistributionType.UNIFORM, 0.5, 2.0),
        DomainParameter("roughness", RandomizationCategory.TEXTURE,
                         DistributionType.UNIFORM, 0.0, 1.0),
        DomainParameter("metallic", RandomizationCategory.TEXTURE,
                         DistributionType.UNIFORM, 0.0, 1.0),
        DomainParameter("specular", RandomizationCategory.TEXTURE,
                         DistributionType.UNIFORM, 0.0, 1.0),
    ]


def _create_default_physics_params() -> List[DomainParameter]:
    """Create default physics randomization parameters."""
    return [
        DomainParameter("mass_scale", RandomizationCategory.PHYSICS,
                         DistributionType.UNIFORM, 0.8, 1.2),
        DomainParameter("friction_lateral", RandomizationCategory.PHYSICS,
                         DistributionType.UNIFORM, 0.5, 1.5),
        DomainParameter("friction_rolling", RandomizationCategory.PHYSICS,
                         DistributionType.UNIFORM, 0.001, 0.01),
        DomainParameter("joint_damping", RandomizationCategory.PHYSICS,
                         DistributionType.UNIFORM, 0.8, 1.2),
        DomainParameter("joint_stiffness", RandomizationCategory.PHYSICS,
                         DistributionType.UNIFORM, 0.8, 1.2),
        DomainParameter("gravity_z", RandomizationCategory.PHYSICS,
                         DistributionType.UNIFORM, -9.9, -9.7),
        DomainParameter("restitution", RandomizationCategory.PHYSICS,
                         DistributionType.UNIFORM, 0.0, 0.3),
        DomainParameter("wind_force_x", RandomizationCategory.PHYSICS,
                         DistributionType.NORMAL, mean=0.0, std=0.5),
        DomainParameter("wind_force_y", RandomizationCategory.PHYSICS,
                         DistributionType.NORMAL, mean=0.0, std=0.5),
    ]


def _create_default_sensor_params() -> List[DomainParameter]:
    """Create default sensor noise randomization parameters."""
    return [
        # Camera noise
        DomainParameter("camera_gaussian_noise_std", RandomizationCategory.SENSOR_NOISE,
                         DistributionType.UNIFORM, 0.0, 0.05),
        DomainParameter("camera_salt_pepper_prob", RandomizationCategory.SENSOR_NOISE,
                         DistributionType.UNIFORM, 0.0, 0.02),
        DomainParameter("camera_blur_kernel", RandomizationCategory.SENSOR_NOISE,
                         DistributionType.CHOICE, choices=[0, 1, 3, 5]),
        DomainParameter("camera_exposure", RandomizationCategory.SENSOR_NOISE,
                         DistributionType.UNIFORM, -1.0, 1.0),

        # LiDAR noise
        DomainParameter("lidar_dropout_prob", RandomizationCategory.SENSOR_NOISE,
                         DistributionType.UNIFORM, 0.0, 0.1),
        DomainParameter("lidar_gaussian_noise_std", RandomizationCategory.SENSOR_NOISE,
                         DistributionType.UNIFORM, 0.0, 0.02),

        # IMU noise
        DomainParameter("imu_accel_bias", RandomizationCategory.SENSOR_NOISE,
                         DistributionType.NORMAL, mean=0.0, std=0.1),
        DomainParameter("imu_gyro_bias", RandomizationCategory.SENSOR_NOISE,
                         DistributionType.NORMAL, mean=0.0, std=0.05),
        DomainParameter("imu_accel_noise_std", RandomizationCategory.SENSOR_NOISE,
                         DistributionType.UNIFORM, 0.0, 0.02),
        DomainParameter("imu_gyro_noise_std", RandomizationCategory.SENSOR_NOISE,
                         DistributionType.UNIFORM, 0.0, 0.01),
    ]


def _create_default_scene_params() -> List[DomainParameter]:
    """Create default scene randomization parameters."""
    return [
        DomainParameter("num_distractors", RandomizationCategory.SCENE,
                         DistributionType.CHOICE, choices=[0, 1, 2, 3, 5, 8]),
        DomainParameter("object_scale", RandomizationCategory.SCENE,
                         DistributionType.UNIFORM, 0.8, 1.2),
        DomainParameter("object_rotation_x", RandomizationCategory.SCENE,
                         DistributionType.UNIFORM, 0, 360),
        DomainParameter("object_rotation_y", RandomizationCategory.SCENE,
                         DistributionType.UNIFORM, 0, 360),
        DomainParameter("object_rotation_z", RandomizationCategory.SCENE,
                         DistributionType.UNIFORM, 0, 360),
        DomainParameter("background_id", RandomizationCategory.SCENE,
                         DistributionType.CHOICE, choices=[0, 1, 2, 3, 4, 5]),
        DomainParameter("table_height", RandomizationCategory.SCENE,
                         DistributionType.UNIFORM, 0.7, 0.9),
    ]


def _create_default_camera_params() -> List[DomainParameter]:
    """Create default camera randomization parameters."""
    return [
        DomainParameter("camera_pos_x", RandomizationCategory.CAMERA,
                         DistributionType.UNIFORM, -0.1, 0.1),
        DomainParameter("camera_pos_y", RandomizationCategory.CAMERA,
                         DistributionType.UNIFORM, -0.1, 0.1),
        DomainParameter("camera_pos_z", RandomizationCategory.CAMERA,
                         DistributionType.UNIFORM, -0.05, 0.05),
        DomainParameter("camera_roll", RandomizationCategory.CAMERA,
                         DistributionType.UNIFORM, -5, 5),
        DomainParameter("camera_pitch", RandomizationCategory.CAMERA,
                         DistributionType.UNIFORM, -5, 5),
        DomainParameter("camera_yaw", RandomizationCategory.CAMERA,
                         DistributionType.UNIFORM, -5, 5),
        DomainParameter("camera_fov", RandomizationCategory.CAMERA,
                         DistributionType.UNIFORM, 55, 75),
    ]


# ============================================================================
# Domain Randomizer
# ============================================================================

class DomainRandomizer:
    """Sim2Real transfer via domain randomization.

    Randomizes simulation parameters each episode to produce policies
    that transfer robustly to the real world.

    Features:
    - 6 randomization categories (lighting, texture, physics, sensor, scene, camera)
    - Multiple distribution types (uniform, normal, log-normal, choice, beta)
    - Curriculum learning (progressive difficulty)
    - Config import/export (YAML)
    - Seed reproducibility
    - Live randomization display
    """

    def __init__(
        self,
        sim_backend: Optional[Any] = None,
        config: Optional[DomainConfig] = None,
        seed: int = 42,
    ):
        self.sim_backend = sim_backend
        self.config = config or self._default_config()
        self.config.seed = seed
        self._rng = np.random.RandomState(seed)
        self._state = RandomizationState()
        self._history: List[RandomizationState] = []
        self._episode_count = 0

    @staticmethod
    def _default_config() -> DomainConfig:
        """Create a default domain configuration."""
        return DomainConfig(
            name="default",
            lighting_params=_create_default_lighting_params(),
            texture_params=_create_default_texture_params(),
            physics_params=_create_default_physics_params(),
            sensor_params=_create_default_sensor_params(),
            scene_params=_create_default_scene_params(),
            camera_params=_create_default_camera_params(),
        )

    # ── Configuration ──────────────────────────────────────────────────────

    @classmethod
    def from_config(cls, config_path: str) -> "DomainRandomizer":
        """Load configuration from a YAML file."""
        path = Path(config_path)
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))

        config = DomainConfig(
            name=raw.get("name", "custom"),
            seed=raw.get("seed", 42),
            difficulty=DifficultyLevel(raw.get("difficulty", "medium")),
            curriculum_enabled=raw.get("curriculum", {}).get("enabled", False),
            curriculum_episodes_per_level=raw.get("curriculum", {}).get("episodes_per_level", 100),
        )

        for cat in RandomizationCategory:
            params = raw.get("parameters", {}).get(cat.value, [])
            parsed = []
            for p in params:
                parsed.append(DomainParameter(
                    name=p["name"],
                    category=cat,
                    distribution=DistributionType(p.get("distribution", "uniform")),
                    min_value=p.get("min", 0.0),
                    max_value=p.get("max", 1.0),
                    mean=p.get("mean", 0.0),
                    std=p.get("std", 1.0),
                    choices=p.get("choices", []),
                ))
            setattr(config, f"{cat.value}_params", parsed)

        dr = cls(config=config, seed=config.seed)
        console.print(f"[green]✓[/green] Loaded domain config: [bold]{config.name}[/bold]")
        return dr

    def save_config(self, output_path: str) -> Path:
        """Save current configuration to a YAML file."""
        output = Path(output_path)

        data = {
            "name": self.config.name,
            "seed": self.config.seed,
            "difficulty": self.config.difficulty.value,
            "curriculum": {
                "enabled": self.config.curriculum_enabled,
                "episodes_per_level": self.config.curriculum_episodes_per_level,
            },
            "parameters": {},
        }

        for cat in RandomizationCategory:
            params = getattr(self.config, f"{cat.value}_params")
            data["parameters"][cat.value] = [
                {
                    "name": p.name,
                    "distribution": p.distribution.value,
                    "min": p.min_value,
                    "max": p.max_value,
                    "mean": p.mean,
                    "std": p.std,
                    "choices": p.choices,
                }
                for p in params
            ]

        output.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False), encoding="utf-8")
        console.print(f"[green]✓[/green] Saved domain config to: [bold]{output}[/bold]")
        return output

    # ── Randomization ──────────────────────────────────────────────────────

    def step(self) -> RandomizationState:
        """Perform one randomization step (called at the start of each episode).

        Returns:
            Current randomization state.
        """
        self._episode_count += 1

        # Update difficulty for curriculum
        if self.config.curriculum_enabled:
            self._update_curriculum()

        # Sample all parameters
        param_values: Dict[str, float] = {}

        for cat in RandomizationCategory:
            params = getattr(self.config, f"{cat.value}_params")
            for p in params:
                val = p.sample(self._rng)
                p.current_value = val
                param_values[p.name] = val

        # Apply to simulator if available
        if self.sim_backend:
            self._apply_to_simulator(param_values)

        self._state = RandomizationState(
            episode=self._episode_count,
            difficulty=self.config.difficulty,
            param_values=param_values,
            timestamp=time.time(),
        )
        self._history.append(self._state)

        return self._state

    def _update_curriculum(self) -> None:
        """Update difficulty based on curriculum progress."""
        level_index = self._episode_count // self.config.curriculum_episodes_per_level
        levels = list(DifficultyLevel)
        self.config.difficulty = levels[min(level_index, len(levels) - 1)]

    def _apply_to_simulator(self, param_values: Dict[str, float]) -> None:
        """Apply randomized parameters to the simulation backend."""
        backend = self.sim_backend
        if not backend:
            return

        # Lighting
        if hasattr(backend, "set_lighting"):
            backend.set_lighting(
                intensity=param_values.get("light_intensity", 1.0),
                color_temp=param_values.get("light_color_temp", 5500),
                direction=(param_values.get("light_direction_azimuth", 45),
                            param_values.get("light_direction_elevation", 45)),
            )

        # Physics
        if hasattr(backend, "set_physics"):
            backend.set_physics(
                gravity=param_values.get("gravity_z", -9.81),
                friction=param_values.get("friction_lateral", 1.0),
            )

        # Camera
        if hasattr(backend, "set_camera_pose"):
            backend.set_camera_pose(
                position=(param_values.get("camera_pos_x", 0),
                           param_values.get("camera_pos_y", 0),
                           param_values.get("camera_pos_z", 0)),
                orientation=(param_values.get("camera_roll", 0),
                              param_values.get("camera_pitch", 0),
                              param_values.get("camera_yaw", 0)),
            )

    # ── Category-Specific Randomization ────────────────────────────────────

    def randomize_lighting(self) -> Dict[str, float]:
        """Randomize only lighting parameters."""
        return self._randomize_category(RandomizationCategory.LIGHTING)

    def randomize_textures(self) -> Dict[str, float]:
        """Randomize only texture parameters."""
        return self._randomize_category(RandomizationCategory.TEXTURE)

    def randomize_physics(self) -> Dict[str, float]:
        """Randomize only physics parameters."""
        return self._randomize_category(RandomizationCategory.PHYSICS)

    def randomize_sensors(self) -> Dict[str, float]:
        """Randomize only sensor noise parameters."""
        return self._randomize_category(RandomizationCategory.SENSOR_NOISE)

    def randomize_scene(self) -> Dict[str, float]:
        """Randomize only scene parameters."""
        return self._randomize_category(RandomizationCategory.SCENE)

    def randomize_camera(self) -> Dict[str, float]:
        """Randomize only camera parameters."""
        return self._randomize_category(RandomizationCategory.CAMERA)

    def _randomize_category(self, category: RandomizationCategory) -> Dict[str, float]:
        """Randomize parameters for a specific category."""
        params = getattr(self.config, f"{category.value}_params")
        values = {}
        for p in params:
            val = p.sample(self._rng)
            p.current_value = val
            values[p.name] = val
        return values

    # ── Difficulty ─────────────────────────────────────────────────────────

    def set_difficulty(self, difficulty: DifficultyLevel) -> None:
        """Set the difficulty level."""
        self.config.difficulty = difficulty
        console.print(f"[yellow]→[/yellow] Difficulty set to: [bold]{difficulty.value}[/bold]")

    def get_difficulty(self) -> DifficultyLevel:
        """Get current difficulty level."""
        return self.config.difficulty

    def enable_curriculum(
        self,
        episodes_per_level: int = 100,
        start_level: DifficultyLevel = DifficultyLevel.EASY,
    ) -> None:
        """Enable curriculum learning with progressive difficulty."""
        self.config.curriculum_enabled = True
        self.config.curriculum_episodes_per_level = episodes_per_level
        self.config.difficulty = start_level
        self._episode_count = 0
        console.print(f"[green]✓[/green] Curriculum enabled: {episodes_per_level} episodes/level, starting at {start_level.value}")

    # ── Visualization ──────────────────────────────────────────────────────

    def show_config(self) -> None:
        """Display current domain randomization configuration."""
        console.print(Panel.fit(
            f"[bold cyan]Domain Config: {self.config.name}[/bold cyan]\n"
            f"Difficulty: [yellow]{self.config.difficulty.value}[/yellow]  "
            f"Seed: {self.config.seed}  "
            f"Curriculum: {'[green]on[/green]' if self.config.curriculum_enabled else '[dim]off[/dim]'}",
            border_style="cyan",
        ))

        for cat in RandomizationCategory:
            params = getattr(self.config, f"{cat.value}_params")
            if not params:
                continue

            table = Table(title=f"[bold]{cat.value.upper()}[/bold] ({len(params)} params)")
            table.add_column("Parameter", style="cyan")
            table.add_column("Distribution", style="yellow")
            table.add_column("Range", style="dim")
            table.add_column("Current", style="green")

            for p in params:
                if p.distribution == DistributionType.CHOICE:
                    range_str = str(p.choices)
                elif p.distribution == DistributionType.NORMAL:
                    range_str = f"μ={p.mean:.2f} σ={p.std:.2f}"
                else:
                    range_str = f"[{p.min_value:.2f}, {p.max_value:.2f}]"

                current = f"{p.current_value:.3f}" if p.current_value else "—"
                table.add_row(p.name, p.distribution.value, range_str, current)

            console.print(table)

    def show_state(self) -> None:
        """Display current randomization state."""
        if not self._state.param_values:
            console.print("[dim]No randomization performed yet. Call .step() first.[/dim]")
            return

        console.print(Panel.fit(
            f"[bold cyan]Episode {self._state.episode}[/bold cyan]  "
            f"Difficulty: [yellow]{self._state.difficulty.value}[/yellow]",
            border_style="cyan",
        ))

        table = Table(title="Current Parameter Values")
        table.add_column("Parameter", style="cyan")
        table.add_column("Value", style="green")
        table.add_column("Category", style="dim")

        for name, val in sorted(self._state.param_values.items()):
            # Find category
            cat = "unknown"
            for c in RandomizationCategory:
                params = getattr(self.config, f"{c.value}_params")
                if any(p.name == name for p in params):
                    cat = c.value
                    break

            table.add_row(name, f"{val:.4f}", cat)

        console.print(table)

    def show_history(self, limit: int = 10) -> None:
        """Show recent randomization history."""
        if not self._history:
            console.print("[dim]No history[/dim]")
            return

        table = Table(title=f"Randomization History (last {min(limit, len(self._history))})")
        table.add_column("Episode", style="dim")
        table.add_column("Difficulty", style="yellow")
        table.add_column("Params", style="cyan")
        table.add_column("Timestamp", style="dim")

        for state in self._history[-limit:]:
            # Show first 3 param values as summary
            param_summary = ", ".join(
                f"{k}={v:.2f}" for k, v in list(state.param_values.items())[:3]
            )
            table.add_row(
                str(state.episode),
                state.difficulty.value,
                param_summary,
                time.strftime("%H:%M:%S", time.localtime(state.timestamp)),
            )

        console.print(table)

    # ── Live Display ───────────────────────────────────────────────────────

    def live_display(self, refresh_per_second: float = 2.0) -> Live:
        """Start a live-updating display of randomization state."""
        def render() -> Panel:
            if not self._state.param_values:
                return Panel("[dim]No randomization yet[/dim]", title="Domain Randomizer")

            text = Text()
            text.append(f"Episode: {self._state.episode}\n", style="bold cyan")
            text.append(f"Difficulty: {self._state.difficulty.value}\n", style="yellow")
            text.append("\n")

            # Group by category
            by_cat = defaultdict(list)
            for name, val in self._state.param_values.items():
                for c in RandomizationCategory:
                    params = getattr(self.config, f"{c.value}_params")
                    if any(p.name == name for p in params):
                        by_cat[c.value].append((name, val))
                        break

            for cat, pairs in by_cat.items():
                text.append(f"  {cat.upper()}\n", style="bold")
                for name, val in pairs[:3]:
                    text.append(f"    {name}: {val:.3f}\n", style="dim")
                if len(pairs) > 3:
                    text.append(f"    ... and {len(pairs) - 3} more\n", style="dim")

            return Panel(text, title="Domain Randomizer")

        live = Live(render(), refresh_per_second=refresh_per_second, console=console)
        return live

    # ── Utility ────────────────────────────────────────────────────────────

    def reset_seed(self, seed: Optional[int] = None) -> None:
        """Reset the random seed."""
        if seed is not None:
            self.config.seed = seed
        self._rng = np.random.RandomState(self.config.seed)
        self._history.clear()
        self._episode_count = 0

    def get_state_dict(self) -> Dict[str, Any]:
        """Get current randomization state as a dictionary."""
        return {
            "episode": self._state.episode,
            "difficulty": self._state.difficulty.value,
            "param_values": self._state.param_values,
            "timestamp": self._state.timestamp,
        }

    def add_parameter(self, param: DomainParameter) -> None:
        """Add a custom randomization parameter."""
        cat_attr = f"{param.category.value}_params"
        params = getattr(self.config, cat_attr)
        # Avoid duplicates
        if not any(p.name == param.name for p in params):
            params.append(param)
            console.print(f"[green]✓[/green] Added parameter: [bold]{param.name}[/bold] ({param.category.value})")

    def remove_parameter(self, name: str, category: Optional[RandomizationCategory] = None) -> bool:
        """Remove a parameter by name."""
        if category:
            params = getattr(self.config, f"{category.value}_params")
            before = len(params)
            setattr(self.config, f"{category.value}_params",
                    [p for p in params if p.name != name])
            return before > len(getattr(self.config, f"{category.value}_params"))

        # Search all categories
        for cat in RandomizationCategory:
            params = getattr(self.config, f"{cat.value}_params")
            before = len(params)
            setattr(self.config, f"{cat.value}_params",
                    [p for p in params if p.name != name])
            if before > len(getattr(self.config, f"{cat.value}_params")):
                return True
        return False
