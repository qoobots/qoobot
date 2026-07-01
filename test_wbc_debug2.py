"""调试 WBC 力矩 - 检查实际施加的力矩值"""
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

# 构建 actuator 映射
act_ids = {}
for aname in P.ACTUATOR_NAMES:
    aid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_ACTUATOR, aname)
    if aid >= 0:
        act_ids[aname] = aid

wbc = OpenLoongWBC(model)

# 设置站立姿态
for jname, angle in P.STAND_POSE.items():
    jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, jname)
    if jid >= 0:
        data.qpos[model.jnt_qposadr[jid]] = angle
data.qpos[2] = 1.0
mujoco.mj_forward(model, data)

# 先稳定化 100 步
print('Stabilizing...')
for step in range(100):
    for aname in P.ACTUATOR_NAMES:
        jname = 'J_' + aname[2:]
        jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, jname)
        if jid >= 0:
            qpos_addr = model.jnt_qposadr[jid]
            dof_addr = model.jnt_dofadr[jid]
            aid = act_ids.get(aname)
            if aid is not None:
                q_cur = data.qpos[qpos_addr]
                qd_cur = data.qvel[dof_addr]
                q_des = P.STAND_POSE.get(jname, 0.0)
                data.ctrl[aid] = np.clip(600.0*(q_des - q_cur) - 20.0*qd_cur, -396, 396)
    mujoco.mj_step(model, data)

print(f'After stabilize: height={data.qpos[2]:.3f}')

# 调用 WBC compute_torques
gait_info = {'leg_state': 'DSt', 'swing_foot': 'none', 'stance_foot': 'both', 'phi': 0.0}
foot_targets = {}
base_pos_des = np.array([0.0, 0.0, 1.0])
base_quat_des = np.array([0.0, 0.0, 0.0, 1.0])

tau = wbc.compute_torques(data, gait_info, foot_targets, base_pos_des, base_quat_des)

# 检查关键关节力矩
print(f'\nWBC 力矩输出 (站立模式, 期望高度=1.0, 实际高度={data.qpos[2]:.3f}):')
for jname in P.LEFT_LEG_JOINTS:
    dof = wbc.joint_dof_map.get(jname)
    if dof is not None:
        aname = 'M_' + jname[2:]
        aid = act_ids.get(aname)
        print(f'  {jname} (dof={dof}, act={aid}): tau={tau[dof]:.1f} Nm')

print(f'\n右腿:')
for jname in P.RIGHT_LEG_JOINTS:
    dof = wbc.joint_dof_map.get(jname)
    if dof is not None:
        print(f'  {jname} (dof={dof}): tau={tau[dof]:.1f} Nm')

# 检查基座受力
print(f'\n基座外力 (qfrc_applied):')
print(f'  force: {data.qfrc_applied[0:3]}')
print(f'  torque: {data.qfrc_applied[3:6]}')
print(f'基座偏差力 (qfrc_bias):')
print(f'  {data.qfrc_bias[0:6]}')

# 单步仿真看高度变化
print(f'\n单步仿真...')
data_before = data.qpos[2]
mujoco.mj_step(model, data)
print(f'  高度变化: {data_before:.4f} -> {data.qpos[2]:.4f} (delta={data.qpos[2]-data_before:.4f})')
