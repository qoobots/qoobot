/**
 * @file qoo_hil_test.c
 * @brief QooBot 硬件在环 (HIL) 测试框架参考实现
 *
 * 符合 docs/08测试与验证规范.md §2 规范
 *
 * HIL 测试平台架构:
 *   仿真主机 (x86)                   待测硬件 (DUT)
 *   物理引擎 (Isaac/MuJoCo) ──► 计算板 (SoC) → 执行器 (电机)
 *   传感器信号模拟           ◄── 传感器接口 ← 编码器
 *   故障注入引擎             ──► 安全 MCU 独立验证
 *
 * 传感器信号模拟:
 *   RGB-D 相机: 虚拟场景渲染 + 深度图 → MIPI CSI 回环/USB3
 *   LiDAR: 点云射线投射 → UDP 回放/SPI 注入
 *   IMU: 6/9轴运动数据 → SPI 回放
 *   麦克风阵列: 空间音频合成 → I2S/TDM 回放
 *   关节编码器: 运动学正解算 → CAN FD/EtherCAT 虚拟从站
 *
 * 故障注入矩阵:
 *   - 传感器数据中断 (预期: 500ms 内检测)
 *   - 传感器数据异常 (预期: 误检率 < 1%)
 *   - 电机通信中断 (预期: 响应 < 100ms)
 *   - 电源电压跌落 (预期: 过渡无数据丢失)
 *   - 安全回路断开 (预期: 响应 < 20ms)
 *
 * 平台：Linux (测试框架)
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <errno.h>
#include <time.h>

#include "../hal/qoo_hal.h"

/* ===== HIL 测试用例类型 ===== */
typedef enum {
    HIL_TEST_SENSOR_PIPELINE = 0,
    HIL_TEST_MOTION_CONTROL  = 1,
    HIL_TEST_SAFETY_SYSTEM   = 2,
    HIL_TEST_POWER_SYSTEM    = 3,
} hil_test_category_t;

/* ===== HIL 测试结果 ===== */
typedef enum {
    HIL_RESULT_PASS   = 0,
    HIL_RESULT_FAIL   = 1,
    HIL_RESULT_SKIP   = 2,
    HIL_RESULT_TIMEOUT = 3,
} hil_test_result_t;

/* ===== 故障注入类型 ===== */
typedef enum {
    FAULT_SENSOR_DROPOUT   = 0,  /* 传感器数据中断 */
    FAULT_SENSOR_NOISE     = 1,  /* 传感器数据异常 */
    FAULT_MOTOR_COMM_LOSS  = 2,  /* 电机通信中断 */
    FAULT_MOTOR_OVERCURRENT = 3, /* 电机过流 */
    FAULT_POWER_BROWNOUT   = 4,  /* 电源电压跌落 */
    FAULT_OVER_TEMP        = 5,  /* 过热 */
    FAULT_SAFETY_LOOP_BREAK = 6, /* 安全回路断开 */
    FAULT_CLOCK_SYNC_LOSS  = 7,  /* 时钟同步丢失 */
} fault_type_t;

/* ===== HIL 测试用例 ===== */
typedef struct {
    const char *name;
    hil_test_category_t category;
    const char *description;
    double pass_criteria;         /* 通过标准 */
    const char *unit;
    double measured_value;        /* 实测值 */
    hil_test_result_t result;
    uint64_t duration_us;         /* 执行时间 */
    const char *error_msg;        /* 错误信息 */
} hil_test_case_t;

/* ===== 故障注入配置 ===== */
typedef struct {
    fault_type_t type;
    const char *name;
    const char *injection_method;
    const char *expected_response;
    double max_response_time_ms;  /* 最大响应时间 */
} fault_injection_config_t;

