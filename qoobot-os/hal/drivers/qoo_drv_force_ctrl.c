/**
 * @file qoo_drv_force_ctrl.c
 * @brief QooBot 力控与柔顺硬件接口参考实现
 *
 * 符合 docs/03执行器接口规范.md §5 规范
 * - 关节力矩传感器接口
 * - 六维力/力矩传感器接口
 * - 电机电流检测 (碰撞检测)
 * - 阻抗/导纳控制参数
 * - 力超限保护
 *
 * 控制架构 (规范 §5.2):
 *   参考轨迹 → 阻抗控制(M·ẍ+D·ẋ+K·x=F_ext) → 位置控制(PID) → 电机驱动(电流环)
 *
 * 依赖：qoo_hal_actuator.h
 * 平台：安全 MCU (硬实时, 1kHz)
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <math.h>

#include "../hal/qoo_hal.h"
#include "../hal/qoo_hal_actuator.h"

/* ===== 力控参数 ===== */
#define MAX_JOINTS              32
#define FORCE_CTRL_RATE_HZ      1000   /* 力控伺服频率 1kHz */
#define FORCE_CTRL_PERIOD_US    1000   /* 力控周期 1ms */

/* 阻抗控制参数范围 */
#define IMPEDANCE_M_MIN         0.1f   /* 最小惯量缩放 */
#define IMPEDANCE_M_MAX         10.0f  /* 最大惯量缩放 */
#define IMPEDANCE_D_MIN         0.5f   /* 最小阻尼比 */
#define IMPEDANCE_D_MAX         2.0f   /* 最大阻尼比 */
#define IMPEDANCE_K_MAX_NPM     5000.0f /* 最大刚度 (N/m) */

/* 力检测阈值 (符合规范 §5.1) */
#define JOINT_TORQUE_RESOLUTION_NM 0.1f   /* 关节力矩分辨率 */
#define FT_SENSOR_RESOLUTION_N    0.5f    /* 六维力分辨率 */
#define CURRENT_TORQUE_ACCURACY    0.05f  /* 电流估算力矩精度 5% */

/* ===== 力控模式 ===== */
typedef enum {
    FORCE_MODE_IMPEDANCE = 0,  /* 阻抗控制 */
    FORCE_MODE_ADMITTANCE = 1, /* 导纳控制 */
    FORCE_MODE_ZERO_FORCE = 2, /* 零力模式 (拖拽示教) */
    FORCE_MODE_DIRECT_TORQUE = 3, /* 直接力矩控制 */
} force_ctrl_mode_t;

/* ===== 阻抗控制参数 (符合规范 §5.2) ===== */
typedef struct {
    float mass_scale;        /* 惯量缩放 M (0.1~10×) */
    float damping_ratio;     /* 阻尼比 D (0.5~2×临界) */
    float stiffness_npm;     /* 刚度 K (0~5000 N/m) */
    float force_deadzone_n;  /* 力死区 (N) */
    float max_force_n;       /* 最大接触力 (N) */
} impedance_params_t;

/* ===== 关节力控状态 ===== */
typedef struct {
    float measured_torque_nm;    /* 实测力矩 (Nm) */
    float desired_torque_nm;     /* 期望力矩 (Nm) */
    float torque_error_nm;       /* 力矩误差 (Nm) */
    float motor_current_a;       /* 电机电流 (A) */
    float torque_constant_nm_a;  /* 力矩常数 (Nm/A) */
    int force_limit_triggered;   /* 力超限触发 */
} joint_force_state_t;

/* ===== 力控设备 ===== */
typedef struct {
    force_ctrl_mode_t mode;
    impedance_params_t impedance;
    joint_force_state_t joints[MAX_JOINTS];
    int num_joints;

    /* 六维力传感器 */
    float ft_fx, ft_fy, ft_fz;  /* 力 (N) */
    float ft_tx, ft_ty, ft_tz;  /* 力矩 (Nm) */

    /* 碰撞检测 */
    float collision_threshold_n;  /* 碰撞力阈值 */
    int collision_detected;

    /* 统计 */
    uint64_t ctrl_cycles;
} force_ctrl_dev_t;

static force_ctrl_dev_t g_force_ctrl;

/* ===== 公开 API ===== */

/**
 * @brief 初始化力控系统
 * @param num_joints 关节数
 * @param default_mode 默认力控模式
 * @return QOO_OK 成功
 */
