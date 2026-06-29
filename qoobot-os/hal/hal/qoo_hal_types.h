/**
 * @file qoo_hal_types.h
 * @brief HAL 通用类型定义
 */

#ifndef QOO_HAL_TYPES_H
#define QOO_HAL_TYPES_H

#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

/*===========================================================================
 * 基础类型
 *===========================================================================*/

/** HAL 错误码 */
typedef int32_t qoo_error_t;
#define QOO_OK              (0)
#define QOO_ERROR          (-1)
#define QOO_ERROR_TIMEOUT  (-2)
#define QOO_ERROR_BUSY     (-3)
#define QOO_ERROR_NOT_SUPPORTED (-4)
#define QOO_ERROR_NOT_FOUND     (-5)
#define QOO_ERROR_INVALID_PARAM (-6)
#define QOO_ERROR_HW_FAULT      (-7)
#define QOO_ERROR_SAFETY_TRIGGERED (-8)

/** HAL 运行状态 */
typedef enum {
    QOO_HAL_STATE_UNINIT = 0,
    QOO_HAL_STATE_INITIALIZED,
    QOO_HAL_STATE_RUNNING,
    QOO_HAL_STATE_SAFE_MODE,
    QOO_HAL_STATE_EMERGENCY_STOP,
    QOO_HAL_STATE_ERROR,
    QOO_HAL_STATE_SHUTDOWN,
} qoo_hal_state_t;

/** 时间戳 (微秒) */
typedef uint64_t qoo_timestamp_us_t;

/** 硬件组件类型 */
typedef enum {
    QOO_HW_TYPE_SENSOR_CAMERA = 0,
    QOO_HW_TYPE_SENSOR_LIDAR,
    QOO_HW_TYPE_SENSOR_IMU,
    QOO_HW_TYPE_SENSOR_MIC_ARRAY,
    QOO_HW_TYPE_SENSOR_TACTILE,
    QOO_HW_TYPE_SENSOR_ENV,
    QOO_HW_TYPE_ACTUATOR_JOINT,
    QOO_HW_TYPE_ACTUATOR_GRIPPER,
    QOO_HW_TYPE_ACTUATOR_LINEAR,
    QOO_HW_TYPE_POWER_BMS,
    QOO_HW_TYPE_POWER_CHARGER,
    QOO_HW_TYPE_SAFETY_MCU,
    QOO_HW_TYPE_COMM_WIFI,
    QOO_HW_TYPE_COMM_BLE,
    QOO_HW_TYPE_COMM_UWB,
    QOO_HW_TYPE_COMM_5G,
    QOO_HW_TYPE_COMPUTE_SOC,
    QOO_HW_TYPE_COMPUTE_NPU,
    QOO_HW_TYPE_STRUCTURE_JOINT_MODULE,
} qoo_hw_type_t;

/** 硬件组件描述符 */
typedef struct {
    uint32_t id;                    /**< 唯一硬件 ID */
    qoo_hw_type_t type;             /**< 组件类型 */
    char name[32];                  /**< 组件名称 */
    char vendor[32];                /**< 厂商名称 */
    char model[32];                 /**< 型号 */
    char fw_version[16];            /**< 固件版本 */
    char serial[32];                /**< 序列号 */
    uint32_t capabilities;          /**< 能力位掩码 */
} qoo_hw_component_t;

/** 硬件清单 */
typedef struct {
    uint32_t count;
    qoo_hw_component_t components[64]; /**< 最多 64 个组件 */
} qoo_hw_inventory_t;

/*===========================================================================
 * 3D 数学类型
 *===========================================================================*/

/** 3D 向量 */
typedef struct {
    float x, y, z;
} qoo_vec3_t;

/** 四元数 */
typedef struct {
    float w, x, y, z;
} qoo_quat_t;

/** 3D 位姿 */
typedef struct {
    qoo_vec3_t position;   /**< 位置 (m) */
    qoo_quat_t orientation; /**< 姿态四元数 */
} qoo_pose_t;

/** 6D 速度 */
typedef struct {
    qoo_vec3_t linear;     /**< 线速度 (m/s) */
    qoo_vec3_t angular;    /**< 角速度 (rad/s) */
} qoo_twist_t;

/** 6D 力/力矩 */
typedef struct {
    qoo_vec3_t force;      /**< 力 (N) */
    qoo_vec3_t torque;     /**< 力矩 (Nm) */
} qoo_wrench_t;

/*===========================================================================
 * HAL 配置
 *===========================================================================*/

/** HAL 配置 */
typedef struct {
    uint32_t control_frequency_hz;  /**< 控制循环频率 */
    bool enable_safety_monitor;     /**< 启用安全监控 */
    bool enable_time_sync;          /**< 启用时间同步 */
    bool enable_logging;            /**< 启用日志 */
    uint32_t sensor_buffer_size;    /**< 传感器数据缓冲大小 */
    void *platform_data;            /**< 平台私有数据 */
} qoo_hal_config_t;

#ifdef __cplusplus
}
#endif

#endif /* QOO_HAL_TYPES_H */
