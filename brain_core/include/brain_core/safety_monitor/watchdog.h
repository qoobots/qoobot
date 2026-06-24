// safety_monitor/watchdog.h — System heartbeat watchdog
#pragma once

#include "brain_core/core_types.h"
#include <chrono>
#include <atomic>
#include <functional>
#include <string>
#include <thread>

namespace brain_core {

/// Watchdog monitors system health via heartbeat.
/// If a module fails to send heartbeat within timeout, emergency stop is triggered.
class Watchdog {
public:
    using TimeoutCallback = std::function<void(const std::string& module)>;

    Watchdog();

    /// Start the watchdog with a timeout period.
    void start(double timeout_seconds = 1.0);

    /// Stop the watchdog.
    void stop();

    /// Feed the watchdog — called by monitored module.
    void feed(const std::string& module_name);

    /// Check if a module is alive.
    bool isAlive(const std::string& module_name) const;

    /// Get time since last heartbeat for a module.
    double lastHeartbeatSec(const std::string& module_name) const;

    /// Register callback for timeout.
    void onTimeout(TimeoutCallback cb);

private:
    void _watchLoop();

    double _timeout_sec{1.0};
    std::atomic<bool> _running{false};
    std::thread _thread;

    struct ModuleHealth {
        std::string name;
        std::chrono::steady_clock::time_point last_heartbeat;
        std::atomic<bool> alive{true};
    };
    std::vector<std::shared_ptr<ModuleHealth>> _modules;
    mutable std::mutex _mutex;
    TimeoutCallback _callback;
};

} // namespace brain_core
