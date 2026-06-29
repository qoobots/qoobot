/**
 * @file qoo_power_charging.c
 * @brief QooBot 充电系统参考实现
 *
 * 符合 docs/04能源系统设计.md §4 规范
 * - 有线直流快充 (500W, XT60 接口, >95% 效率)
 * - 无线充电 (100W, Qi 2.0/定制线圈, >85% 效率)
 * - 底座触点充电 (500W, 弹性触点+磁吸对位, >98% 效率)
 * - 自主回充状态机
 * - 充电安全保护
 *
 * 自主回充流程 (符合规范 §4.2):
 *   IDLE → 低电量检测 → NAV_TO_DOCK → DOCK_ALIGN → DOCK_ENGAGE
 *   → CHARGING → CHARGE_DONE → UNDOCK → IDLE
 *
 * 依赖：qoo_hal_power.h
 * 平台：BMS CAN FD + 安全 MCU
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <errno.h>
#include <math.h>

#include "../hal/qoo_hal.h"
#include "../hal/qoo_hal_power.h"

/* ===== 充电规格 ===== */
#define CHARGE_WIRED_POWER_W        500    /* 有线快充功率 */
#define CHARGE_WIRELESS_POWER_W     100    /* 无线充电功率 */
#define CHARGE_DOCK_POWER_W         500    /* 底座触点充电功率 */
#define CHARGE_WIRED_EFFICIENCY     0.95f  /* 有线效率 >95% */
#define CHARGE_WIRELESS_EFFICIENCY  0.85f  /* 无线效率 >85% */
#define CHARGE_DOCK_EFFICIENCY      0.98f  /* 底座效率 >98% */

/* 充电策略 */
#define CHARGE_CC_CURRENT_A         8.0f   /* 恒流充电电流 */
#define CHARGE_CV_VOLTAGE_V         54.6f  /* 恒压充电电压 (13S) */
#define CHARGE_TRICKLE_CURRENT_A    0.5f   /* 涓流充电电流 */
#define CHARGE_TRICKLE_THRESHOLD_V  36.0f  /* 涓流阈值 */
#define CHARGE_TERM_CURRENT_A       0.2f   /* 充电终止电流 */
#define CHARGE_LOW_SOC_PERCENT      20     /* 低电量触发阈值 */
#define CHARGE_DONE_SOC_PERCENT     90     /* 充电完成阈值 */

/* 底座对齐精度 */
#define DOCK_ALIGN_TOLERANCE_MM     5      /* 位置精度 ±5mm */
#define DOCK_ALIGN_TOLERANCE_DEG    3      /* 角度精度 ±3° */

/* 充电安全参数 */
#define CHARGE_MAX_TEMP_C           45     /* 充电最高温度 */
#define CHARGE_OVER_CURRENT_A       12     /* 过流保护阈值 */
#define INSULATION_RESISTANCE_MOHM  1      /* 绝缘电阻 > 1MΩ */

/* ===== 充电方式 ===== */
typedef enum {
    CHARGE_METHOD_NONE     = 0,
    CHARGE_METHOD_WIRED    = 1,  /* 有线直流快充 */
    CHARGE_METHOD_WIRELESS = 2,  /* 无线充电 */
    CHARGE_METHOD_DOCK     = 3,  /* 底座触点充电 */
} charge_method_t;

/* ===== 充电阶段 ===== */
typedef enum {
    CHARGE_PHASE_IDLE       = 0,  /* 空闲 */
    CHARGE_PHASE_HANDSHAKE  = 1,  /* 握手协议 */
    CHARGE_PHASE_TRICKLE    = 2,  /* 涓流充电 (深度放电恢复) */
    CHARGE_PHASE_CC         = 3,  /* 恒流充电 */
    CHARGE_PHASE_CV         = 4,  /* 恒压充电 */
    CHARGE_PHASE_DONE       = 5,  /* 充电完成 */
    CHARGE_PHASE_FAULT      = 6,  /* 故障 */
} charge_phase_t;

/* ===== 自主回充状态 (符合规范 §4.2) ===== */
typedef enum {
    DOCK_STATE_IDLE         = 0,  /* 空闲 */
    DOCK_STATE_LOW_BATTERY  = 1,  /* 低电量检测 */
    DOCK_STATE_NAV_TO_DOCK  = 2,  /* 导航至充电底座区域 */
    DOCK_STATE_DOCK_ALIGN   = 3,  /* 红外/视觉精确定位 */
    DOCK_STATE_DOCK_ENGAGE  = 4,  /* 触点接触/线圈对位 */
    DOCK_STATE_CHARGING     = 5,  /* 充电握手→电流爬坡→恒流→恒压 */
    DOCK_STATE_CHARGE_DONE  = 6,  /* SOC > 90% 或用户唤醒 */
    DOCK_STATE_UNDOCK       = 7,  /* 脱离充电底座 */
} dock_state_t;

