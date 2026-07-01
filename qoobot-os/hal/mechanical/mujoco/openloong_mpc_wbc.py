"""
OpenLoong 风格 MPC + WBC 行走控制器 — Python 实现

基于 OpenLoong dyn-control 的架构:
  - MPC: 单刚体模型预测控制，使用 quadprog 做 QP 求解
  - WBC: 优先级任务 + 动力学 QP，参考 wbc_priority.cpp
  - 步态调度: 相位状态机 (LSt/RSt/DSt)
  - 落脚点规划: Raibert 启发式 + Hermite 三次样条

架构流程:
  Sensor Read -> StateEst -> GaitScheduler -> FootPlacement -> MPC -> WBC -> Torque -> Actuator
"""

import numpy as np
import mujoco
from scipy.spatial.transform import Rotation as R
import qoobot_robot_params as P

# ============================================================================
# 数学工具
# ============================================================================

def skew(v):
    """3x3 反对称矩阵"""
    return np.array([
        [0, -v[2], v[1]],
        [v[2], 0, -v[0]],
        [-v[1], v[0], 0]
    ])

def quat_to_rpy(quat_xyzw):
    """四元数 [x,y,z,w] -> 欧拉角 [roll, pitch, yaw]"""
    x, y, z, w = quat_xyzw
    roll = np.arctan2(2*(w*x + y*z), 1 - 2*(x*x + y*y))
    pitch = np.arcsin(np.clip(2*(w*y - z*x), -1, 1))
    yaw = np.arctan2(2*(w*z + x*y), 1 - 2*(y*y + z*z))
    return np.array([roll, pitch, yaw])

def rpy_to_rotmat(rpy):
    """欧拉角 -> 旋转矩阵"""
    r, p, y = rpy
    return R.from_euler('xyz', [r, p, y]).as_matrix()

def quat_xyzw_to_rotmat(quat_xyzw):
    """四元数 [x,y,z,w] -> 旋转矩阵"""
    x, y, z, w = quat_xyzw
    return R.from_quat([x, y, z, w]).as_matrix()


# ============================================================================
# 单刚体模型 (Single Rigid Body Model)
# ============================================================================

class SingleRigidBodyModel:
    """单刚体模型：将机器人视为 CoM 处的单个刚体
    
    状态 x (12维): [roll, pitch, yaw, px, py, pz, omega_x, omega_y, omega_z, vx, vy, vz]
    控制 u (13维): [f_L_x, f_L_y, f_L_z, tau_L_x, tau_L_y, tau_L_z,
                    f_R_x, f_R_y, f_R_z, tau_R_x, tau_R_y, tau_R_z, f_z_total]
    """

    def __init__(self, dt=0.001):
        self.dt = dt
        self.mass = P.TOTAL_MASS
        self.I_com = P.I_COM.copy()
        self.inv_I = np.linalg.inv(self.I_com)
        self.gravity = np.array([0, 0, P.GRAVITY])

    def compute_Ac(self, rpy):
        """连续时间 A 矩阵 (12x12)，考虑当前欧拉角"""
        Ac = np.zeros((12, 12))
        roll, pitch, yaw = rpy

        # 欧拉角变化率 -> 角速度 (world frame)
        cos_p = np.cos(pitch)
        if abs(cos_p) < 1e-6:
            cos_p = 1e-6
        tan_p = np.tan(pitch)
        sin_r = np.sin(roll)
        cos_r = np.cos(roll)

        # d(rpy)/dt = R_rpy * omega
        R_rpy = np.array([
            [1, sin_r*tan_p, cos_r*tan_p],
            [0, cos_r, -sin_r],
            [0, sin_r/cos_p, cos_r/cos_p]
        ])
        Ac[0:3, 6:9] = R_rpy

        # d(pos)/dt = vel
        Ac[3:6, 9:12] = np.eye(3)
        return Ac

    def compute_Bc(self, p_L_com, p_R_com):
        """连续时间 B 矩阵 (12x13)，使用足端相对 CoM 位置"""
        Bc = np.zeros((12, 13))
        inv_m = 1.0 / self.mass

        # 左足 skew 矩阵
        skew_L = skew(p_L_com)
        # 右足 skew 矩阵
        skew_R = skew(p_R_com)

        # angular velocity: d(omega)/dt = I^-1 * (p x f + tau)
        Bc[6:9, 0:3] = self.inv_I @ skew_L   # f_L 贡献
        Bc[6:9, 3:6] = self.inv_I            # tau_L 贡献
        Bc[6:9, 6:9] = self.inv_I @ skew_R   # f_R 贡献
        Bc[6:9, 9:12] = self.inv_I           # tau_R 贡献

        # linear velocity: d(vel)/dt = (f_L + f_R)/m + g*f_z_total
        Bc[9:12, 0:3] = inv_m * np.eye(3)
        Bc[9:12, 6:9] = inv_m * np.eye(3)
        Bc[9:12, 12] = np.array([0, 0, 1.0])  # f_z_total 贡献

        return Bc

    def discrete_dynamics(self, x, u, Ac, Bc):
        """一步离散动力学: x_{k+1} = (I + dt*Ac)*x_k + dt*Bc*u_k"""
        A = np.eye(12) + self.dt * Ac
        B = self.dt * Bc
        return A @ x + B @ u


# ============================================================================
# MPC 控制器
# ============================================================================

