package com.qoobot.qooauth.auth.entity;

import jakarta.persistence.*;
import java.time.Instant;

@Entity
@Table(name = "family_groups", indexes = {
    @Index(name = "idx_fg_organizer", columnList = "organizerUserId"),
    @Index(name = "idx_fg_state", columnList = "state")
})
public class FamilyGroup {

    @Id
    @Column(name = "family_id", length = 64)
    private String familyId;

    @Column(name = "name", nullable = false, length = 128)
    private String name;

    @Column(name = "organizer_user_id", nullable = false, length = 64)
    private String organizerUserId;

    @Column(name = "state", nullable = false, length = 16)
    private String state = "ACTIVE";

    @Column(name = "max_members")
    private Integer maxMembers = 6;

    /**
     * Family sharing settings as JSON:
     * { "share_purchases": true, "share_subscriptions": true,
     *   "share_location": true, "share_device_access": false }
     */
    @Column(name = "sharing_settings", columnDefinition = "TEXT")
    private String sharingSettings;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt;

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt;

    // Getters and Setters
    public String getFamilyId() { return familyId; }
    public void setFamilyId(String familyId) { this.familyId = familyId; }
    public String getName() { return name; }
    public void setName(String name) { this.name = name; }
    public String getOrganizerUserId() { return organizerUserId; }
    public void setOrganizerUserId(String organizerUserId) { this.organizerUserId = organizerUserId; }
    public String getState() { return state; }
    public void setState(String state) { this.state = state; }
    public Integer getMaxMembers() { return maxMembers; }
    public void setMaxMembers(Integer maxMembers) { this.maxMembers = maxMembers; }
    public String getSharingSettings() { return sharingSettings; }
    public void setSharingSettings(String sharingSettings) { this.sharingSettings = sharingSettings; }
    public Instant getCreatedAt() { return createdAt; }
    public void setCreatedAt(Instant createdAt) { this.createdAt = createdAt; }
    public Instant getUpdatedAt() { return updatedAt; }
    public void setUpdatedAt(Instant updatedAt) { this.updatedAt = updatedAt; }
}
