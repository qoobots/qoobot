"""
QooBot 机器人物理参数
基于 qoobot_float.xml 和 qoobot_mpc.cpp/qoobot_wbc.cpp 提取
"""
import numpy as np

# ===== 总质量与惯量 =====
TOTAL_MASS = 77.35  # kg (各连杆质量之和)
GRAVITY = -9.81     # m/s^2 (Z轴向下)

# CoM 转动惯量 (in world-aligned CoM frame)
# 来自 qoobot_mpc.cpp m_Ic
I_COM = np.array([
    [12.61, 0.0,   0.37],
    [0.0,   11.15, 0.01],
    [0.37,  0.01,  2.15]
])

# ===== 摩擦系数 =====
MU = 0.5  # 足地摩擦系数

# ===== 足端几何参数 (用于支撑多边形约束) =====
# delta_foot: [+x(前), -x(后), +y(左), -y(右)] 半长/半宽
FOOT_DELTA = np.array([0.073, 0.125, 0.025, 0.025])  # m

# 足端力/力矩约束
F_MIN = np.array([-1000, -1000, 0])     # f_x, f_y, f_z min
F_MAX = np.array([1000, 1000, 2274.09]) # f_x, f_y, f_z max
TAU_MIN = np.array([-20, -80, -100])    # tau_x, tau_y, tau_z min
TAU_MAX = np.array([20, 80, 100])       # tau_x, tau_y, tau_z max

# WBC 力约束
F_Z_LOW = 10.0      # 最小法向力 (N)
F_Z_UPP = 1400.0    # 最大法向力 (N)
TAU_UPP_WALK = np.array([15, 40, 40])
TAU_LOW_WALK = np.array([-15, -40, -40])
TAU_UPP_STAND = np.array([15, 30, 40])
TAU_LOW_STAND = np.array([-15, -30, -40])

# ===== 步态参数 =====
T_SWING = 0.4       # 摆动相时间 (s)
T_STANCE = 0.4      # 支撑相时间 (s)
DT_MPC = 0.001      # MPC 控制周期 (s)
STEP_HEIGHT = 0.08  # 摆动足最大离地高度 (m)
STEP_LENGTH = 0.15  # 默认步长 (m)
FZ_THRESHOLD = 100  # 接触力检测阈值 (N)
FZ_SWITCH_WALK = 280 # 行走模式切换力阈值 (N)
FZ_SWITCH_STOP = 200 # 停止模式切换力阈值 (N)

# ===== MPC 参数 =====
MPC_N = 10   # 预测时域步数
MPC_CH = 3   # 控制时域步数
MPC_NX = 12  # 状态向量维度: [rpy(3), pos(3), omega(3), vel(3)]
MPC_NU = 13  # 控制向量维度: [f_L(3), tau_L(3), f_R(3), tau_R(3), f_z_total(1)]

# QP 权重
MPC_ALPHA = 0.1  # 控制力惩罚权重

# 状态跟踪权重矩阵 L (对角)
MPC_L_WEIGHTS = np.array([
    1.0, 1.0, 10.0,     # rpy 权重 (yaw 更大)
    10.0, 10.0, 50.0,    # pos 权重 (z 更大)
    0.1, 0.1, 0.1,       # ang_vel 权重
    5.0, 5.0, 5.0        # lin_vel 权重
])

# 控制力平滑权重矩阵 K (对角, 13维)
MPC_K_WEIGHTS = np.ones(MPC_NU)

# ===== WBC 参数 =====
WBC_NV = 37  # QooBot nv: 6 (浮动基座) + 31 (关节)
WBC_QP_NV = 18  # QP 变量: delta_ddq_base(6) + delta_Fr(12)

# 关节 DOF 地址 (按模型顺序)
# root_joint: 0-5 (freejoint, 但 nv=6 都在基座)
# 关节索引 (njnt): 0=root_joint(free), 然后按运动学树
JOINT_NAMES = [
    "root_joint",       # 0  (free, qpos[0:7], dof[0:5])
    "J_head_yaw",       # 1
    "J_head_pitch",     # 2
    "J_arm_r_01",       # 3
    "J_arm_r_02",       # 4
    "J_arm_r_03",       # 5
    "J_arm_r_04",       # 6
    "J_arm_r_05",       # 7
    "J_arm_r_06",       # 8
    "J_arm_r_07",       # 9
    "J_arm_l_01",       # 10
    "J_arm_l_02",       # 11
    "J_arm_l_03",       # 12
    "J_arm_l_04",       # 13
    "J_arm_l_05",       # 14
    "J_arm_l_06",       # 15
    "J_arm_l_07",       # 16
    "J_waist_pitch",    # 17
    "J_waist_roll",     # 18
    "J_waist_yaw",      # 19
    "J_hip_r_roll",     # 20
    "J_hip_r_yaw",      # 21
    "J_hip_r_pitch",    # 22
    "J_knee_r_pitch",   # 23
    "J_ankle_r_pitch",  # 24
    "J_ankle_r_roll",   # 25
    "J_hip_l_roll",     # 26
    "J_hip_l_yaw",      # 27
    "J_hip_l_pitch",    # 28
    "J_knee_l_pitch",   # 29
    "J_ankle_l_pitch",  # 30
    "J_ankle_l_roll",   # 31
]

