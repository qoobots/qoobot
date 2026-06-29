"""
QooBot 双足行走控制器 — 集成 MPC + 步态规划 + 关节位置/力矩控制
"""
import numpy as np
import mujoco
from qoobot_mpc_py import QooBotMPC, compute_mpc_gait_flags
from qoobot_gait_planner import GaitScheduler, FootPlacement, RaibertHeuristic
from qoobot_wbc_py import QooBotWBC
import qoobot_robot_params as P


class QooBotWalkingController:
    """QooBot 双足行走控制器

    控制流水线:
      Sensor Read -> StateEst -> GaitScheduler -> FootPlacement -> MPC -> Torque/Position -> Actuator

    支持两种控制模式:
    - position: 关节位置 PD (稳定但较慢)
    - torque: 关节力矩控制 (需要 WBC, 更动态)
    """

    def __init__(self, model: mujoco.MjModel, data: mujoco.MjData):
        self.model = model
        self.data = data
        self.nv = model.nv
        self.nu = model.nu
        self.nq = model.nq

        # 子模块
        self.gait = GaitScheduler()
        self.foot_planner = FootPlacement()
        self.raibert = RaibertHeuristic()
        self.mpc = QooBotMPC()
        self.wbc = QooBotWBC(model)

        # 执行器索引映射
        self._build_actuator_map()

        # 控制参数
        self.step_count = 0
        self.mpc_counter = 0
        self.mpc_interval = 20  # 每 20ms 求解一次 MPC

        # 站立高度
        self.stand_height = 1.0

        # 期望速度
        self.des_vx = 0.0
        self.des_vy = 0.0
        self.des_wz = 0.0

        # 控制模式
        self.control_mode = 'position'  # 'position' or 'torque'

        # 是否启用行走
        self.walking_enabled = False

        # 摆动腿开始时的位置
        self.swing_start_pos = None

        # PD 增益
        self.kp_leg = 600.0    # 腿关节位置增益
        self.kd_leg = 30.0     # 腿关节速度增益
        self.kp_upper = 100.0  # 上半身关节增益
        self.kd_upper = 10.0

        # 支撑补偿
        self.stance_z_boost = 400.0  # 支撑腿额外 z 推力 (N), 需~380N/腿支撑77kg

    def _build_actuator_map(self):
        """构建执行器名称到索引的映射"""
        self.act_id = {}
        for aname in P.ACTUATOR_NAMES:
            aid = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_ACTUATOR, aname)
            if aid >= 0:
                self.act_id[aname] = aid

        # 构建关节名称 -> (actuator_id, joint_id, qpos_addr, dof_addr) 映射
        self.joint_info = {}
        for jname in P.JOINT_NAMES:
            if jname == 'root_joint':
                continue
            jid = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_JOINT, jname)
            if jid < 0:
                continue
            qpos_addr = self.model.jnt_qposadr[jid]
            dof_addr = self.model.jnt_dofadr[jid]

            # 找到对应执行器
            motor_name = 'M_' + jname[2:]  # J_xxx -> M_xxx
            aid = self.act_id.get(motor_name, -1)

            self.joint_info[jname] = {
                'jid': jid,
                'qpos_addr': qpos_addr,
                'dof_addr': dof_addr,
                'act_id': aid,
            }

        # 左腿关节名列表
        self.left_leg_joints = P.LEFT_LEG_JOINTS
        self.right_leg_joints = P.RIGHT_LEG_JOINTS

    def set_velocity(self, vx, vy, wz):
        """设置期望行走速度"""
        self.des_vx = vx
        self.des_vy = vy
        self.des_wz = wz
        if abs(vx) > 0.01 or abs(vy) > 0.01 or abs(wz) > 0.01:
            self.walking_enabled = True
            self.gait.set_velocity(vx, vy, wz)
            self.mpc.set_desired_velocity(vx, vy, wz)

    def stop(self):
        """停止行走"""
        self.walking_enabled = False
        self.gait.stop()
        self.mpc.set_standing()

    def toggle_control_mode(self):
        """切换控制模式"""
        if self.control_mode == 'position':
            self.control_mode = 'torque'
        else:
            self.control_mode = 'position'
        return self.control_mode

    def get_state(self):
        """读取当前状态"""
        data = self.data
        base_pos = data.qpos[0:3].copy()
        base_quat = data.qpos[3:7].copy()
        base_vel = data.qvel[0:3].copy()
        base_omega = data.qvel[3:6].copy()

        # 欧拉角
        from qoobot_wbc_py import quat_to_rotmat
        R = quat_to_rotmat(base_quat)
        roll = np.arctan2(R[2, 1], R[2, 2])
        pitch = np.arcsin(-R[2, 0])
        yaw = np.arctan2(R[1, 0], R[0, 0])

        fe_l_pos = self.wbc.get_foot_position(data, P.LEFT_FOOT_BODY)
        fe_r_pos = self.wbc.get_foot_position(data, P.RIGHT_FOOT_BODY)

        try:
            lf_touch = data.sensor(P.LF_TOUCH_SENSOR).data[0]
            rf_touch = data.sensor(P.RF_TOUCH_SENSOR).data[0]
        except Exception:
            lf_touch = rf_touch = 0.0

        f_L_est = np.array([0, 0, lf_touch * P.TOTAL_MASS * 9.81 / 2])
        f_R_est = np.array([0, 0, rf_touch * P.TOTAL_MASS * 9.81 / 2])

        return {
            'base_pos': base_pos,
            'base_quat': base_quat,
            'base_rpy': np.array([roll, pitch, yaw]),
            'base_vel': base_vel,
            'base_omega': base_omega,
            'fe_l_pos': fe_l_pos,
            'fe_r_pos': fe_r_pos,
            'f_L_est': f_L_est,
            'f_R_est': f_R_est,
        }

    def compute_leg_ik(self, foot_target_W, hip_pos_W, is_left):
        """简化腿部逆运动学 (解析解)

        5DOF 腿: hip_roll, hip_yaw, hip_pitch, knee_pitch, ankle_pitch, ankle_roll
        使用几何方法计算 hip_pitch, knee_pitch, ankle_pitch 的解析解

        Returns:
            q_leg: 6个关节角度 [hip_roll, hip_yaw, hip_pitch, knee, ankle_pitch, ankle_roll]
        """
        # 髋到足向量 (髋坐标系)
        offset = foot_target_W - hip_pos_W

        # 腿长
        L1 = 0.48  # 大腿长度 (hip 到 knee), 实测 0.4799m
        L2 = 0.387 # 小腿长度 (knee 到 ankle)

        # 侧向偏移
        hip_roll = np.arctan2(offset[1], -offset[2])

        # 在矢状面 (x-z) 中求解
        # 有效腿长 (考虑 hip_roll 旋转)
        d_xz = np.sqrt(offset[0]**2 + offset[2]**2)
        d_xz = np.clip(d_xz, 0.01, L1 + L2 - 0.01)

        # 余弦定理求 knee 角度
        cos_knee = (d_xz**2 - L1**2 - L2**2) / (2 * L1 * L2)
        cos_knee = np.clip(cos_knee, -1, 1)
        knee_angle = np.arccos(cos_knee)  # 正值 = 弯曲

        # hip_pitch: 髋到足的连线角度 + 大腿与连线夹角
        alpha = np.arctan2(-offset[0], -offset[2])  # 连线角度
        beta = np.arctan2(L2 * np.sin(knee_angle), L1 + L2 * np.cos(knee_angle))
        hip_pitch = alpha - beta

        # ankle_pitch: 保持足底水平
        ankle_pitch = -(hip_pitch + knee_angle)

        # hip_yaw: 很小
        hip_yaw = 0.0

        # ankle_roll: 保持水平
        ankle_roll = -hip_roll

        return np.array([hip_roll, hip_yaw, hip_pitch, knee_angle, ankle_pitch, ankle_roll])

    def get_hip_position(self, data, is_left):
        """获取髋关节世界位置"""
        hip_body = 'Link_hip_l_roll' if is_left else 'Link_hip_r_roll'
        body_id = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_BODY, hip_body)
        if body_id >= 0:
            return data.xpos[body_id].copy()
        # 回退: 基座 + 偏移
        base_pos = data.qpos[0:3]
        offset = np.array([-0.0875, 0.12 if is_left else -0.12, -0.069])
        return base_pos + offset

    def step(self):
        """单步控制更新"""
        self.step_count += 1

        # 1. 状态读取
        state = self.get_state()

        # 2. 步态调度
        gait_info = self.gait.update(
            state['f_L_est'], state['f_R_est'],
            state['fe_l_pos'], state['fe_r_pos']
        )

        # 3. MPC (低频)
        if self.walking_enabled and self.step_count % self.mpc_interval == 0:
            X_cur = np.concatenate([
                state['base_rpy'], state['base_pos'],
                state['base_omega'], state['base_vel']
            ])
            gait_flags = compute_mpc_gait_flags(
                gait_info['phi'], gait_info['leg_state'], P.MPC_N
            )
            self.mpc.solve(X_cur, gait_flags)

        # 4. 足端轨迹规划
        swing_foot = gait_info['swing_foot']
        phi = gait_info['phi']
        foot_targets = {}

        if swing_foot == 'left':
            # 左足摆动: 从当前位置开始
            if self.swing_start_pos is None or gait_info['leg_state'] != 'RSt':
                self.swing_start_pos = state['fe_l_pos'].copy()
            pos_W, vel_W = self.foot_planner.plan_swing_trajectory(
                phi, self.swing_start_pos, state['fe_r_pos'],
                self.des_vx, self.des_vy, self.des_wz
            )
            foot_targets['left'] = (pos_W, vel_W)
        elif swing_foot == 'right':
            if self.swing_start_pos is None or gait_info['leg_state'] != 'LSt':
                self.swing_start_pos = state['fe_r_pos'].copy()
            pos_W, vel_W = self.foot_planner.plan_swing_trajectory(
                phi, self.swing_start_pos, state['fe_l_pos'],
                self.des_vx, self.des_vy, self.des_wz
            )
            foot_targets['right'] = (pos_W, vel_W)
        else:
            self.swing_start_pos = None

        # 5. 控制输出
        if self.control_mode == 'torque':
            self._step_torque(gait_info, foot_targets, state)
        else:
            self._step_position(gait_info, foot_targets, state)

        return gait_info, state

    def _step_position(self, gait_info, foot_targets, state):
        """位置控制模式: 用 IK 计算关节目标角度，通过 MuJoCo 内置 PD"""
        data = self.data

        # 目标关节位置 (qpos 格式, 只修改关节部分)
        q_des = np.zeros(self.nq)
        q_des[0:7] = data.qpos[0:7]  # 保持基座位姿不变 (实际上我们不控制基座)

        # 默认站立姿态
        for jname in P.JOINT_NAMES:
            if jname == 'root_joint':
                continue
            info = self.joint_info.get(jname)
            if info is None:
                continue
            stand_angle = P.STAND_POSE.get(jname, 0.0)
            q_des[info['qpos_addr']] = stand_angle

        # 对摆动腿使用 IK
        swing_foot = gait_info['swing_foot']
        leg_state = gait_info['leg_state']

        if swing_foot == 'left':
            target_pos, _ = foot_targets.get('left', (np.zeros(3), np.zeros(3)))
            hip_pos = self.get_hip_position(data, is_left=True)
            q_ik = self.compute_leg_ik(target_pos, hip_pos, is_left=True)
            for i, jname in enumerate(self.left_leg_joints):
                info = self.joint_info.get(jname)
                if info:
                    q_des[info['qpos_addr']] = q_ik[i]

        elif swing_foot == 'right':
            target_pos, _ = foot_targets.get('right', (np.zeros(3), np.zeros(3)))
            hip_pos = self.get_hip_position(data, is_left=False)
            q_ik = self.compute_leg_ik(target_pos, hip_pos, is_left=False)
            for i, jname in enumerate(self.right_leg_joints):
                info = self.joint_info.get(jname)
                if info:
                    q_des[info['qpos_addr']] = q_ik[i]

        # 计算支撑腿足端雅可比，施加额外垂直力补偿
        stance_boost_tau = np.zeros(self.nv)
        leg_state = gait_info['leg_state']

        if leg_state == 'LSt' or leg_state == 'DSt':
            # 左腿支撑: 用足端雅可比施加 z 方向推力
            J_L = self.wbc.get_foot_jacobian(data, P.LEFT_FOOT_BODY)
            F_boost = np.array([0, 0, self.stance_z_boost])
            stance_boost_tau += J_L[:3, :].T @ F_boost

        if leg_state == 'RSt' or leg_state == 'DSt':
            J_R = self.wbc.get_foot_jacobian(data, P.RIGHT_FOOT_BODY)
            F_boost = np.array([0, 0, self.stance_z_boost])
            stance_boost_tau += J_R[:3, :].T @ F_boost

        # 施加位置控制 (通过 ctrl)
        for aname in P.ACTUATOR_NAMES:
            aid = self.act_id.get(aname)
            if aid is None:
                continue

            # 找到对应关节
            jname = 'J_' + aname[2:]
            info = self.joint_info.get(jname)
            if info is None:
                self.data.ctrl[aid] = 0.0
                continue

            q_des_val = q_des[info['qpos_addr']]
            q_cur = data.qpos[info['qpos_addr']]
            qd_cur = data.qvel[info['dof_addr']] if info['dof_addr'] < self.nv else 0.0

            # 位置 PD
            is_leg = jname in self.left_leg_joints or jname in self.right_leg_joints
            kp = self.kp_leg if is_leg else self.kp_upper
            kd = self.kd_leg if is_leg else self.kd_upper

            pd_torque = kp * (q_des_val - q_cur) - kd * qd_cur

            # 支撑补偿 (仅腿关节)
            if is_leg:
                boost = stance_boost_tau[info['dof_addr']] if info['dof_addr'] < self.nv else 0.0
                torque = pd_torque + boost
            else:
                torque = pd_torque

            self.data.ctrl[aid] = np.clip(torque, -396, 396)

    def _step_torque(self, gait_info, foot_targets, state):
        """力矩控制模式: WBC 计算关节力矩"""
        base_pos_des = np.array([0.0, 0.0, self.stand_height])
        base_quat_des = np.array([1.0, 0.0, 0.0, 0.0])

        tau = self.wbc.compute_torques(
            self.data, gait_info, foot_targets,
            base_pos_des, base_quat_des
        )

        # 施加力矩
        for aname in P.ACTUATOR_NAMES:
            aid = self.act_id.get(aname)
            if aid is None:
                continue
            jname = 'J_' + aname[2:]
            info = self.joint_info.get(jname)
            if info is None:
                self.data.ctrl[aid] = 0.0
                continue
            dof_addr = info['dof_addr']
            if dof_addr < self.nv:
                self.data.ctrl[aid] = np.clip(tau[dof_addr], -396, 396)
            else:
                self.data.ctrl[aid] = 0.0
