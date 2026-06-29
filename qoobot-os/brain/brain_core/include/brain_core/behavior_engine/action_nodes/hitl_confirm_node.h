// action_nodes/hitl_confirm_node.h — Human-in-the-loop confirmation
#pragma once

#include "brain_core/core_types.h"
#include <string>
#include <atomic>
#include <chrono>
#include <functional>

namespace brain_core {

/// HITL confirmation states.
enum class HITLDecision {
    PENDING,
    APPROVED,
    REJECTED,
    TIMEOUT,       // auto-approve after timeout
    CANCELLED,
};

class HitlConfirmNode {
public:
    using DecisionCallback = std::function<void(HITLDecision)>;

    HitlConfirmNode();

    /// Set the question/prompt to show the user.
    void setPrompt(const std::string& prompt);

    /// Set timeout in seconds (default: 3.0, per requirement).
    void setTimeout(double seconds);

    /// Set whether to auto-approve on timeout (default: true).
    void setAutoApprove(bool approve);

    /// Execute the HITL confirmation cycle.
    /// Returns RUNNING while waiting for decision,
    /// SUCCESS if approved/timeout-approve, FAILURE if rejected.
    BTNodeStatus execute();

    /// External user decision input (from WebSocket/gRPC).
    void setUserDecision(HITLDecision decision);

    /// Get current decision state.
    HITLDecision currentDecision() const { return _decision.load(); }

    /// Reset the node for the next confirmation.
    void reset();

    /// Register callback for decision events.
    void onDecision(DecisionCallback cb);

    /// Cancel the confirmation.
    void cancel();

private:
    std::string _prompt;
    double _timeout_sec{3.0};
    bool _auto_approve{true};
    std::atomic<HITLDecision> _decision{HITLDecision::PENDING};
    std::chrono::steady_clock::time_point _start_time;
    DecisionCallback _callback;
    bool _active{false};
};

} // namespace brain_core
