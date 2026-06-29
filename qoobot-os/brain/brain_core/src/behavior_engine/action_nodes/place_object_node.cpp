// action_nodes/place_object_node.cpp
#include "brain_core/behavior_engine/action_nodes/place_object_node.h"
#include <iostream>

namespace brain_core {

PlaceObjectNode::PlaceObjectNode()
{
    std::cout << "[PlaceObjectNode] Initialized." << std::endl;
}

void PlaceObjectNode::setTarget(double x, double y, double z)
{
    _target_x = x;
    _target_y = y;
    _target_z = z;
    std::cout << "[PlaceObjectNode] Target: (" << x << "," << y << "," << z << ")" << std::endl;
}

void PlaceObjectNode::setSurfaceHeight(double z)
{
    _surface_z = z;
}

BTNodeStatus PlaceObjectNode::execute()
{
    if (!_active) {
        _active = true;
        _released = false;
        std::cout << "[PlaceObjectNode] Moving to hover above target..." << std::endl;
        return BTNodeStatus::RUNNING;
    }

    // Phase 2: lower onto surface
    static int phase = 0;
    phase++;
    if (phase == 1) {
        std::cout << "[PlaceObjectNode] Lowering to surface (z=" << _surface_z << ")" << std::endl;
        return BTNodeStatus::RUNNING;
    }

    // Phase 3: release
    if (!_released) {
        _released = true;
        std::cout << "[PlaceObjectNode] Released object." << std::endl;
        return BTNodeStatus::RUNNING;
    }

    // Phase 4: retract
    std::cout << "[PlaceObjectNode] Retracting. Place complete." << std::endl;
    _active = false;
    phase   = 0;
    return BTNodeStatus::SUCCESS;
}

void PlaceObjectNode::cancel()
{
    _active   = false;
    _released = false;
    std::cout << "[PlaceObjectNode] Place cancelled." << std::endl;
}

} // namespace brain_core
