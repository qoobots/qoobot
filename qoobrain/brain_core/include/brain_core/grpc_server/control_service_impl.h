// grpc_server/control_service_impl.h — ControlService gRPC implementation
#pragma once

#include "brain_core/core_types.h"
#include <string>

namespace brain_core {

/// Implements the ControlService gRPC service:
/// - ExecuteTrajectory: Execute a planned trajectory on the real robot
/// - SetGripper: Open/close the gripper
/// - EmergencyStop: Immediate safety stop
class ControlServiceImpl {
public:
    ControlServiceImpl();

    /// Execute a trajectory on the robot.
    /// Returns true if execution started successfully.
    bool executeTrajectory(const Trajectory& traj);

    /// Set gripper position (0.0=closed, 1.0=open).
    bool setGripper(double position);

    /// Trigger emergency stop.
    bool emergencyStop(const std::string& reason);

    /// Get current robot state.
    RobotState getRobotState() const;

private:
    bool _executing{false};
};

} // namespace brain_core
