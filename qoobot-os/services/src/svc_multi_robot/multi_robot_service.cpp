#include "qoosvc/multi_robot/multi_robot_service.h"
#include <algorithm>
#include <chrono>
#include <mutex>
#include <numeric>

namespace qoosvc::multi_robot {

struct MultiRobotService::Impl {
    RobotInfo self_info;
    std::vector<RobotInfo> known_robots;
    std::vector<CooperativeTask> active_tasks;
    std::vector<CooperativeTask> my_tasks;
    CoCarryConfig carry_config;
    CoCarryStatus carry_status;
    std::vector<SharedData> shared_data_buffer;

    std::function<void(const RobotInfo&)> discovered_callback;
    std::function<void(const std::string&)> lost_callback;
    std::function<void(const CooperativeTask&)> task_callback;
    std::function<void(const CoCarryStatus&)> carry_callback;
    std::function<void(const SharedData&)> data_callback;

    mutable std::mutex mutex;
};

MultiRobotService::MultiRobotService()
    : ServiceBase("multi_robot_service"), impl_(std::make_unique<Impl>()) {}

MultiRobotService::~MultiRobotService() { stop(); }

// ========================================================================
// Robot Discovery
// ========================================================================

Result<DiscoveryResult> MultiRobotService::discover_robots() {
    std::lock_guard<std::mutex> lock(impl_->mutex);

    DiscoveryResult result;
    result.timestamp_us = std::chrono::duration_cast<std::chrono::microseconds>(
        std::chrono::system_clock::now().time_since_epoch()).count();

    // In production: use mDNS/DDS-SSDP for LAN service discovery
    // Filter out self
    for (const auto& robot : impl_->known_robots) {
        if (robot.robot_id != impl_->self_info.robot_id) {
            result.robots.push_back(robot);
        }
    }

    return result;
}

Result<void> MultiRobotService::register_self(const RobotInfo& info) {
    std::lock_guard<std::mutex> lock(impl_->mutex);

    impl_->self_info = info;
    connected_ = true;

    // In production: announce presence via DDS discovery
    return Result<void>::ok();
}

Result<void> MultiRobotService::unregister_self() {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    connected_ = false;
    return Result<void>::ok();
}

std::vector<RobotInfo> MultiRobotService::get_known_robots() const {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    return impl_->known_robots;
}

Result<RobotInfo> MultiRobotService::get_robot_info(const std::string& robot_id) const {
    std::lock_guard<std::mutex> lock(impl_->mutex);

    auto it = std::find_if(impl_->known_robots.begin(), impl_->known_robots.end(),
        [&](const RobotInfo& r) { return r.robot_id == robot_id; });

    if (it == impl_->known_robots.end()) {
        return Result<RobotInfo>::err(ErrorCode::MR_DISCOVERY_FAILED,
                                       "Robot not found: " + robot_id);
    }
    return *it;
}

void MultiRobotService::on_robot_discovered(
    std::function<void(const RobotInfo&)> callback) {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    impl_->discovered_callback = std::move(callback);
}

void MultiRobotService::on_robot_lost(std::function<void(const std::string&)> callback) {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    impl_->lost_callback = std::move(callback);
}

// ========================================================================
// Task Allocation
// ========================================================================

Result<TaskAllocationResult> MultiRobotService::allocate_task(
    const CooperativeTask& task) {

    std::lock_guard<std::mutex> lock(impl_->mutex);

    TaskAllocationResult result;
    result.task_id = task.task_id;

    // Find eligible robots
    std::vector<const RobotInfo*> candidates;
    for (const auto& robot : impl_->known_robots) {
        if (robot.status != "idle") continue;

        const auto& cap = robot.capability;
        if (task.requirements.needs_manipulator && !cap.has_manipulator) continue;
        if (task.requirements.min_payload_kg > cap.max_payload_kg) continue;
        if (task.requirements.min_battery > cap.battery_remaining) continue;

        bool has_skills = true;
        for (const auto& skill : task.requirements.required_skills) {
            if (std::find(cap.skills.begin(), cap.skills.end(), skill) == cap.skills.end()) {
                has_skills = false;
                break;
            }
        }
        if (!has_skills) continue;

        candidates.push_back(&robot);
    }

    if (candidates.empty()) {
        result.success = false;
        result.reason = "No eligible robots available";
        return result;
    }

    // Simple allocation: assign to first N eligible robots
    int32_t to_assign = std::min(task.required_robots,
                                  static_cast<int32_t>(candidates.size()));

    for (int32_t i = 0; i < to_assign; ++i) {
        result.assigned_robot_ids.push_back(candidates[i]->robot_id);
    }

    result.success = true;
    impl_->active_tasks.push_back(task);

    return result;
}

Result<void> MultiRobotService::accept_task(const std::string& task_id) {
    std::lock_guard<std::mutex> lock(impl_->mutex);

    auto it = std::find_if(impl_->active_tasks.begin(), impl_->active_tasks.end(),
        [&](const CooperativeTask& t) { return t.task_id == task_id; });

    if (it == impl_->active_tasks.end()) {
        return Result<void>::err(ErrorCode::MR_TASK_REJECTED, "Task not found");
    }

    it->assigned_robot_ids.push_back(impl_->self_info.robot_id);
    it->assigned_robots++;
    impl_->my_tasks.push_back(*it);

    return Result<void>::ok();
}

Result<void> MultiRobotService::reject_task(const std::string& task_id,
                                              const std::string& reason) {
    return Result<void>::ok();
}

Result<void> MultiRobotService::complete_task(const std::string& task_id) {
    std::lock_guard<std::mutex> lock(impl_->mutex);

    impl_->my_tasks.erase(
        std::remove_if(impl_->my_tasks.begin(), impl_->my_tasks.end(),
            [&](const CooperativeTask& t) { return t.task_id == task_id; }),
        impl_->my_tasks.end());

    return Result<void>::ok();
}

Result<void> MultiRobotService::cancel_task(const std::string& task_id) {
    std::lock_guard<std::mutex> lock(impl_->mutex);

    impl_->active_tasks.erase(
        std::remove_if(impl_->active_tasks.begin(), impl_->active_tasks.end(),
            [&](const CooperativeTask& t) { return t.task_id == task_id; }),
        impl_->active_tasks.end());

    return Result<void>::ok();
}

std::vector<CooperativeTask> MultiRobotService::get_active_tasks() const {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    return impl_->active_tasks;
}

std::vector<CooperativeTask> MultiRobotService::get_my_tasks() const {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    return impl_->my_tasks;
}

void MultiRobotService::on_task_assigned(
    std::function<void(const CooperativeTask&)> callback) {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    impl_->task_callback = std::move(callback);
}

// ========================================================================
// Cooperative Carrying
// ========================================================================

Result<void> MultiRobotService::start_co_carry(const CoCarryConfig& config) {
    std::lock_guard<std::mutex> lock(impl_->mutex);

    impl_->carry_config = config;
    impl_->carry_status.active = true;
    impl_->carry_status.leader_id = config.leader_robot_id;
    impl_->carry_status.active_followers = config.follower_robot_ids;
    impl_->carry_status.all_synced = false;
    impl_->carry_status.progress = 0.0;

    return Result<void>::ok();
}

Result<void> MultiRobotService::stop_co_carry() {
    std::lock_guard<std::mutex> lock(impl_->mutex);

    impl_->carry_status.active = false;
    impl_->carry_status.active_followers.clear();

    return Result<void>::ok();
}

Result<void> MultiRobotService::update_carry_pose(const Pose3D& object_pose) {
    std::lock_guard<std::mutex> lock(impl_->mutex);

    if (!impl_->carry_status.active) {
        return Result<void>::err(ErrorCode::INVALID_ARGUMENT, "No active carry operation");
    }

    impl_->carry_status.object_pose = object_pose;

    // Compute progress toward target
    double dx = object_pose.x - impl_->carry_status.target_pose.x;
    double dy = object_pose.y - impl_->carry_status.target_pose.y;
    double total_dist = std::sqrt(
        (impl_->carry_config.goal_pose.x - impl_->carry_config.start_pose.x) *
        (impl_->carry_config.goal_pose.x - impl_->carry_config.start_pose.x) +
        (impl_->carry_config.goal_pose.y - impl_->carry_config.start_pose.y) *
        (impl_->carry_config.goal_pose.y - impl_->carry_config.start_pose.y));

    double remaining = std::sqrt(dx * dx + dy * dy);
    impl_->carry_status.progress = total_dist > 0 ? 1.0 - remaining / total_dist : 0.0;

    if (impl_->carry_callback) {
        impl_->carry_callback(impl_->carry_status);
    }

    return Result<void>::ok();
}

CoCarryStatus MultiRobotService::get_co_carry_status() const {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    return impl_->carry_status;
}

void MultiRobotService::on_carry_update(
    std::function<void(const CoCarryStatus&)> callback) {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    impl_->carry_callback = std::move(callback);
}

// ========================================================================
// Information Sharing
// ========================================================================

Result<void> MultiRobotService::share_data(const SharedData& data) {
    std::lock_guard<std::mutex> lock(impl_->mutex);

    // In production: send to specific robot via DDS unicast
    impl_->shared_data_buffer.push_back(data);

    // Prune expired data
    int64_t now = std::chrono::duration_cast<std::chrono::microseconds>(
        std::chrono::system_clock::now().time_since_epoch()).count();

    impl_->shared_data_buffer.erase(
        std::remove_if(impl_->shared_data_buffer.begin(),
                        impl_->shared_data_buffer.end(),
                        [now](const SharedData& d) {
                            return (now - d.timestamp_us) > d.ttl_ms * 1000;
                        }),
        impl_->shared_data_buffer.end());

    return Result<void>::ok();
}

Result<void> MultiRobotService::broadcast_data(const SharedData& data) {
    std::lock_guard<std::mutex> lock(impl_->mutex);

    // In production: broadcast via DDS to all robots in cluster
    impl_->shared_data_buffer.push_back(data);

    return Result<void>::ok();
}

void MultiRobotService::on_shared_data(
    std::function<void(const SharedData&)> callback) {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    impl_->data_callback = std::move(callback);
}

std::vector<LoadBalanceInfo> MultiRobotService::get_cluster_load() const {
    std::lock_guard<std::mutex> lock(impl_->mutex);

    std::vector<LoadBalanceInfo> loads;
    for (const auto& robot : impl_->known_robots) {
        LoadBalanceInfo info;
        info.robot_id = robot.robot_id;
        info.battery_level = robot.capability.battery_remaining;
        info.load_score = 1.0 - robot.capability.battery_remaining;  // Simple load metric
        loads.push_back(info);
    }

    return loads;
}

// ========================================================================
// Service Lifecycle
// ========================================================================

Result<void> MultiRobotService::on_initialize() { return Result<void>::ok(); }

Result<void> MultiRobotService::on_stop() {
    unregister_self();
    if (impl_->carry_status.active) stop_co_carry();
    return Result<void>::ok();
}

} // namespace qoosvc::multi_robot
