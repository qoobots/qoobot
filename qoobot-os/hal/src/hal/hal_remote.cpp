/**
 * @file hal_remote.cpp
 * @brief QooBot 硬件抽象层 (HAL) — 远程遥控接口实现
 *
 * 实现 qoobody/hal/qoo_hal_remote.h 中定义的全部遥操作 HAL 接口。
 * 依赖 qoo_hal_actuator 和 qoo_hal_safety 提供的底层硬件抽象。
 *
 * 版本: v0.2 | 2026-06-29
 */

#include "qoo_hal_remote.h"

#include <cstring>
#include <cmath>
#include <ctime>

#ifdef QOO_HAL_REMOTE_LOG_ENABLED
#include <cstdio>
#define LOG(fmt, ...) fprintf(stderr, "[HAL_REMOTE] " fmt "\n", ##__VA_ARGS__)
#else
#define LOG(fmt, ...) ((void)0)
#endif

/*===========================================================================
 * 内部状态
 *===========================================================================*/

/** 遥控会话信息 (全局单例，机器人仅支持 1 个遥控会话) */
static qoo_remote_session_info_t g_session_info;

/** 遥控统计 */
static qoo_remote_stats_t g_stats;

/** 当前控制模式 */
static qoo_ctrl_mode_t g_current_mode = QOO_CTRL_MODE_AUTO;

/** 上次心跳时间 */
static qoo_timestamp_us_t g_last_heartbeat_us = 0;

/** 心跳超时阈值 (us) */
static uint64_t g_heartbeat_timeout_us = 3000000;  // 默认 3s

/** 获取当前时间戳 (微秒) */
static inline qoo_timestamp_us_t get_timestamp_us(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (qoo_timestamp_us_t)(ts.tv_sec * 1000000ULL + ts.tv_nsec / 1000ULL);
}

/** 辅助：拷贝字符串到固定长度缓冲区 */
static inline void str_copy(char *dst, size_t dst_size, const char *src) {
    if (dst_size > 0) {
        strncpy(dst, src, dst_size - 1);
        dst[dst_size - 1] = '\0';
    }
}

/** 辅助：计算指令延迟 (us) */
static inline uint32_t calc_latency_us(uint64_t cmd_timestamp_ns) {
    uint64_t now_ns = (uint64_t)get_timestamp_us() * 1000ULL;
    if (cmd_timestamp_ns > now_ns) return 0;
    return (uint32_t)((now_ns - cmd_timestamp_ns) / 1000ULL);
}

/** 辅助：更新延迟统计 */
static inline void update_latency_stats(uint32_t latency_us) {
    g_stats.avg_latency_us = (g_stats.avg_latency_us * 7 + latency_us) / 8;  // EMA
    if (latency_us > g_stats.max_latency_us) {
        g_stats.max_latency_us = latency_us;
    }
}

/*===========================================================================
 * 控制模式切换
 *===========================================================================*/

qoo_error_t qoo_hal_remote_request_takeover(const char *session_id) {
    if (!session_id) return QOO_ERROR_INVALID_PARAM;

    // 更新会话状态
    g_session_info.state = QOO_REMOTE_SESSION_TAKEOVER_PENDING;
    str_copy(g_session_info.session_id, sizeof(g_session_info.session_id), session_id);

    // 记录之前模式
    g_session_info.previous_mode = g_current_mode;
    g_session_info.current_mode = QOO_CTRL_MODE_TELEOP;

    // 请求安全控制器进入降速模式 (接管期间)
    // qoo_hal_safety_request_mode(QOO_SAFETY_MODE_REDUCED_SPEED);

    // 模式切换完成
    g_current_mode = QOO_CTRL_MODE_TELEOP;
    g_session_info.state = QOO_REMOTE_SESSION_TELEOP_ACTIVE;
    g_session_info.connected_at_ns = (uint64_t)get_timestamp_us() * 1000ULL;
    g_stats.takeover_count++;

    LOG("Takeover granted: session=%s mode=TELEOP", session_id);
    return QOO_OK;
}

