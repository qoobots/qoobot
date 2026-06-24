// safety_monitor/collision_checker.h — Safety collision monitoring
#pragma once

#include "brain_core/core_types.h"
#include <vector>

namespace brain_core {

/// Proximity warning levels for safety monitoring.
enum class ProximityLevel {
    SAFE,
    CAUTION,   // object within warning zone
    DANGER,    // object within danger zone
    CRITICAL,  // imminent collision → trigger emergency stop
};

/// Proximity zone definition.
struct SafetyZoneConfig {
    double caution_radius{0.3};   // m — yellow zone
    double danger_radius{0.15};    // m — red zone
    double critical_radius{0.05};  // m — emergency stop
};

class SafetyCollisionChecker {
public:
    SafetyCollisionChecker();

    /// Configure safety zones.
    void setZones(const SafetyZoneConfig& config);

    /// Update obstacle data from perception.
    void updateObstacles(const std::vector<ObstacleInfo>& obstacles);

    /// Run safety check; returns the highest proximity level.
    ProximityLevel check();

    /// Get the number of obstacles in each zone.
    int inCaution()  const { return _caution_count; }
    int inDanger()   const { return _danger_count; }
    int inCritical() const { return _critical_count; }

    /// Get closest obstacle distance in meters.
    double closestDistance() const { return _closest_dist; }

private:
    SafetyZoneConfig _zones;
    std::vector<ObstacleInfo> _obstacles;
    int _caution_count{0};
    int _danger_count{0};
    int _critical_count{0};
    double _closest_dist{999.0};
};

} // namespace brain_core
