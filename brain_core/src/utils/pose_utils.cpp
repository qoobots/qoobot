// utils/pose_utils.cpp — Pose/Transform math
#include "brain_core/utils/pose_utils.h"
#include <cmath>

namespace brain_core {

// Vec3 methods
double Vec3::norm() const {
    return std::sqrt(x*x + y*y + z*z);
}

Vec3 Vec3::normalized() const {
    double n = norm();
    return (n > 0) ? Vec3{x/n, y/n, z/n} : Vec3{};
}

double Vec3::dot(const Vec3& a, const Vec3& b) {
    return a.x*b.x + a.y*b.y + a.z*b.z;
}

Vec3 Vec3::cross(const Vec3& a, const Vec3& b) {
    return {a.y*b.z - a.z*b.y, a.z*b.x - a.x*b.z, a.x*b.y - a.y*b.x};
}

double Vec3::distance(const Vec3& a, const Vec3& b) {
    return Vec3{a.x-b.x, a.y-b.y, a.z-b.z}.norm();
}

// Matrix4 methods
Matrix4 Matrix4::identity() {
    return Matrix4{};
}

Matrix4 Matrix4::fromPose(double x, double y, double z,
                            double qx, double qy, double qz, double qw) {
    Matrix4 mat;

    // Rotation from quaternion
    double xx = qx*qx, yy = qy*qy, zz = qz*qz;
    double xy = qx*qy, xz = qx*qz, yz = qy*qz;
    double wx = qw*qx, wy = qw*qy, wz = qw*qz;

    mat.m[0]  = 1.0 - 2.0*(yy + zz);
    mat.m[1]  = 2.0*(xy + wz);
    mat.m[2]  = 2.0*(xz - wy);
    mat.m[3]  = 0.0;

    mat.m[4]  = 2.0*(xy - wz);
    mat.m[5]  = 1.0 - 2.0*(xx + zz);
    mat.m[6]  = 2.0*(yz + wx);
    mat.m[7]  = 0.0;

    mat.m[8]  = 2.0*(xz + wy);
    mat.m[9]  = 2.0*(yz - wx);
    mat.m[10] = 1.0 - 2.0*(xx + yy);
    mat.m[11] = 0.0;

    // Translation
    mat.m[12] = x;
    mat.m[13] = y;
    mat.m[14] = z;
    mat.m[15] = 1.0;

    return mat;
}

Matrix4 Matrix4::inverse() const {
    // Simple inverse for homogeneous transform
    // R^T for rotation, -R^T*t for translation
    Matrix4 inv;

    // Transpose rotation part
    inv.m[0] = m[0]; inv.m[1] = m[4]; inv.m[2] = m[8];
    inv.m[4] = m[1]; inv.m[5] = m[5]; inv.m[6] = m[9];
    inv.m[8] = m[2]; inv.m[9] = m[6]; inv.m[10] = m[10];

    // -R^T * t for translation
    double tx = -(m[0]*m[12] + m[4]*m[13] + m[8]*m[14]);
    double ty = -(m[1]*m[12] + m[5]*m[13] + m[9]*m[14]);
    double tz = -(m[2]*m[12] + m[6]*m[13] + m[10]*m[14]);
    inv.m[12] = tx; inv.m[13] = ty; inv.m[14] = tz;
    inv.m[15] = 1.0;

    return inv;
}

Vec3 Matrix4::transformPoint(const Vec3& p) const {
    return {
        m[0]*p.x + m[4]*p.y + m[8]*p.z  + m[12],
        m[1]*p.x + m[5]*p.y + m[9]*p.z  + m[13],
        m[2]*p.x + m[6]*p.y + m[10]*p.z + m[14],
    };
}

// PoseUtils methods
TrajectoryWaypoint PoseUtils::lerp(const TrajectoryWaypoint& a,
                                     const TrajectoryWaypoint& b, double t)
{
    TrajectoryWaypoint result;
    result.x = a.x + (b.x - a.x) * t;
    result.y = a.y + (b.y - a.y) * t;
    result.z = a.z + (b.z - a.z) * t;
    slerp(a.qx, a.qy, a.qz, a.qw, b.qx, b.qy, b.qz, b.qw, t,
          result.qx, result.qy, result.qz, result.qw);
    result.time_from_start_sec = a.time_from_start_sec
        + (b.time_from_start_sec - a.time_from_start_sec) * t;
    return result;
}

void PoseUtils::slerp(double qx1, double qy1, double qz1, double qw1,
                        double qx2, double qy2, double qz2, double qw2,
                        double t,
                        double& qx, double& qy, double& qz, double& qw)
{
    // Cosine of the angle between the two quaternions
    double cos_half_theta = qw1*qw2 + qx1*qx2 + qy1*qy2 + qz1*qz2;

    // If the dot product is negative, slerp takes the long way
    if (cos_half_theta < 0.0) {
        qw2 = -qw2; qx2 = -qx2; qy2 = -qy2; qz2 = -qz2;
        cos_half_theta = -cos_half_theta;
    }

    if (cos_half_theta > 0.9995) {
        // Linear interpolation for very small angles
        qw = qw1 + (qw2 - qw1) * t;
        qx = qx1 + (qx2 - qx1) * t;
        qy = qy1 + (qy2 - qy1) * t;
        qz = qz1 + (qz2 - qz1) * t;
        double norm = std::sqrt(qw*qw + qx*qx + qy*qy + qz*qz);
        qw /= norm; qx /= norm; qy /= norm; qz /= norm;
        return;
    }

    double half_theta = std::acos(cos_half_theta);
    double sin_half_theta = std::sin(half_theta);
    double a = std::sin((1.0 - t) * half_theta) / sin_half_theta;
    double b = std::sin(t * half_theta) / sin_half_theta;

    qw = a*qw1 + b*qw2;
    qx = a*qx1 + b*qx2;
    qy = a*qy1 + b*qy2;
    qz = a*qz1 + b*qz2;
}

double PoseUtils::distance(const TrajectoryWaypoint& a,
                             const TrajectoryWaypoint& b)
{
    return Vec3::distance({a.x, a.y, a.z}, {b.x, b.y, b.z});
}

double PoseUtils::pathLength(const Trajectory& traj)
{
    double total = 0.0;
    for (size_t i = 1; i < traj.waypoints.size(); ++i) {
        total += distance(traj.waypoints[i-1], traj.waypoints[i]);
    }
    return total;
}

} // namespace brain_core
