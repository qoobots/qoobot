"""
QooBot 单刚体模型 (SRBM) MPC 控制器 — Python 实现
基于 OpenLoong dyn-control 的 mpc.cpp 和 qoobot_mpc.cpp

状态向量 X (12维): [rpy(3), pos(3), ang_vel(3), lin_vel(3)]
控制向量 U (13维): [f_L(3), tau_L(3), f_R(3), tau_R(3), f_z_total(1)]
"""
import numpy as np
import qoobot_robot_params as P


class SingleRigidBodyModel:
    """单刚体模型：将机器人视为质心处的单个刚体"""

    def __init__(self, dt=P.DT_MPC):
        self.dt = dt
        self.mass = P.TOTAL_MASS
        self.I_com = P.I_COM.copy()
        self.gravity = np.array([0, 0, P.GRAVITY])
        self.inv_I = np.linalg.inv(self.I_com)

        # 预计算离散化矩阵
        self.Ac = self._build_Ac()
        self.Bc = self._build_Bc()
        self.A = np.eye(P.MPC_NX) + dt * self.Ac
        self.B = dt * self.Bc

    def _build_Ac(self):
        """连续时间 A 矩阵 (12x12)"""
        Ac = np.zeros((P.MPC_NX, P.MPC_NX))
        # drpy/dt = Rz^T * omega (近似为单位阵，小角度假设)
        Ac[0:3, 6:9] = np.eye(3)
        # dpos/dt = vel
        Ac[3:6, 9:12] = np.eye(3)
        # omega_dot 和 vel_dot = 0 (无内部动力学)
        return Ac

    def _build_Bc(self):
        """连续时间 B 矩阵 (12x13)"""
        Bc = np.zeros((P.MPC_NX, P.MPC_NU))
        # d(omega)/dt = IcW^-1 * (p_L x f_L + tau_L + p_R x f_R + tau_R)
        # d(vel)/dt = (f_L + f_R)/m + g
        inv_m = 1.0 / self.mass

        # 足端在 CoM 系中的默认位置 (世界系)
        # 这些值会在 update() 中根据当前姿态更新
        self.p_L = np.array([0.0, 0.10, -0.9])   # 左脚相对 CoM
        self.p_R = np.array([0.0, -0.10, -0.9])  # 右脚相对 CoM

        # angular velocity 部分 (第6-8行)
        # Ic^-1 * skew(p_L) * f_L + Ic^-1 * tau_L
        for i in range(3):
            for j in range(3):
                # f_L 贡献 (列 0-2)
                Bc[6 + i, j] = 0  # 运行时通过 cross 矩阵更新
            # tau_L 贡献 (列 3-5)
            Bc[6 + i, 3 + i] = self.inv_I[i, i]
            # tau_R 贡献 (列 9-11)
            Bc[6 + i, 9 + i] = self.inv_I[i, i]

        # linear velocity 部分 (第9-11行)
        # f_L 贡献
        Bc[9:12, 0:3] = inv_m * np.eye(3)
        # f_R 贡献
        Bc[9:12, 6:9] = inv_m * np.eye(3)
        # 重力
        Bc[9:12, 12] = self.gravity / P.GRAVITY  # 归一化

        return Bc

    def update_foot_positions(self, p_L_world, p_R_world, com_pos):
        """更新世界系足端位置并重建 B 矩阵"""
        self.p_L = p_L_world - com_pos
        self.p_R = p_R_world - com_pos
        self.Bc = self._build_Bc()
        self.B = self.dt * self.Bc

    def get_Bc_for_foot(self, p_foot):
        """根据指定足端位置计算 Bc"""
        Bc = np.zeros((P.MPC_NX, P.MPC_NU))
        inv_m = 1.0 / self.mass

        # skew(p_foot) * f 的贡献
        px, py, pz = p_foot
        skew = np.array([[0, -pz, py], [pz, 0, -px], [-py, px, 0]])

        # angular velocity 部分: Ic^-1 * skew(p_foot)
        Bc[6:9, 0:3] = self.inv_I @ skew  # f_L 贡献
        Bc[6:9, 3:6] = self.inv_I          # tau_L 贡献
        Bc[6:9, 6:9] = self.inv_I @ skew   # f_R 贡献
        Bc[6:9, 9:12] = self.inv_I         # tau_R 贡献

        # linear velocity 部分
        Bc[9:12, 0:3] = inv_m * np.eye(3)
        Bc[9:12, 6:9] = inv_m * np.eye(3)
        Bc[9:12, 12] = np.array([0, 0, 1.0])

        return Bc

    def discrete_dynamics(self, X, U):
        """一步离散动力学前向"""
        return self.A @ X + self.B @ U


