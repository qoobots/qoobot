"""计算 STAND_POSE 下所需的重力补偿力矩"""
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

# 使用较好的姿态
pose = dict(P.STAND_POSE)
pose['J_hip_l_pitch'] = -0.2
pose['J_hip_r_pitch'] = -0.2
pose['J_knee_l_pitch'] = 0.2
pose['J_knee_r_pitch'] = 0.2
pose['J_ankle_l_pitch'] = 0.0
pose['J_ankle_r_pitch'] = 0.0

# 设置姿态和正确高度
for jname, angle in pose.items():
    jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, jname)
    if jid >= 0:
        data.qpos[model.jnt_qposadr[jid]] = angle
data.qpos[2] = 1.1311  # 正确高度

# 固定关节 (除了浮动基座)
# 方法：把所有关节的 qfrc_bias 读出来，这就是重力补偿力矩
mujoco.mj_forward(model, data)

# 获取所有关节的 DOF 地址
joint_dof_map = {}
for jname in P.JOINT_NAMES:
    if jname == 'root_joint':
        continue
    jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, jname)
    if jid >= 0:
        joint_dof_map[jname] = model.jnt_dofadr[jid]

# qfrc_bias 包含了重力、科里奥利力等
# 在零速度时，qfrc_bias = -gravity_torque (需要施加的补偿力矩)
print('Gravity compensation torques (qfrc_bias in STAND_POSE):')
print(f'  Base height: {data.qpos[2]:.4f}m')

for jname, dof in sorted(joint_dof_map.items(), key=lambda x: x[1]):
    if dof < model.nv:
        bias = data.qfrc_bias[dof]
        if abs(bias) > 0.01:
            print(f'  {jname} (dof={dof}): {bias:+.2f} Nm')

# 腿部关节汇总
print('\nLeg joint gravity comp summary:')
for leg_name, leg_joints in [('Left', P.LEFT_LEG_JOINTS), ('Right', P.RIGHT_LEG_JOINTS)]:
    total = 0.0
    for jname in leg_joints:
        dof = joint_dof_map.get(jname)
        if dof is not None:
            total += abs(data.qfrc_bias[dof])
    print(f'  {leg_name} leg total: {total:.2f} Nm')

# 也测试不同高度下的重力补偿力矩
print('\n=== Gravity comp at different heights ===')
for h in [1.1311, 1.0, 0.8, 0.5, 0.2]:
    mujoco.mj_resetData(model, data)
    for jname, angle in pose.items():
        jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, jname)
        if jid >= 0:
            data.qpos[model.jnt_qposadr[jid]] = angle
    data.qpos[2] = h
    mujoco.mj_forward(model, data)

    # 脚底 z
    lf_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, 'Link_ankle_l_roll')
    foot_z = data.xpos[lf_id][2]
    # 脚底 box 底部
    for gid in range(model.ngeom):
        if model.geom_bodyid[gid] == lf_id and model.geom_type[gid] == 6:
            bottom_z = foot_z + model.geom_pos[gid][2] - model.geom_size[gid][2]

    knee_torque = data.qfrc_bias[joint_dof_map['J_knee_l_pitch']]
    hip_torque = data.qfrc_bias[joint_dof_map['J_hip_l_pitch']]
    ankle_torque = data.qfrc_bias[joint_dof_map['J_ankle_l_pitch']]
    print(f'  h={h:.4f}: foot_bottom_z={bottom_z:.4f}, '
          f'knee={knee_torque:+.1f}, hip_pitch={hip_torque:+.1f}, ankle={ankle_torque:+.1f}')
