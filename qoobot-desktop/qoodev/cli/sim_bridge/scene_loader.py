"""场景加载器。

支持从文件或预设加载仿真场景。
"""

import json
import logging
from pathlib import Path
from typing import Optional

from .interface import SimScene, SimRobot, ControlMode

logger = logging.getLogger(__name__)

# 预置场景注册表
_PRESET_SCENES: dict[str, SimScene] = {}


def register_preset(name: str, scene: SimScene) -> None:
    """注册预置场景。"""
    _PRESET_SCENES[name] = scene
    logger.info(f"注册预置场景: {name}")


def get_preset(name: str) -> Optional[SimScene]:
    """获取预置场景。"""
    return _PRESET_SCENES.get(name)


def list_presets() -> list[str]:
    """列出所有预置场景。"""
    return list(_PRESET_SCENES.keys())


class SceneLoader:
    """场景加载器。

    支持:
    - 预置场景 (家居/工厂)
    - MJCF 文件 (MuJoCo)
    - USD 文件 (Isaac Sim)
    - 自定义 JSON 场景描述
    """

    def __init__(self, presets_dir: Optional[Path] = None):
        self.presets_dir = presets_dir or Path(__file__).parent / "presets"

    def load(self, scene_ref: str) -> SimScene:
        """加载场景。

        Args:
            scene_ref: 场景引用，可以是:
                - 预置名称: "home" / "factory"
                - 文件路径: "/path/to/scene.mjcf" / "/path/to/scene.usd"
                - JSON 路径: "/path/to/scene.json"
        """
        # 1. 尝试预置场景
        preset = get_preset(scene_ref)
        if preset is not None:
            logger.info(f"加载预置场景: {scene_ref}")
            return preset

        # 2. 尝试文件路径
        path = Path(scene_ref)
        if path.exists():
            return self._load_from_file(path)

        # 3. 在 presets_dir 中搜索
        local_path = self.presets_dir / scene_ref
        if local_path.exists():
            return self._load_from_file(local_path)

        raise FileNotFoundError(f"无法找到场景: {scene_ref}。"
                                f"可用预置: {list_presets()}")

    def _load_from_file(self, path: Path) -> SimScene:
        """从文件加载场景。"""
        suffix = path.suffix.lower()

        if suffix == ".json":
            return self._load_json(path)
        elif suffix in (".xml", ".mjcf"):
            return self._load_mjcf(path)
        elif suffix in (".usd", ".usda", ".usdc"):
            return self._load_usd(path)
        else:
            raise ValueError(f"不支持的文件格式: {suffix}")

    def _load_json(self, path: Path) -> SimScene:
        """从 JSON 文件加载场景描述。"""
        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        robots = [
            SimRobot(
                name=r["name"],
                model_path=r.get("model_path", ""),
                base_position=tuple(r.get("base_position", [0, 0, 0])),
                base_orientation=tuple(r.get("base_orientation", [1, 0, 0, 0])),
                control_mode=ControlMode(r.get("control_mode", "position")),
                fixed_base=r.get("fixed_base", False),
                actuators=r.get("actuators", {}),
                sensors=r.get("sensors", []),
                extra=r.get("extra", {}),
            )
            for r in data.get("robots", [])
        ]

        return SimScene(
            name=data.get("name", path.stem),
            description=data.get("description", ""),
            scene_path=data.get("scene_path"),
            robots=robots,
            objects=data.get("objects", []),
            lights=data.get("lights", []),
            cameras=data.get("cameras", []),
            extra=data.get("extra", {}),
        )

    def _load_mjcf(self, path: Path) -> SimScene:
        """从 MJCF 文件提取场景信息。"""
        return SimScene(
            name=path.stem,
            description=f"MuJoCo 场景: {path.name}",
            scene_path=str(path),
            robots=[],
        )

    def _load_usd(self, path: Path) -> SimScene:
        """从 USD 文件提取场景信息。"""
        return SimScene(
            name=path.stem,
            description=f"USD 场景: {path.name}",
            scene_path=str(path),
            robots=[],
        )


