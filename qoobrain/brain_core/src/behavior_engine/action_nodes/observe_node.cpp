// action_nodes/observe_node.cpp
#include "brain_core/behavior_engine/action_nodes/observe_node.h"
#include <iostream>

namespace brain_core {

ObserveNode::ObserveNode()
{
    std::cout << "[ObserveNode] Initialized." << std::endl;
}

void ObserveNode::setMode(const std::string& mode)
{
    _mode = mode;
}

void ObserveNode::setSensor(const std::string& sensor_id)
{
    _sensor_id = sensor_id;
}

BTNodeStatus ObserveNode::execute()
{
    if (!_active) {
        _active = true;
        std::cout << "[ObserveNode] Capturing from " << _sensor_id
                  << " (mode=" << _mode << ")..." << std::endl;
    }

    // Stub: simulate observation result
    _result.scene_description = "table with cup, bottle, bowl";
    _result.num_objects = 3;
    _result.frame.source_id = _sensor_id;
    _result.frame.width  = 640;
    _result.frame.height = 480;
    _result.frame.stamp  = std::chrono::system_clock::now();

    std::cout << "[ObserveNode] Observed: " << _result.scene_description
              << " (" << _result.num_objects << " objects)" << std::endl;

    _active = false;

    if (_mode == "continuous") {
        return BTNodeStatus::RUNNING;
    }
    return BTNodeStatus::SUCCESS;
}

ObservationResult ObserveNode::result() const
{
    return _result;
}

void ObserveNode::cancel()
{
    _active = false;
}

} // namespace brain_core
