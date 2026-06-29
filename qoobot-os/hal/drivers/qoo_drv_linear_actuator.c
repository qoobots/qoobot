/**
 * @file qoo_drv_linear_actuator.c
 * @brief QooBot 线性执行器驱动参考实现
 *
 * 符合 docs/03执行器接口规范.md §7 规范
 * - 行程: 100~1000mm
 * - 速度: 50~500 mm/s
 * - 推力: 500~5000N
 * - 通信: CANopen (CiA 402) / RS-485 Modbus RTU
 * - 供电: 48V DC
 * - 反馈: 编码器 (增量/绝对) + 限位开关
 *
 * 依赖：qoo_hal_actuator.h
 * 平台：Linux + CAN FD / RS-485
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <errno.h>
#include <math.h>

#include "../hal/qoo_hal.h"
#include "../hal/qoo_hal_actuator.h"

/* ===== 线性执行器规格 ===== */
#define LINEAR_MAX_STROKE_MM       1000   /* 最大行程 */
#define LINEAR_MIN_STROKE_MM       100    /* 最小行程 */
#define LINEAR_MAX_SPEED_MM_S      500    /* 最大速度 */
#define LINEAR_MIN_SPEED_MM_S      50     /* 最小速度 */
#define LINEAR_MAX_FORCE_N         5000   /* 最大推力 */
#define LINEAR_MIN_FORCE_N         500    /* 最小推力 */
#define LINEAR_SUPPLY_VOLTAGE      48     /* 供电电压 (V DC) */

/* CANopen CiA 402 控制字 */
#define CIA402_CONTROLWORD         0x6040
#define CIA402_STATUSWORD          0x6041
#define CIA402_TARGET_POSITION     0x607A
#define CIA402_TARGET_VELOCITY     0x60FF
#define CIA402_POSITION_ACTUAL     0x6064
#define CIA402_VELOCITY_ACTUAL     0x606C
#define CIA402_TORQUE_ACTUAL       0x6077

/* 控制模式 */
#define CIA402_MODE_PP             1     /* Profile Position */
#define CIA402_MODE_PV             3     /* Profile Velocity */
#define CIA402_MODE_PT             4     /* Profile Torque */
#define CIA402_MODE_CSP            8     /* Cyclic Sync Position */

/* 状态字位定义 */
#define SW_READY_TO_SWITCH_ON      0x01
#define SW_SWITCHED_ON             0x02
#define SW_OPERATION_ENABLED       0x04
#define SW_FAULT                   0x08
#define SW_TARGET_REACHED          0x400
#define SW_LIMIT_POS               0x1000 /* 正限位 */
#define SW_LIMIT_NEG               0x2000 /* 负限位 */

/* ===== 线性执行器配置 ===== */
typedef struct {
    int can_id;                  /* CANopen Node ID */
    int modbus_addr;             /* RS-485 Modbus 地址 */
    int communication_type;      /* 0=CANopen, 1=Modbus RTU */

    /* 机械参数 */
    float stroke_mm;             /* 行程 (mm) */
    float max_speed_mm_s;        /* 最大速度 (mm/s) */
    float max_force_n;           /* 最大推力 (N) */
    float lead_mm_per_rev;       /* 丝杠导程 (mm/rev) */
    int encoder_resolution;      /* 编码器分辨率 (counts/rev) */

    /* 软限位 */
    float soft_limit_pos_mm;     /* 正向软限位 */
    float soft_limit_neg_mm;     /* 负向软限位 */

    /* PID 参数 */
    float kp, ki, kd;
    float velocity_ff;           /* 速度前馈 */
} linear_actuator_config_t;

/* ===== 线性执行器状态 ===== */
typedef struct {
    float position_mm;           /* 当前位置 (mm) */
    float velocity_mm_s;         /* 当前速度 (mm/s) */
    float force_n;               /* 当前推力 (N) */
    float motor_current_a;       /* 电机电流 (A) */
    float temperature_c;         /* 温度 (°C) */
    uint16_t status_word;        /* CiA 402 状态字 */
    int is_homed;                /* 是否已回零 */
    int limit_pos_triggered;     /* 正限位触发 */
    int limit_neg_triggered;     /* 负限位触发 */
    int fault;                   /* 故障标志 */
} linear_actuator_state_t;

