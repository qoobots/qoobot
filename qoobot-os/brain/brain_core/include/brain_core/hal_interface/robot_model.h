// hal_interface/robot_model.h — Robot kinematic/dynamic model
#pragma once

#include "brain_core/core_types.h"
#include <string>
#include <vector>

namespace brain_core {

/// Kinematic chain definition.
struct KinematicChain {
    std::string name;
    std::vector<std::string> joint_names;
    std::vector<std::string> link_names;
    int dof{0};
};

class RobotModel {
public:
    RobotModel();

    /// Load robot description from URDF file.
    bool loadURDF(const std::string& urdf_path);

    /// Get number of joints.
    int numJoints() const { return static_cast<int>(_joint_names.size()); }

    /// Get number of links.
    int numLinks() const { return static_cast<int>(_link_names.size()); }

    /// Get robot name from URDF.
    const std::string& robotName() const { return _robot_name; }

    /// Get joint names.
    const std::vector<std::string>& jointNames() const { return _joint_names; }

    /// Get kinematic chains (arm, gripper, etc.).
    const std::vector<KinematicChain>& chains() const { return _chains; }

    /// Get joint index by name.
    int jointIndex(const std::string& name) const;

    /// Compute forward kinematics (end-effector pose from joints).
    /// Returns: {x, y, z, qx, qy, qz, qw}
    std::vector<double> forwardKinematics(const std::vector<double>& joints) const;

private:
    std::string _robot_name;
    std::string _urdf_path;
    std::vector<std::string> _joint_names;
    std::vector<std::string> _link_names;
    std::vector<KinematicChain> _chains;
    bool _loaded{false};
};

} // namespace brain_core
