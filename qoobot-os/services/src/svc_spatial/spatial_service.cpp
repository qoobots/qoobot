#include "qoosvc/spatial/spatial_service.h"
#include "slam/laser_slam.h"
#include "semantic/room_classifier.h"
#include "semantic/object_annotator.h"
#include "semantic/topological_map.h"
#include <algorithm>
#include <chrono>
#include <mutex>
#include <string>
#include <unordered_map>

namespace qoosvc::spatial {

// ============================================================================
// SpatialService::Impl
// ============================================================================

struct SpatialService::Impl {
    // SLAM engine
    std::unique_ptr<LaserSLAM> slam;
    SLAMStatus slam_status;

    // Semantic mapping
    SemanticMap semantic_map;
    RoomClassifier::Config room_classifier_config;
    ObjectAnnotator::Config object_annotator_config;
    TopologicalMapBuilder::Config topo_builder_config;

    // Topological map
    TopologicalMap topological_map;
    bool topo_map_valid = false;

    // Object memory (for "where are my keys?" queries)
    struct ObjectMemory {
        std::string name;
        std::string object_class;
        Pose3D pose;
        std::string room_name;
        int64_t remembered_at_us = 0;
    };
    std::vector<ObjectMemory> object_memory;

    // Dynamic scene tracking
    std::vector<TrackedObject> tracked_objects;
    std::vector<SceneChange> pending_changes;

    // 3D reconstruction cache
    PointCloud cached_point_cloud;
    Mesh3D cached_mesh;
    bool mesh_valid = false;

    // Callbacks
    std::function<void(const SLAMStatus&)> slam_callback;
    std::function<void(const SceneChange&)> scene_change_callback;

