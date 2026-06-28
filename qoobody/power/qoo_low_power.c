/**
 * @file qoo_low_power.c
 * @brief QooBot 低功耗模式固件参考实现
 *
 * 符合 docs/04能源系统设计.md §6 规范
 * - 运行 (Active): 15~200W, 全功能
 * - 待机 (Standby): <10W, 内存保持, 语音/触摸/定时唤醒, <1s 恢复
 * - 休眠 (Suspend): <2W, 内存→存储, 电源键/定时唤醒, <10s 恢复
 * - 深度休眠 (Off): <0.5W, 完全断电, 电源键唤醒, <30s 恢复
 * - 运输模式: <0.1W, 电池断开, 充电器接入唤醒
 *
 * 待机功耗分解 (符合规范 §6.2):
 *   计算平台 (LP mode) ... 2W
 *   安全 MCU ............ 0.5W
 *   麦克风阵列 (唤醒词) .. 1W
 *   相机 (低帧率 5fps) ... 2W
 *   Wi-Fi/BLE 待机 ...... 0.5W
 *   BMS + 电源树损耗 ..... 2W
 *   其他 ................. 2W
 *   合计 ................. 10W
 *
 * 依赖：qoo_hal_power.h
 * 平台：安全 MCU + 主控 SoC PMIC
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <errno.h>
#include <time.h>

#include "../hal/qoo_hal.h"
#include "../hal/qoo_hal_power.h"

/* ===== 低功耗模式定义 (符合规范 §6.1) ===== */
typedef enum {
    LP_MODE_ACTIVE    = 0,  /* 运行: 15~200W */
    LP_MODE_STANDBY   = 1,  /* 待机: <10W */
    LP_MODE_SUSPEND   = 2,  /* 休眠: <2W */
    LP_MODE_DEEP_SLEEP = 3, /* 深度休眠: <0.5W */
    LP_MODE_SHIPPING  = 4,  /* 运输模式: <0.1W */
} low_power_mode_t;

/* ===== 模式功耗上限 (mW) ===== */
#define LP_POWER_ACTIVE_MAX_MW      200000
#define LP_POWER_STANDBY_MAX_MW      10000
#define LP_POWER_SUSPEND_MAX_MW       2000
#define LP_POWER_DEEP_SLEEP_MAX_MW     500
#define LP_POWER_SHIPPING_MAX_MW       100

/* ===== 模式转换延迟 (ms) ===== */
#define LP_RESUME_ACTIVE_MS           0     /* Active → Active: 无需 */
#define LP_RESUME_STANDBY_MS        1000    /* Standby → Active: <1s */
#define LP_RESUME_SUSPEND_MS       10000    /* Suspend → Active: <10s */
#define LP_RESUME_DEEP_SLEEP_MS    30000    /* Deep Sleep → Active: <30s */
#define LP_RESUME_SHIPPING_MS      60000    /* Shipping → Active: 首次启动 */

/* ===== 待机功耗分解 (mW, 符合规范 §6.2) ===== */
typedef struct {
    const char *component;
    float power_mw;
} standby_power_breakdown_t;

static const standby_power_breakdown_t g_standby_breakdown[] = {
    { "计算平台 (LP mode)", 2000 },
    { "安全 MCU",             500 },
    { "麦克风阵列 (唤醒词)",  1000 },
    { "相机 (5fps)",         2000 },
    { "Wi-Fi/BLE 待机",       500 },
    { "BMS + 电源树损耗",    2000 },
    { "其他",                2000 },
};
#define NUM_STANDBY_COMPONENTS \
    (sizeof(g_standby_breakdown) / sizeof(g_standby_breakdown[0]))

/* ===== 唤醒源定义 ===== */
typedef enum {
    WAKE_SRC_NONE       = 0,
    WAKE_SRC_VOICE      = 1,   /* 语音唤醒词 */
    WAKE_SRC_TOUCH      = 2,   /* 触摸/按键 */
    WAKE_SRC_TIMER      = 3,   /* 定时器 */
    WAKE_SRC_POWER_BTN  = 4,   /* 电源键 */
    WAKE_SRC_CHARGER    = 5,   /* 充电器接入 */
    WAKE_SRC_MOTION     = 6,   /* IMU 运动检测 */
    WAKE_SRC_WIFI       = 7,   /* Wi-Fi WoWLAN */
    WAKE_SRC_BLE        = 8,   /* BLE 连接 */
} wake_source_t;

/* ===== 低功耗管理设备 ===== */
typedef struct {
    low_power_mode_t current_mode;
    low_power_mode_t target_mode;
    int transitioning;

    /* 功耗监控 */
    float current_power_mw;
    float standby_power_mw;

    /* 唤醒配置 */
    uint32_t wake_sources_enabled;  /* 使能的唤醒源位掩码 */
    wake_source_t last_wake_source;
    uint64_t last_wake_time_ms;

    /* 定时唤醒 */
    uint64_t wake_timer_deadline_ms;

    /* 统计 */
    uint32_t standby_entry_count;
    uint32_t suspend_entry_count;
    uint64_t total_standby_time_ms;
    uint64_t total_suspend_time_ms;
} low_power_dev_t;

