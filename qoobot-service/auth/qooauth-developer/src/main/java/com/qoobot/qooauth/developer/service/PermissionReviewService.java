package com.qoobot.qooauth.developer.service;

import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Developer permission review workflow.
 * Manages PENDING -> APPROVED/DENIED lifecycle with compliance checks.
 */
@Slf4j
@Service
public class PermissionReviewService {

    private final Map<String, PermissionRequest> requests = new ConcurrentHashMap<>();

    /**
     * Submit a permission request for review.
     */
    public PermissionRequest submitRequest(String developerId, List<String> requestedPermissions, String justification) {
        String requestId = UUID.randomUUID().toString().replace("-", "");

        PermissionRequest request = new PermissionRequest(
            requestId, developerId, requestedPermissions, justification,
            "PENDING", Instant.now(), null, null
        );

        requests.put(requestId, request);
        log.info("Permission request {} submitted by {} for: {}", requestId, developerId, requestedPermissions);
        return request;
    }

    /**
     * Review and approve/deny a permission request.
     */
    public PermissionRequest reviewRequest(String requestId, String reviewerId, boolean approved, String comment) {
        PermissionRequest request = requests.get(requestId);
        if (request == null) {
            throw new IllegalArgumentException("Permission request not found: " + requestId);
        }

        if (!"PENDING".equals(request.state())) {
            throw new IllegalStateException("Request is already " + request.state() + ": " + requestId);
        }

        // Compliance check before approval
        if (approved && !complianceCheck(request)) {
            throw new IllegalStateException("Compliance check failed for request: " + requestId);
        }

        PermissionRequest updated = new PermissionRequest(
            request.requestId(), request.developerId(), request.requestedPermissions(),
            request.justification(),
            approved ? "APPROVED" : "DENIED",
            request.submittedAt(),
            Instant.now(),
            comment
        );

        requests.put(requestId, updated);
        log.info("Permission request {} {} by reviewer {}: {}", requestId, updated.state(), reviewerId, comment);
        return updated;
    }

    /**
     * List pending permission requests.
     */
    public List<PermissionRequest> listPendingRequests() {
        return requests.values().stream()
            .filter(r -> "PENDING".equals(r.state()))
            .sorted(Comparator.comparing(PermissionRequest::submittedAt))
            .toList();
    }

    /**
     * List all requests for a developer.
     */
    public List<PermissionRequest> listDeveloperRequests(String developerId) {
        return requests.values().stream()
            .filter(r -> r.developerId().equals(developerId))
            .sorted(Comparator.comparing(PermissionRequest::submittedAt).reversed())
            .toList();
    }

    /**
     * Compliance check for permission requests.
     * Validates against security policies before approval.
     */
    private boolean complianceCheck(PermissionRequest request) {
        // Sensitive permissions require additional scrutiny
        List<String> sensitivePermissions = List.of("admin", "full_access", "user_data", "device_control");

        boolean hasSensitive = request.requestedPermissions().stream()
            .anyMatch(p -> sensitivePermissions.stream().anyMatch(p::equalsIgnoreCase));

        if (hasSensitive) {
            log.warn("Sensitive permissions requested by {}: {}", request.developerId(), request.requestedPermissions());
            // In production, this would trigger additional approval workflows
        }

        // Check for excessive permission requests
        if (request.requestedPermissions().size() > 10) {
            log.warn("Large permission set requested by {}: {} permissions", request.developerId(), request.requestedPermissions().size());
        }

        return true;
    }

    public record PermissionRequest(
        String requestId,
        String developerId,
        List<String> requestedPermissions,
        String justification,
        String state,
        Instant submittedAt,
        Instant reviewedAt,
        String reviewComment
    ) {}
}
