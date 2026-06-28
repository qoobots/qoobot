#include "qoosvc/remote/remote_service.h"
#include <algorithm>
#include <chrono>
#include <cmath>
#include <mutex>
#include <thread>

namespace qoosvc::remote {

// ============================================================================
// RemoteService::Impl
// ============================================================================

struct RemoteService::Impl {
    RemoteConfig config;
    bool running = false;

    // 会话
    std::string current_session_id;
    SessionState session_state = SessionState::DISCONNECTED;

    // 模式
    RobotMode current_mode = RobotMode::AUTO;
    RobotMode previous_mode = RobotMode::AUTO;

    // 回调
    StateCallback state_callback;
    TeachingFrameCallback teaching_frame_callback;

    // 示教
    bool teaching_active = false;
    std::string teaching_record_name;
    uint32_t teaching_frame_count = 0;
    std::chrono::steady_clock::time_point teaching_start_time;

    // 心跳
    std::chrono::steady_clock::time_point last_heartbeat;
    std::thread heartbeat_thread;
    std::atomic<bool> heartbeat_active{false};

    // 线程安全
    mutable std::mutex mutex;

    // 状态序列号
    uint64_t state_sequence = 0;
};

RemoteService::RemoteService() : impl_(std::make_unique<Impl>()) {}

RemoteService::~RemoteService() {
    stop();
}

// ========== 生命周期 ==========

bool RemoteService::initialize(const RemoteConfig& config) {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    impl_->config = config;
    return true;
}

bool RemoteService::start() {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    impl_->running = true;

    // 启动心跳线程
    impl_->heartbeat_active = true;
    impl_->heartbeat_thread = std::thread([this]() {
        while (impl_->heartbeat_active) {
            std::this_thread::sleep_for(
                std::chrono::milliseconds(impl_->config.heartbeat_interval_ms));

            std::lock_guard<std::mutex> lock(impl_->mutex);
            if (impl_->session_state == SessionState::TELEOP_ACTIVE ||
                impl_->session_state == SessionState::CONNECTED) {

                auto now = std::chrono::steady_clock::now();
                auto elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(
                    now - impl_->last_heartbeat).count();

                // 心跳超时 → 自动急停
                if (elapsed > impl_->config.heartbeat_timeout_ms) {
                    impl_->session_state = SessionState::DISCONNECTED;
                    // 触发安全停止 (实际调用 HAL 层)
                }

                // 上报状态
                if (impl_->state_callback) {
                    impl_->state_callback(get_current_state());
                }
            }
        }
    });

    return true;
}

void RemoteService::stop() {
    impl_->heartbeat_active = false;
    if (impl_->heartbeat_thread.joinable()) {
        impl_->heartbeat_thread.join();
    }

    std::lock_guard<std::mutex> lock(impl_->mutex);
    impl_->running = false;
    impl_->session_state = SessionState::DISCONNECTED;
    impl_->current_mode = RobotMode::AUTO;
    impl_->teaching_active = false;
}

bool RemoteService::is_running() const {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    return impl_->running;
}

// ========== 会话管理 ==========

bool RemoteService::create_session(const std::string& session_id) {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    if (!impl_->running) return false;
    if (impl_->session_state != SessionState::DISCONNECTED) return false;

    impl_->current_session_id = session_id;
    impl_->session_state = SessionState::CONNECTING;
    impl_->last_heartbeat = std::chrono::steady_clock::now();
    return true;
}

bool RemoteService::close_session(const std::string& session_id) {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    if (impl_->current_session_id != session_id) return false;

    // 如果正在遥控，先切换到自主模式
    if (impl_->current_mode == RobotMode::TELEOP) {
        impl_->current_mode = impl_->previous_mode;
    }

    impl_->session_state = SessionState::DISCONNECTED;
    impl_->current_session_id.clear();
    return true;
}

SessionState RemoteService::get_session_state() const {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    return impl_->session_state;
}

// ========== 控制指令执行 ==========

bool RemoteService::execute_fullbody_command(const TeleopCommand& command) {
    std::lock_guard<std::mutex> lock(impl_->mutex);

    if (impl_->current_mode != RobotMode::TELEOP) return false;

    // 安全校验
    std::vector<std::string> violations;
    if (!validate_command(command, violations)) {
        return false;
    }

    // 应用速度倍率
    double speed_override = std::clamp(static_cast<double>(command.speed_override), 0.0, 1.0);

    // 执行基座运动 → HAL 层
    // qoo_hal_fullbody_set_command(...)

    // 执行关节运动 → HAL 层
    for (const auto& joint : command.joints) {
        // qoo_hal_joint_set_position(joint.joint_name, joint.position * speed_override)
    }

    // 执行末端执行器
    // qoo_hal_gripper_set(command.left_gripper, true)
    // qoo_hal_gripper_set(command.right_gripper, false)

    // 执行头部
    // qoo_hal_head_set(command.head)

    // 更新心跳
    impl_->last_heartbeat = std::chrono::steady_clock::now();

    // 如果正在示教，记录帧
    if (impl_->teaching_active && impl_->teaching_frame_callback) {
        TeachingFrame frame;
        frame.timestamp_ns = command.timestamp_ns;
        frame.frame_index = impl_->teaching_frame_count++;
        frame.joint_points = command.joints;
        frame.base_point = command.base;
        frame.left_gripper = command.left_gripper;
        frame.right_gripper = command.right_gripper;
        frame.head = command.head;
        frame.operator_command = command;
        impl_->teaching_frame_callback(frame);
    }

    return true;
}

bool RemoteService::execute_joint_command(const std::string& joint_name,
                                           const JointSetpoint& setpoint) {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    if (impl_->current_mode != RobotMode::TELEOP) return false;

    std::string violation;
    if (!validate_joint_setpoint(setpoint, violation)) return false;

    // qoo_hal_joint_set_position(joint_name, setpoint.position)
    impl_->last_heartbeat = std::chrono::steady_clock::now();
    return true;
}

bool RemoteService::execute_gripper_command(const GripperCommand& command,
                                              bool is_left) {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    if (impl_->current_mode != RobotMode::TELEOP) return false;

    // qoo_hal_gripper_set(command, is_left)
    impl_->last_heartbeat = std::chrono::steady_clock::now();
    return true;
}

bool RemoteService::execute_head_command(const HeadCommand& command) {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    if (impl_->current_mode != RobotMode::TELEOP) return false;

    // 范围校验
    if (std::abs(command.pitch) > M_PI_2) return false;
    if (std::abs(command.yaw) > M_PI) return false;

    // qoo_hal_head_set(command)
    impl_->last_heartbeat = std::chrono::steady_clock::now();
    return true;
}

bool RemoteService::emergency_stop(StopType type, const std::string& reason) {
    std::lock_guard<std::mutex> lock(impl_->mutex);

    // 调用 HAL 安全层
    // qoo_hal_safety_trigger(SafetyEvent::OPERATOR_ESTOP)

    // 切换到保护性停止或急停
    if (type == StopType::EMERGENCY || type == StopType::STO) {
        impl_->current_mode = RobotMode::AUTO; // 急停后退出遥控模式
        impl_->session_state = SessionState::CONNECTED;
    }

    return true;
}

// ========== 模式切换 ==========

bool RemoteService::request_takeover() {
    std::lock_guard<std::mutex> lock(impl_->mutex);

    if (impl_->session_state != SessionState::CONNECTED) return false;

    impl_->previous_mode = impl_->current_mode;
    impl_->session_state = SessionState::TAKEOVER_PENDING;

    // 平滑切换：保持当前姿态，逐渐过渡到遥控
    // 实际实现需要与 qoobrain 安全监护协调
    impl_->current_mode = RobotMode::TELEOP;
    impl_->session_state = SessionState::TELEOP_ACTIVE;

    return true;
}

bool RemoteService::request_handover() {
    std::lock_guard<std::mutex> lock(impl_->mutex);

    if (impl_->current_mode != RobotMode::TELEOP) return false;

    impl_->session_state = SessionState::HANDOVER_PENDING;

    // 恢复到自主模式
    impl_->current_mode = impl_->previous_mode;
    impl_->session_state = SessionState::CONNECTED;

    return true;
}

RobotMode RemoteService::get_current_mode() const {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    return impl_->current_mode;
}

// ========== 状态上报 ==========

TeleopState RemoteService::get_current_state() const {
    std::lock_guard<std::mutex> lock(impl_->mutex);

    TeleopState state;
    state.timestamp_ns = std::chrono::duration_cast<std::chrono::nanoseconds>(
        std::chrono::system_clock::now().time_since_epoch()).count();
    state.sequence = impl_->state_sequence++;
    state.session_id = impl_->current_session_id;

    // 实际实现从 HAL 层获取：
    // state.base_pose = qoo_hal_get_base_pose();
    // state.joints = qoo_hal_get_joint_states();
    // state.battery_soc = qoo_hal_get_battery_soc();
    // etc.

    return state;
}

void RemoteService::set_state_callback(StateCallback callback) {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    impl_->state_callback = std::move(callback);
}

// ========== 安全校验 ==========

bool RemoteService::validate_command(const TeleopCommand& command,
                                      std::vector<std::string>& violations) const {
    violations.clear();

    // 基座速度校验
    if (std::abs(command.base.vx) > impl_->config.max_base_speed)
        violations.push_back("Base vx exceeds limit");
    if (std::abs(command.base.vy) > impl_->config.max_base_speed)
        violations.push_back("Base vy exceeds limit");
    if (std::abs(command.base.omega) > impl_->config.max_base_omega)
        violations.push_back("Base omega exceeds limit");

    // 关节校验
    for (const auto& joint : command.joints) {
        if (std::abs(joint.velocity) > impl_->config.max_joint_velocity)
            violations.push_back("Joint " + joint.joint_name + " velocity exceeds limit");
        if (std::abs(joint.torque_ff) > impl_->config.max_joint_torque)
            violations.push_back("Joint " + joint.joint_name + " torque exceeds limit");
    }

    // 速度倍率
    if (command.speed_override < 0.0f || command.speed_override > 1.0f)
        violations.push_back("Speed override out of range");

    return violations.empty();
}

bool RemoteService::validate_joint_setpoint(const JointSetpoint& sp,
                                              std::string& violation) const {
    if (std::abs(sp.velocity) > impl_->config.max_joint_velocity) {
        violation = "Joint velocity exceeds limit";
        return false;
    }
    if (std::abs(sp.torque_ff) > impl_->config.max_joint_torque) {
        violation = "Joint torque exceeds limit";
        return false;
    }
    return true;
}

// ========== 示教 ==========

bool RemoteService::start_teaching(const std::string& record_name,
                                    const std::string& description) {
    std::lock_guard<std::mutex> lock(impl_->mutex);

    if (impl_->teaching_active) return false;
    if (impl_->current_mode != RobotMode::TELEOP) return false;

    impl_->teaching_active = true;
    impl_->teaching_record_name = record_name;
    impl_->teaching_frame_count = 0;
    impl_->teaching_start_time = std::chrono::steady_clock::now();

    return true;
}

bool RemoteService::stop_teaching() {
    std::lock_guard<std::mutex> lock(impl_->mutex);

    if (!impl_->teaching_active) return false;

    impl_->teaching_active = false;

    auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(
        std::chrono::steady_clock::now() - impl_->teaching_start_time).count();

    // 实际实现将示教数据打包上传到 qoocloud-teleop

    return true;
}

bool RemoteService::is_teaching() const {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    return impl_->teaching_active;
}

uint32_t RemoteService::get_teaching_frame_count() const {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    return impl_->teaching_frame_count;
}

void RemoteService::set_teaching_frame_callback(TeachingFrameCallback callback) {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    impl_->teaching_frame_callback = std::move(callback);
}

// ========== 配置 ==========

RemoteConfig RemoteService::get_config() const {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    return impl_->config;
}

void RemoteService::update_config(const RemoteConfig& config) {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    impl_->config = config;
}

} // namespace qoosvc::remote
