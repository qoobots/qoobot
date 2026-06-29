// safety_monitor/workspace_validator.h — Robot workspace boundary checking
#pragma once

#include "brain_core/core_types.h"
#include <vector>

namespace brain_core {

/// 3D workspace boundary.
struct WorkspaceBounds {
    double x_min{-0.8}, x_max{0.8};
    double y_min{-0.8}, y_max{0.8};
    double z_min{0.0},  z_max{0.9};
};

/// Workspace violation.
struct WorkspaceViolation {
    double x, y, z;     // violated position
    std::string axis;   // "x_min", "x_max", etc.
    double distance;    // how far outside the boundary
};

class WorkspaceValidator {
public:
    WorkspaceValidator();

    /// Set workspace bounds.
    void setBounds(const WorkspaceBounds& bounds);

    /// Check if a pose is within workspace.
    bool isWithinWorkspace(double x, double y, double z) const;

    /// Validate an entire trajectory.
    /// Returns violations for waypoints outside workspace.
    std::vector<WorkspaceViolation> validateTrajectory(const Trajectory& traj) const;

    /// Get current workspace bounds.
    const WorkspaceBounds& bounds() const { return _bounds; }

private:
    WorkspaceBounds _bounds;
};

} // namespace brain_core
