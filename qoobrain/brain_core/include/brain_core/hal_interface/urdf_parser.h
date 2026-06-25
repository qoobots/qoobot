// hal_interface/urdf_parser.h — URDF model parser
#pragma once

#include "brain_core/core_types.h"
#include <string>
#include <vector>

namespace brain_core {

/// Parsed URDF joint info.
struct URDFJointInfo {
    std::string name;
    std::string type;       // "revolute", "prismatic", "fixed"
    std::string parent_link;
    std::string child_link;
    double origin_xyz[3]{0, 0, 0};
    double origin_rpy[3]{0, 0, 0};
    double axis_xyz[3]{0, 0, 1};
    double lower_limit{-3.14};
    double upper_limit{3.14};
    double max_velocity{2.0};
    double max_effort{50.0};
};

/// Parsed URDF link info.
struct URDFLinkInfo {
    std::string name;
    bool has_visual{false};
    bool has_collision{false};
    double mass{0.0};
    double inertia_ixx{0.0}, inertia_iyy{0.0}, inertia_izz{0.0};
};

class URDFParser {
public:
    URDFParser();

    /// Parse a URDF file.
    bool parse(const std::string& urdf_path);

    /// Parse from raw XML string.
    bool parseFromString(const std::string& urdf_xml);

    /// Get parsed joints.
    const std::vector<URDFJointInfo>& joints() const { return _joints; }

    /// Get parsed links.
    const std::vector<URDFLinkInfo>& links() const { return _links; }

    /// Get robot name.
    const std::string& robotName() const { return _robot_name; }

    /// Get total mass.
    double totalMass() const;

    /// Validate URDF structure.
    bool validate() const;

private:
    std::string _robot_name;
    std::vector<URDFJointInfo> _joints;
    std::vector<URDFLinkInfo> _links;
    bool _parsed{false};
};

} // namespace brain_core
