// safety_monitor/collision_checker.cpp
#include "brain_core/safety_monitor/collision_checker.h"
#include <iostream>
#include <cmath>

namespace brain_core {

SafetyCollisionChecker::SafetyCollisionChecker()
{
    std::cout << "[SafetyCollisionChecker] Initialized." << std::endl;
}

void SafetyCollisionChecker::setZones(const SafetyZoneConfig& config)
{
    _zones = config;
    std::cout << "[SafetyCollisionChecker] Zones: caution=" << _zones.caution_radius
              << "m, danger=" << _zones.danger_radius
              << "m, critical=" << _zones.critical_radius << "m" << std::endl;
}

void SafetyCollisionChecker::updateObstacles(
    const std::vector<ObstacleInfo>& obstacles)
{
    _obstacles = obstacles;
}

ProximityLevel SafetyCollisionChecker::check()
{
    _caution_count  = 0;
    _danger_count   = 0;
    _critical_count = 0;
    _closest_dist   = 999.0;

    for (const auto& obs : _obstacles) {
        double dist = std::sqrt(obs.x*obs.x + obs.y*obs.y + obs.z*obs.z);
        _closest_dist = std::min(_closest_dist, dist);

        if (dist < _zones.critical_radius) {
            _critical_count++;
        } else if (dist < _zones.danger_radius) {
            _danger_count++;
        } else if (dist < _zones.caution_radius) {
            _caution_count++;
        }
    }

    if (_critical_count > 0) return ProximityLevel::CRITICAL;
    if (_danger_count > 0)   return ProximityLevel::DANGER;
    if (_caution_count > 0)  return ProximityLevel::CAUTION;
    return ProximityLevel::SAFE;
}

} // namespace brain_core
