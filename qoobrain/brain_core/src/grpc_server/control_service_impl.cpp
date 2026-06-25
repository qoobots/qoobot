// grpc_server/control_service_impl.cpp — ControlService gRPC implementation
#include "brain_core/grpc_server/control_service_impl.h"
#include <iostream>

namespace brain_core {

ControlServiceImpl::ControlServiceImpl()
{
    std::cout << "[ControlServiceImpl] Initialized." << std::endl;
}

bool ControlServiceImpl::executeTrajectory(const Trajectory& traj)
{
    if (_executing) {
        std::cerr << "[ControlServiceImpl] Already executing a trajectory." << std::endl;
        return false;
    }

    _executing = true;
    std::cout << "[ControlServiceImpl] Executing trajectory: " << traj.name
              << " (" << traj.waypoints.size() << " waypoints, score="
              << traj.score << ")" << std::endl;

    // Stub: simulate execution
    _executing = false;
    return true;
}

bool ControlServiceImpl::setGripper(double position)
{
    if (position < 0.0 || position > 1.0) {
        std::cerr << "[ControlServiceImpl] Invalid gripper position: "
                  << position << std::endl;
        return false;
    }

    std::cout << "[ControlServiceImpl] Gripper → " << position
              << (position < 0.1 ? " (closed)" : position > 0.9 ? " (open)" : " (partial)")
              << std::endl;
    return true;
}

bool ControlServiceImpl::emergencyStop(const std::string& reason)
{
    std::cout << "[ControlServiceImpl] EMERGENCY STOP: " << reason << std::endl;
    _executing = false;
    return true;
}

RobotState ControlServiceImpl::getRobotState() const
{
    RobotState state;
    state.joints.names = {"joint_1", "joint_2", "joint_3",
                           "joint_4", "joint_5", "joint_6"};
    state.joints.positions = {0.0, 0.3, 3.14, -1.57, 0.0, 0.0};
    state.gripper_position = 0.0;
    state.emergency_stop_active = false;
    state.safety_level = SafetyLevel::NORMAL;
    return state;
}

} // namespace brain_core
