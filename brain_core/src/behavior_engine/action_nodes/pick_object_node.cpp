// action_nodes/pick_object_node.cpp
#include "brain_core/behavior_engine/action_nodes/pick_object_node.h"
#include <iostream>

namespace brain_core {

PickObjectNode::PickObjectNode()
{
    std::cout << "[PickObjectNode] Initialized." << std::endl;
}

void PickObjectNode::setTarget(const std::string& object_label)
{
    _target_label = object_label;
    std::cout << "[PickObjectNode] Target: " << object_label << std::endl;
}

void PickObjectNode::setGraspParams(double approach_dist_m,
                                     double grasp_force_n,
                                     double lift_height_m)
{
    _approach_dist = approach_dist_m;
    _grasp_force   = grasp_force_n;
    _lift_height   = lift_height_m;
}

BTNodeStatus PickObjectNode::execute()
{
    if (_target_label.empty()) return BTNodeStatus::FAILURE;

    if (!_active) {
        _active = true;
        std::cout << "[PickObjectNode] Approaching " << _target_label
                  << " (approach_dist=" << _approach_dist << ")" << std::endl;
        return BTNodeStatus::RUNNING;
    }

    if (!_grasped) {
        _grasped = true;
        std::cout << "[PickObjectNode] Grasped " << _target_label
                  << " (force=" << _grasp_force << "N)" << std::endl;
        return BTNodeStatus::RUNNING;
    }

    // Lift phase
    static bool lifted = false;
    if (!lifted) {
        lifted = true;
        std::cout << "[PickObjectNode] Lifting (height=" << _lift_height << "m)" << std::endl;
        return BTNodeStatus::RUNNING;
    }

    std::cout << "[PickObjectNode] Pick complete." << std::endl;
    _active = false;
    lifted  = false;
    return BTNodeStatus::SUCCESS;
}

void PickObjectNode::cancel()
{
    _active  = false;
    _grasped = false;
    std::cout << "[PickObjectNode] Pick cancelled." << std::endl;
}

} // namespace brain_core
