#include "room_classifier.h"
#include <algorithm>
#include <cmath>
#include <queue>
#include <set>
#include <sstream>
#include <unordered_set>

namespace qoosvc::spatial {

RoomClassifier::RoomClassifier(const Config& config)
    : config_(config) {
}

RoomClassifier::~RoomClassifier() = default;

std::vector<RoomClassifier::RoomCandidate>
RoomClassifier::segment_rooms(const OccupancyGrid& grid) {
    std::vector<RoomCandidate> rooms;
    std::vector<int8_t> visited(grid.width * grid.height, 0);
    int32_t label = 0;

    // Scan grid for unvisited free cells
    for (int32_t y = 0; y < grid.height; ++y) {
        for (int32_t x = 0; x < grid.width; ++x) {
            if (visited[y * grid.width + x] != 0) continue;
            if (!grid.is_free(x, y)) continue;

            std::vector<Point2I> region;
            flood_fill(grid, x, y, visited, ++label, region);

            // Filter small regions (noise)
            if (region.size() < 20) continue;

            auto room = compute_features(grid, region);

            // Filter by area
            if (room.area_sqm >= config_.min_room_area &&
                room.area_sqm <= config_.max_room_area) {
                rooms.push_back(std::move(room));
            }
        }
    }

    return rooms;
}

void RoomClassifier::flood_fill(const OccupancyGrid& grid,
                                  int32_t sx, int32_t sy,
                                  std::vector<int8_t>& visited, int32_t label,
                                  std::vector<Point2I>& region) {
    std::queue<Point2I> queue;
    queue.push({sx, sy});
    visited[sy * grid.width + sx] = static_cast<int8_t>(label);

    const int dx[] = {-1, 1, 0, 0, -1, -1, 1, 1};
    const int dy[] = {0, 0, -1, 1, -1, 1, -1, 1};

    while (!queue.empty()) {
        auto p = queue.front();
        queue.pop();
        region.push_back(p);

        // 4-connected for room segmentation (8-connected can bridge narrow gaps)
        for (int i = 0; i < 4; ++i) {
            int32_t nx = p.x + dx[i];
            int32_t ny = p.y + dy[i];

            if (!grid.is_in_bounds(nx, ny)) continue;
            if (visited[ny * grid.width + nx] != 0) continue;
            if (grid.is_occupied(nx, ny)) continue;

            visited[ny * grid.width + nx] = static_cast<int8_t>(label);
            queue.push({nx, ny});
        }
    }
}

RoomClassifier::RoomCandidate
RoomClassifier::compute_features(const OccupancyGrid& grid,
                                   const std::vector<Point2I>& region) {
    RoomCandidate room;

    // Compute centroid and bounding box
    double sum_x = 0, sum_y = 0;
    int32_t min_x = std::numeric_limits<int32_t>::max();
    int32_t max_x = std::numeric_limits<int32_t>::min();
    int32_t min_y = std::numeric_limits<int32_t>::max();
    int32_t max_y = std::numeric_limits<int32_t>::min();

    for (const auto& p : region) {
        sum_x += p.x;
        sum_y += p.y;
        min_x = std::min(min_x, p.x);
        max_x = std::max(max_x, p.x);
        min_y = std::min(min_y, p.y);
        max_y = std::max(max_y, p.y);
    }

    double cx = sum_x / region.size();
    double cy = sum_y / region.size();

    // Convert to world coordinates
    room.centroid = grid.grid_to_world(static_cast<int32_t>(cx),
                                         static_cast<int32_t>(cy));

    // Area
    room.area_sqm = region.size() * grid.resolution * grid.resolution;

    // Aspect ratio
    double width = (max_x - min_x) * grid.resolution;
    double height = (max_y - min_y) * grid.resolution;
    room.aspect_ratio = (height > 0.01) ? width / height : 1.0;

    // Extract boundary
    room.boundary = extract_boundary(grid, region);

    // Count openings
    room.num_openings = count_openings(room.boundary, grid);

    return room;
}

std::vector<Point3D> RoomClassifier::extract_boundary(
    const OccupancyGrid& grid, const std::vector<Point2I>& region) {

    // Simplified convex hull approach
    std::set<std::pair<int32_t, int32_t>> region_set;
    for (const auto& p : region) {
        region_set.insert({p.x, p.y});
    }

    // Find boundary cells (cells adjacent to non-free space)
    std::vector<Point3D> boundary;
    const int dx[] = {-1, 1, 0, 0};
    const int dy[] = {0, 0, -1, 1};

    for (const auto& p : region) {
        bool is_boundary = false;
        for (int i = 0; i < 4; ++i) {
            int32_t nx = p.x + dx[i];
            int32_t ny = p.y + dy[i];
            if (!grid.is_in_bounds(nx, ny) ||
                region_set.find({nx, ny}) == region_set.end()) {
                is_boundary = true;
                break;
            }
        }
        if (is_boundary) {
            boundary.push_back(grid.grid_to_world(p.x, p.y));
        }
    }

    // Simplify: use convex hull of boundary points (Graham scan)
    if (boundary.size() > 50) {
        // Take every Nth point to reduce complexity
        std::vector<Point3D> simplified;
        size_t step = boundary.size() / 50;
        for (size_t i = 0; i < boundary.size(); i += std::max(size_t(1), step)) {
            simplified.push_back(boundary[i]);
        }
        return simplified;
    }

    return boundary;
}

int32_t RoomClassifier::count_openings(const std::vector<Point3D>& boundary,
                                         const OccupancyGrid& grid) {
    // Simplified: estimate openings from boundary gaps
    // In production, this would analyze door-sized gaps in the boundary

    if (boundary.size() < 10) return 1;

    // Count significant gaps between consecutive boundary points
    int32_t openings = 0;
    double max_gap = 0;

    for (size_t i = 0; i < boundary.size(); ++i) {
        size_t j = (i + 1) % boundary.size();
        double gap = boundary[i].distance_to(boundary[j]);

        // Door-sized gap detection
        if (gap > config_.door_width_min && gap < config_.door_width_max) {
            openings++;
        }
        max_gap = std::max(max_gap, gap);
    }

    // If no door-sized gaps found but room is large, assume at least one opening
    if (openings == 0 && boundary.size() > 20) {
        openings = 1;
    }

    return openings;
}

RoomType RoomClassifier::classify(const RoomCandidate& room,
                                    const std::vector<RoomCandidate>& all_rooms) {
    double area = room.area_sqm;
    double ar = room.aspect_ratio;
    int32_t openings = room.num_openings;

    // Classification heuristics
    if (area < 5.0 && openings <= 1) {
        return RoomType::BATHROOM;
    }

    if (area < 8.0 && openings == 1) {
        return RoomType::BATHROOM;
    }

    if (area >= 8.0 && area < 20.0 && openings >= 1) {
        return RoomType::BEDROOM;
    }

    if (area >= 15.0 && area < 50.0 && openings >= 2) {
        return RoomType::LIVING_ROOM;
    }

    if (area >= 8.0 && area < 15.0 && openings >= 1) {
        // Could be kitchen or study
        if (ar > 2.0) {
            return RoomType::KITCHEN;
        }
        return RoomType::STUDY;
    }

    // Corridor detection: narrow and elongated
    if (area >= 3.0 && area < 30.0 && (ar > 3.0 || ar < 0.33) && openings >= 2) {
        return RoomType::HALLWAY;
    }

    if (area >= 50.0) {
        return RoomType::LIVING_ROOM;  // Large room = living room
    }

    if (area >= 20.0 && area < 50.0 && openings >= 2) {
        return RoomType::LIVING_ROOM;
    }

    // Default for small rooms
    if (area < 8.0) {
        return RoomType::BATHROOM;
    }

    return RoomType::UNKNOWN;
}

std::string RoomClassifier::room_type_name(RoomType type) {
    switch (type) {
    case RoomType::LIVING_ROOM: return "Living Room";
    case RoomType::BEDROOM:     return "Bedroom";
    case RoomType::KITCHEN:     return "Kitchen";
    case RoomType::BATHROOM:    return "Bathroom";
    case RoomType::HALLWAY:     return "Hallway";
    case RoomType::DINING_ROOM: return "Dining Room";
    case RoomType::STUDY:       return "Study";
    case RoomType::BALCONY:     return "Balcony";
    case RoomType::GARAGE:      return "Garage";
    case RoomType::OFFICE:      return "Office";
    case RoomType::MEETING_ROOM:return "Meeting Room";
    case RoomType::CORRIDOR:    return "Corridor";
    case RoomType::WAREHOUSE:   return "Warehouse";
    default:                    return "Unknown";
    }
}

} // namespace qoosvc::spatial