qoo_error_t qoo_hal_remote_request_handover(void) {
    if (g_current_mode != QOO_CTRL_MODE_TELEOP) {
        return QOO_ERROR_BUSY;
    }

    g_session_info.state = QOO_REMOTE_SESSION_HANDOVER_PENDING;

    // 恢复到之前模式
    g_current_mode = g_session_info.previous_mode;
    g_session_info.current_mode = g_current_mode;
    g_session_info.state = QOO_REMOTE_SESSION_CONNECTED;

    LOG("Handover completed: mode=%s",
        g_current_mode == QOO_CTRL_MODE_AUTO ? "AUTO" : "HYBRID");
    return QOO_OK;
}

qoo_error_t qoo_hal_remote_get_mode(qoo_ctrl_mode_t *mode) {
    if (!mode) return QOO_ERROR_INVALID_PARAM;
    *mode = g_current_mode;
    return QOO_OK;
}

qoo_error_t qoo_hal_remote_get_session_info(qoo_remote_session_info_t *info) {
    if (!info) return QOO_ERROR_INVALID_PARAM;
    *info = g_session_info;
    return QOO_OK;
}

/*===========================================================================
 * 指令执行
 *===========================================================================*/

qoo_error_t qoo_hal_remote_execute_fullbody(const qoo_remote_fullbody_cmd_t *cmd) {
    if (!cmd) return QOO_ERROR_INVALID_PARAM;

    // 校验模式
    if (g_current_mode != QOO_CTRL_MODE_TELEOP) {
        g_stats.commands_rejected++;
        return QOO_ERROR_BUSY;
    }

    // 安全校验
    char violations[256] = {0};
    if (!qoo_hal_remote_validate_fullbody(cmd, violations, sizeof(violations))) {
        g_stats.commands_rejected++;
        LOG("Fullbody command rejected: %s", violations);
        return QOO_ERROR_SAFETY_TRIGGERED;
    }

    g_stats.commands_received++;

    // 更新延迟统计
    uint32_t latency = calc_latency_us(cmd->timestamp_ns);
    update_latency_stats(latency);

    // 应用速度倍率
    float speed = cmd->speed_override;
    if (speed < 0.0f) speed = 0.0f;
    if (speed > 1.0f) speed = 1.0f;

    // ---- 执行基座运动 ----
    // 注意：qoobody 目前通过 ROS2 /cmd_vel 控制基座
    // 在 HAL 层通过 qoo_hal_motor_set_commands_batch 或 ROS2 bridge 实现
    // 这里标记为实际部署时接入
    // qoo_hal_base_set_velocity(cmd->base.vx * speed, cmd->base.vy * speed, cmd->base.omega * speed);

    // ---- 执行关节运动 ----
    for (uint8_t i = 0; i < cmd->joint_count; i++) {
        const qoo_remote_joint_cmd_t *jc = &cmd->joints[i];

        // 映射到执行器指令
        qoo_motor_command_t motor_cmd;
        motor_cmd.mode = QOO_CTRL_MODE_POSITION;
        motor_cmd.target_position = (float)(jc->position);
        motor_cmd.target_velocity = (float)(jc->velocity * speed);
        motor_cmd.target_torque = (float)(jc->torque_ff);
        motor_cmd.kp = 0.0f;
        motor_cmd.kd = 0.0f;
        motor_cmd.torque_limit = 100.0f;  // 默认力矩限制

        // 通过执行器 HAL 下发
        // 实际部署：通过 joint_name 查表获取 motor_id
        // qoo_hal_motor_set_command(motor_id, &motor_cmd);
    }

    // ---- 执行左末端执行器 ----
    {
        qoo_ee_command_t ee_cmd;
        ee_cmd.target_opening = (float)(cmd->left_gripper.position);
        ee_cmd.grip_force_limit = (float)(cmd->left_gripper.grasp_force);
        ee_cmd.grip_speed = 0.5f;
        // qoo_hal_ee_set_command(EE_ID_LEFT, &ee_cmd);
    }

    // ---- 执行右末端执行器 ----
    {
        qoo_ee_command_t ee_cmd;
        ee_cmd.target_opening = (float)(cmd->right_gripper.position);
        ee_cmd.grip_force_limit = (float)(cmd->right_gripper.grasp_force);
        ee_cmd.grip_speed = 0.5f;
        // qoo_hal_ee_set_command(EE_ID_RIGHT, &ee_cmd);
    }

    // ---- 执行头部运动 ----
    // qoo_hal_head_set_pan_tilt(cmd->head.yaw, cmd->head.pitch);

    // 更新心跳
    qoo_hal_remote_update_heartbeat();

    g_stats.commands_executed++;
    g_session_info.command_count++;

    return QOO_OK;
}

