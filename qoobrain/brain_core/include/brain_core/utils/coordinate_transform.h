// utils/coordinate_transform.h — Coordinate frame transformations
#pragma once

#include <vector>

namespace brain_core {

/// 3D coordinate transformation utilities.
/// Supports ROS 2 ↔ robot base ↔ world ↔ camera frame conversions.
struct Transform {
    double x{0.0}, y{0.0}, z{0.0};
    double qx{0.0}, qy{0.0}, qz{0.0}, qw{1.0};
};

class CoordinateTransform {
public:
    CoordinateTransform();

    /// Set the transform from source frame to target frame.
    void setTransform(const std::string& source_frame,
                      const std::string& target_frame,
                      const Transform& tf);

    /// Transform a point from source to target frame.
    void transformPoint(const std::string& source_frame,
                         const std::string& target_frame,
                         double& x, double& y, double& z) const;

    /// Transform a pose (position + orientation) between frames.
    void transformPose(const std::string& source_frame,
                        const std::string& target_frame,
                        double& x, double& y, double& z,
                        double& qx, double& qy, double& qz, double& qw) const;

    /// Convert Euler angles (roll, pitch, yaw) to quaternion.
    static void eulerToQuat(double roll, double pitch, double yaw,
                             double& qx, double& qy, double& qz, double& qw);

    /// Convert quaternion to Euler angles (roll, pitch, yaw).
    static void quatToEuler(double qx, double qy, double qz, double qw,
                             double& roll, double& pitch, double& yaw);

    /// ROS 2 (right-hand Z-up) → Three.js (right-hand Y-up).
    static void ros2ToThreeJS(double& x, double& y, double& z);

    /// Three.js (right-hand Y-up) → ROS 2 (right-hand Z-up).
    static void threeJSToRos2(double& x, double& y, double& z);

private:
    std::unordered_map<std::string,
                       std::unordered_map<std::string, Transform>> _tfs;
};

} // namespace brain_core
