package com.qoobot.qooauth.auth.entity;

import jakarta.persistence.*;
import java.time.Instant;

@Entity
@Table(name = "users")
public class User {

    @Id
    @Column(name = "user_id", length = 32)
    private String userId;

    @Column(nullable = false, unique = true, length = 255)
    private String email;

    @Column(length = 20, unique = true)
    private String phone;

    @Column(name = "password_hash", nullable = false, length = 255)
    private String passwordHash;

    @Column(name = "password_salt", nullable = false, length = 64)
    private String passwordSalt;

    @Column(nullable = false, length = 64)
    private String nickname;

    @Column(name = "avatar_hash", length = 64)
    private String avatarHash;

    @Column(length = 10)
    private String language = "zh-CN";

    @Column(length = 50)
    private String timezone = "Asia/Shanghai";

    @Column(nullable = false, length = 32)
    private String state = "ACTIVE";

    @Column(name = "email_verified")
    private boolean emailVerified = false;

    @Column(name = "phone_verified")
    private boolean phoneVerified = false;

    @Column(name = "mfa_enabled")
    private boolean mfaEnabled = false;

    @Column(name = "mfa_methods", columnDefinition = "jsonb")
    private String mfaMethods;

    @Column(name = "totp_secret", length = 64)
    private String totpSecret;

    @Column(name = "recovery_codes_hash", columnDefinition = "jsonb")
    private String recoveryCodesHash;

    @Column(name = "password_changed_at")
    private Instant passwordChangedAt;

    @Column(name = "password_history", columnDefinition = "jsonb")
    private String passwordHistory;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt;

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt;

    @Column(name = "last_login_at")
    private Instant lastLoginAt;

    @Column(name = "deleted_at")
    private Instant deletedAt;

    // Getters and setters
    public String getUserId() { return userId; }
    public void setUserId(String userId) { this.userId = userId; }

    public String getEmail() { return email; }
    public void setEmail(String email) { this.email = email; }

    public String getPhone() { return phone; }
    public void setPhone(String phone) { this.phone = phone; }

    public String getPasswordHash() { return passwordHash; }
    public void setPasswordHash(String passwordHash) { this.passwordHash = passwordHash; }

    public String getPasswordSalt() { return passwordSalt; }
    public void setPasswordSalt(String passwordSalt) { this.passwordSalt = passwordSalt; }

    public String getNickname() { return nickname; }
    public void setNickname(String nickname) { this.nickname = nickname; }

    public String getAvatarHash() { return avatarHash; }
    public void setAvatarHash(String avatarHash) { this.avatarHash = avatarHash; }

    public String getLanguage() { return language; }
    public void setLanguage(String language) { this.language = language; }

    public String getTimezone() { return timezone; }
    public void setTimezone(String timezone) { this.timezone = timezone; }

    public String getState() { return state; }
    public void setState(String state) { this.state = state; }

    public boolean isEmailVerified() { return emailVerified; }
    public void setEmailVerified(boolean emailVerified) { this.emailVerified = emailVerified; }

    public boolean isPhoneVerified() { return phoneVerified; }
    public void setPhoneVerified(boolean phoneVerified) { this.phoneVerified = phoneVerified; }

    public boolean isMfaEnabled() { return mfaEnabled; }
    public void setMfaEnabled(boolean mfaEnabled) { this.mfaEnabled = mfaEnabled; }

    public String[] getMfaMethods() {
        if (mfaMethods == null || mfaMethods.isEmpty()) return new String[0];
        return mfaMethods.replaceAll("[\\[\\]\"]", "").split(",");
    }
    public void setMfaMethods(String mfaMethods) { this.mfaMethods = mfaMethods; }

    public String getTotpSecret() { return totpSecret; }
    public void setTotpSecret(String totpSecret) { this.totpSecret = totpSecret; }

    public String getRecoveryCodesHash() { return recoveryCodesHash; }
    public void setRecoveryCodesHash(String recoveryCodesHash) { this.recoveryCodesHash = recoveryCodesHash; }

    public Instant getPasswordChangedAt() { return passwordChangedAt; }
    public void setPasswordChangedAt(Instant passwordChangedAt) { this.passwordChangedAt = passwordChangedAt; }

    public String getPasswordHistory() { return passwordHistory; }
    public void setPasswordHistory(String passwordHistory) { this.passwordHistory = passwordHistory; }

    public Instant getCreatedAt() { return createdAt; }
    public void setCreatedAt(Instant createdAt) { this.createdAt = createdAt; }

    public Instant getUpdatedAt() { return updatedAt; }
    public void setUpdatedAt(Instant updatedAt) { this.updatedAt = updatedAt; }

    public Instant getLastLoginAt() { return lastLoginAt; }
    public void setLastLoginAt(Instant lastLoginAt) { this.lastLoginAt = lastLoginAt; }

    public Instant getDeletedAt() { return deletedAt; }
    public void setDeletedAt(Instant deletedAt) { this.deletedAt = deletedAt; }
}
