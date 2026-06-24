// action_nodes/avoid_obstacle_node.cpp
#include "brain_core/behavior_engine/action_nodes/avoid_obstacle_node.h"
#include <iostream>
#include <cmath>

namespace brain_core {

AvoidObstacleNode::AvoidObstacleNode()
{
    std::cout << "[AvoidObstacleNode] Initialized." << std::endl;
}

void AvoidObstacleNode::setObstacles(const std::vector<ObstacleInfo>& obstacles)
{
    _obstacles = obstacles;
    std::cout << "[AvoidObstacleNode] Received " << obstacles.size() << " obstacles." << std::endl;
}

void AvoidObstacleNode::setSafetyMargin(double radius_m)
{
    _safety_margin = radius_m;
}

BTNodeStatus AvoidObstacleNode::execute()
{
    if (_obstacles.empty()) {
        _path_clear = true;
        return BTNodeStatus::SUCCESS;
    }

    if (!_active) {
        _active = true;
        std::cout << "[AvoidObstacleNode] Computing avoidance path for "
                  << _obstacles.size() << " obstacles (margin="
                  << _safety_margin << "m)..." << std::endl;
    }

    // Stub: simulate avoidance computation
    static int avoidance_ticks = 0;
    avoidance_ticks++;

    if (avoidance_ticks < 2) {
        return BTNodeStatus::RUNNING;
    }

    bool all_clear = true;
    for (const auto& obs : _obstacles) {
        // Simple distance check to origin as mock
        double dist = std::sqrt(obs.x * obs.x + obs.y * obs.y + obs.z * obs.z);
        if (dist < _safety_margin) {
            all_clear = false;
            break;
        }
    }

    _path_clear = all_clear;
    _active = false;
    avoidance_ticks = 0;

    if (_path_clear) {
        std::cout << "[AvoidObstacleNode] Path clear." << std::endl;
        return BTNodeStatus::SUCCESS;
    } else {
        std::cerr << "[AvoidObstacleNode] No safe path found!" << std::endl;
        return BTNodeStatus::FAILURE;
    }
}

void AvoidObstacleNode::cancel()
{
    _active = false;
}

} // namespace brain_core
