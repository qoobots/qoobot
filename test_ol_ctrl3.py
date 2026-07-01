"""测试 OpenLoong 控制器 - 打印力矩值"""
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

# 设置站立姿态并稳定化
for jname, angle in P.STAND_POSE.items():
    jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, jname)
    if jid >= 0:
        data.qpos[model.jnt_qposadr[jid]] = angle
data.qpos[2] = 1.0
mujoco.mj_forward(model, data)

print('Stabilizing...')
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

print(f'After stabilize: height={data.qpos[2]:.3f}')

# 创建控制器 (先站立)
ctrl = OpenLoongWalkingController(model, data)
ctrl.set_velocity(0.0, 0.0, 0.0)

# 打印第一帧的力矩
print('\n=== First WBC step ===')
gait_info, state = ctrl.step()
print(f'height={data.qpos[2]:.3f}, leg_state={gait_info["leg_state"]}')
print('ctrl values (left leg):')
for jname in P.LEFT_LEG_JOINTS:
    aname = 'M_' + jname[2:]
    aid = act_ids.get(aname)
    if aid is not None:
        print(f'  {aname}: {data.ctrl[aid]:.1f} Nm')
print('ctrl values (right leg):')
for jname in P.RIGHT_LEG_JOINTS:
    aname = 'M_' + jname[2:]
    aid = act_ids.get(aname)
    if aid is not None:
        print(f'  {aname}: {data.ctrl[aid]:.1f} Nm')

# 仿真几步看高度变化
print('\n=== Simulating 10 steps ===')
for i in range(10):
    ctrl.step()
    h_before = data.qpos[2]
    mujoco.mj_step(model, data)
    print(f'  step {i}: height {h_before:.4f} -> {data.qpos[2]:.4f} (delta={data.qpos[2]-h_before:.4f}), '
          f'M_knee_l_pitch={data.ctrl[act_ids["M_knee_l_pitch"]]:.1f}')

# 继续更多步
print('\n=== 100 more steps ===')
heights = []
for i in range(100):
    ctrl.step()
    mujoco.mj_step(model, data)
    heights.append(data.qpos[2])
print(f'Height: start={heights[0]:.3f}, end={heights[-1]:.3f}, '
      f'min={min(heights):.3f}, max={max(heights):.3f}')
