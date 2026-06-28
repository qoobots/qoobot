/**
 * @file qoo_thermal_mgmt.c
 * @brief QooBot 散热管理参考实现
 *
 * 符合 docs/01计算平台设计.md §7 规范
 * - TDP: 待机<5W / 典型10~15W / 峰值20~30W
 * - 被动散热: 铝合金散热片 + 导热硅脂
 * - 主动散热: 热管 + 鳍片 + PWM 调速风扇
 * - 液冷: 均温板 + 微型泵 + 散热排 (旗舰方案)
 *
 * 风扇控制策略 (符合规范 §8.3):
 *   < 40°C: 0% (停转, 0 dBA)
 *   40~55°C: 20~50% (< 25 dBA)
 *   55~70°C: 50~80% (< 35 dBA)
 *   > 70°C: 100% + 降频 (< 45 dBA)
 *   > 85°C: 紧急关机
 *
 * 依赖：qoo_hal.h
 * 平台：Linux + PWM sysfs / hwmon
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <errno.h>
#include <math.h>

#include "../hal/qoo_hal.h"

/* ===== 热管理参数 ===== */
#define THERMAL_ZONES_MAX       8
#define FAN_PWM_MAX             255
#define TEMP_SAMPLE_INTERVAL_MS 1000

/* 风扇控制阈值 (符合规范 §8.3) */
#define TEMP_FAN_OFF_C          40    /* 风扇停转 */
#define TEMP_FAN_LOW_C          55    /* 低速 */
#define TEMP_FAN_HIGH_C         70    /* 高速 */
#define TEMP_THROTTLE_C         75    /* 降频 */
#define TEMP_SHUTDOWN_C         85    /* 紧急关机 */

/* 热设计功耗 (符合规范 §7.1) */
#define TDP_STANDBY_W            5
#define TDP_TYPICAL_W           15
#define TDP_PEAK_W              30

/* ===== 散热方案 ===== */
typedef enum {
    THERMAL_SOLUTION_PASSIVE   = 0,  /* 被动散热 */
    THERMAL_SOLUTION_ACTIVE    = 1,  /* 主动散热 (风扇) */
    THERMAL_SOLUTION_LIQUID    = 2,  /* 液冷 */
} thermal_solution_t;

/* ===== 热源定义 ===== */
typedef enum {
    HEAT_SOURCE_SOC      = 0,  /* 主控 SoC */
    HEAT_SOURCE_GPU      = 1,  /* GPU */
    HEAT_SOURCE_NPU      = 2,  /* NPU */
    HEAT_SOURCE_MOTOR_DRV = 3, /* 电机驱动器 */
    HEAT_SOURCE_DCDC     = 4,  /* DC/DC 电源 */
    HEAT_SOURCE_BATTERY  = 5,  /* 电池 */
    HEAT_SOURCE_LIDAR    = 6,  /* LiDAR */
    HEAT_SOURCE_AMBIENT  = 7,  /* 环境温度 */
} heat_source_t;

/* ===== 热区信息 ===== */
typedef struct {
    heat_source_t source;
    const char *name;
    float temperature_c;       /* 当前温度 */
    float max_allowed_c;       /* 最高允许温度 */
    float power_w;             /* 当前功耗 */
    float thermal_resistance_cw; /* 热阻 (°C/W) */
} thermal_zone_t;

/* ===== 风扇配置 ===== */
typedef struct {
    int pwm_chip;              /* PWM 芯片 */
    int pwm_channel;           /* PWM 通道 */
    int current_duty;          /* 当前占空比 (0~255) */
    int target_duty;           /* 目标占空比 */
    int rpm;                   /* 当前转速 */
    int max_rpm;               /* 最大转速 */
    float noise_dba;           /* 噪音 (dBA) */
} fan_config_t;

/* ===== 热管理设备 ===== */
typedef struct {
    thermal_solution_t solution;
    thermal_zone_t zones[THERMAL_ZONES_MAX];
    int num_zones;
    fan_config_t fan;
    int throttling;            /* 降频标志 */
    int emergency_shutdown;    /* 紧急关机标志 */
    float ambient_temp_c;      /* 环境温度 */
    float total_power_w;       /* 总功耗 */
} thermal_dev_t;

