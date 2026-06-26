/**
 * @file qoo_drv_imu.c
 * @brief 通用 IMU 传感器驱动参考实现 (SPI/I2C)
 *
 * 支持型号: BMI270, ICM-42688, MPU6050/9250, ICM-20948
 * 接口: SPI 4-wire (高速) / I2C (低速)
 * 数据输出: FIFO + 数据就绪中断 (DRDY)
 *
 * 编译:
 *   $ gcc -I. -shared -o libqoo_imu.so qoo_drv_imu.c
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <stdbool.h>
#include <errno.h>
#include <unistd.h>
#include <math.h>
#include <pthread.h>

#include "../hal/qoo_hal_types.h"
#include "../hal/qoo_hal_time.h"
#include "../hal/qoo_hal_sensor.h"

/*===========================================================================
 * 配置
 *===========================================================================*/

#define IMU_MAX_DEVICES      8
#define IMU_FIFO_SIZE       512   /* FIFO 深度 (bytes) */
#define IMU_SAMPLE_RATE_HZ 200   /* 输出速率 (Hz) */
#define IMU_DEFAULT_RANGE_G  8    /* 加速度计量程 (±g) */
#define IMU_DEFAULT_RANGE_DPS 2000 /* 陀螺仪量程 (±°/s) */
#define IMU_THREAD_PRIORITY  72    /* SCHED_FIFO 优先级 */

/*===========================================================================
 * IMU 型号定义
 *===========================================================================*/

typedef enum {
    IMU_MODEL_BMI270 = 0,
    IMU_MODEL_ICM42688,
    IMU_MODEL_MPU6050,
    IMU_MODEL_MPU9250,
    IMU_MODEL_ICM20948,
    IMU_MODEL_BMI160,
    IMU_MODEL_COUNT
} qoo_imu_model_t;

static const char *imu_model_names[] = {
    "BMI270", "ICM-42688", "MPU-6050",
    "MPU-9250", "ICM-20948", "BMI160"
};

/*===========================================================================
 * 数据结构
 *===========================================================================*/

/** IMU 原始数据 (未校准) */
typedef struct {
    int16_t accel_x, accel_y, accel_z;  /* 加速度 (raw) */
    int16_t gyro_x,  gyro_y,  gyro_z;   /* 陀螺仪 (raw) */
    int16_t temp;                          /* 温度 (raw, 0.01°C) */
    uint32_t timestamp_ns;                 /* 采集时间戳 (ns) */
    uint8_t  status;                      /* 状态位 (DRDY 等) */
} qoo_imu_raw_data_t;

/** IMU 校准参数 (出厂校准 + 运行时校准) */
typedef struct {
    /* 加速度计零偏 (m/s²) */
    float accel_bias[3];
    /* 陀螺仪零偏 (rad/s) */
    float gyro_bias[3];
    /* 加速度计缩放因子 */
    float accel_scale[3];
    /* 陀螺仪缩放因子 */
    float gyro_scale[3];
    /* 安装旋转矩阵 (体坐标系 → 传感器坐标系) */
    float mount_rot[3][3];
    /* 温度补偿系数 */
    float temp_slope[6];  /* [ax,ay,az,gx,gy,gz] */
    float temp_intercept[6];
} qoo_imu_calib_t;

/** IMU 设备上下文 */
typedef struct {
    uint32_t            imu_id;
    qoo_imu_model_t   model;
    char                bus_path[64];  /* SPI/I2C 总线路径 */
    uint8_t             bus_type;     /* 0=SPI, 1=I2C */
    uint8_t             slave_addr;   /* I2C 地址 / SPI CS */
    int                 fd;           /* 设备文件描述符 */

    /* 配置 */
    uint16_t            sample_rate_hz;
    uint8_t             accel_range_g;
    uint8_t             gyro_range_dps;
    bool                fifo_enabled;
    bool                drdy_enabled;  /* 数据就绪中断 */

    /* 校准 */
    qoo_imu_calib_t   calib;
    bool                calibrated;

    /* 统计 */
    uint64_t            sample_count;
    uint64_t            error_count;
    uint64_t            drdy_count;

    /* 线程 */
    bool                running;
    pthread_t           read_thread;

    /* 回调 */
    void (*data_callback)(uint32_t imu_id,
                         const qoo_imu_data_t *data,
                         void *user_ctx);
    void *user_ctx;
} qoo_imu_ctx_t;

static qoo_imu_ctx_t g_imus[IMU_MAX_DEVICES];
static uint32_t g_imu_count = 0;

