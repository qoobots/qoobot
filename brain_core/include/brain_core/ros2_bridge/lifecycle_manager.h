// lifecycle_manager.h — ROS 2 Lifecycle Node management
#pragma once

#include <string>
#include <vector>
#include <memory>
#include <mutex>
#include <functional>
#include <unordered_map>

namespace brain_core {

/**
 * @brief Manages lifecycle state transitions for managed nodes.
 *
 * Supports ROS 2 lifecycle state machine:
 *   Unconfigured → Inactive → Active → (Finalized)
 */
class LifecycleManager {
public:
    enum class State {
        UNCONFIGURED,
        INACTIVE,
        ACTIVE,
        FINALIZED,
        ERROR,
    };

    using StateChangeCallback = std::function<void(const std::string& node, State old_state, State new_state)>;

    LifecycleManager();
    ~LifecycleManager();

    // ── Registration ──────────────────────────────────────
    bool registerNode(const std::string& name);
    bool unregisterNode(const std::string& name);

    // ── State Transitions ─────────────────────────────────
    bool configure(const std::string& name);
    bool activate(const std::string& name);
    bool deactivate(const std::string& name);
    bool cleanup(const std::string& name);
    bool shutdown(const std::string& name);

    // ── Batch Operations ──────────────────────────────────
    bool configureAll();
    bool activateAll();
    bool shutdownAll();

    // ── Query ─────────────────────────────────────────────
    State getState(const std::string& name) const;
    std::vector<std::string> nodesInState(State state) const;
    bool allActive() const;

    // ── Callbacks ─────────────────────────────────────────
    void setStateChangeCallback(StateChangeCallback cb);

    // ── Utility ───────────────────────────────────────────
    static const char* stateToString(State s);

private:
    struct NodeState {
        std::string name;
        State       state{State::UNCONFIGURED};
    };

    std::unordered_map<std::string, NodeState> nodes_;
    mutable std::mutex mutex_;
    StateChangeCallback state_cb_;
};

} // namespace brain_core