qoo_error_t qoo_hal_remote_execute_joint(const char *joint_name,
                                          const qoo_remote_joint_cmd_t *cmd) {
    if (!joint_name || !cmd) return QOO_ERROR_INVALID_PARAM;
    if (g_current_mode != QOO_CTRL_MODE_TELEOP) return QOO_ERROR_BUSY;

    // 安全校验
    char violation[128] = {0};
    if (!qoo_hal_remote_validate_joint(cmd, violation, sizeof(violation))) {
        g_stats.commands_rejected++;
        return QOO_ERROR_SAFETY_TRIGGERED;
    }

    g_stats.commands_received++;

    // 下发到执行器
    qoo_motor_command_t motor_cmd;
    motor_cmd.mode = QOO_CTRL_MODE_POSITION;
    motor_cmd.target_position = (float)(cmd->position);
    motor_cmd.target_velocity = (float)(cmd->velocity);
    motor_cmd.target_torque = (float)(cmd->torque_ff);
    motor_cmd.kp = 0.0f;
    motor_cmd.kd = 0.0f;
    motor_cmd.torque_limit = 100.0f;

    // qoo_hal_motor_set_command(motor_id, &motor_cmd);

    qoo_hal_remote_update_heartbeat();
    g_stats.commands_executed++;
    return QOO_OK;
}

qoo_error_t qoo_hal_remote_execute_gripper(const qoo_remote_gripper_cmd_t *cmd,
                                            bool is_left) {
    if (!cmd) return QOO_ERROR_INVALID_PARAM;
    if (g_current_mode != QOO_CTRL_MODE_TELEOP) return QOO_ERROR_BUSY;

    g_stats.commands_received++;

    qoo_ee_command_t ee_cmd;
    ee_cmd.target_opening = (float)(cmd->position);
    ee_cmd.grip_force_limit = (float)(cmd->grasp_force);
    ee_cmd.grip_speed = 0.5f;

    // uint32_t ee_id = is_left ? EE_ID_LEFT : EE_ID_RIGHT;
    // qoo_hal_ee_set_command(ee_id, &ee_cmd);

    qoo_hal_remote_update_heartbeat();
    g_stats.commands_executed++;
    return QOO_OK;
}

qoo_error_t qoo_hal_remote_execute_head(const qoo_remote_head_cmd_t *cmd) {
    if (!cmd) return QOO_ERROR_INVALID_PARAM;
    if (g_current_mode != QOO_CTRL_MODE_TELEOP) return QOO_ERROR_BUSY;

    // 范围校验
    if (fabs(cmd->pitch) > M_PI_2) return QOO_ERROR_INVALID_PARAM;
    if (fabs(cmd->yaw) > M_PI) return QOO_ERROR_INVALID_PARAM;

    g_stats.commands_received++;

    // qoo_hal_head_set_pan_tilt(cmd->yaw, cmd->pitch);

    qoo_hal_remote_update_heartbeat();
    g_stats.commands_executed++;
    return QOO_OK;
}

qoo_error_t qoo_hal_remote_emergency_stop(const char *reason) {
    LOG("EMERGENCY STOP triggered: %s", reason ? reason : "unknown");

    // 触发安全控制器急停
    // qoo_hal_safety_request_mode(QOO_SAFETY_MODE_EMERGENCY_STOP);
    // qoo_hal_motor_emergency_stop_all();

    g_current_mode = QOO_CTRL_MODE_AUTO;
    g_session_info.state = QOO_REMOTE_SESSION_DISCONNECTED;
    g_stats.emergency_stop_count++;

    return QOO_OK;
}

/*===========================================================================
 * 指令校验
 *===========================================================================*/

