"""
QooBot 双足行走 Gymnasium 强化学习环境。

基于 MuJoCo 物理引擎，训练双足机器人在平地稳定行走。
支持 PPO/SAC 等主流 RL 算法。

Observation (29 维):
    - base_rpy (3): 基座欧拉角
    - base_omega (3): 基座角速度
    - base_vel (2): 基座 x/y 线速度
    - base_height (1): 基座高度
    - joint_pos (12): 腿部 12 个关节位置
    - joint_vel (12): 腿部 12 个关节速度
    - prev_action (12): 上一帧动作 (12维, 默认减去4)

Action (12 维):
    腿部 12 个关节的目标位置偏移量，范围 [-0.5, 0.5] rad

Reward:
    - 前进速度奖励: vx * 2.0
    - 存活奖励: +0.5
    - 姿态惩罚: -roll² * 0.5 - pitch² * 0.5
    - 能耗惩罚: -sum(action²) * 0.001
    - 高度惩罚: -(height - target_height)² * 2.0
    - 跌倒惩罚: -10.0 (终止)
"""

import logging
import os
import sys
import time
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

# ── Gymnasium 可选依赖 ────────────────────────────────
try:
    import gymnasium as gym
    from gymnasium import spaces
    HAS_GYM = True
except ImportError:
    HAS_GYM = False


def _find_walking_dir() -> Optional[Path]:
    """查找行走控制器所在目录。"""
    current = Path(__file__).resolve().parent
    repo_root = current.parent.parent.parent.parent
    walking_dir = repo_root / "qoobot-os" / "hal" / "mechanical" / "mujoco"
    if walking_dir.exists():
        return walking_dir
    return None