# 执行器名称 (与 motor 标签对应)
ACTUATOR_NAMES = [
    "M_head_yaw",
    "M_head_pitch",
    "M_arm_l_01", "M_arm_l_02", "M_arm_l_03", "M_arm_l_04",
    "M_arm_l_05", "M_arm_l_06", "M_arm_l_07",
    "M_arm_r_01", "M_arm_r_02", "M_arm_r_03", "M_arm_r_04",
    "M_arm_r_05", "M_arm_r_06", "M_arm_r_07",
    "M_waist_pitch", "M_waist_roll", "M_waist_yaw",
    "M_hip_l_roll", "M_hip_l_yaw", "M_hip_l_pitch",
    "M_knee_l_pitch", "M_ankle_l_pitch", "M_ankle_l_roll",
    "M_hip_r_roll", "M_hip_r_yaw", "M_hip_r_pitch",
    "M_knee_r_pitch", "M_ankle_r_pitch", "M_ankle_r_roll",
]

# 左腿执行器名称 (用于 PD 控制)
LEFT_LEG_ACTUATORS = [
    "M_hip_l_roll", "M_hip_l_yaw", "M_hip_l_pitch",
    "M_knee_l_pitch", "M_ankle_l_pitch", "M_ankle_l_roll"
]

# 右腿执行器名称
RIGHT_LEG_ACTUATORS = [
    "M_hip_r_roll", "M_hip_r_yaw", "M_hip_r_pitch",
    "M_knee_r_pitch", "M_ankle_r_pitch", "M_ankle_r_roll"
]

# 左腿关节名称
LEFT_LEG_JOINTS = [
    "J_hip_l_roll", "J_hip_l_yaw", "J_hip_l_pitch",
    "J_knee_l_pitch", "J_ankle_l_pitch", "J_ankle_l_roll"
]

# 右腿关节名称
RIGHT_LEG_JOINTS = [
    "J_hip_r_roll", "J_hip_r_yaw", "J_hip_r_pitch",
    "J_knee_r_pitch", "J_ankle_r_pitch", "J_ankle_r_roll"
]

# 足端 body 名称
LEFT_FOOT_BODY = "Link_ankle_l_roll"
RIGHT_FOOT_BODY = "Link_ankle_r_roll"

# 触地传感器名称
LF_TOUCH_SENSOR = "lf-touch"
RF_TOUCH_SENSOR = "rf-touch"

# 站立姿态关节角度 (rad)
# hip_pitch=-0.33rad(-18.9deg), knee=0.536rad(30.7deg), ankle_pitch=-0.206rad(-11.8deg)
HIP_PITCH_STAND = -0.33   # -18.9 deg
KNEE_STAND = 0.536        # 30.7 deg
ANKLE_PITCH_STAND = -0.206  # -11.8 deg

STAND_POSE = {
    "J_head_yaw": 0.0, "J_head_pitch": 0.0,
    "J_arm_l_01": -0.5, "J_arm_l_02": 0.0, "J_arm_l_03": 0.0,
    "J_arm_l_04": 0.0, "J_arm_l_05": 0.0, "J_arm_l_06": 0.0, "J_arm_l_07": 0.0,
    "J_arm_r_01": -0.5, "J_arm_r_02": 0.0, "J_arm_r_03": 0.0,
    "J_arm_r_04": 0.0, "J_arm_r_05": 0.0, "J_arm_r_06": 0.0, "J_arm_r_07": 0.0,
    "J_waist_pitch": 0.0, "J_waist_roll": 0.0, "J_waist_yaw": 0.0,
    "J_hip_l_roll": 0.1, "J_hip_l_yaw": 0.0, "J_hip_l_pitch": HIP_PITCH_STAND,
    "J_knee_l_pitch": KNEE_STAND, "J_ankle_l_pitch": ANKLE_PITCH_STAND, "J_ankle_l_roll": -0.1,
    "J_hip_r_roll": 0.1, "J_hip_r_yaw": 0.0, "J_hip_r_pitch": HIP_PITCH_STAND,
    "J_knee_r_pitch": KNEE_STAND, "J_ankle_r_pitch": ANKLE_PITCH_STAND, "J_ankle_r_roll": -0.1,
}