/*===========================================================================
 * 内部函数 (寄存器读取/写入，按型号分发)
 *===========================================================================*/

/** 写入单个寄存器 (SPI/I2C 通用) */
static qoo_error_t imu_write_reg(qoo_imu_ctx_t *ctx,
                                   uint8_t reg, uint8_t val)
{
    /* 实际实现:
     *   SPI: 传输 2 字节 [reg & 0x7F, val]
     *   I2C: smbus_write_byte_data(fd, reg, val)
     */
    (void)ctx; (void)reg; (void)val;
    return QOO_OK;
}

/** 读取单个寄存器 */
static qoo_error_t imu_read_reg(qoo_imu_ctx_t *ctx,
                                  uint8_t reg, uint8_t *val)
{
    (void)ctx; (void)reg; (void)val;
    return QOO_OK;
}

/** 突发读取 (FIFO 读取) */
static qoo_error_t imu_burst_read(qoo_imu_ctx_t *ctx,
                                    uint8_t reg, uint8_t *buf,
                                    size_t len)
{
    (void)ctx; (void)reg; (void)buf; (void)len;
    return QOO_OK;
}

/** BMI270 特定: 初始化 */
static qoo_error_t bmi270_init(qoo_imu_ctx_t *ctx)
{
    /* 1. 软复位 */
    imu_write_reg(ctx, 0x7E, 0xB6);  /* CMD 寄存器 */
    usleep(5000);

    /* 2. 检查芯片 ID */
    uint8_t chip_id;
    imu_read_reg(ctx, 0x00, &chip_id);  /* CHIP_ID 寄存器 */
    if (chip_id != 0x24) {  /* BMI270 CHIP_ID = 0x24 */
        fprintf(stderr, "[IMU %d] BMI270 芯片 ID 不匹配: 0x%02X\n",
                ctx->imu_id, chip_id);
        return QOO_ERROR_NOT_SUPPORTED;
    }

    /* 3. 配置加速度计 (ACC_CONF: 0x40) */
    /*    输出速率: 200Hz (ODR=0x0B) */
    imu_write_reg(ctx, 0x40, 0x0B);  /* ACC_CONF */

    /* 4. 配置陀螺仪 (GYR_CONF: 0x42) */
    imu_write_reg(ctx, 0x42, 0x0B);  /* GYR_CONF */

    /* 5. 量程: ACC_RANGE (0x41), GYR_RANGE (0x43) */
    /*    ±8g: 0x08, ±2000°/s: 0x00 */
    imu_write_reg(ctx, 0x41, 0x08);
    imu_write_reg(ctx, 0x43, 0x00);

    /* 6. 启用 FIFO (FIFO_CONFIG_1: 0x48) */
    if (ctx->fifo_enabled) {
        imu_write_reg(ctx, 0x48, 0x80);  /* FIFO_EN = 1 */
    }

    /* 7. 启用传感器 (PWR_CTRL: 0x7D) */
    imu_write_reg(ctx, 0x7D, 0x0E);  /* ACC_EN=1, GYR_EN=1, TEMP_EN=1 */

    printf("[IMU %d] BMI270 初始化完成 (200Hz, ±8g, ±2000°/s)\n",
           ctx->imu_id);
    return QOO_OK;
}

/** ICM-42688 特定: 初始化 */
static qoo_error_t icm42688_init(qoo_imu_ctx_t *ctx)
{
    /* 1. 软复位 */
    imu_write_reg(ctx, 0x06, 0x01);  /* DEVICE_CONFIG, SOFT_RESET */
    usleep(5000);

    /* 2. 检查 WHO_AM_I */
    uint8_t who_am_i;
    imu_read_reg(ctx, 0x75, &who_am_i);
    if (who_am_i != 0x67) {  /* ICM-42688 WHO_AM_I = 0x67 */
        fprintf(stderr, "[IMU %d] ICM-42688 WHO_AM_I 不匹配: 0x%02X\n",
                ctx->imu_id, who_am_i);
        return QOO_ERROR_NOT_SUPPORTED;
    }

    /* 3. 配置 PWR_MGMT0 (0x06): 启用 ACC + GYR */
    imu_write_reg(ctx, 0x06, 0x0F);  /* ACC_LP=0, ACC_EN=1, GYR_EN=1 */

    /* 4. 配置 ACC_CONFIG0 (0x21): ODR=200Hz */
    imu_write_reg(ctx, 0x21, 0x05);  /* ACC_ODR=200Hz */

    /* 5. 配置 GYR_CONFIG0 (0x23): ODR=200Hz */
    imu_write_reg(ctx, 0x23, 0x05);  /* GYR_ODR=200Hz */

    printf("[IMU %d] ICM-42688 初始化完成\n", ctx->imu_id);
    return QOO_OK;
}

