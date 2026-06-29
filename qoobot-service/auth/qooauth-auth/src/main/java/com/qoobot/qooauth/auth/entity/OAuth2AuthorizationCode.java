package com.qoobot.qooauth.auth.entity;

import jakarta.persistence.*;
import java.time.Instant;

/**
 * Short-lived, single-use authorization code for the Authorization Code flow.
 */
@Entity
@Table(name = "oauth2_authorization_codes")
public class OAuth2AuthorizationCode {

    @Id
    @Column(length = 128)
    private String code;

    @Column(name = "client_id", nullable = false, length = 64)
    private String clientId;

    @Column(name = "user_id", nullable = false, length = 32)
    private String userId;

    @Column(name = "redirect_uri", nullable = false, length = 512)
    private String redirectUri;

    @Column(nullable = false, length = 512)
    private String scopes;

    @Column(name = "code_challenge", length = 128)
    private String codeChallenge;

    @Column(name = "code_challenge_method", length = 16)
    private String codeChallengeMethod = "S256";

    @Column(length = 128)
    private String nonce;

    @Column(length = 512)
    private String state;

    @Column(name = "expires_at", nullable = false)
    private Instant expiresAt;

    private boolean used = false;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt;

    // --- Getters / Setters ---

    public String getCode() { return code; }
    public void setCode(String code) { this.code = code; }

    public String getClientId() { return clientId; }
    public void setClientId(String clientId) { this.clientId = clientId; }

    public String getUserId() { return userId; }
    public void setUserId(String userId) { this.userId = userId; }

    public String getRedirectUri() { return redirectUri; }
    public void setRedirectUri(String redirectUri) { this.redirectUri = redirectUri; }

    public String getScopes() { return scopes; }
    public void setScopes(String scopes) { this.scopes = scopes; }

    public String getCodeChallenge() { return codeChallenge; }
    public void setCodeChallenge(String codeChallenge) { this.codeChallenge = codeChallenge; }

    public String getCodeChallengeMethod() { return codeChallengeMethod; }
    public void setCodeChallengeMethod(String codeChallengeMethod) { this.codeChallengeMethod = codeChallengeMethod; }

    public String getNonce() { return nonce; }
    public void setNonce(String nonce) { this.nonce = nonce; }

    public String getState() { return state; }
    public void setState(String state) { this.state = state; }

    public Instant getExpiresAt() { return expiresAt; }
    public void setExpiresAt(Instant expiresAt) { this.expiresAt = expiresAt; }

    public boolean isUsed() { return used; }
    public void setUsed(boolean used) { this.used = used; }

    public Instant getCreatedAt() { return createdAt; }
    public void setCreatedAt(Instant createdAt) { this.createdAt = createdAt; }
}
