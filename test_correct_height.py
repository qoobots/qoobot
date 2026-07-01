"""使用正确的初始高度测试 PD 站立稳定性"""
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

# 使用 knee=0.2, hip=-0.2, ankle=0.0 (最直立)
# 正确初始高度 1.1311m
pose = dict(P.STAND_POSE)
pose['J_hip_l_pitch'] = -0.2
pose['J_hip_r_pitch'] = -0.2
pose['J_knee_l_pitch'] = 0.2
pose['J_knee_r_pitch'] = 0.2
pose['J_ankle_l_pitch'] = 0.0
pose['J_ankle_r_pitch'] = 0.0

CORRECT_HEIGHT = 1.1311

for kp in [200, 400, 600]:
    mujoco.mj_resetData(model, data)
    for jname, angle in pose.items():
        jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, jname)
        if jid >= 0:
            data.qpos[model.jnt_qposadr[jid]] = angle
    data.qpos[2] = CORRECT_HEIGHT  # 正确的初始高度！
    mujoco.mj_forward(model, data)

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
                    data.ctrl[aid] = np.clip(kp*(q_des - q_cur) - 20.0*qd_cur, -396, 396)
        mujoco.mj_step(model, data)
        if step in [99, 199, 299, 499, 999, 1499, 1999, 2999]:
            snapshots.append((step+1, data.qpos[2]))

    heights_str = ', '.join([f't={t}:{h:.3f}' for t, h in snapshots])
    final_h = data.qpos[2]
    print(f'kp={kp}: final_h={final_h:.3f}, [{heights_str}]')
