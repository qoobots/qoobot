// motion_planner/moveit2_client.cpp — MoveIt 2 planning client
#include "brain_core/motion_planner/moveit2_client.h"
#include <iostream>
#include <chrono>
#include <thread>

namespace brain_core {

MoveIt2Client::MoveIt2Client()
{
    std::cout << "[MoveIt2Client] Initialized." << std::endl;
}

bool MoveIt2Client::init(const std::string& move_group_name)
{
    _group_name = move_group_name;
    _connected = true;
    std::cout << "[MoveIt2Client] Connected to MoveIt 2 (group="
              << _group_name << ")." << std::endl;
    return true;
}

MoveItPlanResult MoveIt2Client::plan(const MoveItPlanRequest& request)
{
    MoveItPlanResult result;
    result.planner_id = request.planner_id;

    if (!_connected) {
        result.success = false;
        result.error_message = "Not connected to MoveIt 2";
        return result;
    }

    // Stub: simulate planning
    auto t0 = std::chrono::steady_clock::now();

    int num_joints = request.goal_joints.empty() ? 6
                    : static_cast<int>(request.goal_joints.size());

    // Generate a linear interpolation as the planned trajectory
    double duration = 2.0;
    for (int i = 0; i <= 50; ++i) {
        double t = static_cast<double>(i) / 50.0;
        TrajectoryWaypoint wp;
        wp.x = 0.3 + 0.2 * t;
        wp.y = 0.2 * std::sin(t * 3.14159);
        wp.z = 0.25 + 0.1 * t;
        wp.qx = 0.0; wp.qy = 0.0; wp.qz = 0.0; wp.qw = 1.0;
        wp.time_from_start_sec = t * duration;
        result.waypoints.push_back(wp);
    }

    auto t1 = std::chrono::steady_clock::now();
    result.planning_time_ms = std::chrono::duration_cast<std::chrono::milliseconds>(
        t1 - t0).count();
    result.trajectory_duration_sec = duration;
    result.success = true;

    std::cout << "[MoveIt2Client] Plan computed (" << result.planning_time_ms
              << " ms, " << result.waypoints.size() << " waypoints, "
              << result.trajectory_duration_sec << " s)" << std::endl;

    return result;
}

MoveItPlanResult MoveIt2Client::planCartesian(
    double x, double y, double z,
    double qx, double qy, double qz, double qw,
    double step_size, double jump_threshold)
{
    (void)step_size;
    (void)jump_threshold;

    MoveItPlanRequest req;
    req.planner_id = "Cartesian";
    req.group_name = _group_name;
    return plan(req);
}

bool MoveIt2Client::execute(const MoveItPlanResult& plan)
{
    if (!plan.success) {
        std::cerr << "[MoveIt2Client] Cannot execute: plan failed." << std::endl;
        return false;
    }

    _executing = true;
    std::cout << "[MoveIt2Client] Executing trajectory ("
              << plan.waypoints.size() << " waypoints, "
              << plan.trajectory_duration_sec << " s)..." << std::endl;

    // Stub: simulate execution duration
    std::this_thread::sleep_for(
        std::chrono::milliseconds(100));  // short for stub

    _executing = false;
    std::cout << "[MoveIt2Client] Execution complete." << std::endl;
    return true;
}

bool MoveIt2Client::executeAsync(const MoveItPlanResult& plan)
{
    if (!plan.success) return false;

    _executing = true;
    std::cout << "[MoveIt2Client] Async execution started." << std::endl;
    // In full build: launch async ROS 2 action client
    return true;
}

void MoveIt2Client::cancelExecution()
{
    _executing = false;
    std::cout << "[MoveIt2Client] Execution cancelled." << std::endl;
}

std::vector<double> MoveIt2Client::getCurrentJoints() const
{
    // Stub: return home position
    return {0.0, 0.3, 3.14, -1.57, 0.0, 0.0};
}

} // namespace brain_core
