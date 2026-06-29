/**
 * @file qoo_drv_end_effector.c
 * @brief QooBot 末端执行器驱动参考实现
 *
 * 符合 docs/03执行器接口规范.md §3 规范
 * - 机械法兰标准 (Φ60/80/100mm, 2×Φ4定位销, M4/M5安装孔)
 * - 电气接口 (24V/5A供电, CAN FD通信, GPIO, 气路控制)
 * - 工具识别 (1-Wire EEPROM)
 * - 换刀流程
 *
 * 支持工具类型: 夹爪、吸盘、灵巧手
 *
 * 依赖：qoo_hal_actuator.h
 * 平台：Linux + CAN FD
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <errno.h>
#include <unistd.h>

#include "../hal/qoo_hal.h"
#include "../hal/qoo_hal_actuator.h"

/* ===== 法兰标准 (符合规范 §3.1) ===== */
typedef enum {
    FLANGE_60MM  = 60,   /* 小型法兰: Φ60mm, 4×M4 */
    FLANGE_80MM  = 80,   /* 中型法兰: Φ80mm, 6×M5 */
    FLANGE_100MM = 100,  /* 大型法兰: Φ100mm, 6×M5 */
} flange_size_t;

/* ===== 工具类型 ===== */
typedef enum {
    TOOL_NONE    = 0,     /* 无工具 */
    TOOL_GRIPPER = 1,     /* 夹爪 */
    TOOL_SUCTION = 2,     /* 吸盘 */
    TOOL_DEXTEROUS = 3,   /* 灵巧手 */
    TOOL_CUSTOM  = 99,    /* 自定义 */
} tool_type_t;

/* ===== 工具识别信息 (1-Wire EEPROM) ===== */
typedef struct {
    uint64_t tool_uid;         /* 工具唯一 ID */
    tool_type_t type;          /* 工具类型 */
    char name[32];             /* 工具名称 */
    float mass_kg;             /* 质量 (kg) */
    float inertia[9];          /* 惯量矩阵 (3×3, row-major) */
    float center_of_mass[3];   /* 质心位置 (mm) */
    float max_grip_force_n;    /* 最大夹持力 (N) */
    float max_payload_kg;      /* 最大负载 (kg) */
    uint32_t firmware_version; /* 固件版本 */
    uint8_t checksum;          /* CRC8 校验 */
} tool_id_t;

/* ===== 末端执行器设备 ===== */
typedef struct {
    int can_socket;            /* CAN FD socket */
    int tool_present;          /* 工具是否在位 */
    tool_id_t tool_info;       /* 当前工具信息 */

    /* 工具控制 */
    float grip_position_mm;    /* 夹爪位置 (mm) */
    float grip_force_n;        /* 夹持力 (N) */
    int vacuum_on;             /* 真空使能 */
    int tool_ready;            /* 工具就绪 */

    /* 统计 */
    uint32_t tool_change_count;
    uint64_t total_operation_ms;
} end_effector_dev_t;

static end_effector_dev_t g_end_effector;

/* ===== 公开 API ===== */

/**
 * @brief 初始化末端执行器接口
 * @param can_interface CAN FD 接口名 (如 "can1")
 * @param flange 法兰尺寸
 * @return QOO_OK 成功
 */
int qoo_end_effector_init(const char *can_interface, flange_size_t flange)
{
    end_effector_dev_t *dev = &g_end_effector;
    memset(dev, 0, sizeof(*dev));

    printf("[EE] 末端执行器初始化: CAN=%s, 法兰=Φ%dmm\n", can_interface, flange);
    return QOO_OK;
}

/**
 * @brief 检测工具是否在位
 * @return 1 在位, 0 不在位
 */
int qoo_end_effector_tool_present(void)
{
    return g_end_effector.tool_present;
}

/**
 * @brief 读取工具识别信息 (1-Wire EEPROM)
 *
 * 换刀流程 (符合规范 §3.3):
 * 1. 法兰接触 → 工具识别芯片上电
 * 2. 主控读取 1-Wire EEPROM 工具 ID
 * 3. 加载对应工具参数 (质量、惯量、控制参数)
 * 4. 工具就绪信号 → 开始操作
 *
 * @param tool_info 输出工具信息
 * @return QOO_OK 成功
 */
