"""诊断 WBC 第一步的力矩来源分解"""
import sys
sys.path.insert(0, 'qoobot-os/hal/mechanical/mujoco')

import mujoco
import numpy as np
import qoobot_robot_params as P
from openloong_mpc_wbc import (
    OpenLoongWalkingController, OpenLoongWBC,
    quat_xyzw_to_rotmat, quat_to_rpy, skew
)

model_path = 'qoobot-os/hal/mechanical/mujoco/qoobot_float.xml'
model = mujoco.MjModel.from_xml_path(model_path)
model.opt.timestep = 0.002
data = mujoco.MjData(model)

# 使用较好的姿态
pose = dict(P.STAND_POSE)
pose['J_hip_l_pitch'] = -0.2
pose['J_hip_r_pitch'] = -0.2
pose['J_knee_l_pitch'] = 0.2
pose['J_knee_r_pitch'] = 0.2
pose['J_ankle_l_pitch'] = 0.0
pose['J_ankle_r_pitch'] = 0.0
CORRECT_HEIGHT = 1.1311

for jname, angle in pose.items():
    jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, jname)
    if jid >= 0:
        data.qpos[model.jnt_qposadr[jid]] = angle
data.qpos[2] = CORRECT_HEIGHT
mujoco.mj_forward(model, data)

print(f'Initial height: {data.qpos[2]:.4f}m')
print(f'qfrc_bias (gravity comp needed):')
for jname in ['J_knee_l_pitch', 'J_hip_l_pitch', 'J_ankle_l_pitch']:
    jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, jname)
    if jid >= 0:
        dof = model.jnt_dofadr[jid]
        print(f'  {jname}: qfrc_bias={data.qfrc_bias[dof]:.2f}')

# 手动模拟 WBC 的第一步
wbc = OpenLoongWBC(model)

gait_info = {'leg_state': 'DSt', 'swing_foot': 'none', 'phi': 0.0}
foot_targets = {}
base_pos_des = np.array([0.0, 0.0, CORRECT_HEIGHT])
base_quat_des = np.array([0.0, 0.0, 0.0, 1.0])

tau = wbc.compute_torques(data, gait_info, foot_targets, base_pos_des, base_quat_des)

print(f'\nWBC torque output (first step, DSt):')
for jname in ['J_knee_l_pitch', 'J_knee_r_pitch', 'J_hip_l_pitch', 'J_hip_r_pitch',
              'J_ankle_l_pitch', 'J_ankle_r_pitch']:
    jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, jname)
    if jid >= 0:
        dof = model.jnt_dofadr[jid]
        print(f'  {jname}: tau={tau[dof]:.1f} Nm')

# 手动分解 WBC 力矩
nv = model.nv
qpos = data.qpos
dq = data.qvel

# 基座高度
base_z_cur = qpos[2]
z_err = base_pos_des[2] - base_z_cur
print(f'\nHeight error: {z_err:.6f}')

# 检查足端雅可比映射
J_L = wbc.get_foot_jacobian(data, 'left')
J_R = wbc.get_foot_jacobian(data, 'right')
J_lin_L = J_L[:3, 6:]
J_lin_R = J_R[:3, 6:]

gravity_comp = P.TOTAL_MASS * 9.81
f_z_total = gravity_comp + 2000.0 * z_err - 200.0 * dq[2]
print(f'f_z_total={f_z_total:.1f}N (gravity={gravity_comp:.1f}N)')

f_z_per_leg = f_z_total * 0.5
F_des = np.array([0.0, 0.0, f_z_per_leg])
tau_from_force_L = J_lin_L.T @ F_des * 0.5
tau_from_force_R = J_lin_R.T @ F_des * 0.5

knee_dof_L = model.jnt_dofadr[mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, 'J_knee_l_pitch')]
knee_dof_R = model.jnt_dofadr[mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, 'J_knee_r_pitch')]

print(f'\nForce mapping contribution to knee (index={knee_dof_L-6}):')
print(f'  knee_L from force mapping: {tau_from_force_L[knee_dof_L-6]:.1f} Nm')
print(f'  knee_R from force mapping: {tau_from_force_R[knee_dof_R-6]:.1f} Nm')

# 检查足端雅可比的具体值
print(f'\nFoot Jacobian linear part (first 3 rows, leg joint columns):')
for leg_j in ['J_knee_l_pitch', 'J_hip_l_pitch', 'J_ankle_l_pitch']:
    jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, leg_j)
    dof = model.jnt_dofadr[jid]
    print(f'  d(foot_pos)/d({leg_j}) = {J_lin_L[:, dof-6]}')

# 检查 J_lin.T @ [0, 0, Fz] 对膝关节的影响
# 足端 z 方向关于膝关节的偏导
print(f'\n  d(foot_z)/d(knee_L) = {J_lin_L[2, knee_dof_L-6]:.4f}')
print(f'  d(foot_z)/d(hip_pitch_L) = {J_lin_L[2, model.jnt_dofadr[mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, "J_hip_l_pitch")]-6]:.4f}')
print(f'  d(foot_z)/d(ankle_pitch_L) = {J_lin_L[2, model.jnt_dofadr[mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, "J_ankle_l_pitch")]-6]:.4f}')
