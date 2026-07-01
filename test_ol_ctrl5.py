"""测试 OpenLoong WBC — 使用正确的初始高度"""
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

act_ids = {}
for aname in P.ACTUATOR_NAMES:
    aid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_ACTUATOR, aname)
    if aid >= 0:
        act_ids[aname] = aid

# 使用较好的姿态 (knee=0.2, hip=-0.2, ankle=0.0)
pose = dict(P.STAND_POSE)
pose['J_hip_l_pitch'] = -0.2
pose['J_hip_r_pitch'] = -0.2
pose['J_knee_l_pitch'] = 0.2
pose['J_knee_r_pitch'] = 0.2
pose['J_ankle_l_pitch'] = 0.0
pose['J_ankle_r_pitch'] = 0.0
CORRECT_HEIGHT = 1.1311  # 此姿态的运动学正确高度

# ── 设置正确姿态和高度 ──
for jname, angle in pose.items():
    jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, jname)
    if jid >= 0:
        data.qpos[model.jnt_qposadr[jid]] = angle
data.qpos[2] = CORRECT_HEIGHT
mujoco.mj_forward(model, data)

print(f'Initial: height={data.qpos[2]:.4f}m')

# ── 创建 WBC 控制器 ──
ctrl = OpenLoongWalkingController(model, data)
ctrl.set_velocity(0.0, 0.0, 0.0)  # 站立模式
ctrl.stand_height = CORRECT_HEIGHT  # 匹配姿态高度

# ── 仿真 2000 步 (4秒) ──
heights = []
knee_torques_L = []
for i in range(2000):
    ctrl.step()
    mujoco.mj_step(model, data)
    heights.append(data.qpos[2])
    knee_torques_L.append(data.ctrl[act_ids["M_knee_l_pitch"]])

    if i % 500 == 499:
        h_arr = np.array(heights[-100:])
        t_arr = np.array(knee_torques_L[-100:])
        print(f'  step {i+1}: height={np.mean(h_arr):.4f}±{np.std(h_arr):.4f}m, '
              f'knee_L={np.mean(t_arr):.1f}Nm, saturated={(np.abs(t_arr)>390).sum()}/100')

h_arr = np.array(heights)
print(f'\nFinal: height={h_arr[-1]:.4f}m, min={h_arr.min():.4f}m, max={h_arr.max():.4f}m, '
      f'drop={h_arr[0]-h_arr[-1]:.4f}m')

if h_arr[-1] > 0.8:
    print('[PASS] Height maintained above 0.8m')
elif h_arr[-1] > 0.5:
    print('[PARTIAL] Height maintained above 0.5m but below 0.8m')
else:
    print('[FAIL] Height dropped below 0.5m')

# ── 额外：打印关节角度偏差 ──
print('\nJoint angle tracking (final state):')
for jname in P.LEFT_LEG_JOINTS + P.RIGHT_LEG_JOINTS:
    jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, jname)
    if jid >= 0:
        q_actual = data.qpos[model.jnt_qposadr[jid]]
        q_des = pose.get(jname, 0.0)
        print(f'  {jname}: des={q_des:.3f}, actual={q_actual:.3f}, err={q_des-q_actual:+.3f}')
