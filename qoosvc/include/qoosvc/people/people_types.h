#pragma once

#include <cstdint>
#include <string>
#include <vector>

namespace qoosvc::people {

struct Pose3D {
    double x = 0, y = 0, z = 0;
    double roll = 0, pitch = 0, yaw = 0;
    std::string frame_id = "map";
    double distance_to(const Pose3D& other) const {
        return std::sqrt((x-other.x)*(x-other.x)+(y-other.y)*(y-other.y));
    }
};

struct FaceInfo {
    std::string person_id;
    std::string name;
    std::vector<float> face_embedding;  // 512-dim embedding
    std::string image_path;
    int64_t enrolled_at_us = 0;
    int64_t last_seen_us = 0;
    std::string relationship;           // "family", "colleague", "visitor"
    int32_t interaction_count = 0;
};

struct FaceRecognitionResult {
    bool recognized = false;
    std::string person_id;
    std::string name;
    float confidence = 0.0f;
    bool is_stranger = true;
    Pose3D person_pose;
    float distance_m = 0.0f;
};

struct FollowConfig {
    double target_distance = 1.5;    // meters behind person
    double max_speed = 1.0;         // m/s
    double lookahead_time = 0.5;    // seconds
    bool maintain_line_of_sight = true;
};

struct FollowStatus {
    bool is_following = false;
    std::string target_person_id;
    Pose3D target_pose;
    double distance_to_target = 0.0;
    bool target_visible = true;
    double path_deviation = 0.0;     // meters off ideal path
};

struct SearchConfig {
    std::string person_name;
    std::string person_id;
    std::vector<std::string> search_rooms;  // Ordered list of rooms to search
    double room_search_duration_s = 30.0;
    bool use_camera = true;
    bool use_voice_call = true;      // Call person's name
    bool notify_on_found = true;
};

struct SearchStatus {
    bool search_active = false;
    std::string current_room;
    int32_t rooms_searched = 0;
    int32_t total_rooms = 0;
    bool person_found = false;
    Pose3D found_pose;
    double search_progress = 0.0;    // [0, 1]
};

struct SocialDistanceConfig {
    double personal_space_radius = 0.5;    // meters
    double social_space_radius = 1.2;
    double approach_speed_factor = 0.5;     // Slow down when close
    bool eye_contact_enabled = true;
    double eye_contact_duration_s = 2.0;
    double greeting_distance = 1.5;         // Distance to initiate greeting
};

} // namespace qoosvc::people
