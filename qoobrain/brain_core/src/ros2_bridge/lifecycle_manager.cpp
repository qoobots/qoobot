// lifecycle_manager.cpp — Implementation
#include "brain_core/ros2_bridge/lifecycle_manager.h"
#include <iostream>
#include <algorithm>

namespace brain_core {

LifecycleManager::LifecycleManager()  = default;
LifecycleManager::~LifecycleManager() { shutdownAll(); }

bool LifecycleManager::registerNode(const std::string& name) {
    std::lock_guard<std::mutex> lock(mutex_);
    if (nodes_.count(name)) return false;
    nodes_[name] = {name, State::UNCONFIGURED};
    std::cout << "[LifecycleManager] Registered node: " << name << std::endl;
    return true;
}

bool LifecycleManager::unregisterNode(const std::string& name) {
    std::lock_guard<std::mutex> lock(mutex_);
    return nodes_.erase(name) > 0;
}

bool LifecycleManager::configure(const std::string& name) {
    std::lock_guard<std::mutex> lock(mutex_);
    auto it = nodes_.find(name);
    if (it == nodes_.end() || it->second.state != State::UNCONFIGURED) return false;
    State old = it->second.state;
    it->second.state = State::INACTIVE;
    if (state_cb_) state_cb_(name, old, State::INACTIVE);
    return true;
}

bool LifecycleManager::activate(const std::string& name) {
    std::lock_guard<std::mutex> lock(mutex_);
    auto it = nodes_.find(name);
    if (it == nodes_.end() || it->second.state != State::INACTIVE) return false;
    State old = it->second.state;
    it->second.state = State::ACTIVE;
    if (state_cb_) state_cb_(name, old, State::ACTIVE);
    return true;
}

bool LifecycleManager::deactivate(const std::string& name) {
    std::lock_guard<std::mutex> lock(mutex_);
    auto it = nodes_.find(name);
    if (it == nodes_.end() || it->second.state != State::ACTIVE) return false;
    State old = it->second.state;
    it->second.state = State::INACTIVE;
    if (state_cb_) state_cb_(name, old, State::INACTIVE);
    return true;
}

bool LifecycleManager::cleanup(const std::string& name) {
    std::lock_guard<std::mutex> lock(mutex_);
    auto it = nodes_.find(name);
    if (it == nodes_.end() || it->second.state != State::INACTIVE) return false;
    State old = it->second.state;
    it->second.state = State::UNCONFIGURED;
    if (state_cb_) state_cb_(name, old, State::UNCONFIGURED);
    return true;
}

bool LifecycleManager::shutdown(const std::string& name) {
    std::lock_guard<std::mutex> lock(mutex_);
    auto it = nodes_.find(name);
    if (it == nodes_.end()) return false;
    State old = it->second.state;
    it->second.state = State::FINALIZED;
    if (state_cb_) state_cb_(name, old, State::FINALIZED);
    return true;
}

bool LifecycleManager::configureAll() {
    bool ok = true;
    for (const auto& [name, _] : nodes_) {
        if (!configure(name)) ok = false;
    }
    return ok;
}

bool LifecycleManager::activateAll() {
    bool ok = true;
    for (const auto& [name, _] : nodes_) {
        if (!activate(name)) ok = false;
    }
    return ok;
}

bool LifecycleManager::shutdownAll() {
    bool ok = true;
    for (const auto& [name, _] : nodes_) {
        if (!shutdown(name)) ok = false;
    }
    return ok;
}

LifecycleManager::State LifecycleManager::getState(const std::string& name) const {
    std::lock_guard<std::mutex> lock(mutex_);
    auto it = nodes_.find(name);
    return (it != nodes_.end()) ? it->second.state : State::UNCONFIGURED;
}

std::vector<std::string> LifecycleManager::nodesInState(State state) const {
    std::lock_guard<std::mutex> lock(mutex_);
    std::vector<std::string> result;
    for (const auto& [name, ns] : nodes_) {
        if (ns.state == state) result.push_back(name);
    }
    return result;
}

bool LifecycleManager::allActive() const {
    std::lock_guard<std::mutex> lock(mutex_);
    if (nodes_.empty()) return false;
    for (const auto& [_, ns] : nodes_) {
        if (ns.state != State::ACTIVE) return false;
    }
    return true;
}

void LifecycleManager::setStateChangeCallback(StateChangeCallback cb) {
    std::lock_guard<std::mutex> lock(mutex_);
    state_cb_ = std::move(cb);
}

const char* LifecycleManager::stateToString(State s) {
    switch (s) {
        case State::UNCONFIGURED: return "UNCONFIGURED";
        case State::INACTIVE:     return "INACTIVE";
        case State::ACTIVE:       return "ACTIVE";
        case State::FINALIZED:    return "FINALIZED";
        case State::ERROR:        return "ERROR";
        default:                  return "UNKNOWN";
    }
}

} // namespace brain_core
