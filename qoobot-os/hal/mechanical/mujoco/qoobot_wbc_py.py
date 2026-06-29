"""
QooBot 全身控制器 (WBC) — Python 简化实现
基于 OpenLoong dyn-control 的 wbc_priority.cpp

使用 Null-Space 投影的优先级任务方法：
  P1: 支撑足接触约束
  P2: 基座位姿跟踪
  P3: 摆动足轨迹跟踪
  P4: 冗余关节归零
"""
import numpy as np
import mujoco
import qoobot_robot_params as P


def quat_to_rotmat(quat):
    """四元数转旋转矩阵 (w, x, y, z) -> (3x3)"""
    w, x, y, z = quat[0], quat[1], quat[2], quat[3]
    R = np.array([
        [1 - 2*y*y - 2*z*z, 2*x*y - 2*w*z, 2*x*z + 2*w*y],
        [2*x*y + 2*w*z, 1 - 2*x*x - 2*z*z, 2*y*z - 2*w*x],
        [2*x*z - 2*w*y, 2*y*z + 2*w*x, 1 - 2*x*x - 2*y*y]
    ])
    return R


def skew(v):
    """3x3 反对称矩阵"""
    return np.array([
        [0, -v[2], v[1]],
        [v[2], 0, -v[0]],
        [-v[1], v[0], 0]
    ])


def rotation_error(R_cur, R_des):
    """计算旋转误差 (so(3))"""
    R_err = R_des.T @ R_cur
    # 从旋转矩阵提取轴角
    theta = np.arccos(np.clip((np.trace(R_err) - 1) / 2, -1, 1))
    if abs(theta) < 1e-6:
        return np.zeros(3)
    axis = np.array([
        R_err[2, 1] - R_err[1, 2],
        R_err[0, 2] - R_err[2, 0],
        R_err[1, 0] - R_err[0, 1]
    ]) / (2 * np.sin(theta))
    return theta * axis


