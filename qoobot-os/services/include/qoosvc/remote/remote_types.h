#pragma once

#include <cstdint>
#include <string>
#include <vector>

namespace qoosvc::remote {

/**
 * 机器人运行模式
 */
enum class RobotMode {
    AUTO = 0,       // 完全自主
    HYBRID = 1,     // 混合模式 (自主执行+人工监督)
    TELEOP = 2,     // 完全遥控
};

/**
 * 遥控会话状态
 */
enum class SessionState {
    DISCONNECTED,
    CONNECTING,
    CONNECTED,
    TAKEOVER_PENDING,   // 等待接管确认
    TELEOP_ACTIVE,      // 遥控中
    HANDOVER_PENDING,   // 等待交还确认
    CLOSING,
};

/**
 * 控制模式
 */
enum class ControlMode {
    POSITION = 0,
    VELOCITY = 1,
    TORQUE = 2,
    IMPEDANCE = 3,
    ADMITTANCE = 4,
};

/**
 * 紧急停止类型
 */
enum class StopType {
    PROTECTIVE = 0,   // 保护性停止
    EMERGENCY = 1,    // 紧急停止
    STO = 2,          // 安全转矩关断
};

/**
 * 3D 向量
 */
struct Vec3 {
    double x = 0.0;
    double y = 0.0;
    double z = 0.0;
};

/**
 * 四元数
 */
struct Quaternion {
    double w = 1.0;
    double x = 0.0;
    double y = 0.0;
    double z = 0.0;
};

/**
 * 6D 位姿
 */
struct Pose {
    Vec3 position;
    Quaternion orientation;
};

/**
 * 基座运动指令
 */
struct BaseCommand {
    double vx = 0.0;       // 前进速度 (m/s)
    double vy = 0.0;       // 横向速度 (m/s)
    double omega = 0.0;    // 旋转速度 (rad/s)
};

/**
 * 关节目标
 */
struct JointSetpoint {
    std::string joint_name;
    double position = 0.0;      // 目标位置 (rad)
    double velocity = 0.0;      // 目标速度 (rad/s)
    double torque_ff = 0.0;     // 前馈力矩 (Nm)
    ControlMode control_mode = ControlMode::POSITION;
};

/**
 * 末端执行器指令
 */
struct GripperCommand {
    enum Type { PARALLEL, THREE_FINGER, SUCTION, DEXTEROUS };
    Type type = PARALLEL;
    double position = 0.0;      // 开口宽度 (m)
    double grasp_force = 0.0;   // 抓取力 (N)
    bool suction_on = false;    // 吸盘
};

/**
 * 头部指令
 */
struct HeadCommand {
    double pitch = 0.0;   // 俯仰角 (rad)
    double yaw = 0.0;     // 偏航角 (rad)
    double roll = 0.0;    // 滚转角 (rad)
};

/**
 * 全身运动指令 (遥控下行)
 */
struct TeleopCommand {
    uint64_t timestamp_ns = 0;
    uint64_t sequence = 0;
    std::string session_id;

    BaseCommand base;
    std::vector<JointSetpoint> joints;
    GripperCommand left_gripper;
    GripperCommand right_gripper;
    HeadCommand head;

    ControlMode control_mode = ControlMode::POSITION;
    float speed_override = 1.0f;  // 速度倍率 [0.0, 1.0]
};

/**
 * 关节状态
 */
struct JointState {
    std::string joint_name;
    double position = 0.0;      // 实际位置 (rad)
    double velocity = 0.0;      // 实际速度 (rad/s)
    double torque = 0.0;        // 实际力矩 (Nm)
    double current = 0.0;       // 电流 (A)
    double temperature = 0.0;   // 温度 (C)
    bool ok = true;
};

/**
 * 安全状态
 */
struct SafetyStatus {
    enum Mode {
        NORMAL, REDUCED_SPEED, PROTECTIVE_STOP,
        EMERGENCY_STOP, STO, MAINTENANCE
    };
    Mode current_mode = NORMAL;
    bool emergency_stop_engaged = false;
    bool protective_stop_engaged = false;
    std::vector<std::string> active_events;
};

/**
 * 机器人状态快照 (遥控上行)
 */
struct TeleopState {
    uint64_t timestamp_ns = 0;
    uint64_t sequence = 0;
    std::string session_id;

    // 基座
    Pose base_pose;
    Vec3 base_velocity;
    Vec3 base_angular_velocity;

    // 关节
    std::vector<JointState> joints;

    // 安全
    SafetyStatus safety;

    // 电池
    float battery_soc = 0.0f;       // [0, 1]
    float battery_voltage = 0.0f;
    float battery_temp = 0.0f;

    // 系统
    float cpu_usage = 0.0f;
    float cpu_temp = 0.0f;
    float memory_usage = 0.0f;
    uint32_t network_latency_ms = 0;
};

/**
 * 示教数据帧
 */
struct TeachingFrame {
    uint64_t timestamp_ns = 0;
    uint32_t frame_index = 0;

    // 关节轨迹
    std::vector<JointSetpoint> joint_points;
    BaseCommand base_point;
    GripperCommand left_gripper;
    GripperCommand right_gripper;
    HeadCommand head;

    // 对应的操作员指令 (用于行为克隆)
    TeleopCommand operator_command;
};

/**
 * 远程遥控服务配置
 */
struct RemoteConfig {
    // 会话
    uint32_t heartbeat_interval_ms = 1000;
    uint32_t heartbeat_timeout_ms = 3000;

    // 安全
    double max_base_speed = 2.0;         // m/s
    double max_base_omega = 3.14;        // rad/s
    double max_joint_velocity = 10.0;    // rad/s
    double max_joint_torque = 100.0;     // Nm

    // 示教
    uint32_t max_teaching_duration_s = 1800; // 30分钟
    uint32_t teaching_sample_rate_hz = 100;  // 示教采样率
};

} // namespace qoosvc::remote
