#pragma once

#include "qoosvc/remote/remote_types.h"
#include <functional>
#include <memory>
#include <string>
#include <vector>

namespace qoosvc::remote {

/**
 * RemoteService — 机器人端远程遥控服务 (qooremote Agent)
 *
 * 负责：
 * - 接收和执行遥控指令 (控制下行)
 * - 上报机器人状态 (状态上行)
 * - 自主↔遥控模式切换 (TakeoverHandler)
 * - 示教数据采集 (TeachingCollector)
 * - 指令安全校验
 *
 * 对标: Android Accessibility Service + Device Policy Manager
 */
class RemoteService {
public:
    RemoteService();
    ~RemoteService();

    // ========== 生命周期 ==========

    bool initialize(const RemoteConfig& config);
    bool start();
    void stop();
    bool is_running() const;

    // ========== 会话管理 ==========

    /** 创建遥控会话 */
    bool create_session(const std::string& session_id);

    /** 关闭遥控会话 */
    bool close_session(const std::string& session_id);

    /** 获取当前会话状态 */
    SessionState get_session_state() const;

    // ========== 控制指令执行 ==========

    /** 执行全身运动指令 */
    bool execute_fullbody_command(const TeleopCommand& command);

    /** 执行单关节指令 */
    bool execute_joint_command(const std::string& joint_name,
                                const JointSetpoint& setpoint);

    /** 执行末端执行器指令 */
    bool execute_gripper_command(const GripperCommand& command,
                                  bool is_left);

    /** 执行头部指令 */
    bool execute_head_command(const HeadCommand& command);

    /** 紧急停止 */
    bool emergency_stop(StopType type, const std::string& reason = "");

    // ========== 模式切换 ==========

    /** 请求切换到遥控模式 */
    bool request_takeover();

    /** 请求切换到自主模式 */
    bool request_handover();

    /** 获取当前模式 */
    RobotMode get_current_mode() const;

    // ========== 状态上报 ==========

    /** 获取当前机器人状态快照 */
    TeleopState get_current_state() const;

    /** 设置状态上报回调 (推送到云端) */
    using StateCallback = std::function<void(const TeleopState& state)>;
    void set_state_callback(StateCallback callback);

    // ========== 安全校验 ==========

    /** 校验指令是否在安全范围内 */
    bool validate_command(const TeleopCommand& command,
                          std::vector<std::string>& violations) const;

    /** 校验单关节指令 */
    bool validate_joint_setpoint(const JointSetpoint& sp,
                                  std::string& violation) const;

    // ========== 示教 ==========

    /** 开始示教录制 */
    bool start_teaching(const std::string& record_name,
                        const std::string& description = "");

    /** 停止示教录制 */
    bool stop_teaching();

    /** 是否正在示教 */
    bool is_teaching() const;

    /** 获取示教帧数 */
    uint32_t get_teaching_frame_count() const;

    /** 设置示教帧回调 (上传到云端存储) */
    using TeachingFrameCallback = std::function<void(const TeachingFrame& frame)>;
    void set_teaching_frame_callback(TeachingFrameCallback callback);

    // ========== 配置 ==========

    RemoteConfig get_config() const;
    void update_config(const RemoteConfig& config);

private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};

} // namespace qoosvc::remote
