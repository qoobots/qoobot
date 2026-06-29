#pragma once

#include "qoosvc/spatial/map_types.h"
#include <functional>
#include <string>
#include <vector>

namespace qoosvc::spatial {

/**
 * ObjectAnnotator — Detects and annotates objects in the semantic map.
 *
 * In production, this would use object detection models (YOLO, DETR) to
 * identify furniture, appliances, and other objects from camera data.
 */
class ObjectAnnotator {
public:
    struct Config {
        double min_confidence = 0.5;
        double max_object_size = 3.0;    // meters
        double min_object_size = 0.05;   // meters
    };

    explicit ObjectAnnotator(const Config& config);
    ~ObjectAnnotator();

    /**
     * Detect objects in a point cloud region.
     * Returns annotated object labels.
     */
    std::vector<ObjectLabel> detect_objects(const PointCloud& cloud);

    /**
     * Assign objects to rooms based on spatial containment.
     */
    void assign_to_rooms(std::vector<ObjectLabel>& objects,
                         const std::vector<RoomAnnotation>& rooms);

    /**
     * Register a callback for new object detections.
     */
    void on_detection(std::function<void(const ObjectLabel&)> callback);

    /**
     * Get the next available object instance ID.
     */
    int32_t next_instance_id();

private:
    // Cluster points into object candidates using Euclidean clustering
    std::vector<std::vector<PointXYZI>> cluster_points(const PointCloud& cloud,
                                                         double cluster_tolerance);

    // Compute 3D bounding box for a cluster
    std::vector<Point3D> compute_bounding_box(const std::vector<PointXYZI>& cluster);

    // Simple shape-based object classification
    std::string classify_shape(const std::vector<PointXYZI>& cluster,
                                const std::vector<Point3D>& bbox,
                                double& confidence);

    Config config_;
    int32_t instance_counter_ = 0;
    std::function<void(const ObjectLabel&)> detection_callback_;
};

} // namespace qoosvc::spatial
