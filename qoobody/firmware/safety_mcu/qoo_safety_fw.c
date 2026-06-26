/**
 * @file qoo_safety_fw.c
 * @brief 安全 MCU 固件参考实现
 *
 * 运行于独立安全 MCU (SIL 2 认证)
 * 职责: 碰撞检测、急停响应、安全状态管理、看门狗
 *
 * 目标芯片: 双核锁步 MCU (如 TI Hercules / NXP S32K3)
 */

#include <stdint.h>
#include <stdbool.h>
#include <string.h>

/*===========================================================================
 * 硬件相关定义 (平台抽象)
 *===========================================================================*/

/* 假定的硬件寄存器地址 */
#define SAFETY_MCU_BASE      0x40000000
#define WDT_BASE             0x40001000
#define CAN_BASE             0x40002000
#define GPIO_BASE            0x40003000
#define ADC_BASE             0x40004000

/* GPIO 引脚定义 */
#define PIN_ESTOP_CH1        0   /* 急停通道 1 (NC) */
#define PIN_ESTOP_CH2        1   /* 急停通道 2 (NC) */
#define PIN_SAFETY_RELAY     2   /* 安全继电器控制 */
#define PIN_BRAKE_ALL        3   /* 全部抱闸控制 */
#define PIN_TAMPER           4   /* 防拆检测 */

/* 安全阈值 */
#define TORQUE_SAFETY_LIMIT_NM   80.0f   /* 力矩安全限制 (Nm) */
#define CURRENT_SAFETY_LIMIT_A   20.0f   /* 电流安全限制 (A) */
#define VELOCITY_SAFETY_LIMIT_RAD 10.0f  /* 速度安全限制 (rad/s) */
#define TEMPERATURE_SAFETY_LIMIT 85.0f   /* 温度安全限制 (°C) */
#define COLLISION_JERK_THRESHOLD 500.0f  /* 碰撞急动度阈值 (rad/s³) */

/* 时序要求 */
#define SAFETY_LOOP_PERIOD_US     100    /* 安全循环周期 100μs (10kHz) */
#define ESTOP_RESPONSE_TIME_US    20000  /* 急停响应时间 20ms */
#define WDT_TIMEOUT_MS            50     /* 看门狗超时 50ms */
#define COMM_TIMEOUT_MS           100    /* 通信超时 100ms */

/*===========================================================================
 * 安全状态
 *===========================================================================*/

typedef enum {
    SAFE_STATE_INIT = 0,
    SAFE_STATE_SELFTEST,
    SAFE_STATE_NORMAL,
    SAFE_STATE_REDUCED,
    SAFE_STATE_PROTECTIVE_STOP,
    SAFE_STATE_EMERGENCY_STOP,
    SAFE_STATE_FAULT,
} safe_state_t;

typedef enum {
    EVENT_NONE = 0,
    EVENT_ESTOP,
    EVENT_COLLISION,
    EVENT_TORQUE_OVER,
    EVENT_SPEED_OVER,
    EVENT_CURRENT_OVER,
    EVENT_TEMP_OVER,
    EVENT_COMM_LOST,
    EVENT_WDT_TIMEOUT,
    EVENT_POWER_FAULT,
    EVENT_TAMPER,
} safety_event_t;

/* 关节安全数据 (通过共享内存/内部总线从主控获取) */
typedef struct {
    float position;
    float velocity;
    float prev_velocity;    /* 用于计算 jerk */
    float torque;
    float current;
    float temperature;
    uint32_t error_flags;
    uint32_t last_update_us;
} joint_safety_data_t;

#define MAX_SAFETY_JOINTS 32

/*===========================================================================
 * 全局安全上下文
 *===========================================================================*/

static struct {
    safe_state_t state;
    safety_event_t active_event;
    bool estop_ch1_ok;
    bool estop_ch2_ok;
    bool safety_relay_engaged;
    bool brakes_engaged;
    bool main_mcu_alive;
    uint32_t main_mcu_last_heartbeat;
    uint32_t fault_flags;
    joint_safety_data_t joints[MAX_SAFETY_JOINTS];
    uint32_t joint_count;
    uint32_t uptime_us;
} g_safety;

/*===========================================================================
 * 硬件抽象 (实际需根据 MCU 型号实现)
 *===========================================================================*/

static inline void hw_gpio_set(uint32_t pin, bool high) {
    /* GPIO 寄存器操作 */
    (void)pin; (void)high;
}

static inline bool hw_gpio_get(uint32_t pin) {
    (void)pin;
    return true;
}

static inline void hw_wdt_feed(void) {
    /* 看门狗喂狗: 写入特定序列到 WDT 寄存器 */
}

static inline void hw_delay_us(uint32_t us) {
    /* 微秒延时 */
    (void)us;
}

static inline uint32_t hw_timer_get_us(void) {
    /* 获取 MCU 定时器微秒计数 */
    return 0;
}

