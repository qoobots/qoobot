// safety_monitor/watchdog.cpp
#include "brain_core/safety_monitor/watchdog.h"
#include <iostream>

namespace brain_core {

Watchdog::Watchdog()
{
    std::cout << "[Watchdog] Initialized." << std::endl;
}

void Watchdog::start(double timeout_seconds)
{
    _timeout_sec = timeout_seconds;
    _running = true;
    _thread = std::thread(&Watchdog::_watchLoop, this);
    std::cout << "[Watchdog] Started (timeout=" << timeout_seconds << "s)." << std::endl;
}

void Watchdog::stop()
{
    _running = false;
    if (_thread.joinable()) {
        _thread.join();
    }
    std::cout << "[Watchdog] Stopped." << std::endl;
}

void Watchdog::feed(const std::string& module_name)
{
    std::lock_guard<std::mutex> lock(_mutex);

    // Find or create module health entry
    for (auto& m : _modules) {
        if (m->name == module_name) {
            m->last_heartbeat = std::chrono::steady_clock::now();
            m->alive = true;
            return;
        }
    }

    auto health = std::make_shared<ModuleHealth>();
    health->name = module_name;
    health->last_heartbeat = std::chrono::steady_clock::now();
    _modules.push_back(health);
}

bool Watchdog::isAlive(const std::string& module_name) const
{
    std::lock_guard<std::mutex> lock(_mutex);
    for (const auto& m : _modules) {
        if (m->name == module_name) return m->alive;
    }
    return false;
}

double Watchdog::lastHeartbeatSec(const std::string& module_name) const
{
    std::lock_guard<std::mutex> lock(_mutex);
    for (const auto& m : _modules) {
        if (m->name == module_name) {
            auto now = std::chrono::steady_clock::now();
            return std::chrono::duration_cast<std::chrono::duration<double>>(
                now - m->last_heartbeat).count();
        }
    }
    return -1.0;
}

void Watchdog::onTimeout(TimeoutCallback cb)
{
    _callback = std::move(cb);
}

void Watchdog::_watchLoop()
{
    while (_running) {
        std::this_thread::sleep_for(std::chrono::milliseconds(100));

        std::lock_guard<std::mutex> lock(_mutex);
        auto now = std::chrono::steady_clock::now();

        for (auto& m : _modules) {
            auto elapsed = std::chrono::duration_cast<std::chrono::duration<double>>(
                now - m->last_heartbeat).count();

            if (elapsed > _timeout_sec && m->alive) {
                m->alive = false;
                std::cerr << "[Watchdog] TIMEOUT: " << m->name
                          << " (" << elapsed << "s)" << std::endl;
                if (_callback) _callback(m->name);
            }
        }
    }
}

} // namespace brain_core
