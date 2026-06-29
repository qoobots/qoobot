package com.qoobot.qooauth.device.entity;

import com.qoobot.qooauth.common.enums.DeviceState;
import jakarta.persistence.*;
import lombok.*;

import java.time.OffsetDateTime;

/**
 * JPA entity mapping to the {@code devices} table.
 * <p>
 * Represents a registered device with its X.509 identity certificate,
 * binding relationship to a user, device fingerprints, and status.
 */
@Entity
@Table(name = "devices")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
@ToString(onlyExplicitlyIncluded = true)
public class Device {

    @Id
    @Column(name = "device_id", length = 32, nullable = false, updatable = false)
    @ToString.Include
    private String deviceId;

    @Column(name = "device_serial", length = 64, nullable = false, unique = true)
    @ToString.Include
    private String deviceSerial;

    @Column(name = "hardware_model", length = 64, nullable = false)
    private String hardwareModel;

    @Column(name = "hardware_version", length = 32)
    private String hardwareVersion;

    @Column(name = "firmware_version", length = 32)
    private String firmwareVersion;

    // --- X.509 certificate ---

    @Column(name = "certificate_sn", length = 64, nullable = false, unique = true)
    private String certificateSn;

    @Column(name = "certificate_pem", columnDefinition = "TEXT")
    private String certificatePem;

    @Column(name = "certificate_expires_at", nullable = false)
    private OffsetDateTime certificateExpiresAt;

    // --- Binding ---

    @Column(name = "bound_user_id", length = 32)
    private String boundUserId;

    @Column(name = "device_name", length = 64)
    private String deviceName;

    @Column(name = "bound_at")
    private OffsetDateTime boundAt;

    // --- State ---

    @Enumerated(EnumType.STRING)
    @Column(name = "state", length = 32, nullable = false)
    @Builder.Default
    private DeviceState state = DeviceState.ACTIVATED;

    // --- Device fingerprint ---

    @Column(name = "cpu_id", length = 128)
    private String cpuId;

    @Column(name = "tpm_ek_hash", length = 64)
    private String tpmEkHash;

    @Column(name = "mac_address", length = 17)
    private String macAddress;

    // --- Location & connectivity ---

    @Column(name = "last_ip", columnDefinition = "INET")
    private String lastIp;

    @Column(name = "last_location", columnDefinition = "JSONB")
    private String lastLocation;

    @Column(name = "last_seen_at")
    private OffsetDateTime lastSeenAt;

    // --- Audit timestamps ---

    @Column(name = "created_at", nullable = false, updatable = false)
    private OffsetDateTime createdAt;

    @Column(name = "updated_at", nullable = false)
    private OffsetDateTime updatedAt;

    // --- Lifecycle callbacks ---

    @PrePersist
    protected void onCreate() {
        OffsetDateTime now = OffsetDateTime.now();
        if (createdAt == null) {
            createdAt = now;
        }
        if (updatedAt == null) {
            updatedAt = now;
        }
    }

    @PreUpdate
    protected void onUpdate() {
        updatedAt = OffsetDateTime.now();
    }

    // --- Convenience helpers ---

    public boolean isBound() {
        return state == DeviceState.BOUND && boundUserId != null;
    }

    public boolean isLocked() {
        return state == DeviceState.LOCKED || state == DeviceState.LOST;
    }

    public boolean isWiped() {
        return state == DeviceState.WIPED;
    }
}
