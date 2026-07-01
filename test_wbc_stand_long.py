"""长时间站立测试：10000 步验证稳定性"""
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

for jname, angle in P.STAND_POSE.items():
    jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, jname)
    if jid >= 0:
        data.qpos[model.jnt_qposadr[jid]] = angle
data.qpos[2] = 1.11
mujoco.mj_forward(model, data)

ctrl = OpenLoongWalkingController(model, data)
ctrl.set_velocity(0.0, 0.0, 0.0)
ctrl.stand_height = 1.11

heights = []
rolls = []
pitches = []

for step in range(10000):
    ctrl.step()
    mujoco.mj_step(model, data)

    quat = data.qpos[3:7]
    w, x, y, z = quat[0], quat[1], quat[2], quat[3]
    roll = np.arctan2(2*(w*x + y*z), 1 - 2*(x*x + y*y))
    pitch = np.arcsin(np.clip(2*(w*y - z*x), -1, 1))

    heights.append(data.qpos[2])
    rolls.append(np.degrees(roll))
    pitches.append(np.degrees(pitch))

    if step % 2000 == 0:
        print(f'  step {step}: h={data.qpos[2]:.4f}, roll={np.degrees(roll):.1f}°, '
              f'pitch={np.degrees(pitch):.1f}°')

h_arr = np.array(heights)
r_arr = np.array(rolls)
p_arr = np.array(pitches)

print(f'\n=== Long-term Standing Test (10000 steps, 20s sim) ===')
print(f'Final height: {h_arr[-1]:.4f}m (target=1.11)')
print(f'Steady height: {np.mean(h_arr[-2000:]):.4f}±{np.std(h_arr[-2000:]):.4f}')
print(f'Min height: {h_arr.min():.4f}')
print(f'Final roll: {r_arr[-1]:.1f}°')
print(f'Final pitch: {p_arr[-1]:.1f}°')
print(f'Max |roll|: {np.max(np.abs(r_arr)):.1f}°')
print(f'Max |pitch|: {np.max(np.abs(p_arr)):.1f}°')

success = (h_arr[-1] > 0.9 and abs(r_arr[-1]) < 10 and abs(p_arr[-1]) < 10)
print(f'\n{"✓ 长期站立成功!" if success else "✗ 长期站立失败"}')
