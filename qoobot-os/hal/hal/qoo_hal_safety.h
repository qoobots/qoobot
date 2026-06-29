/**
 * @file qoo_hal_safety.h
 * @brief 安全硬件抽象接口 — 安全控制器 / 碰撞检测 / 急停 / 制动器 / 状态指示
 */

#ifndef QOO_HAL_SAFETY_H
#define QOO_HAL_SAFETY_H

#include "qoo_hal_types.h"

#ifdef __cplusplus
extern "C" {
#endif

/*===========================================================================
 * 安全状态
 *===========================================================================*/

/** 安全模式 */
typedef enum {
    QOO_SAFETY_MODE_NORMAL = 0,       /**< 正常运行 */
    QOO_SAFETY_MODE_REDUCED_SPEED,    /**< 降速模式 */
    QOO_SAFETY_MODE_PROTECTIVE_STOP,  /**< 保护性停止 */
    QOO_SAFETY_MODE_EMERGENCY_STOP,   /**< 紧急停止 */
    QOO_SAFETY_MODE_SAFE_TORQUE_OFF,  /**< 安全力矩关闭 (STO) */
    QOO_SAFETY_MODE_MAINTENANCE,      /**< 维护模式 */
} qoo_safety_mode_t;

/** 安全事件 */
typedef enum {
    QOO_SAFETY_EVENT_NONE = 0,
    QOO_SAFETY_EVENT_ESTOP_PRESSED,     /**< 急停按钮按下 */
    QOO_SAFETY_EVENT_COLLISION_DETECTED, /**< 碰撞检测 */
    QOO_SAFETY_EVENT_TORQUE_OVER_LIMIT,  /**< 力矩超限 */
    QOO_SAFETY_EVENT_SPEED_OVER_LIMIT,   /**< 速度超限 */
    QOO_SAFETY_EVENT_JOINT_LIMIT,        /**< 关节限位触发 */
    QOO_SAFETY_EVENT_COMM_LOST,          /**< 通信丢失 */
    QOO_SAFETY_EVENT_WATCHDOG_TIMEOUT,   /**< 看门狗超时 */
    QOO_SAFETY_EVENT_POWER_FAULT,        /**< 电源故障 */
    QOO_SAFETY_EVENT_THERMAL_OVERHEAT,   /**< 过热 */
    QOO_SAFETY_EVENT_TAMPER_DETECTED,    /**< 防拆检测 */
} qoo_safety_event_t;

/** 安全状态 */
typedef struct {
    qoo_timestamp_us_t timestamp;
    qoo_safety_mode_t mode;
    qoo_safety_event_t active_event;
    uint32_t fault_flags;
    bool estop_active;          /**< 急停是否激活 */
    bool brakes_engaged;        /**< 制动器是否抱闸 */
    bool safety_ok;             /**< 安全回路是否正常 */
} qoo_safety_state_t;

/*===========================================================================
 * 安全控制器接口
 *===========================================================================*/

/**
 * @brief 获取当前安全状态
 */
qoo_error_t qoo_hal_safety_get_state(qoo_safety_state_t *state);

/**
 * @brief 注册安全事件回调
 * @param callback 事件回调 (在安全 MCU 中断上下文中调用)
 */
qoo_error_t qoo_hal_safety_register_callback(
    void (*callback)(qoo_safety_event_t event, void *user_data),
    void *user_data);

/**
 * @brief 请求安全模式切换 (需安全 MCU 确认)
 * @param mode 目标安全模式
 */
qoo_error_t qoo_hal_safety_request_mode(qoo_safety_mode_t mode);

/**
 * @brief 复位安全状态 (清除故障后恢复)
 */
qoo_error_t qoo_hal_safety_reset(void);

/*===========================================================================
 * 碰撞检测
 *===========================================================================*/

/** 碰撞检测配置 */
typedef struct {
    float torque_threshold;         /**< 力矩碰撞阈值 (Nm) */
    float torque_rate_threshold;    /**< 力矩变化率阈值 (Nm/s) */
    float current_threshold;        /**< 电流碰撞阈值 (A) */
    float proximity_threshold;      /**< 电容接近阈值 (pF) */
    bool enable_torque_detect;      /**< 启用力矩检测 */
    bool enable_current_detect;     /**< 启用电流检测 */
    bool enable_proximity_detect;   /**< 启用接近检测 */
} qoo_collision_config_t;

/** 碰撞事件 */
typedef struct {
    qoo_timestamp_us_t timestamp;
    uint32_t joint_id;          /**< 碰撞关节 ID */
    float peak_torque;          /**< 峰值力矩 (Nm) */
    float peak_impact_force;    /**< 峰值冲击力 (N) */
    float duration_ms;          /**< 碰撞持续时间 (ms) */
} qoo_collision_event_t;

/**
 * @brief 配置碰撞检测参数
 */
qoo_error_t qoo_hal_collision_configure(const qoo_collision_config_t *config);

/**
 * @brief 获取最近碰撞事件
 */
qoo_error_t qoo_hal_collision_get_last_event(qoo_collision_event_t *event);

/*===========================================================================
 * 紧急停止
 *===========================================================================*/

/**
 * @brief 触发紧急停止
 * @note 可被任何线程/中断调用, 立即生效
 */
void qoo_hal_estop_trigger(void);

/**
 * @brief 释放紧急停止 (需确认安全条件)
 */
qoo_error_t qoo_hal_estop_release(void);

/**
 * @brief 获取急停按钮状态
 */
bool qoo_hal_estop_is_pressed(void);

/*===========================================================================
 * 制动器
 *===========================================================================*/

/**
 * @brief 抱闸所有制动器
 */
qoo_error_t qoo_hal_brake_engage_all(void);

/**
 * @brief 释放所有制动器
 */
qoo_error_t qoo_hal_brake_release_all(void);

/**
 * @brief 单个关节制动控制
 */
qoo_error_t qoo_hal_brake_set(uint32_t joint_id, bool engage);

/**
 * @brief 制动器磨损状态
 * @param joint_id 关节 ID
 * @param wear_percent [out] 磨损百分比 [0,100]
 */
qoo_error_t qoo_hal_brake_get_wear(uint32_t joint_id, float *wear_percent);

/*===========================================================================
 * 状态指示
 *===========================================================================*/

/** LED 状态模式 */
typedef enum {
    QOO_LED_PATTERN_IDLE,
    QOO_LED_PATTERN_BOOTING,
    QOO_LED_PATTERN_READY,
    QOO_LED_PATTERN_RUNNING,
    QOO_LED_PATTERN_THINKING,
    QOO_LED_PATTERN_WARNING,
    QOO_LED_PATTERN_ERROR,
    QOO_LED_PATTERN_ESTOP,
    QOO_LED_PATTERN_CHARGING,
    QOO_LED_PATTERN_LOW_BATTERY,
} qoo_led_pattern_t;

/** LED 颜色 */
typedef struct {
    uint8_t r, g, b;            /**< RGB [0, 255] */
    uint8_t brightness;         /**< 亮度 [0, 255] */
} qoo_led_color_t;

/**
 * @brief 设置 LED 灯环模式
 */
qoo_error_t qoo_hal_led_set_pattern(qoo_led_pattern_t pattern);

/**
 * @brief 设置 LED 自定义颜色
 * @param segment 灯环段 (0~N)
 * @param color 颜色
 */
qoo_error_t qoo_hal_led_set_segment(uint32_t segment, const qoo_led_color_t *color);

/**
 * @brief 设置显示屏内容
 * @param text 显示文本
 */
qoo_error_t qoo_hal_display_set_text(const char *text);

/**
 * @brief 蜂鸣器控制
 * @param frequency_hz 频率, 0=关闭
 * @param duration_ms 持续时间, 0=持续
 */
qoo_error_t qoo_hal_buzzer_beep(uint32_t frequency_hz, uint32_t duration_ms);

/*===========================================================================
 * 防篡改
 *===========================================================================*/

/**
 * @brief 获取防拆状态
 * @return true=外壳被打开
 */
bool qoo_hal_tamper_is_detected(void);

#ifdef __cplusplus
}
#endif

#endif /* QOO_HAL_SAFETY_H */
