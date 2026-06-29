// node_manager.h — Central ROS 2 node lifecycle management
#pragma once

#include <string>
#include <vector>
#include <memory>
#include <mutex>
#include <functional>

namespace brain_core {

// Forward declarations
struct NodeEntry {
    std::string name;
    void*       raw_node;     // rclcpp::Node*
    bool        active{false};
};

/**
 * @brief Manages the lifecycle of all ROS 2 nodes within brain_core.
 *
 * Responsibilities:
 * - Create and destroy rclcpp::Node instances by name
 * - Track active nodes
 * - Coordinate startup/shutdown ordering
 */
class NodeManager {
public:
    NodeManager();
    ~NodeManager();

    // ── Node Lifecycle ────────────────────────────────────
    bool createNode(const std::string& name, const std::string& ns = "");
    bool destroyNode(const std::string& name);
    bool activateNode(const std::string& name);
    bool deactivateNode(const std::string& name);

    // ── Query ─────────────────────────────────────────────
    bool isActive(const std::string& name) const;
    std::vector<std::string> listActiveNodes() const;
    size_t nodeCount() const { return nodes_.size(); }

    // ── Global helpers ────────────────────────────────────
    void shutdownAll();
    void spinOnce();

private:
    std::vector<NodeEntry> nodes_;
    mutable std::mutex     mutex_;
    bool                   initialized_{false};

    void* createRawNode(const std::string& name, const std::string& ns);
    void  destroyRawNode(void* node);
};

} // namespace brain_core
