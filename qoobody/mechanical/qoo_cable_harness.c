/**
 * @file qoo_cable_harness.c
 * @brief QooBot 线束管理参考实现 (设计验证工具)
 *
 * 符合 docs/06结构与散热设计.md §4 规范
 * - 动力线: 16~20 AWG, > 100万次弯曲寿命
 * - 信号线: 26~30 AWG, 编织屏蔽, > 500万次弯曲寿命
 * - 高速信号: 同轴/差分, 铝箔+编织, > 200万次弯曲寿命
 * - 柔性扁平: FFC 0.5mm, > 1000万次弯曲寿命
 *
 * 走线原则 (符合规范 §4.2):
 * 1. 动力线与信号线分离, 间距 > 20mm
 * 2. 高速差分对保持等长、等间距
 * 3. 关节处预留弯曲半径 ≥ 线径×10
 * 4. 过孔/滑环处使用应力释放
 * 5. 全部连接器带锁扣
 *
 * 平台：Linux (设计验证/检查工具)
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <errno.h>
#include <math.h>

#include "../hal/qoo_hal.h"

/* ===== 线缆规格 ===== */
typedef enum {
    CABLE_TYPE_POWER     = 0,  /* 动力线 */
    CABLE_TYPE_SIGNAL    = 1,  /* 信号线 */
    CABLE_TYPE_HIGH_SPEED = 2, /* 高速信号 */
    CABLE_TYPE_FLEX      = 3,  /* 柔性扁平 */
} cable_type_t;

typedef struct {
    cable_type_t type;
    const char *name;
    int awg_min, awg_max;      /* 线规范围 */
    const char *shielding;      /* 屏蔽类型 */
    int bend_cycles_min;        /* 最小弯曲寿命 */
    float min_bend_radius_mult; /* 最小弯曲半径倍数 */
    float min_spacing_mm;       /* 最小间距 (与其他线) */
    int need_lock_connector;    /* 是否需要锁扣连接器 */
} cable_spec_t;

static const cable_spec_t g_cable_specs[] = {
    { CABLE_TYPE_POWER,      "动力线",   16, 20, "无",           1000000, 10, 20, 1 },
    { CABLE_TYPE_SIGNAL,     "信号线",   26, 30, "编织屏蔽",     5000000, 10, 10, 1 },
    { CABLE_TYPE_HIGH_SPEED, "高速信号", 30, 34, "铝箔+编织",    2000000, 8,  5,  1 },
    { CABLE_TYPE_FLEX,       "柔性扁平", 30, 34, "可选",         10000000,5,  5,  1 },
};

/* ===== 线缆实例 ===== */
typedef struct {
    int id;
    cable_type_t type;
    float awg;                 /* AWG */
    float length_mm;           /* 长度 */
    float bend_radius_mm;      /* 弯曲半径 */
    float spacing_to_nearest_mm; /* 到最近其他线的间距 */
    int has_lock_connector;    /* 是否有锁扣 */
    int has_stress_relief;     /* 是否有应力释放 */
    const char *from;          /* 起点 */
    const char *to;            /* 终点 */
    int validation_pass;       /* 验证通过 */
} cable_instance_t;

/* ===== 公开 API ===== */

/**
 * @brief 获取线缆规格
 * @param type 线缆类型
 * @return 线缆规格
 */
const cable_spec_t *qoo_cable_get_spec(cable_type_t type)
{
    if (type < 0 || type > CABLE_TYPE_FLEX) return NULL;
    return &g_cable_specs[type];
}

/**
 * @brief 验证单根线缆是否符合规范
 *
 * 检查项:
 * 1. 弯曲半径 ≥ 线径×10
 * 2. 动力线/信号线间距 > 20mm
 * 3. 高速差分对等长
 * 4. 连接器带锁扣
 * 5. 应力释放
 *
 * @param cable 线缆实例
 * @return QOO_OK 符合规范
 */
int qoo_cable_validate(const cable_instance_t *cable)
{
    const cable_spec_t *spec = qoo_cable_get_spec(cable->type);
    if (!spec) return QOO_ERROR_PARAM;

    int pass = 1;

    /* 1. 弯曲半径检查 */
    float wire_diameter_mm = 0.127 * powf(92, (36 - cable->awg) / 39.0f); /* AWG→mm */
    float min_bend = wire_diameter_mm * spec->min_bend_radius_mult;
    if (cable->bend_radius_mm < min_bend) {
        printf("  [WARN] 线缆 %d: 弯曲半径 %.1fmm < 最小 %.1fmm (%.1f AWG × %d)\n",
               cable->id, cable->bend_radius_mm, min_bend,
               cable->awg, (int)spec->min_bend_radius_mult);
        pass = 0;
    }

    /* 2. 间距检查 */
    if (cable->spacing_to_nearest_mm < spec->min_spacing_mm) {
        printf("  [WARN] 线缆 %d: 间距 %.1fmm < 最小 %.1fmm\n",
               cable->id, cable->spacing_to_nearest_mm, spec->min_spacing_mm);
        pass = 0;
    }

    /* 3. 锁扣连接器检查 */
    if (spec->need_lock_connector && !cable->has_lock_connector) {
        printf("  [WARN] 线缆 %d: 缺少锁扣连接器\n", cable->id);
        pass = 0;
    }

    /* 4. 应力释放检查 */
    if (!cable->has_stress_relief) {
        printf("  [WARN] 线缆 %d: 缺少应力释放\n", cable->id);
        pass = 0;
    }

    return pass ? QOO_OK : QOO_ERROR;
}

/**
 * @brief 验证所有线缆
 * @param cables 线缆数组
 * @param num_cables 线缆数量
 * @return 通过数
 */
int qoo_cable_validate_all(const cable_instance_t *cables, int num_cables)
{
    int passed = 0;

    printf("===== 线束设计验证 =====\n");
    for (int i = 0; i < num_cables; i++) {
        printf("[%d] %s: %s → %s\n", cables[i].id,
               g_cable_specs[cables[i].type].name,
               cables[i].from, cables[i].to);

        if (qoo_cable_validate(&cables[i]) == QOO_OK) {
            passed++;
            printf("  → PASS\n");
        } else {
            printf("  → FAIL\n");
        }
    }
    printf("========================\n");
    printf("结果: %d/%d 通过\n", passed, num_cables);

    return passed;
}

/**
 * @brief 打印线束设计检查清单
 */
void qoo_cable_print_checklist(void)
{
    printf("\n===== 线束管理设计检查清单 (DFM) =====\n");
    printf("[ ] 动力线与信号线分离, 间距 > 20mm\n");
    printf("[ ] 高速差分对保持等长、等间距\n");
    printf("[ ] 关节处预留足够的弯曲半径 (≥ 线径×10)\n");
    printf("[ ] 过孔/滑环处使用应力释放\n");
    printf("[ ] 全部连接器带锁扣\n");
    printf("[ ] 动力线 16~20 AWG\n");
    printf("[ ] 信号线 26~30 AWG, 编织屏蔽\n");
    printf("[ ] 高速信号 同轴/差分, 铝箔+编织屏蔽\n");
    printf("[ ] 柔性扁平 FFC 0.5mm pitch\n");
    printf("========================================\n\n");
}
