package com.qoobot.qooauth.auth.entity;

import jakarta.persistence.*;
import java.time.Instant;

@Entity
@Table(name = "family_members", indexes = {
    @Index(name = "idx_fm_family", columnList = "familyId"),
    @Index(name = "idx_fm_user", columnList = "userId")
}, uniqueConstraints = {
    @UniqueConstraint(name = "uk_fm_family_user", columnNames = {"familyId", "userId"})
})
public class FamilyMember {

    @Id
    @Column(name = "member_id", length = 64)
    private String memberId;

    @Column(name = "family_id", nullable = false, length = 64)
    private String familyId;

    @Column(name = "user_id", nullable = false, length = 64)
    private String userId;

    /**
     * Role: ORGANIZER, ADULT, CHILD
     */
    @Column(name = "role", nullable = false, length = 16)
    private String role;

    @Column(name = "state", nullable = false, length = 16)
    private String state = "ACTIVE";

    /**
     * Parental control settings for child members as JSON:
     * { "screen_time_limit_minutes": 120, "content_filter": "AGE_10",
     *   "purchase_approval_required": true, "allowed_apps": [...],
     *   "quiet_hours": {"start": "21:00", "end": "07:00"} }
     */
    @Column(name = "parental_controls", columnDefinition = "TEXT")
    private String parentalControls;

    @Column(name = "joined_at", nullable = false)
    private Instant joinedAt;

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt;

    // Getters and Setters
    public String getMemberId() { return memberId; }
    public void setMemberId(String memberId) { this.memberId = memberId; }
    public String getFamilyId() { return familyId; }
    public void setFamilyId(String familyId) { this.familyId = familyId; }
    public String getUserId() { return userId; }
    public void setUserId(String userId) { this.userId = userId; }
    public String getRole() { return role; }
    public void setRole(String role) { this.role = role; }
    public String getState() { return state; }
    public void setState(String state) { this.state = state; }
    public String getParentalControls() { return parentalControls; }
    public void setParentalControls(String parentalControls) { this.parentalControls = parentalControls; }
    public Instant getJoinedAt() { return joinedAt; }
    public void setJoinedAt(Instant joinedAt) { this.joinedAt = joinedAt; }
    public Instant getUpdatedAt() { return updatedAt; }
    public void setUpdatedAt(Instant updatedAt) { this.updatedAt = updatedAt; }
}
