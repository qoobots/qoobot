// action_nodes/navigate_to_node.cpp
#include "brain_core/behavior_engine/action_nodes/navigate_to_node.h"
#include <iostream>
#include <cmath>

namespace brain_core {

NavigateToNode::NavigateToNode()
{
    std::cout << "[NavigateToNode] Initialized." << std::endl;
}

void NavigateToNode::setTarget(double x, double y, double z,
                                double qx, double qy, double qz, double qw)
{
    _target = {x, y, z, qx, qy, qz, qw, 0.0};
    std::cout << "[NavigateToNode] Target set: pos=("
              << x << "," << y << "," << z << ")" << std::endl;
}

void NavigateToNode::setTarget(const TrajectoryWaypoint& wp)
{
    _target = wp;
}

BTNodeStatus NavigateToNode::execute()
{
    if (!_active) {
        _active = true;
        std::cout << "[NavigateToNode] Starting navigation..." << std::endl;

        if (!isReachable()) {
            std::cerr << "[NavigateToNode] Target unreachable!" << std::endl;
            _active = false;
            return BTNodeStatus::FAILURE;
        }
    }

    // Simulate motion: check if close enough to target
    double dist = distanceToTarget();
    if (dist < _position_tolerance) {
        std::cout << "[NavigateToNode] Arrived at target (dist=" << dist << ")" << std::endl;
        _active = false;
        return BTNodeStatus::SUCCESS;
    }

    return BTNodeStatus::RUNNING;
}

void NavigateToNode::cancel()
{
    _active = false;
    std::cout << "[NavigateToNode] Navigation cancelled." << std::endl;
}

double NavigateToNode::distanceToTarget() const
{
    // Stub: return decreasing value to simulate motion
    static double sim_dist = 0.5;
    sim_dist *= 0.7;  // converge toward 0
    return sim_dist;
}

bool NavigateToNode::isReachable() const
{
    // Stub: assume most targets are reachable
    // Full build would call IKSolver and CollisionCheckerFCL
    return true;
}

} // namespace brain_core
