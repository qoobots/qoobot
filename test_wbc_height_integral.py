"""测试 WBC 高度积分控制效果"""
import sys
sys.path.insert(0, 'qoobot-os/hal/mechanical/mujoco')

import mujoco
import numpy as np
import qoobot_robot_params as P
from openloong_mpc_wbc import OpenLoongWBC, quat_to_rpy, quat_xyzw_to_rotmat

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

act_ids = {}
for aname in P.ACTUATOR_NAMES:
    aid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_ACTUATOR, aname)
    if aid >= 0:
        act_ids[aname] = aid

# ── 高度积分 PD 控制器 ──
# 策略：高度误差通过积分累积，动态调整膝关节目标角度
z_err_integral = 0.0
knee_correction = 0.0
z_target = CORRECT_HEIGHT

heights = []
knee_angles = []
knee_torques = []
knee_corrections = []

for step in range(2000):
    # 计算高度误差
    z_cur = data.qpos[2]
    z_err = z_target - z_cur
    z_err_integral += z_err * 0.002  # dt = 0.002
    z_err_integral = np.clip(z_err_integral, -0.3, 0.3)

    # 膝关节目标角度修正（高度低 → knee减小 → 腿变长）
    knee_correction = -z_err * 3.0 - z_err_integral * 2.0
    knee_correction = np.clip(knee_correction, -0.3, 0.5)

    # 施加控制
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

                # 膝关节用修正目标
                if 'knee' in jname:
                    q_des += knee_correction
                    kp_j = 800
                    kd_j = 30
                elif 'hip' in jname and 'pitch' in jname:
                    kp_j = 600
                    kd_j = 20
                elif 'ankle' in jname:
                    kp_j = 300
                    kd_j = 15
                else:
                    kp_j = 400
                    kd_j = 15

                torque = kp_j * (q_des - q_cur) - kd_j * qd_cur
                data.ctrl[aid] = np.clip(torque, -396, 396)

    mujoco.mj_step(model, data)

    heights.append(data.qpos[2])
    knee_angles.append(data.qpos[model.jnt_qposadr[mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, 'J_knee_l_pitch')]])
    knee_torques.append(data.ctrl[act_ids['M_knee_l_pitch']])
    knee_corrections.append(knee_correction)

    if step % 500 == 499:
        h_arr = np.array(heights[-100:])
        k_arr = np.array(knee_angles[-100:])
        t_arr = np.array(knee_torques[-100:])
        c_arr = np.array(knee_corrections[-100:])
        print(f'  step {step+1}: h={np.mean(h_arr):.4f}±{np.std(h_arr):.4f}m, '
              f'knee_angle={np.mean(k_arr):.4f}rad, '
              f'knee_torque={np.mean(t_arr):.1f}Nm, '
              f'correction={np.mean(c_arr):.4f}')

h_arr = np.array(heights)
print(f'\nFinal: h={h_arr[-1]:.4f}m, min={h_arr.min():.4f}m, '
      f'drop={h_arr[0]-h_arr[-1]:.4f}m, z_err_integral={z_err_integral:.4f}')
