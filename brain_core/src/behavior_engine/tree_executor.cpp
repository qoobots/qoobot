// behavior_engine/tree_executor.cpp — Behavior tree lifecycle & execution
#include "brain_core/behavior_engine/tree_executor.h"
#include "brain_core/behavior_engine/bt_loader.h"
#include "brain_core/behavior_engine/node_factory.h"
#include <iostream>
#include <memory>

namespace brain_core {

TreeExecutor::TreeExecutor()
{
    std::cout << "[TreeExecutor] Initialized." << std::endl;
}

TreeExecutor::~TreeExecutor()
{
    halt();
}

bool TreeExecutor::loadTree(const std::string& bt_xml)
{
    BTLoader loader;
    if (!loader.validateXML(bt_xml)) {
        std::cerr << "[TreeExecutor] BT validation failed: " << loader.lastError() << std::endl;
        return false;
    }

    _xml = loader.preprocess(bt_xml);
    _loaded = true;
    _status = BTNodeStatus::IDLE;

    // In a full BehaviorTree.CPP build, this would:
    //   _tree_impl = BT::BehaviorTreeFactory().createTreeFromText(_xml);
    // For the standalone stub, we track the loaded state.
    std::cout << "[TreeExecutor] Behavior tree loaded (" << _xml.size() << " bytes)" << std::endl;
    return true;
}

bool TreeExecutor::loadTreeFromFile(const std::string& path)
{
    BTLoader loader;
    auto xml_opt = loader.loadXML(path);
    if (!xml_opt.has_value()) {
        std::cerr << "[TreeExecutor] Failed to load BT from: " << path << std::endl;
        return false;
    }
    return loadTree(xml_opt.value());
}

BTNodeStatus TreeExecutor::tick()
{
    if (!_loaded) return BTNodeStatus::FAILURE;

    // In a full build, this would call _tree_impl->tickRoot().
    // Stub: simulate SUCCESS after a few ticks.
    static int tick_counter = 0;
    tick_counter++;

    if (tick_counter < 3) {
        _status = BTNodeStatus::RUNNING;
    } else {
        _status = BTNodeStatus::SUCCESS;
    }

    return _status;
}

void TreeExecutor::halt()
{
    if (!_loaded) return;

    // In a full build: _tree_impl->haltTree();
    _status = BTNodeStatus::IDLE;
    _loaded = false;
    std::cout << "[TreeExecutor] Tree halted." << std::endl;
}

void TreeExecutor::reset()
{
    halt();
    _xml.clear();
    _status = BTNodeStatus::IDLE;
}

} // namespace brain_core
