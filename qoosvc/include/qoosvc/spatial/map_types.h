#pragma once

#include <cstdint>
#include <string>
#include <vector>

namespace qoosvc::spatial {

// ============================================================================
// Core Spatial Types
// ============================================================================

/**
 * 2D point with integer coordinates (grid map).
 */
struct Point2I {
    int32_t x = 0;
    int32_t y = 0;

    bool operator==(const Point2I& other) const {
        return x == other.x && y == other.y;
    }
};

/**
 * 3D point with double precision.
 */
struct Point3D {
    double x = 0.0;
    double y = 0.0;
    double z = 0.0;

    Point3D operator+(const Point3D& other) const {
        return {x + other.x, y + other.y, z + other.z};
    }

    Point3D operator-(const Point3D& other) const {
        return {x - other.x, y - other.y, z - other.z};
    }

    double norm() const {
        return std::sqrt(x * x + y * y + z * z);
    }

    double distance_to(const Point3D& other) const {
        return (*this - other).norm();
    }
};

/**
 * 3D pose: position + orientation (roll, pitch, yaw).
 */
struct Pose3D {
    double x = 0.0;
    double y = 0.0;
    double z = 0.0;
    double roll = 0.0;   // radians
    double pitch = 0.0;  // radians
    double yaw = 0.0;    // radians
    std::string frame_id = "map";

    Point3D position() const { return {x, y, z}; }
};

// ============================================================================
// Map Types
// ============================================================================

/**
 * Map type enumeration.
 */
enum class MapType : uint8_t {
    OCCUPANCY_GRID,    // 2D occupancy grid (laser)
    POINT_CLOUD,       // 3D point cloud (LiDAR)
    FEATURE_MAP,       // Visual feature map
    TOPOLOGICAL,       // Graph-based topological map
    SEMANTIC           // Semantic annotated map
};

/**
 * Map metadata.
 */
struct MapMetadata {
    std::string map_id;           // Unique map identifier
    std::string name;             // Human-readable name (e.g., "Home v1")
    MapType type = MapType::OCCUPANCY_GRID;
    int64_t created_at_us = 0;    // Creation timestamp (microseconds)
    int64_t updated_at_us = 0;    // Last update timestamp
    double resolution = 0.05;     // Grid resolution (meters/pixel)
    int32_t width = 0;            // Grid width (pixels)
    int32_t height = 0;           // Grid height (pixels)
    double origin_x = 0.0;        // Map origin x (meters)
    double origin_y = 0.0;        // Map origin y (meters)
    double total_area_sqm = 0.0;  // Total mapped area (sq meters)
    std::string checksum;         // SHA-256 checksum of map data
    std::string format_version = "1.0";
};

// ============================================================================
// Occupancy Grid
// ============================================================================

/**
 * Occupancy grid cell states.
 */
enum class OccupancyState : int8_t {
    UNKNOWN = -1,
    FREE = 0,
    OCCUPIED = 100
};

/**
 * 2D occupancy grid map.
 */
struct OccupancyGrid {
    MapMetadata metadata;
    std::vector<int8_t> data;  // Row-major, OccupancyState values
    double resolution = 0.05;
    int32_t width = 0;
    int32_t height = 0;
    Pose3D origin;

    int8_t at(int32_t x, int32_t y) const {
        if (x < 0 || x >= width || y < 0 || y >= height) return -1;
        return data[y * width + x];
    }

    bool is_occupied(int32_t x, int32_t y) const {
        return at(x, y) == static_cast<int8_t>(OccupancyState::OCCUPIED);
    }

    bool is_free(int32_t x, int32_t y) const {
        return at(x, y) == static_cast<int8_t>(OccupancyState::FREE);
    }

    bool is_unknown(int32_t x, int32_t y) const {
        return at(x, y) < 0;
    }

    bool is_in_bounds(int32_t x, int32_t y) const {
        return x >= 0 && x < width && y >= 0 && y < height;
    }

    Point2I world_to_grid(const Point3D& world) const {
        return {
            static_cast<int32_t>((world.x - origin.x) / resolution),
            static_cast<int32_t>((world.y - origin.y) / resolution)
        };
    }

