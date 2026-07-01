"""调试 WBC 力矩映射"""
import sys
sys.path.insert(0, 'qoobot-os/hal/mechanical/mujoco')

import mujoco
import numpy as np
import qoobot_robot_params as P
from openloong_mpc_wbc import OpenLoongWBC, quat_xyzw_to_rotmat

model_path = 'qoobot-os/hal/mechanical/mujoco/qoobot_float.xml'
model = mujoco.MjModel.from_xml_path(model_path)
model.opt.timestep = 0.002
data = mujoco.MjData(model)

# 设置站立姿态
for jname, angle in P.STAND_POSE.items():
    jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, jname)
    if jid >= 0:
        data.qpos[model.jnt_qposadr[jid]] = angle
data.qpos[2] = 1.0
mujoco.mj_forward(model, data)

wbc = OpenLoongWBC(model)

# 获取足端雅可比
J_L = wbc.get_foot_jacobian(data, 'left')
J_R = wbc.get_foot_jacobian(data, 'right')

print(f'nv={model.nv}, nu={model.nu}')
print(f'J_L shape: {J_L.shape}')
print(f'J_R shape: {J_R.shape}')
print(f'J_L[:3, :] (linear part):')
print(np.array2string(J_L[:3, :], precision=3, suppress_small=True))
print(f'J_R[:3, :] (linear part):')
print(np.array2string(J_R[:3, :], precision=3, suppress_small=True))

# 测试: 期望 800N 向上的力，映射到关节力矩
F_des = np.array([0, 0, 800.0])
tau_from_L = J_L[:3, 6:].T @ F_des
tau_from_R = J_R[:3, 6:].T @ F_des
print(f'\n期望力 F=[0, 0, 800] 映射到关节力矩:')
print(f'  左腿: {np.array2string(tau_from_L, precision=1, suppress_small=True)}')
print(f'  右腿: {np.array2string(tau_from_R, precision=1, suppress_small=True)}')

# 检查力矩是否超过限制
print(f'\n力矩限幅 396Nm 后:')
print(f'  左腿: {np.array2string(np.clip(tau_from_L, -396, 396), precision=1, suppress_small=True)}')
print(f'  右腿: {np.array2string(np.clip(tau_from_R, -396, 396), precision=1, suppress_small=True)}')

# 检查重力补偿需要多少力
print(f'\n重力补偿: mg = {P.TOTAL_MASS * 9.81:.1f} N')
print(f'每条腿需支撑: {P.TOTAL_MASS * 9.81 / 2:.1f} N')

# 实际需要多大的关节力矩
# 从雅可比推算: tau = J^T * F
# 支撑腿需要产生 ~380N 的 z 方向力
F_need = np.array([0, 0, 400.0])
tau_need = J_L[:3, 6:].T @ F_need
print(f'\n支撑 400N 需要的力矩: {np.array2string(tau_need, precision=1, suppress_small=True)}')

# 检查哪些关节力矩超限
for i, jname in enumerate(P.LEFT_LEG_JOINTS):
    print(f'  {jname}: tau={tau_need[i]:.1f} Nm')
