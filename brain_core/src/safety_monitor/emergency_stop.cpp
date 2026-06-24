// safety_monitor/emergency_stop.cpp
#include "brain_core/safety_monitor/emergency_stop.h"
#include <iostream>

namespace brain_core {

EmergencyStop::EmergencyStop()
{
    std::cout << "[EmergencyStop] Initialized." << std::endl;
}

void EmergencyStop::trigger(const std::string& reason)
{
    bool was_active = _active.exchange(true);
    _reason = reason;
    _triggered_at = std::chrono::system_clock::now();

    if (!was_active) {
        std::cout << "[EmergencyStop] TRIGGERED — Reason: " << reason << std::endl;
        if (_callback) _callback(reason);
    }
}

bool EmergencyStop::reset()
{
    if (!_active) return true;

    _active = false;
    std::cout << "[EmergencyStop] Reset." << std::endl;
    return true;
}

void EmergencyStop::onStop(StopCallback cb)
{
    _callback = std::move(cb);
}

} // namespace brain_core
