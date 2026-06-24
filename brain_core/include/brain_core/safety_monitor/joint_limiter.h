// safety_monitor/joint_limiter.h — Joint position/velocity/acceleration limits
#pragma once

#include "brain_core/core_types.h"
#include <vector>
#include <string>

namespace brain_core {

/// Per-joint limit configuration.
struct JointLimit {
    std::string name;
    double position_min{-3.14};
    double position_max{3.14};
    double velocity_max{2.0};      // rad/s
    double acceleration_max{5.0};  // rad/s^2
    bool   soft_limit{true};       // decelerate before hard limit
};

/// Limit violation record.
struct LimitViolation {
    std::string joint_name;
    std::string limit_type;  // "position", "velocity", "acceleration"
    double actual_value;
    double limit_value;
};

class JointLimiter {
public:
    JointLimiter();

    /// Set joint limits.
    void setLimits(const std::vector<JointLimit>& limits);

    /// Validate and clamp a trajectory based on limits.
    /// Returns clamped trajectory + list of violations.
    std::vector<LimitViolation> validate(const std::vector<double>& positions,
                                          const std::vector<double>& velocities,
                                          const std::vector<double>& accelerations);

    /// Clamp a single joint value to its limits.
    double clampPosition(int joint_idx, double value) const;
    double clampVelocity(int joint_idx, double value) const;

    /// Check if trajectory is within all limits.
    bool isWithinLimits(const Trajectory& traj) const;

private:
    std::vector<JointLimit> _limits;
};

} // namespace brain_core
