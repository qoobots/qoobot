// utils/coordinate_transform.cpp
#include "brain_core/utils/coordinate_transform.h"
#include <iostream>
#include <cmath>

namespace brain_core {

CoordinateTransform::CoordinateTransform()
{
    std::cout << "[CoordinateTransform] Initialized." << std::endl;
}

void CoordinateTransform::setTransform(const std::string& source_frame,
                                        const std::string& target_frame,
                                        const Transform& tf)
{
    _tfs[source_frame][target_frame] = tf;
    std::cout << "[CoordinateTransform] " << source_frame
              << " → " << target_frame << std::endl;
}

void CoordinateTransform::transformPoint(const std::string& source_frame,
                                          const std::string& target_frame,
                                          double& x, double& y, double& z) const
{
    auto src_it = _tfs.find(source_frame);
    if (src_it == _tfs.end()) return;  // identity

    auto tgt_it = src_it->second.find(target_frame);
    if (tgt_it == src_it->second.end()) return;

    x += tgt_it->second.x;
    y += tgt_it->second.y;
    z += tgt_it->second.z;
}

void CoordinateTransform::transformPose(const std::string& source_frame,
                                         const std::string& target_frame,
                                         double& x, double& y, double& z,
                                         double&, double&, double&, double&) const
{
    transformPoint(source_frame, target_frame, x, y, z);
}

void CoordinateTransform::eulerToQuat(double roll, double pitch, double yaw,
                                       double& qx, double& qy, double& qz, double& qw)
{
    double cr = std::cos(roll * 0.5);
    double sr = std::sin(roll * 0.5);
    double cp = std::cos(pitch * 0.5);
    double sp = std::sin(pitch * 0.5);
    double cy = std::cos(yaw * 0.5);
    double sy = std::sin(yaw * 0.5);

    qw = cr * cp * cy + sr * sp * sy;
    qx = sr * cp * cy - cr * sp * sy;
    qy = cr * sp * cy + sr * cp * sy;
    qz = cr * cp * sy - sr * sp * cy;
}

void CoordinateTransform::quatToEuler(double qx, double qy, double qz, double qw,
                                       double& roll, double& pitch, double& yaw)
{
    double sinr_cosp = 2.0 * (qw * qx + qy * qz);
    double cosr_cosp = 1.0 - 2.0 * (qx * qx + qy * qy);
    roll = std::atan2(sinr_cosp, cosr_cosp);

    double sinp = 2.0 * (qw * qy - qz * qx);
    if (std::abs(sinp) >= 1.0)
        pitch = std::copysign(M_PI / 2.0, sinp);
    else
        pitch = std::asin(sinp);

    double siny_cosp = 2.0 * (qw * qz + qx * qy);
    double cosy_cosp = 1.0 - 2.0 * (qy * qy + qz * qz);
    yaw = std::atan2(siny_cosp, cosy_cosp);
}

void CoordinateTransform::ros2ToThreeJS(double& x, double& y, double& z)
{
    // ROS 2: X-forward, Y-left, Z-up
    // Three.js: X-right, Y-up, Z-out (from screen)
    double temp = y;
    y = z;
    z = -temp;
}

void CoordinateTransform::threeJSToRos2(double& x, double& y, double& z)
{
    // Inverse of ros2ToThreeJS
    double temp = -z;
    z = y;
    y = temp;
}

} // namespace brain_core
