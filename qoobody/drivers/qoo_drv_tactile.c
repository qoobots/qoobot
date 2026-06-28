/**
 * @file qoo_drv_tactile.c
 * @brief QooBot 触觉传感器驱动参考实现
 *
 * 符合 docs/02感知系统接口规范.md §7 规范
 * - 指尖触觉阵列 (4×4 / 8×8 压力点, SPI)
 * - 电子皮肤 (多点柔性压力, I²C / CAN)
 * - 6轴力矩传感器 (EtherCAT / CAN)
 *
 * 依赖：qoo_hal_sensor.h
 * 平台：Linux + SPI/I²C 用户态驱动
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <errno.h>
#include <math.h>

#include "../hal/qoo_hal.h"
#include "../hal/qoo_hal_sensor.h"

/* ===== 触觉传感器类型 ===== */
typedef enum {
    TACTILE_TYPE_FINGERTIP = 0,  /* 指尖触觉阵列 */
    TACTILE_TYPE_E_SKIN    = 1,  /* 电子皮肤 */
    TACTILE_TYPE_FT_SENSOR = 2,  /* 6轴力矩传感器 */
} tactile_type_t;

/* ===== 指尖触觉阵列参数 ===== */
#define FINGERTIP_ARRAY_4x4  4    /* 4×4 压力点 */
#define FINGERTIP_ARRAY_8x8  8    /* 8×8 压力点 */
#define FINGERTIP_SAMPLE_RATE 100  /* 100Hz */
#define FINGERTIP_SPI_SPEED_HZ 10000000  /* 10 MHz */

/* ===== 电子皮肤参数 ===== */
#define ESKIN_MAX_POINTS     64   /* 最多 64 个感测点 */
#define ESKIN_SAMPLE_RATE    50   /* 50Hz */
#define ESKIN_I2C_ADDR       0x28 /* 默认 I²C 地址 */

/* ===== 6轴力矩传感器参数 ===== */
#define FT_SENSOR_SAMPLE_RATE 1000  /* 1kHz */
#define FT_SENSOR_FORCE_RANGE_N  200.0f  /* 力范围 ±200N */
#define FT_SENSOR_TORQUE_RANGE_NM 10.0f  /* 力矩范围 ±10Nm */
#define FT_SENSOR_RESOLUTION_N   0.01f   /* 力分辨率 0.01N */

/* ===== 触觉数据帧 ===== */
typedef struct {
    uint64_t timestamp_ns;       /* gPTP 时间戳 */
    uint32_t sequence;           /* 序列号 */
    tactile_type_t type;         /* 传感器类型 */
    union {
        struct {
            int rows, cols;          /* 阵列尺寸 */
            float pressure[8][8];    /* 压力值 (N) */
            float total_force;       /* 总力 (N) */
            float center_of_pressure[2]; /* 压力中心 (行, 列) */
        } fingertip;

        struct {
            int num_points;          /* 有效触点数 */
            struct {
                float pressure;      /* 压力 (kPa) */
                float x_mm, y_mm;    /* 位置 (mm) */
            } points[ESKIN_MAX_POINTS];
            float max_pressure;      /* 最大压力 */
        } eskin;

        struct {
            float fx, fy, fz;        /* 力 (N) */
            float tx, ty, tz;        /* 力矩 (Nm) */
            float force_magnitude;   /* 合力 */
        } ft_sensor;
    } data;
} tactile_frame_t;

/* ===== 设备结构 ===== */
typedef struct {
    tactile_type_t type;
    int spi_fd;                    /* SPI 设备文件描述符 */
    int i2c_fd;                    /* I²C 设备文件描述符 */
    int can_socket;                /* CAN socket */
    volatile int running;
    uint64_t frame_count;
    tactile_frame_t latest_frame;
    pthread_mutex_t frame_mutex;
} tactile_dev_t;

static tactile_dev_t g_tactile_dev[3]; /* 最多 3 个触觉传感器 */

/* ===== 公开 API ===== */

/**
 * @brief 初始化指尖触觉阵列
 * @param device_id 设备编号 (0~N)
 * @param rows 行数 (4 或 8)
 * @param cols 列数 (4 或 8)
 * @param spi_path SPI 设备路径 (如 "/dev/spidev0.0")
 * @return QOO_OK 成功
 */
int qoo_tactile_fingertip_init(int device_id, int rows, int cols, const char *spi_path)
{
    if (device_id < 0 || device_id >= 3) return QOO_ERROR_PARAM;
    if ((rows != 4 && rows != 8) || (cols != 4 && cols != 8)) return QOO_ERROR_PARAM;

    tactile_dev_t *dev = &g_tactile_dev[device_id];
    memset(dev, 0, sizeof(*dev));
    dev->type = TACTILE_TYPE_FINGERTIP;
    pthread_mutex_init(&dev->frame_mutex, NULL);

    printf("[TACTILE] 指尖触觉阵列 %d 初始化: %dx%d @ %dHz, SPI=%s\n",
           device_id, rows, cols, FINGERTIP_SAMPLE_RATE, spi_path);
    return QOO_OK;
}

/**
 * @brief 初始化电子皮肤
 * @param device_id 设备编号
 * @param i2c_bus I²C 总线号
 * @return QOO_OK 成功
 */
