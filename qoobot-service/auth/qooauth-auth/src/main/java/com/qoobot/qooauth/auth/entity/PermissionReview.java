package com.qoobot.qooauth.auth.entity;

import jakarta.persistence.*;
import java.time.Instant;

/**
 * Permission Review — sensitive permission audit for developer submissions.
 *
 * When a skill requests sensitive permissions (camera, location, health data, etc.),
 * it triggers a review process. This entity tracks the review lifecycle.
 */
@Entity
@Table(name = "permission_reviews", indexes = {
    @Index(name = "idx_pr_skill", columnList = "skillId"),
    @Index(name = "idx_pr_state", columnList = "state"),
    @Index(name = "idx_pr_reviewer", columnList = "reviewerId")
})
public class PermissionReview {

    @Id
    @Column(name = "review_id", length = 64)
    private String reviewId;

    @Column(name = "skill_id", nullable = false, length = 128)
    private String skillId;

    @Column(name = "skill_version", nullable = false, length = 32)
    private String skillVersion;

    @Column(name = "developer_user_id", nullable = false, length = 64)
    private String developerUserId;

    /**
     * Requested permissions as JSON array:
     * ["camera", "microphone", "location", "health_data", "contacts"]
     */
    @Column(name = "requested_permissions", nullable = false, columnDefinition = "TEXT")
    private String requestedPermissions;

    /**
     * Justification provided by developer for each permission.
     */
    @Column(name = "justification", columnDefinition = "TEXT")
    private String justification;

    /**
     * Review state: PENDING, IN_REVIEW, APPROVED, DENIED, CHANGES_REQUESTED
     */
    @Column(name = "state", nullable = false, length = 32)
    private String state = "PENDING";

    /**
     * Reviewer's decision as JSON:
     * { "approved_permissions": ["camera"], "denied_permissions": ["location"],
     *   "conditions": "Camera access limited to object recognition only" }
     */
    @Column(name = "decision", columnDefinition = "TEXT")
    private String decision;

    @Column(name = "reviewer_id", length = 64)
    private String reviewerId;

    @Column(name = "reviewer_notes", columnDefinition = "TEXT")
    private String reviewerNotes;

    /**
     * Privacy compliance checks passed/failed as JSON:
     * { "data_minimization": "pass", "purpose_limitation": "pass",
     *   "user_consent_required": true, "gdpr_article_6_basis": "consent" }
     */
    @Column(name = "compliance_checks", columnDefinition = "TEXT")
    private String complianceChecks;

    @Column(name = "submitted_at", nullable = false)
    private Instant submittedAt;

    @Column(name = "reviewed_at")
    private Instant reviewedAt;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt;

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt;

    // --- Getters and Setters ---

    public String getReviewId() { return reviewId; }
    public void setReviewId(String reviewId) { this.reviewId = reviewId; }

    public String getSkillId() { return skillId; }
    public void setSkillId(String skillId) { this.skillId = skillId; }

    public String getSkillVersion() { return skillVersion; }
    public void setSkillVersion(String skillVersion) { this.skillVersion = skillVersion; }

    public String getDeveloperUserId() { return developerUserId; }
    public void setDeveloperUserId(String developerUserId) { this.developerUserId = developerUserId; }

    public String getRequestedPermissions() { return requestedPermissions; }
    public void setRequestedPermissions(String requestedPermissions) { this.requestedPermissions = requestedPermissions; }

    public String getJustification() { return justification; }
    public void setJustification(String justification) { this.justification = justification; }

    public String getState() { return state; }
    public void setState(String state) { this.state = state; }

    public String getDecision() { return decision; }
    public void setDecision(String decision) { this.decision = decision; }

    public String getReviewerId() { return reviewerId; }
    public void setReviewerId(String reviewerId) { this.reviewerId = reviewerId; }

    public String getReviewerNotes() { return reviewerNotes; }
    public void setReviewerNotes(String reviewerNotes) { this.reviewerNotes = reviewerNotes; }

    public String getComplianceChecks() { return complianceChecks; }
    public void setComplianceChecks(String complianceChecks) { this.complianceChecks = complianceChecks; }

    public Instant getSubmittedAt() { return submittedAt; }
    public void setSubmittedAt(Instant submittedAt) { this.submittedAt = submittedAt; }

    public Instant getReviewedAt() { return reviewedAt; }
    public void setReviewedAt(Instant reviewedAt) { this.reviewedAt = reviewedAt; }

    public Instant getCreatedAt() { return createdAt; }
    public void setCreatedAt(Instant createdAt) { this.createdAt = createdAt; }

    public Instant getUpdatedAt() { return updatedAt; }
    public void setUpdatedAt(Instant updatedAt) { this.updatedAt = updatedAt; }
}
