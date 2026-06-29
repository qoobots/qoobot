package com.qoobot.qooauth.auth.controller;

import com.qoobot.qooauth.auth.service.KeychainService;
import com.qoobot.qooauth.auth.service.KeychainService.KeychainEntry;
import com.qoobot.qooauth.common.dto.ApiResponse;
import org.springframework.web.bind.annotation.*;

import java.util.Base64;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Keychain Controller.
 * <p>
 * Secure key storage and management endpoints:
 * <ul>
 *   <li>Store/retrieve symmetric keys</li>
 *   <li>Store/retrieve private keys</li>
 *   <li>Store/retrieve passwords and tokens</li>
 *   <li>Key rotation</li>
 *   <li>List and delete keys</li>
 * </ul>
 */
@RestController
@RequestMapping("/api/v1/auth/keychain")
public class KeychainController {

    private final KeychainService keychainService;

    public KeychainController(KeychainService keychainService) {
        this.keychainService = keychainService;
    }

    /**
     * Store a symmetric key.
     */
    @PostMapping("/symmetric")
    public ApiResponse<Map<String, Object>> storeSymmetricKey(@RequestBody Map<String, String> body) {
        try {
            String userId = body.get("user_id");
            String keyAlias = body.get("key_alias");
            byte[] keyData = Base64.getDecoder().decode(body.get("key_data"));
            String accessLevel = body.getOrDefault("access_level", "PRIVATE");
            boolean requireBio = Boolean.parseBoolean(body.getOrDefault("require_biometric", "false"));

            KeychainEntry entry = keychainService.storeSymmetricKey(
                    userId, keyAlias, keyData, accessLevel, requireBio);

            Map<String, Object> result = new HashMap<>();
            result.put("key_alias", entry.keyAlias);
            result.put("key_type", entry.keyType);
            result.put("version", entry.version);
            result.put("created_at", entry.createdAt.toString());
            return ApiResponse.ok(result);
        } catch (Exception e) {
            return ApiResponse.error("KEYCHAIN_STORE_FAILED", e.getMessage());
        }
    }

    /**
     * Store a password/credential.
     */
    @PostMapping("/password")
    public ApiResponse<Map<String, Object>> storePassword(@RequestBody Map<String, String> body) {
        try {
            String userId = body.get("user_id");
            String keyAlias = body.get("key_alias");
            String password = body.get("password");
            String serviceName = body.getOrDefault("service", "default");
            String accessLevel = body.getOrDefault("access_level", "SENSITIVE");

            KeychainEntry entry = keychainService.storePassword(
                    userId, keyAlias, password, serviceName, accessLevel);

            Map<String, Object> result = new HashMap<>();
            result.put("key_alias", entry.keyAlias);
            result.put("key_type", entry.keyType);
            result.put("version", entry.version);
            return ApiResponse.ok(result);
        } catch (Exception e) {
            return ApiResponse.error("KEYCHAIN_STORE_FAILED", e.getMessage());
        }
    }

    /**
     * Store an API token.
     */
    @PostMapping("/token")
    public ApiResponse<Map<String, Object>> storeToken(@RequestBody Map<String, String> body) {
        try {
            String userId = body.get("user_id");
            String keyAlias = body.get("key_alias");
            String token = body.get("token");
            String tokenType = body.getOrDefault("token_type", "bearer");

            KeychainEntry entry = keychainService.storeToken(
                    userId, keyAlias, token, tokenType, null);

            Map<String, Object> result = new HashMap<>();
            result.put("key_alias", entry.keyAlias);
            result.put("key_type", entry.keyType);
            result.put("token_type", tokenType);
            return ApiResponse.ok(result);
        } catch (Exception e) {
            return ApiResponse.error("KEYCHAIN_STORE_FAILED", e.getMessage());
        }
    }

    /**
     * Retrieve a stored password.
     */
    @GetMapping("/password/{userId}/{keyAlias}")
    public ApiResponse<Map<String, String>> getPassword(
            @PathVariable String userId, @PathVariable String keyAlias) {
        try {
            String password = keychainService.getPassword(userId, keyAlias);
            Map<String, String> result = new HashMap<>();
            result.put("key_alias", keyAlias);
            result.put("password", password);
            return ApiResponse.ok(result);
        } catch (Exception e) {
            return ApiResponse.error("KEYCHAIN_RETRIEVE_FAILED", e.getMessage());
        }
    }

    /**
     * Retrieve a stored token.
     */
    @GetMapping("/token/{userId}/{keyAlias}")
    public ApiResponse<Map<String, String>> getToken(
            @PathVariable String userId, @PathVariable String keyAlias) {
        try {
            String token = keychainService.getToken(userId, keyAlias);
            Map<String, String> result = new HashMap<>();
            result.put("key_alias", keyAlias);
            result.put("token", token);
            return ApiResponse.ok(result);
        } catch (Exception e) {
            return ApiResponse.error("KEYCHAIN_RETRIEVE_FAILED", e.getMessage());
        }
    }

    /**
     * Get keychain entry metadata (without decrypting).
     */
    @GetMapping("/entry/{userId}/{keyAlias}")
    public ApiResponse<Map<String, Object>> getEntry(
            @PathVariable String userId, @PathVariable String keyAlias) {
        KeychainEntry entry = keychainService.getEntryMetadata(userId, keyAlias);
        if (entry == null) {
            return ApiResponse.error("NOT_FOUND", "Key not found: " + keyAlias);
        }

        Map<String, Object> result = new HashMap<>();
        result.put("key_alias", entry.keyAlias);
        result.put("key_type", entry.keyType);
        result.put("access_level", entry.accessLevel);
        result.put("require_biometric", entry.requireBiometric);
        result.put("version", entry.version);
        result.put("metadata", entry.metadata);
        result.put("created_at", entry.createdAt.toString());
        result.put("updated_at", entry.updatedAt.toString());
        return ApiResponse.ok(result);
    }

    /**
     * List all keys for a user.
     */
    @GetMapping("/list/{userId}")
    public ApiResponse<List<String>> listKeys(@PathVariable String userId) {
        List<String> keys = keychainService.listKeys(userId);
        return ApiResponse.ok(keys);
    }

    /**
     * Delete a keychain entry.
     */
    @DeleteMapping("/{userId}/{keyAlias}")
    public ApiResponse<Map<String, String>> deleteEntry(
            @PathVariable String userId, @PathVariable String keyAlias) {
        keychainService.deleteEntry(userId, keyAlias);
        return ApiResponse.ok(Map.of("status", "deleted", "key_alias", keyAlias));
    }

    /**
     * Rotate a symmetric key.
     */
    @PostMapping("/rotate")
    public ApiResponse<Map<String, String>> rotateKey(@RequestBody Map<String, String> body) {
        try {
            String userId = body.get("user_id");
            String keyAlias = body.get("key_alias");
            byte[] newKeyData = Base64.getDecoder().decode(body.get("new_key_data"));

            keychainService.rotateKey(userId, keyAlias, newKeyData);

            return ApiResponse.ok(Map.of("key_alias", keyAlias, "status", "rotated"));
        } catch (Exception e) {
            return ApiResponse.error("KEYCHAIN_ROTATE_FAILED", e.getMessage());
        }
    }
}
