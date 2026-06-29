/**
 * @file qoo_emc_design.c
 * @brief QooBot 电磁兼容 (EMC) 设计验证参考实现
 *
 * 符合 docs/06结构与散热设计.md §6 规范
 * - PCB 层叠: ≥ 4 层, 完整地平面
 * - 屏蔽: 关键模组金属屏蔽罩
 * - 滤波: 电源入口 π 型滤波、共模扼流圈
 * - 接地: 单点接地、数字/模拟地分割
 * - 电机 EMI: 电机相线磁环、驱动器 PWM 扩频
 * - 外壳接地: 金属外壳可靠接地 (接地阻抗 < 0.1Ω)
 *
 * 分区隔离 (符合规范 §6.2):
 *   [高噪声区: 电机驱动/DC-DC] ←隔离带→ [计算区: SoC/内存/存储] ←隔离带→ [敏感区: 模拟前端/传感器/射频]
 *
 * EMC 可靠性测试限值 (符合 docs/08测试与验证规范.md §3.4):
 *   辐射发射: CISPR 32 Class B, 30MHz~6GHz
 *   传导发射: CISPR 32 Class B, 150kHz~30MHz
 *   ESD: IEC 61000-4-2, ±8kV 接触 / ±15kV 空气, Level 4
 *   辐射抗扰度: IEC 61000-4-3, 10V/m, 80MHz~6GHz, Level 3
 *   EFT: IEC 61000-4-4, ±2kV 电源 / ±1kV 信号, Level 3
 *
 * 平台：Linux (设计检查/验证工具)
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <math.h>

#include "../hal/qoo_hal.h"

/* ===== EMC 设计参数 ===== */
#define PCB_MIN_LAYERS          4      /* 最少层数 */
#define GROUND_IMPEDANCE_MAX_OHM 0.1f  /* 接地阻抗 < 0.1Ω */
#define SHIELD_EFFECTIVENESS_MIN_DB 40  /* 屏蔽效能 > 40dB */

/* 分区距离要求 */
#define NOISE_TO_COMPUTE_MM     30     /* 高噪声区→计算区 间距 */
#define COMPUTE_TO_SENSITIVE_MM 20     /* 计算区→敏感区 间距 */

/* ===== PCB 层叠配置 ===== */
typedef struct {
    int num_layers;              /* 层数 */
    int has_continuous_gnd;      /* 是否有连续地平面 */
    int has_power_plane;         /* 是否有电源平面 */
    float dielectric_thickness_mm; /* 介质厚度 */
    float copper_weight_oz;      /* 铜厚 (oz) */
    int layer_stack[16];         /* 层叠顺序 (0=SIG, 1=GND, 2=PWR) */
} pcb_stackup_t;

/* ===== 滤波配置 ===== */
typedef struct {
    int has_pi_filter;           /* π 型滤波 */
    float cutoff_freq_khz;       /* 截止频率 */
    int has_common_mode_choke;   /* 共模扼流圈 */
    float cm_impedance_at_100mhz_ohm; /* 100MHz 共模阻抗 */
    int has_ferrite_bead;        /* 磁珠 (电机相线) */
} filter_config_t;

/* ===== 接地配置 ===== */
typedef struct {
    int has_star_ground;         /* 单点接地 */
    int has_split_analog_digital; /* 模拟/数字地分割 */
    float ground_impedance_ohm;  /* 接地阻抗 (Ω) */
    int has_chassis_ground;      /* 外壳接地 */
    float chassis_to_gnd_resistance_ohm; /* 外壳→地电阻 */
} grounding_config_t;

/* ===== EMC 设计检查结果 ===== */
typedef struct {
    pcb_stackup_t pcb;
    filter_config_t filter;
    grounding_config_t ground;
    int has_metal_shielding;     /* 金属屏蔽罩 */
    int has_spread_spectrum;     /* PWM 扩频 */
    int has_ferrite_on_motor;    /* 电机相线磁环 */
    int all_pass;                /* 全部通过 */
} emc_check_result_t;

/* ===== 公开 API ===== */

/**
 * @brief EMC 设计检查
 *
 * 逐项检查 EMC 设计是否符合规范。
 *
 * @param result 输出检查结果
 * @return QOO_OK 全部通过, QOO_ERROR 有未通过项
 */
