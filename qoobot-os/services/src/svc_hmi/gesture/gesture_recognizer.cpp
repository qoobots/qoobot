#include "gesture_recognizer.h"
#include <algorithm>
#include <cmath>

namespace qoosvc::hmi {

// MediaPipe hand landmark indices
static constexpr int WRIST = 0;
static constexpr int THUMB_CMC = 1;
static constexpr int THUMB_MCP = 2;
static constexpr int THUMB_IP = 3;
static constexpr int THUMB_TIP = 4;
static constexpr int INDEX_MCP = 5;
static constexpr int INDEX_PIP = 6;
static constexpr int INDEX_DIP = 7;
static constexpr int INDEX_TIP = 8;
static constexpr int MIDDLE_MCP = 9;
static constexpr int MIDDLE_PIP = 10;
static constexpr int MIDDLE_DIP = 11;
static constexpr int MIDDLE_TIP = 12;
static constexpr int RING_MCP = 13;
static constexpr int RING_PIP = 14;
static constexpr int RING_DIP = 15;
static constexpr int RING_TIP = 16;
static constexpr int PINKY_MCP = 17;
static constexpr int PINKY_PIP = 18;
static constexpr int PINKY_DIP = 19;
static constexpr int PINKY_TIP = 20;

GestureRecognizer::GestureRecognizer(const Config& config)
    : config_(config) {
}

GestureRecognizer::~GestureRecognizer() = default;

GestureResult GestureRecognizer::recognize(const std::vector<Point2D>& landmarks,
                                             bool is_left_hand) {
    GestureResult result;
    result.is_left_hand = is_left_hand;

    if (landmarks.size() < 21) {
        result.type = GestureType::NONE;
        return result;
    }

    auto center = hand_center(landmarks);
    result.hand_x = center.x;
    result.hand_y = center.y;
    result.landmarks = landmarks;

    // Determine which fingers are extended
    bool thumb_ext = is_finger_extended(landmarks, THUMB_TIP, THUMB_IP, THUMB_MCP, WRIST);
    bool index_ext = is_finger_extended(landmarks, INDEX_TIP, INDEX_PIP, INDEX_MCP, WRIST);
    bool middle_ext = is_finger_extended(landmarks, MIDDLE_TIP, MIDDLE_PIP, MIDDLE_MCP, WRIST);
    bool ring_ext = is_finger_extended(landmarks, RING_TIP, RING_PIP, RING_MCP, WRIST);
    bool pinky_ext = is_finger_extended(landmarks, PINKY_TIP, PINKY_PIP, PINKY_MCP, WRIST);

    // Gesture classification
    int extended_count = thumb_ext + index_ext + middle_ext + ring_ext + pinky_ext;

    // FIST — all fingers closed
    if (extended_count == 0) {
        result.type = GestureType::FIST;
        result.confidence = 0.9f;
        return result;
    }

    // OPEN_PALM — all fingers extended
    if (extended_count == 5) {
        result.type = GestureType::OPEN_PALM;
        result.confidence = 0.85f;
        return result;
    }

    // THUMBS_UP — only thumb extended upward
    if (thumb_ext && extended_count == 1) {
        float thumb_y = landmarks[THUMB_TIP].y;
        float wrist_y = landmarks[WRIST].y;
        if (thumb_y < wrist_y) {  // Thumb pointing up
            result.type = GestureType::THUMBS_UP;
            result.confidence = 0.85f;
        } else {
            result.type = GestureType::THUMBS_DOWN;
            result.confidence = 0.8f;
        }
        return result;
    }

    // POINT — only index extended
    if (index_ext && !middle_ext && !ring_ext && !pinky_ext) {
        // Determine pointing direction
        float dx = landmarks[INDEX_TIP].x - landmarks[INDEX_MCP].x;
        float dy = landmarks[INDEX_TIP].y - landmarks[INDEX_MCP].y;

        if (std::abs(dx) > std::abs(dy)) {
            result.type = dx > 0 ? GestureType::POINT_RIGHT : GestureType::POINT_LEFT;
        } else {
            result.type = dy < 0 ? GestureType::POINT_UP : GestureType::POINT_DOWN;
        }
        result.confidence = 0.8f;
        return result;
    }

    // PEACE — index + middle extended, others closed
    if (index_ext && middle_ext && !ring_ext && !pinky_ext) {
        result.type = GestureType::PEACE;
        result.confidence = 0.85f;
        return result;
    }

    // OK — thumb and index form a circle
    float thumb_index_dist = landmark_distance(landmarks, THUMB_TIP, INDEX_TIP);
    if (thumb_index_dist < config_.pinch_threshold &&
        middle_ext && ring_ext && pinky_ext) {
        result.type = GestureType::OK;
        result.confidence = 0.8f;
        return result;
    }

    // PINCH — thumb and index touching
    if (thumb_index_dist < config_.pinch_threshold) {
        result.type = GestureType::PINCH;
        result.confidence = 0.75f;
        return result;
    }

    // COME_HERE — index curled repeatedly (simplified: index extended, others partial)
    if (index_ext && thumb_ext && !middle_ext && !ring_ext && !pinky_ext) {
        result.type = GestureType::COME_HERE;
        result.confidence = 0.6f;
        return result;
    }

    // STOP — all fingers extended upward (palm facing camera)
    if (extended_count >= 4) {
        float avg_tip_y = 0;
        for (int tip : {INDEX_TIP, MIDDLE_TIP, RING_TIP, PINKY_TIP}) {
            avg_tip_y += landmarks[tip].y;
        }
        avg_tip_y /= 4;
        if (avg_tip_y < landmarks[WRIST].y) {
            result.type = GestureType::STOP;
            result.confidence = 0.7f;
            return result;
        }
    }

    // WAVE — side-to-side motion detected over multiple frames
    // Simplified: all fingers extended with spread
    if (extended_count >= 3) {
        result.type = GestureType::WAVE;
        result.confidence = 0.5f;
        return result;
    }

    result.type = GestureType::UNKNOWN;
    result.confidence = 0.2f;
    return result;
}

bool GestureRecognizer::is_finger_extended(const std::vector<Point2D>& landmarks,
                                             int tip_idx, int pip_idx,
                                             int mcp_idx, int wrist_idx) {
    float tip_to_wrist = landmark_distance(landmarks, tip_idx, wrist_idx);
    float pip_to_wrist = landmark_distance(landmarks, pip_idx, wrist_idx);
    return tip_to_wrist > pip_to_wrist * 1.1f;
}

float GestureRecognizer::landmark_distance(const std::vector<Point2D>& landmarks,
                                             int i, int j) {
    float dx = landmarks[i].x - landmarks[j].x;
    float dy = landmarks[i].y - landmarks[j].y;
    return std::sqrt(dx * dx + dy * dy);
}

Point2D GestureRecognizer::hand_center(const std::vector<Point2D>& landmarks) {
    float cx = 0, cy = 0;
    for (const auto& lm : landmarks) {
        cx += lm.x;
        cy += lm.y;
    }
    return {cx / landmarks.size(), cy / landmarks.size()};
}

} // namespace qoosvc::hmi
