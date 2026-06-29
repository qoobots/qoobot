package com.qoobot.qooauth.audit.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.qoobot.qooauth.audit.dto.AuditEventRequest;
import com.qoobot.qooauth.audit.dto.AuditQueryRequest;
import com.qoobot.qooauth.audit.dto.AuditQueryResponse;
import com.qoobot.qooauth.audit.entity.AuditLog;
import com.qoobot.qooauth.audit.repository.AuditLogRepository;
import jakarta.persistence.criteria.Predicate;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.data.jpa.domain.Specification;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Instant;
import java.util.ArrayList;
import java.util.HexFormat;
import java.util.List;
import java.util.Map;

@Slf4j
@Service
@RequiredArgsConstructor
public class AuditService {

    private final AuditLogRepository auditLogRepository;
    private final ObjectMapper objectMapper;

    /**
     * Write a single audit event to persistent storage.
     * Computes integrity hash for tamper detection.
     */
    @Transactional
    public AuditLog writeAuditEvent(AuditEventRequest request) {
        AuditLog log = toEntity(request);
        log.setIntegrityHash(computeIntegrityHash(log));
        AuditLog saved = auditLogRepository.save(log);
        log.debug("Audit event written: eventId={}, action={}, actor={}/{}",
                saved.getEventId(), saved.getAction(), saved.getActorType(), saved.getActorId());
        return saved;
    }

    /**
     * Batch write multiple audit events (from Kafka consumer).
     */
    @Transactional
    public List<AuditLog> writeAuditEvents(List<AuditEventRequest> requests) {
        List<AuditLog> logs = requests.stream().map(request -> {
            AuditLog log = toEntity(request);
            log.setIntegrityHash(computeIntegrityHash(log));
            return log;
        }).toList();
        List<AuditLog> saved = auditLogRepository.saveAll(logs);
        log.debug("Batch audit events written: count={}", saved.size());
        return saved;
    }

    /**
     * Query audit logs with flexible filters.
     */
    @Transactional(readOnly = true)
    public AuditQueryResponse queryAuditLogs(AuditQueryRequest request) {
        Sort.Direction direction = "ASC".equalsIgnoreCase(request.getSortDirection())
                ? Sort.Direction.ASC : Sort.Direction.DESC;
        Pageable pageable = PageRequest.of(request.getPage(), request.getSize(),
                Sort.by(direction, request.getSortBy()));

        Specification<AuditLog> spec = buildSpecification(request);
        Page<AuditLog> page = auditLogRepository.findAll(spec, pageable);

        List<AuditQueryResponse.AuditLogEntry> entries = page.getContent().stream()
                .map(this::toEntry)
                .toList();

        return AuditQueryResponse.builder()
                .events(entries)
                .totalCount(page.getTotalElements())
                .page(page.getNumber())
                .size(page.getSize())
                .totalPages(page.getTotalPages())
                .build();
    }

    /**
     * Get failed events by actor exceeding threshold (for anomaly detection).
     */
    @Transactional(readOnly = true)
    public List<Object[]> findActorsWithExcessiveFailures(Instant startTime, Instant endTime, long threshold) {
        return auditLogRepository.findActorsExceedingFailureThreshold(startTime, endTime, threshold);
    }

    /**
     * Purge audit events older than retention period.
     */
    @Transactional
    public int purgeOldEvents(Instant cutoffTime) {
        int deleted = auditLogRepository.deleteEventsOlderThan(cutoffTime);
        log.info("Purged {} audit events older than {}", deleted, cutoffTime);
        return deleted;
    }

    // --- Private helpers ---

    private AuditLog toEntity(AuditEventRequest request) {
        String detailsJson = null;
        if (request.getDetails() != null && !request.getDetails().isEmpty()) {
            try {
                detailsJson = objectMapper.writeValueAsString(request.getDetails());
            } catch (JsonProcessingException e) {
                log.warn("Failed to serialize audit details: {}", e.getMessage());
            }
        }

        return AuditLog.builder()
                .eventId(request.getEventId())
                .eventTime(request.getEventTime())
                .actorType(request.getActorType())
                .actorId(request.getActorId())
                .actorName(request.getActorName())
                .action(request.getAction())
                .resourceType(request.getResourceType())
                .resourceId(request.getResourceId())
                .resourceName(request.getResourceName())
                .result(request.getResult())
                .errorCode(request.getErrorCode())
                .errorMessage(request.getErrorMessage())
                .clientIp(request.getClientIp())
                .userAgent(request.getUserAgent())
                .geoCountry(request.getGeoCountry())
                .geoCity(request.getGeoCity())
                .geoRegion(request.getGeoRegion())
                .requestId(request.getRequestId())
                .sessionId(request.getSessionId())
                .clientId(request.getClientId())
                .authMethod(request.getAuthMethod())
                .details(detailsJson)
                .traceId(request.getTraceId())
                .spanId(request.getSpanId())
                .build();
    }