static low_power_dev_t g_lp_dev;

/* ===== 内部函数 ===== */
static int lp_enter_standby(void);
static int lp_enter_suspend(void);
static int lp_enter_deep_sleep(void);
static int lp_enter_shipping(void);
static int lp_resume_from_standby(void);
static int lp_resume_from_suspend(void);
static int lp_resume_from_deep_sleep(void);

/* ===== 公开 API ===== */

/**
 * @brief 初始化低功耗管理系统
 * @return QOO_OK 成功
 */
int qoo_low_power_init(void)
{
    low_power_dev_t *dev = &g_lp_dev;
    memset(dev, 0, sizeof(*dev));

    dev->current_mode = LP_MODE_ACTIVE;
    dev->current_power_mw = 15000; /* 典型 15W */

    /* 默认启用语音、触摸、电源键唤醒 */
    dev->wake_sources_enabled =
        (1 << WAKE_SRC_VOICE) |
        (1 << WAKE_SRC_TOUCH) |
        (1 << WAKE_SRC_POWER_BTN);

    printf("[LP] 低功耗管理初始化: 当前=Active, 待机预算=%.0fmW\n",
           (float)LP_POWER_STANDBY_MAX_MW);
    return QOO_OK;
}

/**
 * @brief 请求进入低功耗模式
 *
 * @param mode 目标模式
 * @param timeout_ms 超时后自动进入 (0=立即)
 * @return QOO_OK 成功
 */
int qoo_low_power_request(low_power_mode_t mode, uint32_t timeout_ms)
{
    low_power_dev_t *dev = &g_lp_dev;

    if (mode == dev->current_mode) return QOO_OK;

    printf("[LP] 请求模式切换: %d → %d (超时=%ums)\n",
           dev->current_mode, mode, timeout_ms);

    if (timeout_ms > 0) {
        dev->wake_timer_deadline_ms = timeout_ms; /* + system_time_ms */
    }

    dev->target_mode = mode;

    /* 立即执行切换 */
    switch (mode) {
    case LP_MODE_STANDBY:
        return lp_enter_standby();
    case LP_MODE_SUSPEND:
        return lp_enter_suspend();
    case LP_MODE_DEEP_SLEEP:
        return lp_enter_deep_sleep();
    case LP_MODE_SHIPPING:
        return lp_enter_shipping();
    default:
        break;
    }

    return QOO_OK;
}

/**
 * @brief 启用唤醒源
 * @param source 唤醒源
 * @return QOO_OK 成功
 */
int qoo_low_power_enable_wake_source(wake_source_t source)
{
    g_lp_dev.wake_sources_enabled |= (1 << source);
    printf("[LP] 启用唤醒源: %d\n", source);
    return QOO_OK;
}

/**
 * @brief 禁用唤醒源
 * @param source 唤醒源
 * @return QOO_OK 成功
 */
int qoo_low_power_disable_wake_source(wake_source_t source)
{
    g_lp_dev.wake_sources_enabled &= ~(1 << source);
    printf("[LP] 禁用唤醒源: %d\n", source);
    return QOO_OK;
}

/**
 * @brief 检查唤醒源是否触发
 * @return 触发的唤醒源 (WAKE_SRC_NONE 表示未触发)
 */
wake_source_t qoo_low_power_check_wake(void)
{
    low_power_dev_t *dev = &g_lp_dev;

    /* 检查各唤醒源 (实际需读取硬件状态) */
    if (dev->wake_sources_enabled & (1 << WAKE_SRC_VOICE))
        ; /* 检查语音唤醒词检测 */
    if (dev->wake_sources_enabled & (1 << WAKE_SRC_TOUCH))
        ; /* 检查触摸传感器 */
    if (dev->wake_sources_enabled & (1 << WAKE_SRC_POWER_BTN))
        ; /* 检查电源键 GPIO */
    if (dev->wake_sources_enabled & (1 << WAKE_SRC_CHARGER))
        ; /* 检查充电器插入检测 */

    return WAKE_SRC_NONE;
}

/**
 * @brief 获取当前低功耗模式
 * @return 当前模式
 */
low_power_mode_t qoo_low_power_get_mode(void)
{
    return g_lp_dev.current_mode;
}

/**
 * @brief 获取当前功耗 (mW)
 * @return 功耗 (mW)
 */
float qoo_low_power_get_power_mw(void)
{
    return g_lp_dev.current_power_mw;
}

/**
 * @brief 获取待机功耗分解
 * @param breakdown 输出功耗分解数组 (调用者分配)
 * @return 组件数量
 */