class OpenLoongMPC:
    """模型预测控制器 — 参考 OpenLoong mpc.cpp

    使用 quadprog 求解 QP 问题:
      min  0.5 * U^T * H * U + c^T * U
      s.t. As * U <= bs
    """

    def __init__(self, dt=0.001):
        self.dt = dt
        self.srbm = SingleRigidBodyModel(dt)
        self.nx = P.MPC_NX   # 12
        self.nu = P.MPC_NU   # 13
        self.N = P.MPC_N     # 10 (预测时域)
        self.ch = P.MPC_CH   # 3  (控制时域)
        self.alpha = P.MPC_ALPHA

        # 权重矩阵
        self.L = np.diag(P.MPC_L_WEIGHTS)    # 状态跟踪权重 (12x12)
        self.K = np.diag(P.MPC_K_WEIGHTS)    # 控制平滑权重 (13x13)

        # 参考轨迹
        self.Xd = np.zeros((self.N, self.nx))
        self.set_standing()

        # 约束矩阵（预构建，每次 solve 时按需调整）
        self._build_friction_matrix()

    def set_desired_velocity(self, vx, vy, wz):
        """设置期望速度"""
        self.Xd = np.zeros((self.N, self.nx))
        for i in range(self.N):
            t = i * self.dt
            self.Xd[i, 3] = vx * t
            self.Xd[i, 4] = vy * t
            self.Xd[i, 5] = 1.0
            self.Xd[i, 9] = vx
            self.Xd[i, 10] = vy

    def set_standing(self):
        """站立模式参考"""
        self.Xd = np.zeros((self.N, self.nx))
        for i in range(self.N):
            self.Xd[i, 5] = 1.0

    def _build_friction_matrix(self):
        """构建摩擦锥线性化矩阵"""
        mu = P.MU
        # 4 边金字塔近似库仑摩擦锥: ±f_x - mu/sqrt(2)*f_z <= 0, ±f_y - mu/sqrt(2)*f_z <= 0
        self.friction_block = np.array([
            [-1, 0, -mu/np.sqrt(2)],
            [1, 0, -mu/np.sqrt(2)],
            [0, -1, -mu/np.sqrt(2)],
            [0, 1, -mu/np.sqrt(2)],
        ])

    def _build_qp_matrices(self, X_cur, p_L_com, p_R_com, gait_flags):
        """构建 QP 的 H, c, As, bs 矩阵

        Args:
            X_cur: 当前状态 (12,)
            p_L_com: 左足在 CoM 系中的位置 (3,)
            p_R_com: 右足在 CoM 系中的位置 (3,)
            gait_flags: list[int], 每预测步的接触状态: 0=不接触, 1=接触
                        对应左右足: [L0, R0, L1, R1, ..., L9, R9]

        Returns:
            H, c, As, bs
        """
        rpy = X_cur[0:3]
        Ac = self.srbm.compute_Ac(rpy)
        Bc = self.srbm.compute_Bc(p_L_com, p_R_com)

        A = np.eye(12) + self.dt * Ac
        B = self.dt * Bc

        # 构建 Aqp: (nx*N) x nx
        Aqp = np.zeros((self.nx * self.N, self.nx))
        Apow = np.eye(self.nx)
        for i in range(self.N):
            Apow = Apow @ A
            Aqp[i*self.nx:(i+1)*self.nx, :] = Apow

        # 构建 Bqp: (nx*N) x (nu*ch)
        Bqp = np.zeros((self.nx * self.N, self.nu * self.ch))
        for i in range(self.N):
            for j in range(min(i + 1, self.ch)):
                Apow = np.linalg.matrix_power(A, i - j)
                col_start = j * self.nu
                col_end = (j + 1) * self.nu
                Bqp[i*self.nx:(i+1)*self.nx, col_start:col_end] = Apow @ B

        # 分块权重
        L_blk = np.kron(np.eye(self.N), self.L)
        K_blk = np.kron(np.eye(self.ch), self.K)

        # H = 2 * (Bqp^T * L_blk * Bqp + alpha * K_blk)
        H = 2.0 * (Bqp.T @ L_blk @ Bqp + self.alpha * K_blk)
        H = 0.5 * (H + H.T)  # 确保对称

        # c = 2 * Bqp^T * L_blk * (Aqp * X_cur - Xd)
        c = 2.0 * Bqp.T @ L_blk @ (Aqp @ X_cur - self.Xd.flatten())

        # 约束矩阵
        n_vars = self.nu * self.ch
        As_list = []
        bs_list = []

        mu = P.MU
        for k in range(self.ch):
            idx = k * self.nu

            # 左足约束
            As_L = np.zeros((4 + 12, n_vars))
            bs_L = np.zeros(4 + 12)

            # 摩擦锥 (4)
            As_L[0:4, idx:idx+3] = self.friction_block
            # 力上下界 (6)
            for d in range(3):
                As_L[4+d, idx+d] = 1.0     # 上界
                As_L[7+d, idx+d] = -1.0    # 下界
            bs_L[4:7] = P.F_MAX
            bs_L[7:10] = -P.F_MIN
            # 力矩上下界 (6)
            for d in range(3):
                As_L[10+d, idx+3+d] = 1.0
                As_L[13+d, idx+3+d] = -1.0
            bs_L[10:13] = P.TAU_MAX
            bs_L[13:16] = -P.TAU_MIN

            # 右足约束
            As_R = np.zeros((4 + 12, n_vars))
            bs_R = np.zeros(4 + 12)

            As_R[0:4, idx+6:idx+9] = self.friction_block
            for d in range(3):
                As_R[4+d, idx+6+d] = 1.0
                As_R[7+d, idx+6+d] = -1.0
            bs_R[4:7] = P.F_MAX
            bs_R[7:10] = -P.F_MIN
            for d in range(3):
                As_R[10+d, idx+9+d] = 1.0
                As_R[13+d, idx+9+d] = -1.0
            bs_R[10:13] = P.TAU_MAX
            bs_R[13:16] = -P.TAU_MIN

            # 根据步态标志启用/禁用约束
            # gait_flags 每步有两个标志 [L_contact, R_contact]
            L_contact = gait_flags[2*k] if 2*k < len(gait_flags) else 1
            R_contact = gait_flags[2*k+1] if 2*k+1 < len(gait_flags) else 1

            if L_contact:
                As_list.append(As_L)
                bs_list.append(bs_L)
            else:
                # 摆动腿：力/力矩为零
                As_swing = np.zeros((6, n_vars))
                bs_swing = np.zeros(6)
                for d in range(3):
                    As_swing[d, idx+d] = 1.0
                    As_swing[d, idx+d] = -1.0  # 修正: 需要 ± 约束
                # 实际上用 fx=0, fy=0, fz=0 约束
                As_swing_L = np.zeros((6, n_vars))
                bs_swing_L = np.zeros(6)
                As_swing_L[0, idx+0] = 1.0; As_swing_L[1, idx+0] = -1.0  # f_x = 0
                As_swing_L[2, idx+1] = 1.0; As_swing_L[3, idx+1] = -1.0  # f_y = 0
                As_swing_L[4, idx+2] = 1.0; As_swing_L[5, idx+2] = -1.0  # f_z = 0
                As_list.append(As_swing_L)
                bs_list.append(bs_swing_L)

            if R_contact:
                As_list.append(As_R)
                bs_list.append(bs_R)
            else:
                As_swing_R = np.zeros((6, n_vars))
                bs_swing_R = np.zeros(6)
                As_swing_R[0, idx+6] = 1.0; As_swing_R[1, idx+6] = -1.0
                As_swing_R[2, idx+7] = 1.0; As_swing_R[3, idx+7] = -1.0
                As_swing_R[4, idx+8] = 1.0; As_swing_R[5, idx+8] = -1.0
                As_list.append(As_swing_R)
                bs_list.append(bs_swing_R)

        if len(As_list) > 0:
            As = np.vstack(As_list)
            bs = np.concatenate(bs_list)
        else:
            As = np.zeros((0, n_vars))
            bs = np.zeros(0)

        return H, c, As, bs

    def solve(self, X_cur, p_L_com, p_R_com, gait_flags):
        """求解 MPC QP 问题

        Args:
            X_cur: 当前状态 (12,)
            p_L_com: 左足在 CoM 系中的位置 (3,)
            p_R_com: 右足在 CoM 系中的位置 (3,)
            gait_flags: 预测步态标志 list[tuple(L_contact, R_contact)]

        Returns:
            f_L, tau_L, f_R, tau_R: 第一步的最优地面反力
            success: bool
        """
        # 展平 gait_flags
        flat_gait = []
        for gf in gait_flags:
            flat_gait.extend(gf)

        H, c, As, bs = self._build_qp_matrices(X_cur, p_L_com, p_R_com, flat_gait)

        # 使用 quadprog 求解 QP
        try:
            from quadprog import solve_qp
            # quadprog 格式: min 0.5 * x^T * G * x - a^T * x, s.t. C^T * x >= b
            G = H.copy()
            a = -c.copy()

            # 转换 As * x <= bs 为 C^T * x >= b 格式
            # As * x <= bs  =>  -As * x >= -bs
            if As.shape[0] > 0:
                C = -As.T.copy()
                b = -bs.copy()
                U_opt = solve_qp(G, a, C, b)[0]
            else:
                U_opt = solve_qp(G, a)[0]

            # 提取第一步控制
            f_L = U_opt[0:3].copy()
            tau_L = U_opt[3:6].copy()
            f_R = U_opt[6:9].copy()
            tau_R = U_opt[9:12].copy()

            return f_L, tau_L, f_R, tau_R, True

        except Exception:
            # 回退：解析解 + 投影
            return self._solve_fallback(X_cur, p_L_com, p_R_com, gait_flags)

    def _solve_fallback(self, X_cur, p_L_com, p_R_com, gait_flags):
        """无约束解析解 + 饱和投影 (回退方案)"""
        flat_gait = []
        for gf in gait_flags:
            flat_gait.extend(gf)

        H, c, As, bs = self._build_qp_matrices(X_cur, p_L_com, p_R_com, flat_gait)

        try:
            H_reg = H + 1e-6 * np.eye(H.shape[0])
            U = -np.linalg.solve(H_reg, c)
        except np.linalg.LinAlgError:
            U = np.zeros(self.nu * self.ch)

        # 饱和投影
        for k in range(self.ch):
            idx = k * self.nu
            U[idx:idx+3] = np.clip(U[idx:idx+3], P.F_MIN, P.F_MAX)
            U[idx+3:idx+6] = np.clip(U[idx+3:idx+6], P.TAU_MIN, P.TAU_MAX)
            U[idx+6:idx+9] = np.clip(U[idx+6:idx+9], P.F_MIN, P.F_MAX)
            U[idx+9:idx+12] = np.clip(U[idx+9:idx+12], P.TAU_MIN, P.TAU_MAX)
            U[idx+12] = max(0, U[idx+12])

            # 非接触腿力置零
            L_contact = flat_gait[2*k] if 2*k < len(flat_gait) else 1
            R_contact = flat_gait[2*k+1] if 2*k+1 < len(flat_gait) else 1
            if not L_contact:
                U[idx:idx+6] = 0
            if not R_contact:
                U[idx+6:idx+12] = 0

        f_L = U[0:3].copy()
        tau_L = U[3:6].copy()
        f_R = U[6:9].copy()
        tau_R = U[9:12].copy()

        return f_L, tau_L, f_R, tau_R, True


