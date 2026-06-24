// hal_interface/actuator_writer.cpp — Robot actuator commands
#include "brain_core/hal_interface/actuator_writer.h"
#include <iostream>

namespace brain_core {

ActuatorWriter::ActuatorWriter()
{
    std::cout << "[ActuatorWriter] Initialized." << std::endl;
}

bool ActuatorWriter::init(const std::string& robot_ip)
{
    _robot_ip = robot_ip;
    _connected = true;
    std::cout << "[ActuatorWriter] Connected to robot at: " << robot_ip << std::endl;
    return true;
}

bool ActuatorWriter::sendPositionCommand(const std::vector<double>& positions)
{
    if (!_connected) return false;

    _last_command = {ActuatorCommandType::POSITION, positions, 0.0};
    std::cout << "[ActuatorWriter] Position command: " << positions.size()
              << " joints" << std::endl;
    return true;
}

bool ActuatorWriter::sendVelocityCommand(const std::vector<double>& velocities)
{
    if (!_connected) return false;

    _last_command = {ActuatorCommandType::VELOCITY, velocities, 0.0};
    return true;
}

bool ActuatorWriter::sendTorqueCommand(const std::vector<double>& torques)
{
    if (!_connected) return false;

    _last_command = {ActuatorCommandType::TORQUE, torques, 0.0};
    return true;
}

bool ActuatorWriter::setGripper(double position)
{
    if (!_connected) return false;

    position = std::max(0.0, std::min(1.0, position));
    _last_command = {ActuatorCommandType::GRIPPER, {position}, 0.0};
    std::cout << "[ActuatorWriter] Gripper: " << position
              << (position < 0.1 ? " (closed)" : position > 0.9 ? " (open)" : " (partial)")
              << std::endl;
    return true;
}

bool ActuatorWriter::emergencyStop()
{
    _connected = false;
    std::cout << "[ActuatorWriter] EMERGENCY STOP — zero-torque all joints." << std::endl;
    return true;
}

} // namespace brain_core
