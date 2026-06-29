package com.qoobot.qooauth.security.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * DTO for granting or revoking user consent.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ConsentRequest {

    /**
     * User ID.
     */
    @NotBlank
    private String userId;

    /**
     * Type of consent (e.g., "DATA_COLLECTION", "MARKETING", "THIRD_PARTY_SHARING").
     */
    @NotBlank
    private String consentType;

    /**
     * Version of the consent policy.
     */
    @NotBlank
    private String version;

    /**
     * Whether consent is being granted (true) or revoked (false).
     */
    @NotNull
    private Boolean granted;

    /**
     * IP address of the consent action.
     */
    private String ipAddress;
}