    @SuppressWarnings("unchecked")
    private AuditQueryResponse.AuditLogEntry toEntry(AuditLog log) {
        Object details = null;
        if (log.getDetails() != null) {
            try {
                details = objectMapper.readValue(log.getDetails(), Map.class);
            } catch (JsonProcessingException e) {
                details = log.getDetails();
            }
        }

        return AuditQueryResponse.AuditLogEntry.builder()
                .id(log.getId())
                .eventId(log.getEventId().toString())
                .eventTime(log.getEventTime().toString())
                .actorType(log.getActorType())
                .actorId(log.getActorId())
                .actorName(log.getActorName())
                .action(log.getAction())
                .resourceType(log.getResourceType())
                .resourceId(log.getResourceId())
                .resourceName(log.getResourceName())
                .result(log.getResult())
                .errorCode(log.getErrorCode())
                .clientIp(log.getClientIp())
                .userAgent(log.getUserAgent())
                .geoCountry(log.getGeoCountry())
                .geoCity(log.getGeoCity())
                .sessionId(log.getSessionId())
                .clientId(log.getClientId())
                .authMethod(log.getAuthMethod())
                .details(details)
                .traceId(log.getTraceId())
                .integrityHash(log.getIntegrityHash())
                .build();
    }

    private Specification<AuditLog> buildSpecification(AuditQueryRequest request) {
        return (root, query, cb) -> {
            List<Predicate> predicates = new ArrayList<>();

            if (request.getActorType() != null) {
                predicates.add(cb.equal(root.get("actorType"), request.getActorType()));
            }
            if (request.getActorId() != null) {
                predicates.add(cb.equal(root.get("actorId"), request.getActorId()));
            }
            if (request.getAction() != null) {
                predicates.add(cb.equal(root.get("action"), request.getAction()));
            }
            if (request.getResourceType() != null) {
                predicates.add(cb.equal(root.get("resourceType"), request.getResourceType()));
            }
            if (request.getResourceId() != null) {
                predicates.add(cb.equal(root.get("resourceId"), request.getResourceId()));
            }
            if (request.getResult() != null) {
                predicates.add(cb.equal(root.get("result"), request.getResult()));
            }
            if (request.getClientIp() != null) {
                predicates.add(cb.equal(root.get("clientIp"), request.getClientIp()));
            }
            if (request.getSessionId() != null) {
                predicates.add(cb.equal(root.get("sessionId"), request.getSessionId()));
            }
            if (request.getTraceId() != null) {
                predicates.add(cb.equal(root.get("traceId"), request.getTraceId()));
            }
            if (request.getStartTime() != null) {
                predicates.add(cb.greaterThanOrEqualTo(root.get("eventTime"), request.getStartTime()));
            }
            if (request.getEndTime() != null) {
                predicates.add(cb.lessThanOrEqualTo(root.get("eventTime"), request.getEndTime()));
            }

            return cb.and(predicates.toArray(new Predicate[0]));
        };
    }

    /**
     * Compute SHA-256 integrity hash: hash(eventId + eventTime + actorId + action + resourceId + result + clientIp).
     * Used for tamper-evident audit trail verification.
     */
    private String computeIntegrityHash(AuditLog log) {
        try {
            MessageDigest md = MessageDigest.getInstance("SHA-256");
            md.update(log.getEventId().toString().getBytes(StandardCharsets.UTF_8));
            md.update(log.getEventTime().toString().getBytes(StandardCharsets.UTF_8));
            md.update(log.getActorId().getBytes(StandardCharsets.UTF_8));
            md.update(log.getAction().getBytes(StandardCharsets.UTF_8));
            if (log.getResourceId() != null) {
                md.update(log.getResourceId().getBytes(StandardCharsets.UTF_8));
            }
            md.update(log.getResult().getBytes(StandardCharsets.UTF_8));
            if (log.getClientIp() != null) {
                md.update(log.getClientIp().getBytes(StandardCharsets.UTF_8));
            }
            return HexFormat.of().formatHex(md.digest());
        } catch (NoSuchAlgorithmException e) {
            throw new RuntimeException("SHA-256 not available", e);
        }
    }
}
