package com.qoobot.qooauth.auth.entity;

import jakarta.persistence.*;
import java.time.Instant;

@Entity
@Table(name = "device_activations")
public class DeviceActivation {

    @Id
    @Column(name = "activation_id", length = 64)
    private String activationId;

    @Column(name = "user_id", nullable = false, length = 32)
    private String userId;

    @Column(name = "device_id", nullable = false, length = 64)
    private String deviceId;

    @Column(name = "cert_id", length = 64)
    private String certId;

    @Column(name = "device_serial", nullable = false, length = 128)
    private String deviceSerial;

    @Column(name = "device_model", length = 128)
    private String deviceModel;

    @Column(name = "firmware_version", length = 32)
    private String firmwareVersion;

    @Column(name = "hardware_fingerprint", length = 256)
    private String hardwareFingerprint;

    @Column(name = "activation_state", nullable = false, length = 16)
    private String activationState = "PENDING";

    @Column(name = "bootstrap_cert_id", length = 64)
    private String bootstrapCertId;

    @Column(name = "activation_token", length = 256)
    private String activationToken;

    @Column(name = "challenge_nonce", length = 128)
    private String challengeNonce;

    @Column(name = "challenge_issued_at")
    private Instant challengeIssuedAt;

    @Column(name = "challenge_expires_at")
    private Instant challengeExpiresAt;

    @Column(name = "challenge_attempts", nullable = false)
    private int challengeAttempts = 0;

    @Column(name = "max_challenge_attempts", nullable = false)
    private int maxChallengeAttempts = 5;

    @Column(name = "activated_at")
    private Instant activatedAt;

    @Column(name = "expires_at")
    private Instant expiresAt;

    @Column(name = "failure_reason", length = 512)
    private String failureReason;

    @Column(name = "metadata", columnDefinition = "jsonb")
    private String metadata = "{}";

    @Column(name = "created_at", nullable = false)
    private Instant createdAt;

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt;

    // --- Getters and setters ---
    public String getActivationId() { return activationId; }
    public void setActivationId(String activationId) { this.activationId = activationId; }

    public String getUserId() { return userId; }
    public void setUserId(String userId) { this.userId = userId; }

    public String getDeviceId() { return deviceId; }
    public void setDeviceId(String deviceId) { this.deviceId = deviceId; }

    public String getCertId() { return certId; }
    public void setCertId(String certId) { this.certId = certId; }

    public String getDeviceSerial() { return deviceSerial; }
    public void setDeviceSerial(String deviceSerial) { this.deviceSerial = deviceSerial; }

    public String getDeviceModel() { return deviceModel; }
    public void setDeviceModel(String deviceModel) { this.deviceModel = deviceModel; }

    public String getFirmwareVersion() { return firmwareVersion; }
    public void setFirmwareVersion(String firmwareVersion) { this.firmwareVersion = firmwareVersion; }

    public String getHardwareFingerprint() { return hardwareFingerprint; }
    public void setHardwareFingerprint(String hardwareFingerprint) { this.hardwareFingerprint = hardwareFingerprint; }

    public String getActivationState() { return activationState; }
    public void setActivationState(String activationState) { this.activationState = activationState; }

    public String getBootstrapCertId() { return bootstrapCertId; }
    public void setBootstrapCertId(String bootstrapCertId) { this.bootstrapCertId = bootstrapCertId; }

    public String getActivationToken() { return activationToken; }
    public void setActivationToken(String activationToken) { this.activationToken = activationToken; }

    public String getChallengeNonce() { return challengeNonce; }
    public void setChallengeNonce(String challengeNonce) { this.challengeNonce = challengeNonce; }

    public Instant getChallengeIssuedAt() { return challengeIssuedAt; }
    public void setChallengeIssuedAt(Instant challengeIssuedAt) { this.challengeIssuedAt = challengeIssuedAt; }

    public Instant getChallengeExpiresAt() { return challengeExpiresAt; }
    public void setChallengeExpiresAt(Instant challengeExpiresAt) { this.challengeExpiresAt = challengeExpiresAt; }

    public int getChallengeAttempts() { return challengeAttempts; }
    public void setChallengeAttempts(int challengeAttempts) { this.challengeAttempts = challengeAttempts; }

    public int getMaxChallengeAttempts() { return maxChallengeAttempts; }
    public void setMaxChallengeAttempts(int maxChallengeAttempts) { this.maxChallengeAttempts = maxChallengeAttempts; }

    public Instant getActivatedAt() { return activatedAt; }
    public void setActivatedAt(Instant activatedAt) { this.activatedAt = activatedAt; }

    public Instant getExpiresAt() { return expiresAt; }
    public void setExpiresAt(Instant expiresAt) { this.expiresAt = expiresAt; }

    public String getFailureReason() { return failureReason; }
    public void setFailureReason(String failureReason) { this.failureReason = failureReason; }

    public String getMetadata() { return metadata; }
    public void setMetadata(String metadata) { this.metadata = metadata; }

    public Instant getCreatedAt() { return createdAt; }
    public void setCreatedAt(Instant createdAt) { this.createdAt = createdAt; }

    public Instant getUpdatedAt() { return updatedAt; }
    public void setUpdatedAt(Instant updatedAt) { this.updatedAt = updatedAt; }
}
