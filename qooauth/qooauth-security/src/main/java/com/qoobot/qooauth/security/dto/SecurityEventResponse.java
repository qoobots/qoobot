package com.qoobot.qooauth.security.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.Map;

/**
 * DTO for security event API response.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class SecurityEventResponse {

    private Long id;
    private String userId;
    private String eventType;
    private String severity;
    private String sourceIp;
    private Map<String, Object> details;
    private String detectedAt;
    private String resolvedAt;
    private boolean resolved;
}
