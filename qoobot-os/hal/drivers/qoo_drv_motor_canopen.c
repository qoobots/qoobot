/**
 * @file qoo_drv_motor_canopen.c
 * @brief CANopen 关节电机驱动参考实现 (CiA 402)
 *
 * 支持位置/速度/力矩/周期同步位置模式
 * 通信: CAN FD @ 5Mbps
 * 协议: CANopen CiA 301 + CiA 402
 */

#include "../hal/qoo_hal_actuator.h"
#include "../hal/qoo_hal_comm.h"
#include "../hal/qoo_hal_time.h"
#include <string.h>
#include <stddef.h>

/*===========================================================================
 * CANopen 常量
 *===========================================================================*/

/* NMT 命令 */
#define NMT_START_NODE          0x01
#define NMT_STOP_NODE           0x02
#define NMT_ENTER_PREOP         0x80
#define NMT_RESET_NODE          0x81
#define NMT_RESET_COMM          0x82

/* SDO 命令码 */
#define SDO_RX_UPLOAD_REQ       0x40
#define SDO_TX_DOWNLOAD_REQ     0x22
#define SDO_TX_DOWNLOAD_REQ_4B  0x23
#define SDO_RX_ABORT            0x80

/* PDO COB-ID 偏移 */
#define PDO1_TX_COBID_OFFSET    0x180
#define PDO1_RX_COBID_OFFSET    0x200

/* CiA 402 对象字典 */
#define OD_CONTROLWORD          0x6040
#define OD_STATUSWORD           0x6041
#define OD_MODES_OF_OPERATION   0x6060
#define OD_MODES_OF_OPERATION_DISPLAY 0x6061
#define OD_TARGET_POSITION      0x607A
#define OD_TARGET_VELOCITY      0x60FF
#define OD_TARGET_TORQUE        0x6071
#define OD_POSITION_ACTUAL      0x6064
#define OD_VELOCITY_ACTUAL      0x606C
#define OD_TORQUE_ACTUAL        0x6077
#define OD_CURRENT_ACTUAL       0x6078
#define OD_TEMP_MOTOR           0x2000  /* 厂商特定 */

/* CiA 402 控制字 */
#define CW_SHUTDOWN             0x0006
#define CW_SWITCH_ON            0x0007
#define CW_ENABLE_OPERATION     0x000F
#define CW_QUICK_STOP           0x0002
#define CW_DISABLE_VOLTAGE      0x0000
#define CW_FAULT_RESET          0x0080

/* CiA 402 状态字位 */
#define SW_READY_TO_SWITCH_ON   0x0001
#define SW_SWITCHED_ON          0x0002
#define SW_OPERATION_ENABLED    0x0004
#define SW_FAULT                0x0008
#define SW_VOLTAGE_ENABLED      0x0010
#define SW_QUICK_STOP           0x0020
#define SW_WARNING              0x0080
#define SW_TARGET_REACHED       0x0400

/* 操作模式 */
#define MODE_PROFILE_POSITION   1
#define MODE_PROFILE_VELOCITY   3
#define MODE_PROFILE_TORQUE     4
#define MODE_CYCLIC_SYNC_POS    8
#define MODE_CYCLIC_SYNC_VEL    9
#define MODE_CYCLIC_SYNC_TORQUE 10

/*===========================================================================
 * 电机驱动上下文
 *===========================================================================*/

typedef struct {
    uint32_t motor_id;
    uint32_t can_bus_id;
    uint32_t node_id;           /**< CANopen 节点 ID */
    qoo_motor_config_t config;
    qoo_motor_state_t state;
    qoo_motor_feedback_t last_fb;
    bool enabled;
} motor_canopen_ctx_t;

#define MAX_MOTORS 32
static motor_canopen_ctx_t g_motors[MAX_MOTORS];
static uint32_t g_motor_count = 0;

/*===========================================================================
 * CAN 帧构建辅助
 *===========================================================================*/

/** 计算 CAN COB-ID (功能码 + 节点 ID) */
static uint32_t make_cobid(uint32_t function_code, uint32_t node_id) {
    return function_code + node_id;
}