/** 将原始数据转换为物理量 (通用) */
static void imu_raw_to_physical(qoo_imu_ctx_t *ctx,
                                    const qoo_imu_raw_data_t *raw,
                                    qoo_imu_data_t *data)
{
    /* 加速度: raw → m/s² */
    float accel_scale = 0;
    switch (ctx->accel_range_g) {
        case 2:  accel_scale = 2.0f  * 9.81f / 32768.0f; break;
        case 4:  accel_scale = 4.0f  * 9.81f / 32768.0f; break;
        case 8:  accel_scale = 8.0f  * 9.81f / 32768.0f; break;
        case 16: accel_scale = 16.0f * 9.81f / 32768.0f; break;
    }

    float ax = raw->accel_x * accel_scale;
    float ay = raw->accel_y * accel_scale;
    float az = raw->accel_z * accel_scale;

    /* 陀螺仪: raw → rad/s */
    float gyro_scale = 0;
    switch (ctx->gyro_range_dps) {
        case 125:  gyro_scale = 125.0f  * (3.14159265359f / 180.0f) / 32768.0f; break;
        case 250:  gyro_scale = 250.0f  * (3.14159265359f / 180.0f) / 32768.0f; break;
        case 500:  gyro_scale = 500.0f  * (3.14159265359f / 180.0f) / 32768.0f; break;
        case 1000: gyro_scale = 1000.0f * (3.14159265359f / 180.0f) / 32768.0f; break;
        case 2000: gyro_scale = 2000.0f * (3.14159265359f / 180.0f) / 32768.0f; break;
    }

    float gx = raw->gyro_x * gyro_scale;
    float gy = raw->gyro_y * gyro_scale;
    float gz = raw->gyro_z * gyro_scale;

    /* 应用校准 (零偏补偿) */
    if (ctx->calibrated) {
        ax = (ax - ctx->calib.accel_bias[0]) * ctx->calib.accel_scale[0];
        ay = (ay - ctx->calib.accel_bias[1]) * ctx->calib.accel_scale[1];
        az = (az - ctx->calib.accel_bias[2]) * ctx->calib.accel_scale[2];
        gx = (gx - ctx->calib.gyro_bias[0])  * ctx->calib.gyro_scale[0];
        gy = (gy - ctx->calib.gyro_bias[1])  * ctx->calib.gyro_scale[1];
        gz = (gz - ctx->calib.gyro_bias[2])  * ctx->calib.gyro_scale[2];
    }

    /* 应用安装旋转矩阵 */
    data->accel[0] = ctx->calib.mount_rot[0][0] * ax + ctx->calib.mount_rot[0][1] * ay + ctx->calib.mount_rot[0][2] * az;
    data->accel[1] = ctx->calib.mount_rot[1][0] * ax + ctx->calib.mount_rot[1][1] * ay + ctx->calib.mount_rot[1][2] * az;
    data->accel[2] = ctx->calib.mount_rot[2][0] * ax + ctx->calib.mount_rot[2][1] * ay + ctx->calib.mount_rot[2][2] * az;

    data->gyro[0] = ctx->calib.mount_rot[0][0] * gx + ctx->calib.mount_rot[0][1] * gy + ctx->calib.mount_rot[0][2] * gz;
    data->gyro[1] = ctx->calib.mount_rot[1][0] * gx + ctx->calib.mount_rot[1][1] * gy + ctx->calib.mount_rot[1][2] * gz;
    data->gyro[2] = ctx->calib.mount_rot[2][0] * gx + ctx->calib.mount_rot[2][1] * gy + ctx->calib.mount_rot[2][2] * gz;

    /* 温度: raw → °C (型号相关) */
    if (ctx->model == IMU_MODEL_BMI270) {
        data->temperature = raw->temp * 0.01f + 23.0f;  /* BMI270: 0.01°C/LSB */
    } else if (ctx->model == IMU_MODEL_ICM42688) {
        data->temperature = raw->temp * 0.01f + 25.0f;  /* ICM-42688 */
    }

    data->timestamp_ns = raw->timestamp_ns;
}

/*===========================================================================
 * 数据读取线程
 *===========================================================================*/

