/**
 * @file qoo_reliability_test.c
 * @brief QooBot 可靠性测试标准参考实现
 *
 * 符合 docs/08测试与验证规范.md §3 规范
 *
 * 环境应力测试:
 *   高温运行: +60°C, 96h, 功能正常无降级
 *   低温运行: -10°C, 96h, 电池容量 ≥ 80%
 *   湿热循环: 25~55°C, 95%RH, 10循环, 无凝露
 *   温度冲击: -20°C ↔ +70°C, 100循环, 焊点无裂纹
 *   盐雾: 5% NaCl, 35°C, 48h, 无严重腐蚀
 *
 * 机械应力测试:
 *   随机振动: 5~500Hz, 2.5g rms
 *   机械冲击: 15g, 11ms, 半正弦
 *   跌落测试: 1m 自由落体 (包装)
 *   关节耐久: 50% 额定扭矩, 100万次
 *
 * 老化与寿命测试:
 *   关节减速器: 额定扭矩连续, ≥ 5000h
 *   电池循环: 1C 充放电, ≥ 500 循环
 *   线缆弯折: 关节全范围往复, ≥ 100 万次
 *   连接器插拔: ≥ 5000 次
 *
 * 平台：Linux (测试脚本框架)
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <errno.h>
#include <time.h>

#include "../hal/qoo_hal.h"

/* ===== 测试类型 ===== */
typedef enum {
    REL_TEST_ENV_HIGH_TEMP   = 0,  /* 高温运行 */
    REL_TEST_ENV_LOW_TEMP    = 1,  /* 低温运行 */
    REL_TEST_ENV_HUMIDITY    = 2,  /* 湿热循环 */
    REL_TEST_ENV_THERMAL_SHOCK = 3, /* 温度冲击 */
    REL_TEST_ENV_SALT_SPRAY  = 4,  /* 盐雾 */
    REL_TEST_MECH_VIBRATION  = 5,  /* 随机振动 */
    REL_TEST_MECH_SHOCK      = 6,  /* 机械冲击 */
    REL_TEST_MECH_DROP       = 7,  /* 跌落 */
    REL_TEST_MECH_JOINT_DUR  = 8,  /* 关节耐久 */
    REL_TEST_AGING_GEARBOX   = 9,  /* 减速器寿命 */
    REL_TEST_AGING_BATTERY   = 10, /* 电池循环 */
    REL_TEST_AGING_CABLE     = 11, /* 线缆弯折 */
    REL_TEST_AGING_CONNECTOR = 12, /* 连接器插拔 */
} reliability_test_type_t;

/* ===== 测试规格 ===== */
typedef struct {
    reliability_test_type_t type;
    const char *name;
    const char *standard_ref;     /* 参考标准 */
    const char *test_condition;   /* 测试条件 */
    const char *duration;         /* 持续时间 */
    const char *pass_criteria;    /* 判定标准 */
    int result;                   /* 0=PASS, 1=FAIL */
    const char *remarks;          /* 备注 */
} reliability_test_spec_t;

static reliability_test_spec_t g_rel_tests[] = {
    { REL_TEST_ENV_HIGH_TEMP,   "高温运行",   "IEC 60068-2-2",
      "+60°C, 额定负载",       "96h",
      "功能正常，无降级",       0, "" },
    { REL_TEST_ENV_LOW_TEMP,    "低温运行",   "IEC 60068-2-1",
      "-10°C, 额定负载",       "96h",
      "功能正常，电池容量 ≥ 80%", 0, "" },
    { REL_TEST_ENV_HUMIDITY,    "湿热循环",   "IEC 60068-2-30",
      "25~55°C, 95%RH",       "10 循环",
      "无凝露短路，无腐蚀",     0, "" },
    { REL_TEST_ENV_THERMAL_SHOCK,"温度冲击",  "IEC 60068-2-14",
      "-20°C ↔ +70°C",       "100 循环",
      "焊点无裂纹，功能正常",   0, "" },
    { REL_TEST_ENV_SALT_SPRAY,  "盐雾",       "IEC 60068-2-11",
      "5% NaCl, 35°C",        "48h",
      "无严重腐蚀 (关节除外)",  0, "" },
    { REL_TEST_MECH_VIBRATION,  "随机振动",   "IEC 60068-2-64",
      "5~500Hz, 2.5g rms",    "—",
      "结构无松动，电气连接可靠", 0, "" },
    { REL_TEST_MECH_SHOCK,      "机械冲击",   "IEC 60068-2-27",
      "15g, 11ms, 半正弦",     "—",
      "功能正常，无永久变形",   0, "" },
    { REL_TEST_MECH_DROP,       "跌落测试",   "ISTA 1A",
      "1m 自由落体 (包装)",    "—",
      "包装内产品无损坏",       0, "" },
    { REL_TEST_MECH_JOINT_DUR,  "关节耐久",   "—",
      "50% 额定扭矩",          "100 万次",
      "间隙增量 < 0.1°",       0, "" },
    { REL_TEST_AGING_GEARBOX,   "减速器寿命", "—",
      "额定扭矩连续运行",      "≥ 5000h",
      "等效寿命 ≥ 5000h",      0, "" },
    { REL_TEST_AGING_BATTERY,   "电池循环",   "—",
      "1C 充放电循环",         "≥ 500 循环",
      "≥ 80% 容量保持",        0, "" },
    { REL_TEST_AGING_CABLE,     "线缆弯折",   "—",
      "关节全范围往复",        "≥ 100 万次",
      "电气导通，无断裂",       0, "" },
    { REL_TEST_AGING_CONNECTOR, "连接器插拔", "—",
      "手动插拔",              "≥ 5000 次",
      "接触电阻 < 50mΩ",       0, "" },
};
#define NUM_REL_TESTS (sizeof(g_rel_tests) / sizeof(g_rel_tests[0]))