    Point3D grid_to_world(int32_t gx, int32_t gy) const {
        return {
            origin.x + gx * resolution + resolution * 0.5,
            origin.y + gy * resolution + resolution * 0.5,
            0.0
        };
    }
};

// ============================================================================
// Point Cloud
// ============================================================================

/**
 * Single point in a point cloud.
 */
struct PointXYZI {
    float x = 0.0f;
    float y = 0.0f;
    float z = 0.0f;
    float intensity = 0.0f;
    uint32_t ring = 0;  // LiDAR ring index
};

/**
 * 3D point cloud.
 */
struct PointCloud {
    MapMetadata metadata;
    std::vector<PointXYZI> points;
    int64_t timestamp_us = 0;
    std::string frame_id = "lidar";
    bool is_dense = true;
};

// ============================================================================
// Semantic Map
// ============================================================================

/**
 * Room type classification.
 */
enum class RoomType : uint8_t {
    UNKNOWN = 0,
    LIVING_ROOM,
    BEDROOM,
    KITCHEN,
    BATHROOM,
    HALLWAY,
    DINING_ROOM,
    STUDY,
    BALCONY,
    GARAGE,
    OFFICE,
    MEETING_ROOM,
    CORRIDOR,
    WAREHOUSE
};

/**
 * Object semantic label.
 */
struct ObjectLabel {
    int32_t instance_id = 0;
    std::string class_name;        // e.g., "chair", "table", "door"
    double confidence = 0.0;
    Point3D centroid;
    std::vector<Point3D> bounding_box;  // 8 corners of 3D bounding box
};

/**
 * Room annotation.
 */
struct RoomAnnotation {
    int32_t room_id = 0;
    RoomType type = RoomType::UNKNOWN;
    std::string name;              // e.g., "Master Bedroom"
    std::vector<Point3D> boundary; // Polygon boundary
    double area_sqm = 0.0;
    std::vector<ObjectLabel> objects;
    double confidence = 0.0;
};

/**
 * Semantic map: occupancy grid + room/object annotations.
 */
struct SemanticMap {
    OccupancyGrid grid;
    std::vector<RoomAnnotation> rooms;
    std::vector<ObjectLabel> objects;
    int64_t annotated_at_us = 0;
};

// ============================================================================
// Topological Map
// ============================================================================

/**
 * A node in the topological map (e.g., room center, doorway).
 */
struct TopoNode {
    int32_t node_id = 0;
    Pose3D pose;
    std::string label;             // e.g., "living_room_center", "doorway_1"
    std::vector<std::string> tags; // e.g., {"charging_station", "pickup_point"}
};

/**
 * An edge connecting two topological nodes.
 */
struct TopoEdge {
    int32_t from_node_id = 0;
    int32_t to_node_id = 0;
    double distance = 0.0;         // Path distance (meters)
    double traversability = 1.0;   // 0.0 = blocked, 1.0 = fully traversable
    std::string passage_type;      // "door", "corridor", "stairs", "open"
};

/**
 * Topological map: graph-based representation.
 */
struct TopologicalMap {
    MapMetadata metadata;
    std::vector<TopoNode> nodes;
    std::vector<TopoEdge> edges;
};

// ============================================================================
// SLAM Types
// ============================================================================

/**
 * SLAM algorithm type.
 */
enum class SLAMAlgorithm : uint8_t {
    CARTOGRAPHER,      // Google Cartographer (lidar)
    GTSAM,             // Factor graph optimization
    G2O,               // General graph optimization
    ORB_SLAM3,         // Visual SLAM
    FAST_LIO           // LiDAR-inertial odometry
};

/**
 * SLAM configuration.
 */
struct SLAMConfig {
    SLAMAlgorithm algorithm = SLAMAlgorithm::CARTOGRAPHER;
    bool use_imu = true;
    bool use_odometry = true;
    bool loop_closure_enabled = true;
    double loop_closure_distance = 3.0;    // meters
    double loop_closure_angle = 0.3;       // radians
    int32_t submap_size = 100;             // scans per submap
    double resolution = 0.05;              // grid resolution
    double max_range = 30.0;               // LiDAR max range (meters)
    double min_range = 0.1;                // LiDAR min range (meters)
    bool publish_tf = true;
    std::string map_frame = "map";
    std::string odom_frame = "odom";
    std::string base_frame = "base_link";
};

/**
 * SLAM state.
 */
enum class SLAMState : uint8_t {
    UNINITIALIZED,
    INITIALIZING,
    MAPPING,
    LOCALIZING,
    LOOP_CLOSURE,
    OPTIMIZING,
    ERROR
};

/**
 * SLAM status information.
 */
struct SLAMStatus {
    SLAMState state = SLAMState::UNINITIALIZED;
    Pose3D current_pose;
    int32_t num_submaps = 0;
    int32_t num_landmarks = 0;
    int32_t num_loop_closures = 0;
    double mapping_area_sqm = 0.0;
    double localization_error = 0.0;  // meters
    double cpu_usage_percent = 0.0;
    double memory_mb = 0.0;
    int64_t last_update_us = 0;
};

// ============================================================================
// 3D Reconstruction Types
// ============================================================================

/**
 * 3D reconstruction method.
 */
enum class ReconstructionMethod : uint8_t {
    TSDF,              // Truncated Signed Distance Function
    MESH_NAIVE,        // Naive mesh from point cloud
    POISSON,           // Poisson surface reconstruction
    GAUSSIAN_SPLATTING // 3D Gaussian Splatting
};

/**
 * Triangle mesh face.
 */
struct TriangleFace {
    uint32_t v0 = 0;
    uint32_t v1 = 0;
    uint32_t v2 = 0;
};

/**
 * 3D mesh.
 */
struct Mesh3D {
    MapMetadata metadata;
    std::vector<Point3D> vertices;
    std::vector<TriangleFace> faces;
    std::vector<float> vertex_colors;  // RGB packed as floats, 3 per vertex
    bool has_normals = false;
    std::vector<Point3D> normals;
};

// ============================================================================
// Object Pose Estimation Types
// ============================================================================

/**
 * 6D object pose estimation result.
 */
struct ObjectPose6D {
    int32_t object_id = 0;
    std::string class_name;
    Pose3D pose;                    // 6D pose in world frame
    double confidence = 0.0;
    std::vector<Point3D> bounding_box_3d;
    Point2I bounding_box_2d_min;    // 2D projection (image coordinates)
    Point2I bounding_box_2d_max;
};

/**
 * Grasp point candidate.
 */
struct GraspPoint {
    Point3D position;
    Point3D approach_direction;     // Normalized approach vector
    double width = 0.0;             // Required gripper opening (meters)
    double quality = 0.0;           // Grasp quality score [0, 1]
};

// ============================================================================
// Dynamic Scene Types
// ============================================================================

/**
 * Tracked object state.
 */
struct TrackedObject {
    int32_t track_id = 0;
    std::string class_name;
    Pose3D pose;
    Point3D velocity;               // m/s in world frame
    double size_x = 0.0;
    double size_y = 0.0;
    double size_z = 0.0;
    double confidence = 0.0;
    int64_t first_seen_us = 0;
    int64_t last_seen_us = 0;
    bool is_static = false;
};

/**
 * Scene change event.
 */
struct SceneChange {
    enum class Type : uint8_t {
        OBJECT_ADDED,
        OBJECT_REMOVED,
        OBJECT_MOVED,
        ROOM_CHANGED,
        OCCUPANCY_CHANGED
    };
    Type type = Type::OBJECT_MOVED;
    int32_t object_id = 0;
    Pose3D old_pose;
    Pose3D new_pose;
    int64_t timestamp_us = 0;
    double significance = 0.0;      // How significant the change is [0, 1]
};

// ============================================================================
// Object Query Types
// ============================================================================

/**
 * Query for finding objects in the environment.
 */
struct ObjectQuery {
    std::string object_name;           // e.g., "keys", "wallet"
    std::string object_class;          // e.g., "keys", "phone", "book"
    int32_t max_results = 5;
    double min_confidence = 0.5;
    bool include_last_seen = true;     // Include objects from memory
    int64_t time_window_us = 0;        // 0 = no time limit
};

/**
 * Object query result.
 */
struct ObjectQueryResult {
    std::string object_name;
    std::string object_class;
    Pose3D last_known_pose;
    int64_t last_seen_us = 0;
    double confidence = 0.0;
    std::string room_name;             // Room where object was last seen
    bool is_currently_visible = false;
};

// ============================================================================
// Map File Format
// ============================================================================

/**
 * QooMap file header (binary format .qoomap).
 */
struct QooMapHeader {
    char magic[8] = {'Q', 'O', 'O', 'M', 'A', 'P', ' ', ' '};
    uint32_t version = 1;
    uint32_t header_size = sizeof(QooMapHeader);
    MapType map_type = MapType::OCCUPANCY_GRID;
    double resolution = 0.05;
    int32_t width = 0;
    int32_t height = 0;
    double origin_x = 0.0;
    double origin_y = 0.0;
    int64_t created_at_us = 0;
    int64_t updated_at_us = 0;
    uint32_t checksum = 0;         // CRC32 of data section
    uint32_t reserved[4] = {0};
};

} // namespace qoosvc::spatial