int qoo_low_power_get_standby_breakdown(standby_power_breakdown_t *breakdown)
{
    memcpy(breakdown, g_standby_breakdown, sizeof(g_standby_breakdown));
    return NUM_STANDBY_COMPONENTS;
}

/**
 * @brief 获取上次唤醒信息
 * @param source 输出唤醒源
 * @param wake_time_ms 输出唤醒时间
 */
void qoo_low_power_get_last_wake(wake_source_t *source, uint64_t *wake_time_ms)
{
    if (source)       *source       = g_lp_dev.last_wake_source;
    if (wake_time_ms) *wake_time_ms = g_lp_dev.last_wake_time_ms;
}

/**
 * @brief 打印低功耗统计
 */
void qoo_low_power_print_stats(void)
{
    low_power_dev_t *dev = &g_lp_dev;

    printf("\n===== 低功耗统计 =====\n");
    printf("当前模式: %d\n", dev->current_mode);
    printf("当前功耗: %.0f mW\n", dev->current_power_mw);
    printf("待机次数: %u, 累计: %llu ms\n",
           dev->standby_entry_count,
           (unsigned long long)dev->total_standby_time_ms);
    printf("休眠次数: %u, 累计: %llu ms\n",
           dev->suspend_entry_count,
           (unsigned long long)dev->total_suspend_time_ms);
    printf("上次唤醒: source=%d\n", dev->last_wake_source);
    printf("======================\n\n");
}

/* ===== 模式切换实现 ===== */

static int lp_enter_standby(void)
{
    low_power_dev_t *dev = &g_lp_dev;
    dev->current_mode = LP_MODE_STANDBY;
    dev->current_power_mw = LP_POWER_STANDBY_MAX_MW;
    dev->standby_entry_count++;

    printf("[LP] → 待机模式 (< 10W)\n");

    /* 待机操作:
     * 1. 降低 SoC 到低功耗模式 (LP cluster only)
     * 2. 降低相机帧率到 5fps
     * 3. 保持麦克风阵列唤醒词检测
     * 4. 保持 Wi-Fi/BLE 待机连接
     * 5. 关闭非必要外设电源
     */
    return QOO_OK;
}

static int lp_enter_suspend(void)
{
    low_power_dev_t *dev = &g_lp_dev;
    dev->current_mode = LP_MODE_SUSPEND;
    dev->current_power_mw = LP_POWER_SUSPEND_MAX_MW;
    dev->suspend_entry_count++;

    printf("[LP] → 休眠模式 (< 2W)\n");

    /* 休眠操作:
     * 1. 保存内存到存储 (suspend-to-disk)
     * 2. 关闭 SoC 电源 (除唤醒域)
     * 3. 关闭所有传感器
     * 4. 仅安全 MCU 运行
     */
    return QOO_OK;
}

static int lp_enter_deep_sleep(void)
{
    low_power_dev_t *dev = &g_lp_dev;
    dev->current_mode = LP_MODE_DEEP_SLEEP;
    dev->current_power_mw = LP_POWER_DEEP_SLEEP_MAX_MW;

    printf("[LP] → 深度休眠 (< 0.5W)\n");

    /* 深度休眠操作:
     * 1. 完全断电 (除安全 MCU 和电源键检测)
     * 2. 断开电池输出 (通过 BMS MOSFET)
     */
    return QOO_OK;
}

static int lp_enter_shipping(void)
{
    low_power_dev_t *dev = &g_lp_dev;
    dev->current_mode = LP_MODE_SHIPPING;
    dev->current_power_mw = LP_POWER_SHIPPING_MAX_MW;

    printf("[LP] → 运输模式 (< 0.1W)\n");

    /* 运输模式操作:
     * 1. BMS 断开电池输出
     * 2. 仅充电器接入可唤醒
     */
    return QOO_OK;
}

static int lp_resume_from_standby(void)
{
    printf("[LP] 从待机恢复 (< 1s)\n");
    g_lp_dev.current_mode = LP_MODE_ACTIVE;
    g_lp_dev.current_power_mw = 15000;
    return QOO_OK;
}

static int lp_resume_from_suspend(void)
{
    printf("[LP] 从休眠恢复 (< 10s)\n");
    g_lp_dev.current_mode = LP_MODE_ACTIVE;
    g_lp_dev.current_power_mw = 15000;
    return QOO_OK;
}

static int lp_resume_from_deep_sleep(void)
{
    printf("[LP] 从深度休眠恢复 (< 30s)\n");
    g_lp_dev.current_mode = LP_MODE_ACTIVE;
    g_lp_dev.current_power_mw = 15000;
    return QOO_OK;
}

/**
 * @brief 释放低功耗管理资源
 */
int qoo_low_power_deinit(void)
{
    memset(&g_lp_dev, 0, sizeof(g_lp_dev));
    return QOO_OK;
}
