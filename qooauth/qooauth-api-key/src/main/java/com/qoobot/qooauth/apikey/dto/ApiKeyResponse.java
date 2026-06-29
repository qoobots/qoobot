package com.qoobot.qooauth.apikey.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;
import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ApiKeyResponse {

    private String keyId;

    private String name;

    /** The raw API key value - only shown once upon creation. */
    private String apiKey;

    private List<String> permissions;

    private String state;

    private Instant createdAt;

    private Instant expiresAt;

    private Instant lastUsedAt;

    public static ApiKeyResponse withoutRawKey(ApiKeyResponse response) {
        return ApiKeyResponse.builder()
            .keyId(response.getKeyId())
            .name(response.getName())
            .apiKey(null)
            .permissions(response.getPermissions())
            .state(response.getState())
            .createdAt(response.getCreatedAt())
            .expiresAt(response.getExpiresAt())
            .lastUsedAt(response.getLastUsedAt())
            .build();
    }
}
