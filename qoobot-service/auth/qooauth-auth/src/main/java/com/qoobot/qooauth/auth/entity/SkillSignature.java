package com.qoobot.qooauth.auth.entity;

import jakarta.persistence.*;
import java.time.Instant;

/**
 * Skill Signature — code signing for .qooskills packages.
 *
 * Each skill package is signed by a developer certificate,
 * ensuring integrity and authenticity. The signature chain
 * is verified before installation on any robot.
 */
@Entity
@Table(name = "skill_signatures", indexes = {
    @Index(name = "idx_ss_skill", columnList = "skillId"),
    @Index(name = "idx_ss_cert", columnList = "developerCertId"),
    @Index(name = "idx_ss_state", columnList = "state")
})
public class SkillSignature {

    @Id
    @Column(name = "signature_id", length = 64)
    private String signatureId;

    /**
     * Unique skill identifier (e.g., "com.qoobot.skills.navigation")
     */
    @Column(name = "skill_id", nullable = false, length = 128)
    private String skillId;

    @Column(name = "skill_version", nullable = false, length = 32)
    private String skillVersion;

    /**
     * SHA-256 hash of the .qooskills package content.
     */
    @Column(name = "package_hash", nullable = false, length = 128)
    private String packageHash;

    /**
     * ECDSA signature (DER-encoded, Base64) of the package hash.
     */
    @Column(name = "signature", nullable = false, columnDefinition = "TEXT")
    private String signature;

    /**
     * Developer certificate used for signing.
     */
    @Column(name = "developer_cert_id", nullable = false, length = 64)
    private String developerCertId;

    @Column(name = "developer_user_id", nullable = false, length = 64)
    private String developerUserId;

    /**
     * Timestamp counter-signature (RFC 3161 TSA).
     * Ensures signature was created before certificate expiry.
     */
    @Column(name = "timestamp_signature", columnDefinition = "TEXT")
    private String timestampSignature;

    @Column(name = "timestamp_authority_url", length = 256)
    private String timestampAuthorityUrl;

    /**
     * Signature state: VALID, REVOKED, EXPIRED
     */
    @Column(name = "state", nullable = false, length = 16)
    private String state = "VALID";

    /**
     * Additional signature metadata as JSON:
     * { "signing_tool": "qoodev 1.5.0", "platform": "linux-x64" }
     */
    @Column(name = "metadata", columnDefinition = "TEXT")
    private String metadata;

    @Column(name = "signed_at", nullable = false)
    private Instant signedAt;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt;

    // --- Getters and Setters ---

    public String getSignatureId() { return signatureId; }
    public void setSignatureId(String signatureId) { this.signatureId = signatureId; }

    public String getSkillId() { return skillId; }
    public void setSkillId(String skillId) { this.skillId = skillId; }

    public String getSkillVersion() { return skillVersion; }
    public void setSkillVersion(String skillVersion) { this.skillVersion = skillVersion; }

    public String getPackageHash() { return packageHash; }
    public void setPackageHash(String packageHash) { this.packageHash = packageHash; }

    public String getSignature() { return signature; }
    public void setSignature(String signature) { this.signature = signature; }

    public String getDeveloperCertId() { return developerCertId; }
    public void setDeveloperCertId(String developerCertId) { this.developerCertId = developerCertId; }

    public String getDeveloperUserId() { return developerUserId; }
    public void setDeveloperUserId(String developerUserId) { this.developerUserId = developerUserId; }

    public String getTimestampSignature() { return timestampSignature; }
    public void setTimestampSignature(String timestampSignature) { this.timestampSignature = timestampSignature; }

    public String getTimestampAuthorityUrl() { return timestampAuthorityUrl; }
    public void setTimestampAuthorityUrl(String timestampAuthorityUrl) { this.timestampAuthorityUrl = timestampAuthorityUrl; }

    public String getState() { return state; }
    public void setState(String state) { this.state = state; }

    public String getMetadata() { return metadata; }
    public void setMetadata(String metadata) { this.metadata = metadata; }

    public Instant getSignedAt() { return signedAt; }
    public void setSignedAt(Instant signedAt) { this.signedAt = signedAt; }

    public Instant getCreatedAt() { return createdAt; }
    public void setCreatedAt(Instant createdAt) { this.createdAt = createdAt; }
}
