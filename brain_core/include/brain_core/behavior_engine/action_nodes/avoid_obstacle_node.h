// action_nodes/avoid_obstacle_node.h — Reactive obstacle avoidance
#pragma once

#include "brain_core/core_types.h"
#include <vector>

namespace brain_core {

/// Obstacle description for avoidance.
struct ObstacleInfo {
    double x, y, z;
    double radius{0.1};  // safety margin
    double velocity_x{0.0}, velocity_y{0.0}, velocity_z{0.0};
};

class AvoidObstacleNode {
public:
    AvoidObstacleNode();

    /// Set obstacle data from perception.
    void setObstacles(const std::vector<ObstacleInfo>& obstacles);

    /// Set safety margin radius (default: 0.15 m).
    void setSafetyMargin(double radius_m);

    /// Execute avoidance maneuver. Returns SUCCESS when clear,
    /// RUNNING while avoiding, FAILURE if no safe path exists.
    BTNodeStatus execute();

    /// Cancel avoidance.
    void cancel();

    /// Check if path is currently clear.
    bool isClear() const { return _path_clear; }

private:
    std::vector<ObstacleInfo> _obstacles;
    double _safety_margin{0.15};
    bool _active{false};
    bool _path_clear{true};
};

} // namespace brain_core