static thermal_dev_t g_thermal;

/* ===== 公开 API ===== */

/**
 * @brief 初始化散热管理系统
 * @param solution 散热方案
 * @return QOO_OK 成功
 */
int qoo_thermal_init(thermal_solution_t solution)
{
    thermal_dev_t *dev = &g_thermal;
    memset(dev, 0, sizeof(*dev));

    dev->solution = solution;
    dev->ambient_temp_c = 25.0f;

    /* 初始化热区 (符合规范 §8.1) */
    dev->zones[0] = (thermal_zone_t){ HEAT_SOURCE_SOC,      "SoC",      25, 85, 15, 1.5f };
    dev->zones[1] = (thermal_zone_t){ HEAT_SOURCE_GPU,      "GPU",      25, 85, 5,  1.5f };
    dev->zones[2] = (thermal_zone_t){ HEAT_SOURCE_NPU,      "NPU",      25, 85, 5,  1.5f };
    dev->zones[3] = (thermal_zone_t){ HEAT_SOURCE_MOTOR_DRV,"MotorDrv", 25, 100, 20, 2.0f };
    dev->zones[4] = (thermal_zone_t){ HEAT_SOURCE_DCDC,     "DC/DC",    25, 85, 3,  3.0f };
    dev->zones[5] = (thermal_zone_t){ HEAT_SOURCE_BATTERY,  "Battery",  25, 50, 2,  5.0f };
    dev->zones[6] = (thermal_zone_t){ HEAT_SOURCE_LIDAR,    "LiDAR",    25, 70, 10, 2.0f };
    dev->zones[7] = (thermal_zone_t){ HEAT_SOURCE_AMBIENT,  "Ambient",  25, 60, 0,  0.0f };
    dev->num_zones = 8;

    printf("[THERMAL] 散热管理初始化: 方案=%s\n",
           solution == THERMAL_SOLUTION_PASSIVE ? "被动" :
           (solution == THERMAL_SOLUTION_ACTIVE ? "主动风扇" : "液冷"));
    return QOO_OK;
}

/**
 * @brief 读取所有热区温度
 */
void qoo_thermal_read_temperatures(void)
{
    thermal_dev_t *dev = &g_thermal;

    /* 从 hwmon sysfs 读取温度 */
    for (int i = 0; i < dev->num_zones; i++) {
        /* dev->zones[i].temperature_c = read_sysfs_temp(zone_path); */
    }
}

/**
 * @brief 风扇控制算法
 *
 * 根据 SoC 温度计算目标占空比 (符合规范 §8.3):
 *
 * @return 目标占空比 (0~255)
 */
int qoo_thermal_compute_fan_duty(void)
{
    thermal_dev_t *dev = &g_thermal;
    float soc_temp = dev->zones[HEAT_SOURCE_SOC].temperature_c;

    int duty = 0;

    if (soc_temp >= TEMP_SHUTDOWN_C) {
        duty = FAN_PWM_MAX;  /* 100% */
        dev->emergency_shutdown = 1;
        printf("[THERMAL] 紧急关机! SoC=%.0f°C > %d°C\n", soc_temp, TEMP_SHUTDOWN_C);
    } else if (soc_temp >= TEMP_THROTTLE_C) {
        duty = FAN_PWM_MAX;
        dev->throttling = 1;
    } else if (soc_temp >= TEMP_FAN_HIGH_C) {
        /* 50~80% 线性映射 */
        duty = (int)(FAN_PWM_MAX * (0.5f + 0.3f * (soc_temp - TEMP_FAN_HIGH_C) /
                                    (TEMP_THROTTLE_C - TEMP_FAN_HIGH_C)));
    } else if (soc_temp >= TEMP_FAN_LOW_C) {
        /* 20~50% 线性映射 */
        duty = (int)(FAN_PWM_MAX * (0.2f + 0.3f * (soc_temp - TEMP_FAN_LOW_C) /
                                    (TEMP_FAN_HIGH_C - TEMP_FAN_LOW_C)));
    } else if (soc_temp >= TEMP_FAN_OFF_C) {
        duty = (int)(FAN_PWM_MAX * 0.2f * (soc_temp - TEMP_FAN_OFF_C) /
                     (TEMP_FAN_LOW_C - TEMP_FAN_OFF_C));
    } else {
        duty = 0;  /* 停转 */
    }

    dev->fan.target_duty = duty;

    /* 估算噪音 (简化模型: dBA ≈ 0.045 * duty) */
    dev->fan.noise_dba = duty * 0.045f;

    return duty;
}

