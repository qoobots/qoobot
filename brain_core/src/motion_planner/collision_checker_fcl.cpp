// motion_planner/collision_checker_fcl.cpp — FCL collision detection
#include "brain_core/motion_planner/collision_checker_fcl.h"
#include <iostream>
#include <cmath>

namespace brain_core {

CollisionCheckerFCL::CollisionCheckerFCL()
{
    std::cout << "[CollisionCheckerFCL] Initialized (standalone stub)." << std::endl;
}

bool CollisionCheckerFCL::loadURDF(const std::string& urdf_path)
{
    _urdf_path = urdf_path;
    _urdf_loaded = true;

    // Stub: populate with simplified Kinova Gen3 model
    // In full FCL build, this parses URDF collision geometries
    _links.clear();
    for (int i = 0; i < 7; ++i) {
        CollisionGeometry geom;
        geom.type = CollisionGeometry::CYLINDER;
        geom.params[0] = 0.05;  // radius
        geom.params[1] = 0.2;   // half-length
        _links.push_back(geom);
    }

    std::cout << "[CollisionCheckerFCL] Loaded URDF: " << urdf_path
              << " (" << _links.size() << " links)" << std::endl;
    return true;
}

void CollisionCheckerFCL::addObstacle(const std::string& name,
                                       const CollisionGeometry& geom)
{
    _obstacles[name] = geom;
    std::cout << "[CollisionCheckerFCL] Added obstacle: " << name << std::endl;
}

void CollisionCheckerFCL::removeObstacle(const std::string& name)
{
    _obstacles.erase(name);
}

std::vector<CollisionResult> CollisionCheckerFCL::checkCollisions(
    const std::vector<double>& joint_positions)
{
    auto self = checkSelfCollision(joint_positions);
    auto env  = checkEnvironmentCollision(joint_positions);

    std::vector<CollisionResult> all;
    all.insert(all.end(), self.begin(), self.end());
    all.insert(all.end(), env.begin(), env.end());
    return all;
}

std::vector<CollisionResult> CollisionCheckerFCL::checkSelfCollision(
    const std::vector<double>& joint_positions)
{
    (void)joint_positions;
    // Stub: assume no self-collision in normal configurations
    return {};
}

std::vector<CollisionResult> CollisionCheckerFCL::checkEnvironmentCollision(
    const std::vector<double>& joint_positions)
{
    (void)joint_positions;

    std::vector<CollisionResult> results;

    // Stub: check if any obstacle is very close to a mock arm position
    for (const auto& [name, obs] : _obstacles) {
        double dist = std::sqrt(obs.x * obs.x + obs.y * obs.y + obs.z * obs.z);

        // Mock: if obstacle is within 0.2 m of arm base, flag collision
        if (dist < 0.2) {
            CollisionResult cr;
            cr.colliding = true;
            cr.link_a = "arm_link_3";
            cr.link_b = name;
            cr.penetration_depth = 0.2 - dist;
            cr.contact_x = obs.x * 0.5;
            cr.contact_y = obs.y * 0.5;
            cr.contact_z = obs.z * 0.5;
            results.push_back(cr);
        }
    }

    return results;
}

bool CollisionCheckerFCL::isCollisionFree(const std::vector<double>& joint_positions)
{
    return checkCollisions(joint_positions).empty();
}

void CollisionCheckerFCL::clearObstacles()
{
    _obstacles.clear();
    std::cout << "[CollisionCheckerFCL] Obstacles cleared." << std::endl;
}

} // namespace brain_core