    // Thread safety
    mutable std::mutex mutex;
};

// ============================================================================
// Constructor / Destructor
// ============================================================================

SpatialService::SpatialService()
    : ServiceBase("spatial_service")
    , impl_(std::make_unique<Impl>()) {

    impl_->room_classifier_config.min_room_area = 4.0;
    impl_->room_classifier_config.max_room_area = 200.0;
    impl_->room_classifier_config.door_width_min = 0.6;
    impl_->room_classifier_config.door_width_max = 1.5;

    impl_->object_annotator_config.min_confidence = 0.5;
    impl_->object_annotator_config.max_object_size = 3.0;

    impl_->topo_builder_config.doorway_connection_distance = 2.0;
}

SpatialService::~SpatialService() {
    stop();
}

// ============================================================================
// Configuration
// ============================================================================

Result<void> SpatialService::configure(const SLAMConfig& config) {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    config_ = config;
    return Result<void>::ok();
}

// ============================================================================
// SLAM
// ============================================================================

Result<void> SpatialService::start_slam() {
    std::lock_guard<std::mutex> lock(impl_->mutex);

    if (slam_active_) {
        return Result<void>::err(ErrorCode::INTERNAL, "SLAM already active");
    }

    impl_->slam = std::make_unique<LaserSLAM>(config_);
    if (!impl_->slam->initialize()) {
        impl_->slam.reset();
        return Result<void>::err(ErrorCode::SPATIAL_SLAM_FAILED,
                                  "Failed to initialize SLAM");
    }

    impl_->slam_status = SLAMStatus{};
    impl_->slam_status.state = SLAMState::MAPPING;
    impl_->topo_map_valid = false;
    impl_->mesh_valid = false;

    slam_active_ = true;
    return Result<void>::ok();
}

Result<void> SpatialService::stop_slam() {
    std::lock_guard<std::mutex> lock(impl_->mutex);

    if (!slam_active_ || !impl_->slam) {
        return Result<void>::err(ErrorCode::INTERNAL, "SLAM not active");
    }

    impl_->slam_status = impl_->slam->get_status();
    impl_->slam_status.state = SLAMState::UNINITIALIZED;

    slam_active_ = false;
    return Result<void>::ok();
}

Result<void> SpatialService::pause_slam() {
    std::lock_guard<std::mutex> lock(impl_->mutex);

    if (!slam_active_) {
        return Result<void>::err(ErrorCode::INTERNAL, "SLAM not active");
    }

    impl_->slam_status.state = SLAMState::LOCALIZING;
    return Result<void>::ok();
}

Result<void> SpatialService::resume_slam() {
    std::lock_guard<std::mutex> lock(impl_->mutex);

    if (!slam_active_) {
        return Result<void>::err(ErrorCode::INTERNAL, "SLAM not active");
    }

    impl_->slam_status.state = SLAMState::MAPPING;
    return Result<void>::ok();
}

Result<OccupancyGrid> SpatialService::get_occupancy_grid() const {
    std::lock_guard<std::mutex> lock(impl_->mutex);

    if (!impl_->slam) {
        return Result<OccupancyGrid>::err(ErrorCode::SPATIAL_MAP_NOT_LOADED,
                                           "SLAM not initialized");
    }

    return impl_->slam->get_grid();
}

SLAMStatus SpatialService::get_slam_status() const {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    if (impl_->slam) {
        return impl_->slam->get_status();
    }
    return impl_->slam_status;
}

void SpatialService::on_slam_update(std::function<void(const SLAMStatus&)> callback) {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    impl_->slam_callback = std::move(callback);
}

Result<void> SpatialService::save_map(const std::string& filepath) {
    std::lock_guard<std::mutex> lock(impl_->mutex);

    if (!impl_->slam) {
        return Result<void>::err(ErrorCode::SPATIAL_MAP_NOT_LOADED,
                                  "No map to save");
    }

    if (!impl_->slam->save_map(filepath)) {
        return Result<void>::err(ErrorCode::INTERNAL, "Failed to save map");
    }

    return Result<void>::ok();
}

Result<void> SpatialService::load_map(const std::string& filepath) {
    std::lock_guard<std::mutex> lock(impl_->mutex);

    if (!impl_->slam) {
        impl_->slam = std::make_unique<LaserSLAM>(config_);
        impl_->slam->initialize();
    }

    if (!impl_->slam->load_map(filepath)) {
        return Result<void>::err(ErrorCode::SPATIAL_MAP_NOT_LOADED,
                                  "Failed to load map: " + filepath);
    }

    impl_->slam_status.state = SLAMState::LOCALIZING;
    slam_active_ = true;
    impl_->topo_map_valid = false;
    impl_->mesh_valid = false;

    return Result<void>::ok();
}

Result<Pose3D> SpatialService::get_current_pose() const {
    std::lock_guard<std::mutex> lock(impl_->mutex);

    if (!impl_->slam) {
        return Result<Pose3D>::err(ErrorCode::SPATIAL_MAP_NOT_LOADED,
                                    "No pose available");
    }

    return impl_->slam->get_pose();
}

// ============================================================================
// Semantic Mapping
// ============================================================================

Result<SemanticMap> SpatialService::generate_semantic_map() {
    std::lock_guard<std::mutex> lock(impl_->mutex);

    if (!impl_->slam) {
        return Result<SemanticMap>::err(ErrorCode::SPATIAL_MAP_NOT_LOADED,
                                         "No occupancy grid available");
    }

    const auto& grid = impl_->slam->get_grid();

    // 1. Segment rooms
    RoomClassifier classifier(impl_->room_classifier_config);
    auto room_candidates = classifier.segment_rooms(grid);

    // 2. Classify rooms
    SemanticMap sem_map;
    sem_map.grid = grid;
    int32_t room_id = 0;

    for (const auto& candidate : room_candidates) {
        RoomAnnotation room;
        room.room_id = room_id++;
        room.type = classifier.classify(candidate, room_candidates);
        room.name = RoomClassifier::room_type_name(room.type) + " " +
                    std::to_string(room.room_id);
        room.boundary = candidate.boundary;
        room.area_sqm = candidate.area_sqm;
        room.confidence = 0.7;

        sem_map.rooms.push_back(room);
    }

    // 3. Annotate objects (from cached point cloud if available)
    if (!impl_->cached_point_cloud.points.empty()) {
        ObjectAnnotator annotator(impl_->object_annotator_config);
        auto objects = annotator.detect_objects(impl_->cached_point_cloud);
        annotator.assign_to_rooms(objects, sem_map.rooms);
        sem_map.objects = std::move(objects);
    }

    sem_map.annotated_at_us = std::chrono::duration_cast<std::chrono::microseconds>(
        std::chrono::system_clock::now().time_since_epoch()).count();

    impl_->semantic_map = sem_map;

    return sem_map;
}

Result<SemanticMap> SpatialService::get_semantic_map() const {
    std::lock_guard<std::mutex> lock(impl_->mutex);

    if (impl_->semantic_map.rooms.empty()) {
        return Result<SemanticMap>::err(ErrorCode::SPATIAL_MAP_NOT_LOADED,
                                         "Semantic map not yet generated");
    }

    return impl_->semantic_map;
}

Result<void> SpatialService::annotate_object(const ObjectLabel& object) {
    std::lock_guard<std::mutex> lock(impl_->mutex);

    impl_->semantic_map.objects.push_back(object);
    return Result<void>::ok();
}

Result<void> SpatialService::remove_object_annotation(int32_t object_id) {
    std::lock_guard<std::mutex> lock(impl_->mutex);

    auto& objects = impl_->semantic_map.objects;
    auto it = std::find_if(objects.begin(), objects.end(),
        [object_id](const ObjectLabel& o) { return o.instance_id == object_id; });

    if (it == objects.end()) {
        return Result<void>::err(ErrorCode::SPATIAL_OBJECT_NOT_FOUND,
                                  "Object not found: " + std::to_string(object_id));
    }

    objects.erase(it);
    return Result<void>::ok();
}

Result<std::vector<ObjectLabel>> SpatialService::find_objects_by_class(
    const std::string& class_name) const {

    std::lock_guard<std::mutex> lock(impl_->mutex);

    std::vector<ObjectLabel> results;
    for (const auto& obj : impl_->semantic_map.objects) {
        if (obj.class_name == class_name) {
            results.push_back(obj);
        }
    }

    return results;
}

Result<std::vector<ObjectLabel>> SpatialService::get_objects_in_room(
    int32_t room_id) const {

    std::lock_guard<std::mutex> lock(impl_->mutex);

    // Find room
    auto room_it = std::find_if(impl_->semantic_map.rooms.begin(),
        impl_->semantic_map.rooms.end(),
        [room_id](const RoomAnnotation& r) { return r.room_id == room_id; });

    if (room_it == impl_->semantic_map.rooms.end()) {
        return Result<std::vector<ObjectLabel>>::err(
            ErrorCode::SPATIAL_OBJECT_NOT_FOUND, "Room not found");
    }

    // Find objects in room (simple containment check)
    std::vector<ObjectLabel> results;
    for (const auto& obj : impl_->semantic_map.objects) {
        bool inside = false;
        const auto& boundary = room_it->boundary;
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
            results.push_back(obj);
        }
    }

