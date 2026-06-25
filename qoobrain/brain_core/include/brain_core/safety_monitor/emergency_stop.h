// safety_monitor/emergency_stop.h — Emergency stop mechanism
#pragma once

#include "brain_core/core_types.h"
#include <string>
#include <atomic>
#include <functional>
#include <chrono>

namespace brain_core {

class EmergencyStop {
public:
    using StopCallback = std::function<void(const std::string& reason)>;

    EmergencyStop();

    /// Trigger emergency stop with reason.
    void trigger(const std::string& reason);

    /// Reset emergency stop (requires explicit acknowledgment).
    bool reset();

    /// Check if emergency stop is active.
    bool isActive() const { return _active; }

    /// Get the reason for the last trigger.
    const std::string& reason() const { return _reason; }

    /// Get timestamp of last trigger.
    std::chrono::system_clock::time_point triggeredAt() const { return _triggered_at; }

    /// Register callback on stop trigger.
    void onStop(StopCallback cb);

private:
    std::atomic<bool> _active{false};
    std::string _reason;
    std::chrono::system_clock::time_point _triggered_at;
    StopCallback _callback;
};

} // namespace brain_core
