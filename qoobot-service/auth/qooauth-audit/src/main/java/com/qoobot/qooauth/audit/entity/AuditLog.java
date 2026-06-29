package com.qoobot.qooauth.audit.entity;

import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;
import java.util.UUID;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Entity
@Table(name = "audit_logs")
public class AuditLog {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "event_id", nullable = false, updatable = false)
    @Builder.Default
    private UUID eventId = UUID.randomUUID();

    @Column(name = "event_time", nullable = false, updatable = false)
    @Builder.Default
    private Instant eventTime = Instant.now();

    // --- Actor ---
    @Column(name = "actor_type", nullable = false, length = 32)
    private String actorType;

    @Column(name = "actor_id", nullable = false, length = 32)
    private String actorId;

    @Column(name = "actor_name", length = 128)
    private String actorName;

    // --- Action ---
    @Column(name = "action", nullable = false, length = 64)
    private String action;

    @Column(name = "resource_type", length = 32)
    private String resourceType;

    @Column(name = "resource_id", length = 32)
    private String resourceId;

    @Column(name = "resource_name", length = 256)
    private String resourceName;

    // --- Result ---
    @Column(name = "result", nullable = false, length = 16)
    private String result;

    @Column(name = "error_code", length = 32)
    private String errorCode;

    @Column(name = "error_message", length = 512)
    private String errorMessage;

    // --- Context ---
    @Column(name = "client_ip", columnDefinition = "inet")
    private String clientIp;

    @Column(name = "user_agent", length = 512)
    private String userAgent;

    @Column(name = "geo_country", length = 2)
    private String geoCountry;

    @Column(name = "geo_city", length = 128)
    private String geoCity;

    @Column(name = "geo_region", length = 128)
    private String geoRegion;

    // --- Request metadata ---
    @Column(name = "request_id", length = 64)
    private String requestId;

    @Column(name = "session_id", length = 64)
    private String sessionId;

    @Column(name = "client_id", length = 64)
    private String clientId;

    @Column(name = "auth_method", length = 32)
    private String authMethod;

    // --- Details ---
    @Column(name = "details", columnDefinition = "jsonb")
    private String details;

    // --- Tracing ---
    @Column(name = "trace_id", length = 64)
    private String traceId;

    @Column(name = "span_id", length = 32)
    private String spanId;

    // --- Integrity ---
    @Column(name = "integrity_hash", length = 128)
    private String integrityHash;
}
