// action_nodes/wait_node.h — Timed or conditional wait
#pragma once

#include "brain_core/core_types.h"
#include <chrono>

namespace brain_core {

class WaitNode {
public:
    WaitNode();

    /// Wait for a fixed duration in seconds.
    void setDuration(double seconds);

    /// Wait until a specific condition is met (polled externally).
    void waitUntil(bool* condition);

    /// Execute the wait. Returns RUNNING during wait,
    /// SUCCESS when duration/condition is met.
    BTNodeStatus execute();

    /// Reset the wait timer.
    void reset();

    /// Get remaining wait time in seconds.
    double remainingSec() const;

private:
    double _duration_sec{1.0};
    bool* _condition{nullptr};
    std::chrono::steady_clock::time_point _start_time;
    bool _started{false};
};

} // namespace brain_core
