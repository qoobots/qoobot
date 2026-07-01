"""测量 STAND_POSE 在不同 PD 增益下的稳态高度"""
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

for kp in [200, 300, 400, 500, 600, 800, 1000]:
    # 重置
    mujoco.mj_resetData(model, data)
    for jname, angle in P.STAND_POSE.items():
        jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, jname)
        if jid >= 0:
            data.qpos[model.jnt_qposadr[jid]] = angle
    data.qpos[2] = 1.0
    mujoco.mj_forward(model, data)

    # 稳定化 500 步
    for _ in range(500):
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
                    data.ctrl[aid] = np.clip(kp*(q_des - q_cur) - 20.0*qd_cur, -396, 396)
        mujoco.mj_step(model, data)

    # 再跑 200 步取平均值
    heights = []
    for _ in range(200):
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
                    data.ctrl[aid] = np.clip(kp*(q_des - q_cur) - 20.0*qd_cur, -396, 396)
        mujoco.mj_step(model, data)
        heights.append(data.qpos[2])

    avg_h = np.mean(heights)
    std_h = np.std(heights)
    print(f'kp={kp:4d}: height={avg_h:.4f} ± {std_h:.4f}m')

# 再测量足端位置
print('\n=== Foot positions at kp=600 steady state ===')
mujoco.mj_resetData(model, data)
for jname, angle in P.STAND_POSE.items():
    jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, jname)
    if jid >= 0:
        data.qpos[model.jnt_qposadr[jid]] = angle
data.qpos[2] = 1.0
mujoco.mj_forward(model, data)
for _ in range(500):
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
                data.ctrl[aid] = np.clip(600*(q_des - q_cur) - 20.0*qd_cur, -396, 396)
    mujoco.mj_step(model, data)

for _ in range(200):
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
                data.ctrl[aid] = np.clip(600*(q_des - q_cur) - 20.0*qd_cur, -396, 396)
    mujoco.mj_step(model, data)

lf_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, 'Link_ankle_l_roll')
rf_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, 'Link_ankle_r_roll')
print(f'Base height: {data.qpos[2]:.4f}m')
print(f'Left foot:  xpos={data.xpos[lf_id]}')
print(f'Right foot: xpos={data.xpos[rf_id]}')
print(f'Foot z positions: L={data.xpos[lf_id][2]:.4f}, R={data.xpos[rf_id][2]:.4f}')
