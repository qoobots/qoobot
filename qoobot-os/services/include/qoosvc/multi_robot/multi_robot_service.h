#pragma once

#include "mr_types.h"
#include "../common/result.h"
#include "../common/service_base.h"
#include <functional>
#include <memory>
#include <string>
#include <vector>

namespace qoosvc::multi_robot {

class MultiRobotService : public ServiceBase {
public:
    MultiRobotService();
    ~MultiRobotService() override;

    // ========================================================================
    // Robot Discovery
    // ========================================================================
    Result<DiscoveryResult> discover_robots();
    Result<void> register_self(const RobotInfo& info);
    Result<void> unregister_self();
    std::vector<RobotInfo> get_known_robots() const;
    Result<RobotInfo> get_robot_info(const std::string& robot_id) const;
    void on_robot_discovered(std::function<void(const RobotInfo&)> callback);
    void on_robot_lost(std::function<void(const std::string&)> callback);

    // ========================================================================
    // Task Allocation
    // ========================================================================
    Result<TaskAllocationResult> allocate_task(const CooperativeTask& task);
    Result<void> accept_task(const std::string& task_id);
    Result<void> reject_task(const std::string& task_id, const std::string& reason);
    Result<void> complete_task(const std::string& task_id);
    Result<void> cancel_task(const std::string& task_id);
    std::vector<CooperativeTask> get_active_tasks() const;
    std::vector<CooperativeTask> get_my_tasks() const;
    void on_task_assigned(std::function<void(const CooperativeTask&)> callback);

    // ========================================================================
    // Cooperative Carrying
    // ========================================================================
    Result<void> start_co_carry(const CoCarryConfig& config);
    Result<void> stop_co_carry();
    Result<void> update_carry_pose(const Pose3D& object_pose);
    CoCarryStatus get_co_carry_status() const;
    void on_carry_update(std::function<void(const CoCarryStatus&)> callback);

    // ========================================================================
    // Information Sharing
    // ========================================================================
    Result<void> share_data(const SharedData& data);
    Result<void> broadcast_data(const SharedData& data);
    void on_shared_data(std::function<void(const SharedData&)> callback);
    std::vector<LoadBalanceInfo> get_cluster_load() const;

    // ========================================================================
    // Service Lifecycle
    // ========================================================================
    bool is_connected() const { return connected_; }

protected:
    Result<void> on_initialize() override;
    Result<void> on_stop() override;

private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
    bool connected_ = false;
};

} // namespace qoosvc::multi_robot
