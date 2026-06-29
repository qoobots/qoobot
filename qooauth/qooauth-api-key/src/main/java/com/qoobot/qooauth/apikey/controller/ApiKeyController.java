package com.qoobot.qooauth.apikey.controller;

import com.qoobot.qooauth.apikey.dto.ApiKeyCreateRequest;
import com.qoobot.qooauth.apikey.dto.ApiKeyResponse;
import com.qoobot.qooauth.apikey.service.ApiKeyService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.security.Principal;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/v1/api-keys")
@RequiredArgsConstructor
public class ApiKeyController {

    private final ApiKeyService apiKeyService;

    /**
     * Create a new API key.
     * Returns the raw key only once - it cannot be retrieved again.
     */
    @PostMapping
    public ResponseEntity<ApiKeyResponse> createApiKey(
            @Valid @RequestBody ApiKeyCreateRequest request,
            Principal principal) {
        String userId = principal.getName();
        ApiKeyResponse response = apiKeyService.generateApiKey(userId, request);
        return ResponseEntity.status(HttpStatus.CREATED).body(response);
    }

    /**
     * List all API keys for the authenticated user.
     * Raw key values are never returned.
     */
    @GetMapping
    public ResponseEntity<List<ApiKeyResponse>> listApiKeys(Principal principal) {
        String userId = principal.getName();
        List<ApiKeyResponse> keys = apiKeyService.listByUser(userId);
        return ResponseEntity.ok(keys);
    }

    /**
     * Revoke (delete) an API key.
     */
    @DeleteMapping("/{keyId}")
    public ResponseEntity<Map<String, String>> revokeApiKey(
            @PathVariable String keyId,
            Principal principal) {
        String userId = principal.getName();
        apiKeyService.revokeKey(keyId, userId);
        return ResponseEntity.ok(Map.of("status", "revoked", "key_id", keyId));
    }

    /**
     * Rotate an existing API key - generates new key material while preserving metadata.
     */
    @PostMapping("/{keyId}/rotate")
    public ResponseEntity<ApiKeyResponse> rotateApiKey(
            @PathVariable String keyId,
            Principal principal) {
        String userId = principal.getName();
        ApiKeyResponse response = apiKeyService.rotateKey(keyId, userId);
        return ResponseEntity.ok(response);
    }

    /**
     * Check remaining API key quota for the authenticated user.
     */
    @GetMapping("/quota")
    public ResponseEntity<Map<String, Object>> checkQuota(Principal principal) {
        String userId = principal.getName();
        long remaining = apiKeyService.checkQuota(userId);
        return ResponseEntity.ok(Map.of(
            "remaining", remaining,
            "max", 20L
        ));
    }
}