static const fault_injection_config_t g_fault_configs[] = {
    { FAULT_SENSOR_DROPOUT,   "传感器数据中断",  "停止数据流",
      "500ms 内检测，切换到降级模式", 500 },
    { FAULT_SENSOR_NOISE,     "传感器数据异常",  "注入噪声/偏移",
      "异常检测触发，数据被丢弃",     0,  /* 误检率 < 1% */ },
    { FAULT_MOTOR_COMM_LOSS,  "电机通信中断",    "断开 CAN/EtherCAT",
      "安全 MCU 触发抱闸",            100 },
    { FAULT_MOTOR_OVERCURRENT,"电机过流",       "注入过流信号",
      "安全 MCU 切断驱动使能",        50 },
    { FAULT_POWER_BROWNOUT,   "电源电压跌落",    "降低供电电压",
      "BMS 触发低功耗模式/安全关机",  0 },
    { FAULT_OVER_TEMP,        "计算板过热",      "模拟温度传感器超限",
      "降频→安全停止",               0 },
    { FAULT_SAFETY_LOOP_BREAK,"安全回路断开",    "断开急停回路",
      "立即切断动力，抱闸制动",       20 },
    { FAULT_CLOCK_SYNC_LOSS,  "时钟同步丢失",    "断开 gPTP 同步",
      "降级为本地时间戳，告警上报",   1000 },
};

/* ===== HIL 测试报告 ===== */
typedef struct {
    hil_test_case_t cases[50];
    int num_cases;
    int passed;
    int failed;
    int skipped;
    uint64_t total_duration_us;
    char report_file[256];
} hil_test_report_t;

static hil_test_report_t g_hil_report;

/* ===== 公开 API ===== */

/**
 * @brief 初始化 HIL 测试框架
 * @param report_file 报告文件路径
 * @return QOO_OK 成功
 */
int qoo_hil_init(const char *report_file)
{
    memset(&g_hil_report, 0, sizeof(g_hil_report));
    if (report_file) strncpy(g_hil_report.report_file, report_file, 255);

    printf("[HIL] HIL 测试框架初始化\n");
    return QOO_OK;
}

/**
 * @brief 注册 HIL 测试用例
 */
void qoo_hil_register_test(const char *name, hil_test_category_t category,
                            const char *description, double pass_criteria,
                            const char *unit)
{
    hil_test_report_t *report = &g_hil_report;
    if (report->num_cases >= 50) return;

    hil_test_case_t *tc = &report->cases[report->num_cases++];
    tc->name = name;
    tc->category = category;
    tc->description = description;
    tc->pass_criteria = pass_criteria;
    tc->unit = unit;
    tc->result = HIL_RESULT_SKIP;
}

/**
 * @brief 运行单个 HIL 测试
 */
hil_test_result_t qoo_hil_run_test(int index, double measured_value)
{
    hil_test_report_t *report = &g_hil_report;
    if (index < 0 || index >= report->num_cases) return HIL_RESULT_SKIP;

    hil_test_case_t *tc = &report->cases[index];
    tc->measured_value = measured_value;

    if (measured_value <= tc->pass_criteria) {
        tc->result = HIL_RESULT_PASS;
        report->passed++;
    } else {
        tc->result = HIL_RESULT_FAIL;
        report->failed++;
    }

    return tc->result;
}

/**
 * @brief 故障注入
 *
 * @param fault_type 故障类型
 * @param duration_ms 故障持续时间 (0=永久)
 * @return QOO_OK 注入成功
 */
int qoo_hil_inject_fault(fault_type_t fault_type, uint32_t duration_ms)
{
    const fault_injection_config_t *cfg = NULL;
    for (int i = 0; i < (int)(sizeof(g_fault_configs) / sizeof(g_fault_configs[0])); i++) {
        if (g_fault_configs[i].type == fault_type) {
            cfg = &g_fault_configs[i];
            break;
        }
    }
    if (!cfg) return QOO_ERROR_PARAM;

    printf("[HIL] 故障注入: %s (持续 %ums)\n", cfg->name, duration_ms);
    printf("      方式: %s\n", cfg->injection_method);
    printf("      预期: %s\n", cfg->expected_response);

    /* 实际注入逻辑 (根据类型):
     * FAULT_SENSOR_DROPOUT: 停止数据流发送
     * FAULT_SENSOR_NOISE: 修改数据包添加噪声
     * FAULT_MOTOR_COMM_LOSS: 断开 CAN socket
     * etc.
     */

    return QOO_OK;
}