    return results;
}

Result<RoomAnnotation> SpatialService::get_room_info(int32_t room_id) const {
    std::lock_guard<std::mutex> lock(impl_->mutex);

    auto it = std::find_if(impl_->semantic_map.rooms.begin(),
        impl_->semantic_map.rooms.end(),
        [room_id](const RoomAnnotation& r) { return r.room_id == room_id; });

    if (it == impl_->semantic_map.rooms.end()) {
        return Result<RoomAnnotation>::err(ErrorCode::SPATIAL_OBJECT_NOT_FOUND,
                                            "Room not found");
    }

    return *it;
}

Result<std::vector<RoomAnnotation>> SpatialService::get_all_rooms() const {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    return impl_->semantic_map.rooms;
}

// ============================================================================
// Topological Map
// ============================================================================

Result<TopologicalMap> SpatialService::build_topological_map() {
    std::lock_guard<std::mutex> lock(impl_->mutex);

    if (impl_->semantic_map.rooms.empty()) {
        return Result<TopologicalMap>::err(ErrorCode::SPATIAL_MAP_NOT_LOADED,
                                            "Semantic map not available");
    }

    TopologicalMapBuilder builder(impl_->topo_builder_config);
    impl_->topological_map = builder.build(impl_->semantic_map);
    impl_->topo_map_valid = true;

    return impl_->topological_map;
}

