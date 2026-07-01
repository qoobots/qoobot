"""寻找稳定的站立姿态"""
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

# 尝试不同的 knee 角度 (更直立)
for knee_angle in [0.2, 0.3, 0.4, 0.5, 0.536]:
    for hip_pitch in [-0.2, -0.25, -0.3, -0.33]:
        ankle_pitch = -(hip_pitch + knee_angle)  # 保持足底水平
        
        mujoco.mj_resetData(model, data)
        pose = dict(P.STAND_POSE)
        pose['J_hip_l_pitch'] = hip_pitch
        pose['J_hip_r_pitch'] = hip_pitch
        pose['J_knee_l_pitch'] = knee_angle
        pose['J_knee_r_pitch'] = knee_angle
        pose['J_ankle_l_pitch'] = ankle_pitch
        pose['J_ankle_r_pitch'] = ankle_pitch

        for jname, angle in pose.items():
            jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, jname)
            if jid >= 0:
                data.qpos[model.jnt_qposadr[jid]] = angle
        data.qpos[2] = 1.0
        mujoco.mj_forward(model, data)

        heights = []
        kp = 600
        for step in range(300):
            for aname in P.ACTUATOR_NAMES:
                jname = 'J_' + aname[2:]
                jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, jname)
                if jid >= 0:
                    qpos_addr = model.jnt_qposadr[jid]
                    dof_addr = model.jnt_dofadr[jid]
                    q_cur = data.qpos[qpos_addr]
                    qd_cur = data.qvel[dof_addr]
                    q_des = pose.get(jname, 0.0)
                    aid = act_ids.get(aname)
                    if aid is not None:
                        data.ctrl[aid] = np.clip(kp*(q_des - q_cur) - 20.0*qd_cur, -396, 396)
            mujoco.mj_step(model, data)
            heights.append(data.qpos[2])

        final_h = data.qpos[2]
        if final_h > 0.8:
            print(f'  ** GOOD ** knee={knee_angle:.3f}, hip_pitch={hip_pitch:.3f}, '
                  f'ankle={ankle_pitch:.3f}: final_h={final_h:.3f}, mean_h={np.mean(heights):.3f}')
        else:
            print(f'  knee={knee_angle:.3f}, hip_pitch={hip_pitch:.3f}, '
                  f'ankle={ankle_pitch:.3f}: final_h={final_h:.3f}')
