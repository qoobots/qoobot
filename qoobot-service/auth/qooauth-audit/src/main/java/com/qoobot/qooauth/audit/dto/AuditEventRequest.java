package com.qoobot.qooauth.audit.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;
import java.util.Map;
import java.util.UUID;

/**
 * Audit event published to Kafka by other services.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class AuditEventRequest {

    @NotNull
    private UUID eventId;

    @NotNull
    private Instant eventTime;

    // Actor
    @NotBlank
    private String actorType;

    @NotBlank
    private String actorId;

    private String actorName;

    // Action
    @NotBlank
    private String action;

    private String resourceType;
    private String resourceId;
    private String resourceName;

    // Result
    @NotBlank
    private String result;

    private String errorCode;
    private String errorMessage;

    // Context
    private String clientIp;
    private String userAgent;
    private String geoCountry;
    private String geoCity;
    private String geoRegion;

    // Request metadata
    private String requestId;
    private String sessionId;
    private String clientId;
    private String authMethod;

    // Flexible details
    private Map<String, Object> details;

    // Tracing
    private String traceId;
    private String spanId;
}
