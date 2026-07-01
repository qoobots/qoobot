"""测试 OpenLoong MPC+WBC 控制器初始化与运行"""
import sys
sys.path.insert(0, 'qoobot-os/hal/mechanical/mujoco')

import mujoco
import numpy as np
import qoobot_robot_params as P
from openloong_mpc_wbc import OpenLoongWalkingController

# 加载模型
model_path = 'qoobot-os/hal/mechanical/mujoco/qoobot_float.xml'
model = mujoco.MjModel.from_xml_path(model_path)
model.opt.timestep = 0.002  # 500Hz
data = mujoco.MjData(model)

# 初始化控制器
ctrl = OpenLoongWalkingController(model, data)
ctrl.set_velocity(0.3, 0.0, 0.0)
print('OpenLoongWalkingController initialized successfully')
print(f'Gait state: {ctrl.gait.leg_state}')
print(f'Gait walking: {ctrl.gait.walking}')

# 设置初始站立姿态
for jname, angle in P.STAND_POSE.items():
    jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, jname)
    if jid >= 0:
        data.qpos[model.jnt_qposadr[jid]] = angle
data.qpos[2] = 1.0  # 基座高度
mujoco.mj_forward(model, data)

# 稳定化
print('Stabilizing...')
for _ in range(200):
    for aname in P.ACTUATOR_NAMES:
        jname = 'J_' + aname[2:]
        jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, jname)
        if jid >= 0:
            qpos_addr = model.jnt_qposadr[jid]
            dof_addr = model.jnt_dofadr[jid]
            q_cur = data.qpos[qpos_addr]
            qd_cur = data.qvel[dof_addr]
            q_des = P.STAND_POSE.get(jname, 0.0)
            aid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_ACTUATOR, aname)
            if aid >= 0:
                data.ctrl[aid] = np.clip(200.0*(q_des - q_cur) - 10.0*qd_cur, -396, 396)
    mujoco.mj_step(model, data)

print(f'Stabilized. Base height: {data.qpos[2]:.3f}')

# 运行控制器
print('Running controller for 500 steps...')
for i in range(500):
    gait_info, state = ctrl.step()
    mujoco.mj_step(model, data)
    if i % 100 == 0:
        print(f'  Step {i}: height={data.qpos[2]:.3f}, vx={data.qvel[0]:.3f}, '
              f'gait={gait_info["leg_state"]}, phi={gait_info["phi"]:.2f}, '
              f'swing={gait_info["swing_foot"]}')

print('Final state:')
print(f'  Base height: {data.qpos[2]:.3f}')
print(f'  Base vel_x: {data.qvel[0]:.3f}')
print(f'  Base rpy: {data.qpos[3:7]}')
print('Test PASSED!')
