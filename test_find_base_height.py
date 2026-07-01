"""计算 STAND_POSE 下正确的基座初始高度"""
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

# 尝试多种姿态
poses = [
    ('original STAND_POSE', P.STAND_POSE),
    ('knee=0.2 hip=-0.2 ankle=0.0', {
        **P.STAND_POSE,
        'J_hip_l_pitch': -0.2, 'J_hip_r_pitch': -0.2,
        'J_knee_l_pitch': 0.2, 'J_knee_r_pitch': 0.2,
        'J_ankle_l_pitch': 0.0, 'J_ankle_r_pitch': 0.0,
    }),
    ('knee=0.4 hip=-0.25 ankle=-0.15', {
        **P.STAND_POSE,
        'J_hip_l_pitch': -0.25, 'J_hip_r_pitch': -0.25,
        'J_knee_l_pitch': 0.4, 'J_knee_r_pitch': 0.4,
        'J_ankle_l_pitch': -0.15, 'J_ankle_r_pitch': -0.15,
    }),
]

lf_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, 'Link_ankle_l_roll')
rf_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, 'Link_ankle_r_roll')

for name, pose in poses:
    print(f'\n=== {name} ===')
    
    # 设置关节角度，基座高度=1.0
    mujoco.mj_resetData(model, data)
    for jname, angle in pose.items():
        jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, jname)
        if jid >= 0:
            data.qpos[model.jnt_qposadr[jid]] = angle
    data.qpos[2] = 1.0
    mujoco.mj_forward(model, data)

    # 找到脚底最低点
    # 左脚 box geom
    for gid in range(model.ngeom):
        if model.geom_bodyid[gid] == lf_id and model.geom_type[gid] == 6:  # box
            gsize = model.geom_size[gid]
            gpos_rel = model.geom_pos[gid]
            lf_bottom_z = data.xpos[lf_id][2] + gpos_rel[2] - gsize[2]
            print(f'  LF bottom z: {lf_bottom_z:.4f}m (foot z={data.xpos[lf_id][2]:.4f}, '
                  f'box center={gpos_rel[2]:.4f}, half_size_z={gsize[2]:.4f})')
        if model.geom_bodyid[gid] == rf_id and model.geom_type[gid] == 6:
            gsize = model.geom_size[gid]
            gpos_rel = model.geom_pos[gid]
            rf_bottom_z = data.xpos[rf_id][2] + gpos_rel[2] - gsize[2]
            print(f'  RF bottom z: {rf_bottom_z:.4f}m (foot z={data.xpos[rf_id][2]:.4f}, '
                  f'box center={gpos_rel[2]:.4f}, half_size_z={gsize[2]:.4f})')

    # 脚底最低点在 base_height=1.0 时低于地面的量
    bottom_min = min(lf_bottom_z, rf_bottom_z)
    # 需要把基座抬高这么多才能让脚底刚好碰到地面
    required_height = 1.0 - bottom_min
    print(f'  Required base height for feet on ground: {required_height:.4f}m')

    # 在基座高度=1.0 时的腿长 (base -> foot 的 z 差)
    leg_z_L = data.qpos[2] - data.xpos[lf_id][2]
    leg_z_R = data.qpos[2] - data.xpos[rf_id][2]
    print(f'  Leg length (base->foot z): L={leg_z_L:.4f}m, R={leg_z_R:.4f}m')

    # 足端 body 中心到脚底 box 底部的偏移
    foot_body_to_bottom_L = -(gpos_rel[2] - gsize[2])  # 需要重新获取
    # 直接算：base_height = leg_z + foot_to_ground_offset
    # foot 的 z 位置 = base_z - leg_z
    # 脚底 = foot_z - foot_body_to_bottom = base_z - leg_z - foot_body_to_bottom
    # 当脚底=0: base_z = leg_z + foot_body_to_bottom
    for gid in range(model.ngeom):
        if model.geom_bodyid[gid] == lf_id and model.geom_type[gid] == 6:
            gpos_rel = model.geom_pos[gid]
            gsize = model.geom_size[gid]
            foot_body_to_bottom = gpos_rel[2] - gsize[2]
    correct_height_L = leg_z_L - foot_body_to_bottom
    correct_height_R = leg_z_R - foot_body_to_bottom
    print(f'  Correct base height (foot bottom at z=0): L={correct_height_L:.4f}m, R={correct_height_R:.4f}m')

    # 直接计算：用正运动学算脚底位置
    # foot bottom = foot_body_xpos.z + (geom_pos.z - geom_size.z)
    # base_height = foot_bottom + (base_z - foot_bottom) = foot_bottom + leg_effective
    # 当 foot_bottom = 0: base_height = 0 + (base_z - foot_bottom)
    # = base_z - (foot_body_z + geom_pos.z - geom_size.z)
    # = base_z - foot_body_z - geom_pos.z + geom_size.z
    # 用 leg_z = base_z - foot_body_z:
    # required_height = leg_z - (geom_pos.z - geom_size.z)
    # = leg_z - geom_pos.z + geom_size.z

    print(f'  Formula check: leg_z - geom_pos.z + geom_size.z = {leg_z_L - gpos_rel[2] + gsize[2]:.4f}')
