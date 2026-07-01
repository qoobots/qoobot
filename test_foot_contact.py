"""检查足端接触情况"""
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

# 使用较好的姿态: knee=0.2, hip=-0.2, ankle=0.0
pose = dict(P.STAND_POSE)
pose['J_hip_l_pitch'] = -0.2
pose['J_hip_r_pitch'] = -0.2
pose['J_knee_l_pitch'] = 0.2
pose['J_knee_r_pitch'] = 0.2
pose['J_ankle_l_pitch'] = 0.0
pose['J_ankle_r_pitch'] = 0.0

for jname, angle in pose.items():
    jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, jname)
    if jid >= 0:
        data.qpos[model.jnt_qposadr[jid]] = angle
data.qpos[2] = 1.0
mujoco.mj_forward(model, data)

# 获取足端 body
lf_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, 'Link_ankle_l_roll')
rf_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, 'Link_ankle_r_roll')

# 获取足底 geom (box)
# 遍历所有 geom 找到属于足端 body 的
print('Foot geoms:')
for gid in range(model.ngeom):
    if model.geom_bodyid[gid] in (lf_id, rf_id):
        side = 'L' if model.geom_bodyid[gid] == lf_id else 'R'
        gtype = model.geom_type[gid]
        gsize = model.geom_size[gid].copy()
        gpos = model.geom_pos[gid].copy()
        gquat = model.geom_quat[gid].copy()
        contype = model.geom_contype[gid]
        conaffinity = model.geom_conaffinity[gid]
        print(f'  geom[{gid}] body={side}, type={gtype}, size={gsize}, '
              f'pos={gpos}, contype={contype}, conaffinity={conaffinity}')

# 检查接触
print(f'\nInitial state:')
print(f'  Base pos: {data.qpos[0:3]}')
print(f'  LF xpos: {data.xpos[lf_id]}')
print(f'  RF xpos: {data.xpos[rf_id]}')

# 检查 contact
print(f'\nContacts ({data.ncon}):')
for i in range(data.ncon):
    g1 = data.contact[i].geom1
    g2 = data.contact[i].geom2
    b1 = model.geom_bodyid[g1]
    b2 = model.geom_bodyid[g2]
    pos = data.contact[i].pos.copy()
    frame = data.contact[i].frame.copy()
    print(f'  contact[{i}]: body[{b1}]-body[{b2}], pos={pos}, '
          f'penetration={data.contact[i].dist:.6f}')

# 检查脚底最低点
for side, body_id in [('L', lf_id), ('R', rf_id)]:
    for gid in range(model.ngeom):
        if model.geom_bodyid[gid] == body_id and model.geom_type[gid] == 6:  # box
            gsize = model.geom_size[gid]
            gpos_rel = model.geom_pos[gid]
            # geom 在世界坐标系中的位置和姿态
            # 需要计算底部最低点
            print(f'\n  {side} foot box: size={gsize}, pos_rel={gpos_rel}')
            # box 最低点 z = xpos[2] + local_bottom_z (在 body 坐标系中)
            # local_bottom_z = pos_rel[2] - size[2]
            local_bottom = gpos_rel[2] - gsize[2]
            print(f'    local_bottom_z={local_bottom:.4f}')

# 运行几步看看接触力
print('\n=== PD standing, checking contact forces ===')
for step in range(10):
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
                q_des = pose.get(jname, 0.0)
                data.ctrl[aid] = np.clip(600*(q_des - q_cur) - 20.0*qd_cur, -396, 396)
    mujoco.mj_step(model, data)

    # 计算接触力
    total_fz = 0.0
    for i in range(data.ncon):
        # 接触力在 contact frame 中
        fc = np.zeros(6)
        mujoco.mj_contactForce(model, data, i, fc)
        fz = fc[2]  # contact frame 的 z 分量 (法向)
        total_fz += fz

    print(f'  step {step}: height={data.qpos[2]:.4f}, ncon={data.ncon}, '
          f'total_fz={total_fz:.1f}N, LF_z={data.xpos[lf_id][2]:.4f}, '
          f'RF_z={data.xpos[rf_id][2]:.4f}')
