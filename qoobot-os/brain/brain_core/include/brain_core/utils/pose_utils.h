// utils/pose_utils.h — Pose/Transform math utilities
#pragma once

#include "brain_core/core_types.h"
#include <vector>

namespace brain_core {

/// 3D vector with basic operations.
struct Vec3 {
    double x{0.0}, y{0.0}, z{0.0};

    double norm() const;
    Vec3 normalized() const;
    static double dot(const Vec3& a, const Vec3& b);
    static Vec3 cross(const Vec3& a, const Vec3& b);
    static double distance(const Vec3& a, const Vec3& b);
};

/// 4x4 homogeneous transform matrix (column-major storage).
struct Matrix4 {
    double m[16]{1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1};  // identity

    static Matrix4 fromPose(double x, double y, double z,
                             double qx, double qy, double qz, double qw);
    static Matrix4 identity();
    Matrix4 inverse() const;
    Vec3 transformPoint(const Vec3& p) const;
};

class PoseUtils {
public:
    /// Lerp between two poses.
    static TrajectoryWaypoint lerp(const TrajectoryWaypoint& a,
                                    const TrajectoryWaypoint& b,
                                    double t);

    /// Slerp (spherical linear interpolation) for quaternions.
    static void slerp(double qx1, double qy1, double qz1, double qw1,
                       double qx2, double qy2, double qz2, double qw2,
                       double t,
                       double& qx, double& qy, double& qz, double& qw);

    /// Distance between two waypoints (Euclidean position).
    static double distance(const TrajectoryWaypoint& a,
                            const TrajectoryWaypoint& b);

    /// Path length of a trajectory.
    static double pathLength(const Trajectory& traj);
};

} // namespace brain_core