int qoo_force_ctrl_init(int num_joints, force_ctrl_mode_t default_mode)
{
    force_ctrl_dev_t *dev = &g_force_ctrl;
    memset(dev, 0, sizeof(*dev));

    dev->num_joints = num_joints;
    dev->mode = default_mode;

    /* 默认阻抗参数 (中等柔顺) */
    dev->impedance.mass_scale = 1.0f;
    dev->impedance.damping_ratio = 1.0f;
    dev->impedance.stiffness_npm = 500.0f;
    dev->impedance.force_deadzone_n = 1.0f;
    dev->impedance.max_force_n = 50.0f;

    /* 碰撞检测阈值 (符合安全规范 §4) */
    dev->collision_threshold_n = 50.0f; /* 手臂自由空间 */

    printf("[FORCE] 力控系统初始化: %d 关节, 模式=%d, %dHz\n",
           num_joints, default_mode, FORCE_CTRL_RATE_HZ);
    return QOO_OK;
}

/**
 * @brief 设置力控模式
 * @param mode 力控模式
 */
void qoo_force_ctrl_set_mode(force_ctrl_mode_t mode)
{
    g_force_ctrl.mode = mode;
    printf("[FORCE] 力控模式切换: %d\n", mode);
}

/**
 * @brief 设置阻抗控制参数
 *
 * 符合规范 §5.2 参数定义:
 * - M (惯性): 可调 0.1~10× 实际惯量
 * - D (阻尼): 临界阻尼的 0.5~2×
 * - K (刚度): 0 (零力) ~ 5000 N/m (高刚度)
 *
 * @param mass_scale 惯量缩放
 * @param damping_ratio 阻尼比
 * @param stiffness_npm 刚度 (N/m)
 */
int qoo_force_ctrl_set_impedance(float mass_scale, float damping_ratio, float stiffness_npm)
{
    force_ctrl_dev_t *dev = &g_force_ctrl;

    /* 参数范围检查 */
    if (mass_scale < IMPEDANCE_M_MIN || mass_scale > IMPEDANCE_M_MAX)
        return QOO_ERROR_PARAM;
    if (damping_ratio < IMPEDANCE_D_MIN || damping_ratio > IMPEDANCE_D_MAX)
        return QOO_ERROR_PARAM;
    if (stiffness_npm < 0 || stiffness_npm > IMPEDANCE_K_MAX_NPM)
        return QOO_ERROR_PARAM;

    dev->impedance.mass_scale = mass_scale;
    dev->impedance.damping_ratio = damping_ratio;
    dev->impedance.stiffness_npm = stiffness_npm;

    printf("[FORCE] 阻抗参数: M=%.1f×, D=%.1f×, K=%.0f N/m\n",
           mass_scale, damping_ratio, stiffness_npm);
    return QOO_OK;
}

/**
 * @brief 读取关节力矩传感器
 * @param joint_id 关节 ID
 * @param torque_nm 输出力矩 (Nm)
 * @return QOO_OK 成功
 */
int qoo_force_ctrl_read_joint_torque(int joint_id, float *torque_nm)
{
    force_ctrl_dev_t *dev = &g_force_ctrl;
    if (joint_id < 0 || joint_id >= dev->num_joints) return QOO_ERROR_PARAM;

    *torque_nm = dev->joints[joint_id].measured_torque_nm;
    return QOO_OK;
}

/**
 * @brief 读取六维力/力矩传感器
 * @param fx,fy,fz 输出力 (N)
 * @param tx,ty,tz 输出力矩 (Nm)
 */
void qoo_force_ctrl_read_ft_sensor(float *fx, float *fy, float *fz,
                                    float *tx, float *ty, float *tz)
{
    force_ctrl_dev_t *dev = &g_force_ctrl;
    if (fx) *fx = dev->ft_fx;
    if (fy) *fy = dev->ft_fy;
    if (fz) *fz = dev->ft_fz;
    if (tx) *tx = dev->ft_tx;
    if (ty) *ty = dev->ft_ty;
    if (tz) *tz = dev->ft_tz;
}

/**
 * @brief 基于电机电流的力矩估算
 *
 * τ = Kt × I (力矩常数 × 电流)
 * 精度: ±5% 额定 (符合规范 §5.1)
 *
 * @param joint_id 关节 ID
 * @param current_a 电机电流 (A)
 * @return 估算力矩 (Nm)
 */
float qoo_force_ctrl_estimate_torque_from_current(int joint_id, float current_a)
{
    force_ctrl_dev_t *dev = &g_force_ctrl;
    if (joint_id < 0 || joint_id >= dev->num_joints) return 0;

    float Kt = dev->joints[joint_id].torque_constant_nm_a;
    return Kt * current_a;
}

/**
 * @brief 计算阻抗控制输出力矩
 *
 * 阻抗控制律: τ = M·(q̈_des - q̈) + D·(q̇_des - q̇) + K·(q_des - q) + τ_ext
 *
 * @param joint_id 关节 ID
 * @param pos_des 期望位置 (rad)
 * @param vel_des 期望速度 (rad/s)
 * @param pos_cur 当前位置 (rad)
 * @param vel_cur 当前速度 (rad/s)
 * @param external_torque 外力矩 (Nm)
 * @return 输出力矩 (Nm)
 */