class QooBotWalkingEnv(gym.Env):
    """QooBot 双足行走 Gymnasium 环境。

    Attributes:
        model_path: qoobot_float.xml 模型路径
        render_mode: "human" | "rgb_array" | None
        max_episode_steps: 最大步数
    """
    metadata = {"render_modes": ["human", "rgb_array"], "render_fps": 100}

    # ── 关节信息 ────────────────────────────────────
    LEG_JOINTS = [
        "J_hip_l_roll", "J_hip_l_yaw", "J_hip_l_pitch",
        "J_knee_l_pitch", "J_ankle_l_pitch", "J_ankle_l_roll",
        "J_hip_r_roll", "J_hip_r_yaw", "J_hip_r_pitch",
        "J_knee_r_pitch", "J_ankle_r_pitch", "J_ankle_r_roll",
    ]

    LEG_ACTUATORS = [
        "M_hip_l_roll", "M_hip_l_yaw", "M_hip_l_pitch",
        "M_knee_l_pitch", "M_ankle_l_pitch", "M_ankle_l_roll",
        "M_hip_r_roll", "M_hip_r_yaw", "M_hip_r_pitch",
        "M_knee_r_pitch", "M_ankle_r_pitch", "M_ankle_r_roll",
    ]

    # 站立姿态参考值
    STAND_POSE = {
        "J_hip_l_roll": 0.1, "J_hip_l_yaw": 0.0, "J_hip_l_pitch": -0.33,
        "J_knee_l_pitch": 0.536, "J_ankle_l_pitch": -0.206, "J_ankle_l_roll": -0.1,
        "J_hip_r_roll": 0.1, "J_hip_r_yaw": 0.0, "J_hip_r_pitch": -0.33,
        "J_knee_r_pitch": 0.536, "J_ankle_r_pitch": -0.206, "J_ankle_r_roll": -0.1,
    }

    def __init__(
        self,
        model_path: Optional[str] = None,
        render_mode: Optional[str] = None,
        max_episode_steps: int = 1000,
        target_velocity: float = 0.5,
        use_mpc_guide: bool = False,
        use_openloong_controller: bool = False,
    ):
        super().__init__()

        if not HAS_GYM:
            raise ImportError(
                "Gymnasium 未安装。请运行: pip install gymnasium"
            )

        self.render_mode = render_mode
        self.max_episode_steps = max_episode_steps
        self.target_velocity = target_velocity
        self.use_mpc_guide = use_mpc_guide
        self.use_openloong_controller = use_openloong_controller

        # 模型路径
        if model_path is None:
            walking_dir = _find_walking_dir()
            if walking_dir is None:
                raise FileNotFoundError("未找到 qoobot_float.xml 模型文件")
            self.model_path = str(walking_dir / "qoobot_float.xml")
        else:
            self.model_path = model_path

        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"模型文件不存在: {self.model_path}")

        # 导入 mujoco
        import mujoco
        self._mj = mujoco

        # 加载模型
        self._model = mujoco.MjModel.from_xml_path(self.model_path)
        self._data = mujoco.MjData(self._model)

        # 仿真参数
        self._model.opt.timestep = 0.002  # 500Hz
        self._model.opt.gravity[:] = [0, 0, -9.81]
        self._model.opt.solver = mujoco.mjtSolver.mjSOL_NEWTON
        self._model.opt.iterations = 50

        # 渲染器 (headless 时也需要用于 rgb_array)
        self._renderer = None
        self._viewer = None

        # 索引执行器和关节
        self._act_ids = {}
        for aname in self.LEG_ACTUATORS:
            aid = mujoco.mj_name2id(self._model, mujoco.mjtObj.mjOBJ_ACTUATOR, aname)
            if aid >= 0:
                self._act_ids[aname] = aid

        self._joint_info = {}
        for jname in self.LEG_JOINTS:
            jid = mujoco.mj_name2id(self._model, mujoco.mjtObj.mjOBJ_JOINT, jname)
            if jid >= 0:
                self._joint_info[jname] = {
                    "qpos_addr": self._model.jnt_qposadr[jid],
                    "dof_addr": self._model.jnt_dofadr[jid],
                }

        # 足端 body id
        self._foot_body_ids = {
            "left": mujoco.mj_name2id(self._model, mujoco.mjtObj.mjOBJ_BODY, "Link_ankle_l_roll"),
            "right": mujoco.mj_name2id(self._model, mujoco.mjtObj.mjOBJ_BODY, "Link_ankle_r_roll"),
        }

        # 动作空间: 12 个腿部关节目标位置偏移量
        self.action_space = spaces.Box(
            low=-0.5, high=0.5, shape=(12,), dtype=np.float32
        )

        # 观测空间
        obs_dim = 3 + 3 + 2 + 1 + 12 + 12 + 12  # = 45
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(obs_dim,), dtype=np.float32
        )

        # 步数计数
        self._step_count = 0
        self._prev_action = np.zeros(12, dtype=np.float32)

        # MPC 引导 (可选)
        self._mpc_controller = None
        self._openloong_ctrl = None
        if use_mpc_guide:
            self._init_mpc_guide()
        if use_openloong_controller:
            self._init_openloong_controller()

    def _init_mpc_guide(self):
        """初始化 MPC 引导控制器。"""
        walking_dir = _find_walking_dir()
        if walking_dir is None:
            logger.warning("MPC 引导不可用: 未找到控制器目录")
            return
        walking_dir_str = str(walking_dir)
        if walking_dir_str not in sys.path:
            sys.path.insert(0, walking_dir_str)
        try:
            from qoobot_walking_controller import QooBotWalkingController
            self._mpc_controller = QooBotWalkingController(self._model, self._data)
            self._mpc_controller.control_mode = 'position'
            logger.info("MPC 引导控制器已初始化")
        except Exception as e:
            logger.warning(f"MPC 引导控制器初始化失败: {e}")

    def _init_openloong_controller(self):
        """初始化 OpenLoong 风格 MPC+WBC 控制器。"""
        walking_dir = _find_walking_dir()
        if walking_dir is None:
            logger.warning("OpenLoong 控制器不可用: 未找到控制器目录")
            return
        walking_dir_str = str(walking_dir)
        if walking_dir_str not in sys.path:
            sys.path.insert(0, walking_dir_str)
        try:
            from openloong_mpc_wbc import OpenLoongWalkingController
            self._openloong_ctrl = OpenLoongWalkingController(self._model, self._data)
            # 设置目标速度（行走模式）
            self._openloong_ctrl.set_velocity(self.target_velocity, 0.0, 0.0)
            # 站立高度匹配 STAND_POSE 运动学高度（脚底刚好触地）
            self._openloong_ctrl.stand_height = 1.11
            logger.info(
                f"OpenLoong MPC+WBC 控制器已初始化 "
                f"(目标速度: {self.target_velocity} m/s, 站立高度: {self._openloong_ctrl.stand_height:.2f}m)"
            )
        except Exception as e:
            logger.warning(f"OpenLoong 控制器初始化失败: {e}")
            import traceback
            traceback.print_exc()

    # ── Gym API ──────────────────────────────────────

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)

        # 重置仿真
        self._mj.mj_resetData(self._model, self._data)

        # 设置初始姿态 (站立)
        for jname, angle in self.STAND_POSE.items():
            info = self._joint_info.get(jname)
            if info:
                self._data.qpos[info["qpos_addr"]] = angle

        # 基座初始高度（STAND_POSE 运动学计算：脚底刚好触地）
        self._data.qpos[2] = 1.11

        # 随机扰动
        if self.np_random is not None:
            self._data.qpos[0] += self.np_random.uniform(-0.05, 0.05)
            self._data.qpos[1] += self.np_random.uniform(-0.05, 0.05)
            self._data.qpos[2] += self.np_random.uniform(-0.02, 0.02)
            # 小幅随机 yaw
            self._data.qpos[3:7] = self._random_yaw_quat(
                self.np_random.uniform(-0.1, 0.1)
            )

        self._mj.mj_forward(self._model, self._data)

        # 稳定化 (100 步无动作)
        for _ in range(100):
            self._apply_stand_torque()
            self._mj.mj_step(self._model, self._data)

        self._step_count = 0
        self._prev_action = np.zeros(12, dtype=np.float32)

        obs = self._get_obs()
        info = {}

        if self.render_mode == "human":
            self._render()

        return obs, info

    def step(self, action):
        self._step_count += 1

        # 施加动作: 目标位置 = 站立姿态 + 动作偏移
        # 先计算 RL PD 力矩，但不直接写入 ctrl（等 MPC 力矩计算完后叠加）
        rl_torques = {}
        for i, jname in enumerate(self.LEG_JOINTS):
            info = self._joint_info.get(jname)
            if info:
                target = self.STAND_POSE.get(jname, 0.0) + float(action[i])
                current = self._data.qpos[info["qpos_addr"]]
                velocity = self._data.qvel[info["dof_addr"]]
                aname = self.LEG_ACTUATORS[i]
                aid = self._act_ids.get(aname)
                if aid is not None:
                    kp = 200.0
                    kd = 10.0
                    torque = kp * (target - current) - kd * velocity
                    rl_torques[aid] = np.clip(torque, -396, 396)

        # 物理步进 (仿真 2ms * 5 = 控制周期 10ms)
        for sub_step in range(5):
            # 如果使用 OpenLoong MPC+WBC 控制器，在每个子步调用
            if self._openloong_ctrl is not None:
                try:
                    self._openloong_ctrl.step()
                except Exception:
                    pass
            elif self._mpc_controller is not None:
                try:
                    self._mpc_controller.step()
                except Exception:
                    pass

            self._mj.mj_step(self._model, self._data)

            if self.render_mode == "human" and self._viewer is not None and self._viewer.is_running():
                self._viewer.sync()

        # RL PD 力矩叠加到 ctrl（在 MPC/WBC 力矩之上）
        # 如果使用了 OpenLoong 控制器，RL 力矩作为额外引导叠加
        if self._openloong_ctrl is not None or self._mpc_controller is not None:
            for aid, rl_torque in rl_torques.items():
                # 叠加：MPC 提供基础力矩，RL 提供微调
                self._data.ctrl[aid] += rl_torque * 0.3  # RL 力矩衰减为 30%
                self._data.ctrl[aid] = np.clip(self._data.ctrl[aid], -396, 396)
        else:
            # 纯 RL 模式：直接写入 ctrl
            for aid, rl_torque in rl_torques.items():
                self._data.ctrl[aid] = rl_torque

        # 观测
        obs = self._get_obs()
        self._prev_action = action.copy()

        # 奖励计算
        reward = self._compute_reward(action)

        # 终止判断
        terminated = self._is_terminated()
        truncated = self._step_count >= self.max_episode_steps

        info = {
            "step": self._step_count,
            "base_height": float(self._data.qpos[2]),
            "base_vel_x": float(self._data.qvel[0]),
        }

        return obs, float(reward), terminated, truncated, info

    def render(self):
        if self.render_mode == "rgb_array":
            return self._render_rgb()
        elif self.render_mode == "human":
            self._render()

    def close(self):
        if self._viewer is not None:
            try:
                self._viewer.close()
            except Exception:
                pass
            self._viewer = None
        self._renderer = None

    # ── 内部方法 ──────────────────────────────────────

    def _get_obs(self) -> np.ndarray:
        """构建观测向量。"""
        data = self._data

        # 基座姿态
        base_quat = data.qpos[3:7].copy()
        rpy = self._quat_to_rpy(base_quat)

        # 角速度
        base_omega = data.qvel[3:6].copy()

        # 线速度 (世界坐标系)
        base_vel = data.qvel[0:2].copy()

        # 高度
        base_height = np.array([data.qpos[2]], dtype=np.float32)

        # 腿部关节位置和速度
        joint_pos = np.zeros(12, dtype=np.float32)
        joint_vel = np.zeros(12, dtype=np.float32)
        for i, jname in enumerate(self.LEG_JOINTS):
            info = self._joint_info.get(jname)
            if info:
                joint_pos[i] = float(data.qpos[info["qpos_addr"]])
                joint_vel[i] = float(data.qvel[info["dof_addr"]])

        # 上一帧动作
        prev_action = self._prev_action.copy()

        obs = np.concatenate([
            rpy.astype(np.float32),
            base_omega.astype(np.float32),
            base_vel.astype(np.float32),
            base_height.astype(np.float32),
            joint_pos,
            joint_vel,
            prev_action,
        ])

        return obs

    def _compute_reward(self, action: np.ndarray) -> float:
        """计算奖励 (参考 DeepMind MuJoCo 行走任务设计)。"""
        data = self._data

        base_quat = data.qpos[3:7].copy()
        rpy = self._quat_to_rpy(base_quat)

        vx = float(data.qvel[0])
        vy = float(data.qvel[1])
        height = float(data.qpos[2])
        target_height = 1.11
        target_vel = self.target_velocity  # 0.5 m/s

        # 1. 目标速度高斯奖励 (核心：鼓励精确匹配 0.5m/s)
        vel_reward = np.exp(-((vx - target_vel) ** 2) / 0.25)

        # 2. 存活奖励 (保持活着)
        alive_bonus = 1.0

        # 3. 姿态惩罚 (保持直立)
        roll, pitch = rpy[0], rpy[1]
        orientation_penalty = -(roll ** 2 + pitch ** 2) * 2.0

        # 4. 能耗惩罚 (减小，避免过度惩罚动作)
        energy_penalty = -float(np.sum(np.square(action))) * 0.0005

        # 5. 高度惩罚 (保持目标高度)
        height_penalty = -((height - target_height) ** 2) * 5.0

        # 6. 侧向速度惩罚 (直线前进)
        lateral_penalty = -(vy ** 2) * 1.0

        # 7. 关节加速度惩罚 (鼓励平滑动作)
        action_diff = action - self._prev_action
        smooth_penalty = -float(np.sum(np.square(action_diff))) * 0.01

        reward = (
            vel_reward * 2.0
            + alive_bonus
            + orientation_penalty
            + energy_penalty
            + height_penalty
            + lateral_penalty
            + smooth_penalty
        )

        return reward

    def _is_terminated(self) -> bool:
        """判断是否终止。"""
        data = self._data

        # 基座高度过低
        if data.qpos[2] < 0.5:
            return True

        # 基座高度过高 (飞起来了)
        if data.qpos[2] > 1.5:
            return True

        # 姿态过大 (倒地)
        base_quat = data.qpos[3:7].copy()
        rpy = self._quat_to_rpy(base_quat)
        if abs(rpy[0]) > 0.8 or abs(rpy[1]) > 0.8:
            return True

        return False

    def _apply_stand_torque(self):
        """施加站立姿态的 PD 控制力矩。"""
        for i, jname in enumerate(self.LEG_JOINTS):
            info = self._joint_info.get(jname)
            if info:
                target = self.STAND_POSE.get(jname, 0.0)
                current = self._data.qpos[info["qpos_addr"]]
                velocity = self._data.qvel[info["dof_addr"]]
                aname = self.LEG_ACTUATORS[i]
                aid = self._act_ids.get(aname)
                if aid is not None:
                    kp = 400.0  # 提高增益以更好支撑
                    kd = 15.0
                    torque = kp * (target - current) - kd * velocity
                    self._data.ctrl[aid] = np.clip(torque, -396, 396)

    def _render_rgb(self) -> np.ndarray:
        """渲染 RGB 图像。"""
        if self._renderer is None:
            self._renderer = self._mj.Renderer(self._model, 480, 640)
        self._renderer.update_scene(self._data, camera="track")
        return self._renderer.render()

    def _render(self):
        """启动/更新渲染窗口 (被动模式 + 主动同步)。"""
        if self._viewer is None:
            try:
                from mujoco import viewer as mj_viewer
                self._viewer = mj_viewer.launch_passive(
                    self._model, self._data,
                    show_left_ui=False,
                    show_right_ui=False,
                )
            except Exception as e:
                logger.warning(f"无法启动渲染窗口: {e}")
        if self._viewer is not None and self._viewer.is_running():
            self._viewer.sync()

    @staticmethod
    def _quat_to_rpy(quat):
        """四元数转欧拉角 (roll, pitch, yaw)。"""
        w, x, y, z = quat
        roll = np.arctan2(2 * (w * x + y * z), 1 - 2 * (x * x + y * y))
        pitch = np.arcsin(np.clip(2 * (w * y - z * x), -1, 1))
        yaw = np.arctan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z))
        return np.array([roll, pitch, yaw], dtype=np.float32)

    @staticmethod
    def _random_yaw_quat(yaw):
        """生成随机 yaw 的四元数。"""
        half_yaw = yaw / 2
        return np.array([
            np.cos(half_yaw), 0, 0, np.sin(half_yaw)
        ], dtype=np.float64)

    @property
    def model(self):
        return self._model

    @property
    def data(self):
        return self._data


# ── 环境注册 ──────────────────────────────────────────

def register_envs():
    """注册 QooBot Gymnasium 环境。"""
    if not HAS_GYM:
        return
    gym.register(
        id="QooBotWalking-v0",
        entry_point="cli.sim_bridge.walking_env:QooBotWalkingEnv",
        max_episode_steps=1000,
    )
