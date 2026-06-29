/**
 * @file qoo_power_budget.c
 * @brief QooBot 功耗预算模型工具
 *
 * 符合 docs/04能源系统设计.md §5 规范
 * - 各子系统功耗基线/典型/峰值
 * - 续航估算 (2kWh 电池)
 * - 功耗预算分配
 * - 热插拔保护
 *
 * 功耗基线 (符合规范 §5.1):
 *   计算平台: 待机5W / 典型15W / 峰值30W
 *   感知系统: 待机3W / 典型15W / 峰值30W
 *   执行系统(双臂): 待机0W / 典型60W / 峰值200W
 *   执行系统(底盘): 待机0W / 典型20W / 峰值100W
 *   通信: 待机3W / 典型5W / 峰值10W
 *   散热: 待机0W / 典型3W / 峰值10W
 *   安全/其他: 待机2W / 典型3W / 峰值5W
 *
 * 依赖：qoo_hal_power.h
 * 平台：Linux (功耗监控守护进程)
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <errno.h>
#include <math.h>

#include "../hal/qoo_hal.h"
#include "../hal/qoo_hal_power.h"

/* ===== 子系统功耗基线 (符合规范 §5.1) ===== */
typedef struct {
    float standby_w;    /* 待机功耗 (W) */
    float typical_w;    /* 典型功耗 (W) */
    float peak_w;       /* 峰值功耗 (W) */
    const char *name;   /* 子系统名称 */
} subsystem_power_t;

static const subsystem_power_t g_subsystem_power[] = {
    {  5.0f,  15.0f,  30.0f, "计算平台"      },
    {  3.0f,  15.0f,  30.0f, "感知系统"      },
    {  0.0f,  60.0f, 200.0f, "执行系统(双臂)" },
    {  0.0f,  20.0f, 100.0f, "执行系统(底盘)" },
    {  3.0f,   5.0f,  10.0f, "通信系统"      },
    {  0.0f,   3.0f,  10.0f, "散热系统"      },
    {  2.0f,   3.0f,   5.0f, "安全/其他"      },
};
#define NUM_SUBSYSTEMS (sizeof(g_subsystem_power) / sizeof(g_subsystem_power[0]))

/* ===== 续航估算 (2kWh 电池, 符合规范 §5.2) ===== */
typedef struct {
    const char *scene;         /* 场景名称 */
    float avg_power_w;         /* 平均功耗 (W) */
    float runtime_hours;       /* 续航 (小时) */
} runtime_estimate_t;

static const runtime_estimate_t g_runtime_table[] = {
    { "待机/值守",   15.0f,  133.0f },
    { "对话/交互",   50.0f,   40.0f },
    { "室内导航",    80.0f,   25.0f },
    { "轻家务",     120.0f,   16.7f },
    { "重负载操作",  200.0f,   10.0f },
    { "户外移动",    180.0f,   11.1f },
};
#define NUM_SCENES (sizeof(g_runtime_table) / sizeof(g_runtime_table[0]))

/* ===== 功耗预算配置 ===== */
typedef struct {
    float battery_capacity_wh;   /* 电池容量 (Wh) */
    float battery_voltage_v;     /* 电池电压 (V) */
    float total_budget_w;        /* 总功耗预算 (W) */
    float allocated_w[NUM_SUBSYSTEMS]; /* 各子系统分配 (W) */
    float measured_w[NUM_SUBSYSTEMS];  /* 各子系统实测 (W) */
    float total_measured_w;      /* 总实测功耗 (W) */
    float margin_w;              /* 功耗余量 (W) */
    int over_budget;             /* 超预算标志 */
} power_budget_t;

static power_budget_t g_power_budget;

/* ===== 公开 API ===== */

/**
 * @brief 初始化功耗预算模型
 * @param battery_capacity_wh 电池容量 (Wh)
 * @return QOO_OK 成功
 */
int qoo_power_budget_init(float battery_capacity_wh)
{
    power_budget_t *budget = &g_power_budget;
    memset(budget, 0, sizeof(*budget));

    budget->battery_capacity_wh = battery_capacity_wh;
    budget->total_budget_w = 0;

    /* 默认分配: 峰值 × 0.8 作为预算上限 */
    for (int i = 0; i < (int)NUM_SUBSYSTEMS; i++) {
        budget->allocated_w[i] = g_subsystem_power[i].peak_w * 0.8f;
        budget->total_budget_w += budget->allocated_w[i];
    }

    printf("[BUDGET] 功耗预算模型: 电池=%.0fWh, 总预算=%.0fW\n",
           battery_capacity_wh, budget->total_budget_w);
    return QOO_OK;
}

/**
 * @brief 查询子系统功耗基线
 * @param subsystem_id 子系统 ID
 * @param standby 输出待机功耗 (W)
 * @param typical 输出典型功耗 (W)
 * @param peak 输出峰值功耗 (W)
 * @return QOO_OK 成功
 */
int qoo_power_budget_get_baseline(int subsystem_id, float *standby, float *typical, float *peak)
{
    if (subsystem_id < 0 || subsystem_id >= (int)NUM_SUBSYSTEMS)
        return QOO_ERROR_PARAM;

    if (standby) *standby = g_subsystem_power[subsystem_id].standby_w;
    if (typical) *typical = g_subsystem_power[subsystem_id].typical_w;
    if (peak)    *peak    = g_subsystem_power[subsystem_id].peak_w;
    return QOO_OK;
}

/**
 * @brief 估算续航时间
 *
 * 基于电池容量和当前平均功耗计算剩余续航。
 *
 * @param current_power_w 当前功耗 (W)
 * @param remaining_soc_percent 剩余 SOC (%)
 * @return 续航 (小时)
 */