/** 发送 NMT 命令 */
static qoo_error_t nmt_command(uint32_t bus_id, uint32_t node_id, uint8_t cmd) {
    qoo_can_frame_t frame;
    frame.id = 0x000; /* NMT COB-ID */
    frame.is_extended = false;
    frame.is_fd = false;
    frame.dlc = 2;
    frame.data[0] = cmd;
    frame.data[1] = node_id;
    return qoo_hal_can_send(bus_id, &frame);
}

/** 通过 SDO 读取 32 位对象字典 */
static qoo_error_t sdo_read32(uint32_t bus_id, uint32_t node_id,
    uint16_t index, uint8_t subindex, uint32_t *value)
{
    qoo_can_frame_t frame;
    frame.id = make_cobid(0x600, node_id); /* SDO RX */
    frame.is_extended = false;
    frame.is_fd = false;
    frame.dlc = 8;
    frame.data[0] = SDO_RX_UPLOAD_REQ;
    frame.data[1] = index & 0xFF;
    frame.data[2] = (index >> 8) & 0xFF;
    frame.data[3] = subindex;
    frame.data[4] = 0; frame.data[5] = 0;
    frame.data[6] = 0; frame.data[7] = 0;

    /* 实际应等待 SDO TX 响应, 这里简化为同步调用 */
    qoo_error_t err = qoo_hal_can_send(bus_id, &frame);
    *value = 0;
    (void)value; /* 实际需解析响应 */
    return err;
}

/** 通过 SDO 写入 32 位对象字典 */
static qoo_error_t sdo_write32(uint32_t bus_id, uint32_t node_id,
    uint16_t index, uint8_t subindex, uint32_t value)
{
    qoo_can_frame_t frame;
    frame.id = make_cobid(0x600, node_id);
    frame.is_extended = false;
    frame.is_fd = false;
    frame.dlc = 8;
    frame.data[0] = SDO_TX_DOWNLOAD_REQ_4B;
    frame.data[1] = index & 0xFF;
    frame.data[2] = (index >> 8) & 0xFF;
    frame.data[3] = subindex;
    frame.data[4] = value & 0xFF;
    frame.data[5] = (value >> 8) & 0xFF;
    frame.data[6] = (value >> 16) & 0xFF;
    frame.data[7] = (value >> 24) & 0xFF;
    return qoo_hal_can_send(bus_id, &frame);
}

/** 通过 PDO 发送控制指令 (周期同步位置模式) */
static qoo_error_t pdo_send_csp(uint32_t bus_id, uint32_t node_id,
    uint16_t controlword, int32_t target_position)
{
    qoo_can_frame_t frame;
    frame.id = make_cobid(PDO1_RX_COBID_OFFSET, node_id);
    frame.is_extended = false;
    frame.is_fd = false;
    frame.dlc = 6;
    /* 控制字 (2 bytes) */
    frame.data[0] = controlword & 0xFF;
    frame.data[1] = (controlword >> 8) & 0xFF;
    /* 目标位置 (4 bytes) */
    memcpy(&frame.data[2], &target_position, 4);
    return qoo_hal_can_send(bus_id, &frame);
}

/*===========================================================================
 * 电机状态机
 *===========================================================================*/

/** 状态机转换表 (CiA 402) */
static qoo_error_t motor_state_machine(motor_canopen_ctx_t *ctx,
    qoo_motor_state_t target_state)
{
    uint16_t cw;
    uint32_t sw;

    /* 读取当前状态字 */
    sdo_read32(ctx->can_bus_id, ctx->node_id, OD_STATUSWORD, 0, &sw);

    /* 故障复位 */
    if (sw & SW_FAULT) {
        cw = CW_FAULT_RESET;
        pdo_send_csp(ctx->can_bus_id, ctx->node_id, cw, 0);
        return QOO_OK;
    }

    switch (target_state) {
        case QOO_MOTOR_STATE_SWITCH_ON_DISABLED:
            cw = CW_DISABLE_VOLTAGE;
            break;
        case QOO_MOTOR_STATE_READY:
            cw = CW_SHUTDOWN;
            break;
        case QOO_MOTOR_STATE_SWITCHED_ON:
            cw = CW_SWITCH_ON;
            break;
        case QOO_MOTOR_STATE_OPERATION_ENABLED:
            cw = CW_ENABLE_OPERATION;
            break;
        case QOO_MOTOR_STATE_QUICK_STOP:
            cw = CW_QUICK_STOP;
            break;
        default:
            return QOO_ERROR_INVALID_PARAM;
    }

    pdo_send_csp(ctx->can_bus_id, ctx->node_id, cw, 0);

    /* 等待状态字变化 (实际应异步处理) */
    /* ... */

    ctx->state = target_state;
    return QOO_OK;
}

