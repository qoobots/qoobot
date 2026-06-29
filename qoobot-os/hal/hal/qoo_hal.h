/**
 * @file qoo_hal.h
 * @brief QooBot 硬件抽象层 (HAL) — 主入口头文件
 *
 * 本文件定义 qoobrain 与硬件之间的所有标准化接口。
 * 任何符合本 HAL 规范的硬件平台均可运行 qoobrain。
 *
 * 版本: v0.1 | 2026-06-26
 */

#ifndef QOO_HAL_H
#define QOO_HAL_H

#include "qoo_hal_types.h"
#include "qoo_hal_sensor.h"
#include "qoo_hal_actuator.h"
#include "qoo_hal_power.h"
#include "qoo_hal_safety.h"
#include "qoo_hal_comm.h"
#include "qoo_hal_time.h"
#include "qoo_hal_error.h"

#ifdef __cplusplus
extern "C" {
#endif

/*===========================================================================
 * 系统初始化与生命周期
 *===========================================================================*/

/**
 * @brief 初始化 HAL 层，探测并注册所有硬件
 * @param config HAL 配置（平台相关）
 * @return QOO_OK 成功，其他为错误码
 */
qoo_error_t qoo_hal_init(const qoo_hal_config_t *config);

/**
 * @brief 启动 HAL，开始数据采集和控制循环
 * @return QOO_OK 成功
 */
qoo_error_t qoo_hal_start(void);

/**
 * @brief 停止 HAL，安全关闭所有硬件
 * @return QOO_OK 成功
 */
qoo_error_t qoo_hal_stop(void);

/**
 * @brief 获取 HAL 运行状态
 * @return 当前状态
 */
qoo_hal_state_t qoo_hal_get_state(void);

/**
 * @brief 获取 HAL 版本信息
 * @return 版本号字符串
 */
const char* qoo_hal_get_version(void);

/**
 * @brief 获取已注册的硬件清单
 * @param inventory [out] 硬件清单
 * @return QOO_OK 成功
 */
qoo_error_t qoo_hal_get_inventory(qoo_hw_inventory_t *inventory);

#ifdef __cplusplus
}
#endif

#endif /* QOO_HAL_H */
