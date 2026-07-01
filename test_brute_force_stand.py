"""暴力测试各种控制策略能否维持高度 — 包含新的 Wrench-based 策略"""
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

# 使用更稳定的站立姿态（膝关节更直，减小重力力矩臂）
pose = dict(P.STAND_POSE)
pose['J_hip_l_pitch'] = -0.2
pose['J_hip_r_pitch'] = -0.2
pose['J_knee_l_pitch'] = 0.2
pose['J_knee_r_pitch'] = 0.2
pose['J_ankle_l_pitch'] = 0.0
pose['J_ankle_r_pitch'] = 0.0
CORRECT_HEIGHT = 1.1311

# 关节名到 DOF 索引的映射
joint_dof_map = {}
for jname in P.JOINT_NAMES:
    if jname == 'root_joint':
        continue
    jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, jname)
    if jid >= 0:
        joint_dof_map[jname] = model.jnt_dofadr[jid]

# 足端 body ID
foot_body_id = {
    'left': mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, P.LEFT_FOOT_BODY),
    'right': mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, P.RIGHT_FOOT_BODY),
}

LEFT_LEG_JOINTS = P.LEFT_LEG_JOINTS
RIGHT_LEG_JOINTS = P.RIGHT_LEG_JOINTS


def reset_data():
    mujoco.mj_resetData(model, data)
    for jname, angle in pose.items():
        jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, jname)
        if jid >= 0:
            data.qpos[model.jnt_qposadr[jid]] = angle
    data.qpos[2] = CORRECT_HEIGHT
    mujoco.mj_forward(model, data)


def run_test(name, control_fn, steps=2000):
    reset_data()
    heights = []
    rolls = []
    pitches = []
    for step in range(steps):
        control_fn(data, step)
        mujoco.mj_step(model, data)
        heights.append(data.qpos[2])
        # 计算 rpy
        quat = data.qpos[3:7]  # [w,x,y,z]
        w, x, y, z = quat[0], quat[1], quat[2], quat[3]
        roll = np.arctan2(2*(w*x + y*z), 1 - 2*(x*x + y*y))
        pitch = np.arcsin(np.clip(2*(w*y - z*x), -1, 1))
        rolls.append(roll)
        pitches.append(pitch)

    h_arr = np.array(heights)
    steady_h = np.mean(h_arr[-500:])
    steady_std = np.std(h_arr[-500:])
    final_roll = np.degrees(rolls[-1])
    final_pitch = np.degrees(pitches[-1])
    print(f'{name}: final_h={h_arr[-1]:.4f}, steady_h={steady_h:.4f}±{steady_std:.4f}, '
          f'min={h_arr.min():.4f}, roll={final_roll:.1f}°, pitch={final_pitch:.1f}°')
    return h_arr[-1] > 0.5


def get_foot_jacobian(data, side):
    body_id = foot_body_id.get(side, -1)
    if body_id < 0:
        return np.zeros((6, model.nv))
    jacp = np.zeros((3, model.nv))
    jacr = np.zeros((3, model.nv))
    mujoco.mj_jac(model, data, jacp, jacr, np.zeros(3), body_id)
    J = np.zeros((6, model.nv))
    J[:3, :] = jacp
    J[3:6, :] = jacr
    return J


# ── 测试1: 极高增益 PD ──
def ctrl_high_kp(data, step):
    for aname in P.ACTUATOR_NAMES:
        jname = 'J_' + aname[2:]
        jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, jname)
        if jid >= 0:
            q_cur = data.qpos[model.jnt_qposadr[jid]]
            qd_cur = data.qvel[model.jnt_dofadr[jid]]
            q_des = pose.get(jname, 0.0)
            aid = act_ids.get(aname)
            if aid is not None:
                if 'knee' in jname:
                    kp, kd = 2000, 40
                elif 'hip' in jname and 'pitch' in jname:
                    kp, kd = 1500, 30
                else:
                    kp, kd = 800, 20
                data.ctrl[aid] = np.clip(kp*(q_des - q_cur) - kd*qd_cur, -396, 396)