/*===========================================================================
 * 电机驱动公共接口实现
 *===========================================================================*/

qoo_error_t qoo_hal_motor_register(uint32_t motor_id, const qoo_motor_config_t *config)
{
    if (g_motor_count >= MAX_MOTORS) return QOO_ERROR_BUSY;

    motor_canopen_ctx_t *ctx = &g_motors[g_motor_count];
    ctx->motor_id = motor_id;
    ctx->node_id = config->can_id & 0x7F; /* CANopen 节点 ID 7bit */
    ctx->can_bus_id = 0; /* 默认 CAN 总线 0 */
    memcpy(&ctx->config, config, sizeof(qoo_motor_config_t));
    ctx->state = QOO_MOTOR_STATE_NOT_READY;
    ctx->enabled = false;

    g_motor_count++;

    /* 发送 NMT 重置节点进入预操作 */
    nmt_command(ctx->can_bus_id, ctx->node_id, NMT_RESET_COMM);
    /* 等待启动... */

    return QOO_OK;
}

qoo_error_t qoo_hal_motor_enable(uint32_t motor_id)
{
    motor_canopen_ctx_t *ctx = NULL;
    for (uint32_t i = 0; i < g_motor_count; i++) {
        if (g_motors[i].motor_id == motor_id) { ctx = &g_motors[i]; break; }
    }
    if (!ctx) return QOO_ERROR_NOT_FOUND;

    /* 发送 NMT 启动节点 */
    nmt_command(ctx->can_bus_id, ctx->node_id, NMT_START_NODE);

    /* 设置操作模式为 CSP (周期同步位置) */
    sdo_write32(ctx->can_bus_id, ctx->node_id, OD_MODES_OF_OPERATION, 0, MODE_CYCLIC_SYNC_POS);

    /* 状态机转换: NOT_READY → SWITCHED_ON → OPERATION_ENABLED */
    motor_state_machine(ctx, QOO_MOTOR_STATE_SWITCHED_ON);
    motor_state_machine(ctx, QOO_MOTOR_STATE_OPERATION_ENABLED);

    ctx->enabled = true;
    return QOO_OK;
}

qoo_error_t qoo_hal_motor_disable(uint32_t motor_id)
{
    motor_canopen_ctx_t *ctx = NULL;
    for (uint32_t i = 0; i < g_motor_count; i++) {
        if (g_motors[i].motor_id == motor_id) { ctx = &g_motors[i]; break; }
    }
    if (!ctx) return QOO_ERROR_NOT_FOUND;

    motor_state_machine(ctx, QOO_MOTOR_STATE_SWITCH_ON_DISABLED);
    ctx->enabled = false;
    return QOO_OK;
}

qoo_error_t qoo_hal_motor_set_command(uint32_t motor_id, const qoo_motor_command_t *cmd)
{
    motor_canopen_ctx_t *ctx = NULL;
    for (uint32_t i = 0; i < g_motor_count; i++) {
        if (g_motors[i].motor_id == motor_id) { ctx = &g_motors[i]; break; }
    }
    if (!ctx || !ctx->enabled) return QOO_ERROR_INVALID_PARAM;

    /* 将目标位置 (rad) 转换为编码器单位 */
    float gear_ratio = ctx->config.gear_ratio;
    int32_t enc_pos = (int32_t)(cmd->target_position * gear_ratio /
        (2.0f * 3.14159265359f) * 10000.0f); /* 10000 counts/rev */

    /* 力矩限制通过 SDO 设置 */
    if (cmd->torque_limit > 0) {
        uint32_t torque_limit_mNm = (uint32_t)(cmd->torque_limit * 1000.0f);
        sdo_write32(ctx->can_bus_id, ctx->node_id, 0x6072, 0, torque_limit_mNm); /* Max Torque */
    }

    /* 通过 PDO 发送周期同步位置指令 */
    return pdo_send_csp(ctx->can_bus_id, ctx->node_id,
        CW_ENABLE_OPERATION, enc_pos);
}

