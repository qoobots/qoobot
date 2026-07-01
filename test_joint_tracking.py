"""诊断 PD 控制下关节实际角度跟踪情况"""
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

# 设置姿态和高度
for jname, angle in pose.items():
    jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, jname)
    if jid >= 0:
        data.qpos[model.jnt_qposadr[jid]] = angle
data.qpos[2] = CORRECT_HEIGHT
mujoco.mj_forward(model, data)

# 获取重力补偿
gravity_comp = data.qfrc_bias.copy()

joint_dof_map = {}
for jname in P.JOINT_NAMES:
    if jname == 'root_joint':
        continue
    jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, jname)
    if jid >= 0:
        joint_dof_map[jname] = model.jnt_dofadr[jid]

# 重点跟踪的关节
track_joints = ['J_knee_l_pitch', 'J_hip_l_pitch', 'J_ankle_l_pitch',
                'J_knee_r_pitch', 'J_hip_r_pitch', 'J_ankle_r_pitch']
track_dofs = {j: joint_dof_map[j] for j in track_joints if j in joint_dof_map}

# 运行 500 步，记录关节角度偏差
joint_errors = {j: [] for j in track_joints}
heights = []
torques = {j: [] for j in track_joints}

for step in range(500):
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
                kp = 600
                kd = 20
                ff = gravity_comp[dof_addr] if dof_addr < model.nv else 0
                torque = kp*(q_des - q_cur) - kd*qd_cur + ff
                clamped = np.clip(torque, -396, 396)
                data.ctrl[aid] = clamped

                if jname in track_joints:
                    joint_errors[jname].append(q_des - q_cur)
                    torques[jname].append(clamped)

    mujoco.mj_step(model, data)
    heights.append(data.qpos[2])

# 输出
print('Joint tracking errors (q_des - q_actual) over 500 steps:')
for jname in track_joints:
    err = np.array(joint_errors[jname])
    tq = np.array(torques[jname])
    print(f'  {jname}: err_mean={np.mean(err):+.4f}rad, err_max={np.max(np.abs(err)):.4f}rad, '
          f'torque_mean={np.mean(tq):+.1f}Nm, torque_sat={(np.abs(tq)>390).sum()}/500')

print(f'\nHeight: start={heights[0]:.4f}, end={heights[-1]:.4f}')

# ── 检查：是否有特定关节导致不稳定 ──
# 试试把 kp 提高到 2000 会怎样
print('\n=== kp=2000 for knees only ===')
mujoco.mj_resetData(model, data)
for jname, angle in pose.items():
    jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, jname)
    if jid >= 0:
        data.qpos[model.jnt_qposadr[jid]] = angle
data.qpos[2] = CORRECT_HEIGHT
mujoco.mj_forward(model, data)

for step in range(1000):
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
                ff = gravity_comp[dof_addr] if dof_addr < model.nv else 0
                # knee 用极高增益
                if 'knee' in jname:
                    kp_j, kd_j = 2000, 40
                elif 'hip' in jname and 'pitch' in jname:
                    kp_j, kd_j = 800, 20
                else:
                    kp_j, kd_j = 600, 20
                torque = kp_j*(q_des - q_cur) - kd_j*qd_cur + ff
                data.ctrl[aid] = np.clip(torque, -396, 396)
    mujoco.mj_step(model, data)
    if step % 200 == 199:
        print(f'  step {step+1}: height={data.qpos[2]:.4f}')

print(f'Final height: {data.qpos[2]:.4f}')
