"""检查在正确高度下的接触稳定性"""
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

# 姿态
pose = dict(P.STAND_POSE)
pose['J_hip_l_pitch'] = -0.2
pose['J_hip_r_pitch'] = -0.2
pose['J_knee_l_pitch'] = 0.2
pose['J_knee_r_pitch'] = 0.2
pose['J_ankle_l_pitch'] = 0.0
pose['J_ankle_r_pitch'] = 0.0

CORRECT_HEIGHT = 1.1311
lf_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, 'Link_ankle_l_roll')
rf_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, 'Link_ankle_r_roll')

for test_h in [CORRECT_HEIGHT, CORRECT_HEIGHT + 0.001, CORRECT_HEIGHT - 0.001]:
    mujoco.mj_resetData(model, data)
    for jname, angle in pose.items():
        jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, jname)
        if jid >= 0:
            data.qpos[model.jnt_qposadr[jid]] = angle
    data.qpos[2] = test_h
    mujoco.mj_forward(model, data)

    # 脚底最低点
    for gid in range(model.ngeom):
        if model.geom_bodyid[gid] == lf_id and model.geom_type[gid] == 6:
            gsize = model.geom_size[gid]
            gpos_rel = model.geom_pos[gid]
            lf_bottom = data.xpos[lf_id][2] + gpos_rel[2] - gsize[2]
        if model.geom_bodyid[gid] == rf_id and model.geom_type[gid] == 6:
            gsize = model.geom_size[gid]
            gpos_rel = model.geom_pos[gid]
            rf_bottom = data.xpos[rf_id][2] + gpos_rel[2] - gsize[2]

    print(f'\nbase_h={test_h:.4f}: LF_bottom={lf_bottom:.6f}, RF_bottom={rf_bottom:.6f}, '
          f'ncon={data.ncon}')

    # 单步仿真，关闭所有控制，看纯接触力
    data.ctrl[:] = 0.0
    mujoco.mj_step(model, data)

    # 检查接触力
    total_fz = 0.0
    for i in range(data.ncon):
        fc = np.zeros(6)
        mujoco.mj_contactForce(model, data, i, fc)
        total_fz += fc[2]

    print(f'  After 1 step (no control): height={data.qpos[2]:.4f}, '
          f'ncon={data.ncon}, total_fz={total_fz:.1f}N, '
          f'base_vz={data.qvel[2]:.4f}')

# ── 关键测试：加上重力补偿 + PD，看是否能稳定 ──
print('\n\n=== With gravity compensation feedforward + PD ===')
# 获取重力补偿力矩
mujoco.mj_resetData(model, data)
for jname, angle in pose.items():
    jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, jname)
    if jid >= 0:
        data.qpos[model.jnt_qposadr[jid]] = angle
data.qpos[2] = CORRECT_HEIGHT
mujoco.mj_forward(model, data)
gravity_comp = data.qfrc_bias.copy()  # 保存重力补偿

joint_dof_map = {}
for jname in P.JOINT_NAMES:
    if jname == 'root_joint':
        continue
    jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, jname)
    if jid >= 0:
        joint_dof_map[jname] = model.jnt_dofadr[jid]

snapshots = []
for step in range(3000):
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
                # PD + 重力补偿前馈
                kp = 600
                kd = 20
                # 注意：qfrc_bias 已经是需要补偿的值
                ff = gravity_comp[dof_addr] if dof_addr < model.nv else 0
                torque = kp*(q_des - q_cur) - kd*qd_cur + ff
                data.ctrl[aid] = np.clip(torque, -396, 396)
    mujoco.mj_step(model, data)
    if step in [99, 199, 299, 499, 999, 1499, 1999, 2999]:
        snapshots.append((step+1, data.qpos[2]))

heights_str = ', '.join([f't={t}:{h:.3f}' for t, h in snapshots])
print(f'With gravity comp: [{heights_str}]')
print(f'Final height: {data.qpos[2]:.4f}m')
