"""行走控制器桥接模块。

将 qoobot-os 中的 MPC+WBC 行走控制器桥接到 qoodev 仿真框架。
"""

import logging
import os
import sys
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# 行走控制器实例缓存
_walking_controller = None
_walking_model = None
_walking_data = None


def _find_walking_controller_dir() -> Optional[Path]:
    """查找行走控制器所在目录。"""
    current = Path(__file__).resolve().parent
    # cli/sim_bridge -> cli -> qoodev -> qoobot-desktop -> qoobot
    repo_root = current.parent.parent.parent.parent
    walking_dir = repo_root / "qoobot-os" / "hal" / "mechanical" / "mujoco"
    if walking_dir.exists():
        return walking_dir
    return None


def init_walking_controller(model, data) -> bool:
    """初始化行走控制器。

    Args:
        model: MuJoCo MjModel 实例
        data: MuJoCo MjData 实例

    Returns:
        是否成功初始化
    """
    global _walking_controller, _walking_model, _walking_data

    walking_dir = _find_walking_controller_dir()
    if walking_dir is None:
        logger.warning("未找到行走控制器目录")
        return False

    # 确保控制器目录在 sys.path 中
    walking_dir_str = str(walking_dir)
    if walking_dir_str not in sys.path:
        sys.path.insert(0, walking_dir_str)

    try:
        from qoobot_walking_controller import QooBotWalkingController
        from qoobot_robot_params import STAND_POSE
        import mujoco

        _walking_controller = QooBotWalkingController(model, data)
        _walking_controller.control_mode = 'position'
        _walking_model = model
        _walking_data = data

        # 初始化站立姿态
        for jname, angle in STAND_POSE.items():
            jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, jname)
            if jid >= 0:
                qpos_addr = model.jnt_qposadr[jid]
                if qpos_addr >= 0:
                    data.qpos[qpos_addr] = angle

        data.qpos[2] = 1.0  # 基座高度

        # 稳定接触
        for _ in range(200):
            _walking_controller.step()
            mujoco.mj_step(model, data)

        _walking_controller.stop()
        logger.info("行走控制器初始化完成，机器人已站立")
        return True

    except ImportError as e:
        logger.warning(f"行走控制器导入失败: {e}")
        return False
    except Exception as e:
        logger.error(f"行走控制器初始化失败: {e}")
        return False


def walking_step() -> bool:
    """执行一步行走控制。

    Returns:
        是否成功执行
    """
    global _walking_controller, _walking_model, _walking_data
    if _walking_controller is None:
        return False
    try:
        _walking_controller.step()
        return True
    except Exception as e:
        logger.error(f"行走控制步进失败: {e}")
        return False


def set_walking_velocity(vx: float = 0.0, vy: float = 0.0, wz: float = 0.0) -> None:
    """设置行走速度指令。

    Args:
        vx: 前进速度 (m/s)
        vy: 侧向速度 (m/s)
        wz: 转向角速度 (rad/s)
    """
    global _walking_controller
    if _walking_controller is None:
        return
    if vx == 0.0 and vy == 0.0 and wz == 0.0:
        _walking_controller.stop()
    else:
        _walking_controller.set_velocity(vx, vy, wz)


def stop_walking() -> None:
    """停止行走。"""
    global _walking_controller
    if _walking_controller is not None:
        _walking_controller.stop()


def toggle_control_mode() -> str:
    """切换控制模式 (position <-> torque)。"""
    global _walking_controller
    if _walking_controller is not None:
        return _walking_controller.toggle_control_mode()
    return "unknown"


def get_walking_state() -> dict:
    """获取行走状态信息。"""
    global _walking_controller
    if _walking_controller is None:
        return {}
    try:
        gait = _walking_controller.gait
        return {
            "leg_state": gait.leg_state,
            "phase": gait.phi,
            "control_mode": _walking_controller.control_mode,
            "walking_enabled": _walking_controller.walking_enabled,
        }
    except Exception:
        return {}


def shutdown_walking_controller() -> None:
    """关闭行走控制器。"""
    global _walking_controller, _walking_model, _walking_data
    _walking_controller = None
    _walking_model = None
    _walking_data = None
