// behavior_engine/tick_scheduler.cpp — Rate-limited BT ticking
#include "brain_core/behavior_engine/tick_scheduler.h"
#include <iostream>
#include <thread>

namespace brain_core {

TickScheduler::TickScheduler()
    : _last_tick(std::chrono::steady_clock::now())
{
    std::cout << "[TickScheduler] Initialized." << std::endl;
}

void TickScheduler::start(int rate_hz)
{
    _rate_hz = rate_hz;
    _interval_ms = (rate_hz > 0) ? (1000 / rate_hz) : 20;
    _tick_count = 0;
    _active = true;
    std::cout << "[TickScheduler] Started at " << rate_hz << " Hz (interval="
              << _interval_ms << " ms)" << std::endl;
}

void TickScheduler::stop()
{
    _active = false;
    std::cout << "[TickScheduler] Stopped. Total ticks: " << _tick_count << std::endl;
}

bool TickScheduler::shouldTick()
{
    if (!_active) return false;

    auto now = std::chrono::steady_clock::now();
    auto elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(
        now - _last_tick).count();

    if (elapsed >= _interval_ms) {
        _last_tick = now;
        _tick_count++;
        return true;
    }

    // Sleep briefly to avoid busy-wait
    std::this_thread::sleep_for(std::chrono::milliseconds(1));
    return false;
}

} // namespace brain_core