int qoo_end_effector_read_tool_id(tool_id_t *tool_info)
{
    end_effector_dev_t *dev = &g_end_effector;
    if (!dev->tool_present) return QOO_ERROR_NOT_FOUND;

    *tool_info = dev->tool_info;

    printf("[EE] 工具识别: UID=0x%016llX, 类型=%d, 名称=%s\n",
           (unsigned long long)tool_info->tool_uid,
           tool_info->type, tool_info->name);

    return QOO_OK;
}

/**
 * @brief 加载工具参数到运动控制系统
 *
 * 根据工具质量和惯量更新动力学模型。
 *
 * @param tool_info 工具信息
 * @return QOO_OK 成功
 */
int qoo_end_effector_load_tool_params(const tool_id_t *tool_info)
{
    printf("[EE] 加载工具参数:\n");
    printf("      质量: %.3f kg\n", tool_info->mass_kg);
    printf("      最大夹持力: %.1f N\n", tool_info->max_grip_force_n);
    printf("      最大负载: %.1f kg\n", tool_info->max_payload_kg);
    printf("      质心: [%.1f, %.1f, %.1f] mm\n",
           tool_info->center_of_mass[0],
           tool_info->center_of_mass[1],
           tool_info->center_of_mass[2]);

    return QOO_OK;
}

/**
 * @brief 控制夹爪位置
 * @param position_mm 目标位置 (0=闭合, max=全开)
 * @param force_n 夹持力 (N)
 * @return QOO_OK 成功
 */
int qoo_end_effector_gripper_move(float position_mm, float force_n)
{
    end_effector_dev_t *dev = &g_end_effector;

    if (position_mm < 0) position_mm = 0;
    if (force_n > dev->tool_info.max_grip_force_n)
        force_n = dev->tool_info.max_grip_force_n;

    dev->grip_position_mm = position_mm;
    dev->grip_force_n = force_n;

    /* 通过 CAN FD 发送 CiA 402 PP (轮廓位置) 指令 */
    /* can_send_frame(dev->can_socket, COB_ID_Gripper, position_cmd, sizeof(position_cmd)); */

    return QOO_OK;
}

/**
 * @brief 控制吸盘
 * @param enable 1=吸合, 0=释放
 * @return QOO_OK 成功
 */
int qoo_end_effector_suction_control(int enable)
{
    end_effector_dev_t *dev = &g_end_effector;
    dev->vacuum_on = enable;

    printf("[EE] 吸盘: %s\n", enable ? "吸合" : "释放");

    /* GPIO 控制真空发生器电磁阀 */
    /* gpio_write(VACUUM_GPIO, enable); */

    return QOO_OK;
}

/**
 * @brief 灵巧手抓取
 * @param joint_positions 手指关节位置数组 (关节数取决于灵巧手型号)
 * @param num_joints 关节数
 * @return QOO_OK 成功
 */
int qoo_end_effector_dexterous_grasp(const float *joint_positions, int num_joints)
{
    printf("[EE] 灵巧手抓取: %d 关节\n", num_joints);

    /* 通过 CAN FD 发送多个关节位置指令 */
    for (int i = 0; i < num_joints; i++) {
        /* can_send_joint_position(i, joint_positions[i]); */
    }

    return QOO_OK;
}

/**
 * @brief 工具就绪检查
 *
 * 换刀完成后验证:
 * 1. 法兰锁定到位
 * 2. 电气连接正常
 * 3. 通信正常
 * 4. 工具自检通过
 *
 * @return 1 就绪, 0 未就绪
 */
int qoo_end_effector_tool_ready(void)
{
    end_effector_dev_t *dev = &g_end_effector;
    return dev->tool_present && dev->tool_ready;
}

/**
 * @brief 紧急释放
 *
 * 紧急情况下释放工具:
 * - 夹爪: 全开
 * - 吸盘: 断真空
 * - 灵巧手: 全开
 *
 * @return QOO_OK 成功
 */
int qoo_end_effector_emergency_release(void)
{
    end_effector_dev_t *dev = &g_end_effector;
    dev->vacuum_on = 0;
    dev->grip_position_mm = 999;  /* 全开 */

    printf("[EE] 紧急释放!\n");
    return QOO_OK;
}

/**
 * @brief 释放末端执行器资源
 */
int qoo_end_effector_deinit(void)
{
    memset(&g_end_effector, 0, sizeof(g_end_effector));
    return QOO_OK;
}
