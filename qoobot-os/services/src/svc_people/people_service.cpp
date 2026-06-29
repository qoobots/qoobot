#include "qoosvc/people/people_service.h"
#include <algorithm>
#include <chrono>
#include <cmath>
#include <mutex>

namespace qoosvc::people {

struct PeopleService::Impl {
    std::vector<FaceInfo> face_db;
    FollowStatus follow_status;
    FollowConfig follow_config;
    SearchStatus search_status;
    SearchConfig search_config;
    std::function<void(const FollowStatus&)> follow_callback;
    std::function<void(const SearchStatus&)> search_callback;
    std::function<void(const std::string&, const Pose3D&)> found_callback;
    mutable std::mutex mutex;
};

PeopleService::PeopleService() : ServiceBase("people_service"), impl_(std::make_unique<Impl>()) {
    social_config_.personal_space_radius = 0.5;
    social_config_.social_space_radius = 1.2;
    social_config_.approach_speed_factor = 0.5;
    social_config_.eye_contact_enabled = true;
}

PeopleService::~PeopleService() { stop(); }

// ========================================================================
// Face Recognition
// ========================================================================

Result<FaceRecognitionResult> PeopleService::recognize_face(
    const std::vector<float>& face_embedding) {

    std::lock_guard<std::mutex> lock(impl_->mutex);

    FaceRecognitionResult result;

    if (impl_->face_db.empty()) {
        result.recognized = false;
        result.is_stranger = true;
        return result;
    }

    // Find best match by cosine similarity
    double best_similarity = 0.6;  // Minimum threshold
    const FaceInfo* best_match = nullptr;

    for (const auto& person : impl_->face_db) {
        if (person.face_embedding.size() != face_embedding.size()) continue;

        double dot = 0.0, norm_a = 0.0, norm_b = 0.0;
        for (size_t i = 0; i < face_embedding.size(); ++i) {
            dot += person.face_embedding[i] * face_embedding[i];
            norm_a += person.face_embedding[i] * person.face_embedding[i];
            norm_b += face_embedding[i] * face_embedding[i];
        }

        double similarity = dot / (std::sqrt(norm_a) * std::sqrt(norm_b) + 1e-10);

        if (similarity > best_similarity) {
            best_similarity = similarity;
            best_match = &person;
        }
    }

    if (best_match) {
        result.recognized = true;
        result.person_id = best_match->person_id;
        result.name = best_match->name;
        result.confidence = static_cast<float>(best_similarity);
        result.is_stranger = false;
    } else {
        result.is_stranger = true;
    }

    return result;
}

Result<std::string> PeopleService::enroll_person(
    const std::string& name, const std::vector<float>& face_embedding,
    const std::string& relationship) {

    std::lock_guard<std::mutex> lock(impl_->mutex);

    FaceInfo person;
    person.person_id = "person_" + std::to_string(impl_->face_db.size() + 1);
    person.name = name;
    person.face_embedding = face_embedding;
    person.relationship = relationship;
    person.enrolled_at_us = std::chrono::duration_cast<std::chrono::microseconds>(
        std::chrono::system_clock::now().time_since_epoch()).count();
    person.last_seen_us = person.enrolled_at_us;

    impl_->face_db.push_back(person);
    return person.person_id;
}

Result<void> PeopleService::remove_person(const std::string& person_id) {
    std::lock_guard<std::mutex> lock(impl_->mutex);

    auto it = std::find_if(impl_->face_db.begin(), impl_->face_db.end(),
        [&](const FaceInfo& f) { return f.person_id == person_id; });

    if (it == impl_->face_db.end()) {
        return Result<void>::err(ErrorCode::PEOPLE_FACE_NOT_RECOGNIZED, "Person not found");
    }

    impl_->face_db.erase(it);
    return Result<void>::ok();
}

Result<void> PeopleService::update_person_name(const std::string& person_id,
                                                 const std::string& new_name) {
    std::lock_guard<std::mutex> lock(impl_->mutex);

    auto it = std::find_if(impl_->face_db.begin(), impl_->face_db.end(),
        [&](const FaceInfo& f) { return f.person_id == person_id; });

    if (it == impl_->face_db.end()) {
        return Result<void>::err(ErrorCode::PEOPLE_FACE_NOT_RECOGNIZED, "Person not found");
    }

    it->name = new_name;
    return Result<void>::ok();
}

std::vector<FaceInfo> PeopleService::get_enrolled_persons() const {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    return impl_->face_db;
}

Result<FaceInfo> PeopleService::get_person_info(const std::string& person_id) const {
    std::lock_guard<std::mutex> lock(impl_->mutex);

    auto it = std::find_if(impl_->face_db.begin(), impl_->face_db.end(),
        [&](const FaceInfo& f) { return f.person_id == person_id; });

    if (it == impl_->face_db.end()) {
        return Result<FaceInfo>::err(ErrorCode::PEOPLE_FACE_NOT_RECOGNIZED, "Person not found");
    }

    return *it;
}

// ========================================================================
// Person Following
// ========================================================================

Result<void> PeopleService::start_following(const std::string& person_id,
                                              const FollowConfig& config) {
    std::lock_guard<std::mutex> lock(impl_->mutex);

    follow_active_ = true;
    impl_->follow_config = config;
    impl_->follow_status.is_following = true;
    impl_->follow_status.target_person_id = person_id;
    impl_->follow_status.target_visible = true;
    impl_->follow_status.distance_to_target = config.target_distance;

    return Result<void>::ok();
}

Result<void> PeopleService::stop_following() {
    std::lock_guard<std::mutex> lock(impl_->mutex);

    follow_active_ = false;
    impl_->follow_status.is_following = false;

    if (impl_->follow_callback) {
        impl_->follow_callback(impl_->follow_status);
    }

    return Result<void>::ok();
}

Result<void> PeopleService::update_target_pose(const Pose3D& pose) {
    std::lock_guard<std::mutex> lock(impl_->mutex);

    if (!follow_active_) {
        return Result<void>::err(ErrorCode::PEOPLE_TRACKING_LOST, "Not following");
    }

    impl_->follow_status.target_pose = pose;

    // Compute distance and path deviation
    // In production: get robot's current pose and compute
    impl_->follow_status.distance_to_target = 1.5;  // placeholder

    // Check if too close
    if (is_too_close(pose)) {
        impl_->follow_status.target_visible = true;
        // Robot should slow down or stop
    }

    if (impl_->follow_callback) {
        impl_->follow_callback(impl_->follow_status);
    }

    return Result<void>::ok();
}

FollowStatus PeopleService::get_follow_status() const {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    return impl_->follow_status;
}

void PeopleService::on_follow_update(std::function<void(const FollowStatus&)> callback) {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    impl_->follow_callback = std::move(callback);
}

// ========================================================================
// Person Search
// ========================================================================

Result<void> PeopleService::start_search(const SearchConfig& config) {
    std::lock_guard<std::mutex> lock(impl_->mutex);

    search_active_ = true;
    impl_->search_config = config;
    impl_->search_status.search_active = true;
    impl_->search_status.total_rooms = static_cast<int32_t>(config.search_rooms.size());
    impl_->search_status.rooms_searched = 0;
    impl_->search_status.person_found = false;
    impl_->search_status.search_progress = 0.0;

    if (!config.search_rooms.empty()) {
        impl_->search_status.current_room = config.search_rooms[0];
    }

    return Result<void>::ok();
}

Result<void> PeopleService::stop_search() {
    std::lock_guard<std::mutex> lock(impl_->mutex);

    search_active_ = false;
    impl_->search_status.search_active = false;

    return Result<void>::ok();
}

Result<void> PeopleService::continue_search() {
    std::lock_guard<std::mutex> lock(impl_->mutex);

    if (!search_active_) {
        return Result<void>::err(ErrorCode::INVALID_ARGUMENT, "No active search to continue");
    }

    // Move to next room
    impl_->search_status.rooms_searched++;
    impl_->search_status.search_progress =
        static_cast<double>(impl_->search_status.rooms_searched) /
        impl_->search_status.total_rooms;

    if (impl_->search_status.rooms_searched < impl_->search_status.total_rooms) {
        impl_->search_status.current_room =
            impl_->search_config.search_rooms[impl_->search_status.rooms_searched];
    } else {
        // All rooms searched
        search_active_ = false;
        impl_->search_status.search_active = false;
    }

    if (impl_->search_callback) {
        impl_->search_callback(impl_->search_status);
    }

    return Result<void>::ok();
}

SearchStatus PeopleService::get_search_status() const {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    return impl_->search_status;
}

void PeopleService::on_search_update(std::function<void(const SearchStatus&)> callback) {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    impl_->search_callback = std::move(callback);
}

void PeopleService::on_person_found(
    std::function<void(const std::string&, const Pose3D&)> callback) {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    impl_->found_callback = std::move(callback);
}

// ========================================================================
// Social Distance
// ========================================================================

Result<void> PeopleService::configure_social_distance(const SocialDistanceConfig& config) {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    social_config_ = config;
    return Result<void>::ok();
}

bool PeopleService::is_too_close(const Pose3D& person_pose) const {
    // In production: compare with robot's current pose
    return false;  // placeholder
}

double PeopleService::recommended_distance(const std::string& relationship) const {
    if (relationship == "family") return social_config_.personal_space_radius;
    if (relationship == "colleague") return social_config_.social_space_radius;
    return social_config_.social_space_radius * 1.5;  // Stranger
}

// ========================================================================
// Service Lifecycle
// ========================================================================

Result<void> PeopleService::on_initialize() { return Result<void>::ok(); }

Result<void> PeopleService::on_stop() {
    if (follow_active_) stop_following();
    if (search_active_) stop_search();
    return Result<void>::ok();
}

} // namespace qoosvc::people
