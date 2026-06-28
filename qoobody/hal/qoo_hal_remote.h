/**
 * @file qoo_hal_remote.h
 * @brief QooBot 硬件抽象层 (HAL) — 远程遥控接口
 *
 * 定义遥操作所需的 HAL 层接口，包括：
 * - 远程控制模式切换
 * - 全身运动指令执行
 * - 控制权管理
 * - 视频/音频流控制
 *
 * 版本: v0.1 | 2026-06-28
 */

#ifndef QOO_HAL_REMOTE_H
#define QOO_HAL_REMOTE_H

#include "qoo_hal_types.h"
#include "qoo_hal_actuator.h"
#include "qoo_hal_safety.h"

#ifdef __cplusplus
extern "C" {
#endif

/*===========================================================================
 * 控制模式
 *===========================================================================*/

/** 机器人控制模式 */
typedef enum {
    QOO_CTRL_MODE_AUTO = 0,     /**< 完全自主 */
    QOO_CTRL_MODE_HYBRID = 1,   /**< 混合模式 (自主执行+人工监督) */
    QOO_CTRL_MODE_TELEOP = 2,   /**< 完全遥控 */
} qoo_ctrl_mode_t;

/** 遥控会话状态 */
typedef enum {
    QOO_REMOTE_SESSION_DISCONNECTED = 0,
    QOO_REMOTE_SESSION_CONNECTING = 1,
    QOO_REMOTE_SESSION_CONNECTED = 2,
    QOO_REMOTE_SESSION_TAKEOVER_PENDING = 3,
    QOO_REMOTE_SESSION_TELEOP_ACTIVE = 4,
    QOO_REMOTE_SESSION_HANDOVER_PENDING = 5,
    QOO_REMOTE_SESSION_CLOSING = 6,
} qoo_remote_session_state_t;

/*===========================================================================
 * 遥控指令结构
 *===========================================================================*/

/** 基座运动指令 */
typedef struct {
    double vx;              /**< 前进速度 (m/s) */
    double vy;              /**< 横向速度 (m/s) */
    double omega;           /**< 旋转速度 (rad/s) */
} qoo_remote_base_cmd_t;

/** 单关节遥控指令 */
typedef struct {
    char joint_name[32];    /**< 关节名称 */
    double position;        /**< 目标位置 (rad) */
    double velocity;        /**< 目标速度 (rad/s), 0 表示不限制 */
    double torque_ff;       /**< 前馈力矩 (Nm) */
    uint8_t control_mode;   /**< qoo_ctrl_mode_t */
} qoo_remote_joint_cmd_t;

/** 末端执行器遥控指令 */
typedef struct {
    uint8_t type;           /**< 0=平行夹爪, 1=三指, 2=吸盘, 3=灵巧手 */
    double position;        /**< 开口宽度 (m) */
    double grasp_force;     /**< 抓取力 (N) */
    bool suction_on;        /**< 吸盘开关 */
} qoo_remote_gripper_cmd_t;

/** 头部遥控指令 */
typedef struct {
    double pitch;           /**< 俯仰角 (rad) */
    double yaw;             /**< 偏航角 (rad) */
    double roll;            /**< 滚转角 (rad) */
} qoo_remote_head_cmd_t;

/** 全身遥控指令 */
typedef struct {
    uint64_t timestamp_ns;              /**< 时间戳 */
    uint64_t sequence;                  /**< 序列号 */
    char session_id[64];                /**< 会话ID */

    qoo_remote_base_cmd_t base;         /**< 基座运动 */
    uint8_t joint_count;                /**< 关节数量 */
    qoo_remote_joint_cmd_t joints[64];  /**< 关节指令数组 */
    qoo_remote_gripper_cmd_t left_gripper;
    qoo_remote_gripper_cmd_t right_gripper;
    qoo_remote_head_cmd_t head;

    uint8_t control_mode;               /**< 控制模式 */
    float speed_override;               /**< 速度倍率 [0.0, 1.0] */
} qoo_remote_fullbody_cmd_t;

/*===========================================================================
 * 遥控状态结构
 *===========================================================================*/

/** 遥控会话信息 */
typedef struct {
    char session_id[64];
    qoo_remote_session_state_t state;
    qoo_ctrl_mode_t current_mode;
    qoo_ctrl_mode_t previous_mode;
    uint64_t last_heartbeat_ns;
    uint64_t connected_at_ns;
    uint64_t command_count;
} qoo_remote_session_info_t;

/** 遥控统计 */
typedef struct {
    uint64_t commands_received;
    uint64_t commands_rejected;     /**< 校验失败 */
    uint64_t commands_executed;
    uint64_t takeover_count;        /**< 接管次数 */
    uint64_t emergency_stop_count;
    uint32_t avg_latency_us;        /**< 平均指令延迟 */
    uint32_t max_latency_us;        /**< 最大指令延迟 */
    uint32_t heartbeat_timeouts;    /**< 心跳超时次数 */
} qoo_remote_stats_t;

/*===========================================================================
 * HAL 遥控接口
 *===========================================================================*/

/**
 * @brief 请求切换到遥控模式
 *
 * 从 AUTO/HYBRID 模式切换到 TELEOP 模式。
 * 平滑过渡：保持当前姿态，逐渐切换到遥控指令控制。
 *
 * @param session_id 遥控会话ID
 * @return QOO_OK 成功
 */
qoo_error_t qoo_hal_remote_request_takeover(const char *session_id);

/**
 * @brief 请求切换到自主模式
 *
 * 从 TELEOP 模式切换回 AUTO 模式。
 * 机器人恢复自主控制，保持运动连续性。
 *
 * @return QOO_OK 成功
 */
qoo_error_t qoo_hal_remote_request_handover(void);

/**
 * @brief 获取当前控制模式
 * @param mode [out] 当前模式
 * @return QOO_OK 成功
 */
qoo_error_t qoo_hal_remote_get_mode(qoo_ctrl_mode_t *mode);

/**
 * @brief 获取遥控会话信息
 * @param info [out] 会话信息
 * @return QOO_OK 成功
 */
qoo_error_t qoo_hal_remote_get_session_info(qoo_remote_session_info_t *info);

/*===========================================================================
 * 指令执行
 *===========================================================================*/

/**
 * @brief 执行全身遥控指令
 *
 * 接收操作员端的全身运动指令，校验后执行。
 * 仅在 TELEOP 模式下有效。
 *
 * @param cmd 全身遥控指令
 * @return QOO_OK 成功
 */
qoo_error_t qoo_hal_remote_execute_fullbody(const qoo_remote_fullbody_cmd_t *cmd);

/**
 * @brief 执行单关节遥控指令
 * @param joint_name 关节名称
 * @param cmd 关节指令
 * @return QOO_OK 成功
 */
qoo_error_t qoo_hal_remote_execute_joint(const char *joint_name,
                                          const qoo_remote_joint_cmd_t *cmd);

/**
 * @brief 执行末端执行器遥控指令
 * @param cmd 末端指令
 * @param is_left true=左, false=右
 * @return QOO_OK 成功
 */
qoo_error_t qoo_hal_remote_execute_gripper(const qoo_remote_gripper_cmd_t *cmd,
                                            bool is_left);

/**
 * @brief 执行头部遥控指令
 * @param cmd 头部指令
 * @return QOO_OK 成功
 */
qoo_error_t qoo_hal_remote_execute_head(const qoo_remote_head_cmd_t *cmd);

/**
 * @brief 遥控紧急停止
 *
 * 立即停止所有运动，进入 SAFETY_MODE_EMERGENCY_STOP。
 * 仅在 TELEOP 或 HYBRID 模式下有效。
 *
 * @param reason 停止原因
 * @return QOO_OK 成功
 */
qoo_error_t qoo_hal_remote_emergency_stop(const char *reason);

/*===========================================================================
 * 指令校验
 *===========================================================================*/

/**
 * @brief 校验全身遥控指令是否在安全范围内
 *
 * 检查基座速度、关节速度/力矩、速度倍率等参数。
 *
 * @param cmd 指令
 * @param violations [out] 违规描述 (预分配 256 字节)
 * @param violations_size violations 缓冲区大小
 * @return true 校验通过, false 校验失败
 */
bool qoo_hal_remote_validate_fullbody(const qoo_remote_fullbody_cmd_t *cmd,
                                       char *violations,
                                       size_t violations_size);

/**
 * @brief 校验单关节指令
 * @param cmd 关节指令
 * @param violation [out] 违规描述
 * @param violation_size 缓冲区大小
 * @return true 通过
 */
bool qoo_hal_remote_validate_joint(const qoo_remote_joint_cmd_t *cmd,
                                    char *violation,
                                    size_t violation_size);

/*===========================================================================
 * 遥控统计
 *===========================================================================*/

/**
 * @brief 获取遥控统计
 * @param stats [out] 统计数据
 * @return QOO_OK 成功
 */
qoo_error_t qoo_hal_remote_get_stats(qoo_remote_stats_t *stats);

/**
 * @brief 重置遥控统计
 * @return QOO_OK 成功
 */
qoo_error_t qoo_hal_remote_reset_stats(void);

/**
 * @brief 更新心跳时间戳
 *
 * 每次收到有效遥控指令或心跳包时调用。
 * 如果心跳超时（>heartbeat_timeout_ms），自动触发安全停止。
 *
 * @return QOO_OK 成功
 */
qoo_error_t qoo_hal_remote_update_heartbeat(void);

/*===========================================================================
 * 视频流控制 (遥操作相关)
 *===========================================================================*/

/**
 * @brief 设置视频流编码参数
 *
 * 动态调整编码参数以适应网络条件。
 *
 * @param camera_id 摄像头ID
 * @param bitrate_kbps 目标码率
 * @param width 分辨率宽
 * @param height 分辨率高
 * @param fps 帧率
 * @return QOO_OK 成功
 */
qoo_error_t qoo_hal_remote_set_video_params(const char *camera_id,
                                              uint32_t bitrate_kbps,
                                              uint32_t width,
                                              uint32_t height,
                                              uint32_t fps);

/**
 * @brief 请求关键帧 (I-Frame)
 *
 * 网络切换或丢包恢复时请求关键帧。
 *
 * @param camera_id 摄像头ID
 * @return QOO_OK 成功
 */
qoo_error_t qoo_hal_remote_request_keyframe(const char *camera_id);

#ifdef __cplusplus
}
#endif

#endif /* QOO_HAL_REMOTE_H */
