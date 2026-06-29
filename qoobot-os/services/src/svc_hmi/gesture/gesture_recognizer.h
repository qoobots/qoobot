#pragma once

#include "qoosvc/hmi/hmi_types.h"
#include <vector>

namespace qoosvc::hmi {

/**
 * GestureRecognizer — Recognizes hand gestures from 21 hand landmarks.
 *
 * Uses geometric heuristics on MediaPipe-style hand landmarks
 * to classify gestures. In production, this would use a trained
 * classifier model via qoocore ONNX inference.
 */
class GestureRecognizer {
public:
    struct Config {
        float min_confidence = 0.5f;
        float pinch_threshold = 0.05f;   // Thumb-index distance for pinch
        float point_threshold = 0.1f;    // Finger extension ratio for pointing
    };

    explicit GestureRecognizer(const Config& config);
    ~GestureRecognizer();

    /**
     * Recognize gesture from 21 hand landmarks.
     * Landmarks follow MediaPipe hand landmark model order:
     *   0: wrist, 1-4: thumb, 5-8: index, 9-12: middle,
     *   13-16: ring, 17-20: pinky
     */
    GestureResult recognize(const std::vector<Point2D>& landmarks,
                             bool is_left_hand);

private:
    // Check if a finger is extended (tip is further from wrist than PIP joint)
    bool is_finger_extended(const std::vector<Point2D>& landmarks,
                            int tip_idx, int pip_idx, int mcp_idx, int wrist_idx);

    // Distance between two landmarks
    float landmark_distance(const std::vector<Point2D>& landmarks,
                            int i, int j);

    // Compute hand centroid
    Point2D hand_center(const std::vector<Point2D>& landmarks);

    Config config_;
};

} // namespace qoosvc::hmi
