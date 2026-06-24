// behavior_engine/node_factory.h — Factory for BehaviorTree.CPP node creation
#pragma once

#include <string>
#include <memory>
#include <unordered_map>
#include <functional>

namespace brain_core {

/// Forward-declared opaque handle for BT::TreeNode.
using BTNodePtr = void*;

/// Factory registry that maps node type names to constructors.
/// Supports both built-in BT.CPP nodes and custom action nodes.
class NodeFactory {
public:
    using NodeCreator = std::function<BTNodePtr(const std::string& name)>;

    NodeFactory();

    /// Register a custom node type.
    void registerType(const std::string& type, NodeCreator creator);

    /// Create a node instance by type name and instance name.
    /// Returns nullptr if type is unknown.
    BTNodePtr createNode(const std::string& type, const std::string& name);

    /// Check if a node type is registered.
    bool hasType(const std::string& type) const;

    /// List all registered node types.
    std::vector<std::string> registeredTypes() const;

    /// Register all built-in action nodes (NavigateTo, Pick, Place, etc.).
    void registerBuiltinNodes();

private:
    std::unordered_map<std::string, NodeCreator> _registry;
};

} // namespace brain_core
