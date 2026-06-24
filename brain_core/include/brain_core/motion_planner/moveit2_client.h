// motion_planner/moveit2_client.h — MoveIt 2 planning client
#pragma once

#include "brain_core/core_types.h"
#include <string>
#include <vector>
#include <optional>
#include <functional>

namespace brain_core {

/// MoveIt 2 planning request.
struct MoveItPlanRequest {
    std::string group_name{"arm"};
    std::string planner_id{"STOMP"};  // STOMP | RRTConnect | TRRT | PRM
    std::vector<double> start_joints;
    std::vector<double> goal_joints;
    double allowed_planning_time{5.0};
    double goal_position_tolerance{0.01};
    double goal_orientation_tolerance{0.05};
};

/// MoveIt 2 planning result.
struct MoveItPlanResult {
    bool success{false};
    std::string planner_id;
    std::vector<TrajectoryWaypoint> waypoints;
    double planning_time_ms{0.0};
    double trajectory_duration_sec{0.0};
    std::string error_message;
};

class MoveIt2Client {
public:
    MoveIt2Client();

    /// Initialize connection to MoveIt 2 via ROS 2 action.
    bool init(const std::string& move_group_name = "arm");

    /// Plan a trajectory from start to goal joints.
    MoveItPlanResult plan(const MoveItPlanRequest& request);

    /// Plan to a Cartesian pose (linear path).
    MoveItPlanResult planCartesian(double x, double y, double z,
                                    double qx, double qy, double qz, double qw,
                                    double step_size = 0.01,
                                    double jump_threshold = 0.0);

    /// Execute a pre-planned trajectory.
    bool execute(const MoveItPlanResult& plan);

    /// Execute a trajectory asynchronously (non-blocking).
    bool executeAsync(const MoveItPlanResult& plan);

    /// Check if the robot is currently executing a trajectory.
    bool isExecuting() const { return _executing; }

    /// Cancel the current execution.
    void cancelExecution();

    /// Get current robot joint state.
    std::vector<double> getCurrentJoints() const;

    /// Check if MoveIt is connected.
    bool isConnected() const { return _connected; }

private:
    std::string _group_name;
    bool _connected{false};
    bool _executing{false};
};

} // namespace brain_core
