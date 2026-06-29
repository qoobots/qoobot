#include "object_annotator.h"
#include <algorithm>
#include <cmath>
#include <queue>
#include <unordered_set>

namespace qoosvc::spatial {

ObjectAnnotator::ObjectAnnotator(const Config& config)
    : config_(config) {
}

ObjectAnnotator::~ObjectAnnotator() = default;

std::vector<ObjectLabel> ObjectAnnotator::detect_objects(const PointCloud& cloud) {
    if (cloud.points.empty()) return {};

    // Cluster points into object candidates
    auto clusters = cluster_points(cloud, 0.3);  // 30cm cluster tolerance

    std::vector<ObjectLabel> objects;

    for (const auto& cluster : clusters) {
        if (cluster.size() < 10) continue;  // Too few points

        auto bbox = compute_bounding_box(cluster);

        // Filter by size
        double sx = bbox[1].x - bbox[0].x;
        double sy = bbox[1].y - bbox[0].y;
        double sz = bbox[1].z - bbox[0].z;

        if (sx < config_.min_object_size && sy < config_.min_object_size) continue;
        if (sx > config_.max_object_size || sy > config_.max_object_size) continue;

        double confidence = 0.0;
        std::string class_name = classify_shape(cluster, bbox, confidence);

        if (confidence < config_.min_confidence) continue;

        ObjectLabel obj;
        obj.instance_id = next_instance_id();
        obj.class_name = class_name;
        obj.confidence = confidence;
        obj.bounding_box = bbox;

        // Compute centroid
        double cx = 0, cy = 0, cz = 0;
        for (const auto& p : cluster) {
            cx += p.x; cy += p.y; cz += p.z;
        }
        obj.centroid = {cx / cluster.size(), cy / cluster.size(), cz / cluster.size()};

        objects.push_back(obj);

        if (detection_callback_) {
            detection_callback_(obj);
        }
    }

    return objects;
}

void ObjectAnnotator::assign_to_rooms(std::vector<ObjectLabel>& objects,
                                       const std::vector<RoomAnnotation>& rooms) {
    for (auto& obj : objects) {
        for (const auto& room : rooms) {
            // Simple point-in-polygon test for 2D containment
            bool inside = false;
            const auto& boundary = room.boundary;
            size_t n = boundary.size();

            if (n >= 3) {
                for (size_t i = 0, j = n - 1; i < n; j = i++) {
                    if (((boundary[i].y > obj.centroid.y) !=
                         (boundary[j].y > obj.centroid.y)) &&
                        (obj.centroid.x <
                         (boundary[j].x - boundary[i].x) *
                         (obj.centroid.y - boundary[i].y) /
                         (boundary[j].y - boundary[i].y) + boundary[i].x)) {
                        inside = !inside;
                    }
                }
            }

            if (inside) {
                // Object is in this room (annotation stored separately)
                break;
            }
        }
    }
}

void ObjectAnnotator::on_detection(std::function<void(const ObjectLabel&)> callback) {
    detection_callback_ = std::move(callback);
}

int32_t ObjectAnnotator::next_instance_id() {
    return ++instance_counter_;
}

// ============================================================================
// Private Methods
// ============================================================================

std::vector<std::vector<PointXYZI>>
ObjectAnnotator::cluster_points(const PointCloud& cloud, double cluster_tolerance) {
    // Euclidean clustering using a simple grid-based approach
    if (cloud.points.empty()) return {};

    // Build spatial hash grid
    double cell_size = cluster_tolerance;
    std::unordered_map<int64_t, std::vector<size_t>> grid;

    for (size_t i = 0; i < cloud.points.size(); ++i) {
        const auto& p = cloud.points[i];
        int64_t cx = static_cast<int64_t>(std::floor(p.x / cell_size));
        int64_t cy = static_cast<int64_t>(std::floor(p.y / cell_size));
        int64_t cz = static_cast<int64_t>(std::floor(p.z / cell_size));
        int64_t key = (cx << 42) ^ (cy << 21) ^ cz;
        grid[key].push_back(i);
    }

    // Union-Find clustering
    std::vector<size_t> parent(cloud.points.size());
    for (size_t i = 0; i < parent.size(); ++i) parent[i] = i;

    std::function<size_t(size_t)> find = [&](size_t x) -> size_t {
        if (parent[x] != x) parent[x] = find(parent[x]);
        return parent[x];
    };

    auto union_sets = [&](size_t a, size_t b) {
        size_t ra = find(a), rb = find(b);
        if (ra != rb) parent[rb] = ra;
    };

    // Check neighbors in adjacent cells
    for (const auto& [key, indices] : grid) {
        int64_t cx = (key >> 42) & 0x1FFFFF;
        int64_t cy = (key >> 21) & 0x1FFFFF;
        int64_t cz = key & 0x1FFFFF;

        for (int64_t dx = -1; dx <= 1; ++dx) {
            for (int64_t dy = -1; dy <= 1; ++dy) {
                for (int64_t dz = -1; dz <= 1; ++dz) {
                    int64_t nkey = ((cx + dx) << 42) ^ ((cy + dy) << 21) ^ (cz + dz);
                    auto nit = grid.find(nkey);
                    if (nit == grid.end()) continue;

                    for (size_t i : indices) {
                        for (size_t j : nit->second) {
                            double dx_p = cloud.points[i].x - cloud.points[j].x;
                            double dy_p = cloud.points[i].y - cloud.points[j].y;
                            double dz_p = cloud.points[i].z - cloud.points[j].z;
                            double dist = std::sqrt(dx_p*dx_p + dy_p*dy_p + dz_p*dz_p);
                            if (dist < cluster_tolerance) {
                                union_sets(i, j);
                            }
                        }
                    }
                }
            }
        }
    }

    // Collect clusters
    std::unordered_map<size_t, std::vector<PointXYZI>> clusters;
    for (size_t i = 0; i < cloud.points.size(); ++i) {
        clusters[find(i)].push_back(cloud.points[i]);
    }

    std::vector<std::vector<PointXYZI>> result;
    for (auto& [root, pts] : clusters) {
        result.push_back(std::move(pts));
    }

    return result;
}

std::vector<Point3D> ObjectAnnotator::compute_bounding_box(
    const std::vector<PointXYZI>& cluster) {

    float min_x = std::numeric_limits<float>::max();
    float min_y = std::numeric_limits<float>::max();
    float min_z = std::numeric_limits<float>::max();
    float max_x = std::numeric_limits<float>::lowest();
    float max_y = std::numeric_limits<float>::lowest();
    float max_z = std::numeric_limits<float>::lowest();

    for (const auto& p : cluster) {
        min_x = std::min(min_x, p.x);
        min_y = std::min(min_y, p.y);
        min_z = std::min(min_z, p.z);
        max_x = std::max(max_x, p.x);
        max_y = std::max(max_y, p.y);
        max_z = std::max(max_z, p.z);
    }

    // 8 corners of axis-aligned bounding box
    return {
        {min_x, min_y, min_z},
        {max_x, min_y, min_z},
        {max_x, max_y, min_z},
        {min_x, max_y, min_z},
        {min_x, min_y, max_z},
        {max_x, min_y, max_z},
        {max_x, max_y, max_z},
        {min_x, max_y, max_z}
    };
}

std::string ObjectAnnotator::classify_shape(const std::vector<PointXYZI>& cluster,
                                              const std::vector<Point3D>& bbox,
                                              double& confidence) {
    // Simple shape-based classification using bounding box dimensions
    double sx = bbox[1].x - bbox[0].x;
    double sy = bbox[1].y - bbox[0].y;
    double sz = bbox[1].z - bbox[0].z;

    // Normalize: sort dimensions
    std::vector<double> dims = {sx, sy, sz};
    std::sort(dims.begin(), dims.end());
    double w = dims[0], h = dims[1], d = dims[2];

    // Height from ground (approximate)
    double z_min = bbox[0].z;

    // Classification heuristics
    if (d > 1.0 && d < 2.5 && h > 0.3 && h < 1.2 && w > 0.3 && w < 1.0) {
        confidence = 0.7;
        return "chair";
    }

    if (d > 0.8 && d < 2.5 && h > 0.5 && h < 1.2 && w > 0.6 && w < 1.5) {
        confidence = 0.65;
        return "table";
    }

    if (d > 1.5 && d < 2.5 && h > 1.5 && h < 2.5 && w > 0.5 && w < 1.0) {
        confidence = 0.6;
        return "door";
    }

    if (d > 0.3 && d < 1.0 && h > 0.3 && h < 1.0 && w > 0.3 && w < 1.0) {
        confidence = 0.5;
        return "box";
    }

    if (d > 2.0 && h > 0.3 && h < 1.2) {
        confidence = 0.55;
        return "sofa";
    }

    if (d > 0.5 && d < 1.5 && h > 0.5 && h < 2.0 && w > 0.5 && w < 1.0) {
        confidence = 0.5;
        return "cabinet";
    }

    confidence = 0.3;
    return "unknown";
}

} // namespace qoosvc::spatial
