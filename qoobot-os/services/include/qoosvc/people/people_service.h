#pragma once

#include "people_types.h"
#include "../common/result.h"
#include "../common/service_base.h"
#include <functional>
#include <memory>
#include <string>
#include <vector>

namespace qoosvc::people {

class PeopleService : public ServiceBase {
public:
    PeopleService();
    ~PeopleService() override;

    // ========================================================================
    // Face Recognition
    // ========================================================================
    Result<FaceRecognitionResult> recognize_face(const std::vector<float>& face_embedding);
    Result<std::string> enroll_person(const std::string& name,
                                       const std::vector<float>& face_embedding,
                                       const std::string& relationship = "family");
    Result<void> remove_person(const std::string& person_id);
    Result<void> update_person_name(const std::string& person_id, const std::string& new_name);
    std::vector<FaceInfo> get_enrolled_persons() const;
    Result<FaceInfo> get_person_info(const std::string& person_id) const;

    // ========================================================================
    // Person Following
    // ========================================================================
    Result<void> start_following(const std::string& person_id, const FollowConfig& config = {});
    Result<void> stop_following();
    Result<void> update_target_pose(const Pose3D& pose);
    FollowStatus get_follow_status() const;
    void on_follow_update(std::function<void(const FollowStatus&)> callback);

    // ========================================================================
    // Person Search
    // ========================================================================
    Result<void> start_search(const SearchConfig& config);
    Result<void> stop_search();
    Result<void> continue_search();  // Resume after interruption
    SearchStatus get_search_status() const;
    void on_search_update(std::function<void(const SearchStatus&)> callback);
    void on_person_found(std::function<void(const std::string&, const Pose3D&)> callback);

    // ========================================================================
    // Social Distance
    // ========================================================================
    Result<void> configure_social_distance(const SocialDistanceConfig& config);
    SocialDistanceConfig social_distance_config() const { return social_config_; }
    bool is_too_close(const Pose3D& person_pose) const;
    double recommended_distance(const std::string& relationship) const;

    // ========================================================================
    // Service Lifecycle
    // ========================================================================
    bool is_following() const { return follow_active_; }
    bool is_searching() const { return search_active_; }

protected:
    Result<void> on_initialize() override;
    Result<void> on_stop() override;

private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
    SocialDistanceConfig social_config_;
    bool follow_active_ = false;
    bool search_active_ = false;
};

} // namespace qoosvc::people