static void *imu_read_thread(void *arg)
{
    qoo_imu_ctx_t *ctx = (qoo_imu_ctx_t *)arg;

    /* 设置实时优先级 */
    struct sched_param sp;
    sp.sched_priority = IMU_THREAD_PRIORITY;
    pthread_setschedparam(pthread_self(), SCHED_FIFO, &sp);

    printf("[IMU %d] 读取线程启动 (优先级: %d)\n",
           ctx->imu_id, IMU_THREAD_PRIORITY);

    qoo_imu_raw_data_t raw;
    qoo_imu_data_t    phy;
    struct timespec period;

    clock_gettime(CLOCK_MONOTONIC, &period);
    uint64_t period_ns = 1000000000ULL / ctx->sample_rate_hz;  /* ns */

    while (ctx->running) {
        /* 1. 读取数据 (从 FIFO 或数据寄存器) */
        if (ctx->fifo_enabled) {
            uint8_t fifo_buf[IMU_FIFO_SIZE];
            uint16_t fifo_len;
            /* 读取 FIFO 长度 */
            /* imu_burst_read(ctx, FIFO_DATA_REG, fifo_buf, fifo_len); */
            /* 解析 FIFO (型号相关) */
            /* 每个样本: 12 字节 (ACC X/Y/Z + GYR X/Y/Z, 各 2B) */
        } else {
            /* 直接读取数据寄存器 */
            imu_read_reg(ctx, 0x0C, (uint8_t *)&raw.accel_x);  /* ACC_X LSB */
            /* ... 读取 12 个字节 ... */
            raw.timestamp_ns = qoo_hal_time_now();
        }

        ctx->sample_count++;

        /* 2. 转换为物理量 */
        if (ctx->sample_count > 0) {  /* 有数据 */
            imu_raw_to_physical(ctx, &raw, &phy);

            /* 3. 回调 */
            if (ctx->data_callback) {
                ctx->data_callback(ctx->imu_id, &phy, ctx->user_ctx);
            }
        }

        /* 4. 周期性睡眠 */
        period.tv_nsec += period_ns;
        if (period.tv_nsec >= 1000000000) {
            period.tv_nsec -= 1000000000;
            period.tv_sec++;
        }
        clock_nanosleep(CLOCK_MONOTONIC, TIMER_ABSTIME, &period, NULL);
    }

    printf("[IMU %d] 读取线程退出 (样本数: %lu)\n",
           ctx->imu_id, ctx->sample_count);
    return NULL;
}

/*===========================================================================
 * 公共接口
 *===========================================================================*/

/** 枚举 IMU 设备 (通过 sysfs 或设备树) */
uint32_t qoo_imu_enumerate(void)
{
    g_imu_count = 0;

    /* 扫描 SPI 总线 */
    for (int i = 0; i < IMU_MAX_DEVICES; i++) {
        char path[64];
        snprintf(path, sizeof(path), "/dev/spidev0.%d", i);
        if (access(path, R_OK | W_OK) == 0) {
            g_imus[g_imu_count].imu_id   = g_imu_count;
            g_imus[g_imu_count].fd       = -1;
            g_imus[g_imu_count].bus_type = 0;  /* SPI */
            snprintf(g_imus[g_imu_count].bus_path,
                     sizeof(g_imus[g_imu_count].bus_path),
                     "%s", path);
            g_imu_count++;
        }
    }

    /* 扫描 I2C 总线 */
    for (int i = 0; i < IMU_MAX_DEVICES; i++) {
        char path[64];
        snprintf(path, sizeof(path), "/dev/i2c-%d", i);
        if (access(path, R_OK | W_OK) == 0) {
            /* 探测常见 I2C 地址 */
            int fd = open(path, O_RDWR);
            if (fd >= 0) {
                /* 尝试读取 WHO_AM_I 寄存器 (不同型号地址不同) */
                /* 简化: 假设设备存在 */
                g_imus[g_imu_count].imu_id   = g_imu_count;
                g_imus[g_imu_count].fd       = -1;
                g_imus[g_imu_count].bus_type = 1;  /* I2C */
                snprintf(g_imus[g_imu_count].bus_path,
                         sizeof(g_imus[g_imu_count].bus_path),
                         "%s", path);
                g_imu_count++;
                close(fd);
            }
        }
    }

    printf("[IMU] 枚举到 %u 个 IMU 设备\n", g_imu_count);
    return g_imu_count;
}

