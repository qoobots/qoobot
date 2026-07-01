"""分析最终平衡状态"""
import sys
sys.path.insert(0, 'qoobot-os/hal/mechanical/mujoco')

import mujoco
import numpy as np
import qoobot_robot_params as P

model_path = 'qoobot-os/hal/mechanical/mujoco/qoobot_float.xml'
model = mujoco.MjModel.from_xml_path(model_path)
model.opt.timestep = 0.002
data = mujoco.MjData(model)

act_ids = {}
for aname in P.ACTUATOR_NAMES:
    aid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_ACTUATOR, aname)
    if aid >= 0:
        act_ids[aname] = aid

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

# PD 仿真到稳态（3000步）
for step in range(3000):
    for aname in P.ACTUATOR_NAMES:
        jname = 'J_' + aname[2:]
        jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, jname)
        if jid >= 0:
            q_cur = data.qpos[model.jnt_qposadr[jid]]
            qd_cur = data.qvel[model.jnt_dofadr[jid]]
            q_des = pose.get(jname, 0.0)
            aid = act_ids.get(aname)
            if aid is not None:
                data.ctrl[aid] = np.clip(800*(q_des - q_cur) - 20*qd_cur, -396, 396)
    mujoco.mj_step(model, data)

print(f'Final state (after 3000 steps PD):')
print(f'  Base height: {data.qpos[2]:.4f}m')
print(f'  Base quat: {data.qpos[3:7]}')

lf_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, 'Link_ankle_l_roll')
rf_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, 'Link_ankle_r_roll')

print(f'  LF pos: {data.xpos[lf_id]}')
print(f'  RF pos: {data.xpos[rf_id]}')

# 脚底高度
for side, body_id in [('L', lf_id), ('R', rf_id)]:
    for gid in range(model.ngeom):
        if model.geom_bodyid[gid] == body_id and model.geom_type[gid] == 6:
            gsize = model.geom_size[gid]
            gpos_rel = model.geom_pos[gid]
            bottom_z = data.xpos[body_id][2] + gpos_rel[2] - gsize[2]
            print(f'  {side} foot bottom z: {bottom_z:.4f}')

# 关节角度 vs 目标
print(f'\nJoint angles vs targets:')
for jname in P.LEFT_LEG_JOINTS + P.RIGHT_LEG_JOINTS:
    jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, jname)
    if jid >= 0:
        q_cur = data.qpos[model.jnt_qposadr[jid]]
        q_des = pose.get(jname, 0.0)
        print(f'  {jname}: actual={q_cur:.4f}, target={q_des:.4f}, err={q_des-q_cur:+.4f}')

# CoM 和接触力
mujoco.mj_forward(model, data)
com = data.subtree_com[0]
print(f'\n  CoM: {com}')
print(f'  CoM z: {com[2]:.4f}')

# 接触力
total_fz = 0.0
for i in range(data.ncon):
    fc = np.zeros(6)
    mujoco.mj_contactForce(model, data, i, fc)
    total_fz += fc[2]
print(f'  Total contact Fz: {total_fz:.1f}N (gravity = {P.TOTAL_MASS*9.81:.1f}N)')
print(f'  ncon: {data.ncon}')

# 力矩
print(f'\n  Joint torques (ctrl):')
for jname in P.LEFT_LEG_JOINTS:
    aname = 'M_' + jname[2:]
    aid = act_ids.get(aname)
    if aid is not None:
        print(f'    {jname}: {data.ctrl[aid]:.1f} Nm')

# 检查：如果所有力矩都是0（无控制），系统能否维持当前姿态？
print(f'\n  qfrc_bias at equilibrium:')
for jname in P.LEFT_LEG_JOINTS:
    jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, jname)
    if jid >= 0:
        dof = model.jnt_dofadr[jid]
        print(f'    {jname}: qfrc_bias={data.qfrc_bias[dof]:.1f}')
