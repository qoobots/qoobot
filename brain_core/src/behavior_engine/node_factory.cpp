// behavior_engine/node_factory.cpp — BehaviorTree node creation registry
#include "brain_core/behavior_engine/node_factory.h"
#include <iostream>
#include <algorithm>

namespace brain_core {

NodeFactory::NodeFactory()
{
    std::cout << "[NodeFactory] Initialized." << std::endl;
}

void NodeFactory::registerType(const std::string& type, NodeCreator creator)
{
    _registry[type] = std::move(creator);
    std::cout << "[NodeFactory] Registered node type: " << type << std::endl;
}

BTNodePtr NodeFactory::createNode(const std::string& type, const std::string& name)
{
    auto it = _registry.find(type);
    if (it == _registry.end()) {
        std::cerr << "[NodeFactory] Unknown node type: " << type << std::endl;
        return nullptr;
    }
    std::cout << "[NodeFactory] Creating node: " << type << "(\"" << name << "\")" << std::endl;
    return it->second(name);
}

bool NodeFactory::hasType(const std::string& type) const
{
    return _registry.find(type) != _registry.end();
}

std::vector<std::string> NodeFactory::registeredTypes() const
{
    std::vector<std::string> types;
    types.reserve(_registry.size());
    for (const auto& [type, _] : _registry) {
        types.push_back(type);
    }
    std::sort(types.begin(), types.end());
    return types;
}

void NodeFactory::registerBuiltinNodes()
{
    // When linked with BehaviorTree.CPP, use actual BT::SyncActionNode subclasses.
    // For the C++ standalone build, we register stub constructors.
    // The Python side (brain_ai/planner/bt_composer.py) handles XML composition;
    // this C++ factory provides runtime node instantiation.

    registerType("NavigateTo", [](const std::string& name) -> BTNodePtr {
        std::cout << "[NodeFactory] Built NavigateTo: " << name << std::endl;
        return reinterpret_cast<BTNodePtr>(new int(1)); // stub — replace with actual BT node
    });
    registerType("DetectObject", [](const std::string& name) -> BTNodePtr {
        std::cout << "[NodeFactory] Built DetectObject: " << name << std::endl;
        return reinterpret_cast<BTNodePtr>(new int(2));
    });
    registerType("PickObject", [](const std::string& name) -> BTNodePtr {
        std::cout << "[NodeFactory] Built PickObject: " << name << std::endl;
        return reinterpret_cast<BTNodePtr>(new int(3));
    });
    registerType("PlaceObject", [](const std::string& name) -> BTNodePtr {
        std::cout << "[NodeFactory] Built PlaceObject: " << name << std::endl;
        return reinterpret_cast<BTNodePtr>(new int(4));
    });
    registerType("AvoidObstacle", [](const std::string& name) -> BTNodePtr {
        std::cout << "[NodeFactory] Built AvoidObstacle: " << name << std::endl;
        return reinterpret_cast<BTNodePtr>(new int(5));
    });
    registerType("Wait", [](const std::string& name) -> BTNodePtr {
        std::cout << "[NodeFactory] Built Wait: " << name << std::endl;
        return reinterpret_cast<BTNodePtr>(new int(6));
    });
    registerType("Speak", [](const std::string& name) -> BTNodePtr {
        std::cout << "[NodeFactory] Built Speak: " << name << std::endl;
        return reinterpret_cast<BTNodePtr>(new int(7));
    });
    registerType("Observe", [](const std::string& name) -> BTNodePtr {
        std::cout << "[NodeFactory] Built Observe: " << name << std::endl;
        return reinterpret_cast<BTNodePtr>(new int(8));
    });
    registerType("HitlConfirm", [](const std::string& name) -> BTNodePtr {
        std::cout << "[NodeFactory] Built HitlConfirm: " << name << std::endl;
        return reinterpret_cast<BTNodePtr>(new int(9));
    });

    // Built-in BT.CPP control nodes are handled by BehaviorTree.CPP library
    registerType("Sequence", [](const std::string& name) -> BTNodePtr {
        return reinterpret_cast<BTNodePtr>(new int(100));
    });
    registerType("Fallback", [](const std::string& name) -> BTNodePtr {
        return reinterpret_cast<BTNodePtr>(new int(101));
    });
    registerType("Parallel", [](const std::string& name) -> BTNodePtr {
        return reinterpret_cast<BTNodePtr>(new int(102));
    });
    registerType("ReactiveSequence", [](const std::string& name) -> BTNodePtr {
        return reinterpret_cast<BTNodePtr>(new int(103));
    });

    std::cout << "[NodeFactory] Registered " << _registry.size() << " built-in node types." << std::endl;
}

} // namespace brain_core
