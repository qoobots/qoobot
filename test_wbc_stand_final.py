"""综合测试：OpenLoong MPC+WBC 控制器站立稳定性"""
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

# 设置 STAND_POSE
for jname, angle in P.STAND_POSE.items():
    jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, jname)
    if jid >= 0:
        data.qpos[model.jnt_qposadr[jid]] = angle
data.qpos[2] = 1.11  # STAND_POSE 运动学高度
mujoco.mj_forward(model, data)

# 初始化控制器（会自动 sync_pose_from_data 和读取 stand_height）
ctrl = OpenLoongWalkingController(model, data)

# 设置为站立模式（速度为 0）
ctrl.set_velocity(0.0, 0.0, 0.0)

# 手动修正 stand_height
ctrl.stand_height = 1.11
print(f'Stand height: {ctrl.stand_height}')
print(f'Virtual base enabled: {ctrl._virtual_base_enabled}')

heights = []
rolls = []
pitches = []

for step in range(3000):
    ctrl.step()
    mujoco.mj_step(model, data)

    quat = data.qpos[3:7]
    w, x, y, z = quat[0], quat[1], quat[2], quat[3]
    roll = np.arctan2(2*(w*x + y*z), 1 - 2*(x*x + y*y))
    pitch = np.arcsin(np.clip(2*(w*y - z*x), -1, 1))

    heights.append(data.qpos[2])
    rolls.append(np.degrees(roll))
    pitches.append(np.degrees(pitch))

    if step % 500 == 0:
        print(f'  step {step}: h={data.qpos[2]:.4f}, roll={np.degrees(roll):.1f}°, '
              f'pitch={np.degrees(pitch):.1f}°')

h_arr = np.array(heights)
r_arr = np.array(rolls)
p_arr = np.array(pitches)

print(f'\n=== OpenLoong MPC+WBC + Virtual Base (3000 steps) ===')
print(f'Final height: {h_arr[-1]:.4f}m')
print(f'Steady height: {np.mean(h_arr[-500:]):.4f}±{np.std(h_arr[-500:]):.4f}')
print(f'Min height: {h_arr.min():.4f}')
print(f'Final roll: {r_arr[-1]:.1f}°')
print(f'Final pitch: {p_arr[-1]:.1f}°')
print(f'Max |roll|: {np.max(np.abs(r_arr)):.1f}°')
print(f'Max |pitch|: {np.max(np.abs(p_arr)):.1f}°')

# 检查关节跟踪
print(f'\nFinal joint angles vs targets (left leg):')
for jname in P.LEFT_LEG_JOINTS:
    jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, jname)
    if jid >= 0:
        q_cur = data.qpos[model.jnt_qposadr[jid]]
        q_des = P.STAND_POSE.get(jname, 0.0)
        print(f'  {jname}: actual={q_cur:.4f}, target={q_des:.4f}, err={q_des-q_cur:+.4f}')

# 检查虚拟基座力和力矩
base_body_id = ctrl._base_body_id
print(f'\nVirtual base wrench:')
print(f'  F_virtual = {data.xfrc_applied[base_body_id,:3]}')
print(f'  T_virtual = {data.xfrc_applied[base_body_id,3:6]}')

# 足端接触力
mujoco.mj_forward(model, data)
total_fz = 0.0
for i in range(data.ncon):
    fc = np.zeros(6)
    mujoco.mj_contactForce(model, data, i, fc)
    total_fz += fc[2]
print(f'  Contact Fz: {total_fz:.1f}N (gravity={P.TOTAL_MASS*9.81:.1f}N)')
print(f'  Virtual Fz + Contact Fz = {data.xfrc_applied[base_body_id,2] + total_fz:.1f}N')

# 判断结果
success = (h_arr[-1] > 0.8 and abs(r_arr[-1]) < 10 and abs(p_arr[-1]) < 10)
print(f'\n{"✓ 站立成功!" if success else "✗ 站立失败"}')