int qoo_emc_design_check(emc_check_result_t *result)
{
    int pass = 1;

    printf("===== EMC 设计检查 =====\n");

    /* 1. PCB 层叠检查 */
    printf("\n[PCB 层叠]\n");
    if (result->pcb.num_layers < PCB_MIN_LAYERS) {
        printf("  FAIL: 层数 %d < %d (最低要求)\n",
               result->pcb.num_layers, PCB_MIN_LAYERS);
        pass = 0;
    } else {
        printf("  PASS: 层数 %d ≥ %d\n", result->pcb.num_layers, PCB_MIN_LAYERS);
    }

    if (!result->pcb.has_continuous_gnd) {
        printf("  FAIL: 缺少连续地平面\n");
        pass = 0;
    } else {
        printf("  PASS: 有连续地平面\n");
    }

    /* 2. 屏蔽检查 */
    printf("\n[屏蔽]\n");
    if (!result->has_metal_shielding) {
        printf("  FAIL: 关键模组缺少金属屏蔽罩\n");
        pass = 0;
    } else {
        printf("  PASS: 有金属屏蔽罩\n");
    }

    /* 3. 滤波检查 */
    printf("\n[滤波]\n");
    if (!result->filter.has_pi_filter) {
        printf("  FAIL: 电源入口缺少 π 型滤波\n");
        pass = 0;
    } else {
        printf("  PASS: 电源入口 π 型滤波 (fc=%.0fkHz)\n",
               result->filter.cutoff_freq_khz);
    }

    if (!result->filter.has_common_mode_choke) {
        printf("  FAIL: 缺少共模扼流圈\n");
        pass = 0;
    } else {
        printf("  PASS: 共模扼流圈 (%.0fΩ @ 100MHz)\n",
               result->filter.cm_impedance_at_100mhz_ohm);
    }

    /* 4. 接地检查 */
    printf("\n[接地]\n");
    if (result->ground.ground_impedance_ohm > GROUND_IMPEDANCE_MAX_OHM) {
        printf("  FAIL: 接地阻抗 %.3fΩ > %.3fΩ\n",
               result->ground.ground_impedance_ohm, GROUND_IMPEDANCE_MAX_OHM);
        pass = 0;
    } else {
        printf("  PASS: 接地阻抗 %.3fΩ < %.3fΩ\n",
               result->ground.ground_impedance_ohm, GROUND_IMPEDANCE_MAX_OHM);
    }

    if (!result->ground.has_chassis_ground) {
        printf("  FAIL: 外壳未接地\n");
        pass = 0;
    } else {
        printf("  PASS: 外壳可靠接地\n");
    }

    if (!result->ground.has_split_analog_digital) {
        printf("  WARN: 建议数字/模拟地分割\n");
    }

    /* 5. 电机 EMI */
    printf("\n[电机 EMI]\n");
    if (!result->has_ferrite_on_motor) {
        printf("  FAIL: 电机相线缺少磁环\n");
        pass = 0;
    } else {
        printf("  PASS: 电机相线磁环\n");
    }

    if (!result->has_spread_spectrum) {
        printf("  WARN: 建议 PWM 扩频以降低 EMI\n");
    } else {
        printf("  PASS: PWM 扩频使能\n");
    }

    /* 6. 分区隔离检查 */
    printf("\n[分区隔离]\n");
    printf("  INFO: 高噪声区 (电机驱动/DC-DC) → 隔离带 → 计算区 (SoC) → 隔离带 → 敏感区 (传感器/射频)\n");

    result->all_pass = pass;
    printf("\n结论: %s\n", pass ? "ALL PASS ✓" : "HAS FAILURES ✗");
    printf("=======================\n");

    return pass ? QOO_OK : QOO_ERROR;
}

/**
 * @brief 打印 EMC 设计检查清单
 */
void qoo_emc_print_checklist(void)
{
    printf("\n===== EMC 设计检查清单 =====\n");
    printf("PCB 设计:\n");
    printf("  [ ] ≥ 4 层 PCB, 完整地平面\n");
    printf("  [ ] 高速差分对等长 ±5mil (PCIe) / ±2mil (MIPI)\n");
    printf("  [ ] 参考层连续, 无跨分割\n");
    printf("\n屏蔽:\n");
    printf("  [ ] 关键模组金属屏蔽罩\n");
    printf("  [ ] 屏蔽效能 > 40dB\n");
    printf("\n滤波:\n");
    printf("  [ ] 电源入口 π 型滤波\n");
    printf("  [ ] 共模扼流圈\n");
    printf("  [ ] 电机相线磁环\n");
    printf("\n接地:\n");
    printf("  [ ] 单点接地\n");
    printf("  [ ] 数字/模拟地分割\n");
    printf("  [ ] 金属外壳可靠接地 (接地阻抗 < 0.1Ω)\n");
    printf("\nEMI 抑制:\n");
    printf("  [ ] 驱动器 PWM 扩频\n");
    printf("  [ ] 关键信号串联阻尼电阻\n");
    printf("\nEMC 测试 (CISPR 32 / IEC 61000):\n");
    printf("  [ ] 辐射发射 Class B (30MHz~6GHz)\n");
    printf("  [ ] 传导发射 Class B (150kHz~30MHz)\n");
    printf("  [ ] ESD ±8kV 接触 / ±15kV 空气 (Level 4)\n");
    printf("  [ ] 辐射抗扰度 10V/m (Level 3)\n");
    printf("  [ ] EFT ±2kV 电源 / ±1kV 信号 (Level 3)\n");
    printf("============================\n\n");
}
