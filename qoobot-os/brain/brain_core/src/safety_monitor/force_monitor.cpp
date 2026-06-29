// safety_monitor/force_monitor.cpp
#include "brain_core/safety_monitor/force_monitor.h"
#include <iostream>

namespace brain_core {

ForceMonitor::ForceMonitor()
{
    std::cout << "[ForceMonitor] Initialized." << std::endl;
}

void ForceMonitor::setLimits(const std::vector<JointForceLimits>& limits)
{
    _limits = limits;
}

void ForceMonitor::updateEfforts(const std::vector<double>& efforts)
{
    _current_efforts = efforts;
}

ForceMonitorResult ForceMonitor::check()
{
    _last_result.all_ok = true;

    for (size_t i = 0; i < _limits.size() && i < _current_efforts.size(); ++i) {
        double limit = _limits[i].max_torque_nm;
        double warning = limit * _limits[i].warning_threshold;

        if (std::abs(_current_efforts[i]) > warning) {
            _last_result.warning_joint = _limits[i].joint_name;
            _last_result.current_value = std::abs(_current_efforts[i]);
            _last_result.limit_value = limit;

            if (std::abs(_current_efforts[i]) > limit) {
                _last_result.all_ok = false;
                std::cerr << "[ForceMonitor] LIMIT EXCEEDED: " << _limits[i].joint_name
                          << " (" << _current_efforts[i] << " > " << limit << " Nm)" << std::endl;
            }
        }
    }

    return _last_result;
}

} // namespace brain_core
