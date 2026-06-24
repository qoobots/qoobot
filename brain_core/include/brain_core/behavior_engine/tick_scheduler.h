// behavior_engine/tick_scheduler.h — Rate-limited behavior tree ticking
#pragma once

#include "brain_core/core_types.h"
#include <chrono>
#include <atomic>

namespace brain_core {

/// Scheduler that drives the behavior tree at a fixed rate.
/// Thread-safe shouldTick() pattern suitable for real-time loops.
class TickScheduler {
public:
    TickScheduler();

    /// Start ticking at the given rate (Hz). Default: 50 Hz.
    void start(int rate_hz = 50);

    /// Stop the scheduler.
    void stop();

    /// Returns true when it's time for the next tick.
    /// Blocks briefly (1 ms) between polls to avoid busy-wait.
    bool shouldTick();

    /// Get the current tick rate in Hz.
    int rateHz() const { return _rate_hz; }

    /// Get the number of ticks since start.
    uint64_t tickCount() const { return _tick_count; }

    /// Check if scheduler is active.
    bool isActive() const { return _active; }

private:
    int _rate_hz{50};
    int _interval_ms{20};
    std::atomic<bool> _active{false};
    std::atomic<uint64_t> _tick_count{0};
    std::chrono::steady_clock::time_point _last_tick;
};

} // namespace brain_core