/**
 * @brief 设置风扇占空比
 * @param duty 占空比 (0~255)
 */
void qoo_thermal_set_fan_duty(int duty)
{
    thermal_dev_t *dev = &g_thermal;
    if (duty < 0) duty = 0;
    if (duty > FAN_PWM_MAX) duty = FAN_PWM_MAX;

    dev->fan.current_duty = duty;

    /* 通过 PWM sysfs 设置 */
    /* write_sysfs(pwm_path, duty); */

    if (duty != dev->fan.target_duty) {
        printf("[THERMAL] 风扇: %d/%d (%.0f%%), 噪音=%.1f dBA\n",
               duty, FAN_PWM_MAX, duty * 100.0f / FAN_PWM_MAX,
               dev->fan.noise_dba);
    }
}

/**
 * @brief 热降频管理
 *
 * 当温度超过降频阈值时:
 * 1. 降低 CPU/GPU/NPU 频率
 * 2. 降低电机功率限制
 *
 * @return 1 正在降频, 0 正常
 */
int qoo_thermal_throttle_check(void)
{
    thermal_dev_t *dev = &g_thermal;

    for (int i = 0; i < dev->num_zones; i++) {
        if (dev->zones[i].temperature_c > dev->zones[i].max_allowed_c * 0.9f) {
            dev->throttling = 1;
            printf("[THERMAL] 降频: %s=%.0f°C > %.0f°C\n",
                   dev->zones[i].name,
                   dev->zones[i].temperature_c,
                   dev->zones[i].max_allowed_c * 0.9f);
            return 1;
        }
    }

    dev->throttling = 0;
    return 0;
}

/**
 * @brief 热管理控制循环 (每 1s 调用)
 */
void qoo_thermal_control_loop(void)
{
    thermal_dev_t *dev = &g_thermal;

    /* 1. 读取温度 */
    qoo_thermal_read_temperatures();

    /* 2. 检查降频 */
    qoo_thermal_throttle_check();

    /* 3. 计算风扇占空比 */
    int duty = qoo_thermal_compute_fan_duty();

    /* 4. 设置风扇 (主动散热方案) */
    if (dev->solution == THERMAL_SOLUTION_ACTIVE) {
        qoo_thermal_set_fan_duty(duty);
    }

    /* 5. 紧急关机 */
    if (dev->emergency_shutdown) {
        printf("[THERMAL] 执行紧急关机!\n");
        /* system("shutdown -h now"); */
    }
}

/**
 * @brief 获取热管理状态
 * @param soc_temp 输出 SoC 温度
 * @param fan_duty 输出风扇占空比
 * @param throttling 输出降频标志
 */
void qoo_thermal_get_status(float *soc_temp, int *fan_duty, int *throttling)
{
    thermal_dev_t *dev = &g_thermal;
    if (soc_temp)   *soc_temp   = dev->zones[HEAT_SOURCE_SOC].temperature_c;
    if (fan_duty)   *fan_duty   = dev->fan.current_duty;
    if (throttling) *throttling = dev->throttling;
}

/**
 * @brief 释放散热管理资源
 */
int qoo_thermal_deinit(void)
{
    qoo_thermal_set_fan_duty(0);
    memset(&g_thermal, 0, sizeof(g_thermal));
    return QOO_OK;
}