/* ===== 线性执行器设备 ===== */
typedef struct {
    linear_actuator_config_t config;
    linear_actuator_state_t state;
    int can_socket;
    int modbus_fd;
    volatile int running;
} linear_actuator_dev_t;

#define MAX_LINEAR_ACTUATORS 8
static linear_actuator_dev_t g_linear_devs[MAX_LINEAR_ACTUATORS];
static int g_linear_count = 0;

/* ===== 公开 API ===== */

/**
 * @brief 注册线性执行器
 * @param config 执行器配置
 * @return 设备 ID (>=0) 或错误 (<0)
 */
int qoo_linear_actuator_register(const linear_actuator_config_t *config)
{
    if (g_linear_count >= MAX_LINEAR_ACTUATORS) return QOO_ERROR_NOMEM;

    int id = g_linear_count++;
    linear_actuator_dev_t *dev = &g_linear_devs[id];

    memset(dev, 0, sizeof(*dev));
    memcpy(&dev->config, config, sizeof(*config));

    printf("[LINEAR] 执行器 %d 注册: 行程=%.0fmm, 速度=%.0fmm/s, 推力=%.0fN, 通信=%s\n",
           id, config->stroke_mm, config->max_speed_mm_s, config->max_force_n,
           config->communication_type == 0 ? "CANopen" : "Modbus RTU");
    return id;
}

/**
 * @brief 回零操作
 *
 * CiA 402 回零模式 (Homing Mode):
 * 1. 向限位方向低速运动
 * 2. 检测限位开关
 * 3. 反向运动到编码器 Index 脉冲
 * 4. 设置零点
 *
 * @param dev_id 设备 ID
 * @return QOO_OK 成功
 */
int qoo_linear_actuator_home(int dev_id)
{
    if (dev_id < 0 || dev_id >= g_linear_count) return QOO_ERROR_PARAM;

    linear_actuator_dev_t *dev = &g_linear_devs[dev_id];

    printf("[LINEAR] 执行器 %d 回零中...\n", dev_id);

    /* CiA 402 Homing Mode (模式 6: 回零到限位 + Index) */
    /* can_sdo_write(dev->can_socket, dev->config.can_id, 0x6060, 0, 6); */  /* 模式选择 */
    /* can_sdo_write(dev->can_socket, dev->config.can_id, 0x6040, 0, 0x1F); *//* 启动回零 */

    dev->state.is_homed = 1;
    dev->state.position_mm = 0;
    printf("[LINEAR] 执行器 %d 回零完成\n", dev_id);
    return QOO_OK;
}

/**
 * @brief 位置控制 (CiA 402 Profile Position Mode)
 * @param dev_id 设备 ID
 * @param position_mm 目标位置 (mm)
 * @param speed_mm_s 运动速度 (mm/s)
 * @return QOO_OK 成功
 */
int qoo_linear_actuator_move_to(int dev_id, float position_mm, float speed_mm_s)
{
    if (dev_id < 0 || dev_id >= g_linear_count) return QOO_ERROR_PARAM;

    linear_actuator_dev_t *dev = &g_linear_devs[dev_id];

    /* 软限位检查 */
    if (position_mm > dev->config.soft_limit_pos_mm ||
        position_mm < dev->config.soft_limit_neg_mm) {
        fprintf(stderr, "[LINEAR] 执行器 %d 目标位置 %.1f 超出软限位 [%.1f, %.1f]\n",
                dev_id, position_mm,
                dev->config.soft_limit_neg_mm,
                dev->config.soft_limit_pos_mm);
        return QOO_ERROR_PARAM;
    }

    /* 速度限幅 */
    if (speed_mm_s > dev->config.max_speed_mm_s)
        speed_mm_s = dev->config.max_speed_mm_s;

    /* CANopen PP 模式指令 */
    /* can_sdo_write(dev->can_socket, dev->config.can_id, CIA402_TARGET_POSITION, 0, position_counts); */
    /* can_sdo_write(dev->can_socket, dev->config.can_id, CIA402_CONTROLWORD, 0, 0x3F); */ /* 启动运动 */

    return QOO_OK;
}