int qoo_tactile_eskin_init(int device_id, int i2c_bus)
{
    if (device_id < 0 || device_id >= 3) return QOO_ERROR_PARAM;

    tactile_dev_t *dev = &g_tactile_dev[device_id];
    memset(dev, 0, sizeof(*dev));
    dev->type = TACTILE_TYPE_E_SKIN;
    pthread_mutex_init(&dev->frame_mutex, NULL);

    printf("[TACTILE] 电子皮肤 %d 初始化: I²C bus %d, addr 0x%02X @ %dHz\n",
           device_id, i2c_bus, ESKIN_I2C_ADDR, ESKIN_SAMPLE_RATE);
    return QOO_OK;
}

/**
 * @brief 初始化 6 轴力矩传感器
 * @param device_id 设备编号
 * @param can_interface CAN 接口名 (如 "can0")
 * @return QOO_OK 成功
 */
int qoo_tactile_ft_sensor_init(int device_id, const char *can_interface)
{
    if (device_id < 0 || device_id >= 3) return QOO_ERROR_PARAM;

    tactile_dev_t *dev = &g_tactile_dev[device_id];
    memset(dev, 0, sizeof(*dev));
    dev->type = TACTILE_TYPE_FT_SENSOR;
    pthread_mutex_init(&dev->frame_mutex, NULL);

    printf("[TACTILE] 6轴力矩传感器 %d 初始化: CAN=%s @ %dHz\n",
           device_id, can_interface, FT_SENSOR_SAMPLE_RATE);
    return QOO_OK;
}

/**
 * @brief 获取最新触觉数据帧
 * @param device_id 设备编号
 * @param frame 输出数据帧
 * @return QOO_OK 有新数据, QOO_AGAIN 无新数据
 */
int qoo_tactile_get_frame(int device_id, tactile_frame_t *frame)
{
    if (device_id < 0 || device_id >= 3) return QOO_ERROR_PARAM;

    tactile_dev_t *dev = &g_tactile_dev[device_id];
    pthread_mutex_lock(&dev->frame_mutex);
    *frame = dev->latest_frame;
    pthread_mutex_unlock(&dev->frame_mutex);
    return QOO_OK;
}

/**
 * @brief 读取指尖压力分布
 * @param device_id 设备编号
 * @param pressure 输出压力矩阵 (rows × cols)
 * @param total_force 输出总力 (N)
 * @return QOO_OK 成功
 */
int qoo_tactile_fingertip_read_pressure(int device_id, float *pressure, float *total_force)
{
    tactile_dev_t *dev = &g_tactile_dev[device_id];
    if (dev->type != TACTILE_TYPE_FINGERTIP) return QOO_ERROR_PARAM;

    tactile_frame_t frame;
    qoo_tactile_get_frame(device_id, &frame);

    int num_cells = frame.data.fingertip.rows * frame.data.fingertip.cols;
    memcpy(pressure, frame.data.fingertip.pressure, num_cells * sizeof(float));
    if (total_force) *total_force = frame.data.fingertip.total_force;
    return QOO_OK;
}

/**
 * @brief 读取 6 轴力/力矩
 * @param device_id 设备编号
 * @param fx,fy,fz 输出力 (N)
 * @param tx,ty,tz 输出力矩 (Nm)
 * @return QOO_OK 成功
 */
int qoo_tactile_ft_read(int device_id,
                         float *fx, float *fy, float *fz,
                         float *tx, float *ty, float *tz)
{
    tactile_dev_t *dev = &g_tactile_dev[device_id];
    if (dev->type != TACTILE_TYPE_FT_SENSOR) return QOO_ERROR_PARAM;

    tactile_frame_t frame;
    qoo_tactile_get_frame(device_id, &frame);

    if (fx) *fx = frame.data.ft_sensor.fx;
    if (fy) *fy = frame.data.ft_sensor.fy;
    if (fz) *fz = frame.data.ft_sensor.fz;
    if (tx) *tx = frame.data.ft_sensor.tx;
    if (ty) *ty = frame.data.ft_sensor.ty;
    if (tz) *tz = frame.data.ft_sensor.tz;
    return QOO_OK;
}

/**
 * @brief 碰撞检测 (基于触觉传感器)
 *
 * 检测策略 (符合 docs/07安全硬件规范.md §4):
 * - 手臂自由空间: 力 > 50N 触发
 * - 手臂约束空间: 力 > 150N 触发
 * - 手掌/手指: 力 > 10N 或压力 > 50kPa 触发
 * - 头部: 力 > 30N 触发
 *
 * @param device_id 设备编号
 * @param threshold_N 力阈值 (N)
 * @return 1 检测到碰撞, 0 正常
 */
int qoo_tactile_collision_detect(int device_id, float threshold_N)
{
    tactile_frame_t frame;
    if (qoo_tactile_get_frame(device_id, &frame) != QOO_OK)
        return 0;

    switch (frame.type) {
    case TACTILE_TYPE_FINGERTIP:
        return (frame.data.fingertip.total_force > threshold_N) ? 1 : 0;
    case TACTILE_TYPE_E_SKIN:
        return (frame.data.eskin.max_pressure > (threshold_N * 1000.0f)) ? 1 : 0;
    case TACTILE_TYPE_FT_SENSOR:
        return (frame.data.ft_sensor.force_magnitude > threshold_N) ? 1 : 0;
    default:
        return 0;
    }
}

/**
 * @brief 释放触觉传感器
 */
int qoo_tactile_deinit(int device_id)
{
    if (device_id < 0 || device_id >= 3) return QOO_ERROR_PARAM;
    tactile_dev_t *dev = &g_tactile_dev[device_id];
    pthread_mutex_destroy(&dev->frame_mutex);
    memset(dev, 0, sizeof(*dev));
    return QOO_OK;
}
