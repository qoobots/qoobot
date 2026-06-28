package com.qoobot.qooauth.auth.entity;

import jakarta.persistence.*;
import java.time.Instant;

@Entity
@Table(name = "activation_challenges")
public class ActivationChallenge {

    @Id
    @Column(name = "challenge_id", length = 64)
    private String challengeId;

    @Column(name = "activation_id", nullable = false, length = 64)
    private String activationId;

    @Column(name = "device_id", nullable = false, length = 64)
    private String deviceId;

    @Column(name = "challenge_type", nullable = false, length = 32)
    private String challengeType = "SIGNATURE";

    @Column(name = "challenge_nonce", nullable = false, length = 128)
    private String challengeNonce;

    @Column(name = "expected_response_hash", length = 64)
    private String expectedResponseHash;

    @Column(name = "actual_response", columnDefinition = "TEXT")
    private String actualResponse;

    @Column(name = "response_valid")
    private Boolean responseValid;

    @Column(name = "challenge_state", nullable = false, length = 16)
    private String challengeState = "PENDING";

    @Column(name = "issued_at", nullable = false)
    private Instant issuedAt;

    @Column(name = "responded_at")
    private Instant respondedAt;

    @Column(name = "expires_at", nullable = false)
    private Instant expiresAt;

    @Column(name = "metadata", columnDefinition = "jsonb")
    private String metadata = "{}";

    // --- Getters and setters ---
    public String getChallengeId() { return challengeId; }
    public void setChallengeId(String challengeId) { this.challengeId = challengeId; }

    public String getActivationId() { return activationId; }
    public void setActivationId(String activationId) { this.activationId = activationId; }

    public String getDeviceId() { return deviceId; }
    public void setDeviceId(String deviceId) { this.deviceId = deviceId; }

    public String getChallengeType() { return challengeType; }
    public void setChallengeType(String challengeType) { this.challengeType = challengeType; }

    public String getChallengeNonce() { return challengeNonce; }
    public void setChallengeNonce(String challengeNonce) { this.challengeNonce = challengeNonce; }

    public String getExpectedResponseHash() { return expectedResponseHash; }
    public void setExpectedResponseHash(String expectedResponseHash) { this.expectedResponseHash = expectedResponseHash; }

    public String getActualResponse() { return actualResponse; }
    public void setActualResponse(String actualResponse) { this.actualResponse = actualResponse; }

    public Boolean getResponseValid() { return responseValid; }
    public void setResponseValid(Boolean responseValid) { this.responseValid = responseValid; }

    public String getChallengeState() { return challengeState; }
    public void setChallengeState(String challengeState) { this.challengeState = challengeState; }

    public Instant getIssuedAt() { return issuedAt; }
    public void setIssuedAt(Instant issuedAt) { this.issuedAt = issuedAt; }

    public Instant getRespondedAt() { return respondedAt; }
    public void setRespondedAt(Instant respondedAt) { this.respondedAt = respondedAt; }

    public Instant getExpiresAt() { return expiresAt; }
    public void setExpiresAt(Instant expiresAt) { this.expiresAt = expiresAt; }

    public String getMetadata() { return metadata; }
    public void setMetadata(String metadata) { this.metadata = metadata; }
}
