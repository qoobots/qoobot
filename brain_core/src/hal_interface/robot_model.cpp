// hal_interface/robot_model.cpp — Robot kinematic/dynamic model
#include "brain_core/hal_interface/robot_model.h"
#include <iostream>
#include <algorithm>
#include <cmath>

namespace brain_core {

RobotModel::RobotModel()
{
    std::cout << "[RobotModel] Initialized." << std::endl;
}

bool RobotModel::loadURDF(const std::string& urdf_path)
{
    _urdf_path = urdf_path;
    _robot_name = "kinova_gen3";  // default

    // Stub: populate mock Kinova Gen3 model
    _joint_names = {"joint_1", "joint_2", "joint_3",
                    "joint_4", "joint_5", "joint_6"};
    _link_names  = {"base_link", "shoulder_link", "upper_arm_link",
                    "forearm_link", "wrist_1_link", "wrist_2_link", "wrist_3_link"};

    KinematicChain arm;
    arm.name = "arm";
    arm.joint_names = _joint_names;
    arm.link_names  = _link_names;
    arm.dof = 6;
    _chains = {arm};

    _loaded = true;
    std::cout << "[RobotModel] Loaded URDF: " << urdf_path
              << " (robot=" << _robot_name << ", joints=" << numJoints()
              << ", links=" << numLinks() << ", chains=" << _chains.size() << ")" << std::endl;
    return true;
}

int RobotModel::jointIndex(const std::string& name) const
{
    auto it = std::find(_joint_names.begin(), _joint_names.end(), name);
    if (it != _joint_names.end()) {
        return static_cast<int>(std::distance(_joint_names.begin(), it));
    }
    return -1;
}

std::vector<double> RobotModel::forwardKinematics(
    const std::vector<double>& joints) const
{
    // Stub: simple FK approximation for mock testing
    // Full build would use KDL or Pinocchio
    double x = 0.5 * std::cos(joints.empty() ? 0.0 : joints[0]);
    double y = 0.5 * std::sin(joints.empty() ? 0.0 : joints[0]);
    double z = 0.3 + 0.4 * std::sin(joints.size() > 1 ? joints[1] : 0.0);

    return {x, y, z, 0.0, 0.0, 0.0, 1.0};
}

} // namespace brain_core
