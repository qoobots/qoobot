// action_adapter.cpp — Implementation
#include "brain_core/ros2_bridge/action_adapter.h"
#include <iostream>

namespace brain_core {

ActionAdapter::ActionAdapter()  = default;
ActionAdapter::~ActionAdapter() = default;

bool ActionAdapter::initialize(void* node_handle) {
    if (!node_handle) return false;
    node_handle_ = node_handle;
    initialized_ = true;
    std::cout << "[ActionAdapter] Initialized." << std::endl;
    return true;
}

bool ActionAdapter::createActionServer(const std::string& action_name, const std::string& action_type) {
    if (!initialized_) return false;
    std::lock_guard<std::mutex> lock(mutex_);
    if (actions_.count(action_name)) return false;

    ActionEntry entry;
    entry.name        = action_name;
    entry.action_type = action_type;
    entry.raw_server  = reinterpret_cast<void*>(1); // stub
    actions_[action_name] = entry;
    std::cout << "[ActionAdapter] Created action server: " << action_name << std::endl;
    return true;
}

void ActionAdapter::removeActionServer(const std::string& action_name) {
    std::lock_guard<std::mutex> lock(mutex_);
    actions_.erase(action_name);
}

bool ActionAdapter::sendGoal(const std::string& action_name, const std::string& goal_json) {
    std::lock_guard<std::mutex> lock(mutex_);
    auto it = actions_.find(action_name);
    if (it == actions_.end()) return false;

    (void)goal_json;
    std::cout << "[ActionAdapter] Goal sent to: " << action_name << std::endl;
    // Stub: simulate result callback
    if (it->second.result_cb) {
        it->second.result_cb(action_name, true, "{\"status\":\"completed\"}");
    }
    return true;
}

bool ActionAdapter::cancelGoal(const std::string& action_name) {
    std::lock_guard<std::mutex> lock(mutex_);
    auto it = actions_.find(action_name);
    if (it == actions_.end()) return false;
    std::cout << "[ActionAdapter] Goal cancelled: " << action_name << std::endl;
    return true;
}

void ActionAdapter::setFeedbackCallback(const std::string& action_name, FeedbackCallback cb) {
    std::lock_guard<std::mutex> lock(mutex_);
    auto it = actions_.find(action_name);
    if (it != actions_.end()) it->second.feedback_cb = std::move(cb);
}

void ActionAdapter::setResultCallback(const std::string& action_name, ResultCallback cb) {
    std::lock_guard<std::mutex> lock(mutex_);
    auto it = actions_.find(action_name);
    if (it != actions_.end()) it->second.result_cb = std::move(cb);
}

bool ActionAdapter::isActionActive(const std::string& action_name) const {
    std::lock_guard<std::mutex> lock(mutex_);
    return actions_.count(action_name) > 0;
}

std::vector<std::string> ActionAdapter::listActions() const {
    std::lock_guard<std::mutex> lock(mutex_);
    std::vector<std::string> result;
    for (const auto& [k, _] : actions_) result.push_back(k);
    return result;
}

} // namespace brain_core
