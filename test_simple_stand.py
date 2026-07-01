"""简单测试: 纯 PD 站立是否稳定"""
import sys
sys.path.insert(0, 'qoobot-os/hal/mechanical/mujoco')

import mujoco
import numpy as np
import qoobot_robot_params as P

model_path = 'qoobot-os/hal/mechanical/mujoco/qoobot_float.xml'
model = mujoco.MjModel.from_xml_path(model_path)
model.opt.timestep = 0.002
data = mujoco.MjData(model)

# 构建 actuator 映射
act_ids = {}
for aname in P.ACTUATOR_NAMES:
    aid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_ACTUATOR, aname)
    if aid >= 0:
        act_ids[aname] = aid

# 设置站立姿态
for jname, angle in P.STAND_POSE.items():
    jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, jname)
    if jid >= 0:
        data.qpos[model.jnt_qposadr[jid]] = angle
data.qpos[2] = 1.0
mujoco.mj_forward(model, data)

print('Testing standing with different PD gains...')
print(f'Initial height: {data.qpos[2]:.3f}')
print(f'Gravity compensation needed: {P.TOTAL_MASS * 9.81:.1f} N')

# 测试不同 kp 值
for kp in [200, 400, 600, 800]:
    mujoco.mj_resetData(model, data)
    for jname, angle in P.STAND_POSE.items():
        jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, jname)
        if jid >= 0:
            data.qpos[model.jnt_qposadr[jid]] = angle
    data.qpos[2] = 1.0
    mujoco.mj_forward(model, data)

    heights = []
    for step in range(500):
        for aname in P.ACTUATOR_NAMES:
            jname = 'J_' + aname[2:]
            jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, jname)
            if jid >= 0:
                qpos_addr = model.jnt_qposadr[jid]
                dof_addr = model.jnt_dofadr[jid]
                q_cur = data.qpos[qpos_addr]
                qd_cur = data.qvel[dof_addr]
                q_des = P.STAND_POSE.get(jname, 0.0)
                aid = act_ids.get(aname)
                if aid is not None:
                    data.ctrl[aid] = np.clip(kp*(q_des - q_cur) - 15.0*qd_cur, -396, 396)
        mujoco.mj_step(model, data)
        heights.append(data.qpos[2])

    print(f'  kp={kp}: final_height={data.qpos[2]:.3f}, '
          f'min={min(heights):.3f}, max={max(heights):.3f}, '
          f'mean={np.mean(heights):.3f}')