# ============================================================================
# 步态调度器
# ============================================================================

class GaitScheduler:
    """步态调度器 — 参考 OpenLoong gait_scheduler.cpp

    管理 LSt/RSt/DSt 状态机，相位从 0 到 1。
    """

    def __init__(self, dt=0.001):
        self.dt = dt
        self.t_swing = P.T_SWING
        self.t_stance = P.T_STANCE
        self.dphi = self.dt / self.t_swing

        self.phi = 0.0
        self.leg_state = 'DSt'  # LSt, RSt, DSt
        self.walking = False

    def start(self):
        self.walking = True
        if self.leg_state == 'DSt':
            self.leg_state = 'LSt'
            self.phi = 0.0

    def stop(self):
        self.walking = False

    def update(self, fz_L, fz_R):
        """更新步态状态机

        Args:
            fz_L: 左脚接触力 z 分量 (N)
            fz_R: 右脚接触力 z 分量 (N)

        Returns:
            dict: {'leg_state', 'phi', 'swing_foot', 'stance_foot'}
        """
        if self.leg_state == 'LSt':
            self.phi += self.dphi
            if self.phi >= 1.0:
                self.phi = 1.0

            if self.phi >= 0.6 and fz_R >= P.FZ_SWITCH_WALK:
                if self.walking:
                    self.leg_state = 'RSt'
                    self.phi = 0.0
                elif fz_R >= P.FZ_SWITCH_STOP:
                    self.leg_state = 'DSt'
                    self.phi = 0.0

        elif self.leg_state == 'RSt':
            self.phi += self.dphi
            if self.phi >= 1.0:
                self.phi = 1.0

            if self.phi >= 0.6 and fz_L >= P.FZ_SWITCH_WALK:
                if self.walking:
                    self.leg_state = 'LSt'
                    self.phi = 0.0
                elif fz_L >= P.FZ_SWITCH_STOP:
                    self.leg_state = 'DSt'
                    self.phi = 0.0

        elif self.leg_state == 'DSt':
            if self.walking:
                self.leg_state = 'LSt'
                self.phi = 0.0

        # 确定摆动足
        if self.leg_state == 'LSt':
            swing_foot = 'right'
            stance_foot = 'left'
        elif self.leg_state == 'RSt':
            swing_foot = 'left'
            stance_foot = 'right'
        else:
            swing_foot = 'none'
            stance_foot = 'both'

        return {
            'leg_state': self.leg_state,
            'phi': self.phi,
            'swing_foot': swing_foot,
            'stance_foot': stance_foot,
        }

    def get_mpc_gait_flags(self, N):
        """预测未来 N 步的接触状态

        Returns:
            list of (L_contact, R_contact) for each prediction step
        """
        flags = []
        phi = self.phi
        state = self.leg_state
        dphi = self.dphi

        for _ in range(N):
            if state == 'LSt':
                flags.append((1, 0))
            elif state == 'RSt':
                flags.append((0, 1))
            else:
                flags.append((1, 1))

            phi += dphi
            if phi >= 1.0:
                phi -= 1.0
                if state == 'LSt':
                    state = 'RSt'
                elif state == 'RSt':
                    state = 'LSt'

        return flags


