/**
 * @file qoo_hal_error.h
 * @brief HAL 错误处理与诊断接口
 */

#ifndef QOO_HAL_ERROR_H
#define QOO_HAL_ERROR_H

#include "qoo_hal_types.h"

#ifdef __cplusplus
extern "C" {
#endif

/*===========================================================================
 * 错误码
 *===========================================================================*/

/** 错误严重等级 */
typedef enum {
    QOO_ERROR_SEVERITY_INFO = 0,    /**< 信息 (非错误) */
    QOO_ERROR_SEVERITY_WARNING,     /**< 警告 (可恢复) */
    QOO_ERROR_SEVERITY_ERROR,       /**< 错误 (需处理) */
    QOO_ERROR_SEVERITY_CRITICAL,    /**< 严重错误 (需立即停止) */
    QOO_ERROR_SEVERITY_FATAL,       /**< 致命错误 (需重启) */
} qoo_error_severity_t;

/** 错误类别 */
typedef enum {
    QOO_ERROR_CAT_NONE = 0,
    QOO_ERROR_CAT_SENSOR,           /**< 传感器错误 */
    QOO_ERROR_CAT_ACTUATOR,         /**< 执行器错误 */
    QOO_ERROR_CAT_POWER,            /**< 电源错误 */
    QOO_ERROR_CAT_COMM,             /**< 通信错误 */
    QOO_ERROR_CAT_SAFETY,           /**< 安全错误 */
    QOO_ERROR_CAT_COMPUTE,          /**< 计算错误 */
    QOO_ERROR_CAT_SYSTEM,           /**< 系统错误 */
} qoo_error_category_t;

/** 错误记录 */
typedef struct {
    qoo_timestamp_us_t timestamp;
    qoo_error_category_t category;
    qoo_error_severity_t severity;
    qoo_error_t code;
    uint32_t component_id;          /**< 出错的硬件组件 ID */
    char message[128];
} qoo_error_record_t;

/*===========================================================================
 * 错误管理
 *===========================================================================*/

/**
 * @brief 上报错误
 * @param record 错误记录
 */
qoo_error_t qoo_hal_error_report(const qoo_error_record_t *record);

/**
 * @brief 获取最近 N 条错误记录
 * @param records [out] 错误记录数组
 * @param max_count 最大数量
 * @param count [out] 实际返回数量
 */
qoo_error_t qoo_hal_error_get_recent(qoo_error_record_t *records,
    uint32_t max_count, uint32_t *count);

/**
 * @brief 清除错误历史
 */
qoo_error_t qoo_hal_error_clear(void);

/**
 * @brief 注册错误回调
 */
qoo_error_t qoo_hal_error_register_callback(
    void (*callback)(const qoo_error_record_t *record, void *user_data),
    void *user_data);

/**
 * @brief 将错误码转为字符串
 */
const char* qoo_hal_error_to_string(qoo_error_t code);

/**
 * @brief 获取错误统计
 * @param category 错误类别
 * @param total [out] 总错误数
 * @param active [out] 当前活跃错误数
 */
qoo_error_t qoo_hal_error_get_stats(qoo_error_category_t category,
    uint32_t *total, uint32_t *active);

#ifdef __cplusplus
}
#endif

#endif /* QOO_HAL_ERROR_H */
