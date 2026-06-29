// safety_monitor/workspace_validator.cpp
#include "brain_core/safety_monitor/workspace_validator.h"
#include <iostream>

namespace brain_core {

WorkspaceValidator::WorkspaceValidator()
{
    std::cout << "[WorkspaceValidator] Initialized." << std::endl;
}

void WorkspaceValidator::setBounds(const WorkspaceBounds& bounds)
{
    _bounds = bounds;
    std::cout << "[WorkspaceValidator] Workspace: x=[" << _bounds.x_min
              << "," << _bounds.x_max << "] y=[" << _bounds.y_min
              << "," << _bounds.y_max << "] z=[" << _bounds.z_min
              << "," << _bounds.z_max << "]" << std::endl;
}

bool WorkspaceValidator::isWithinWorkspace(double x, double y, double z) const
{
    return x >= _bounds.x_min && x <= _bounds.x_max
        && y >= _bounds.y_min && y <= _bounds.y_max
        && z >= _bounds.z_min && z <= _bounds.z_max;
}

std::vector<WorkspaceViolation> WorkspaceValidator::validateTrajectory(
    const Trajectory& traj) const
{
    std::vector<WorkspaceViolation> violations;

    for (const auto& wp : traj.waypoints) {
        if (wp.x < _bounds.x_min) {
            violations.push_back({wp.x, wp.y, wp.z, "x_min", _bounds.x_min - wp.x});
        } else if (wp.x > _bounds.x_max) {
            violations.push_back({wp.x, wp.y, wp.z, "x_max", wp.x - _bounds.x_max});
        }
        if (wp.y < _bounds.y_min) {
            violations.push_back({wp.x, wp.y, wp.z, "y_min", _bounds.y_min - wp.y});
        } else if (wp.y > _bounds.y_max) {
            violations.push_back({wp.x, wp.y, wp.z, "y_max", wp.y - _bounds.y_max});
        }
        if (wp.z < _bounds.z_min) {
            violations.push_back({wp.x, wp.y, wp.z, "z_min", _bounds.z_min - wp.z});
        } else if (wp.z > _bounds.z_max) {
            violations.push_back({wp.x, wp.y, wp.z, "z_max", wp.z - _bounds.z_max});
        }
    }

    if (!violations.empty()) {
        std::cerr << "[WorkspaceValidator] " << violations.size()
                  << " workspace violations detected!" << std::endl;
    }

    return violations;
}

} // namespace brain_core
