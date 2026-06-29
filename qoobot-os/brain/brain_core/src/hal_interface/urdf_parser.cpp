// hal_interface/urdf_parser.cpp — URDF model parser
#include "brain_core/hal_interface/urdf_parser.h"
#include <iostream>

namespace brain_core {

URDFParser::URDFParser()
{
    std::cout << "[URDFParser] Initialized." << std::endl;
}

bool URDFParser::parse(const std::string& urdf_path)
{
    // Stub: mock parse for Kinova Gen3
    _robot_name = "kinova_gen3";

    _joints = {
        {"joint_1", "revolute", "base_link", "shoulder_link",
         {0, 0, 0.1564}, {0, 0, 0}, {0, 0, 1}, -3.14, 3.14, 1.4, 50.0},
        {"joint_2", "revolute", "shoulder_link", "upper_arm_link",
         {0, 0, 0}, {0, 0, 0}, {0, 1, 0}, -2.0, 2.0, 1.4, 50.0},
        {"joint_3", "revolute", "upper_arm_link", "forearm_link",
         {0, 0, 0.410}, {0, 0, 0}, {0, 1, 0}, -2.0, 2.0, 1.4, 50.0},
        {"joint_4", "revolute", "forearm_link", "wrist_1_link",
         {0, 0, 0.207}, {0, 0, 0}, {0, 1, 0}, -3.14, 3.14, 2.0, 25.0},
        {"joint_5", "revolute", "wrist_1_link", "wrist_2_link",
         {0, 0, 0.1035}, {0, 0, 0}, {0, 0, 1}, -2.0, 2.0, 2.0, 25.0},
        {"joint_6", "revolute", "wrist_2_link", "wrist_3_link",
         {0, 0, 0.1035}, {0, 0, 0}, {0, 1, 0}, -3.14, 3.14, 3.0, 15.0},
    };

    _links = {
        {"base_link", false, false, 2.5, 0.1, 0.1, 0.05},
        {"shoulder_link", false, false, 1.5, 0.05, 0.05, 0.02},
        {"upper_arm_link", false, false, 1.2, 0.03, 0.03, 0.01},
        {"forearm_link", false, false, 0.8, 0.02, 0.02, 0.01},
        {"wrist_1_link", false, false, 0.3, 0.01, 0.01, 0.005},
        {"wrist_2_link", false, false, 0.2, 0.005, 0.005, 0.002},
        {"wrist_3_link", false, false, 0.1, 0.002, 0.002, 0.001},
    };

    _parsed = true;
    std::cout << "[URDFParser] Parsed " << urdf_path << ": "
              << _joints.size() << " joints, " << _links.size() << " links" << std::endl;
    return true;
}

bool URDFParser::parseFromString(const std::string& urdf_xml)
{
    (void)urdf_xml;
    // Minimal stub — full implementation would use tinyxml2/urdfdom
    _parsed = true;
    return true;
}

double URDFParser::totalMass() const
{
    double mass = 0.0;
    for (const auto& link : _links) mass += link.mass;
    return mass;
}

bool URDFParser::validate() const
{
    if (!_parsed) return false;
    if (_joints.empty() || _links.empty()) return false;
    // Each joint should reference valid parent/child links
    return true;
}

} // namespace brain_core