Result<TopologicalMap> SpatialService::get_topological_map() const {
    std::lock_guard<std::mutex> lock(impl_->mutex);

    if (!impl_->topo_map_valid) {
        return Result<TopologicalMap>::err(ErrorCode::SPATIAL_MAP_NOT_LOADED,
                                            "Topological map not built");
    }

    return impl_->topological_map;
}

Result<std::vector<int32_t>> SpatialService::find_topological_path(
    int32_t from_node, int32_t to_node) const {

    std::lock_guard<std::mutex> lock(impl_->mutex);

    if (!impl_->topo_map_valid) {
        return Result<std::vector<int32_t>>::err(ErrorCode::SPATIAL_MAP_NOT_LOADED,
                                                   "Topological map not built");
    }

    auto path = TopologicalMapBuilder::find_shortest_path(
        impl_->topological_map, from_node, to_node);

    if (path.empty()) {
        return Result<std::vector<int32_t>>::err(ErrorCode::NAV_NO_PATH,
                                                   "No path found between nodes");
    }

    return path;
}

// ============================================================================
// 3D Scene Reconstruction
// ============================================================================

Result<PointCloud> SpatialService::generate_point_cloud() {
    std::lock_guard<std::mutex> lock(impl_->mutex);

    // In production, this would aggregate LiDAR scans into a dense point cloud
    // For now, return cached point cloud
    if (impl_->cached_point_cloud.points.empty()) {
        // Create a placeholder point cloud from occupancy grid
        if (!impl_->slam) {
            return Result<PointCloud>::err(ErrorCode::SPATIAL_MAP_NOT_LOADED,
                                            "No map available");
        }

        const auto& grid = impl_->slam->get_grid();
        PointCloud cloud;
        cloud.metadata.map_id = "reconstruction_1";
        cloud.metadata.type = MapType::POINT_CLOUD;
        cloud.frame_id = "map";
        cloud.is_dense = false;

        for (int32_t y = 0; y < grid.height; y += 2) {
            for (int32_t x = 0; x < grid.width; x += 2) {
                if (grid.is_occupied(x, y)) {
                    auto wp = grid.grid_to_world(x, y);
                    cloud.points.push_back({
                        static_cast<float>(wp.x),
                        static_cast<float>(wp.y),
                        0.5f,   // Assume 0.5m height for occupied cells
                        0.5f,   // Medium intensity
                        0
                    });
                }
            }
        }

        impl_->cached_point_cloud = cloud;
    }

    return impl_->cached_point_cloud;
}

Result<Mesh3D> SpatialService::generate_mesh(ReconstructionMethod method) {
    std::lock_guard<std::mutex> lock(impl_->mutex);

    // Get point cloud first
    auto pc_result = generate_point_cloud();
    if (pc_result.is_err()) {
        return Result<Mesh3D>::err(pc_result.error_code(), pc_result.error_message());
    }

    const auto& cloud = *pc_result;

    // Generate mesh from point cloud
    Mesh3D mesh;
    mesh.metadata.map_id = "mesh_1";
    mesh.metadata.type = MapType::FEATURE_MAP;

    // Convert points to vertices
    mesh.vertices.reserve(cloud.points.size());
    for (const auto& p : cloud.points) {
        mesh.vertices.push_back({p.x, p.y, p.z});
    }

    // In production, this would use Poisson surface reconstruction
    // or Marching Cubes for TSDF-based reconstruction.
    // For now, create a simple triangulation of nearby points.

    if (method == ReconstructionMethod::MESH_NAIVE && cloud.points.size() >= 3) {
        // Create a simple height-map triangulation
        // Group points into a grid and triangulate
        std::unordered_map<int64_t, std::vector<size_t>> grid_map;
        double cell_size = 0.5;

        for (size_t i = 0; i < cloud.points.size(); ++i) {
            int64_t cx = static_cast<int64_t>(std::floor(cloud.points[i].x / cell_size));
            int64_t cy = static_cast<int64_t>(std::floor(cloud.points[i].y / cell_size));
            grid_map[(cx << 32) ^ cy].push_back(i);
        }

        for (const auto& [key, indices] : grid_map) {
            int64_t cx = (key >> 32) & 0xFFFFFFFF;
            int64_t cy = key & 0xFFFFFFFF;

            // Check right neighbor
            int64_t rkey = ((cx + 1) << 32) ^ cy;
            auto rit = grid_map.find(rkey);

            // Check bottom neighbor
            int64_t bkey = (cx << 32) ^ (cy + 1);
            auto bit = grid_map.find(bkey);

            // Check diagonal neighbor
            int64_t dkey = ((cx + 1) << 32) ^ (cy + 1);
            auto dit = grid_map.find(dkey);

            if (rit != grid_map.end() && dit != grid_map.end()) {
                mesh.faces.push_back({
                    static_cast<uint32_t>(indices[0]),
                    static_cast<uint32_t>(rit->second[0]),
                    static_cast<uint32_t>(dit->second[0])
                });
            }

            if (bit != grid_map.end() && dit != grid_map.end()) {
                mesh.faces.push_back({
                    static_cast<uint32_t>(indices[0]),
                    static_cast<uint32_t>(dit->second[0]),
                    static_cast<uint32_t>(bit->second[0])
                });
            }
        }
    }

    impl_->cached_mesh = mesh;
    impl_->mesh_valid = true;

    return mesh;
}

