"""诊断 WBC 第一步力矩 — 逐步分解"""
import sys
sys.path.insert(0, 'qoobot-os/hal/mechanical/mujoco')

import mujoco
import numpy as np
import qoobot_robot_params as P
from openloong_mpc_wbc import (
    OpenLoongWalkingController, OpenLoongWBC,
    quat_xyzw_to_rotmat, quat_to_rpy
)

model_path = 'qoobot-os/hal/mechanical/mujoco/qoobot_float.xml'
model = mujoco.MjModel.from_xml_path(model_path)
model.opt.timestep = 0.002
data = mujoco.MjData(model)

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

# 手动构建 WBC 力矩，逐项检查
wbc = OpenLoongWBC(model)
wbc._z_err_integral = 0.0  # 手动初始化

nv = wbc.nv
tau = np.zeros(nv)

# Step 1: 关节 PD
print('=== Step 1: Joint PD ===')
for jname in P.LEFT_LEG_JOINTS + P.RIGHT_LEG_JOINTS:
    dof = wbc.joint_dof_map.get(jname)
    if dof is None:
        continue
    q_cur = data.qpos[dof] if dof < len(data.qpos) else 0
    q_des = wbc.q_des_stand[dof]
    print(f'  {jname}: q_des={q_des:.4f}, q_cur={q_cur:.4f}, err={q_des-q_cur:.6f}')

# Step 2: 足端力映射
J_L = wbc.get_foot_jacobian(data, 'left')
J_R = wbc.get_foot_jacobian(data, 'right')
J_lin_L = J_L[:3, 6:]
J_lin_R = J_R[:3, 6:]

gravity_comp = P.TOTAL_MASS * 9.81
f_z_total = gravity_comp  # z_err = 0
f_z_per_leg = f_z_total * 0.5
F_des = np.array([0.0, 0.0, f_z_per_leg])

tau_from_force = (J_lin_L.T + J_lin_R.T) @ F_des * 0.5

knee_dof_L = model.jnt_dofadr[mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, 'J_knee_l_pitch')]
print(f'\nForce mapping contribution:')
print(f'  knee_L tau = {tau_from_force[knee_dof_L-6]:.1f} Nm')

# Step 3: 检查踝关节策略
base_quat_cur = data.qpos[3:7].copy()
base_rpy = quat_to_rpy(base_quat_cur[[1,2,3,0]])
print(f'\nBase rpy: {base_rpy}')

# ankle_roll_des = q_des_stand - base_rpy[0]
ankle_roll_dof_L = wbc.joint_dof_map.get('J_ankle_l_roll')
ankle_pitch_dof_L = wbc.joint_dof_map.get('J_ankle_l_pitch')
ankle_roll_dof_R = wbc.joint_dof_map.get('J_ankle_r_roll')
ankle_pitch_dof_R = wbc.joint_dof_map.get('J_ankle_r_pitch')

print(f'Ankle roll: q_des={wbc.q_des_stand[ankle_roll_dof_L]:.4f}, '
      f'ankle_roll_des={wbc.q_des_stand[ankle_roll_dof_L] - base_rpy[0]:.4f}')
print(f'Ankle pitch: q_des={wbc.q_des_stand[ankle_pitch_dof_L]:.4f}, '
      f'ankle_pitch_des={wbc.q_des_stand[ankle_pitch_dof_L] - base_rpy[1]:.4f}')

# 实际调用 compute_torques
print('\n=== Full compute_torques ===')
wbc._z_err_integral = 0.0
tau_full = wbc.compute_torques(
    data,
    {'leg_state': 'DSt', 'swing_foot': 'none', 'phi': 0.0},
    {},
    np.array([0.0, 0.0, CORRECT_HEIGHT]),
    np.array([0.0, 0.0, 0.0, 1.0]),
)

for jname in P.LEFT_LEG_JOINTS:
    dof = wbc.joint_dof_map.get(jname)
    if dof is not None and dof < nv:
        print(f'  {jname}: tau={tau_full[dof]:.1f} Nm')
