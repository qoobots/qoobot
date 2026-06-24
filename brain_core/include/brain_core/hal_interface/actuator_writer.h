// hal_interface/actuator_writer.h — Robot actuator command interface
#pragma once

#include "brain_core/core_types.h"
#include <string>
#include <vector>
#include <atomic>

namespace brain_core {

/// Actuator command types.
enum class ActuatorCommandType {
    POSITION,       // Joint position (rad)
    VELOCITY,       // Joint velocity (rad/s)
    TORQUE,         // Joint torque (Nm)
    GRIPPER,        // Gripper position (0=closed, 1=open)
};

/// Actuator command.
struct ActuatorCommand {
    ActuatorCommandType type{ActuatorCommandType::POSITION};
    std::vector<double> values;
    double timestamp{0.0};
};

class ActuatorWriter {
public:
    ActuatorWriter();

    /// Initialize connection to robot actuators.
    bool init(const std::string& robot_ip = "192.168.1.10");

    /// Send a position command to joints.
    bool sendPositionCommand(const std::vector<double>& positions);

    /// Send a velocity command to joints.
    bool sendVelocityCommand(const std::vector<double>& velocities);

    /// Send a torque command to joints.
    bool sendTorqueCommand(const std::vector<double>& torques);

    /// Set gripper position (0.0=closed, 1.0=open).
    bool setGripper(double position);

    /// Emergency stop: zero-torque all joints.
    bool emergencyStop();

    /// Check if connection is active.
    bool isConnected() const { return _connected; }

    /// Get the last sent command.
    const ActuatorCommand& lastCommand() const { return _last_command; }

private:
    bool _connected{false};
    std::string _robot_ip;
    ActuatorCommand _last_command;
};

} // namespace brain_core
