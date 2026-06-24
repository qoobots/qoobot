// grpc_server/safety_service_impl.h — SafetyService gRPC implementation
#pragma once

#include "brain_core/core_types.h"
#include <string>

namespace brain_core {

/// Implements the SafetyService gRPC service:
/// - GetSafetyStatus: Current safety level and active alerts
/// - AcknowledgeAlert: Human acknowledgment of a safety alert
/// - SetSafetyConfig: Configure safety parameters remotely
class SafetyServiceImpl {
public:
    SafetyServiceImpl();

    /// Get current safety status.
    SafetyLevel getSafetyStatus() const { return _current_level; }

    /// Acknowledge an active safety alert.
    bool acknowledgeAlert(const std::string& alert_id);

    /// Configure safety parameters.
    void setSafetyConfig(double emergency_timeout_s,
                          double warning_radius_m,
                          double danger_radius_m);

    /// Trigger a safety alert (called by safety_monitor).
    void triggerAlert(const std::string& alert_id, SafetyLevel level,
                       const std::string& description);

private:
    SafetyLevel _current_level{SafetyLevel::NORMAL};
    double _emergency_timeout{0.1};
    double _warning_radius{0.3};
    double _danger_radius{0.15};
};

} // namespace brain_core