# ── 测试2: Wrench-based 站立控制 ──
def ctrl_wrench_based(data, step):
    """通过足端力映射实现基座 wrench 控制"""
    nv = model.nv
    tau = np.zeros(nv)

    # 高度 PD
    z_err = CORRECT_HEIGHT - data.qpos[2]
    z_vel = data.qvel[2]
    gravity_comp = P.TOTAL_MASS * 9.81
    Fz_des = gravity_comp + 2000*z_err + 300*(z_err * 0.002) - 200*z_vel
    Fz_des = max(0, Fz_des)

    # 姿态误差
    quat_cur = data.qpos[3:7]  # [w,x,y,z]
    w, x, y, z = quat_cur[0], quat_cur[1], quat_cur[2], quat_cur[3]
    # 期望姿态: [1,0,0,0] (直立)
    roll = np.arctan2(2*(w*x + y*z), 1 - 2*(x*x + y*y))
    pitch = np.arcsin(np.clip(2*(w*y - z*x), -1, 1))
    omega = data.qvel[3:6]

    Tx_des = 800*(-roll) - 40*omega[0]
    Ty_des = 800*(-pitch) - 40*omega[1]

    base_pos = data.qpos[0:3]

    # 双足支撑：分配力
    for leg_side, foot_body in [('left', 'left'), ('right', 'right')]:
        J = get_foot_jacobian(data, foot_body)
        J_lin = J[:3, 6:]

        foot_pos = data.xpos[foot_body_id[foot_body]].copy()
        r = foot_pos - base_pos

        fz = Fz_des / 2.0  # 均分重力

        # 通过 y 方向力差产生 roll 力矩
        fx = 0.0
        fy = 0.0
        if leg_side == 'left':
            fx = -Tx_des / (2 * abs(r[1]) + 1e-3)  # roll
        else:
            fx = Tx_des / (2 * abs(r[1]) + 1e-3)

        fy = Ty_des / (2 * abs(r[0]) + 1e-3)

        # 摩擦锥约束
        max_f_horiz = abs(fz) * 0.6
        f_horiz = np.sqrt(fx**2 + fy**2)
        if f_horiz > max_f_horiz and max_f_horiz > 1e-6:
            scale = max_f_horiz / f_horiz
            fx *= scale
            fy *= scale

        F_des = np.array([fx, fy, fz])
        tau[6:] += J_lin.T @ F_des

    # Null-space 关节 PD（轻量级）
    for jname in LEFT_LEG_JOINTS + RIGHT_LEG_JOINTS:
        dof = joint_dof_map.get(jname)
        if dof is None or dof >= nv:
            continue
        q_cur = data.qpos[dof] if dof < len(data.qpos) else 0
        qd_cur = data.qvel[dof] if dof < len(data.qvel) else 0
        q_des = pose.get(jname, 0.0)
        kp = 100.0  # 轻量 PD
        kd = 5.0
        tau[dof] += kp*(q_des - q_cur) - kd*qd_cur

    tau[:6] = 0
    tau = np.clip(tau, -396, 396)

    for aname in P.ACTUATOR_NAMES:
        jname = 'J_' + aname[2:]
        jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, jname)
        if jid >= 0:
            dof = model.jnt_dofadr[jid]
            aid = act_ids.get(aname)
            if aid is not None and dof < nv:
                data.ctrl[aid] = float(tau[dof])


