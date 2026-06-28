package com.qoobot.qooauth.auth.entity;

import jakarta.persistence.*;
import java.time.Instant;

/**
 * Registered OAuth2 client (Relying Party).
 * Stores client metadata for OAuth2/OIDC flows.
 */
@Entity
@Table(name = "oauth2_clients")
public class OAuth2Client {

    @Id
    @Column(name = "client_id", length = 64)
    private String clientId;

    @Column(name = "client_secret", length = 255)
    private String clientSecret;

    @Column(name = "client_name", nullable = false, length = 128)
    private String clientName;

    @Column(name = "redirect_uris", nullable = false, columnDefinition = "TEXT")
    private String redirectUris;  // JSON array

    @Column(name = "grant_types", nullable = false, length = 255)
    private String grantTypes;    // comma-separated

    @Column(length = 512)
    private String scopes = "openid profile email";

    @Column(name = "token_endpoint_auth_method", length = 32)
    private String tokenEndpointAuthMethod = "client_secret_basic";

    @Column(name = "require_pkce")
    private boolean requirePkce = true;

    @Column(name = "require_consent")
    private boolean requireConsent = true;

    @Column(name = "logo_uri", length = 512)
    private String logoUri;

    @Column(name = "homepage_uri", length = 512)
    private String homepageUri;

    @Column(name = "policy_uri", length = 512)
    private String policyUri;

    @Column(name = "tos_uri", length = 512)
    private String tosUri;

    @Column(name = "owner_user_id", length = 32)
    private String ownerUserId;

    private boolean enabled = true;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt;

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt;

    // --- Getters / Setters ---

    public String getClientId() { return clientId; }
    public void setClientId(String clientId) { this.clientId = clientId; }

    public String getClientSecret() { return clientSecret; }
    public void setClientSecret(String clientSecret) { this.clientSecret = clientSecret; }

    public String getClientName() { return clientName; }
    public void setClientName(String clientName) { this.clientName = clientName; }

    public String getRedirectUris() { return redirectUris; }
    public void setRedirectUris(String redirectUris) { this.redirectUris = redirectUris; }

    public String getGrantTypes() { return grantTypes; }
    public void setGrantTypes(String grantTypes) { this.grantTypes = grantTypes; }

    public String getScopes() { return scopes; }
    public void setScopes(String scopes) { this.scopes = scopes; }

    public String getTokenEndpointAuthMethod() { return tokenEndpointAuthMethod; }
    public void setTokenEndpointAuthMethod(String tokenEndpointAuthMethod) { this.tokenEndpointAuthMethod = tokenEndpointAuthMethod; }

    public boolean isRequirePkce() { return requirePkce; }
    public void setRequirePkce(boolean requirePkce) { this.requirePkce = requirePkce; }

    public boolean isRequireConsent() { return requireConsent; }
    public void setRequireConsent(boolean requireConsent) { this.requireConsent = requireConsent; }

    public String getLogoUri() { return logoUri; }
    public void setLogoUri(String logoUri) { this.logoUri = logoUri; }

    public String getHomepageUri() { return homepageUri; }
    public void setHomepageUri(String homepageUri) { this.homepageUri = homepageUri; }

    public String getPolicyUri() { return policyUri; }
    public void setPolicyUri(String policyUri) { this.policyUri = policyUri; }

    public String getTosUri() { return tosUri; }
    public void setTosUri(String tosUri) { this.tosUri = tosUri; }

    public String getOwnerUserId() { return ownerUserId; }
    public void setOwnerUserId(String ownerUserId) { this.ownerUserId = ownerUserId; }

    public boolean isEnabled() { return enabled; }
    public void setEnabled(boolean enabled) { this.enabled = enabled; }

    public Instant getCreatedAt() { return createdAt; }
    public void setCreatedAt(Instant createdAt) { this.createdAt = createdAt; }

    public Instant getUpdatedAt() { return updatedAt; }
    public void setUpdatedAt(Instant updatedAt) { this.updatedAt = updatedAt; }
}