/** 打开并初始化 IMU */
qoo_error_t qoo_imu_open(uint32_t imu_id, qoo_imu_model_t model)
{
    if (imu_id >= g_imu_count) return QOO_ERROR_NOT_FOUND;
    qoo_imu_ctx_t *ctx = &g_imus[imu_id];

    /* 1. 打开总线 */
    if (ctx->bus_type == 0) {
        /* SPI */
        ctx->fd = open(ctx->bus_path, O_RDWR, 0);
    } else {
        /* I2C */
        ctx->fd = open(ctx->bus_path, O_RDWR, 0);
    }
    if (ctx->fd < 0) {
        perror("[IMU] 打开总线失败");
        return QOO_ERROR_IO;
    }

    /* 2. 配置参数 */
    ctx->model           = model;
    ctx->sample_rate_hz  = IMU_SAMPLE_RATE_HZ;
    ctx->accel_range_g   = IMU_DEFAULT_RANGE_G;
    ctx->gyro_range_dps  = IMU_DEFAULT_RANGE_DPS;
    ctx->fifo_enabled    = true;
    ctx->drdy_enabled    = false;
    ctx->calibrated      = false;

    /* 3. 初始化安装旋转矩阵 (单位矩阵 = 传感器与身体坐标系对齐) */
    for (int i = 0; i < 3; i++) {
        for (int j = 0; j < 3; j++) {
            ctx->calib.mount_rot[i][j] = (i == j) ? 1.0f : 0.0f;
        }
    }

    /* 4. 型号特定初始化 */
    qoo_error_t err = QOO_OK;
    switch (model) {
        case IMU_MODEL_BMI270:
            err = bmi270_init(ctx);
            break;
        case IMU_MODEL_ICM42688:
            err = icm42688_init(ctx);
            break;
        default:
            fprintf(stderr, "[IMU %d] 未支持的型号: %d\n", imu_id, model);
            err = QOO_ERROR_NOT_SUPPORTED;
            break;
    }

    if (err != QOO_OK) {
        close(ctx->fd);
        ctx->fd = -1;
        return err;
    }

    printf("[IMU %d] 打开成功: 型号=%s, %u Hz\n",
           imu_id, imu_model_names[model], ctx->sample_rate_hz);
    return QOO_OK;
}

/** 注册数据回调 */
qoo_error_t qoo_imu_register_callback(uint32_t imu_id,
    void (*callback)(uint32_t, const qoo_imu_data_t *, void *),
    void *user_ctx)
{
    if (imu_id >= g_imu_count) return QOO_ERROR_NOT_FOUND;
    g_imus[imu_id].data_callback = callback;
    g_imus[imu_id].user_ctx      = user_ctx;
    return QOO_OK;
}

/** 启动数据读取 */
qoo_error_t qoo_imu_start(uint32_t imu_id)
{
    if (imu_id >= g_imu_count) return QOO_ERROR_NOT_FOUND;
    qoo_imu_ctx_t *ctx = &g_imus[imu_id];

    if (ctx->running) return QOO_OK;

    ctx->running = true;
    pthread_create(&ctx->read_thread, NULL, imu_read_thread, ctx);
    pthread_detach(ctx->read_thread);

    printf("[IMU %d] 开始数据读取\n", imu_id);
    return QOO_OK;
}

/** 停止数据读取 */
qoo_error_t qoo_imu_stop(uint32_t imu_id)
{
    if (imu_id >= g_imu_count) return QOO_ERROR_NOT_FOUND;
    qoo_imu_ctx_t *ctx = &g_imus[imu_id];

    ctx->running = false;
    usleep(100000);

    printf("[IMU %d] 停止数据读取 (样本数: %lu)\n",
           imu_id, ctx->sample_count);
    return QOO_OK;
}