Result<Mesh3D> SpatialService::get_mesh() const {
    std::lock_guard<std::mutex> lock(impl_->mutex);

    if (!impl_->mesh_valid) {
        return Result<Mesh3D>::err(ErrorCode::INTERNAL,
                                    "Mesh not yet generated");
    }

    return impl_->cached_mesh;
}

// ============================================================================
// Object Pose Estimation
// ============================================================================

Result<ObjectPose6D> SpatialService::estimate_object_pose(const std::string& object_class) {
    std::lock_guard<std::mutex> lock(impl_->mutex);

    // Search semantic map for matching objects
    for (const auto& obj : impl_->semantic_map.objects) {
        if (obj.class_name == object_class) {
            ObjectPose6D pose;
            pose.object_id = obj.instance_id;
            pose.class_name = obj.class_name;
            pose.pose = {obj.centroid.x, obj.centroid.y, obj.centroid.z,
                         0, 0, 0, "map"};
            pose.confidence = obj.confidence;
            pose.bounding_box_3d = obj.bounding_box;
            return pose;
        }
    }

    return Result<ObjectPose6D>::err(ErrorCode::SPATIAL_OBJECT_NOT_FOUND,
                                      "Object not found: " + object_class);
}

Result<std::vector<GraspPoint>> SpatialService::detect_grasp_points(
    const ObjectPose6D& object_pose) {

    // Generate candidate grasp points around the object
    std::vector<GraspPoint> grasps;

    // Top-down approach grasps
    for (int i = 0; i < 4; ++i) {
        double angle = i * M_PI / 2.0;
        GraspPoint gp;
        gp.position = {
            object_pose.pose.x + 0.1 * std::cos(angle),
            object_pose.pose.y + 0.1 * std::sin(angle),
            object_pose.pose.z + 0.15  // Slightly above center
        };
        gp.approach_direction = {0, 0, -1};  // Top-down
        gp.width = 0.08;  // 8cm gripper opening
        gp.quality = 0.7;
        grasps.push_back(gp);
    }

    // Side approach grasps
    for (int i = 0; i < 4; ++i) {
        double angle = i * M_PI / 2.0;
        GraspPoint gp;
        gp.position = {
            object_pose.pose.x + 0.15 * std::cos(angle),
            object_pose.pose.y + 0.15 * std::sin(angle),
            object_pose.pose.z
        };
        gp.approach_direction = {
            -std::cos(angle),
            -std::sin(angle),
            0
        };
        gp.width = 0.08;
        gp.quality = 0.6;
        grasps.push_back(gp);
    }

    return grasps;
}

// ============================================================================
// Dynamic Scene Understanding
// ============================================================================