# ── 注册预置场景 ────────────────────────────────────────

def _register_default_presets() -> None:
    """注册默认预置场景。"""

    # 家居场景
    home = SimScene(
        name="home",
        description="家居仿真场景 — 客厅 + 厨房，适合服务机器人技能开发",
        robots=[
            SimRobot(
                name="mobile_manipulator",
                model_path="robots/franka_panda/mobile_panda.xml",
                base_position=(0.0, 0.0, 0.0),
                control_mode=ControlMode.END_EFFECTOR,
                sensors=["rgbd_camera", "imu", "joint_states"],
            ),
        ],
        objects=[
            {"name": "table", "type": "mesh", "path": "objects/furniture/table.stl",
             "position": [0.8, 0.0, 0.0], "size": [1.2, 0.8, 0.75]},
            {"name": "cup", "type": "mesh", "path": "objects/kitchen/cup.stl",
             "position": [0.8, 0.1, 0.75], "size": [0.08, 0.08, 0.12]},
            {"name": "plate", "type": "mesh", "path": "objects/kitchen/plate.stl",
             "position": [0.8, -0.15, 0.75], "size": [0.25, 0.25, 0.03]},
            {"name": "chair", "type": "mesh", "path": "objects/furniture/chair.stl",
             "position": [1.5, -0.5, 0.0], "size": [0.5, 0.5, 1.0]},
            {"name": "shelf", "type": "mesh", "path": "objects/furniture/shelf.stl",
             "position": [-0.5, 1.5, 0.0], "size": [1.0, 0.3, 1.8]},
        ],
        lights=[
            {"type": "directional", "position": [0, 0, 5], "direction": [0, 0, -1]},
            {"type": "ambient", "intensity": 0.3},
        ],
        cameras=[
            {"name": "overhead", "position": [0, 0, 3], "target": [0, 0, 0.5], "fov": 60},
            {"name": "front", "position": [2, 0, 1], "target": [0, 0, 0.5], "fov": 45},
        ],
    )

    # 工厂场景
    factory = SimScene(
        name="factory",
        description="工厂仿真场景 — 产线 + 仓储，适合工业机器人技能开发",
        robots=[
            SimRobot(
                name="industrial_arm",
                model_path="robots/ur5e/ur5e.xml",
                base_position=(0.0, 0.0, 0.0),
                control_mode=ControlMode.POSITION,
                fixed_base=True,
                sensors=["joint_states", "force_torque"],
            ),
            SimRobot(
                name="conveyor_belt",
                model_path="robots/conveyor/conveyor.xml",
                base_position=(1.5, 0.0, 0.0),
                control_mode=ControlMode.VELOCITY,
                fixed_base=True,
                sensors=["joint_states"],
            ),
        ],
        objects=[
            {"name": "workbench", "type": "mesh", "path": "objects/industrial/workbench.stl",
             "position": [0.5, -0.8, 0.0], "size": [1.5, 0.8, 0.9]},
            {"name": "parts_bin", "type": "mesh", "path": "objects/industrial/bin.stl",
             "position": [0.5, 0.6, 0.0], "size": [0.6, 0.4, 0.3]},
            {"name": "pallet", "type": "mesh", "path": "objects/industrial/pallet.stl",
             "position": [2.5, 0.0, 0.0], "size": [1.2, 1.0, 0.15]},
        ],
        lights=[
            {"type": "directional", "position": [0, 0, 8], "direction": [0, 0, -1]},
            {"type": "point", "position": [2, 2, 3], "intensity": 0.5},
            {"type": "ambient", "intensity": 0.2},
        ],
        cameras=[
            {"name": "top_down", "position": [1, 0, 4], "target": [1, 0, 0.5], "fov": 70},
            {"name": "side", "position": [3, -2, 1.5], "target": [0.5, 0, 0.5], "fov": 50},
        ],
    )

    register_preset("home", home)
    register_preset("factory", factory)

    # 空白场景
    empty = SimScene(
        name="empty",
        description="空白仿真场景，适合从零搭建",
    )
    register_preset("empty", empty)


_register_default_presets()