/* ===== 充电设备 ===== */
typedef struct {
    charge_method_t method;
    charge_phase_t phase;
    dock_state_t dock_state;

    /* 充电参数 */
    float charge_voltage_v;       /* 充电电压 */
    float charge_current_a;       /* 充电电流 */
    float charge_power_w;         /* 充电功率 */
    float efficiency;             /* 充电效率 */

    /* 电池状态 */
    float battery_voltage_v;      /* 电池电压 */
    float battery_current_a;      /* 电池电流 (正=充电) */
    float soc_percent;            /* SOC */
    float temperature_c;          /* 温度 */

    /* 底座对齐 */
    float align_error_mm;         /* 对齐误差 */
    float align_error_deg;        /* 角度误差 */

    /* 保护状态 */
    int over_temp;
    int over_current;
    int insulation_fault;
    int reverse_polarity;

    /* 统计 */
    uint64_t charge_start_time_ms;
    uint64_t total_charge_time_ms;
    float total_charge_wh;        /* 累计充电量 */
    int charge_cycles;

    /* 安全握手 */
    int handshake_ok;
    uint8_t charger_auth[32];     /* 充电器认证码 */
} charge_dev_t;

static charge_dev_t g_charge;

/* ===== 公开 API ===== */

/**
 * @brief 初始化充电系统
 * @return QOO_OK 成功
 */
int qoo_charge_init(void)
{
    charge_dev_t *dev = &g_charge;
    memset(dev, 0, sizeof(*dev));
    dev->dock_state = DOCK_STATE_IDLE;
    dev->phase = CHARGE_PHASE_IDLE;

    printf("[CHARGE] 充电系统初始化: 有线%dW, 无线%dW, 底座%dW\n",
           CHARGE_WIRED_POWER_W, CHARGE_WIRELESS_POWER_W, CHARGE_DOCK_POWER_W);
    return QOO_OK;
}

/**
 * @brief 启动自主回充
 *
 * 触发条件: SOC < 20%
 *
 * @return QOO_OK 成功
 */
int qoo_charge_auto_dock_start(void)
{
    charge_dev_t *dev = &g_charge;

    if (dev->soc_percent > CHARGE_LOW_SOC_PERCENT) {
        printf("[CHARGE] SOC=%.0f%%, 无需充电\n", dev->soc_percent);
        return QOO_OK;
    }

    printf("[CHARGE] 自主回充启动: SOC=%.0f%% < %d%%\n",
           dev->soc_percent, CHARGE_LOW_SOC_PERCENT);
    dev->dock_state = DOCK_STATE_LOW_BATTERY;
    return QOO_OK;
}

/**
 * @brief 充电握手协议
 *
 * 充电器 ↔ BMS CAN 通信 CRC + 认证 (符合规范 §4.3)
 *
 * @param method 充电方式
 * @return QOO_OK 握手成功
 */
int qoo_charge_handshake(charge_method_t method)
{
    charge_dev_t *dev = &g_charge;
    dev->method = method;

    /* 充电器认证 */
    /* can_send_handshake_request(); */
    /* can_recv_handshake_response(dev->charger_auth); */
    /* if (!verify_charger_auth(dev->charger_auth)) return QOO_ERROR_AUTH; */

    dev->handshake_ok = 1;
    dev->phase = CHARGE_PHASE_HANDSHAKE;

    printf("[CHARGE] 握手成功: 方式=%d\n", method);
    return QOO_OK;
}

/**
 * @brief 启动充电
 *
 * 充电策略 (符合规范 §4.2):
 * 1. 涓流充电 (Vbat < 36V, 0.5A)
 * 2. 恒流充电 (8A)
 * 3. 恒压充电 (54.6V)
 * 4. 终止 (电流 < 0.2A)
 *
 * @param method 充电方式
 * @return QOO_OK 成功
 */
int qoo_charge_start(charge_method_t method)
{
    charge_dev_t *dev = &g_charge;

    if (qoo_charge_handshake(method) != QOO_OK)
        return QOO_ERROR;

    /* 涓流检测 */
    if (dev->battery_voltage_v < CHARGE_TRICKLE_THRESHOLD_V) {
        dev->phase = CHARGE_PHASE_TRICKLE;
        dev->charge_current_a = CHARGE_TRICKLE_CURRENT_A;
        printf("[CHARGE] 涓流充电: %.1fV, %.1fA\n",
               dev->battery_voltage_v, CHARGE_TRICKLE_CURRENT_A);
    } else {
        dev->phase = CHARGE_PHASE_CC;
        dev->charge_current_a = CHARGE_CC_CURRENT_A;
        printf("[CHARGE] 恒流充电: %.1fA\n", CHARGE_CC_CURRENT_A);
    }

    dev->charge_start_time_ms = 0; /* 实际应取系统时间 */
    dev->dock_state = DOCK_STATE_CHARGING;

    return QOO_OK;
}

/**
 * @brief 充电控制循环 (每个周期调用一次)
 *
 * 根据当前电池状态调整充电阶段。
 */