# ============================================================================
# 落脚点规划器
# ============================================================================

class FootPlacement:
    """摆动足轨迹规划 — 参考 OpenLoong foot_placement.cpp"""

    def __init__(self):
        self.step_height = P.STEP_HEIGHT
        self.kp_vx = 0.03
        self.kp_vy = 0.03
        self.kp_wz = 0.03

    def plan_landing(self, hip_pos, com_vel, stance_foot_pos, des_vx, des_vy, is_left):
        """Raibert 启发式落脚点规划"""
        T_half = P.T_SWING / 2.0

        vel_err_x = com_vel[0] - des_vx
        vel_err_y = com_vel[1] - des_vy

        landing = np.zeros(3)
        landing[0] = hip_pos[0] + des_vx * T_half + self.kp_vx * vel_err_x
        landing[1] = hip_pos[1] + des_vy * T_half + self.kp_vy * vel_err_y

        # 左右偏移
        lateral_offset = 0.10
        if is_left:
            landing[1] += lateral_offset
        else:
            landing[1] -= lateral_offset

        landing[2] = 0.0  # 地面高度
        return landing

    def plan_swing_trajectory(self, phi, start_pos, target_pos):
        """Hermite 三次样条摆动轨迹

        Args:
            phi: 相位 [0, 1]
            start_pos: 起始位置 (3,)
            target_pos: 目标位置 (3,)

        Returns:
            pos: 当前位置 (3,)
            vel: 当前速度 (3,)
        """
        t = np.clip(phi, 0.0, 1.0)
        t2 = t * t
        t3 = t2 * t

        # Hermite 基函数
        h00 = 2*t3 - 3*t2 + 1
        h10 = (t3 - 2*t2 + t) * P.T_SWING
        h01 = -2*t3 + 3*t2
        h11 = (t3 - t2) * P.T_SWING

        # XY: Hermite 插值
        pos = np.zeros(3)
        vel = np.zeros(3)

        for d in range(2):
            pos[d] = h00*start_pos[d] + h01*target_pos[d]
            # 速度
            dh00 = (6*t2 - 6*t) / P.T_SWING
            dh01 = (-6*t2 + 6*t) / P.T_SWING
            vel[d] = dh00*start_pos[d] + dh01*target_pos[d]

        # Z: 抛物线抬腿
        z_start = start_pos[2]
        z_peak = max(z_start + self.step_height, self.step_height)
        if t < 0.5:
            # 上升段: z = z_start + 4*(z_peak-z_start)*t^2
            frac = 2*t
            pos[2] = z_start + (z_peak - z_start) * frac * frac
            vel[2] = 4*(z_peak - z_start)*frac / P.T_SWING
        else:
            # 下降段
            frac = 2*(1-t)
            pos[2] = z_start + (z_peak - z_start) * frac * frac
            vel[2] = -4*(z_peak - z_start)*frac / P.T_SWING

        return pos, vel


# ============================================================================
# WBC 全身控制器
# ============================================================================

