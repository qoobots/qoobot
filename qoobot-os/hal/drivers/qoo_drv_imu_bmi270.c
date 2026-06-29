/**
 * @file qoo_drv_imu_bmi270.c
 * @brief Bosch BMI270 IMU 驱动参考实现
 *
 * 接口: SPI
 * 数据: 6轴 (3轴加速度计 + 3轴陀螺仪)
 * 采样率: 最高 1.6kHz
 */

#include "qoo_drv_sensor_base.h"
#include "../hal/qoo_hal_time.h"
#include <string.h>

/*===========================================================================
 * BMI270 寄存器定义
 *===========================================================================*/

#define BMI270_REG_CHIP_ID      0x00
#define BMI270_REG_ERR_REG      0x02
#define BMI270_REG_STATUS       0x03
#define BMI270_REG_ACC_DATA     0x0C    /* 加速度数据起始 (6 bytes) */
#define BMI270_REG_GYR_DATA     0x12    /* 陀螺仪数据起始 (6 bytes) */
#define BMI270_REG_ACC_CONF     0x40
#define BMI270_REG_GYR_CONF     0x42
#define BMI270_REG_PWR_CTRL     0x7D
#define BMI270_REG_CMD          0x7E

#define BMI270_CHIP_ID          0x24

/* 加速度计量程 */
#define BMI270_ACC_RANGE_2G     0x00
#define BMI270_ACC_RANGE_4G     0x01
#define BMI270_ACC_RANGE_8G     0x02
#define BMI270_ACC_RANGE_16G    0x03

/* 陀螺仪量程 */
#define BMI270_GYR_RANGE_2000   0x00
#define BMI270_GYR_RANGE_1000   0x01
#define BMI270_GYR_RANGE_500    0x02
#define BMI270_GYR_RANGE_250    0x03
#define BMI270_GYR_RANGE_125    0x04

/* 电源模式 */
#define BMI270_PWR_ACC_SUSPEND  0x00
#define BMI270_PWR_ACC_LOW      0x01
#define BMI270_PWR_ACC_NORMAL   0x02
#define BMI270_PWR_ACC_PERF     0x03

/*===========================================================================
 * 驱动上下文
 *===========================================================================*/

/** 加速度计配置 */
typedef struct {
    uint8_t range;          /**< 量程 */
    uint16_t odr;           /**< 输出数据速率 (Hz) */
    uint8_t bw;             /**< 滤波器带宽 */
} bmi270_acc_config_t;

/** 陀螺仪配置 */
typedef struct {
    uint8_t range;          /**< 量程 */
    uint16_t odr;           /**< 输出数据速率 (Hz) */
    uint8_t bw;             /**< 滤波器带宽 */
} bmi270_gyr_config_t;

/** BMI270 驱动上下文 */
typedef struct {
    uint32_t spi_bus;           /**< SPI 总线号 */
    uint32_t spi_cs;            /**< SPI 片选 */
    bmi270_acc_config_t acc_cfg;
    bmi270_gyr_config_t gyr_cfg;
    float acc_scale;            /**< 加速度转换系数 */
    float gyr_scale;            /**< 陀螺仪转换系数 */
    qoo_hw_component_t info;
} bmi270_ctx_t;

/*===========================================================================
 * 内部辅助函数
 *===========================================================================*/

/** 通过 SPI 读寄存器 */
static qoo_error_t bmi270_reg_read(bmi270_ctx_t *ctx, uint8_t reg,
    uint8_t *data, uint32_t len)
{
    /* SPI 读: 第一个字节 = reg | 0x80 (读标志) */
    uint8_t tx_buf[128] = { reg | 0x80 };
    /* 实际应调用 HAL SPI 接口 */
    /* qoo_hal_spi_transfer(ctx->spi_bus, ctx->spi_cs, tx_buf, data, len + 1); */
    (void)ctx; (void)reg; (void)data; (void)len;
    return QOO_OK;
}

/** 通过 SPI 写寄存器 */
static qoo_error_t bmi270_reg_write(bmi270_ctx_t *ctx, uint8_t reg,
    const uint8_t *data, uint32_t len)
{
    uint8_t tx_buf[128];
    tx_buf[0] = reg & 0x7F; /* 写标志 */
    memcpy(tx_buf + 1, data, len);
    /* qoo_hal_spi_transfer(ctx->spi_bus, ctx->spi_cs, tx_buf, NULL, len + 1); */
    (void)ctx;
    return QOO_OK;
}

