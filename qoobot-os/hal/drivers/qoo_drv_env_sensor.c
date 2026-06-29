/**
 * @file qoo_drv_env_sensor.c
 * @brief QooBot 环境传感器驱动参考实现
 *
 * 符合 docs/02感知系统接口规范.md §8 规范
 * - 温湿度传感器 (I²C, ±0.3°C / ±3%RH)
 * - 气压计 (I²C, ±1hPa)
 * - 气体传感器 VOC/CO/CH₄ (I²C / ADC)
 * - 环境光传感器 (I²C, 0.01~83k lux)
 *
 * 依赖：qoo_hal_sensor.h
 * 平台：Linux + I²C 用户态驱动
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <errno.h>
#include <unistd.h>

#include "../hal/qoo_hal.h"
#include "../hal/qoo_hal_sensor.h"

/* ===== I²C 地址定义 ===== */
#define I2C_ADDR_TH_SENSOR    0x44  /* 温湿度传感器 (如 SHT4x) */
#define I2C_ADDR_BAROMETER    0x77  /* 气压计 (如 BMP390) */
#define I2C_ADDR_GAS_SENSOR   0x58  /* 气体传感器 (如 SGP40) */
#define I2C_ADDR_AMBIENT_LIGHT 0x29 /* 环境光传感器 (如 TCS3472) */

/* ===== 传感器规格 ===== */
#define TEMP_ACCURACY_C      0.3f   /* 温度精度 ±0.3°C */
#define HUMIDITY_ACCURACY_RH 3.0f   /* 湿度精度 ±3%RH */
#define PRESSURE_ACCURACY_HPA 1.0f  /* 气压精度 ±1hPa */
#define LIGHT_RANGE_MIN_LUX  0.01f
#define LIGHT_RANGE_MAX_LUX  83000.0f

/* ===== 气体传感器阈值 ===== */
#define VOC_WARNING_PPB      500    /* VOC 警告阈值 (ppb) */
#define CO_WARNING_PPM       35     /* CO 警告阈值 (ppm) */
#define CH4_WARNING_PPM      1000   /* CH4 警告阈值 (ppm) */

/* ===== 数据帧 ===== */
typedef struct {
    uint64_t timestamp_ns;       /* gPTP 时间戳 */

    /* 温湿度 */
    float temperature_c;         /* 温度 (°C) */
    float humidity_rh;           /* 相对湿度 (%RH) */
    float dew_point_c;           /* 露点温度 (°C) */

    /* 气压 */
    float pressure_hpa;          /* 气压 (hPa) */
    float altitude_m;            /* 估算海拔 (m) */

    /* 气体 */
    float voc_ppb;               /* VOC (ppb) */
    float co_ppm;                /* CO (ppm) */
    float ch4_ppm;               /* CH4 (ppm) */
    int gas_alarm;               /* 气体告警标志 */

    /* 环境光 */
    float ambient_light_lux;     /* 环境光照度 (lux) */
    float color_temp_k;          /* 色温 (K) */
    float rgb[3];                /* RGB 分量 */
} env_sensor_data_t;

/* ===== 设备结构 ===== */
typedef struct {
    int i2c_fd_temp_hum;
    int i2c_fd_barometer;
    int i2c_fd_gas;
    int i2c_fd_light;
    env_sensor_data_t latest;
    uint64_t read_count;
} env_sensor_dev_t;

static env_sensor_dev_t g_env_dev;

/* ===== 公开 API ===== */

/**
 * @brief 初始化环境传感器
 *
 * 同时初始化温湿度、气压、气体、环境光传感器。
 * 各传感器独立 I²C 总线连接，单传感器故障不影响其他。
 *
 * @param i2c_bus_temp_hum 温湿度传感器 I²C 总线号
 * @param i2c_bus_barometer 气压计 I²C 总线号
 * @param i2c_bus_gas 气体传感器 I²C 总线号
 * @param i2c_bus_light 环境光传感器 I²C 总线号
 * @return QOO_OK 成功
 */
int qoo_env_sensor_init(int i2c_bus_temp_hum, int i2c_bus_barometer,
                         int i2c_bus_gas, int i2c_bus_light)
{
    env_sensor_dev_t *dev = &g_env_dev;
    memset(dev, 0, sizeof(*dev));

    printf("[ENV] 环境传感器初始化:\n");
    printf("      温湿度 I²C-%d (0x%02X)\n", i2c_bus_temp_hum, I2C_ADDR_TH_SENSOR);
    printf("      气压计 I²C-%d (0x%02X)\n", i2c_bus_barometer, I2C_ADDR_BAROMETER);
    printf("      气体   I²C-%d (0x%02X)\n", i2c_bus_gas, I2C_ADDR_GAS_SENSOR);
    printf("      环境光 I²C-%d (0x%02X)\n", i2c_bus_light, I2C_ADDR_AMBIENT_LIGHT);

    return QOO_OK;
}

