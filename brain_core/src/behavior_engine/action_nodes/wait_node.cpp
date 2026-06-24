// action_nodes/wait_node.cpp
#include "brain_core/behavior_engine/action_nodes/wait_node.h"
#include <iostream>

namespace brain_core {

WaitNode::WaitNode()
{
    std::cout << "[WaitNode] Initialized." << std::endl;
}

void WaitNode::setDuration(double seconds)
{
    _duration_sec = seconds;
    _condition = nullptr;
}

void WaitNode::waitUntil(bool* condition)
{
    _condition = condition;
}

BTNodeStatus WaitNode::execute()
{
    if (!_started) {
        _started = true;
        _start_time = std::chrono::steady_clock::now();
        std::cout << "[WaitNode] Waiting " << _duration_sec << "s..." << std::endl;
        return BTNodeStatus::RUNNING;
    }

    // Check condition-based wait
    if (_condition && *_condition) {
        std::cout << "[WaitNode] Condition met." << std::endl;
        _started = false;
        return BTNodeStatus::SUCCESS;
    }

    // Check time-based wait
    auto now = std::chrono::steady_clock::now();
    auto elapsed = std::chrono::duration_cast<std::chrono::duration<double>>(
        now - _start_time).count();

    if (elapsed >= _duration_sec) {
        std::cout << "[WaitNode] Wait complete (" << elapsed << "s)." << std::endl;
        _started = false;
        return BTNodeStatus::SUCCESS;
    }

    return BTNodeStatus::RUNNING;
}

void WaitNode::reset()
{
    _started = false;
    _condition = nullptr;
}

double WaitNode::remainingSec() const
{
    if (!_started) return _duration_sec;
    auto now = std::chrono::steady_clock::now();
    auto elapsed = std::chrono::duration_cast<std::chrono::duration<double>>(
        now - _start_time).count();
    return std::max(0.0, _duration_sec - elapsed);
}

} // namespace brain_core
