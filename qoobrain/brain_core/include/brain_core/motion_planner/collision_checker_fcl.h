// motion_planner/collision_checker_fcl.h — FCL-based collision detection
#pragma once

#include "brain_core/core_types.h"
#include <vector>
#include <string>
#include <unordered_map>

namespace brain_core {

/// Collision geometry primitive for FCL.
struct CollisionGeometry {
    enum Type { SPHERE, BOX, CYLINDER, MESH };
    Type type{SPHERE};
    double params[3]{0.1, 0.0, 0.0};  // depends on type
    double x{0.0}, y{0.0}, z{0.0};     // position
    double qx{0.0}, qy{0.0}, qz{0.0}, qw{1.0};  // orientation
};

/// Collision pair result.
struct CollisionResult {
    bool colliding{false};
    std::string link_a;
    std::string link_b;
    double penetration_depth{0.0};
    double contact_x{0.0}, contact_y{0.0}, contact_z{0.0};
};

class CollisionCheckerFCL {
public:
    CollisionCheckerFCL();

    /// Load robot collision model from URDF.
    bool loadURDF(const std::string& urdf_path);

    /// Add an environment obstacle.
    void addObstacle(const std::string& name, const CollisionGeometry& geom);

    /// Remove an environment obstacle.
    void removeObstacle(const std::string& name);

    /// Check if a robot configuration is collision-free.
    /// Returns all collision pairs (empty = safe).
    std::vector<CollisionResult> checkCollisions(
        const std::vector<double>& joint_positions);

    /// Check self-collision only (robot links vs robot links).
    std::vector<CollisionResult> checkSelfCollision(
        const std::vector<double>& joint_positions);

    /// Check environment collision only (robot vs obstacles).
    std::vector<CollisionResult> checkEnvironmentCollision(
        const std::vector<double>& joint_positions);

    /// Quick check: returns true if configuration is collision-free.
    bool isCollisionFree(const std::vector<double>& joint_positions);

    /// Clear all environment obstacles.
    void clearObstacles();

    /// Get the number of registered link geometries.
    int numLinks() const { return static_cast<int>(_links.size()); }

private:
    std::string _urdf_path;
    std::vector<CollisionGeometry> _links;
    std::unordered_map<std::string, CollisionGeometry> _obstacles;
    bool _urdf_loaded{false};
};

} // namespace brain_core