Result<std::vector<TrackedObject>> SpatialService::update_tracking(
    const PointCloud& cloud) {

    std::lock_guard<std::mutex> lock(impl_->mutex);

    // Simple tracking: cluster new points and match to existing tracks
    ObjectAnnotator annotator(impl_->object_annotator_config);
    auto detections = annotator.detect_objects(cloud);

    int64_t now_us = std::chrono::duration_cast<std::chrono::microseconds>(
        std::chrono::system_clock::now().time_since_epoch()).count();

    // Match detections to existing tracks (nearest-neighbor association)
    std::vector<bool> detection_matched(detections.size(), false);

    for (auto& track : impl_->tracked_objects) {
        double best_dist = 2.0;  // Max association distance (meters)
        int32_t best_idx = -1;

        for (size_t i = 0; i < detections.size(); ++i) {
            if (detection_matched[i]) continue;

            double dist = std::hypot(
                detections[i].centroid.x - track.pose.x,
                detections[i].centroid.y - track.pose.y);

            if (dist < best_dist) {
                best_dist = dist;
                best_idx = static_cast<int32_t>(i);
            }
        }

        if (best_idx >= 0) {
            detection_matched[best_idx] = true;

            // Update track
            Point3D new_pos = {detections[best_idx].centroid.x,
                                detections[best_idx].centroid.y,
                                detections[best_idx].centroid.z};

            // Compute velocity
            double dt = (now_us - track.last_seen_us) / 1e6;
            if (dt > 0 && dt < 5.0) {
                track.velocity = {
                    (new_pos.x - track.pose.x) / dt,
                    (new_pos.y - track.pose.y) / dt,
                    (new_pos.z - track.pose.z) / dt
                };
            }

            // Check if object moved significantly
            double moved = new_pos.distance_to({track.pose.x, track.pose.y, track.pose.z});
            if (moved > 0.3 && track.last_seen_us > 0) {
                SceneChange change;
                change.type = SceneChange::Type::OBJECT_MOVED;
                change.object_id = track.track_id;
                change.old_pose = track.pose;
                track.pose = {new_pos.x, new_pos.y, new_pos.z, 0, 0, 0, "map"};
                change.new_pose = track.pose;
                change.timestamp_us = now_us;
                change.significance = std::min(1.0, moved / 2.0);
                impl_->pending_changes.push_back(change);

                if (impl_->scene_change_callback) {
                    impl_->scene_change_callback(change);
                }
            } else {
                track.pose = {new_pos.x, new_pos.y, new_pos.z, 0, 0, 0, "map"};
            }

            track.last_seen_us = now_us;
            track.confidence = detections[best_idx].confidence;
            track.is_static = (track.velocity.norm() < 0.1);
        }
    }

    // Create new tracks for unmatched detections
    for (size_t i = 0; i < detections.size(); ++i) {
        if (detection_matched[i]) continue;

        TrackedObject track;
        track.track_id = static_cast<int32_t>(impl_->tracked_objects.size());
        track.class_name = detections[i].class_name;
        track.pose = {detections[i].centroid.x, detections[i].centroid.y,
                       detections[i].centroid.z, 0, 0, 0, "map"};
        track.confidence = detections[i].confidence;
        track.first_seen_us = now_us;
        track.last_seen_us = now_us;
        track.is_static = true;
        impl_->tracked_objects.push_back(track);

        // New object detected
        SceneChange change;
        change.type = SceneChange::Type::OBJECT_ADDED;
        change.object_id = track.track_id;
        change.new_pose = track.pose;
        change.timestamp_us = now_us;
        change.significance = 0.5;
        impl_->pending_changes.push_back(change);
    }

    // Remove stale tracks (not seen for >30 seconds)
    impl_->tracked_objects.erase(
        std::remove_if(impl_->tracked_objects.begin(),
                        impl_->tracked_objects.end(),
                        [now_us](const TrackedObject& t) {
                            return (now_us - t.last_seen_us) > 30'000'000;
                        }),
        impl_->tracked_objects.end());

    return impl_->tracked_objects;
}

std::vector<TrackedObject> SpatialService::get_tracked_objects() const {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    return impl_->tracked_objects;
}

Result<std::vector<SceneChange>> SpatialService::detect_changes() {
    std::lock_guard<std::mutex> lock(impl_->mutex);

    auto changes = std::move(impl_->pending_changes);
    impl_->pending_changes.clear();

    return changes;
}

void SpatialService::on_scene_change(
    std::function<void(const SceneChange&)> callback) {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    impl_->scene_change_callback = std::move(callback);
}

// ============================================================================
// Object Retrieval
// ============================================================================

