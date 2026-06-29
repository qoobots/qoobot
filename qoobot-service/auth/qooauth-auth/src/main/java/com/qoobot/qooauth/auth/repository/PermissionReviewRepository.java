package com.qoobot.qooauth.auth.repository;

import com.qoobot.qooauth.auth.entity.PermissionReview;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface PermissionReviewRepository extends JpaRepository<PermissionReview, String> {

    List<PermissionReview> findBySkillId(String skillId);

    List<PermissionReview> findByDeveloperUserId(String developerUserId);

    List<PermissionReview> findByState(String state);

    List<PermissionReview> findByReviewerId(String reviewerId);

    @Query("SELECT r FROM PermissionReview r WHERE r.state = 'PENDING' ORDER BY r.submittedAt ASC")
    List<PermissionReview> findPendingReviews();

    @Query("SELECT r FROM PermissionReview r WHERE r.skillId = :skillId ORDER BY r.submittedAt DESC")
    List<PermissionReview> findHistoryBySkill(@Param("skillId") String skillId);
}