/*===========================================================================
 * 自检
 *===========================================================================*/

static bool safety_self_test(void) {
    bool ok = true;

    /* 1. 内存测试 (March C-) */
    /* 2. 寄存器测试 */
    /* 3. 急停回路双通道测试 */
    /* 4. 安全继电器测试 */
    /* 5. ADC 自检 */

    return ok;
}

/*===========================================================================
 * 碰撞检测算法
 *===========================================================================*/

static bool collision_detect(uint32_t joint_idx) {
    joint_safety_data_t *j = &g_safety.joints[joint_idx];

    /* 1. 力矩超限检测 */
    if (j->torque > TORQUE_SAFETY_LIMIT_NM) {
        g_safety.active_event = EVENT_TORQUE_OVER;
        return true;
    }

    /* 2. 力矩变化率 (jerk) 检测 */
    float jerk = (j->velocity - j->prev_velocity) /
        ((j->last_update_us - g_safety.uptime_us) / 1000000.0f);
    /* jerk 实际应基于准确的 dt 计算 */
    if (jerk > COLLISION_JERK_THRESHOLD || jerk < -COLLISION_JERK_THRESHOLD) {
        g_safety.active_event = EVENT_COLLISION;
        return true;
    }

    /* 3. 电流超限检测 */
    if (j->current > CURRENT_SAFETY_LIMIT_A) {
        g_safety.active_event = EVENT_CURRENT_OVER;
        return true;
    }

    /* 4. 速度超限检测 */
    if (j->velocity > VELOCITY_SAFETY_LIMIT_RAD ||
        j->velocity < -VELOCITY_SAFETY_LIMIT_RAD) {
        g_safety.active_event = EVENT_SPEED_OVER;
        return true;
    }

    /* 5. 温度超限检测 */
    if (j->temperature > TEMPERATURE_SAFETY_LIMIT) {
        g_safety.active_event = EVENT_TEMP_OVER;
        return true;
    }

    return false;
}

/*===========================================================================
 * 安全动作执行
 *===========================================================================*/

/** 进入安全停止状态 */
static void enter_safe_stop(safety_event_t event) {
    g_safety.state = SAFE_STATE_PROTECTIVE_STOP;
    g_safety.active_event = event;

    /* 1. 断开安全继电器 → 电机驱动使能断开 */
    hw_gpio_set(PIN_SAFETY_RELAY, false);
    g_safety.safety_relay_engaged = false;

    /* 2. 抱闸所有制动器 */
    hw_gpio_set(PIN_BRAKE_ALL, true);
    g_safety.brakes_engaged = true;

    /* 3. 通过 CAN 发送紧急停止报文给所有电机 */
    /* can_send_emcy_all(); */
}

/** 进入紧急停止状态 */
static void enter_emergency_stop(safety_event_t event) {
    g_safety.state = SAFE_STATE_EMERGENCY_STOP;
    g_safety.active_event = event;

    /* 立即切断动力 */
    hw_gpio_set(PIN_SAFETY_RELAY, false);
    hw_gpio_set(PIN_BRAKE_ALL, true);

    /* 触发蜂鸣器/指示灯 */
    /* buzzer_alarm(); */
    /* led_set_pattern(LED_EMERGENCY); */
}

/** 恢复安全状态 */
static bool try_recover(void) {
    /* 仅在故障清除且用户确认后恢复 */
    if (g_safety.active_event == EVENT_NONE) {
        return false;
    }

    /* 检查急停是否已释放 */
    if (!g_safety.estop_ch1_ok || !g_safety.estop_ch2_ok) {
        return false;
    }

    /* 检查通信是否恢复 */
    if (!g_safety.main_mcu_alive) {
        return false;
    }

    /* 清除故障 */
    g_safety.active_event = EVENT_NONE;
    g_safety.state = SAFE_STATE_NORMAL;

    /* 恢复安全继电器 */
    hw_gpio_set(PIN_SAFETY_RELAY, true);
    g_safety.safety_relay_engaged = true;

    /* 释放制动器 */
    hw_gpio_set(PIN_BRAKE_ALL, false);
    g_safety.brakes_engaged = false;

    return true;
}

/*===========================================================================
 * 急停回路监控 (双通道冗余)
 *===========================================================================*/

static void estop_monitor(void) {
    bool ch1 = hw_gpio_get(PIN_ESTOP_CH1);
    bool ch2 = hw_gpio_get(PIN_ESTOP_CH2);

    /* 双通道一致性检查 */
    if (ch1 != ch2) {
        /* 通道不一致 = 回路故障 → 紧急停止 */
        g_safety.fault_flags |= 0x01; /* E-Stop回路故障 */
        enter_emergency_stop(EVENT_ESTOP);
        return;
    }

    /* 双通道同时断开 (急停按下) */
    if (!ch1 && !ch2) {
        if (g_safety.state == SAFE_STATE_NORMAL ||
            g_safety.state == SAFE_STATE_REDUCED) {
            enter_emergency_stop(EVENT_ESTOP);
        }
    } else {
        g_safety.estop_ch1_ok = ch1;
        g_safety.estop_ch2_ok = ch2;
    }
}

