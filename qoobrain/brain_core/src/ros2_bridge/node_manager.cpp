// node_manager.cpp — Implementation
#include "brain_core/ros2_bridge/node_manager.h"
#include <algorithm>
#include <iostream>

namespace brain_core {

NodeManager::NodeManager()  = default;
NodeManager::~NodeManager() { shutdownAll(); }

bool NodeManager::createNode(const std::string& name, const std::string& ns) {
    std::lock_guard<std::mutex> lock(mutex_);
    auto it = std::find_if(nodes_.begin(), nodes_.end(),
        [&](const NodeEntry& e) { return e.name == name; });
    if (it != nodes_.end()) return false; // already exists

    NodeEntry entry;
    entry.name = name;
    entry.raw_node = createRawNode(name, ns);
    entry.active   = false;
    nodes_.push_back(entry);
    std::cout << "[NodeManager] Created node: " << name << std::endl;
    return true;
}

bool NodeManager::destroyNode(const std::string& name) {
    std::lock_guard<std::mutex> lock(mutex_);
    auto it = std::find_if(nodes_.begin(), nodes_.end(),
        [&](const NodeEntry& e) { return e.name == name; });
    if (it == nodes_.end()) return false;

    if (it->active) deactivateNode(name);
    destroyRawNode(it->raw_node);
    nodes_.erase(it);
    std::cout << "[NodeManager] Destroyed node: " << name << std::endl;
    return true;
}

bool NodeManager::activateNode(const std::string& name) {
    std::lock_guard<std::mutex> lock(mutex_);
    auto it = std::find_if(nodes_.begin(), nodes_.end(),
        [&](const NodeEntry& e) { return e.name == name; });
    if (it == nodes_.end()) return false;
    it->active = true;
    return true;
}

bool NodeManager::deactivateNode(const std::string& name) {
    std::lock_guard<std::mutex> lock(mutex_);
    auto it = std::find_if(nodes_.begin(), nodes_.end(),
        [&](const NodeEntry& e) { return e.name == name; });
    if (it == nodes_.end()) return false;
    it->active = false;
    return true;
}

bool NodeManager::isActive(const std::string& name) const {
    std::lock_guard<std::mutex> lock(mutex_);
    auto it = std::find_if(nodes_.begin(), nodes_.end(),
        [&](const NodeEntry& e) { return e.name == name; });
    return (it != nodes_.end()) && it->active;
}

std::vector<std::string> NodeManager::listActiveNodes() const {
    std::lock_guard<std::mutex> lock(mutex_);
    std::vector<std::string> result;
    for (const auto& e : nodes_) {
        if (e.active) result.push_back(e.name);
    }
    return result;
}

void NodeManager::shutdownAll() {
    std::lock_guard<std::mutex> lock(mutex_);
    for (auto& e : nodes_) {
        if (e.raw_node) {
            destroyRawNode(e.raw_node);
            e.raw_node = nullptr;
        }
    }
    nodes_.clear();
}

void NodeManager::spinOnce() {
    // Placeholder: in real ROS 2, call rclcpp::spin_some(node)
    // For now, this is a stub for build verification
}

// ── Private ───────────────────────────────────────────────
void* NodeManager::createRawNode(const std::string& name, const std::string& ns) {
    // Stub: returns non-null opaque handle for build verification
    // Real impl: auto node = std::make_shared<rclcpp::Node>(name, ns);
    static int id = 0;
    return reinterpret_cast<void*>(static_cast<intptr_t>(++id));
}

void NodeManager::destroyRawNode(void* node) {
    // Stub: no-op; real impl would reset shared_ptr
    (void)node;
}

} // namespace brain_core