/** 计算加速度量程对应的转换系数 */
static float bmi270_acc_scale_from_range(uint8_t range)
{
    switch (range) {
        case BMI270_ACC_RANGE_2G:  return 2.0f / 32768.0f * 9.80665f; /* m/s² */
        case BMI270_ACC_RANGE_4G:  return 4.0f / 32768.0f * 9.80665f;
        case BMI270_ACC_RANGE_8G:  return 8.0f / 32768.0f * 9.80665f;
        case BMI270_ACC_RANGE_16G: return 16.0f / 32768.0f * 9.80665f;
        default: return 2.0f / 32768.0f * 9.80665f;
    }
}

/** 计算陀螺仪量程对应的转换系数 */
static float bmi270_gyr_scale_from_range(uint8_t range)
{
    switch (range) {
        case BMI270_GYR_RANGE_2000: return 2000.0f / 32768.0f * 0.0174533f; /* rad/s */
        case BMI270_GYR_RANGE_1000: return 1000.0f / 32768.0f * 0.0174533f;
        case BMI270_GYR_RANGE_500:  return 500.0f / 32768.0f * 0.0174533f;
        case BMI270_GYR_RANGE_250:  return 250.0f / 32768.0f * 0.0174533f;
        case BMI270_GYR_RANGE_125:  return 125.0f / 32768.0f * 0.0174533f;
        default: return 2000.0f / 32768.0f * 0.0174533f;
    }
}

/*===========================================================================
 * 驱动接口实现
 *===========================================================================*/

static qoo_error_t bmi270_init(void *drv_ctx)
{
    bmi270_ctx_t *ctx = (bmi270_ctx_t *)drv_ctx;
    uint8_t chip_id = 0;

    /* 1. 读取芯片 ID 验证 */
    bmi270_reg_read(ctx, BMI270_REG_CHIP_ID, &chip_id, 1);
    if (chip_id != BMI270_CHIP_ID) {
        return QOO_ERROR_HW_FAULT;
    }

    /* 2. 执行软复位 */
    uint8_t cmd = 0xB6;
    bmi270_reg_write(ctx, BMI270_REG_CMD, &cmd, 1);

    /* 3. 配置加速度计 */
    uint8_t acc_conf = (ctx->acc_cfg.bw << 4) | (ctx->acc_cfg.odr > 100 ? 0x0C : 0x0A);
    bmi270_reg_write(ctx, BMI270_REG_ACC_CONF, &acc_conf, 1);

    /* 4. 配置陀螺仪 */
    uint8_t gyr_conf = (ctx->gyr_cfg.bw << 4) | (ctx->gyr_cfg.odr > 400 ? 0x0D : 0x0B);
    bmi270_reg_write(ctx, BMI270_REG_GYR_CONF, &gyr_conf, 1);

    /* 5. 设置电源模式为性能模式 */
    uint8_t pwr = BMI270_PWR_ACC_PERF;
    bmi270_reg_write(ctx, BMI270_REG_PWR_CTRL, &pwr, 1);

    /* 6. 计算转换系数 */
    ctx->acc_scale = bmi270_acc_scale_from_range(ctx->acc_cfg.range);
    ctx->gyr_scale = bmi270_gyr_scale_from_range(ctx->gyr_cfg.range);

    return QOO_OK;
}

static qoo_error_t bmi270_deinit(void *drv_ctx)
{
    bmi270_ctx_t *ctx = (bmi270_ctx_t *)drv_ctx;
    /* 挂起传感器 */
    uint8_t pwr = BMI270_PWR_ACC_SUSPEND;
    bmi270_reg_write(ctx, BMI270_REG_PWR_CTRL, &pwr, 1);
    return QOO_OK;
}

static qoo_error_t bmi270_start(void *drv_ctx)
{
    /* 已在 init 中完成配置, 无需额外操作 */
    (void)drv_ctx;
    return QOO_OK;
}

static qoo_error_t bmi270_stop(void *drv_ctx)
{
    return bmi270_deinit(drv_ctx);
}

