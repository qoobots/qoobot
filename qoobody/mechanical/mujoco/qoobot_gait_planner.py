"""
QooBot 步态调度器 + 摆动足轨迹规划 — Python 实现
基于 OpenLoong dyn-control 的 gait_scheduler.cpp 和 foot_placement.cpp
"""
import numpy as np
import qoobot_robot_params as P


class GaitScheduler:
    """步态调度器：管理 LSt/RSt/DSt 状态机"""

    def __init__(self, dt=P.DT_MPC):
        self.dt = dt
        self.t_swing = P.T_SWING
        self.t_stance = P.T_STANCE
        self.dphi = self.dt / self.t_swing  # 每步相位增量

        self.phi = 0.0                      # 当前相位 [0, 1]
        self.leg_state = 'DSt'              # LSt, RSt, DSt
        self.enable_next_step = True        # 是否继续步行

        # 摆动足起始位置 (世界系)
        self.swing_start_pos_W = np.zeros(3)

        # 期望步行速度
        self.des_vx = 0.0
        self.des_vy = 0.0
        self.des_wz = 0.0

    def set_velocity(self, vx, vy, wz):
        self.des_vx = vx
        self.des_vy = vy
        self.des_wz = wz
        if abs(vx) > 0.01 or abs(vy) > 0.01 or abs(wz) > 0.01:
            self.enable_next_step = True
            if self.leg_state == 'DSt':
                # 从站立启动：以当前相位 0 开始左支撑
                self.phi = 0.0
                self.leg_state = 'LSt'

    def stop(self):
        """停止步行"""
        self.enable_next_step = False

    def update(self, f_L_est, f_R_est, fe_l_pos_W, fe_r_pos_W):
        """更新步态状态

        Args:
            f_L_est: 左脚估计接触力 [3] (世界系)
            f_R_est: 右脚估计接触力 [3] (世界系)
            fe_l_pos_W: 左脚世界位置 [3]
            fe_r_pos_W: 右脚世界位置 [3]

        Returns:
            dict: 步态状态信息
        """
        fz_L = f_L_est[2] if len(f_L_est) >= 3 else 0
        fz_R = f_R_est[2] if len(f_R_est) >= 3 else 0

        if self.leg_state == 'LSt':
            # 左支撑相：等待右腿着地
            self.phi += self.dphi
            if self.phi >= 1.0:
                self.phi = 1.0  # 钳位

            # 切换条件：相位 >= 0.6 且右腿接触力 >= 阈值
            if self.phi >= 0.6 and fz_R >= P.FZ_SWITCH_WALK:
                if self.enable_next_step:
                    self.leg_state = 'RSt'
                    self.swing_start_pos_W = fe_l_pos_W.copy()
                    self.phi = 0.0
                else:
                    # 停止：进入双支撑
                    if fz_R >= P.FZ_SWITCH_STOP:
                        self.leg_state = 'DSt'
                        self.phi = 0.0

        elif self.leg_state == 'RSt':
            # 右支撑相
            self.phi += self.dphi
            if self.phi >= 1.0:
                self.phi = 1.0

            if self.phi >= 0.6 and fz_L >= P.FZ_SWITCH_WALK:
                if self.enable_next_step:
                    self.leg_state = 'LSt'
                    self.swing_start_pos_W = fe_r_pos_W.copy()
                    self.phi = 0.0
                else:
                    if fz_L >= P.FZ_SWITCH_STOP:
                        self.leg_state = 'DSt'
                        self.phi = 0.0

        elif self.leg_state == 'DSt':
            # 双支撑：等待启动命令
            if self.enable_next_step:
                self.leg_state = 'LSt'
                self.swing_start_pos_W = fe_r_pos_W.copy()
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
            'phi': self.phi,
            'leg_state': self.leg_state,
            'swing_foot': swing_foot,
            'stance_foot': stance_foot,
            'fz_L': fz_L,
            'fz_R': fz_R,
        }