/* ===== 公开 API ===== */

/**
 * @brief 打印可靠性测试标准总览
 */
void qoo_reliability_print_standards(void)
{
    printf("\n========================================\n");
    printf("     QooBot 可靠性测试标准\n");
    printf("========================================\n");

    printf("\n--- 环境应力测试 ---\n");
    for (int i = 0; i <= REL_TEST_ENV_SALT_SPRAY; i++) {
        printf("  %-12s: %s | %s | %s | %s\n",
               g_rel_tests[i].name,
               g_rel_tests[i].standard_ref,
               g_rel_tests[i].test_condition,
               g_rel_tests[i].duration,
               g_rel_tests[i].pass_criteria);
    }

    printf("\n--- 机械应力测试 ---\n");
    for (int i = REL_TEST_MECH_VIBRATION; i <= REL_TEST_MECH_JOINT_DUR; i++) {
        printf("  %-12s: %s | %s | %s | %s\n",
               g_rel_tests[i].name,
               g_rel_tests[i].standard_ref,
               g_rel_tests[i].test_condition,
               g_rel_tests[i].duration,
               g_rel_tests[i].pass_criteria);
    }

    printf("\n--- 老化与寿命测试 ---\n");
    for (int i = REL_TEST_AGING_GEARBOX; i <= REL_TEST_AGING_CONNECTOR; i++) {
        printf("  %-12s: %s | %s | %s\n",
               g_rel_tests[i].name,
               g_rel_tests[i].test_condition,
               g_rel_tests[i].duration,
               g_rel_tests[i].pass_criteria);
    }

    printf("========================================\n\n");
}

/**
 * @brief 可靠性测试门禁检查
 *
 * 根据 docs/08测试与验证规范.md §6 验证阶段门禁:
 * - EVT: 所有 P0 功能通过
 * - DVT: 全部测试通过，无 P0/P1 缺陷
 * - PVT: 互操作 A/B 级 ≥ 90%
 * - MP: AQL 抽检合格率 ≥ 99%
 */
void qoo_reliability_gate_check(const char *phase)
{
    printf("\n===== 可靠性测试门禁: %s =====\n", phase);

    int passed = 0;
    for (int i = 0; i < (int)NUM_REL_TESTS; i++) {
        if (g_rel_tests[i].result == 0) passed++;
    }

    printf("通过: %d/%d\n", passed, (int)NUM_REL_TESTS);

    if (strcmp(phase, "EVT") == 0) {
        /* EVT: 环境应力测试必须全部通过 */
        int env_pass = 1;
        for (int i = 0; i <= REL_TEST_ENV_SALT_SPRAY; i++) {
            if (g_rel_tests[i].result != 0) env_pass = 0;
        }
        printf("EVT 门禁: %s\n", env_pass ? "PASS ✓" : "FAIL ✗");
    } else if (strcmp(phase, "DVT") == 0) {
        printf("DVT 门禁: %s\n",
               passed == (int)NUM_REL_TESTS ? "PASS ✓" : "FAIL ✗");
    }

    printf("===============================\n\n");
}
