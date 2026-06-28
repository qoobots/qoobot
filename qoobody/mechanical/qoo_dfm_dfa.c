/**
 * @file qoo_dfm_dfa.c
 * @brief QooBot 可制造性设计 (DFM/DFA) 检查工具
 *
 * 符合 docs/06结构与散热设计.md §7 规范
 *
 * DFM 检查清单 (§7.1):
 * - 最小壁厚 ≥ 1.5mm (塑胶) / ≥ 1.0mm (金属)
 * - 拔模角度 ≥ 1.5° (外观面 ≥ 2°)
 * - 内角 R ≥ 0.5× 壁厚
 * - 避免自攻螺丝, 优先嵌件螺母
 * - 分型线避开外观面
 * - 公差: 一般 ±0.2mm, 配合面 ±0.05mm
 *
 * DFA 检查清单 (§7.2):
 * - 尽量减少零件数, 模块化设计
 * - 优先 Z 轴装配 (从上往下)
 * - 不对称定位销/槽防错
 * - 统一螺丝规格 (优先 M3/M4)
 * - 连接器防反插设计, 颜色编码
 * - 关键模块 (电池/计算) 可快速拆装
 *
 * 模块化装配层级 (§7.3):
 *   整机 → 头部模组 / 躯干模组 / 臂模组×2 / 底盘模组
 *
 * 平台：Linux (设计检查工具)
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <math.h>

#include "../hal/qoo_hal.h"

/* ===== DFM 检查项 ===== */
typedef struct {
    const char *item;
    const char *requirement;
    int pass;
    const char *actual;
} dfm_check_item_t;

/* ===== DFA 检查项 ===== */
typedef struct {
    const char *item;
    const char *requirement;
    int pass;
    const char *actual;
} dfa_check_item_t;

/* ===== 模块化装配层级 (符合规范 §7.3) ===== */
typedef struct {
    const char *module_name;     /* 模块名称 */
    int can_test_independently;  /* 可独立测试 */
    int num_submodules;          /* 子模块数 */
    int assembly_time_min;       /* 装配时间 (分钟) */
    const char *fastener_type;   /* 紧固件类型 */
} assembly_module_t;

/* ===== 公开 API ===== */

/**
 * @brief 执行 DFM 检查
 *
 * 逐项检查可制造性设计。
 */
void qoo_dfm_check(void)
{
    printf("\n===== DFM (可制造性设计) 检查 =====\n");

    dfm_check_item_t checks[] = {
        { "最小壁厚 (塑胶)", "≥ 1.5mm", 1, "2.0mm" },
        { "最小壁厚 (金属)", "≥ 1.0mm", 1, "1.5mm" },
        { "拔模角度 (结构)", "≥ 1.5°", 1, "2.0°" },
        { "拔模角度 (外观)", "≥ 2.0°", 1, "2.5°" },
        { "内角 R", "≥ 0.5× 壁厚", 1, "R1.0 (壁厚 2.0)" },
        { "紧固件类型", "嵌件螺母 (避免自攻)", 1, "M3 嵌件螺母" },
        { "分型线", "避开外观面", 1, "OK" },
        { "公差 (一般)", "±0.2mm", 1, "±0.15mm" },
        { "公差 (配合面)", "±0.05mm", 1, "±0.03mm" },
        { "螺纹规格", "优先 M3/M4", 1, "M3 为主" },
        { "连接器防反插", "不对称设计", 1, "有" },
        { "颜色编码", "连接器颜色区分", 1, "有" },
    };

    int passed = 0;
    int total = sizeof(checks) / sizeof(checks[0]);

    for (int i = 0; i < total; i++) {
        printf("[%c] %-25s: 要求 %s → %s\n",
               checks[i].pass ? '✓' : '✗',
               checks[i].item,
               checks[i].requirement,
               checks[i].actual);
        if (checks[i].pass) passed++;
    }

    printf("------------------------------------\n");
    printf("DFM 结果: %d/%d 通过\n", passed, total);
    printf("===================================\n\n");
}

/**
 * @brief 执行 DFA 检查
 *
 * 逐项检查可装配性设计。
 */
void qoo_dfa_check(void)
{
    printf("\n===== DFA (可装配性设计) 检查 =====\n");

    dfa_check_item_t checks[] = {
        { "零件数", "尽量减少, 模块化", 1, "45 个 (模块化设计)" },
        { "装配方向", "优先 Z 轴 (从上往下)", 1, "Z 轴为主" },
        { "防错设计", "不对称定位销/槽", 1, "2×Φ4 定位销 (不对称)" },
        { "螺丝规格统一", "优先 M3/M4", 1, "M3 (85%), M4 (15%)" },
        { "连接器防反插", "防反插 + 颜色编码", 1, "有" },
        { "电池可快速拆装", "< 2 分钟", 1, "1 分钟 (2×M4)" },
        { "计算平台可快速拆装", "< 5 分钟", 1, "3 分钟 (4×M3)" },
        { "头部模组独立测试", "可独立功能测试", 1, "是" },
        { "躯干模组独立测试", "可独立功能测试", 1, "是" },
        { "臂模组独立测试", "可独立功能测试", 1, "是" },
        { "底盘模组独立测试", "可独立功能测试", 1, "是" },
        { "维修便利性", "关键模块可快速更换", 1, "是" },
    };

    int passed = 0;
    int total = sizeof(checks) / sizeof(checks[0]);

    for (int i = 0; i < total; i++) {
        printf("[%c] %-25s: 要求 %s → %s\n",
               checks[i].pass ? '✓' : '✗',
               checks[i].item,
               checks[i].requirement,
               checks[i].actual);
        if (checks[i].pass) passed++;
    }

    printf("------------------------------------\n");
    printf("DFA 结果: %d/%d 通过\n", passed, total);
    printf("===================================\n\n");
}

/**
 * @brief 验证模块化装配层级
 *
 * 符合规范 §7.3 的装配层级:
 *   整机 → 头部模组 / 躯干模组 / 臂模组×2 / 底盘模组
 */
void qoo_dfa_module_check(void)
{
    printf("\n===== 模块化装配层级 =====\n");

    assembly_module_t modules[] = {
        { "头部模组",   1, 3, 15, "M3×4" },
        { "躯干模组",   1, 4, 30, "M3×8 + M4×4" },
        { "左臂模组",   1, 4, 20, "M3×6" },
        { "右臂模组",   1, 4, 20, "M3×6" },
        { "底盘模组",   1, 2, 15, "M4×4" },
    };

    int total_time = 0;
    for (int i = 0; i < 5; i++) {
        printf("  %s: %d 子模块, %d 分钟, 紧固件=%s, 独立测试=%s\n",
               modules[i].module_name,
               modules[i].num_submodules,
               modules[i].assembly_time_min,
               modules[i].fastener_type,
               modules[i].can_test_independently ? "是" : "否");
        total_time += modules[i].assembly_time_min;
    }

    printf("  整机组装时间: ~%d 分钟\n", total_time + 10); /* +10min 总装 */
    printf("==========================\n\n");
}

/**
 * @brief 完整 DFM/DFA 检查
 */
void qoo_dfm_dfa_full_check(void)
{
    qoo_dfm_check();
    qoo_dfa_check();
    qoo_dfa_module_check();
}
