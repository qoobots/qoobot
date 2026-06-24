// safety_monitor/force_monitor.h — Joint force/torque monitoring
#pragma once

#include "brain_core/core_types.h"
#include <vector>
#include <string>

namespace brain_core {

/// Force/torque limits per joint.
struct JointForceLimits {
    std::string joint_name;
    double max_torque_nm{50.0};
    double max_force_n{100.0};
    double warning_threshold{0.8};  // 80% of max → warning
};

/// Force monitoring result.
struct ForceMonitorResult {
    bool all_ok{true};
    std::string warning_joint;
    double current_value{0.0};
    double limit_value{0.0};
};

class ForceMonitor {
public:
    ForceMonitor();

    /// Set force limits for joints.
    void setLimits(const std::vector<JointForceLimits>& limits);

    /// Update current joint efforts.
    void updateEfforts(const std::vector<double>& efforts);

    /// Check if any joint exceeds limits.
    ForceMonitorResult check();

    /// Get the last check result.
    const ForceMonitorResult& lastResult() const { return _last_result; }

private:
    std::vector<JointForceLimits> _limits;
    std::vector<double> _current_efforts;
    ForceMonitorResult _last_result;
};

} // namespace brain_core
