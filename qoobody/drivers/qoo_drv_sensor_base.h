/**
 * @file qoo_drv_sensor_base.h
 * @brief 传感器驱动基类 — 定义所有传感器驱动的统一接口
 *
 * 每个具体传感器驱动实现此接口，通过 HAL 注册后即可被 qoobrain 访问。
 */

#ifndef QOO_DRV_SENSOR_BASE_H
#define QOO_DRV_SENSOR_BASE_H

#include "../hal/qoo_hal_types.h"
#include "../hal/qoo_hal_sensor.h"

#ifdef __cplusplus
extern "C" {
#endif

/*===========================================================================
 * 传感器驱动虚表 (VTable)
 *===========================================================================*/

/** 传感器驱动操作接口 (类似面向对象的虚函数表) */
typedef struct {
    /** 驱动名称 */
    const char *name;

    /** 初始化传感器硬件 */
    qoo_error_t (*init)(void *drv_ctx);

    /** 反初始化/释放资源 */
    qoo_error_t (*deinit)(void *drv_ctx);

    /** 启动数据流 */
    qoo_error_t (*start)(void *drv_ctx);

    /** 停止数据流 */
    qoo_error_t (*stop)(void *drv_ctx);

    /** 读取传感器数据 (阻塞, 带超时) */
    qoo_error_t (*read)(void *drv_ctx, void *data, uint32_t timeout_ms);

    /** 获取传感器配置 */
    qoo_error_t (*get_config)(void *drv_ctx, void *config);

    /** 设置传感器配置 */
    qoo_error_t (*set_config)(void *drv_ctx, const void *config);

    /** 自检 */
    qoo_error_t (*self_test)(void *drv_ctx, bool *healthy);

    /** 获取传感器信息 */
    qoo_error_t (*get_info)(void *drv_ctx, qoo_hw_component_t *info);
} qoo_drv_sensor_ops_t;

/** 传感器驱动实例 */
typedef struct {
    const qoo_drv_sensor_ops_t *ops;  /**< 操作接口 */
    void *ctx;                         /**< 驱动上下文 (私有数据) */
    uint32_t id;                       /**< 传感器 ID */
    bool initialized;
    bool streaming;
} qoo_drv_sensor_t;

/*===========================================================================
 * 驱动管理
 *===========================================================================*/

/**
 * @brief 注册传感器驱动到 HAL
 * @param driver 驱动实例
 * @param sensor_id [out] 分配的传感器 ID
 */
qoo_error_t qoo_drv_sensor_register(qoo_drv_sensor_t *driver, uint32_t *sensor_id);

/**
 * @brief 注销传感器驱动
 * @param sensor_id 传感器 ID
 */
qoo_error_t qoo_drv_sensor_unregister(uint32_t sensor_id);

/**
 * @brief 根据 ID 查找传感器驱动
 */
qoo_drv_sensor_t* qoo_drv_sensor_find(uint32_t sensor_id);

#ifdef __cplusplus
}
#endif

#endif /* QOO_DRV_SENSOR_BASE_H */