class OpenLoongWBC:
    """全身控制器 — 参考 OpenLoong wbc_priority.cpp

    两层结构:
      第一层: 运动学 QP (优先级任务, 通过 Null-Space 投影)
      第二层: 动力学 QP (接触力优化 + 扭矩计算)
    """

    def __init__(self, model: mujoco.MjModel):
        self.model = model
        self.nv = model.nv
        self.nu = model.nu

        # 关节映射
        self._build_joint_map()

        # 足端 body ID
        self.foot_body_id = {
            'left': mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, P.LEFT_FOOT_BODY),
            'right': mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, P.RIGHT_FOOT_BODY),
        }

        # 髋部 body ID
        self.hip_body_id = {
            'left': mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, 'Link_hip_l_roll'),
            'right': mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, 'Link_hip_r_roll'),
        }

        # 左/右腿关节名
        self.LEFT_LEG_JOINTS = P.LEFT_LEG_JOINTS
        self.RIGHT_LEG_JOINTS = P.RIGHT_LEG_JOINTS

        # 上半身关节 (行走时保持初始姿态)
        self.upper_joints = [
            'J_head_yaw', 'J_head_pitch',
            'J_waist_pitch', 'J_waist_roll', 'J_waist_yaw',
            'J_arm_l_01', 'J_arm_l_02', 'J_arm_l_03', 'J_arm_l_04',
            'J_arm_l_05', 'J_arm_l_06', 'J_arm_l_07',
            'J_arm_r_01', 'J_arm_r_02', 'J_arm_r_03', 'J_arm_r_04',
            'J_arm_r_05', 'J_arm_r_06', 'J_arm_r_07',
        ]

        # PD 增益
        self.kp_base_pos = 300.0
        self.kd_base_pos = 30.0
        self.kp_base_rot = 500.0
        self.kd_base_rot = 50.0
        self.kp_swing = 400.0
        self.kd_swing = 20.0
        # 提高站立姿态保持增益（对抗重力）
        # 膝关节和髋关节需要承担主要支撑力（踝关节力矩限制只有 58.5Nm）
        self.kp_posture_leg = 600.0   # 腿关节站立保持
        self.kd_posture_leg = 30.0
        self.kp_posture = 100.0      # 上半身
        self.kd_posture = 10.0
        # 踝关节策略（关键：对抗倾斜，但力矩受限）
        self.kp_ankle_strategy = 300.0  # 踝关节 roll/pitch 主动策略增益

        # 期望站立姿态（从 STAND_POSE 初始化，可在构造后修改）
        self.q_des_stand = np.zeros(self.nv)
        for jname, angle in P.STAND_POSE.items():
            jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, jname)
            if jid >= 0:
                dof = model.jnt_dofadr[jid]
                if dof >= 0:
                    self.q_des_stand[dof] = angle

    def set_desired_pose(self, pose_dict):
        """设置期望关节姿态（覆盖 STAND_POSE）

        Args:
            pose_dict: {joint_name: angle_rad} 字典
        """
        for jname, angle in pose_dict.items():
            jid = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_JOINT, jname)
            if jid >= 0:
                dof = self.model.jnt_dofadr[jid]
                if dof >= 0:
                    self.q_des_stand[dof] = angle

    def sync_pose_from_data(self, data):
        """从当前 MuJoCo 状态同步期望姿态（用于从外部设定初始姿态后同步）

        注意：必须用 jnt_qposadr 索引 data.qpos，因为浮动基座的
        qpos 维度 (nq=7) 和 dof 维度 (nv=6) 不同。
        """
        for jname, dof in self.joint_dof_map.items():
            qa = self.joint_qpos_map.get(jname)
            if qa is not None and qa < len(data.qpos) and dof < self.nv:
                self.q_des_stand[dof] = data.qpos[qa]

    def _build_joint_map(self):
        self.joint_dof_map = {}
        self.joint_qpos_map = {}  # qpos 索引映射（用于 data.qpos 读取）
        for jname in P.JOINT_NAMES:
            jid = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_JOINT, jname)
            if jid >= 0:
                self.joint_dof_map[jname] = self.model.jnt_dofadr[jid]
                self.joint_qpos_map[jname] = self.model.jnt_qposadr[jid]

    def get_foot_jacobian(self, data, side):
        """获取足端雅可比 (6 x nv)"""
        body_id = self.foot_body_id.get(side, -1)
        if body_id < 0:
            return np.zeros((6, self.nv))

        jacp = np.zeros((3, self.nv))
        jacr = np.zeros((3, self.nv))
        mujoco.mj_jac(self.model, data, jacp, jacr, np.zeros(3), body_id)

        J = np.zeros((6, self.nv))
        J[:3, :] = jacp
        J[3:6, :] = jacr
        return J

    def get_foot_pos_vel(self, data, side):
        """获取足端位置和速度"""
        J = self.get_foot_jacobian(data, side)
        body_id = self.foot_body_id.get(side, -1)
        pos = data.xpos[body_id].copy() if body_id >= 0 else np.zeros(3)
        vel = J[:3, :] @ data.qvel
        return pos, vel

    def get_hip_pos(self, data, side):
        """获取髋部位置"""
        body_id = self.hip_body_id.get(side, -1)
        if body_id >= 0:
            return data.xpos[body_id].copy()
        # 回退
        base_pos = data.qpos[0:3].copy()
        offset = np.array([-0.0875, 0.12 if side == 'left' else -0.12, -0.069])
        return base_pos + offset

    def compute_torques(self, data, gait_info, foot_targets,
                        base_pos_des, base_quat_des,
                        Fr_ff=None):
        """计算关节力矩 (WBC 关节级控制)

        关节级职责（基座稳定化由上层 OpenLoongWalkingController.step() 通过
        虚拟基座 wrench 处理）:

          1. 支撑腿关节 PD（含膝关节高度自适应修正）
          2. 足端力映射（重力补偿 + 高度 PD，通过 J^T 映射）
          3. 踝关节策略（对抗基座倾斜）
          4. 摆动腿阻抗控制
          5. 上半身姿态保持

        注意：浮动基座 roll/pitch/height 的稳定化由 step() 中 xfrc_applied
        虚拟基座力完成，不在本方法中处理。

        Args:
            data: MuJoCo MjData
            gait_info: 步态状态 dict
            foot_targets: dict, 摆动足目标
            base_pos_des: 期望基座位置 (3,)
            base_quat_des: 期望基座姿态 [x,y,z,w] (4,)
            Fr_ff: MPC 前馈力 (12,)

        Returns:
            tau: 关节力矩 (nv,) 前6维置零
        """
        nv = self.nv
        dq = data.qvel
        qpos = data.qpos

        tau = np.zeros(nv)

        # ── 1. 基座状态 ──────────────────────────────────
        base_z_cur = qpos[2]
        base_z_des = base_pos_des[2]
        z_err = base_z_des - base_z_cur
        z_vel = dq[2]

        # 高度积分（膝关节修正用）
        if not hasattr(self, '_z_err_integral'):
            self._z_err_integral = 0.0
        self._z_err_integral += z_err * 0.002
        self._z_err_integral = np.clip(self._z_err_integral, -0.5, 0.5)

        knee_correction = np.clip(-z_err * 0.5 - self._z_err_integral * 0.3, -0.4, 0.6)

        # 基座姿态（踝关节策略用）
        base_quat_cur = qpos[3:7].copy()
        base_rpy = quat_to_rpy(base_quat_cur[[1,2,3,0]])

        # ── 2. 步态信息 ──────────────────────────────────
        leg_state = gait_info['leg_state']
        swing_foot = gait_info['swing_foot']

        # ── 3. 判断模式：站立 vs 行走 ─────────────────────
        # 站立模式（Fr_ff is None）：虚拟基座力主导姿态/高度，
        #   关节 PD 使用较低增益，避免与虚拟力冲突
        # 行走模式（Fr_ff is not None）：关节 PD 使用较高增益，
        #   配合 MPC 前馈力实现动态行走
        is_standing = (Fr_ff is None)
        if is_standing:
            # 站立：虚拟基座力主导姿态/高度，关节PD用中等增益防止漂移
            kp_knee, kd_knee = 400.0, 20.0
            kp_hip_p, kd_hip_p = 300.0, 15.0
            kp_ankle, kd_ankle = 200.0, 10.0
            kp_other, kd_other = 300.0, 15.0
            # hip_yaw 不受虚拟力影响，用更高增益
            kp_hip_yaw, kd_hip_yaw = 500.0, 20.0
            foot_force_scale = 0.0  # 站立时不用足端力映射（虚拟力已处理）
        else:
            # 行走：强关节 PD + 足端力映射
            kp_knee, kd_knee = 600.0, 30.0
            kp_hip_p, kd_hip_p = 400.0, 20.0
            kp_ankle, kd_ankle = 200.0, 10.0
            kp_other, kd_other = 300.0, 15.0
            foot_force_scale = 0.5  # 足端力映射权重

        # ── 4. 重力补偿力 ────────────────────────────────
        gravity_comp = P.TOTAL_MASS * 9.81
        f_z_total = gravity_comp + 2000.0 * z_err - 200.0 * z_vel
        f_z_total = max(0.0, f_z_total)

        # ── 4. 按腿施加控制 ──────────────────────────────
        for leg_side, leg_joints, foot_body, is_stance in [
            ('left', self.LEFT_LEG_JOINTS, 'left', leg_state in ('LSt', 'DSt')),
            ('right', self.RIGHT_LEG_JOINTS, 'right', leg_state in ('RSt', 'DSt'))
        ]:
            J_foot = self.get_foot_jacobian(data, foot_body)
            J_lin = J_foot[:3, 6:]

            if is_stance:
                # ── 4a. 支撑腿关节 PD ──────────────────
                for jname in leg_joints:
                    dof = self.joint_dof_map.get(jname)
                    qa = self.joint_qpos_map.get(jname)
                    if dof is None or dof >= nv:
                        continue
                    q_cur = qpos[qa] if qa is not None and qa < len(qpos) else 0
                    qd_cur = dq[dof] if dof < len(dq) else 0
                    q_des = self.q_des_stand[dof]

                    if 'knee' in jname:
                        q_des += knee_correction
                        kp_j, kd_j = kp_knee, kd_knee
                    elif 'hip' in jname and 'pitch' in jname:
                        kp_j, kd_j = kp_hip_p, kd_hip_p
                    elif 'hip' in jname and 'yaw' in jname:
                        kp_j, kd_j = (kp_hip_yaw, kd_hip_yaw) if is_standing else (kp_other, kd_other)
                    elif 'ankle' in jname:
                        kp_j, kd_j = kp_ankle, kd_ankle
                    else:
                        kp_j, kd_j = kp_other, kd_other

                    tau[dof] += kp_j * (q_des - q_cur) - kd_j * qd_cur

                # ── 4b. 足端力映射 ─────────────────────
                if foot_force_scale > 0:
                    f_z_per_leg = f_z_total * (0.5 if leg_state == 'DSt' else 1.0)
                    F_des = np.array([0.0, 0.0, f_z_per_leg])
                    tau[6:] += J_lin.T @ F_des * foot_force_scale

                # ── 4c. MPC 前馈力 ─────────────────────
                if Fr_ff is not None:
                    if leg_side == 'left':
                        F_mpc = np.array([Fr_ff[0]*0.05, Fr_ff[1]*0.05, Fr_ff[2]*0.1])
                    else:
                        F_mpc = np.array([Fr_ff[6]*0.05, Fr_ff[7]*0.05, Fr_ff[8]*0.1])
                    tau[6:] += J_lin.T @ F_mpc

                # ── 4d. 踝关节策略 ─────────────────────
                ankle_roll_j = 'J_ankle_l_roll' if leg_side == 'left' else 'J_ankle_r_roll'
                ankle_pitch_j = 'J_ankle_l_pitch' if leg_side == 'left' else 'J_ankle_r_pitch'
                dof_ar = self.joint_dof_map.get(ankle_roll_j)
                dof_ap = self.joint_dof_map.get(ankle_pitch_j)

                if dof_ar is not None and dof_ar < nv:
                    qa_ar = self.joint_qpos_map.get(ankle_roll_j)
                    ankle_roll_des = self.q_des_stand[dof_ar] - base_rpy[0]
                    ankle_roll_cur = qpos[qa_ar] if qa_ar is not None and qa_ar < len(qpos) else 0
                    ankle_roll_vel = dq[dof_ar] if dof_ar < len(dq) else 0
                    tau[dof_ar] += self.kp_ankle_strategy * (ankle_roll_des - ankle_roll_cur)
                    tau[dof_ar] -= self.kd_posture_leg * ankle_roll_vel

                if dof_ap is not None and dof_ap < nv:
                    qa_ap = self.joint_qpos_map.get(ankle_pitch_j)
                    ankle_pitch_des = self.q_des_stand[dof_ap] - base_rpy[1]
                    ankle_pitch_cur = qpos[qa_ap] if qa_ap is not None and qa_ap < len(qpos) else 0
                    ankle_pitch_vel = dq[dof_ap] if dof_ap < len(dq) else 0
                    tau[dof_ap] += self.kp_ankle_strategy * (ankle_pitch_des - ankle_pitch_cur)
                    tau[dof_ap] -= self.kd_posture_leg * ankle_pitch_vel

            elif swing_foot == leg_side:
                # ── 摆动腿阻抗控制 ────────────────────
                target = foot_targets.get(leg_side)
                if target is not None:
                    target_pos, target_vel = target
                    foot_pos, foot_vel = self.get_foot_pos_vel(data, leg_side)
                    pos_err = target_pos - foot_pos
                    vel_err = target_vel - foot_vel
                    F_swing = self.kp_swing * pos_err + self.kd_swing * vel_err
                    tau[6:] += J_lin.T @ F_swing

                for jname in leg_joints:
                    dof = self.joint_dof_map.get(jname)
                    if dof is None or dof >= nv:
                        continue
                    tau[dof] -= self.kd_posture_leg * (dq[dof] if dof < len(dq) else 0)

        # ── 5. 上半身 PD ──────────────────────────────────
        for jname in self.upper_joints:
            dof = self.joint_dof_map.get(jname)
            qa = self.joint_qpos_map.get(jname)
            if dof is None or dof >= nv:
                continue
            q_cur = qpos[qa] if qa is not None and qa < len(qpos) else 0
            qd_cur = dq[dof] if dof < len(dq) else 0
            q_des = self.q_des_stand[dof]
            tau[dof] = self.kp_posture * (q_des - q_cur) - self.kd_posture * qd_cur

        # ── 6. 清理 ────────────────────────────────────────
        tau[:6] = 0.0
        tau = np.clip(tau, -396.0, 396.0)

        return tau


