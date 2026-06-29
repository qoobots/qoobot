/**
 * @file qoo_hal_time.h
 * @brief 时间同步抽象接口 — gPTP / 硬件触发 / 时间戳管理
 */

#ifndef QOO_HAL_TIME_H
#define QOO_HAL_TIME_H

#include "qoo_hal_types.h"

#ifdef __cplusplus
extern "C" {
#endif

/*===========================================================================
 * 系统时间
 *===========================================================================*/

/**
 * @brief 获取系统时间 (μs)
 * @note 单调递增，用于控制循环计时
 */
qoo_timestamp_us_t qoo_hal_time_now(void);

/**
 * @brief 获取 UTC 时间戳
 * @param sec [out] 秒
 * @param nsec [out] 纳秒
 */
qoo_error_t qoo_hal_time_get_utc(uint64_t *sec, uint32_t *nsec);

/*===========================================================================
 * gPTP 时间同步 (IEEE 802.1AS)
 *===========================================================================*/

/** gPTP 同步状态 */
typedef enum {
    QOO_PTP_STATE_INITIALIZING,
    QOO_PTP_STATE_FAULTY,
    QOO_PTP_STATE_DISABLED,
    QOO_PTP_STATE_LISTENING,
    QOO_PTP_STATE_PRE_MASTER,
    QOO_PTP_STATE_MASTER,
    QOO_PTP_STATE_PASSIVE,
    QOO_PTP_STATE_UNCALIBRATED,
    QOO_PTP_STATE_SLAVE,
} qoo_ptp_state_t;

/** gPTP 状态 */
typedef struct {
    qoo_ptp_state_t state;
    int64_t offset_from_master;     /**< 与主时钟偏差 (ns) */
    uint32_t mean_path_delay;       /**< 平均路径延迟 (ns) */
    uint8_t gm_priority1;           /**< Grandmaster Priority1 */
    uint8_t gm_priority2;
    uint64_t gm_identity[2];        /**< Grandmaster 标识 */
    bool is_grandmaster;            /**< 是否为 Grandmaster */
} qoo_ptp_status_t;

/**
 * @brief 初始化 gPTP 时间同步
 */
qoo_error_t qoo_hal_ptp_init(void);

/**
 * @brief 获取 gPTP 同步状态
 */
qoo_error_t qoo_hal_ptp_get_status(qoo_ptp_status_t *status);

/**
 * @brief 等待 gPTP 同步完成
 * @param timeout_ms 超时 (ms)
 */
qoo_error_t qoo_hal_ptp_wait_sync(uint32_t timeout_ms);

/*===========================================================================
 * 硬件触发同步
 *===========================================================================*/

/**
 * @brief 发送硬件触发脉冲 (同步传感器采集时刻)
 * @param line 触发线号
 */
qoo_error_t qoo_hal_trigger_pulse(uint32_t line);

/**
 * @brief 配置硬件触发源
 * @param source_id 触发源 (0=RTC, 1=PPS, 2=外部, 3=软件)
 * @param frequency_hz 触发频率
 */
qoo_error_t qoo_hal_trigger_configure(uint32_t source_id, uint32_t frequency_hz);

/**
 * @brief 获取触发计数器 (用于传感器帧与触发对齐)
 */
uint64_t qoo_hal_trigger_get_counter(void);

/*===========================================================================
 * 时间戳对齐
 *===========================================================================*/

/**
 * @brief 将传感器本地时间戳转换为全局同步时间戳
 * @param sensor_id 传感器 ID
 * @param local_ts 本地时间戳
 * @return 全局同步时间戳 (μs)
 */
qoo_timestamp_us_t qoo_hal_time_convert(uint32_t sensor_id, qoo_timestamp_us_t local_ts);

/**
 * @brief 获取传感器时钟偏差估计
 * @param sensor_id 传感器 ID
 * @param offset_ns [out] 时钟偏差 (ns)
 * @param drift_ppm [out] 时钟漂移 (ppm)
 */
qoo_error_t qoo_hal_time_get_sensor_offset(uint32_t sensor_id,
    int64_t *offset_ns, float *drift_ppm);

#ifdef __cplusplus
}
#endif

#endif /* QOO_HAL_TIME_H */
