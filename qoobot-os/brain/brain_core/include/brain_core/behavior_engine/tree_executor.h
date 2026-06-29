// behavior_engine/tree_executor.h — Behavior tree lifecycle & execution
#pragma once

#include "brain_core/core_types.h"
#include <string>
#include <vector>
#include <memory>

namespace brain_core {

/// Manages the lifecycle of a BehaviorTree.CPP tree:
/// load → tick loop → halt → unload.
class TreeExecutor {
public:
    TreeExecutor();
    ~TreeExecutor();

    /// Load a behavior tree from XML content.
    /// Returns false if validation fails.
    bool loadTree(const std::string& bt_xml);

    /// Load from a file path (delegates to BTLoader).
    bool loadTreeFromFile(const std::string& path);

    /// Execute one tick of the behavior tree.
    /// Returns SUCCESS when tree completes, RUNNING otherwise.
    BTNodeStatus tick();

    /// Halt the tree immediately (emergency stop).
    void halt();

    /// Check if a tree is currently loaded.
    bool isLoaded() const { return _loaded; }

    /// Get the current tree status.
    BTNodeStatus status() const { return _status; }

    /// Get the XML of the currently loaded tree.
    const std::string& currentXML() const { return _xml; }

    /// Reset executor state for a new tree.
    void reset();

private:
    bool        _loaded{false};
    BTNodeStatus _status{BTNodeStatus::IDLE};
    std::string _xml;
    void*       _tree_impl{nullptr};  // BT::Tree* (opaque)
};

} // namespace brain_core