qoo_error_t qoo_hal_motor_set_commands_batch(
    const uint32_t *motor_ids, const qoo_motor_command_t *cmds, uint32_t count)
{
    /* 批量同步发送 (利用 CAN FD 高带宽) */
    for (uint32_t i = 0; i < count; i++) {
        qoo_hal_motor_set_command(motor_ids[i], &cmds[i]);
    }
    return QOO_OK;
}

qoo_error_t qoo_hal_motor_get_feedback(uint32_t motor_id, qoo_motor_feedback_t *fb)
{
    motor_canopen_ctx_t *ctx = NULL;
    for (uint32_t i = 0; i < g_motor_count; i++) {
        if (g_motors[i].motor_id == motor_id) { ctx = &g_motors[i]; break; }
    }
    if (!ctx) return QOO_ERROR_NOT_FOUND;

    /* 通过 SDO 或 PDO 映射读取反馈 */
    uint32_t pos_raw, vel_raw, torque_raw, current_raw, temp_raw;
    uint32_t sw;

    sdo_read32(ctx->can_bus_id, ctx->node_id, OD_POSITION_ACTUAL, 0, &pos_raw);
    sdo_read32(ctx->can_bus_id, ctx->node_id, OD_VELOCITY_ACTUAL, 0, &vel_raw);
    sdo_read32(ctx->can_bus_id, ctx->node_id, OD_TORQUE_ACTUAL, 0, &torque_raw);
    sdo_read32(ctx->can_bus_id, ctx->node_id, OD_CURRENT_ACTUAL, 0, &current_raw);
    sdo_read32(ctx->can_bus_id, ctx->node_id, OD_TEMP_MOTOR, 0, &temp_raw);
    sdo_read32(ctx->can_bus_id, ctx->node_id, OD_STATUSWORD, 0, &sw);

    /* 编码器单位 → 物理单位 */
    float gear_ratio = ctx->config.gear_ratio;
    fb->position = (int32_t)pos_raw * 2.0f * 3.14159265359f / (10000.0f * gear_ratio);
    fb->velocity = (int32_t)vel_raw * 2.0f * 3.14159265359f / (10000.0f * gear_ratio);
    fb->torque = (int32_t)torque_raw * ctx->config.torque_constant / 1000.0f; /* mNm → Nm */
    fb->motor_current = current_raw / 1000.0f; /* mA → A */
    fb->temperature = temp_raw / 10.0f; /* 0.1°C → °C */
    fb->timestamp = qoo_hal_time_now();

    /* 状态字解析 */
    fb->error_flags = (sw & SW_FAULT) ? 0x01 : 0x00;
    if (sw & SW_OPERATION_ENABLED)
        fb->state = QOO_MOTOR_STATE_OPERATION_ENABLED;
    else if (sw & SW_SWITCHED_ON)
        fb->state = QOO_MOTOR_STATE_SWITCHED_ON;
    else
        fb->state = QOO_MOTOR_STATE_SWITCH_ON_DISABLED;

    memcpy(&ctx->last_fb, fb, sizeof(qoo_motor_feedback_t));
    return QOO_OK;
}

qoo_error_t qoo_hal_motor_get_feedbacks_batch(
    const uint32_t *motor_ids, qoo_motor_feedback_t *fbs, uint32_t count)
{
    for (uint32_t i = 0; i < count; i++) {
        qoo_hal_motor_get_feedback(motor_ids[i], &fbs[i]);
    }
    return QOO_OK;
}

qoo_error_t qoo_hal_motor_emergency_stop_all(void)
{
    for (uint32_t i = 0; i < g_motor_count; i++) {
        /* 发送急停命令 */
        pdo_send_csp(g_motors[i].can_bus_id, g_motors[i].node_id,
            CW_QUICK_STOP, 0);
        g_motors[i].state = QOO_MOTOR_STATE_QUICK_STOP;
        g_motors[i].enabled = false;
    }
    return QOO_OK;
}
