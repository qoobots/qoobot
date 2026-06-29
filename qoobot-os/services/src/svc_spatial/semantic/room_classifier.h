#pragma once

#include "qoosvc/spatial/map_types.h"
#include <string>
#include <unordered_map>
#include <vector>

namespace qoosvc::spatial {

/**
 * RoomClassifier — Classifies room types from occupancy grid geometry.
 *
 * Uses geometric heuristics (area, aspect ratio, connected openings)
 * to determine room types. In production, this would be augmented with
 * visual features from camera data.
 */
class RoomClassifier {
public:
    struct Config {
        double min_room_area = 4.0;        // sq meters
        double max_room_area = 200.0;
        double door_width_min = 0.6;       // meters
        double door_width_max = 1.5;
        double corridor_width_max = 2.5;   // Narrower than this = corridor
    };

    struct RoomCandidate {
        std::vector<Point3D> boundary;
        double area_sqm = 0.0;
        double aspect_ratio = 1.0;
        int32_t num_openings = 0;
        Point3D centroid;
    };

    explicit RoomClassifier(const Config& config);
    ~RoomClassifier();

    /**
     * Segment the occupancy grid into room candidates.
     */
    std::vector<RoomCandidate> segment_rooms(const OccupancyGrid& grid);

    /**
     * Classify a room candidate into a RoomType.
     */
    RoomType classify(const RoomCandidate& room, const std::vector<RoomCandidate>& all_rooms);

    /**
     * Get human-readable room name.
     */
    static std::string room_type_name(RoomType type);

private:
    // Flood-fill to find connected free space regions
    void flood_fill(const OccupancyGrid& grid, int32_t sx, int32_t sy,
                    std::vector<int8_t>& visited, int32_t label,
                    std::vector<Point2I>& region);

    // Extract boundary polygon from a region
    std::vector<Point3D> extract_boundary(const OccupancyGrid& grid,
                                           const std::vector<Point2I>& region);

    // Count door-sized openings in the boundary
    int32_t count_openings(const std::vector<Point3D>& boundary,
                           const OccupancyGrid& grid);

    // Compute room features
    RoomCandidate compute_features(const OccupancyGrid& grid,
                                    const std::vector<Point2I>& region);

    Config config_;
};

} // namespace qoosvc::spatial