Result<std::vector<ObjectQueryResult>> SpatialService::find_object(
    const ObjectQuery& query) {

    std::lock_guard<std::mutex> lock(impl_->mutex);

    std::vector<ObjectQueryResult> results;
    int64_t now_us = std::chrono::duration_cast<std::chrono::microseconds>(
        std::chrono::system_clock::now().time_since_epoch()).count();

    // 1. Search semantic map objects
    for (const auto& obj : impl_->semantic_map.objects) {
        if (!query.object_class.empty() && obj.class_name != query.object_class) {
            continue;
        }
        if (obj.confidence < query.min_confidence) continue;

        ObjectQueryResult result;
        result.object_name = obj.class_name;
        result.object_class = obj.class_name;
        result.last_known_pose = {obj.centroid.x, obj.centroid.y, obj.centroid.z,
                                   0, 0, 0, "map"};
        result.confidence = obj.confidence;
        result.is_currently_visible = true;

        // Find which room this object is in
        for (const auto& room : impl_->semantic_map.rooms) {
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
                result.room_name = room.name;
                break;
            }
        }

        results.push_back(result);
    }

    // 2. Search object memory (for objects not currently visible)
    for (const auto& mem : impl_->object_memory) {
        bool already_found = false;
        for (const auto& r : results) {
            if (r.object_name == mem.name) {
                already_found = true;
                break;
            }
        }
        if (already_found) continue;

        if (!query.object_name.empty() && mem.name != query.object_name) continue;

        // Check time window
        if (query.time_window_us > 0 &&
            (now_us - mem.remembered_at_us) > query.time_window_us) {
            continue;
        }

        ObjectQueryResult result;
        result.object_name = mem.name;
        result.object_class = mem.object_class;
        result.last_known_pose = mem.pose;
        result.last_seen_us = mem.remembered_at_us;
        result.confidence = 0.5;  // Memory is less certain
        result.room_name = mem.room_name;
        result.is_currently_visible = false;

        results.push_back(result);
    }

    // Sort by confidence (highest first), limit results
    std::sort(results.begin(), results.end(),
        [](const ObjectQueryResult& a, const ObjectQueryResult& b) {
            return a.confidence > b.confidence;
        });

    if (results.size() > static_cast<size_t>(query.max_results)) {
        results.resize(query.max_results);
    }

    return results;
}

Result<void> SpatialService::remember_object(const std::string& name,
                                               const std::string& object_class,
                                               const Pose3D& pose,
                                               const std::string& room_name) {
    std::lock_guard<std::mutex> lock(impl_->mutex);

    // Update existing memory or add new
    for (auto& mem : impl_->object_memory) {
        if (mem.name == name) {
            mem.object_class = object_class;
            mem.pose = pose;
            mem.room_name = room_name;
            mem.remembered_at_us = std::chrono::duration_cast<std::chrono::microseconds>(
                std::chrono::system_clock::now().time_since_epoch()).count();
            return Result<void>::ok();
        }
    }

    Impl::ObjectMemory mem;
    mem.name = name;
    mem.object_class = object_class;
    mem.pose = pose;
    mem.room_name = room_name;
    mem.remembered_at_us = std::chrono::duration_cast<std::chrono::microseconds>(
        std::chrono::system_clock::now().time_since_epoch()).count();
    impl_->object_memory.push_back(mem);

    return Result<void>::ok();
}

Result<void> SpatialService::forget_object(const std::string& name) {
    std::lock_guard<std::mutex> lock(impl_->mutex);

    auto it = std::find_if(impl_->object_memory.begin(),
        impl_->object_memory.end(),
        [&name](const Impl::ObjectMemory& m) { return m.name == name; });

    if (it == impl_->object_memory.end()) {
        return Result<void>::err(ErrorCode::SPATIAL_OBJECT_NOT_FOUND,
                                  "Object not in memory: " + name);
    }

    impl_->object_memory.erase(it);
    return Result<void>::ok();
}

// ============================================================================
// Service Lifecycle
// ============================================================================

Result<void> SpatialService::on_initialize() {
    return Result<void>::ok();
}

Result<void> SpatialService::on_stop() {
    if (slam_active_) {
        stop_slam();
    }
    return Result<void>::ok();
}

} // namespace qoosvc::spatial
