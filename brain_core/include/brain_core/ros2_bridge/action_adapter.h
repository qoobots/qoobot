// action_adapter.h — ROS 2 Action client/server abstraction
#pragma once

#include <string>
#include <memory>
#include <functional>
#include <mutex>
#include <unordered_map>

namespace brain_core {

/**
 * @brief Wraps ROS 2 action client and server creation/management.
 *
 * Actions are long-running, goal-oriented, preemptable tasks
 * (e.g., "Navigate to (x,y)").
 */
class ActionAdapter {
public:
    // Feedback callback: (action_name, feedback_json)
    using FeedbackCallback = std::function<void(const std::string&, const std::string&)>;
    // Result callback: (action_name, success, result_json)
    using ResultCallback   = std::function<void(const std::string&, bool, const std::string&)>;

    ActionAdapter();
    ~ActionAdapter();

    bool initialize(void* node_handle);

    // ── Action Server ─────────────────────────────────────
    bool createActionServer(const std::string& action_name, const std::string& action_type);
    void removeActionServer(const std::string& action_name);

    // ── Action Client ─────────────────────────────────────
    bool sendGoal(const std::string& action_name, const std::string& goal_json);
    bool cancelGoal(const std::string& action_name);
    void setFeedbackCallback(const std::string& action_name, FeedbackCallback cb);
    void setResultCallback(const std::string& action_name, ResultCallback cb);

    // ── Query ─────────────────────────────────────────────
    bool isActionActive(const std::string& action_name) const;
    std::vector<std::string> listActions() const;

private:
    void* node_handle_{nullptr};
    bool  initialized_{false};

    struct ActionEntry {
        std::string name;
        std::string action_type;
        void*       raw_server{nullptr};
        void*       raw_client{nullptr};
        FeedbackCallback feedback_cb;
        ResultCallback   result_cb;
    };

    std::unordered_map<std::string, ActionEntry> actions_;
    mutable std::mutex mutex_;
};

} // namespace brain_core
