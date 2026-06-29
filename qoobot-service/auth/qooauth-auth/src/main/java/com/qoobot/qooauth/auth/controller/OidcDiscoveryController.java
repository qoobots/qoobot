package com.qoobot.qooauth.auth.controller;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.Map;

/**
 * OIDC Discovery endpoint (.well-known/openid-configuration).
 * Enables standard OIDC client auto-configuration.
 */
@RestController
public class OidcDiscoveryController {

    private static final String ISSUER = "https://id.qoobot.com";

    @GetMapping("/.well-known/openid-configuration")
    public ResponseEntity<Map<String, Object>> getOpenIdConfiguration() {
        Map<String, Object> config = Map.ofEntries(
                Map.entry("issuer", ISSUER),
                Map.entry("authorization_endpoint", ISSUER + "/oauth2/authorize"),
                Map.entry("token_endpoint", ISSUER + "/oauth2/token"),
                Map.entry("userinfo_endpoint", ISSUER + "/oauth2/userinfo"),
                Map.entry("jwks_uri", ISSUER + "/oauth2/jwks"),
                Map.entry("registration_endpoint", ISSUER + "/oauth2/register"),
                Map.entry("scopes_supported", List.of("openid", "profile", "email", "phone", "address")),
                Map.entry("response_types_supported", List.of("code", "id_token", "token id_token")),
                Map.entry("grant_types_supported", List.of("authorization_code", "refresh_token",
                        "client_credentials", "urn:ietf:params:oauth:grant-type:device_code")),
                Map.entry("subject_types_supported", List.of("public")),
                Map.entry("id_token_signing_alg_values_supported", List.of("Ed25519", "RS256")),
                Map.entry("token_endpoint_auth_methods_supported", List.of(
                        "client_secret_basic", "client_secret_post", "private_key_jwt")),
                Map.entry("claims_supported", List.of("sub", "iss", "aud", "exp", "iat",
                        "email", "email_verified", "name", "picture", "locale")),
                Map.entry("code_challenge_methods_supported", List.of("S256")),
                Map.entry("ui_locales_supported", List.of("zh-CN", "en-US", "ja-JP"))
        );
        return ResponseEntity.ok(config);
    }
}