static qoo_error_t bmi270_read(void *drv_ctx, void *data, uint32_t timeout_ms)
{
    bmi270_ctx_t *ctx = (bmi270_ctx_t *)drv_ctx;
    qoo_imu_data_t *imu = (qoo_imu_data_t *)data;
    uint8_t raw[12];
    int16_t acc_x, acc_y, acc_z;
    int16_t gyr_x, gyr_y, gyr_z;

    /* 读取加速度 + 陀螺仪原始数据 (12 bytes) */
    qoo_error_t err = bmi270_reg_read(ctx, BMI270_REG_ACC_DATA, raw, 12);
    if (err != QOO_OK) return err;

    /* 解析加速度计 (小端序) */
    acc_x = (int16_t)(raw[0] | (raw[1] << 8));
    acc_y = (int16_t)(raw[2] | (raw[3] << 8));
    acc_z = (int16_t)(raw[4] | (raw[5] << 8));

    /* 解析陀螺仪 */
    gyr_x = (int16_t)(raw[6] | (raw[7] << 8));
    gyr_y = (int16_t)(raw[8] | (raw[9] << 8));
    gyr_z = (int16_t)(raw[10] | (raw[11] << 8));

    /* 填充 IMU 数据结构 */
    imu->header.timestamp = qoo_hal_time_now();
    imu->header.sequence++;
    imu->header.flags = 0x01; /* 有效 */

    imu->accel.x = acc_x * ctx->acc_scale;
    imu->accel.y = acc_y * ctx->acc_scale;
    imu->accel.z = acc_z * ctx->acc_scale;

    imu->gyro.x = gyr_x * ctx->gyr_scale;
    imu->gyro.y = gyr_y * ctx->gyr_scale;
    imu->gyro.z = gyr_z * ctx->gyr_scale;

    /* 无磁场数据 (6轴) */
    imu->mag.x = imu->mag.y = imu->mag.z = 0.0f;
    imu->temperature = 25.0f; /* 可读取内部温度传感器 */

    (void)timeout_ms;
    return QOO_OK;
}

static qoo_error_t bmi270_self_test(void *drv_ctx, bool *healthy)
{
    /* 读取错误寄存器 */
    bmi270_ctx_t *ctx = (bmi270_ctx_t *)drv_ctx;
    uint8_t err_reg;
    bmi270_reg_read(ctx, BMI270_REG_ERR_REG, &err_reg, 1);
    *healthy = (err_reg == 0);
    return QOO_OK;
}

static qoo_error_t bmi270_get_info(void *drv_ctx, qoo_hw_component_t *info)
{
    bmi270_ctx_t *ctx = (bmi270_ctx_t *)drv_ctx;
    memcpy(info, &ctx->info, sizeof(qoo_hw_component_t));
    return QOO_OK;
}

/*===========================================================================
 * 驱动虚表
 *===========================================================================*/

static const qoo_drv_sensor_ops_t bmi270_ops = {
    .name       = "BMI270",
    .init       = bmi270_init,
    .deinit     = bmi270_deinit,
    .start      = bmi270_start,
    .stop       = bmi270_stop,
    .read       = bmi270_read,
    .get_config = NULL,
    .set_config = NULL,
    .self_test  = bmi270_self_test,
    .get_info   = bmi270_get_info,
};

/*===========================================================================
 * 驱动工厂
 *===========================================================================*/

/**
 * @brief 创建 BMI270 驱动实例
 * @param spi_bus SPI 总线号
 * @param spi_cs  SPI 片选
 * @param acc_odr 加速度计采样率 (Hz)
 * @param gyr_odr 陀螺仪采样率 (Hz)
 * @return 驱动实例, NULL 表示失败
 */
qoo_drv_sensor_t* bmi270_driver_create(uint32_t spi_bus, uint32_t spi_cs,
    uint16_t acc_odr, uint16_t gyr_odr)
{
    static bmi270_ctx_t ctx;
    static qoo_drv_sensor_t driver;

    memset(&ctx, 0, sizeof(ctx));
    ctx.spi_bus = spi_bus;
    ctx.spi_cs = spi_cs;

    /* 默认配置 */
    ctx.acc_cfg.range = BMI270_ACC_RANGE_8G;
    ctx.acc_cfg.odr = acc_odr;
    ctx.acc_cfg.bw = 2; /* Normal mode */

    ctx.gyr_cfg.range = BMI270_GYR_RANGE_2000;
    ctx.gyr_cfg.odr = gyr_odr;
    ctx.gyr_cfg.bw = 2;

    /* 硬件信息 */
    ctx.info.type = QOO_HW_TYPE_SENSOR_IMU;
    strncpy(ctx.info.name, "IMU_0", sizeof(ctx.info.name));
    strncpy(ctx.info.vendor, "Bosch", sizeof(ctx.info.vendor));
    strncpy(ctx.info.model, "BMI270", sizeof(ctx.info.model));
    strncpy(ctx.info.fw_version, "1.0", sizeof(ctx.info.fw_version));

    driver.ops = &bmi270_ops;
    driver.ctx = &ctx;

    return &driver;
}