# ── 测试3: Wrench + 强关节 PD ──
def ctrl_wrench_strong_pd(data, step):
    """Wrench 力控制 + 强关节 PD 作为 null-space 补充"""
    nv = model.nv
    tau = np.zeros(nv)

    # 高度 PD
    z_err = CORRECT_HEIGHT - data.qpos[2]
    z_vel = data.qvel[2]
    gravity_comp = P.TOTAL_MASS * 9.81
    Fz_des = gravity_comp + 2000*z_err - 200*z_vel
    Fz_des = max(0, Fz_des)

    # 姿态误差
    quat_cur = data.qpos[3:7]
    w, x, y, z = quat_cur[0], quat_cur[1], quat_cur[2], quat_cur[3]
    roll = np.arctan2(2*(w*x + y*z), 1 - 2*(x*x + y*y))
    pitch = np.arcsin(np.clip(2*(w*y - z*x), -1, 1))
    omega = data.qvel[3:6]

    Tx_des = 1000*(-roll) - 50*omega[0]
    Ty_des = 1000*(-pitch) - 50*omega[1]

    base_pos = data.qpos[0:3]

    for leg_side, foot_body in [('left', 'left'), ('right', 'right')]:
        J = get_foot_jacobian(data, foot_body)
        J_lin = J[:3, 6:]
        foot_pos = data.xpos[foot_body_id[foot_body]].copy()
        r = foot_pos - base_pos

        fz = Fz_des / 2.0
        fx = (-Tx_des if leg_side == 'left' else Tx_des) / (2 * abs(r[1]) + 1e-3)
        fy = Ty_des / (2 * abs(r[0]) + 1e-3)

        max_f_horiz = abs(fz) * 0.6
        f_horiz = np.sqrt(fx**2 + fy**2)
        if f_horiz > max_f_horiz and max_f_horiz > 1e-6:
            scale = max_f_horiz / f_horiz
            fx *= scale
            fy *= scale

        F_des = np.array([fx, fy, fz])
        tau[6:] += J_lin.T @ F_des

    # 强关节 PD（关节级跟踪）
    for aname in P.ACTUATOR_NAMES:
        jname = 'J_' + aname[2:]
        jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, jname)
        if jid >= 0:
            dof = model.jnt_dofadr[jid]
            q_cur = data.qpos[model.jnt_qposadr[jid]]
            qd_cur = data.qvel[dof]
            q_des = pose.get(jname, 0.0)
            if 'knee' in jname:
                kp, kd = 600, 30
            elif 'hip' in jname:
                kp, kd = 400, 20
            else:
                kp, kd = 200, 10
            tau[dof] += kp*(q_des - q_cur) - kd*qd_cur

    tau[:6] = 0
    tau = np.clip(tau, -396, 396)

    for aname in P.ACTUATOR_NAMES:
        jname = 'J_' + aname[2:]
        jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, jname)
        if jid >= 0:
            dof = model.jnt_dofadr[jid]
            aid = act_ids.get(aname)
            if aid is not None and dof < nv:
                data.ctrl[aid] = float(tau[dof])


# ── 测试4: PD + 重力补偿前馈 ──
gcomp = None


def _init_gcomp():
    global gcomp
    reset_data()
    gcomp = data.qfrc_bias.copy()


_init_gcomp()


def ctrl_pd_gravity_comp(data, step):
    for aname in P.ACTUATOR_NAMES:
        jname = 'J_' + aname[2:]
        jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, jname)
        if jid >= 0:
            q_cur = data.qpos[model.jnt_qposadr[jid]]
            qd_cur = data.qvel[model.jnt_dofadr[jid]]
            dof = model.jnt_dofadr[jid]
            q_des = pose.get(jname, 0.0)
            aid = act_ids.get(aname)
            if aid is not None:
                ff = gcomp[dof] if dof < model.nv else 0
                kp, kd = 800, 20
                data.ctrl[aid] = np.clip(kp*(q_des - q_cur) - kd*qd_cur + ff, -396, 396)


# ── 测试5: 位置伺服 ──
def ctrl_position_servo(data, step):
    for aname in P.ACTUATOR_NAMES:
        jname = 'J_' + aname[2:]
        jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, jname)
        if jid >= 0:
            q_cur = data.qpos[model.jnt_qposadr[jid]]
            qd_cur = data.qvel[model.jnt_dofadr[jid]]
            q_des = pose.get(jname, 0.0)
            aid = act_ids.get(aname)
            if aid is not None:
                data.ctrl[aid] = np.clip(5000*(q_des - q_cur) - 100*qd_cur, -396, 396)


print('=== Testing different control strategies (2000 steps each) ===')
print(f'Pose: knee={pose["J_knee_l_pitch"]}, hip_pitch={pose["J_hip_l_pitch"]}, '
      f'ankle={pose["J_ankle_l_pitch"]}, init_height={CORRECT_HEIGHT}')
print()

run_test('1. High KP PD', ctrl_high_kp)
run_test('2. Wrench-based (force mapping)', ctrl_wrench_based)
run_test('3. Wrench + Strong PD', ctrl_wrench_strong_pd)
run_test('4. PD + gravity comp', ctrl_pd_gravity_comp)
run_test('5. Position servo (kp=5000)', ctrl_position_servo)
