// action_nodes/navigate_to_node.h — Navigate robot arm to a target pose
#pragma once

#include "brain_core/core_types.h"
#include <string>
#include <vector>
#include <optional>

namespace brain_core {

class NavigateToNode {
public:
    NavigateToNode();

    /// Set the target pose (position + orientation quaternion).
    void setTarget(double x, double y, double z,
                   double qx, double qy, double qz, double qw);

    /// Set target via TrajectoryWaypoint.
    void setTarget(const TrajectoryWaypoint& wp);

    /// Execute the navigation. Returns SUCCESS on arrival,
    /// RUNNING while in motion, FAILURE on unreachable.
    BTNodeStatus execute();

    /// Cancel current navigation.
    void cancel();

    /// Get distance to target in meters.
    double distanceToTarget() const;

    /// Check if target is reachable (IK + collision).
    bool isReachable() const;

private:
    TrajectoryWaypoint _target{};
    bool _active{false};
    double _position_tolerance{0.01};  // 1 cm
    double _orientation_tolerance{0.05};  // ~3 deg
};

} // namespace brain_core
