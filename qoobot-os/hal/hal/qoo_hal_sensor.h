/**
 * @file qoo_hal_sensor.h
 * @brief 传感器抽象接口 — 视觉 / LiDAR / IMU / 麦克风 / 触觉 / 环境
 */

#ifndef QOO_HAL_SENSOR_H
#define QOO_HAL_SENSOR_H

#include "qoo_hal_types.h"

#ifdef __cplusplus
extern "C" {
#endif

/*===========================================================================
 * 通用传感器接口
 *===========================================================================*/

/** 传感器数据头 (所有传感器数据包的前缀) */
typedef struct {
    qoo_timestamp_us_t timestamp;   /**< 硬件时间戳 (μs) */
    uint32_t sensor_id;             /**< 传感器 ID */
    uint32_t sequence;              /**< 帧序号 */
    uint32_t flags;                 /**< 标志位: bit0=有效, bit1=时间同步, bit2=错误 */
    uint32_t data_size;             /**< 负载大小 (字节) */
} qoo_sensor_header_t;

/*===========================================================================
 * 视觉传感器 (RGB-D / Stereo / 多目)
 *===========================================================================*/

/** 相机内参 */
typedef struct {
    float fx, fy;           /**< 焦距 (像素) */
    float cx, cy;           /**< 主点 (像素) */
    float k1, k2, k3;       /**< 径向畸变 */
    float p1, p2;           /**< 切向畸变 */
} qoo_camera_intrinsics_t;

/** 相机外参 (相对于基准坐标系) */
typedef struct {
    qoo_pose_t pose;        /**< 相机在基准坐标系的位姿 */
} qoo_camera_extrinsics_t;

/** RGB 图像 */
typedef struct {
    qoo_sensor_header_t header;
    uint32_t width, height;
    uint32_t stride;            /**< 行步长 (字节) */
    uint32_t format;            /**< 像素格式: 0=RGB888, 1=BGR888, 2=YUV420, 3=NV12 */
    qoo_camera_intrinsics_t intrinsics;
    const uint8_t *data;        /**< 图像数据指针 */
} qoo_image_t;

/** 深度图 */
typedef struct {
    qoo_sensor_header_t header;
    uint32_t width, height;
    float depth_scale;          /**< 深度单位 (m/count), 如 0.001 表示 mm */
    float min_depth, max_depth; /**< 有效深度范围 (m) */
    const uint16_t *data;       /**< 16bit 深度数据指针 */
} qoo_depth_image_t;

/** RGB-D 帧 (对齐后的彩色+深度) */
typedef struct {
    qoo_sensor_header_t header;
    qoo_image_t rgb;
    qoo_depth_image_t depth;
    qoo_camera_extrinsics_t extrinsics;
} qoo_rgbd_frame_t;

/**
 * @brief 获取最新 RGB-D 帧 (非阻塞)
 * @param sensor_id 传感器 ID
 * @param frame [out] 帧数据
 * @return QOO_OK 有新帧, QOO_ERROR_BUSY 无新帧
 */
qoo_error_t qoo_hal_camera_get_frame(uint32_t sensor_id, qoo_rgbd_frame_t *frame);

/**
 * @brief 注册帧回调 (零拷贝模式)
 * @param sensor_id 传感器 ID
 * @param callback 回调函数
 * @param user_data 用户数据
 */
qoo_error_t qoo_hal_camera_register_callback(uint32_t sensor_id,
    void (*callback)(const qoo_rgbd_frame_t *frame, void *user_data),
    void *user_data);

/*===========================================================================
 * LiDAR 传感器 (2D / 3D / ToF)
 *===========================================================================*/

/** LiDAR 点 */
typedef struct {
    float x, y, z;          /**< 坐标 (m) */
    float intensity;        /**< 反射强度 [0, 1] */
    uint16_t ring;          /**< 激光线号 (多线 LiDAR) */
    qoo_timestamp_us_t timestamp; /**< 单点时间戳 (用于运动补偿) */
} qoo_lidar_point_t;

/** LiDAR 点云 */
typedef struct {
    qoo_sensor_header_t header;
    uint32_t point_count;
    uint32_t max_points;
    const qoo_lidar_point_t *points;
    qoo_pose_t sensor_pose;     /**< 传感器在基准坐标系的位姿 */
} qoo_pointcloud_t;

/**
 * @brief 获取最新点云
 * @param sensor_id 传感器 ID
 * @param cloud [out] 点云数据
 */
qoo_error_t qoo_hal_lidar_get_cloud(uint32_t sensor_id, qoo_pointcloud_t *cloud);

/*===========================================================================
 * IMU 惯性传感器 (6轴 / 9轴)
 *===========================================================================*/

/** IMU 数据 */
typedef struct {
    qoo_sensor_header_t header;
    qoo_vec3_t accel;           /**< 加速度 (m/s²) */
    qoo_vec3_t gyro;            /**< 角速度 (rad/s) */
    qoo_vec3_t mag;             /**< 磁场 (μT), 9轴有效 */
    float temperature;          /**< 温度 (°C) */
} qoo_imu_data_t;

/**
 * @brief 获取最新 IMU 数据
 * @param sensor_id 传感器 ID
 * @param imu [out] IMU 数据
 */
qoo_error_t qoo_hal_imu_get_data(uint32_t sensor_id, qoo_imu_data_t *imu);

/**
 * @brief 获取 IMU 偏置估计 (用于导航)
 * @param sensor_id 传感器 ID
 * @param accel_bias [out] 加速度计偏置
 * @param gyro_bias [out] 陀螺仪偏置
 */
qoo_error_t qoo_hal_imu_get_bias(uint32_t sensor_id,
    qoo_vec3_t *accel_bias, qoo_vec3_t *gyro_bias);

/*===========================================================================
 * 麦克风阵列
 *===========================================================================*/

/** 音频帧 */
typedef struct {
    qoo_sensor_header_t header;
    uint8_t channel_count;      /**< 通道数 (4/6/8) */
    uint32_t sample_rate;       /**< 采样率 (Hz) */
    uint32_t sample_count;      /**< 每通道采样数 */
    const int16_t *data;        /**< 交织音频数据 [channel][sample] */
    int16_t aec_ref;            /**< AEC 参考信号 (回采信号) */
} qoo_audio_frame_t;

/**
 * @brief 获取最新音频帧
 * @param sensor_id 传感器 ID
 * @param audio [out] 音频帧
 */
qoo_error_t qoo_hal_mic_get_frame(uint32_t sensor_id, qoo_audio_frame_t *audio);

/*===========================================================================
 * 触觉传感器 (指尖/手掌阵列)
 *===========================================================================*/

/** 触觉传感器数据 */
typedef struct {
    qoo_sensor_header_t header;
    uint8_t taxel_count;        /**< 触觉单元数 */
    const float *pressure;      /**< 压力值 [taxel_count] (N) */
    qoo_vec3_t contact_point;   /**< 接触点位置 (传感器坐标系) */
    qoo_vec3_t contact_force;   /**< 合力 (传感器坐标系) */
} qoo_tactile_data_t;

qoo_error_t qoo_hal_tactile_get_data(uint32_t sensor_id, qoo_tactile_data_t *tactile);

/*===========================================================================
 * 环境传感器
 *===========================================================================*/

typedef struct {
    qoo_sensor_header_t header;
    float temperature;          /**< 温度 (°C) */
    float humidity;             /**< 湿度 (%RH) */
    float pressure;             /**< 气压 (hPa) */
    float gas_voc;              /**< VOC 指数 */
    float ambient_light;        /**< 环境光 (lux) */
} qoo_env_data_t;

qoo_error_t qoo_hal_env_get_data(uint32_t sensor_id, qoo_env_data_t *env);

#ifdef __cplusplus
}
#endif

#endif /* QOO_HAL_SENSOR_H */
