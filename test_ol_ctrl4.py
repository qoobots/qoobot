"""测试 OpenLoong WBC 控制器 — 长时间站立稳定性 + 力矩分析"""
import sys
sys.path.insert(0, 'qoobot-os/hal/mechanical/mujoco')

import mujoco
import numpy as np
import qoobot_robot_params as P
from openloong_mpc_wbc import OpenLoongWalkingController

model_path = 'qoobot-os/hal/mechanical/mujoco/qoobot_float.xml'
model = mujoco.MjModel.from_xml_path(model_path)
model.opt.timestep = 0.002
data = mujoco.MjData(model)

# 执行器索引
act_ids = {}
for aname in P.ACTUATOR_NAMES:
    aid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_ACTUATOR, aname)
    if aid >= 0:
        act_ids[aname] = aid

# 关节 DOF 索引
joint_dof_map = {}
for jname in P.JOINT_NAMES:
    if jname == 'root_joint':
        continue
    jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, jname)
    if jid >= 0:
        joint_dof_map[jname] = model.jnt_dofadr[jid]

# ── 设置站立姿态 ──
for jname, angle in P.STAND_POSE.items():
    jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, jname)
    if jid >= 0:
        data.qpos[model.jnt_qposadr[jid]] = angle
data.qpos[2] = 1.0  # 初始高度
mujoco.mj_forward(model, data)

# ── PD 稳定化 (kp=600) ──
print('=== Phase 1: PD stabilization (kp=600) ===')
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
                data.ctrl[aid] = np.clip(600.0*(q_des - q_cur) - 20.0*qd_cur, -396, 396)
    mujoco.mj_step(model, data)

pd_height = data.qpos[2]
print(f'After PD stabilize: height={pd_height:.4f}m')

# ── 创建 OpenLoong WBC 控制器 ──
ctrl = OpenLoongWalkingController(model, data)
ctrl.set_velocity(0.0, 0.0, 0.0)  # 站立模式

# ── Phase 2: WBC 站立 500 步 (1秒仿真) ──
print('\n=== Phase 2: WBC standing 500 steps (1.0s simulation) ===')

heights = []
rolls = []
pitches = []
knee_torques_L = []
knee_torques_R = []
ankle_torques_L = []
ankle_torques_R = []

for i in range(500):
    gait_info, state = ctrl.step()
    mujoco.mj_step(model, data)

    heights.append(data.qpos[2])
    base_quat = data.qpos[3:7]
    w, x, y, z = base_quat
    roll = np.arctan2(2*(w*x + y*z), 1 - 2*(x*x + y*y))
    pitch = np.arcsin(np.clip(2*(w*y - z*x), -1, 1))
    rolls.append(roll)
    pitches.append(pitch)

    knee_torques_L.append(data.ctrl[act_ids["M_knee_l_pitch"]])
    knee_torques_R.append(data.ctrl[act_ids["M_knee_r_pitch"]])
    ankle_torques_L.append(data.ctrl[act_ids["M_ankle_l_pitch"]])
    ankle_torques_R.append(data.ctrl[act_ids["M_ankle_r_pitch"]])

print(f'Height:  start={heights[0]:.4f}, end={heights[-1]:.4f}, '
      f'min={min(heights):.4f}, max={max(heights):.4f}, '
      f'drop={heights[0]-heights[-1]:.4f}m')
print(f'Roll:   max_abs={max(abs(np.array(rolls))):.4f}rad')
print(f'Pitch:  max_abs={max(abs(np.array(pitches))):.4f}rad')

# ── 力矩统计 ──
print('\n=== Torque Statistics ===')
for name, torques in [('knee_L', knee_torques_L), ('knee_R', knee_torques_R),
                       ('ankle_L', ankle_torques_L), ('ankle_R', ankle_torques_R)]:
    t_arr = np.array(torques)
    print(f'  {name}: mean={np.mean(t_arr):.1f}, std={np.std(t_arr):.1f}, '
          f'min={np.min(t_arr):.1f}, max={np.max(t_arr):.1f}, '
          f'saturated={(np.abs(t_arr) > 390).sum()}/{len(t_arr)}')

# ── Phase 3: WBC 更长站立 (2500步 = 5秒) ──
print('\n=== Phase 3: WBC standing 2500 steps (5.0s simulation) ===')
long_heights = []
for i in range(2500):
    ctrl.step()
    mujoco.mj_step(model, data)
    if i % 500 == 0:
        long_heights.append(data.qpos[2])

print(f'Height every 500 steps: {[f"{h:.4f}" for h in long_heights]}')
print(f'Total drop: {long_heights[0]-long_heights[-1]:.4f}m')

# ── 判断 ──
final_height = data.qpos[2]
if final_height > 0.6 and abs(heights[0] - heights[-1]) < 0.05:
    print('\n[PASS] Controller maintains standing height adequately.')
else:
    print(f'\n[WARN] Height loss may be excessive. final_height={final_height:.4f}m')
