#pragma once

#include "map_types.h"
#include "../common/result.h"
#include "../common/service_base.h"
#include <functional>
#include <future>
#include <memory>
#include <optional>
#include <string>
#include <vector>

namespace qoosvc::spatial {

/**
 * SpatialService — Robot spatial understanding service.
 *
 * Provides SLAM, semantic mapping, 3D reconstruction, object pose estimation,
 * dynamic scene understanding, and object retrieval.
 *
 * This is QooBot's spatial intelligence layer, analogous to ARKit/RoomPlan
 * for robots — enabling the robot to understand, navigate, and interact with
 * its physical environment.
 */
class SpatialService : public ServiceBase {
public:
    SpatialService();
    ~SpatialService() override;

    // ========================================================================
    // Configuration
    // ========================================================================

    Result<void> configure(const SLAMConfig& config);
    const SLAMConfig& config() const { return config_; }

    // ========================================================================
    // SLAM (Simultaneous Localization and Mapping)
    // ========================================================================

    /**
     * Start SLAM session. Robot will begin mapping its environment
     * while simultaneously localizing itself within it.
     */
    Result<void> start_slam();

    /**
     * Stop the SLAM session and finalize the map.
     */
    Result<void> stop_slam();

    /**
     * Pause SLAM (e.g., during navigation to a different area).
     */
    Result<void> pause_slam();

    /**
     * Resume a paused SLAM session.
     */
    Result<void> resume_slam();

    /**
     * Get the current occupancy grid map.
     */
    Result<OccupancyGrid> get_occupancy_grid() const;

    /**
     * Get the current SLAM status.
     */
    SLAMStatus get_slam_status() const;

    /**
     * Register a callback for SLAM status updates.
     */
    void on_slam_update(std::function<void(const SLAMStatus&)> callback);

    /**
     * Save the current map to a file (.qoomap format).
     */
    Result<void> save_map(const std::string& filepath);

    /**
     * Load a map from a file (.qoomap format).
     */
    Result<void> load_map(const std::string& filepath);

    /**
     * Get the robot's current pose estimate in the map frame.
     */
    Result<Pose3D> get_current_pose() const;

    // ========================================================================
    // Semantic Mapping
    // ========================================================================

    /**
     * Generate a semantic map from the current occupancy grid.
     * Classifies rooms, annotates objects, and builds topological connections.
     */
    Result<SemanticMap> generate_semantic_map();

    /**
     * Get the latest semantic map.
     */
    Result<SemanticMap> get_semantic_map() const;

    /**
     * Annotate a specific object in the map.
     */
    Result<void> annotate_object(const ObjectLabel& object);

    /**
     * Remove an object annotation.
     */
    Result<void> remove_object_annotation(int32_t object_id);

    /**
     * Get all objects of a specific class.
     */
    Result<std::vector<ObjectLabel>> find_objects_by_class(const std::string& class_name) const;

    /**
     * Get all objects in a specific room.
     */
    Result<std::vector<ObjectLabel>> get_objects_in_room(int32_t room_id) const;

    /**
     * Get room information by ID.
     */
    Result<RoomAnnotation> get_room_info(int32_t room_id) const;

    /**
     * Get all rooms.
     */
    Result<std::vector<RoomAnnotation>> get_all_rooms() const;

    // ========================================================================
    // Topological Map
    // ========================================================================

    /**
     * Build a topological map from the semantic map.
     * Creates nodes at room centers, doorways, and key points.
     */
    Result<TopologicalMap> build_topological_map();

    /**
     * Get the current topological map.
     */
    Result<TopologicalMap> get_topological_map() const;

    /**
     * Find the shortest topological path between two nodes.
     */
    Result<std::vector<int32_t>> find_topological_path(int32_t from_node, int32_t to_node) const;

    // ========================================================================
    // 3D Scene Reconstruction
    // ========================================================================

    /**
     * Generate a dense 3D point cloud of the environment.
     */
    Result<PointCloud> generate_point_cloud();

    /**
     * Generate a 3D mesh from the point cloud.
     */
    Result<Mesh3D> generate_mesh(ReconstructionMethod method = ReconstructionMethod::POISSON);

    /**
     * Get the latest 3D mesh.
     */
    Result<Mesh3D> get_mesh() const;

    // ========================================================================
    // Object Pose Estimation (6-DoF)
    // ========================================================================

    /**
     * Estimate the 6D pose of a known object.
     */
    Result<ObjectPose6D> estimate_object_pose(const std::string& object_class);

    /**
     * Detect grasp points on an object at the given pose.
     */
    Result<std::vector<GraspPoint>> detect_grasp_points(const ObjectPose6D& object_pose);

    // ========================================================================
    // Dynamic Scene Understanding
    // ========================================================================

    /**
     * Update tracking with latest sensor data.
     * Returns currently tracked objects.
     */
    Result<std::vector<TrackedObject>> update_tracking(const PointCloud& cloud);

    /**
     * Get all currently tracked objects.
     */
    std::vector<TrackedObject> get_tracked_objects() const;

    /**
     * Detect scene changes since last observation.
     */
    Result<std::vector<SceneChange>> detect_changes();

    /**
     * Register a callback for scene change events.
     */
    void on_scene_change(std::function<void(const SceneChange&)> callback);

    // ========================================================================
    // Object Retrieval ("Where are my keys?")
    // ========================================================================

    /**
     * Query for an object in the environment.
     * Searches semantic map + object memory.
     */
    Result<std::vector<ObjectQueryResult>> find_object(const ObjectQuery& query);

    /**
     * Remember an object's location for future queries.
     */
    Result<void> remember_object(const std::string& name, const std::string& object_class,
                                  const Pose3D& pose, const std::string& room_name);

    /**
     * Forget a remembered object.
     */
    Result<void> forget_object(const std::string& name);

    // ========================================================================
    // Service Lifecycle
    // ========================================================================

    bool is_slam_active() const { return slam_active_; }

protected:
    Result<void> on_initialize() override;
    Result<void> on_stop() override;

private:
    struct Impl;
    std::unique_ptr<Impl> impl_;

    SLAMConfig config_;
    bool slam_active_ = false;
};

} // namespace qoosvc::spatial
