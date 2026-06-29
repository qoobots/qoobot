/**
 * @file qoo_hal_power.h
 * @brief 能源系统抽象接口 — BMS / 充电 / 功耗管理 / 低功耗模式
 */

#ifndef QOO_HAL_POWER_H
#define QOO_HAL_POWER_H

#include "qoo_hal_types.h"

#ifdef __cplusplus
extern "C" {
#endif

/*===========================================================================
 * 电池管理系统 (BMS)
 *===========================================================================*/

/** 电池状态 */
typedef struct {
    qoo_timestamp_us_t timestamp;
    float voltage_total;        /**< 总电压 (V) */
    float current;              /**< 电流 (A), 正=放电, 负=充电 */
    float soc;                  /**< State of Charge [0, 100] % */
    float soh;                  /**< State of Health [0, 100] % */
    float temperature;          /**< 温度 (°C) */
    float remaining_capacity;   /**< 剩余容量 (Wh) */
    float full_capacity;        /**< 满充容量 (Wh) */
    float time_to_empty;        /**< 预估剩余时间 (分钟) */
    uint32_t cycle_count;       /**< 充放电循环次数 */
    bool is_charging;           /**< 是否正在充电 */
    uint32_t fault_flags;       /**< 故障标志 */
} qoo_bms_state_t;

/** 电芯信息 */
typedef struct {
    uint8_t cell_count;
    float cell_voltages[16];    /**< 单体电压 (最多 16 串) */
    float cell_temps[4];        /**< 多点温度 */
    float voltage_min, voltage_max; /**< 单体电压极值 */
    float temp_min, temp_max;   /**< 温度极值 */
    float imbalance_mv;         /**< 最大压差 (mV) */
} qoo_bms_cell_info_t;

/**
 * @brief 获取 BMS 状态
 */
qoo_error_t qoo_hal_bms_get_state(qoo_bms_state_t *state);

/**
 * @brief 获取电芯详细信息
 */
qoo_error_t qoo_hal_bms_get_cell_info(qoo_bms_cell_info_t *info);

/*===========================================================================
 * 电源树
 *===========================================================================*/

/** 电源域 */
typedef enum {
    QOO_PWR_DOMAIN_MAIN,        /**< 主计算域 */
    QOO_PWR_DOMAIN_SENSOR,      /**< 传感器域 */
    QOO_PWR_DOMAIN_ACTUATOR,    /**< 执行器域 */
    QOO_PWR_DOMAIN_SAFETY,      /**< 安全域 (常供电) */
    QOO_PWR_DOMAIN_COMM,        /**< 通信域 */
} qoo_power_domain_t;

/** 电源域状态 */
typedef struct {
    qoo_power_domain_t domain;
    float voltage;              /**< 当前电压 (V) */
    float current;              /**< 当前电流 (A) */
    float power;                /**< 当前功率 (W) */
    bool enabled;
} qoo_power_domain_state_t;

/**
 * @brief 获取指定电源域状态
 */
qoo_error_t qoo_hal_power_get_domain_state(qoo_power_domain_t domain,
    qoo_power_domain_state_t *state);

/**
 * @brief 控制电源域开关
 */
qoo_error_t qoo_hal_power_set_domain(qoo_power_domain_t domain, bool enable);

/*===========================================================================
 * 充电系统
 *===========================================================================*/

/** 充电状态 */
typedef enum {
    QOO_CHARGE_STATE_IDLE = 0,
    QOO_CHARGE_STATE_DOCKING,       /**< 正在对接充电座 */
    QOO_CHARGE_STATE_DOCKED,        /**< 已对接 */
    QOO_CHARGE_STATE_CC,            /**< 恒流充电 */
    QOO_CHARGE_STATE_CV,            /**< 恒压充电 */
    QOO_CHARGE_STATE_COMPLETE,      /**< 充电完成 */
    QOO_CHARGE_STATE_FAULT,         /**< 充电故障 */
} qoo_charge_state_t;

typedef struct {
    qoo_timestamp_us_t timestamp;
    qoo_charge_state_t state;
    float charge_power;         /**< 充电功率 (W) */
    float charge_current;       /**< 充电电流 (A) */
    float time_to_full;         /**< 预估充满时间 (分钟) */
    bool dock_detected;         /**< 是否检测到充电座 */
} qoo_charger_state_t;

/**
 * @brief 获取充电状态
 */
qoo_error_t qoo_hal_charger_get_state(qoo_charger_state_t *state);

/**
 * @brief 请求自主回充 (启动对接流程)
 */
qoo_error_t qoo_hal_charger_request_docking(void);

/*===========================================================================
 * 功耗管理
 *===========================================================================*/

/** 低功耗模式 */
typedef enum {
    QOO_LP_MODE_ACTIVE,         /**< 全功能运行 */
    QOO_LP_MODE_STANDBY,        /**< 待机 (传感器关闭, 通信保持) */
    QOO_LP_MODE_SLEEP,          /**< 休眠 (仅安全域运行) */
    QOO_LP_MODE_DEEP_SLEEP,     /**< 深度休眠 (RTC 唤醒) */
    QOO_LP_MODE_SHIPPING,       /**< 运输模式 (完全断电) */
} qoo_low_power_mode_t;

/** 功耗预算 */
typedef struct {
    float compute_power;        /**< 计算平台 (W) */
    float sensor_power;         /**< 传感器 (W) */
    float actuator_power;       /**< 执行器 (W) */
    float comm_power;           /**< 通信 (W) */
    float safety_power;         /**< 安全系统 (W) */
    float total_power;          /**< 总功耗 (W) */
    float peak_available;       /**< 可用峰值功率 (W) */
    float thermal_headroom;     /**< 热余量 (°C) */
} qoo_power_budget_t;

/**
 * @brief 获取当前功耗预算
 */
qoo_error_t qoo_hal_power_get_budget(qoo_power_budget_t *budget);

/**
 * @brief 设置低功耗模式
 */
qoo_error_t qoo_hal_power_set_low_power_mode(qoo_low_power_mode_t mode);

/**
 * @brief 获取低功耗模式
 */
qoo_low_power_mode_t qoo_hal_power_get_low_power_mode(void);

/**
 * @brief 注册唤醒源
 * @param wakeup_sources 唤醒源位掩码 (bit0=RTC, bit1=充电, bit2=通信, bit3=按键)
 */
qoo_error_t qoo_hal_power_set_wakeup_sources(uint32_t wakeup_sources);

#ifdef __cplusplus
}
#endif

#endif /* QOO_HAL_POWER_H */