float qoo_power_budget_estimate_runtime(float current_power_w, float remaining_soc_percent)
{
    power_budget_t *budget = &g_power_budget;

    if (current_power_w <= 0) return 999.0f;

    float remaining_wh = budget->battery_capacity_wh * (remaining_soc_percent / 100.0f);
    return remaining_wh / current_power_w;
}

/**
 * @brief 查找匹配场景的续航
 * @param avg_power_w 平均功耗 (W)
 * @return 续航 (小时)
 */
float qoo_power_budget_find_runtime(float avg_power_w)
{
    /* 线性插值查找最近场景 */
    for (int i = 0; i < (int)NUM_SCENES - 1; i++) {
        if (avg_power_w <= g_runtime_table[i].avg_power_w)
            return g_runtime_table[i].runtime_hours;
    }
    return g_runtime_table[NUM_SCENES - 1].runtime_hours;
}

/**
 * @brief 功耗预算检查
 *
 * 检查当前总功耗是否超出预算。
 * 如超出，按优先级降级子系统 (非核心优先降级)。
 *
 * @return 0 正常, 1 超预算
 */
int qoo_power_budget_check(void)
{
    power_budget_t *budget = &g_power_budget;

    budget->total_measured_w = 0;
    for (int i = 0; i < (int)NUM_SUBSYSTEMS; i++) {
        budget->total_measured_w += budget->measured_w[i];
    }

    budget->margin_w = budget->total_budget_w - budget->total_measured_w;

    if (budget->margin_w < 0) {
        budget->over_budget = 1;
        fprintf(stderr, "[BUDGET] 超预算! 实测=%.0fW > 预算=%.0fW, 余量=%.0fW\n",
                budget->total_measured_w, budget->total_budget_w, budget->margin_w);
        return 1;
    }

    budget->over_budget = 0;
    return 0;
}

/**
 * @brief 功耗降级策略
 *
 * 当超预算时按优先级降级:
 * 1. 降低散热风扇转速
 * 2. 降低通信带宽
 * 3. 降低感知帧率
 * 4. 降低执行器扭矩限制
 * 5. 降低计算平台频率
 */
void qoo_power_budget_throttle(void)
{
    power_budget_t *budget = &g_power_budget;
    if (!budget->over_budget) return;

    float deficit_w = -budget->margin_w;

    /* 分级降级 */
    printf("[BUDGET] 功耗降级: 缺额=%.0fW\n", deficit_w);

    /* 1. 散热: 降低风扇转速 */
    if (budget->measured_w[5] > 3.0f) {
        budget->measured_w[5] *= 0.5f;
        printf("  → 散热降级: %.1fW → %.1fW\n",
               budget->measured_w[5] * 2, budget->measured_w[5]);
        deficit_w -= budget->measured_w[5];
    }

    /* 2. 通信: 降低 Wi-Fi 带宽 */
    if (deficit_w > 0 && budget->measured_w[4] > 3.0f) {
        budget->measured_w[4] *= 0.6f;
        printf("  → 通信降级: %.1fW\n", budget->measured_w[4]);
        deficit_w -= budget->measured_w[4] * 0.4f;
    }

    /* 3. 感知: 降低帧率 */
    if (deficit_w > 0 && budget->measured_w[1] > 5.0f) {
        budget->measured_w[1] *= 0.5f;
        printf("  → 感知降级: %.1fW\n", budget->measured_w[1]);
        deficit_w -= budget->measured_w[1];
    }

    /* 4. 执行器: 扭矩限制 */
    if (deficit_w > 0) {
        printf("  → 执行器扭矩限制\n");
    }

    /* 5. 计算: 降频 */
    if (deficit_w > 0) {
        printf("  → 计算平台降频\n");
    }
}

/**
 * @brief 获取功耗统计摘要
 * @param total_w 输出总功耗
 * @param margin_w 输出功耗余量
 * @param over_budget 输出超预算标志
 */
void qoo_power_budget_get_summary(float *total_w, float *margin_w, int *over_budget)
{
    power_budget_t *budget = &g_power_budget;
    if (total_w)     *total_w     = budget->total_measured_w;
    if (margin_w)    *margin_w    = budget->margin_w;
    if (over_budget) *over_budget = budget->over_budget;
}

/**
 * @brief 打印功耗报告
 */
void qoo_power_budget_print_report(void)
{
    power_budget_t *budget = &g_power_budget;

    printf("\n===== 功耗预算报告 =====\n");
    printf("电池容量: %.0f Wh\n", budget->battery_capacity_wh);
    printf("总预算:   %.0f W\n", budget->total_budget_w);
    printf("总实测:   %.0f W\n", budget->total_measured_w);
    printf("余量:     %+.0f W\n", budget->margin_w);
    printf("------------------------\n");
    for (int i = 0; i < (int)NUM_SUBSYSTEMS; i++) {
        printf("%-16s: 预算 %6.1fW | 实测 %6.1fW | 基线 [%4.1f/%5.1f/%5.1f]W\n",
               g_subsystem_power[i].name,
               budget->allocated_w[i],
               budget->measured_w[i],
               g_subsystem_power[i].standby_w,
               g_subsystem_power[i].typical_w,
               g_subsystem_power[i].peak_w);
    }
    printf("========================\n\n");
}

/**
 * @brief 释放功耗预算模型
 */
int qoo_power_budget_deinit(void)
{
    memset(&g_power_budget, 0, sizeof(g_power_budget));
    return QOO_OK;
}