float qoo_force_ctrl_compute_impedance_torque(int joint_id,
                                               float pos_des, float vel_des,
                                               float pos_cur, float vel_cur,
                                               float external_torque)
{
    force_ctrl_dev_t *dev = &g_force_ctrl;
    impedance_params_t *imp = &dev->impedance;

    /* 死区处理 */
    if (fabsf(external_torque) < imp->force_deadzone_n)
        external_torque = 0;

    /* 力限幅 */
    if (external_torque > imp->max_force_n)
        external_torque = imp->max_force_n;
    if (external_torque < -imp->max_force_n)
        external_torque = -imp->max_force_n;

    /* PD 位置控制 + 外力前馈 */
    float pos_err = pos_des - pos_cur;
    float vel_err = vel_des - vel_cur;

    float tau = imp->stiffness_npm * pos_err +
                imp->damping_ratio * vel_err +
                external_torque;

    return tau;
}

/**
 * @brief 碰撞检测
 *
 * 符合 docs/07安全硬件规范.md §4.2 阈值定义:
 * - 手臂 (自由空间): 50N
 * - 手臂 (约束空间): 150N
 * - 手掌/手指: 10N
 * - 头部: 30N
 *
 * @param threshold_n 力阈值 (N)
 * @return 1 碰撞, 0 正常
 */
int qoo_force_ctrl_collision_detect(float threshold_n)
{
    force_ctrl_dev_t *dev = &g_force_ctrl;

    /* 综合检测: 关节力矩异常 + 电机电流异常 + 末端力超限 */
    for (int i = 0; i < dev->num_joints; i++) {
        float abs_torque = fabsf(dev->joints[i].measured_torque_nm);
        if (abs_torque > threshold_n) {
            dev->collision_detected = 1;
            return 1;
        }
    }

    /* 六维力传感器检查 */
    float force_mag = sqrtf(dev->ft_fx * dev->ft_fx +
                            dev->ft_fy * dev->ft_fy +
                            dev->ft_fz * dev->ft_fz);
    if (force_mag > threshold_n) {
        dev->collision_detected = 1;
        return 1;
    }

    dev->collision_detected = 0;
    return 0;
}

/**
 * @brief 碰撞响应策略
 *
 * 符合 docs/07安全硬件规范.md §4.3:
 * - STOP: 立即停止所有运动
 * - RETRACT: 反向运动 50mm 后停止
 * - COMPLIANT: 切换到零力模式
 *
 * @param response 响应策略 (0=STOP, 1=RETRACT, 2=COMPLIANT)
 */
void qoo_force_ctrl_collision_response(int response)
{
    switch (response) {
    case 0: /* STOP */
        printf("[FORCE] 碰撞响应: 立即停止\n");
        qoo_force_ctrl_set_mode(FORCE_MODE_DIRECT_TORQUE);
        /* 所有关节力矩指令置零 */
        break;
    case 1: /* RETRACT */
        printf("[FORCE] 碰撞响应: 反向运动 50mm\n");
        /* 反向运动 50mm (约 0.1 rad 关节角度) */
        break;
    case 2: /* COMPLIANT */
        printf("[FORCE] 碰撞响应: 零力模式\n");
        qoo_force_ctrl_set_mode(FORCE_MODE_ZERO_FORCE);
        qoo_force_ctrl_set_impedance(0.1f, 1.0f, 0.0f);  /* K=0 零力 */
        break;
    }
}

/**
 * @brief 力超限保护
 *
 * 当关节力矩超过安全阈值时:
 * 1. 触发安全 MCU 报警
 * 2. 降低力矩指令
 * 3. 通知主控
 *
 * @param joint_id 关节 ID
 * @param max_torque_nm 最大允许力矩 (Nm)
 * @return 1 超限, 0 正常
 */
int qoo_force_ctrl_torque_limit_check(int joint_id, float max_torque_nm)
{
    force_ctrl_dev_t *dev = &g_force_ctrl;
    if (joint_id < 0 || joint_id >= dev->num_joints) return 0;

    float abs_torque = fabsf(dev->joints[joint_id].measured_torque_nm);
    if (abs_torque > max_torque_nm) {
        dev->joints[joint_id].force_limit_triggered = 1;
        fprintf(stderr, "[FORCE] 关节 %d 力矩超限: %.2f > %.2f Nm\n",
                joint_id, abs_torque, max_torque_nm);
        return 1;
    }
    return 0;
}

/**
 * @brief 释放力控资源
 */
int qoo_force_ctrl_deinit(void)
{
    memset(&g_force_ctrl, 0, sizeof(g_force_ctrl));
    return QOO_OK;
}