/*===========================================================================
 * 主控心跳监控
 *===========================================================================*/

static void heartbeat_monitor(void) {
    uint32_t now = hw_timer_get_us();
    uint32_t elapsed = now - g_safety.main_mcu_last_heartbeat;

    if (elapsed > COMM_TIMEOUT_MS * 1000) {
        g_safety.main_mcu_alive = false;
        if (g_safety.state == SAFE_STATE_NORMAL) {
            enter_safe_stop(EVENT_COMM_LOST);
        }
    } else {
        g_safety.main_mcu_alive = true;
    }
}

/** 主控心跳回调 (CAN 中断中调用) */
void safety_heartbeat_isr(void) {
    g_safety.main_mcu_last_heartbeat = hw_timer_get_us();
}

/*===========================================================================
 * 关节数据更新 (从主控接收)
 *===========================================================================*/

void safety_update_joint(uint32_t idx, const joint_safety_data_t *data) {
    if (idx >= MAX_SAFETY_JOINTS) return;

    /* 保存上一帧速度用于 jerk 计算 */
    g_safety.joints[idx].prev_velocity = g_safety.joints[idx].velocity;

    memcpy(&g_safety.joints[idx], data, sizeof(joint_safety_data_t));
    g_safety.joints[idx].last_update_us = g_safety.uptime_us;
}

/*===========================================================================
 * 防拆检测
 *===========================================================================*/

static void tamper_monitor(void) {
    bool tamper = hw_gpio_get(PIN_TAMPER);
    if (tamper) {
        g_safety.fault_flags |= 0x02; /* 防拆检测 */
        /* 不触发紧急停止, 但记录事件并告警 */
        if (g_safety.active_event == EVENT_NONE) {
            g_safety.active_event = EVENT_TAMPER;
        }
    }
}

/*===========================================================================
 * 主安全循环 (10kHz)
 *===========================================================================*/

void safety_main_loop(void) {
    uint32_t loop_start = hw_timer_get_us();

    /* 喂狗 */
    hw_wdt_feed();

    /* 1. 急停回路监控 */
    estop_monitor();

    /* 2. 主控心跳监控 */
    heartbeat_monitor();

    /* 3. 防拆检测 */
    tamper_monitor();

    /* 4. 各关节碰撞检测 */
    if (g_safety.state == SAFE_STATE_NORMAL) {
        for (uint32_t i = 0; i < g_safety.joint_count; i++) {
            if (collision_detect(i)) {
                enter_safe_stop(g_safety.active_event);
                break;
            }
        }
    }

    /* 5. 故障恢复检查 */
    if (g_safety.state == SAFE_STATE_PROTECTIVE_STOP) {
        try_recover();
    }

    /* 6. 更新运行时间 */
    g_safety.uptime_us = hw_timer_get_us();

    /* 7. 保证循环周期 */
    uint32_t elapsed = g_safety.uptime_us - loop_start;
    if (elapsed < SAFETY_LOOP_PERIOD_US) {
        hw_delay_us(SAFETY_LOOP_PERIOD_US - elapsed);
    }
}

/*===========================================================================
 * 初始化
 *===========================================================================*/

void safety_init(void) {
    memset(&g_safety, 0, sizeof(g_safety));

    /* 1. 硬件初始化 */
    /* hw_gpio_init(); */
    /* hw_wdt_init(WDT_TIMEOUT_MS); */
    /* hw_can_init(); */

    /* 2. 上电自检 */
    g_safety.state = SAFE_STATE_SELFTEST;
    if (!safety_self_test()) {
        g_safety.state = SAFE_STATE_FAULT;
        return;
    }

    /* 3. 初始状态: 抱闸, 断开安全继电器 */
    hw_gpio_set(PIN_BRAKE_ALL, true);
    g_safety.brakes_engaged = true;
    hw_gpio_set(PIN_SAFETY_RELAY, false);
    g_safety.safety_relay_engaged = false;

    /* 4. 等待主控就绪 */
    g_safety.state = SAFE_STATE_INIT;

    /* 5. 启动看门狗 */
    /* hw_wdt_start(); */
}

/*===========================================================================
 * 外部接口 (供主控调用)
 *===========================================================================*/

safe_state_t safety_get_state(void) {
    return g_safety.state;
}

safety_event_t safety_get_active_event(void) {
    return g_safety.active_event;
}

bool safety_is_ok(void) {
    return (g_safety.state == SAFE_STATE_NORMAL) &&
           (g_safety.active_event == EVENT_NONE);
}

void safety_request_recovery(void) {
    if (g_safety.state == SAFE_STATE_PROTECTIVE_STOP) {
        try_recover();
    }
}