class QooBotWBC:
    """QooBot 全身控制器 (简化 WBC)

    使用解析 Null-Space 投影而非 QP 求解，大幅简化计算。
    控制策略：
      1. 支撑足零加速度约束
      2. 基座位姿 PD 跟踪
      3. 摆动足轨迹 PD 跟踪
      4. 通过伪逆映射到关节力矩
    """

    def __init__(self, model: mujoco.MjModel):
        self.model = model
        self.nv = model.nv
        self.nu = model.nu
        self.dt = model.opt.timestep

        # 关节 DOF 地址映射
        self._build_joint_map()

        # 腿关节索引 (在 qpos 中的位置，排除浮动基座)
        self.leg_joint_ids = []
        for jname in P.LEFT_LEG_JOINTS + P.RIGHT_LEG_JOINTS:
            jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, jname)
            if jid >= 0:
                self.leg_joint_ids.append(jid)

        # PD 增益
        self.kp_base_pos = 200.0
        self.kd_base_pos = 20.0
        self.kp_base_rot = 500.0
        self.kd_base_rot = 50.0
        self.kp_swing = 500.0
        self.kd_swing = 30.0
        self.kp_posture = 100.0
        self.kd_posture = 10.0

        # 期望站立关节角度
        self.q_des_stand = np.zeros(self.nv)
        for jname, angle in P.STAND_POSE.items():
            jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, jname)
            if jid >= 0:
                dof_addr = model.jnt_dofadr[jid]
                if dof_addr >= 0:
                    self.q_des_stand[dof_addr] = angle

    def _build_joint_map(self):
        """构建关节名称到 DOF 地址的映射"""
        self.joint_dof_map = {}
        for jname in P.JOINT_NAMES:
            jid = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_JOINT, jname)
            if jid >= 0:
                self.joint_dof_map[jname] = self.model.jnt_dofadr[jid]

    def get_foot_jacobian(self, data, foot_body_name):
        """计算足端雅可比矩阵 (6 x nv)"""
        body_id = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_BODY, foot_body_name)
        if body_id < 0:
            return np.zeros((6, self.nv))

        jacp = np.zeros((3, self.nv))
        jacr = np.zeros((3, self.nv))
        point = np.zeros(3)
        mujoco.mj_jac(self.model, data, jacp, jacr, point, body_id)

        J = np.zeros((6, self.nv))
        J[0:3, :] = jacp
        J[3:6, :] = jacr
        return J

    def get_foot_jacobian_dot(self, data, foot_body_name):
        """计算足端雅可比导数 dJ * dq"""
        body_id = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_BODY, foot_body_name)
        if body_id < 0:
            return np.zeros(6)

        djacp = np.zeros((3, self.nv))
        djacr = np.zeros((3, self.nv))
        point = np.zeros(3)
        mujoco.mj_jacDot(self.model, data, djacp, djacr, point, body_id)

        dJdq = np.zeros(6)
        dq = data.qvel
        dJdq[0:3] = djacp @ dq
        dJdq[3:6] = djacr @ dq
        return dJdq

    def get_foot_position(self, data, foot_body_name):
        """获取足端世界位置"""
        body_id = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_BODY, foot_body_name)
        if body_id < 0:
            return np.zeros(3)
        return data.xpos[body_id].copy()

    def get_foot_velocity(self, data, foot_body_name):
        """获取足端世界速度"""
        J = self.get_foot_jacobian(data, foot_body_name)
        return J[:3, :] @ data.qvel

    def compute_torques(self, data, gait_info, foot_targets,
                         base_pos_des=None, base_quat_des=None):
        """计算关节力矩 (WBC 核心)

        Args:
            data: MuJoCo MjData
            gait_info: 步态状态 dict (from GaitScheduler.update)
            foot_targets: dict {'left': (pos, vel), 'right': (pos, vel)}
            base_pos_des: 期望基座位置 [3] (可选)
            base_quat_des: 期望基座姿态 [w,x,y,z] (可选)

        Returns:
            tau: 关节力矩 [nv] (前6维为基座力矩, 置零)
        """
        nv = self.nv
        dq = data.qvel

        # --- 1. 计算质量矩阵 M 和非线性项 ---
        M = np.zeros((nv, nv))
        mujoco.mj_fullM(self.model, data, M)
        # 使 M 对称化
        M = 0.5 * (M + M.T)
        # Non = C(q,dq)*dq + g(q)
        Non = data.qfrc_bias.copy()

        # --- 2. 计算足端雅可比 ---
        J_L = self.get_foot_jacobian(data, P.LEFT_FOOT_BODY)
        J_R = self.get_foot_jacobian(data, P.RIGHT_FOOT_BODY)
        dJdq_L = self.get_foot_jacobian_dot(data, P.LEFT_FOOT_BODY)
        dJdq_R = self.get_foot_jacobian_dot(data, P.RIGHT_FOOT_BODY)

        # --- 3. 接触约束雅可比 ---
        leg_state = gait_info['leg_state']
        if leg_state == 'LSt':
            # 左支撑: J_c = J_L
            J_c = J_L
            dJdq_c = dJdq_L
            nc = 6
        elif leg_state == 'RSt':
            # 右支撑: J_c = J_R
            J_c = J_R
            dJdq_c = dJdq_R
            nc = 6
        else:
            # 双支撑: J_c = [J_L; J_R]
            J_c = np.vstack([J_L, J_R])
            dJdq_c = np.hstack([dJdq_L, dJdq_R])
            nc = 12

        # --- 4. 构建任务 ---
        # 基座任务 (6维: pos + rot)
        base_pos_cur = data.qpos[0:3].copy()
        base_quat_cur = data.qpos[3:7].copy()

        if base_pos_des is None:
            base_pos_des = np.array([0.0, 0.0, 1.0])
        if base_quat_des is None:
            base_quat_des = np.array([1.0, 0.0, 0.0, 0.0])

        # 基座误差
        pos_err = base_pos_des - base_pos_cur
        vel_err = -dq[0:3]  # 期望速度 = 0

        R_cur = quat_to_rotmat(base_quat_cur)
        R_des = quat_to_rotmat(base_quat_des)
        rot_err = rotation_error(R_cur, R_des)
        omega_err = -dq[3:6]

        # 基座任务雅可比 (前6 DOF 为单位阵)
        J_base = np.zeros((6, nv))
        J_base[:6, :6] = np.eye(6)

        # 基座期望加速度
        ddx_base_des = np.zeros(6)
        ddx_base_des[0:3] = self.kp_base_pos * pos_err + self.kd_base_pos * vel_err
        ddx_base_des[3:6] = self.kp_base_rot * rot_err + self.kd_base_rot * omega_err

        # --- 5. 摆动足任务 ---
        swing_foot = gait_info['swing_foot']
        if swing_foot == 'left':
            J_swing = J_L
            dJdq_swing = dJdq_L
            target_pos, target_vel = foot_targets.get('left', (np.zeros(3), np.zeros(3)))
        elif swing_foot == 'right':
            J_swing = J_R
            dJdq_swing = dJdq_R
            target_pos, target_vel = foot_targets.get('right', (np.zeros(3), np.zeros(3)))
        else:
            J_swing = None

        # --- 6. Null-Space 投影求解 ---
        # 使用 Operational Space Formulation
        # 约束动力学方程:
        #   J_c * ddq + dJdq_c = 0
        #   M * ddq + Non = J_c^T * F_c + tau_task
        #
        # 从约束方程解出 ddq:
        #   ddq = M^{-1} * (J_c^T * F_c + tau_task - Non)
        #
        # 代入 J_c * ddq + dJdq_c = 0:
        #   J_c * M^{-1} * J_c^T * F_c = J_c * M^{-1} * (Non - tau_task) - dJdq_c

        # 计算操作空间惯量
        M_inv = np.linalg.inv(M + 1e-6 * np.eye(nv))

        # Lambda_c = (J_c * M^{-1} * J_c^T)^{-1}
        Lambda_c_inv = J_c @ M_inv @ J_c.T
        Lambda_c = np.linalg.inv(Lambda_c_inv + 1e-6 * np.eye(nc))

        # 约束一致的操作空间投影
        # P_c = I - J_c^T * Lambda_c * J_c * M^{-1}
        P_c = np.eye(nv) - J_c.T @ Lambda_c @ J_c @ M_inv

        # 约束力矩: 确保 J_c * ddq + dJdq_c = 0
        tau_c = J_c.T @ Lambda_c @ (J_c @ M_inv @ Non - dJdq_c)

        # --- 7. 任务力矩 ---
        # 基座任务
        tau_base = J_base.T @ ddx_base_des

        # 摆动足任务
        if J_swing is not None:
            swing_pos_cur = self.get_foot_position(data,
                P.LEFT_FOOT_BODY if swing_foot == 'left' else P.RIGHT_FOOT_BODY)
            swing_vel_cur = self.get_foot_velocity(data,
                P.LEFT_FOOT_BODY if swing_foot == 'left' else P.RIGHT_FOOT_BODY)

            pos_err_swing = target_pos - swing_pos_cur
            vel_err_swing = target_vel - swing_vel_cur
            ddx_swing_des = self.kp_swing * pos_err_swing + self.kd_swing * vel_err_swing
            tau_swing = J_swing[:3, :].T @ ddx_swing_des
        else:
            tau_swing = np.zeros(nv)

        # --- 8. 组合力矩 ---
        # 总力矩: tau = Non + tau_c + P_c * (tau_base + tau_swing)
        tau_total = Non + tau_c + P_c @ (tau_base + tau_swing)

        # 基座力矩置零 (只返回关节力矩)
        tau_total[:6] = 0.0

        # 力矩限制
        tau_max = 396.0  # Nm (对应 ctrlrange 最大的腿关节)
        tau_total = np.clip(tau_total, -tau_max, tau_max)

        return tau_total

    def compute_simple_pd(self, data, gait_info, foot_targets,
                           base_pos_des=None, base_quat_des=None):
        """改进的 PD+前馈控制

        策略:
        1. 支撑腿: 关节 PD 保持站立姿态 + 踝关节前馈产生推进力
        2. 摆动腿: 足端阻抗控制 (通过雅可比逆映射到关节力矩)
        3. 基座高度 PD 控制 (通过髋/膝/踝关节)
        4. 所有关节阻尼
        """
        nv = self.nv
        qpos = data.qpos
        qvel = data.qvel

        tau = np.zeros(nv)

        # --- 基座高度 PD ---
        base_z_cur = qpos[2]
        base_z_des = 1.0 if base_pos_des is None else base_pos_des[2]
        z_err = base_z_des - base_z_cur
        z_vel = qvel[2]
        kp_z = 500.0
        kd_z = 100.0
        f_z_des = kp_z * z_err - kd_z * z_vel  # 期望总法向力

        # 分配到双腿
        f_z_per_leg = max(0, f_z_des / 2.0)

        # --- 前向推力 ---
        base_vx = qvel[0]
        kp_vx = 100.0
        kd_vx = 50.0
        f_x_des = kp_vx * (0.0 - base_vx)  # 阻尼水平速度，阻止漂移

        leg_state = gait_info['leg_state']
        swing_foot = gait_info['swing_foot']

        # 左右腿关节 PD + 足端力映射
        for leg_side, leg_joints, foot_body in [
            ('left', P.LEFT_LEG_JOINTS, P.LEFT_FOOT_BODY),
            ('right', P.RIGHT_LEG_JOINTS, P.RIGHT_FOOT_BODY)
        ]:
            is_stance = (
                (leg_state == 'DSt') or
                (leg_state == 'LSt' and leg_side == 'left') or
                (leg_state == 'RSt' and leg_side == 'right')
            )

            if is_stance:
                # 支撑腿: 关节 PD + 足端力映射
                J_foot = self.get_foot_jacobian(data, foot_body)
                J_lin = J_foot[:3, 6:]  # 仅关节部分 (去掉基座前6列)

                # 期望足端力 (世界系)
                F_des = np.array([f_x_des / 2, 0.0, f_z_per_leg])

                # 映射到关节力矩: tau = J^T * F
                tau_foot = J_lin.T @ F_des
                tau[6:] += tau_foot

                # 同时施加关节 PD 维持姿态
                for jname in leg_joints:
                    dof_addr = self.joint_dof_map.get(jname)
                    if dof_addr is None:
                        continue
                    q_cur = qpos[dof_addr]
                    qd_cur = qvel[dof_addr]
                    q_des = self.q_des_stand[dof_addr]
                    tau[dof_addr] += self.kp_posture * (q_des - q_cur)
                    tau[dof_addr] -= self.kd_posture * qd_cur

            elif swing_foot == leg_side:
                # 摆动腿: 足端阻抗控制
                target_pos, target_vel = foot_targets.get(leg_side,
                    (np.zeros(3), np.zeros(3)))

                J_foot = self.get_foot_jacobian(data, foot_body)
                J_lin = J_foot[:3, 6:]

                foot_pos = self.get_foot_position(data, foot_body)
                foot_vel = self.get_foot_velocity(data, foot_body)

                pos_err = target_pos - foot_pos
                vel_err = target_vel - foot_vel

                # 足端虚拟力
                F_swing = self.kp_swing * pos_err + self.kd_swing * vel_err

                # 映射到关节力矩
                tau_swing = J_lin.T @ F_swing
                tau[6:] += tau_swing

                # 加关节阻尼
                for jname in leg_joints:
                    dof_addr = self.joint_dof_map.get(jname)
                    if dof_addr is None:
                        continue
                    tau[dof_addr] -= self.kd_posture * qvel[dof_addr]

        # 上半身关节 PD 归零
        upper_joints = [
            'J_head_yaw', 'J_head_pitch',
            'J_waist_pitch', 'J_waist_roll', 'J_waist_yaw',
            'J_arm_l_01', 'J_arm_l_02', 'J_arm_l_03', 'J_arm_l_04',
            'J_arm_l_05', 'J_arm_l_06', 'J_arm_l_07',
            'J_arm_r_01', 'J_arm_r_02', 'J_arm_r_03', 'J_arm_r_04',
            'J_arm_r_05', 'J_arm_r_06', 'J_arm_r_07',
        ]
        for jname in upper_joints:
            dof_addr = self.joint_dof_map.get(jname)
            if dof_addr is None:
                continue
            q_cur = qpos[dof_addr]
            qd_cur = qvel[dof_addr]
            q_des = self.q_des_stand[dof_addr]
            tau[dof_addr] = self.kp_posture * (q_des - q_cur) - self.kd_posture * qd_cur

        # 力矩限制
        tau_max = 396.0
        tau = np.clip(tau, -tau_max, tau_max)
        return tau