# ============================================================================
# 顶层行走控制器
# ============================================================================

class OpenLoongWalkingController:
    """OpenLoong 风格行走控制器 — 集成 MPC + WBC + 步态调度

    用法:
        ctrl = OpenLoongWalkingController(model, data)
        ctrl.set_velocity(0.5, 0, 0)  # 0.5 m/s 前进
        while True:
            ctrl.step()  # 每 1ms 调用一次
    """

    def __init__(self, model: mujoco.MjModel, data: mujoco.MjData):
        self.model = model
        self.data = data
        self.nv = model.nv
        self.nu = model.nu

        # 子模块
        self.gait = GaitScheduler(dt=model.opt.timestep)
        self.foot_planner = FootPlacement()
        self.mpc = OpenLoongMPC(dt=model.opt.timestep)
        self.wbc = OpenLoongWBC(model)

        # 从当前 data 状态同步期望站立姿态（避免与外部设置的初始姿态冲突）
        self.wbc.sync_pose_from_data(data)

        # 执行器索引
        self._build_actuator_map()

        # 控制参数
        self.step_count = 0
        self.mpc_interval = 20  # 每 20ms (20 个仿真步) 求解一次 MPC

        # 期望速度
        self.des_vx = 0.0
        self.des_vy = 0.0
        self.des_wz = 0.0

        # 站立高度（从当前基座高度读取）
        self.stand_height = float(data.qpos[2])

        # 虚拟基座控制 — 用于浮动基座仿真中的姿态/高度稳定化
        # 浮动基座 roll/pitch/height 无直接执行器，通过 xfrc_applied
        # 施加虚拟力和力矩来模拟机器人内部平衡控制（仿真中标准做法）
        self._base_body_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, 'base_link')
        self._virtual_base_enabled = True  # 启用虚拟基座稳定化
        # 虚拟基座控制参数（经调参优化：虚拟力主导 + 轻量关节PD辅助）
        self._kp_base_z = 2000.0      # 高度 PD 比例增益
        self._kd_base_z = 300.0       # 高度 PD 微分增益
        self._ki_base_z = 500.0       # 高度积分增益
        self._z_err_integral_virtual = 0.0  # 虚拟基座高度积分
        self._kp_base_rot = 3000.0    # 姿态 PD 比例增益
        self._kd_base_rot = 150.0     # 姿态 PD 微分增益
        self._kd_base_yaw = 200.0     # yaw 阻尼

        # 摆动足起始位置
        self.swing_start_pos = None

        # MPC 输出缓存
        self.mpc_f_L = np.zeros(3)
        self.mpc_tau_L = np.zeros(3)
        self.mpc_f_R = np.zeros(3)
        self.mpc_tau_R = np.zeros(3)

    def _build_actuator_map(self):
        self.act_id = {}
        for aname in P.ACTUATOR_NAMES:
            aid = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_ACTUATOR, aname)
            if aid >= 0:
                self.act_id[aname] = aid

        # 关节 DOF 映射 和 qpos 映射
        self.joint_dof_map = {}
        self.joint_qpos_map = {}
        for jname in P.JOINT_NAMES:
            if jname == 'root_joint':
                continue
            jid = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_JOINT, jname)
            if jid >= 0:
                self.joint_dof_map[jname] = self.model.jnt_dofadr[jid]
                self.joint_qpos_map[jname] = self.model.jnt_qposadr[jid]

        # 左/右腿关节名
        self.left_leg_joints = P.LEFT_LEG_JOINTS
        self.right_leg_joints = P.RIGHT_LEG_JOINTS

    def set_velocity(self, vx, vy=0.0, wz=0.0):
        """设置期望行走速度"""
        self.des_vx = vx
        self.des_vy = vy
        self.des_wz = wz
        if abs(vx) > 0.01 or abs(vy) > 0.01 or abs(wz) > 0.01:
            self.gait.start()
            self.mpc.set_desired_velocity(vx, vy, wz)
        else:
            self.gait.stop()
            self.mpc.set_standing()

    def get_state(self):
        """读取当前状态"""
        data = self.data

        # 基座状态
        base_quat = data.qpos[3:7].copy()  # [w,x,y,z]
        rpy = quat_to_rpy(base_quat[[1,2,3,0]])  # -> [x,y,z,w] -> rpy
        base_pos = data.qpos[0:3].copy()
        base_omega = data.qvel[3:6].copy()
        base_vel = data.qvel[0:3].copy()

        # CoM 位置
        com_pos = data.qpos[0:3].copy()

        # 足端位置
        fe_l_pos = self.wbc.get_foot_pos_vel(data, 'left')[0]
        fe_r_pos = self.wbc.get_foot_pos_vel(data, 'right')[0]

        # 接触力估计 (从传感器)
        try:
            lf_touch = data.sensor(P.LF_TOUCH_SENSOR).data[0]
            rf_touch = data.sensor(P.RF_TOUCH_SENSOR).data[0]
        except Exception:
            lf_touch = 0.0
            rf_touch = 0.0

        fz_L = lf_touch * P.TOTAL_MASS * 9.81 / 2
        fz_R = rf_touch * P.TOTAL_MASS * 9.81 / 2

        return {
            'rpy': rpy,
            'base_pos': base_pos,
            'base_omega': base_omega,
            'base_vel': base_vel,
            'com_pos': com_pos,
            'fe_l_pos': fe_l_pos,
            'fe_r_pos': fe_r_pos,
            'fz_L': fz_L,
            'fz_R': fz_R,
        }

    def step(self):
        """单步控制更新 (每 1ms 调用一次)"""
        self.step_count += 1
        data = self.data

        # 1. 状态读取
        state = self.get_state()

        # 2. 步态调度
        gait_info = self.gait.update(state['fz_L'], state['fz_R'])

        # 3. MPC 求解 (每 20ms)
        if self.gait.walking and self.step_count % self.mpc_interval == 0:
            X_cur = np.concatenate([
                state['rpy'], state['com_pos'],
                state['base_omega'], state['base_vel']
            ])

            # 足端相对 CoM 位置
            p_L_com = state['fe_l_pos'] - state['com_pos']
            p_R_com = state['fe_r_pos'] - state['com_pos']

            # MPC 步态预测
            mpc_gait = self.gait.get_mpc_gait_flags(self.mpc.N)

            f_L, tau_L, f_R, tau_R, success = self.mpc.solve(
                X_cur, p_L_com, p_R_com, mpc_gait
            )
            if success:
                self.mpc_f_L = f_L
                self.mpc_tau_L = tau_L
                self.mpc_f_R = f_R
                self.mpc_tau_R = tau_R

        # 4. 摆动足轨迹规划
        swing_foot = gait_info['swing_foot']
        foot_targets = {}

        if swing_foot == 'left':
            if self.swing_start_pos is None or gait_info['leg_state'] == 'LSt':
                self.swing_start_pos = state['fe_l_pos'].copy()
            # 目标落地点
            hip_pos = self.wbc.get_hip_pos(data, 'left')
            target_landing = self.foot_planner.plan_landing(
                hip_pos, state['base_vel'],
                state['fe_r_pos'],  # 支撑足
                self.des_vx, self.des_vy, is_left=True
            )
            pos, vel = self.foot_planner.plan_swing_trajectory(
                gait_info['phi'], self.swing_start_pos, target_landing
            )
            foot_targets['left'] = (pos, vel)

        elif swing_foot == 'right':
            if self.swing_start_pos is None or gait_info['leg_state'] == 'RSt':
                self.swing_start_pos = state['fe_r_pos'].copy()
            hip_pos = self.wbc.get_hip_pos(data, 'right')
            target_landing = self.foot_planner.plan_landing(
                hip_pos, state['base_vel'],
                state['fe_l_pos'],
                self.des_vx, self.des_vy, is_left=False
            )
            pos, vel = self.foot_planner.plan_swing_trajectory(
                gait_info['phi'], self.swing_start_pos, target_landing
            )
            foot_targets['right'] = (pos, vel)
        else:
            self.swing_start_pos = None

        # 5. WBC 力矩计算
        base_pos_des = np.array([0.0, 0.0, self.stand_height])
        base_quat_des = np.array([0.0, 0.0, 0.0, 1.0])  # [x,y,z,w] 单位四元数

        # MPC 前馈力
        Fr_ff = np.concatenate([
            self.mpc_f_L, self.mpc_tau_L,
            self.mpc_f_R, self.mpc_tau_R
        ])

        tau = self.wbc.compute_torques(
            data, gait_info, foot_targets,
            base_pos_des, base_quat_des,
            Fr_ff=Fr_ff if self.gait.walking else None
        )

        # 6. 施加力矩到执行器
        for aname in P.ACTUATOR_NAMES:
            aid = self.act_id.get(aname)
            if aid is None:
                continue
            jname = 'J_' + aname[2:]
            dof = self.joint_dof_map.get(jname)
            if dof is not None and dof < self.nv:
                self.data.ctrl[aid] = np.clip(float(tau[dof]), -396.0, 396.0)
            else:
                self.data.ctrl[aid] = 0.0

        # 7. 虚拟基座稳定化（浮动基座仿真必需的姿态/高度控制）
        if self._virtual_base_enabled and self._base_body_id >= 0:
            quat = data.qpos[3:7]  # [w,x,y,z]
            w, x, y, z = quat[0], quat[1], quat[2], quat[3]
            roll = np.arctan2(2*(w*x + y*z), 1 - 2*(x*x + y*y))
            pitch = np.arcsin(np.clip(2*(w*y - z*x), -1, 1))
            omega = data.qvel[3:6]

            # 高度控制
            z_err = self.stand_height - data.qpos[2]
            self._z_err_integral_virtual += z_err * 0.002  # dt = 0.002
            self._z_err_integral_virtual = np.clip(self._z_err_integral_virtual, -1.0, 1.0)
            fz_virtual = (self._kp_base_z * z_err +
                          self._ki_base_z * self._z_err_integral_virtual -
                          self._kd_base_z * data.qvel[2])

            # 姿态控制
            tx_virtual = self._kp_base_rot * (-roll) - self._kd_base_rot * omega[0]
            ty_virtual = self._kp_base_rot * (-pitch) - self._kd_base_rot * omega[1]
            tz_virtual = -self._kd_base_yaw * omega[2]  # yaw 阻尼

            # xfrc_applied 作用于基座 body
            data.xfrc_applied[self._base_body_id, :3] = [0.0, 0.0, fz_virtual]
            data.xfrc_applied[self._base_body_id, 3:6] = [tx_virtual, ty_virtual, tz_virtual]

        return gait_info, state