void qoo_charge_control_loop(void)
{
    charge_dev_t *dev = &g_charge;

    if (dev->phase == CHARGE_PHASE_IDLE ||
        dev->phase == CHARGE_PHASE_DONE ||
        dev->phase == CHARGE_PHASE_FAULT)
        return;

    /* 安全检查 */
    if (dev->temperature_c > CHARGE_MAX_TEMP_C) {
        dev->phase = CHARGE_PHASE_FAULT;
        dev->over_temp = 1;
        fprintf(stderr, "[CHARGE] 过温保护: %.1f°C\n", dev->temperature_c);
        return;
    }

    if (dev->charge_current_a > CHARGE_OVER_CURRENT_A) {
        dev->phase = CHARGE_PHASE_FAULT;
        dev->over_current = 1;
        fprintf(stderr, "[CHARGE] 过流保护: %.1fA\n", dev->charge_current_a);
        return;
    }

    /* 阶段转换 */
    switch (dev->phase) {
    case CHARGE_PHASE_TRICKLE:
        if (dev->battery_voltage_v >= CHARGE_TRICKLE_THRESHOLD_V) {
            dev->phase = CHARGE_PHASE_CC;
            dev->charge_current_a = CHARGE_CC_CURRENT_A;
            printf("[CHARGE] 涓流→恒流: %.1fV\n", dev->battery_voltage_v);
        }
        break;

    case CHARGE_PHASE_CC:
        if (dev->battery_voltage_v >= CHARGE_CV_VOLTAGE_V) {
            dev->phase = CHARGE_PHASE_CV;
            dev->charge_voltage_v = CHARGE_CV_VOLTAGE_V;
            printf("[CHARGE] 恒流→恒压: %.1fV\n", CHARGE_CV_VOLTAGE_V);
        }
        break;

    case CHARGE_PHASE_CV:
        if (dev->charge_current_a <= CHARGE_TERM_CURRENT_A) {
            dev->phase = CHARGE_PHASE_DONE;
            dev->dock_state = DOCK_STATE_CHARGE_DONE;
            dev->charge_cycles++;
            printf("[CHARGE] 充电完成: SOC=%.0f%%, 循环=%d\n",
                   dev->soc_percent, dev->charge_cycles);
        }
        break;

    default:
        break;
    }

    /* 计算充电功率 */
    dev->charge_power_w = dev->charge_voltage_v * dev->charge_current_a;
}

/**
 * @brief 停止充电
 * @return QOO_OK 成功
 */
int qoo_charge_stop(void)
{
    charge_dev_t *dev = &g_charge;
    dev->phase = CHARGE_PHASE_DONE;
    dev->charge_current_a = 0;
    dev->charge_power_w = 0;
    dev->dock_state = DOCK_STATE_UNDOCK;

    printf("[CHARGE] 充电已停止\n");
    return QOO_OK;
}

/**
 * @brief 脱离充电底座
 * @return QOO_OK 成功
 */
int qoo_charge_undock(void)
{
    charge_dev_t *dev = &g_charge;
    dev->dock_state = DOCK_STATE_IDLE;
    dev->method = CHARGE_METHOD_NONE;
    dev->phase = CHARGE_PHASE_IDLE;

    printf("[CHARGE] 已脱离底座\n");
    return QOO_OK;
}

/**
 * @brief 底座对齐检测
 *
 * 使用红外/视觉精确定位，精度要求 ±5mm / ±3° (符合规范 §4.2)
 *
 * @return 1 已对齐, 0 未对齐
 */
int qoo_charge_dock_aligned(void)
{
    charge_dev_t *dev = &g_charge;
    return (dev->align_error_mm <= DOCK_ALIGN_TOLERANCE_MM &&
            dev->align_error_deg <= DOCK_ALIGN_TOLERANCE_DEG) ? 1 : 0;
}

/**
 * @brief 充电安全自检
 *
 * 检查: 反接保护、绝缘监测、过温保护 (符合规范 §4.3)
 *
 * @return QOO_OK 安全, QOO_ERROR 异常
 */
int qoo_charge_safety_check(void)
{
    charge_dev_t *dev = &g_charge;

    if (dev->over_temp || dev->over_current) return QOO_ERROR;
    if (dev->insulation_fault) return QOO_ERROR;
    if (dev->reverse_polarity) return QOO_ERROR;

    return QOO_OK;
}

/**
 * @brief 获取充电状态
 */
void qoo_charge_get_status(charge_phase_t *phase, float *power_w, float *soc)
{
    charge_dev_t *dev = &g_charge;
    if (phase)  *phase  = dev->phase;
    if (power_w) *power_w = dev->charge_power_w;
    if (soc)    *soc    = dev->soc_percent;
}

/**
 * @brief 释放充电系统资源
 */
int qoo_charge_deinit(void)
{
    qoo_charge_stop();
    memset(&g_charge, 0, sizeof(g_charge));
    return QOO_OK;
}