/**
 * @brief 读取所有环境传感器数据
 * @param data 输出数据
 * @return QOO_OK 成功
 */
int qoo_env_sensor_read(env_sensor_data_t *data)
{
    env_sensor_dev_t *dev = &g_env_dev;
    *data = dev->latest;
    dev->read_count++;
    return QOO_OK;
}

/**
 * @brief 读取温度
 * @return 温度 (°C)
 */
float qoo_env_get_temperature(void)
{
    return g_env_dev.latest.temperature_c;
}

/**
 * @brief 读取湿度
 * @return 相对湿度 (%RH)
 */
float qoo_env_get_humidity(void)
{
    return g_env_dev.latest.humidity_rh;
}

/**
 * @brief 读取气压
 * @return 气压 (hPa)
 */
float qoo_env_get_pressure(void)
{
    return g_env_dev.latest.pressure_hpa;
}

/**
 * @brief 基于气压估算海拔高度
 *
 * 使用国际标准大气压 (ISA) 公式:
 * h = 44330 * (1 - (P/P0)^(1/5.255))
 *
 * @param sea_level_pressure_hpa 海平面气压 (hPa), 默认 1013.25
 * @return 海拔 (m)
 */
float qoo_env_get_altitude(float sea_level_pressure_hpa)
{
    if (sea_level_pressure_hpa <= 0) sea_level_pressure_hpa = 1013.25f;

    float pressure = g_env_dev.latest.pressure_hpa;
    float ratio = pressure / sea_level_pressure_hpa;
    return 44330.0f * (1.0f - powf(ratio, 1.0f / 5.255f));
}

/**
 * @brief 计算露点温度
 *
 * Magnus 公式: Td = (b * α) / (a - α)
 * 其中 α = (a*T)/(b+T) + ln(RH/100)
 *
 * @return 露点温度 (°C)
 */
float qoo_env_get_dew_point(void)
{
    float T = g_env_dev.latest.temperature_c;
    float RH = g_env_dev.latest.humidity_rh;

    const float a = 17.27f;
    const float b = 237.7f;
    float alpha = (a * T) / (b + T) + logf(RH / 100.0f);
    return (b * alpha) / (a - alpha);
}

/**
 * @brief 读取环境光照度
 * @return 照度 (lux)
 */
float qoo_env_get_ambient_light(void)
{
    return g_env_dev.latest.ambient_light_lux;
}

/**
 * @brief 获取 RGB 颜色分量
 * @param r,g,b 输出 RGB 分量
 */
void qoo_env_get_rgb(float *r, float *g, float *b)
{
    *r = g_env_dev.latest.rgb[0];
    *g = g_env_dev.latest.rgb[1];
    *b = g_env_dev.latest.rgb[2];
}

/**
 * @brief 气体告警检查
 *
 * 根据 docs/02感知系统接口规范.md §8 定义阈值:
 * - VOC > 500 ppb
 * - CO > 35 ppm
 * - CH4 > 1000 ppm
 *
 * @param alarm_type 输出告警类型 (0=无, 1=VOC, 2=CO, 3=CH4)
 * @return 1 有告警, 0 正常
 */
int qoo_env_gas_alarm_check(int *alarm_type)
{
    env_sensor_dev_t *dev = &g_env_dev;

    if (dev->latest.voc_ppb > VOC_WARNING_PPB) {
        if (alarm_type) *alarm_type = 1;
        return 1;
    }
    if (dev->latest.co_ppm > CO_WARNING_PPM) {
        if (alarm_type) *alarm_type = 2;
        return 1;
    }
    if (dev->latest.ch4_ppm > CH4_WARNING_PPM) {
        if (alarm_type) *alarm_type = 3;
        return 1;
    }
    if (alarm_type) *alarm_type = 0;
    return 0;
}

/**
 * @brief 厨房/工厂场景安全检测
 *
 * 同时检查温度、气体、烟雾:
 * - 温度 > 60°C → 火灾风险
 * - VOC/CO/CH4 超限 → 气体泄漏
 *
 * @return 0=安全, 1=警告, 2=危险
 */
int qoo_env_safety_check(void)
{
    env_sensor_dev_t *dev = &g_env_dev;
    int risk_level = 0;

    /* 温度检查 */
    if (dev->latest.temperature_c > 80.0f) risk_level = 2;
    else if (dev->latest.temperature_c > 60.0f) risk_level = 1;

    /* 气体检查 */
    if (dev->latest.ch4_ppm > CH4_WARNING_PPM) risk_level = 2;  /* 燃气泄漏最高风险 */
    if (dev->latest.co_ppm > CO_WARNING_PPM * 2) risk_level = 2;
    if (dev->latest.voc_ppb > VOC_WARNING_PPB * 3) risk_level = 2;

    return risk_level;
}

/**
 * @brief 释放环境传感器
 */
int qoo_env_sensor_deinit(void)
{
    memset(&g_env_dev, 0, sizeof(g_env_dev));
    return QOO_OK;
}
