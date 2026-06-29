package com.qoobot.qooauth.auth.entity;

import jakarta.persistence.*;
import java.time.Instant;

@Entity
@Table(name = "organization_profiles", indexes = {
    @Index(name = "idx_op_admin", columnList = "adminUserId"),
    @Index(name = "idx_op_state", columnList = "state")
})
public class OrganizationProfile {

    @Id
    @Column(name = "org_id", length = 64)
    private String orgId;

    @Column(name = "name", nullable = false, length = 256)
    private String name;

    @Column(name = "admin_user_id", nullable = false, length = 64)
    private String adminUserId;

    @Column(name = "state", nullable = false, length = 16)
    private String state = "ACTIVE";

    /**
     * MDM configuration as JSON:
     * { "enforce_encryption": true, "min_os_version": "1.0.0",
     *   "allowed_wifi_networks": [...], "vpn_config": {...},
     *   "device_policies": {...}, "compliance_policies": {...} }
     */
    @Column(name = "mdm_config", columnDefinition = "TEXT")
    private String mdmConfig;

    @Column(name = "max_devices")
    private Integer maxDevices = 100;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt;

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt;

    // Getters and Setters
    public String getOrgId() { return orgId; }
    public void setOrgId(String orgId) { this.orgId = orgId; }
    public String getName() { return name; }
    public void setName(String name) { this.name = name; }
    public String getAdminUserId() { return adminUserId; }
    public void setAdminUserId(String adminUserId) { this.adminUserId = adminUserId; }
    public String getState() { return state; }
    public void setState(String state) { this.state = state; }
    public String getMdmConfig() { return mdmConfig; }
    public void setMdmConfig(String mdmConfig) { this.mdmConfig = mdmConfig; }
    public Integer getMaxDevices() { return maxDevices; }
    public void setMaxDevices(Integer maxDevices) { this.maxDevices = maxDevices; }
    public Instant getCreatedAt() { return createdAt; }
    public void setCreatedAt(Instant createdAt) { this.createdAt = createdAt; }
    public Instant getUpdatedAt() { return updatedAt; }
    public void setUpdatedAt(Instant updatedAt) { this.updatedAt = updatedAt; }
}
