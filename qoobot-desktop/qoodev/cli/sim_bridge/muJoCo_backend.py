"""MuJoCo 仿真后端。

基于 DeepMind MuJoCo 物理引擎的仿真后端实现。
支持 MJCF 场景格式，适用于快速原型开发和 CI/CD。
"""

import logging
import os
import time
from pathlib import Path
from typing import Any, Optional

import numpy as np

from .interface import (
    SimBackend,
    SimConfig,
    SimControlCommand,
    SimScene,
    SimSensorData,
    SimState,
    SimStats,
    SensorType,
    ControlMode,
)

logger = logging.getLogger(__name__)


class MuJoCoBackend(SimBackend):
    """MuJoCo 物理引擎后端。

    Requirements:
        pip install mujoco
    """

    def __init__(self, config: SimConfig):
        super().__init__(config)
        self._model = None       # mujoco.MjModel
        self._data = None        # mujoco.MjData
        self._renderer = None    # mujoco.Renderer
        self._viewer = None      # mujoco.Viewer (非 headless)
        self._cameras: dict[str, int] = {}      # name -> camera_id
        self._sensors: dict[str, dict] = {}     # name -> sensor_info
        self._actuators: dict[str, dict] = {}   # name -> actuator_info
        self._joint_map: dict[str, int] = {}    # robot.joint -> mj_id

    # ── 生命周期 ──────────────────────────────────────

    def initialize(self) -> None:
        """初始化 MuJoCo 引擎。"""
        try:
            import mujoco
            self._mujoco = mujoco
        except ImportError:
            raise ImportError(
                "MuJoCo 未安装。请运行: pip install mujoco"
            )

        self.state = SimState.READY
        logger.info("MuJoCo 后端初始化完成")

    def load_scene(self, scene: SimScene) -> None:
        """加载 MJCF 场景。"""
        self.state = SimState.LOADING
        self.scene = scene

        # 确定模型路径
        if scene.scene_path and os.path.exists(scene.scene_path):
            model_path = scene.scene_path
        else:
            # 使用预置场景生成 MJCF
            model_path = self._generate_mjcf(scene)

        logger.info(f"加载 MuJoCo 模型: {model_path}")

        self._model = self._mujoco.MjModel.from_xml_path(model_path)
        self._data = self._mujoco.MjData(self._model)

        # 配置物理参数
        self._model.opt.timestep = self.config.time_step
        self._model.opt.gravity[:] = self.config.gravity
        self._model.opt.solver = self._mujoco.mjtSolver.mjSOL_NEWTON
        self._model.opt.iterations = self.config.solver_iterations

        # 初始化渲染器
        if not self.config.headless:
            # 使用模型定义的 offscreen framebuffer 大小，避免超出限制
            render_w = min(self.config.render_width, max(self._model.vis.global_.offwidth, 640))
            render_h = min(self.config.render_height, max(self._model.vis.global_.offheight, 480))
            self._renderer = self._mujoco.Renderer(
                self._model,
                render_h,
                render_w,
            )

            # 启动被动渲染窗口（独立进程，不阻塞仿真循环）
            # left_ui=左侧信息面板, right_ui=右侧控制面板(含播放/暂停/重置/速度等按钮)
            try:
                from mujoco import viewer as mj_viewer
                self._viewer = mj_viewer.launch_passive(
                    self._model, self._data,
                    show_left_ui=True,
                    show_right_ui=True,
                )
                logger.info("MuJoCo 被动渲染窗口已启动")
            except Exception as e:
                logger.warning(f"无法启动渲染窗口: {e}。"
                               "仿真将在无窗口模式下运行。")

        # 索引相机、传感器、执行器
        self._index_elements()

        self._mujoco.mj_forward(self._model, self._data)

        # 行走控制器（可选）
        self._walking_enabled = False
        self._walking_ctrl = None

        self.state = SimState.READY
        logger.info(f"场景加载完成: {scene.name} "
                     f"(qpos={self._model.nq}, qvel={self._model.nv})")

    def enable_walking(self) -> bool:
        """启用行走控制器（MPC+WBC）。"""
        from .walking_bridge import init_walking_controller
        if init_walking_controller(self._model, self._data):
            self._walking_enabled = True
            logger.info("行走控制器已启用")
            return True
        logger.warning("行走控制器启用失败")
        return False

    def disable_walking(self) -> None:
        """禁用行走控制器。"""
        from .walking_bridge import shutdown_walking_controller
        shutdown_walking_controller()
        self._walking_enabled = False
        logger.info("行走控制器已禁用")

    def set_walking_velocity(self, vx: float = 0.0, vy: float = 0.0, wz: float = 0.0) -> None:
        """设置行走速度。"""
        from .walking_bridge import set_walking_velocity
        set_walking_velocity(vx, vy, wz)

    def step(self) -> None:
        """推进一个仿真步长。"""
        if self.state != SimState.RUNNING:
            return
        step_start = time.perf_counter()

        # 行走控制器步进（在物理步进之前）
        if self._walking_enabled:
            from .walking_bridge import walking_step
            walking_step()

        self._mujoco.mj_step(self._model, self._data)

        physics_time = time.perf_counter() - step_start

        # 同步被动渲染窗口
        if self._viewer and self._viewer.is_running():
            self._viewer.sync()
            render_time = time.perf_counter() - step_start - physics_time
        elif self._renderer and not self.config.headless:
            self._renderer.update_scene(self._data)
            render_time = time.perf_counter() - step_start - physics_time
        else:
            render_time = 0.0

        self.stats.total_steps += 1
        self.stats.total_time += self.config.time_step
        self.stats.physics_time_ms = physics_time * 1000
        self.stats.render_time_ms = render_time * 1000
        self.stats.step_time_ms = (physics_time + render_time) * 1000
        if self.stats.step_time_ms > 0:
            self.stats.real_time_factor = (
                self.config.time_step * 1000 / self.stats.step_time_ms
            )

    def reset(self) -> None:
        """重置仿真到初始状态。"""
        if self._model and self._data:
            self._mujoco.mj_resetData(self._model, self._data)
            self._mujoco.mj_forward(self._model, self._data)
            self.stats = SimStats()
            logger.info("仿真已重置")

    def shutdown(self) -> None:
        """关闭 MuJoCo 引擎。"""
        self.state = SimState.STOPPED
        if self._viewer:
            try:
                self._viewer.close()
            except Exception:
                pass
            self._viewer = None
        self._model = None
        self._data = None
        self._renderer = None
        logger.info("MuJoCo 后端已关闭")

    # ── 状态控制 ──────────────────────────────────────

    def pause(self) -> None:
        if self.state == SimState.RUNNING:
            self.state = SimState.PAUSED
            logger.info("仿真已暂停")

    def resume(self) -> None:
        if self.state == SimState.PAUSED:
            self.state = SimState.RUNNING
            logger.info("仿真已恢复")

    # ── 传感器 ────────────────────────────────────────

    def get_sensor_data(self, sensor_name: str) -> SimSensorData:
        """获取指定传感器数据。"""
        if sensor_name not in self._sensors:
            raise KeyError(f"传感器不存在: {sensor_name}")

        sensor_info = self._sensors[sensor_name]
        sensor_type = sensor_info["type"]
        adr = sensor_info["adr"]
        dim = sensor_info["dim"]

        raw = self._data.sensordata[adr:adr + dim].copy()

        return self._build_sensor_data(sensor_name, sensor_type, raw)

    def get_all_sensor_data(self) -> list[SimSensorData]:
        """获取所有传感器数据。"""
        results = []
        for name in self._sensors:
            try:
                results.append(self.get_sensor_data(name))
            except Exception:
                logger.exception(f"读取传感器 {name} 失败")
        return results

    # ── 控制 ──────────────────────────────────────────

    def apply_control(self, command: SimControlCommand) -> None:
        """发送控制指令。"""
        robot_name = command.robot_name

        if robot_name not in self._actuators:
            logger.warning(f"机器人 {robot_name} 无执行器")
            return

        for i, joint_name in enumerate(command.joint_names):
            if i >= len(command.targets):
                break
            actuator_id = self._actuators.get(
                f"{robot_name}/{joint_name}",
                self._actuators.get(joint_name),
            )
            if actuator_id is not None:
                target = command.targets[i]
                if command.control_mode == ControlMode.POSITION:
                    self._data.ctrl[actuator_id["id"]] = target
                elif command.control_mode == ControlMode.VELOCITY:
                    self._data.ctrl[actuator_id["id"]] = target
                elif command.control_mode == ControlMode.TORQUE:
                    self._data.ctrl[actuator_id["id"]] = target

    def get_joint_states(self, robot_name: str) -> dict[str, Any]:
        """获取关节状态。"""
        joint_ids = self._joint_map.get(robot_name, {})
        positions = {}
        velocities = {}
        for name, jid in joint_ids.items():
            qpos_addr = self._model.jnt_qposadr[jid]
            qvel_addr = self._model.jnt_dofadr[jid]
            positions[name] = float(self._data.qpos[qpos_addr])
            velocities[name] = float(self._data.qvel[qvel_addr])

        return {
            "name": robot_name,
            "positions": positions,
            "velocities": velocities,
            "timestamp": self._data.time,
        }

    # ── 位姿查询 ──────────────────────────────────────

    def get_robot_pose(self, robot_name: str) -> tuple[np.ndarray, np.ndarray]:
        """获取机器人基座位姿。"""
        body_id = self._model.body(robot_name).id if hasattr(
            self._model, 'body'
        ) else 0
        pos = self._data.xpos[body_id].copy()
        quat = self._data.xquat[body_id].copy()
        return pos, quat

    def get_object_pose(self, object_name: str) -> tuple[np.ndarray, np.ndarray]:
        """获取物体位姿。"""
        try:
            body_id = self._mujoco.mj_name2id(
                self._model, self._mujoco.mjtObj.mjOBJ_BODY, object_name
            )
        except Exception:
            body_id = 0
        pos = self._data.xpos[body_id].copy()
        quat = self._data.xquat[body_id].copy()
        return pos, quat

    # ── 渲染 ──────────────────────────────────────────

    def render(self, camera_name: str = "") -> np.ndarray:
        """渲染一帧 RGB 图像。"""
        if self._renderer is None:
            raise RuntimeError("渲染器未初始化（可能处于 headless 模式）")

        if camera_name and camera_name in self._cameras:
            camera_id = self._cameras[camera_name]
            self._renderer.update_scene(self._data, camera=camera_id)
        else:
            self._renderer.update_scene(self._data)

        pixels = self._renderer.render()
        return pixels

    # ── 统计 ──────────────────────────────────────────

    def get_stats(self) -> SimStats:
        return self.stats

    # ── 内部方法 ───────────────────────────────────────

    def _index_elements(self) -> None:
        """索引场景中的相机、传感器和执行器。"""
        self._cameras.clear()
        self._sensors.clear()
        self._actuators.clear()
        self._joint_map.clear()

        # 索引相机
        for i in range(self._model.ncam):
            name = self._model.camera(i).name or f"camera_{i}"
            self._cameras[name] = i

        # 索引传感器
        for i in range(self._model.nsensor):
            name = self._model.sensor(i).name or f"sensor_{i}"
            sensor_type = self._mujoco.mjtSensor(self._model.sensor_type[i])
            self._sensors[name] = {
                "id": i,
                "adr": self._model.sensor_adr[i],
                "dim": self._model.sensor_dim[i],
                "type": sensor_type,
            }

        # 索引执行器
        for i in range(self._model.nu):
            name = self._model.actuator(i).name or f"actuator_{i}"
            self._actuators[name] = {"id": i}

        # 索引关节
        for i in range(self._model.njnt):
            name = self._model.joint(i).name or f"joint_{i}"
            # 按机器人分组（简化：所有关节属于 scene 中的第一个机器人）
            robot_name = self.scene.robots[0].name if self.scene and self.scene.robots else "robot"
            if robot_name not in self._joint_map:
                self._joint_map[robot_name] = {}
            self._joint_map[robot_name][name] = i

    def _build_sensor_data(
        self, name: str, sensor_type: Any, raw: np.ndarray
    ) -> SimSensorData:
        """将原始传感器数据转换为统一格式。"""
        mj_sensor = self._mujoco.mjtSensor

        if sensor_type in (mj_sensor.mjSENS_FRAMEPOS, mj_sensor.mjSENS_FRAMEXAXIS):
            stype = SensorType.ODOMETRY
        elif sensor_type in (mj_sensor.mjSENS_ACCELEROMETER, mj_sensor.mjSENS_GYRO):
            stype = SensorType.IMU
        elif sensor_type in (mj_sensor.mjSENS_JOINTPOS, mj_sensor.mjSENS_JOINTVEL):
            stype = SensorType.JOINT_STATES
        elif sensor_type in (mj_sensor.mjSENS_FORCE, mj_sensor.mjSENS_TORQUE):
            stype = SensorType.FORCE_TORQUE
        elif sensor_type == mj_sensor.mjSENS_TOUCH:
            stype = SensorType.CONTACT
        else:
            stype = SensorType.JOINT_STATES

        return SimSensorData(
            sensor_type=stype,
            timestamp=self._data.time,
            data=raw,
            frame_id=name,
            metadata={"raw_type": str(sensor_type)},
        )

    def _generate_mjcf(self, scene: SimScene) -> str:
        """为预置场景生成临时 MJCF 文件。"""
        import tempfile

        xml = self._build_mjcf_xml(scene)
        tmp = tempfile.NamedTemporaryFile(
            suffix=".xml", delete=False, mode="w", encoding="utf-8"
        )
        tmp.write(xml)
        tmp.close()
        return tmp.name

    def _build_mjcf_xml(self, scene: SimScene) -> str:
        """构建 MJCF XML 字符串。"""
        lines = ['<mujoco model="qoo_scene">']

        # 编译器选项
        lines.append(f'  <option timestep="{self.config.time_step}" '
                     f'gravity="{" ".join(map(str, self.config.gravity))}" '
                     f'iterations="{self.config.solver_iterations}"/>')

        # 视觉设置（offscreen framebuffer）
        lines.append(f'  <visual>')
        lines.append(f'    <global offwidth="{self.config.render_width}" '
                     f'offheight="{self.config.render_height}"/>')
        lines.append(f'  </visual>')

        # 默认设置
        lines.append('  <default>')
        lines.append('    <geom friction="0.5 0.005 0.0001"/>')
        lines.append('    <joint limited="true" damping="1"/>')
        lines.append('  </default>')

        # 资源
        lines.append('  <asset>')
        lines.append('    <texture type="skybox" builtin="gradient" '
                     'rgb1="0.3 0.5 0.7" rgb2="0 0 0" width="512" height="512"/>')
        lines.append('    <texture type="2d" name="groundplane" builtin="checker" '
                     'mark="edge" rgb1="0.2 0.3 0.4" rgb2="0.1 0.2 0.3" '
                     'markrgb="0.8 0.8 0.8" width="300" height="300"/>')
        lines.append('    <material name="groundplane" texture="groundplane" '
                     'texrepeat="5 5" texuniform="true" reflectance="0.2"/>')
        lines.append('  </asset>')

        # 世界
        lines.append('  <worldbody>')
        lines.append('    <geom name="floor" type="plane" size="5 5 0.05" '
                     'material="groundplane"/>')
        lines.append('    <light directional="true" pos="0 0 5" dir="0 0 -1"/>')

        # 物体
        for obj in scene.objects:
            pos = " ".join(map(str, obj.get("position", [0, 0, 0.5])))
            size = " ".join(map(str, obj.get("size", [0.1, 0.1, 0.1])))
            obj_type = obj.get("type", "box")
            # mesh 类型需要 mesh 文件，对于预置场景回退为 box
            if obj_type == "mesh":
                obj_type = "box"
            lines.append(
                f'    <body name="{obj["name"]}" pos="{pos}">'
            )
            lines.append(
                f'      <geom name="{obj["name"]}_geom" type="{obj_type}" '
                f'size="{size}" rgba="0.6 0.6 0.6 1"/>'
            )
            lines.append(f'    </body>')

        # 机器人
        for robot in scene.robots:
            pos = " ".join(map(str, robot.base_position))
            lines.append(f'    <body name="{robot.name}" pos="{pos}">')
            lines.append(f'      <joint name="{robot.name}_root" type="free"/>')
            # 简化：添加一个可视化的方块代表机器人基座
            lines.append(
                f'      <geom name="{robot.name}_base" type="box" '
                f'size="0.3 0.3 0.05" rgba="0.2 0.6 0.9 1"/>'
            )
            # 机械臂简化表示
            lines.append(
                f'      <body name="{robot.name}_arm_link1" pos="0 0 0.3">'
            )
            lines.append(
                f'        <joint name="{robot.name}_j1" type="hinge" axis="0 0 1" range="-3.14 3.14"/>'
            )
            lines.append(
                f'        <geom name="{robot.name}_link1" type="cylinder" '
                f'size="0.05 0.2" rgba="0.3 0.7 0.9 1"/>'
            )
            lines.append(
                f'        <body name="{robot.name}_arm_link2" pos="0 0 0.2">'
            )
            lines.append(
                f'          <joint name="{robot.name}_j2" type="hinge" axis="0 1 0" range="-2.5 2.5"/>'
            )
            lines.append(
                f'          <geom name="{robot.name}_link2" type="cylinder" '
                f'size="0.04 0.18" rgba="0.4 0.8 0.9 1"/>'
            )
            # 末端执行器
            lines.append(
                f'          <body name="{robot.name}_ee" pos="0 0 0.18">'
            )
            lines.append(
                f'            <geom name="{robot.name}_gripper" type="box" '
                f'size="0.03 0.03 0.05" rgba="0.9 0.3 0.2 1"/>'
            )
            lines.append(
                f'            <site name="{robot.name}_ee" pos="0 0 0" size="0.01"/>'
            )
            lines.append(f'          </body>')
            lines.append(f'        </body>')
            lines.append(f'      </body>')

            # 相机（在 worldbody 中作为渲染相机）
            if "rgbd_camera" in robot.sensors:
                lines.append(
                    f'      <camera name="{robot.name}_cam" pos="0.15 0 0.5" '
                    f'xyaxes="1 0 0 0 1 0"/>'
                )

            lines.append(f'    </body>')

        lines.append('  </worldbody>')

        # 传感器
        has_sensors = any(
            "imu" in r.sensors
            for r in scene.robots
        )
        if has_sensors:
            lines.append('  <sensor>')
            for robot in scene.robots:
                if "imu" in robot.sensors:
                    lines.append(
                        f'    <accelerometer name="{robot.name}_accel" site="{robot.name}_ee"/>'
                    )
                    lines.append(
                        f'    <gyro name="{robot.name}_gyro" site="{robot.name}_ee"/>'
                    )
            lines.append('  </sensor>')

        # 执行器
        lines.append('  <actuator>')
        for robot in scene.robots:
            lines.append(
                f'    <position name="{robot.name}_j1_act" '
                f'joint="{robot.name}_j1" kp="100"/>'
            )
            lines.append(
                f'    <position name="{robot.name}_j2_act" '
                f'joint="{robot.name}_j2" kp="100"/>'
            )
        lines.append('  </actuator>')

        lines.append('</mujoco>')
        return "\n".join(lines)