class FootPlacement:
    """摆动足轨迹规划 (三次样条)"""

    def __init__(self):
        self.step_height = P.STEP_HEIGHT
        self.step_length = P.STEP_LENGTH

    def plan_swing_trajectory(self, phi, swing_start_W, stance_foot_W,
                               des_vx=0.0, des_vy=0.0, des_wz=0.0):
        """规划摆动足轨迹

        Args:
            phi: 相位 [0, 1]
            swing_start_W: 摆动起始位置 (世界系)
            stance_foot_W: 支撑足位置 (世界系)
            des_vx, des_vy, des_wz: 期望速度

        Returns:
            pos_W: 当前相位下的足端位置 (世界系) [3]
            vel_W: 当前相位下的足端速度 (世界系) [3]
        """
        # 目标落地点: 基于 Raibert 启发式
        # p_target = p_stance + v_des * t_stance / 2 + k * (v - v_des)
        landing_offset = np.array([
            des_vx * self.step_length / 0.15,   # x 偏移
            des_vy * 0.05,                       # y 偏移
            0.0
        ])

        # 默认步长下的目标位置
        if abs(des_vx) > 0.01:
            target_x = stance_foot_W[0] + np.sign(des_vx) * self.step_length
        else:
            target_x = stance_foot_W[0]

        target_W = np.array([
            target_x,
            stance_foot_W[1] + landing_offset[1],
            0.0  # 地面高度
        ])

        # 三次样条插值 (相位 0->1)
        # x(t) = a0 + a1*t + a2*t^2 + a3*t^3
        # 边界条件: x(0)=start, x(1)=target, x'(0)=0, x'(1)=0
        t = phi
        t2 = t * t
        t3 = t2 * t

        # Hermite 插值
        h00 = 2 * t3 - 3 * t2 + 1
        h10 = t3 - 2 * t2 + t
        h01 = -2 * t3 + 3 * t2
        h11 = t3 - t2

        # 位置 (x, y 用 Hermite, z 用抛物线)
        pos_W = np.zeros(3)
        pos_W[0] = h00 * swing_start_W[0] + h10 * 0 + h01 * target_W[0] + h11 * 0
        pos_W[1] = h00 * swing_start_W[1] + h10 * 0 + h01 * target_W[1] + h11 * 0

        # z 方向: 抛物线 (最高点在 phi=0.5)
        z_start = swing_start_W[2]
        z_mid = max(z_start, self.step_height)
        pos_W[2] = z_start + 4 * (z_mid - z_start) * t * (1 - t)
        if t > 0.9:
            # 最后 10% 快速下降
            frac = (t - 0.9) / 0.1
            pos_W[2] = z_mid * (1 - frac) + 0.0 * frac

        # 速度
        vel_W = np.zeros(3)
        dh00 = (6 * t2 - 6 * t) / P.T_SWING
        dh10 = (3 * t2 - 4 * t + 1) / P.T_SWING
        dh01 = (-6 * t2 + 6 * t) / P.T_SWING
        dh11 = (3 * t2 - 2 * t) / P.T_SWING

        vel_W[0] = dh00 * swing_start_W[0] + dh01 * target_W[0]
        vel_W[1] = dh00 * swing_start_W[1] + dh01 * target_W[1]
        vel_W[2] = 4 * (z_mid - z_start) * (1 - 2 * t) / P.T_SWING
        if t > 0.9:
            vel_W[2] = -z_mid / (0.1 * P.T_SWING)

        return pos_W, vel_W


class RaibertHeuristic:
    """Raibert 式足端落点规划"""

    def __init__(self):
        self.k_vx = 0.03    # 速度反馈增益
        self.k_vy = 0.02
        self.hip_height = 0.9

    def compute_foot_landing(self, com_pos, com_vel, stance_foot_W,
                              des_vx=0.0, des_vy=0.0, des_wz=0.0,
                              is_left=True):
        """计算摆动足的落地点

        Args:
            com_pos: CoM 世界位置 [3]
            com_vel: CoM 世界速度 [3]
            stance_foot_W: 支撑足位置 [3]
            des_vx, des_vy, des_wz: 期望速度
            is_left: 是否为左足

        Returns:
            landing_pos: 落地点世界位置 [3]
        """
        # Raibert: p_landing = p_hip + v*T/2 + k*(v - v_des)
        # 髋部位置近似
        hip_pos = com_pos.copy()
        hip_pos[2] -= self.hip_height

        # 半步周期
        T_half = P.T_SWING / 2.0

        # 速度误差
        vel_error_x = com_vel[0] - des_vx
        vel_error_y = com_vel[1] - des_vy

        landing = np.zeros(3)
        landing[0] = hip_pos[0] + des_vx * T_half + self.k_vx * vel_error_x
        landing[1] = hip_pos[1] + des_vy * T_half + self.k_vy * vel_error_y

        # 左右偏移
        if is_left:
            landing[1] += 0.10
        else:
            landing[1] -= 0.10

        landing[2] = 0.0  # 地面高度

        return landing
