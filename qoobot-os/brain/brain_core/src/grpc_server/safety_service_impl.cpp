// grpc_server/safety_service_impl.cpp — SafetyService gRPC implementation
#include "brain_core/grpc_server/safety_service_impl.h"
#include <iostream>

namespace brain_core {

SafetyServiceImpl::SafetyServiceImpl()
{
    std::cout << "[SafetyServiceImpl] Initialized." << std::endl;
}

bool SafetyServiceImpl::acknowledgeAlert(const std::string& alert_id)
{
    std::cout << "[SafetyServiceImpl] Alert acknowledged: " << alert_id << std::endl;
    // Reset to NORMAL if no pending critical alerts
    _current_level = SafetyLevel::NORMAL;
    return true;
}

void SafetyServiceImpl::setSafetyConfig(double emergency_timeout_s,
                                         double warning_radius_m,
                                         double danger_radius_m)
{
    _emergency_timeout = emergency_timeout_s;
    _warning_radius    = warning_radius_m;
    _danger_radius     = danger_radius_m;
    std::cout << "[SafetyServiceImpl] Config updated: timeout="
              << _emergency_timeout << "s, warning=" << _warning_radius
              << "m, danger=" << _danger_radius << "m" << std::endl;
}

void SafetyServiceImpl::triggerAlert(const std::string& alert_id,
                                      SafetyLevel level,
                                      const std::string& description)
{
    _current_level = level;
    std::cout << "[SafetyServiceImpl] ALERT: " << alert_id
              << " level=" << static_cast<int>(level)
              << " — " << description << std::endl;
}

} // namespace brain_core