/**
 * @brief 运行标准 HIL 测试套件
 *
 * 包含 docs/08测试与验证规范.md §2.4 定义的全部测试用例:
 * - sensor_pipeline: 延迟/同步/吞吐量
 * - motion_control: 位置跟踪/速度平滑/力矩响应/急停
 * - safety_system: 碰撞检测/力超限/看门狗
 * - power_system: 电压跌落/热插拔/满载
 */
void qoo_hil_run_standard_suite(void)
{
    printf("\n===== HIL 标准测试套件 =====\n");

    /* 感知管线 */
    qoo_hil_register_test("感知延迟",      HIL_TEST_SENSOR_PIPELINE,
                           "端到端感知延迟 < 50ms", 50, "ms");
    qoo_hil_register_test("传感器同步",    HIL_TEST_SENSOR_PIPELINE,
                           "多传感器时间戳偏差 < 100μs", 0.1, "ms");
    qoo_hil_register_test("感知吞吐量",    HIL_TEST_SENSOR_PIPELINE,
                           "视觉+LiDAR满带宽不丢帧", 0, "frames lost");

    /* 运动控制 */
    qoo_hil_register_test("位置跟踪",      HIL_TEST_MOTION_CONTROL,
                           "位置跟踪误差 < 0.1°", 0.1, "deg");
    qoo_hil_register_test("速度平滑",      HIL_TEST_MOTION_CONTROL,
                           "速度波动 < 5%", 5, "%");
    qoo_hil_register_test("力矩响应",      HIL_TEST_MOTION_CONTROL,
                           "力矩响应时间 < 5ms", 5, "ms");
    qoo_hil_register_test("急停",          HIL_TEST_MOTION_CONTROL,
                           "急停到静止 < 200ms", 200, "ms");

    /* 安全系统 */
    qoo_hil_register_test("碰撞检测",      HIL_TEST_SAFETY_SYSTEM,
                           "碰撞检测延迟 < 10ms", 10, "ms");
    qoo_hil_register_test("力超限保护",    HIL_TEST_SAFETY_SYSTEM,
                           "力超限保护响应 < 5ms", 5, "ms");
    qoo_hil_register_test("看门狗",        HIL_TEST_SAFETY_SYSTEM,
                           "主控心跳丢失→安全停止 < 50ms", 50, "ms");

    /* 电源系统 */
    qoo_hil_register_test("电压跌落恢复",  HIL_TEST_POWER_SYSTEM,
                           "电压跌落恢复无重启", 0, "restarts");
    qoo_hil_register_test("热插拔",        HIL_TEST_POWER_SYSTEM,
                           "热插拔传感器不触发保护", 0, "faults");
    qoo_hil_register_test("满载运行",      HIL_TEST_POWER_SYSTEM,
                           "满载运行2h不过热降频", 0, "throttles");

    printf("注册 %d 个测试用例\n", g_hil_report.num_cases);
    printf("==========================\n\n");
}

/**
 * @brief 生成 HIL 测试报告
 */
void qoo_hil_generate_report(void)
{
    hil_test_report_t *report = &g_hil_report;

    printf("\n========================================\n");
    printf("         HIL 硬件在环测试报告\n");
    printf("========================================\n");

    for (int i = 0; i < report->num_cases; i++) {
        hil_test_case_t *tc = &report->cases[i];
        const char *result_str = tc->result == HIL_RESULT_PASS ? "PASS" :
                                  tc->result == HIL_RESULT_FAIL ? "FAIL" : "SKIP";

        printf("[%s] %-20s: %.2f %s (标准: <%.2f %s)\n",
               result_str, tc->name,
               tc->measured_value, tc->unit,
               tc->pass_criteria, tc->unit);
    }

    printf("----------------------------------------\n");
    printf("通过: %d, 失败: %d, 跳过: %d\n",
           report->passed, report->failed, report->skipped);
    printf("========================================\n\n");
}

/**
 * @brief 释放 HIL 测试框架
 */
int qoo_hil_deinit(void)
{
    memset(&g_hil_report, 0, sizeof(g_hil_report));
    return QOO_OK;
}
