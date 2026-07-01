"""分析脚底几何形状和接触"""
import sys
sys.path.insert(0, 'qoobot-os/hal/mechanical/mujoco')

import mujoco
import numpy as np
import qoobot_robot_params as P

model_path = 'qoobot-os/hal/mechanical/mujoco/qoobot_float.xml'
model = mujoco.MjModel.from_xml_path(model_path)
model.opt.timestep = 0.002
data = mujoco.MjData(model)

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

lf_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, 'Link_ankle_l_roll')
rf_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, 'Link_ankle_r_roll')

# 检查脚底 box 在世界坐标系中的姿态
for side, body_id in [('L', lf_id), ('R', rf_id)]:
    for gid in range(model.ngeom):
        if model.geom_bodyid[gid] == body_id and model.geom_type[gid] == 6:
            gsize = model.geom_size[gid]
            gpos_rel = model.geom_pos[gid]
            gquat_rel = model.geom_quat[gid]

            # geom 在世界坐标系中的位置和旋转
            # 注意：MuJoCo 存储的是相对于 body frame 的
            body_xpos = data.xpos[body_id]
            body_xmat = data.xmat[body_id].reshape(3, 3)

            # geom 中心在世界坐标系
            geom_center_world = body_xpos + body_xmat @ gpos_rel

            # box 8 个角点在世界坐标系（相对于 geom 中心）
            sx, sy, sz = gsize
            corners_local = np.array([
                [ sx,  sy,  sz], [ sx,  sy, -sz], [ sx, -sy,  sz], [ sx, -sy, -sz],
                [-sx,  sy,  sz], [-sx,  sy, -sz], [-sx, -sy,  sz], [-sx, -sy, -sz],
            ])

            # geom 的旋转矩阵（世界系）
            # 简化：body 的旋转矩阵就是 geom 的（如果 geom 没有额外旋转）
            # 实际上 geom_quat 也需要考虑，但这里先简化
            corners_world = geom_center_world + corners_local @ body_xmat.T

            min_z = corners_world[:, 2].min()
            max_z = corners_world[:, 2].max()

            print(f'{side} foot box:')
            print(f'  geom_center_world = {geom_center_world}')
            print(f'  box size = [{sx*2:.4f}, {sy*2:.4f}, {sz*2:.4f}] (full)')
            print(f'  corners z range = [{min_z:.4f}, {max_z:.4f}]')
            print(f'  bottom surface z = {min_z:.4f} (should be 0 for perfect contact)')
            print(f'  top surface z = {max_z:.4f}')

            # 检查脚底是否水平
            # 底部四个角的 z 值应该相同
            bottom_corners = corners_world[corners_world[:, 2] < (min_z + 0.001)]
            if len(bottom_corners) > 0:
                print(f'  bottom corners z: {bottom_corners[:, 2]}')

# 检查 body 姿态
print(f'\nBody orientations:')
for side, body_id in [('L', lf_id), ('R', rf_id)]:
    xmat = data.xmat[body_id].reshape(3, 3)
    # 提取欧拉角
    roll = np.arctan2(xmat[2,1], xmat[2,2])
    pitch = np.arcsin(-xmat[2,0])
    yaw = np.arctan2(xmat[1,0], xmat[0,0])
    print(f'  {side} foot body rpy: [{np.degrees(roll):.1f}, {np.degrees(pitch):.1f}, {np.degrees(yaw):.1f}] deg')
    print(f'    xmat[:,2] (local z in world) = {xmat[:,2]}')

# 检查 CoM 位置
print(f'\nSystem CoM (subtree_com):')
mujoco.mj_forward(model, data)
com = data.subtree_com[0].copy()  # body 0 = world
print(f'  CoM: {com}')
print(f'  CoM relative to base: {com - data.qpos[0:3]}')
print(f'  CoM x/y relative to foot center:')
lf_xy = data.xpos[lf_id][0:2]
rf_xy = data.xpos[rf_id][0:2]
foot_center_xy = (lf_xy + rf_xy) / 2
print(f'  Foot center xy: {foot_center_xy}')
print(f'  CoM - foot_center: {com[0:2] - foot_center_xy}')
print(f'  Support polygon: L={lf_xy}, R={rf_xy}')
