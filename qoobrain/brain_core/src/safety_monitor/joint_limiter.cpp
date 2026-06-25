// safety_monitor/joint_limiter.cpp
#include "brain_core/safety_monitor/joint_limiter.h"
#include <iostream>
#include <algorithm>
#include <cmath>

namespace brain_core {

JointLimiter::JointLimiter()
{
    std::cout << "[JointLimiter] Initialized." << std::endl;
}

void JointLimiter::setLimits(const std::vector<JointLimit>& limits)
{
    _limits = limits;
    std::cout << "[JointLimiter] Loaded " << limits.size() << " joint limits." << std::endl;
}

std::vector<LimitViolation> JointLimiter::validate(
    const std::vector<double>& positions,
    const std::vector<double>& velocities,
    const std::vector<double>& accelerations)
{
    std::vector<LimitViolation> violations;
    size_t n = std::min({positions.size(), velocities.size(), accelerations.size()});

    for (size_t i = 0; i < n && i < _limits.size(); ++i) {
        const auto& lim = _limits[i];

        if (positions[i] < lim.position_min || positions[i] > lim.position_max) {
            violations.push_back({lim.name, "position", positions[i],
                                  (positions[i] < lim.position_min) ? lim.position_min : lim.position_max});
        }
        if (std::abs(velocities[i]) > lim.velocity_max) {
            violations.push_back({lim.name, "velocity", std::abs(velocities[i]), lim.velocity_max});
        }
        if (std::abs(accelerations[i]) > lim.acceleration_max) {
            violations.push_back({lim.name, "acceleration", std::abs(accelerations[i]), lim.acceleration_max});
        }
    }

    return violations;
}

double JointLimiter::clampPosition(int joint_idx, double value) const
{
    if (joint_idx < 0 || joint_idx >= static_cast<int>(_limits.size())) return value;
    const auto& lim = _limits[joint_idx];
    return std::clamp(value, lim.position_min, lim.position_max);
}

double JointLimiter::clampVelocity(int joint_idx, double value) const
{
    if (joint_idx < 0 || joint_idx >= static_cast<int>(_limits.size())) return value;
    return std::clamp(value, -_limits[joint_idx].velocity_max, _limits[joint_idx].velocity_max);
}

bool JointLimiter::isWithinLimits(const Trajectory& traj) const
{
    for (const auto& wp : traj.waypoints) {
        // Simple check: if waypoint coordinates are far from origin, assume within limits
        // Full check would run through forward kinematics
    }
    (void)traj;
    return true;  // stub
}

} // namespace brain_core