/** 校准 IMU (简易版本: 静止 5 秒采集零偏) */
qoo_error_t qoo_imu_calibrate(uint32_t imu_id)
{
    if (imu_id >= g_imu_count) return QOO_ERROR_NOT_FOUND;
    qoo_imu_ctx_t *ctx = &g_imus[imu_id];

    printf("[IMU %d] 开始校准 (请保持静止 5 秒)...\n", imu_id);

    /* 实际: 读取 N 个样本，计算平均值作为零偏 */
    float accel_sum[3] = {0};
    float gyro_sum[3]  = {0};
    uint32_t n = 0;

    /* 此处为示意，实际应从读取线程获取数据 */
    for (int i = 0; i < 1000; i++) {
        /* accel_sum[0] += ... */
        /* gyro_sum[0]  += ... */
        n++;
        usleep(1000);
    }

    if (n > 0) {
        ctx->calib.accel_bias[0] = accel_sum[0] / n;
        ctx->calib.accel_bias[1] = accel_sum[1] / n;
        ctx->calib.accel_bias[2] = accel_sum[2] / n;
        ctx->calib.gyro_bias[0]  = gyro_sum[0] / n;
        ctx->calib.gyro_bias[1]  = gyro_sum[1] / n;
        ctx->calib.gyro_bias[2]  = gyro_sum[2] / n;
        ctx->calibrated = true;

        printf("[IMU %d] 校准完成:\n", imu_id);
        printf("  ACC 零偏: %.4f, %.4f, %.4f m/s²\n",
               ctx->calib.accel_bias[0], ctx->calib.accel_bias[1], ctx->calib.accel_bias[2]);
        printf("  GYRO 零偏: %.4f, %.4f, %.4f rad/s\n",
               ctx->calib.gyro_bias[0], ctx->calib.gyro_bias[1], ctx->calib.gyro_bias[2]);
    }

    return QOO_OK;
}

/** 设置安装旋转矩阵 */
qoo_error_t qoo_imu_set_mount_rotation(uint32_t imu_id,
                                                     const float rot[3][3])
{
    if (imu_id >= g_imu_count) return QOO_ERROR_NOT_FOUND;
    qoo_imu_ctx_t *ctx = &g_imus[imu_id];

    memcpy(ctx->calib.mount_rot, rot, sizeof(ctx->calib.mount_rot));
    printf("[IMU %d] 安装旋转矩阵已设置\n", imu_id);
    return QOO_OK;
}

/** 关闭 IMU */
qoo_error_t qoo_imu_close(uint32_t imu_id)
{
    if (imu_id >= g_imu_count) return QOO_ERROR_NOT_FOUND;
    qoo_imu_ctx_t *ctx = &g_imus[imu_id];

    qoo_imu_stop(imu_id);

    if (ctx->fd >= 0) {
        close(ctx->fd);
        ctx->fd = -1;
    }

    printf("[IMU %d] 已关闭\n", imu_id);
    return QOO_OK;
}

/** 获取 IMU 统计 */
void qoo_imu_get_stats(uint32_t imu_id,
                             uint64_t *sample_count, uint64_t *error_count,
                             uint64_t *drdy_count)
{
    if (imu_id >= g_imu_count) return;
    qoo_imu_ctx_t *ctx = &g_imus[imu_id];
    *sample_count = ctx->sample_count;
    *error_count  = ctx->error_count;
    *drdy_count  = ctx->drdy_count;
}

/*===========================================================================
 * 使用示例
 *===========================================================================*/

#if 0

static void my_imu_callback(uint32_t imu_id,
                             const qoo_imu_data_t *data,
                             void *user_ctx)
{
    (void)user_ctx;
    if ((data->timestamp_ns / 1000000000ULL) % 1 == 0) {  /* 每秒打印 */
        printf("[APP] IMU %d: ACC=(%.3f, %.3f, %.3f) m/s², "
               "GYRO=(%.3f, %.3f, %.3f) rad/s, T=%.1f °C\n",
               imu_id,
               data->accel[0], data->accel[1], data->accel[2],
               data->gyro[0],  data->gyro[1],  data->gyro[2],
               data->temperature);
    }

    /* 此处可:
     *  - 发送数据到 AHRS/EKF 姿态估计
     *  - 发布到 ROS2 Topic (sensor_msgs/Imu)
     *  - 存储到日志文件
     */
}

int main(void)
{
    /* 1. 枚举设备 */
    uint32_t num = qoo_imu_enumerate();
    if (num == 0) {
        fprintf(stderr, "未找到 IMU 设备 (检查 SPI/I2C 总线及设备树)\n");
        return 1;
    }

    /* 2. 打开 IMU 0 (BMI270) */
    qoo_error_t err = qoo_imu_open(0, IMU_MODEL_BMI270);
    if (err != QOO_OK) {
        fprintf(stderr, "打开 IMU 0 失败: %d\n", err);
        return 1;
    }

    /* 3. 校准 (首次使用或环境变化时) */
    qoo_imu_calibrate(0);

    /* 4. 注册回调 */
    qoo_imu_register_callback(0, my_imu_callback, NULL);

    /* 5. 启动数据读取 */
    qoo_imu_start(0);

    /* 6. 主循环 */
    sleep(60);

    /* 7. 停止并关闭 */
    qoo_imu_close(0);

    return 0;
}

#endif