class QooBotMPC:
    """QooBot 模型预测控制器

    预测时域: MPC_N=10 步, 控制时域: MPC_CH=3 步
    状态: X = [rpy, pos, omega, vel] (12维)
    控制: U = [f_L, tau_L, f_R, tau_R] (12维, 实际每步)
    """

    def __init__(self, dt=P.DT_MPC):
        self.dt = dt
        self.model = SingleRigidBodyModel(dt)
        self.nx = P.MPC_NX
        self.nu = P.MPC_NU
        self.N = P.MPC_N
        self.ch = P.MPC_CH
        self.alpha = P.MPC_ALPHA

        # 权重矩阵
        self.L = np.diag(P.MPC_L_WEIGHTS)  # 状态跟踪权重 (12x12)
        self.K = np.diag(P.MPC_K_WEIGHTS)  # 控制平滑权重 (13x13)

        # 预计算 MPC 矩阵
        self._build_mpc_matrices()

        # 参考轨迹
        self.Xd = np.zeros((self.N, self.nx))

        # 上一帧的最优控制 (用于热启动)
        self.U_prev = None

    def _build_mpc_matrices(self):
        """构建 Aqp, Bqp 矩阵"""
        A = self.model.A
        B = self.model.B

        # Aqp: (nx*N) x nx, 从 X(0) 到所有预测步的转移
        self.Aqp = np.zeros((self.nx * self.N, self.nx))
        Apow = np.eye(self.nx)
        for i in range(self.N):
            Apow = Apow @ A
            self.Aqp[i * self.nx:(i + 1) * self.nx, :] = Apow

        # Bqp: (nx*N) x (nu*ch), 控制压缩到 control horizon
        self.Bqp = np.zeros((self.nx * self.N, self.nu * self.ch))
        for i in range(self.N):
            for j in range(min(i + 1, self.ch)):
                Apow = np.linalg.matrix_power(A, i - j)
                col_start = j * self.nu
                col_end = (j + 1) * self.nu
                self.Bqp[i * self.nx:(i + 1) * self.nx, col_start:col_end] = Apow @ B

        # 约束矩阵: 摩擦金字塔 + 力/力矩上下界
        self._build_constraint_matrices()

    def _build_constraint_matrices(self):
        """构建不等式约束矩阵 As * U <= bs"""
        # 每步约束维度
        nc_per_step = 32  # 8 (摩擦) + 24 (力/力矩上下界)
        self.nc = nc_per_step
        self.As = np.zeros((nc_per_step * self.ch, self.nu * self.ch))

        # 摩擦金字塔: 每足 4 个不等式 (C++ 中的 friction_pyramid)
        mu = P.MU
        friction_c = np.array([
            [-1, 0, -mu / np.sqrt(2)],   # -f_x - mu/sqrt(2)*f_z <= 0
            [1, 0, -mu / np.sqrt(2)],    # +f_x - mu/sqrt(2)*f_z <= 0
            [0, -1, -mu / np.sqrt(2)],   # -f_y - mu/sqrt(2)*f_z <= 0
            [0, 1, -mu / np.sqrt(2)],    # +f_y - mu/sqrt(2)*f_z <= 0
        ])

        for k in range(self.ch):
            base_row = k * nc_per_step
            base_col = k * self.nu

            # 左足摩擦 (4 行, 列 0-2 和 12)
            self.As[base_row:base_row + 4, base_col:base_col + 3] = friction_c[:, :3]
            self.As[base_row:base_row + 4, base_col + 12] = friction_c[:, 2]  # f_z_total

            # 右足摩擦 (4 行, 列 6-8 和 12)
            self.As[base_row + 4:base_row + 8, base_col + 6:base_col + 9] = friction_c[:, :3]
            self.As[base_row + 4:base_row + 8, base_col + 12] = friction_c[:, 2]

            # 力/力矩上下界 (24 行)
            # f_x, f_y, f_z, tau_x, tau_y, tau_z for each foot
            row = base_row + 8
            # 左足上界
            for i in range(3):
                self.As[row + i, base_col + i] = 1.0    # f 上界
                self.As[row + 3 + i, base_col + i] = -1.0  # f 下界
            for i in range(3):
                self.As[row + 6 + i, base_col + 3 + i] = 1.0    # tau 上界
                self.As[row + 9 + i, base_col + 3 + i] = -1.0   # tau 下界
            # 右足上界
            for i in range(3):
                self.As[row + 12 + i, base_col + 6 + i] = 1.0
                self.As[row + 15 + i, base_col + 6 + i] = -1.0
            for i in range(3):
                self.As[row + 18 + i, base_col + 9 + i] = 1.0
                self.As[row + 21 + i, base_col + 9 + i] = -1.0

        # bs 向量
        self.bs = np.zeros(nc_per_step * self.ch)
        for k in range(self.ch):
            base_row = k * nc_per_step
            row = base_row + 8
            # 左足
            self.bs[row:row + 3] = P.F_MAX
            self.bs[row + 3:row + 6] = -P.F_MIN
            self.bs[row + 6:row + 9] = P.TAU_MAX
            self.bs[row + 9:row + 12] = -P.TAU_MIN
            # 右足
            self.bs[row + 12:row + 15] = P.F_MAX
            self.bs[row + 15:row + 18] = -P.F_MIN
            self.bs[row + 18:row + 21] = P.TAU_MAX
            self.bs[row + 21:row + 24] = -P.TAU_MIN

    def set_desired_velocity(self, vx, vy, wz):
        """设置期望速度 (m/s, m/s, rad/s)"""
        self.Xd = np.zeros((self.N, self.nx))
        for i in range(self.N):
            t = i * self.dt
            self.Xd[i, 3] = vx * t     # x 位置
            self.Xd[i, 4] = vy * t     # y 位置
            self.Xd[i, 5] = 1.0        # z 位置 (保持站立高度)
            self.Xd[i, 9] = vx         # x 速度
            self.Xd[i, 10] = vy        # y 速度
            self.Xd[i, 11] = 0.0       # z 速度

    def set_standing(self):
        """设置站立参考"""
        self.Xd = np.zeros((self.N, self.nx))
        for i in range(self.N):
            self.Xd[i, 5] = 1.0  # 保持站立高度

    def solve(self, X_cur, gait_flags):
        """求解 MPC QP 问题

        Args:
            X_cur: 当前状态 (12,)
            gait_flags: list[bool], 长度 N, 每步是否左足支撑 (True=左支撑)

        Returns:
            U_opt: 最优控制 (ch*nu,) 或 (N*nu,)
        """
        # 构建 QP: min 0.5 * U^T * H * U + c^T * U  s.t. As * U <= bs
        # H = 2 * (Bqp^T * L_blk * Bqp + alpha * K_blk)
        # c = 2 * Bqp^T * L_blk * (Aqp * X_cur - Xd)

        L_blk = np.kron(np.eye(self.N), self.L)
        K_blk = np.kron(np.eye(self.ch), self.K)

        H = 2.0 * (self.Bqp.T @ L_blk @ self.Bqp + self.alpha * K_blk)
        c = 2.0 * self.Bqp.T @ L_blk @ (self.Aqp @ X_cur - self.Xd.flatten())

        # 简化求解: 使用无约束 QP 解析解，然后用饱和投影
        # H * U = -c  =>  U = -H^{-1} * c
        try:
            H_reg = H + 1e-6 * np.eye(H.shape[0])
            U_unconstrained = -np.linalg.solve(H_reg, c)
        except np.linalg.LinAlgError:
            U_unconstrained = np.zeros(self.nu * self.ch)

        # 投影到约束空间 (简化版：只施加力/力矩边界)
        U_opt = self._project_constraints(U_unconstrained)

        return U_opt

    def _project_constraints(self, U):
        """将控制投影到约束空间"""
        U_proj = U.copy()
        for k in range(self.ch):
            idx = k * self.nu
            # 左足力
            U_proj[idx:idx + 3] = np.clip(U_proj[idx:idx + 3], P.F_MIN, P.F_MAX)
            # 左足力矩
            U_proj[idx + 3:idx + 6] = np.clip(U_proj[idx + 3:idx + 6], P.TAU_MIN, P.TAU_MAX)
            # 右足力
            U_proj[idx + 6:idx + 9] = np.clip(U_proj[idx + 6:idx + 9], P.F_MIN, P.F_MAX)
            # 右足力矩
            U_proj[idx + 9:idx + 12] = np.clip(U_proj[idx + 9:idx + 12], P.TAU_MIN, P.TAU_MAX)
            # f_z_total >= 0
            U_proj[idx + 12] = max(0, U_proj[idx + 12])
        return U_proj

    def get_grf(self, U_opt, step_idx=0):
        """从最优控制中提取地面反力 (第一控制步)"""
        idx = step_idx * self.nu
        f_L = U_opt[idx:idx + 3].copy()
        tau_L = U_opt[idx + 3:idx + 6].copy()
        f_R = U_opt[idx + 6:idx + 9].copy()
        tau_R = U_opt[idx + 9:idx + 12].copy()
        return f_L, tau_L, f_R, tau_R


def compute_mpc_gait_flags(phi, leg_state, N):
    """根据当前相位和腿状态预测 N 步的步态标志

    Args:
        phi: 当前相位 [0, 1]
        leg_state: 'LSt' 左支撑, 'RSt' 右支撑, 'DSt' 双支撑
        N: 预测步数

    Returns:
        gait_flags: list[bool], True=左足支撑
    """
    dphi = P.DT_MPC / P.T_SWING
    flags = []
    current_phi = phi
    current_state = leg_state

    for i in range(N):
        if current_state == 'LSt':
            flags.append(True)  # 左支撑
        elif current_state == 'RSt':
            flags.append(False)  # 右支撑
        else:  # DSt
            flags.append(True)  # 双支撑时假设左支撑

        current_phi += dphi
        if current_phi >= 1.0:
            current_phi -= 1.0
            # 切换
            if current_state == 'LSt':
                current_state = 'RSt'
            elif current_state == 'RSt':
                current_state = 'LSt'

    return flags
