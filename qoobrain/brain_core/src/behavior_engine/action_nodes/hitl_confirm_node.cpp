// action_nodes/hitl_confirm_node.cpp
#include "brain_core/behavior_engine/action_nodes/hitl_confirm_node.h"
#include <iostream>

namespace brain_core {

HitlConfirmNode::HitlConfirmNode()
{
    std::cout << "[HitlConfirmNode] Initialized." << std::endl;
}

void HitlConfirmNode::setPrompt(const std::string& prompt)
{
    _prompt = prompt;
}

void HitlConfirmNode::setTimeout(double seconds)
{
    _timeout_sec = seconds;
}

void HitlConfirmNode::setAutoApprove(bool approve)
{
    _auto_approve = approve;
}

BTNodeStatus HitlConfirmNode::execute()
{
    if (!_active) {
        _active = true;
        _decision = HITLDecision::PENDING;
        _start_time = std::chrono::steady_clock::now();

        std::cout << "[HitlConfirmNode] Prompt: \"" << _prompt
                  << "\" (timeout=" << _timeout_sec << "s, auto-approve="
                  << (_auto_approve ? "yes" : "no") << ")" << std::endl;
        return BTNodeStatus::RUNNING;
    }

    // Check for user decision
    HITLDecision current = _decision.load();
    if (current == HITLDecision::APPROVED) {
        std::cout << "[HitlConfirmNode] User APPROVED." << std::endl;
        _active = false;
        if (_callback) _callback(HITLDecision::APPROVED);
        return BTNodeStatus::SUCCESS;
    }
    if (current == HITLDecision::REJECTED) {
        std::cout << "[HitlConfirmNode] User REJECTED." << std::endl;
        _active = false;
        if (_callback) _callback(HITLDecision::REJECTED);
        return BTNodeStatus::FAILURE;
    }
    if (current == HITLDecision::CANCELLED) {
        std::cout << "[HitlConfirmNode] Cancelled." << std::endl;
        _active = false;
        return BTNodeStatus::FAILURE;
    }

    // Check timeout
    auto now = std::chrono::steady_clock::now();
    auto elapsed = std::chrono::duration_cast<std::chrono::duration<double>>(
        now - _start_time).count();

    if (elapsed >= _timeout_sec) {
        if (_auto_approve) {
            std::cout << "[HitlConfirmNode] Timeout — auto-APPROVED ("
                      << elapsed << "s)." << std::endl;
            _decision = HITLDecision::TIMEOUT;
            _active = false;
            if (_callback) _callback(HITLDecision::TIMEOUT);
            return BTNodeStatus::SUCCESS;
        } else {
            std::cout << "[HitlConfirmNode] Timeout — auto-REJECTED ("
                      << elapsed << "s)." << std::endl;
            _decision = HITLDecision::TIMEOUT;
            _active = false;
            if (_callback) _callback(HITLDecision::TIMEOUT);
            return BTNodeStatus::FAILURE;
        }
    }

    return BTNodeStatus::RUNNING;
}

void HitlConfirmNode::setUserDecision(HITLDecision decision)
{
    _decision = decision;
    std::cout << "[HitlConfirmNode] Decision override: "
              << static_cast<int>(decision) << std::endl;
}

void HitlConfirmNode::reset()
{
    _active = false;
    _decision = HITLDecision::PENDING;
}

void HitlConfirmNode::onDecision(DecisionCallback cb)
{
    _callback = std::move(cb);
}

void HitlConfirmNode::cancel()
{
    _decision = HITLDecision::CANCELLED;
    _active = false;
}

} // namespace brain_core