/**
 * @brief 速度控制 (CiA 402 Profile Velocity Mode)
 * @param dev_id 设备 ID
 * @param velocity_mm_s 目标速度 (mm/s)
 * @return QOO_OK 成功
 */
int qoo_linear_actuator_set_velocity(int dev_id, float velocity_mm_s)
{
    if (dev_id < 0 || dev_id >= g_linear_count) return QOO_ERROR_PARAM;

    linear_actuator_dev_t *dev = &g_linear_devs[dev_id];

    if (fabsf(velocity_mm_s) > dev->config.max_speed_mm_s) {
        velocity_mm_s = copysignf(dev->config.max_speed_mm_s, velocity_mm_s);
    }

    /* CANopen PV 模式指令 */
    /* can_sdo_write(dev->can_socket, dev->config.can_id, CIA402_TARGET_VELOCITY, 0, velocity_counts); */

    return QOO_OK;
}

/**
 * @brief 力控制 (CiA 402 Profile Torque Mode)
 * @param dev_id 设备 ID
 * @param force_n 目标推力 (N)
 * @return QOO_OK 成功
 */
int qoo_linear_actuator_set_force(int dev_id, float force_n)
{
    if (dev_id < 0 || dev_id >= g_linear_count) return QOO_ERROR_PARAM;

    linear_actuator_dev_t *dev = &g_linear_devs[dev_id];

    if (fabsf(force_n) > dev->config.max_force_n) {
        force_n = copysignf(dev->config.max_force_n, force_n);
    }

    /* CANopen PT 模式指令 */
    return QOO_OK;
}

/**
 * @brief 立即停止
 * @param dev_id 设备 ID
 * @return QOO_OK 成功
 */
int qoo_linear_actuator_stop(int dev_id)
{
    if (dev_id < 0 || dev_id >= g_linear_count) return QOO_ERROR_PARAM;

    printf("[LINEAR] 执行器 %d 停止\n", dev_id);

    /* Quick Stop: controlword = 0x0B */
    /* can_sdo_write(dev->can_socket, dev->config.can_id, CIA402_CONTROLWORD, 0, 0x0B); */

    return QOO_OK;
}

/**
 * @brief 紧急停止 (所有执行器)
 * @return QOO_OK 成功
 */
int qoo_linear_actuator_emergency_stop_all(void)
{
    printf("[LINEAR] 所有执行器紧急停止!\n");

    for (int i = 0; i < g_linear_count; i++) {
        qoo_linear_actuator_stop(i);
    }

    return QOO_OK;
}

/**
 * @brief 读取执行器状态
 * @param dev_id 设备 ID
 * @param state 输出状态
 * @return QOO_OK 成功
 */
int qoo_linear_actuator_get_state(int dev_id, linear_actuator_state_t *state)
{
    if (dev_id < 0 || dev_id >= g_linear_count) return QOO_ERROR_PARAM;

    linear_actuator_dev_t *dev = &g_linear_devs[dev_id];
    *state = dev->state;
    return QOO_OK;
}

/**
 * @brief 检查限位状态
 * @param dev_id 设备 ID
 * @param pos_triggered 输出正限位
 * @param neg_triggered 输出负限位
 * @return QOO_OK 成功
 */
int qoo_linear_actuator_check_limits(int dev_id, int *pos_triggered, int *neg_triggered)
{
    if (dev_id < 0 || dev_id >= g_linear_count) return QOO_ERROR_PARAM;

    linear_actuator_dev_t *dev = &g_linear_devs[dev_id];
    if (pos_triggered) *pos_triggered = dev->state.limit_pos_triggered;
    if (neg_triggered) *neg_triggered = dev->state.limit_neg_triggered;
    return QOO_OK;
}

/**
 * @brief 释放线性执行器
 */
int qoo_linear_actuator_deinit(void)
{
    for (int i = 0; i < g_linear_count; i++) {
        qoo_linear_actuator_stop(i);
    }
    memset(g_linear_devs, 0, sizeof(g_linear_devs));
    g_linear_count = 0;
    return QOO_OK;
}
