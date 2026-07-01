"""分析足端力映射对关节力矩的影响方向"""
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

# 获取足端雅可比
lf_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, 'Link_ankle_l_roll')
rf_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, 'Link_ankle_r_roll')

nv = model.nv
jacp_L = np.zeros((3, nv))
jacr_L = np.zeros((3, nv))
jacp_R = np.zeros((3, nv))
jacr_R = np.zeros((3, nv))

mujoco.mj_jac(model, data, jacp_L, jacr_L, np.zeros(3), lf_id)
mujoco.mj_jac(model, data, jacp_R, jacr_R, np.zeros(3), rf_id)

# 对于每个腿关节，显示 d(foot_pos)/d(joint) 向量
leg_joints = P.LEFT_LEG_JOINTS
print('Left foot Jacobian (d(foot_world_pos)/d(joint)):')
print(f'  Base height: {data.qpos[2]:.4f}m')
print(f'  Foot pos: {data.xpos[lf_id]}')

for jname in leg_joints:
    jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, jname)
    dof = model.jnt_dofadr[jid]
    if dof < nv:
        j_col = jacp_L[:, dof]
        print(f'  {jname}: dfoot/dq = [{j_col[0]:.4f}, {j_col[1]:.4f}, {j_col[2]:.4f}], |dfoot/dq|={np.linalg.norm(j_col):.4f}')

# 分析：在脚底施加 F_z = 379N 向上力，对各关节的力矩
# tau_j = J^T @ F = J_z_col * F_z (如果 F = [0, 0, Fz])
F_z = P.TOTAL_MASS * 9.81 / 2  # 每腿 379N
print(f'\nTorque from F_z={F_z:.1f}N upward at left foot:')
for jname in leg_joints:
    jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, jname)
    dof = model.jnt_dofadr[jid]
    if dof < nv:
        tau_from_fz = jacp_L[2, dof] * F_z
        print(f'  {jname}: tau={tau_from_fz:+.1f} Nm')

# 正向力 (向上) 应该产生什么效果？
# d(foot_z)/d(knee) > 0 → 膝盖弯曲使脚下降 → Fz_up 产生负膝盖力矩（伸直膝盖）
# 这是正确的！

# 现在模拟一步 WBC，但去掉足端力映射，看纯 PD 能维持多久
print('\n=== Pure PD (no force mapping) test ===')
from openloong_mpc_wbc import OpenLoongWBC

wbc = OpenLoongWBC(model)
wbc.sync_pose_from_data(data)

tau_pd_only = np.zeros(nv)
for jname in P.LEFT_LEG_JOINTS + P.RIGHT_LEG_JOINTS:
    dof = wbc.joint_dof_map.get(jname)
    if dof is None or dof >= nv:
        continue
    q_cur = data.qpos[dof] if dof < len(data.qpos) else 0
    q_des = wbc.q_des_stand[dof]
    kp = 600
    kd = 20
    tau_pd_only[dof] = kp * (q_des - q_cur) - kd * data.qvel[dof] if dof < len(data.qvel) else 0

print('Pure PD torques (initial):')
for jname in P.LEFT_LEG_JOINTS:
    dof = wbc.joint_dof_map.get(jname)
    if dof is not None and dof < nv:
        print(f'  {jname}: tau={tau_pd_only[dof]:+.1f} Nm')

# 纯 PD 仿真 500 步
act_ids = {}
for aname in P.ACTUATOR_NAMES:
    aid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_ACTUATOR, aname)
    if aid >= 0:
        act_ids[aname] = aid

heights_pd = []
for step in range(500):
    for aname in P.ACTUATOR_NAMES:
        jname = 'J_' + aname[2:]
        jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, jname)
        if jid >= 0:
            dof = model.jnt_dofadr[jid]
            aid = act_ids.get(aname)
            if aid is not None:
                q_cur = data.qpos[model.jnt_qposadr[jid]]
                qd_cur = data.qvel[dof]
                q_des = pose.get(jname, 0.0)
                data.ctrl[aid] = np.clip(600*(q_des - q_cur) - 20*qd_cur, -396, 396)
    mujoco.mj_step(model, data)
    heights_pd.append(data.qpos[2])
    if step % 100 == 99:
        print(f'  step {step+1}: height={data.qpos[2]:.4f}')

print(f'Pure PD final height: {heights_pd[-1]:.4f}m (drop={heights_pd[0]-heights_pd[-1]:.4f})')
