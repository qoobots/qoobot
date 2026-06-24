// action_nodes/detect_object_node.cpp
#include "brain_core/behavior_engine/action_nodes/detect_object_node.h"
#include <iostream>

namespace brain_core {

DetectObjectNode::DetectObjectNode()
{
    std::cout << "[DetectObjectNode] Initialized." << std::endl;
}

void DetectObjectNode::setTargetLabel(const std::string& label)
{
    _target_label = label;
    std::cout << "[DetectObjectNode] Looking for: " << label << std::endl;
}

void DetectObjectNode::setConfidenceThreshold(double thresh)
{
    _confidence_threshold = thresh;
}

BTNodeStatus DetectObjectNode::execute()
{
    if (_target_label.empty()) {
        std::cerr << "[DetectObjectNode] No target label set!" << std::endl;
        return BTNodeStatus::FAILURE;
    }

    _active = true;

    // Stub: simulate detection — mock a detection of the target
    _results.clear();
    DetectionResult det;
    det.label = _target_label;
    det.confidence = 0.88;
    det.x = 0.4; det.y = 0.3; det.z = 0.15;
    det.width = 0.08; det.height = 0.08; det.depth = 0.12;
    _results.push_back(det);

    std::cout << "[DetectObjectNode] Detected " << _target_label
              << " (conf=" << det.confidence << ")" << std::endl;

    if (_callback) {
        _callback(_results);
    }

    _active = false;

    if (det.confidence >= _confidence_threshold) {
        return BTNodeStatus::SUCCESS;
    }
    return BTNodeStatus::FAILURE;
}

std::vector<DetectionResult> DetectObjectNode::results() const
{
    return _results;
}

void DetectObjectNode::onDetected(DetectionCallback cb)
{
    _callback = std::move(cb);
}

void DetectObjectNode::cancel()
{
    _active = false;
}

} // namespace brain_core