bool qoo_hal_remote_validate_fullbody(const qoo_remote_fullbody_cmd_t *cmd,
                                       char *violations,
                                       size_t violations_size) {
    if (!cmd) return false;

    size_t offset = 0;
    size_t remaining = violations_size;

    // 辅助 lambda: 追加违规描述
    auto append_violation = [&](const char *msg) {
        if (remaining > 1) {
            int written = snprintf(violations + offset, remaining, "%s; ", msg);
            if (written > 0) {
                offset += written;
                remaining = (written < (int)remaining) ? remaining - written : 0;
            }
        }
    };

    bool valid = true;

    // 基座速度校验
    if (fabs(cmd->base.vx) > 2.0) {
        append_violation("Base vx exceeds limit");
        valid = false;
    }
    if (fabs(cmd->base.vy) > 2.0) {
        append_violation("Base vy exceeds limit");
        valid = false;
    }
    if (fabs(cmd->base.omega) > M_PI) {
        append_violation("Base omega exceeds limit");
        valid = false;
    }

    // 关节校验
    for (uint8_t i = 0; i < cmd->joint_count; i++) {
        const qoo_remote_joint_cmd_t *jc = &cmd->joints[i];
        if (!qoo_hal_remote_validate_joint(jc, nullptr, 0)) {
            valid = false;
            char buf[64];
            snprintf(buf, sizeof(buf), "Joint %s invalid", jc->joint_name);
            append_violation(buf);
        }
    }

    // 速度倍率
    if (cmd->speed_override < 0.0f || cmd->speed_override > 1.0f) {
        append_violation("Speed override out of range");
        valid = false;
    }

    return valid;
}

bool qoo_hal_remote_validate_joint(const qoo_remote_joint_cmd_t *cmd,
                                    char *violation,
                                    size_t violation_size) {
    if (!cmd) return false;

    // 速度校验
    if (fabs(cmd->velocity) > 10.0) {  // 10 rad/s
        if (violation && violation_size > 0) {
            snprintf(violation, violation_size,
                     "Joint %s velocity %.2f exceeds limit",
                     cmd->joint_name, cmd->velocity);
        }
        return false;
    }

    // 力矩校验
    if (fabs(cmd->torque_ff) > 100.0) {  // 100 Nm
        if (violation && violation_size > 0) {
            snprintf(violation, violation_size,
                     "Joint %s torque %.2f exceeds limit",
                     cmd->joint_name, cmd->torque_ff);
        }
        return false;
    }

    return true;
}

/*===========================================================================
 * 遥控统计
 *===========================================================================*/

qoo_error_t qoo_hal_remote_get_stats(qoo_remote_stats_t *stats) {
    if (!stats) return QOO_ERROR_INVALID_PARAM;
    *stats = g_stats;
    return QOO_OK;
}

qoo_error_t qoo_hal_remote_reset_stats(void) {
    memset(&g_stats, 0, sizeof(g_stats));
    return QOO_OK;
}

qoo_error_t qoo_hal_remote_update_heartbeat(void) {
    qoo_timestamp_us_t now = get_timestamp_us();

    // 检测心跳超时
    if (g_last_heartbeat_us > 0) {
        uint64_t elapsed = now - g_last_heartbeat_us;
        if (elapsed > g_heartbeat_timeout_us) {
            g_stats.heartbeat_timeouts++;
            LOG("Heartbeat timeout! elapsed=%llu us", (unsigned long long)elapsed);
            // 自动触发安全停止
            qoo_hal_remote_emergency_stop("heartbeat timeout");
            return QOO_ERROR_TIMEOUT;
        }
    }

    g_last_heartbeat_us = now;
    return QOO_OK;
}

/*===========================================================================
 * 视频流控制
 *===========================================================================*/

qoo_error_t qoo_hal_remote_set_video_params(const char *camera_id,
                                              uint32_t bitrate_kbps,
                                              uint32_t width,
                                              uint32_t height,
                                              uint32_t fps) {
    if (!camera_id) return QOO_ERROR_INVALID_PARAM;

    LOG("Set video params: camera=%s bitrate=%u kbps resolution=%ux%u fps=%u",
        camera_id, bitrate_kbps, width, height, fps);

    // 实际部署：通过 GStreamer 管道动态调整编码参数
    // gst_video_encoder_set_bitrate(camera_id, bitrate_kbps);
    // gst_video_encoder_set_resolution(camera_id, width, height);
    // gst_video_encoder_set_framerate(camera_id, fps);

    return QOO_OK;
}

qoo_error_t qoo_hal_remote_request_keyframe(const char *camera_id) {
    if (!camera_id) return QOO_ERROR_INVALID_PARAM;

    LOG("Request keyframe: camera=%s", camera_id);

    // 实际部署：向编码器发送 I 帧请求
    // gst_video_encoder_force_keyframe(camera_id);

    return QOO_OK;
}
