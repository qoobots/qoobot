// action_nodes/detect_object_node.h — Object detection via camera/perception
#pragma once

#include "brain_core/core_types.h"
#include <string>
#include <vector>
#include <functional>

namespace brain_core {

/// Detection result from the perception pipeline.
struct DetectionResult {
    std::string label;
    double      confidence{0.0};
    double      x{0.0}, y{0.0}, z{0.0};  // world coordinates
    double      width{0.0}, height{0.0}, depth{0.0};  // bbox size
};

class DetectObjectNode {
public:
    using DetectionCallback = std::function<void(const std::vector<DetectionResult>&)>;

    DetectObjectNode();

    /// Set the object label to look for (e.g., "cup", "bottle").
    void setTargetLabel(const std::string& label);

    /// Set minimum confidence threshold (default: 0.6).
    void setConfidenceThreshold(double thresh);

    /// Execute detection. Returns SUCCESS if target found,
    /// FAILURE if no detection above threshold.
    BTNodeStatus execute();

    /// Get the latest detection results.
    std::vector<DetectionResult> results() const;

    /// Register a callback for detection results.
    void onDetected(DetectionCallback cb);

    /// Cancel ongoing detection.
    void cancel();

private:
    std::string _target_label;
    double      _confidence_threshold{0.6};
    std::vector<DetectionResult> _results;
    DetectionCallback _callback;
    bool _active{false};
};

} // namespace brain_core
