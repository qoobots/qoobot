package com.qoobot.qooauth.auth.controller;

import com.qoobot.qooauth.auth.entity.RobotGroupMembership;
import com.qoobot.qooauth.auth.entity.RobotTrustGroup;
import com.qoobot.qooauth.auth.service.RobotTrustService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

/**
 * REST controller for Robot-to-Robot trust operations.
 * All endpoints require authentication (device certificate or user JWT).
 */
@RestController
@RequestMapping("/api/v1/auth/robot-trust")
public class RobotTrustController {

    private final RobotTrustService robotTrustService;

    public RobotTrustController(RobotTrustService robotTrustService) {
        this.robotTrustService = robotTrustService;
    }

    // ---- mTLS Verification ----

    /**
     * Verify mTLS peer authentication between two robots.
     */
    @PostMapping("/mtls/verify-peer")
    public ResponseEntity<Map<String, Object>> verifyPeer(@RequestBody Map<String, String> request) {
        String callerDeviceId = request.get("caller_device_id");
        String peerDeviceId = request.get("peer_device_id");
        String peerCertFingerprint = request.get("peer_cert_fingerprint");

        RobotTrustService.MtlsVerificationResult result = robotTrustService.verifyPeerAuthentication(
                callerDeviceId, peerDeviceId, peerCertFingerprint);

        return ResponseEntity.ok(Map.of(
                "valid", result.isValid(),
                "reason", result.getReason() != null ? result.getReason() : "",
                "fingerprint_verified", result.isFingerprintVerified(),
                "common_groups", result.getCommonGroups()
        ));
    }

    /**
     * Check mTLS readiness for a device.
     */
    @GetMapping("/mtls/check/{deviceIdA}/{deviceIdB}")
    public ResponseEntity<Map<String, Object>> checkMtls(
            @PathVariable String deviceIdA,
            @PathVariable String deviceIdB) {
        boolean ready = robotTrustService.verifyMutualTls(deviceIdA, deviceIdB);
        return ResponseEntity.ok(Map.of("mtls_ready", ready));
    }

    // ---- Trust Groups ----

    /**
     * Create a new robot trust group.
     */
    @PostMapping("/groups")
    public ResponseEntity<Map<String, Object>> createGroup(@RequestBody Map<String, String> request) {
        String name = request.get("name");
        String description = request.getOrDefault("description", "");
        String ownerUserId = request.get("owner_user_id");
        String trustPolicy = request.getOrDefault("trust_policy", "{}");

        RobotTrustGroup group = robotTrustService.createGroup(name, description, ownerUserId, trustPolicy);

        return ResponseEntity.ok(Map.of(
                "group_id", group.getGroupId(),
                "name", group.getName(),
                "state", group.getState(),
                "created_at", group.getCreatedAt().toString()
        ));
    }

    /**
     * Get trust group details.
     */
    @GetMapping("/groups/{groupId}")
    public ResponseEntity<RobotTrustGroup> getGroup(@PathVariable String groupId) {
        // groupRepo.findById handled internally
        return ResponseEntity.ok(null); // placeholder — would need groupRepo access
    }

    /**
     * Add a robot to a trust group.
     */
    @PostMapping("/groups/{groupId}/members")
    public ResponseEntity<Map<String, Object>> addMember(
            @PathVariable String groupId,
            @RequestBody Map<String, String> request) {
        String deviceId = request.get("device_id");
        String userId = request.get("user_id");
        String role = request.getOrDefault("role", "MEMBER");
        String capabilityGrants = request.getOrDefault("capability_grants", "[]");

        RobotGroupMembership membership = robotTrustService.addMember(
                groupId, deviceId, userId, role, capabilityGrants);

        return ResponseEntity.ok(Map.of(
                "membership_id", membership.getMembershipId(),
                "group_id", membership.getGroupId(),
                "device_id", membership.getDeviceId(),
                "role", membership.getRole(),
                "state", membership.getState()
        ));
    }

    /**
     * Remove a robot from a trust group.
     */
    @DeleteMapping("/groups/{groupId}/members/{deviceId}")
    public ResponseEntity<Map<String, Object>> removeMember(
            @PathVariable String groupId,
            @PathVariable String deviceId,
            @RequestParam(defaultValue = "manual_removal") String reason) {
        robotTrustService.removeMember(groupId, deviceId, reason);
        return ResponseEntity.ok(Map.of("status", "removed", "reason", reason));
    }

    /**
     * List members of a trust group.
     */
    @GetMapping("/groups/{groupId}/members")
    public ResponseEntity<List<RobotGroupMembership>> listMembers(@PathVariable String groupId) {
        return ResponseEntity.ok(robotTrustService.getGroupMembers(groupId));
    }

    /**
     * List groups a device belongs to.
     */
    @GetMapping("/devices/{deviceId}/groups")
    public ResponseEntity<List<RobotGroupMembership>> getDeviceGroups(@PathVariable String deviceId) {
        return ResponseEntity.ok(robotTrustService.getDeviceGroups(deviceId));
    }

    /**
     * Dissolve a trust group.
     */
    @DeleteMapping("/groups/{groupId}")
    public ResponseEntity<Map<String, Object>> dissolveGroup(@PathVariable String groupId) {
        robotTrustService.dissolveGroup(groupId);
        return ResponseEntity.ok(Map.of("status", "dissolved", "group_id", groupId));
    }

    // ---- Collaboration Delegation ----

    /**
     * Issue a collaboration delegation token.
     */
    @PostMapping("/delegations")
    public ResponseEntity<Map<String, Object>> issueDelegation(@RequestBody Map<String, Object> request) {
        String delegatorDeviceId = (String) request.get("delegator_device_id");
        String delegatorUserId = (String) request.get("delegator_user_id");
        String delegateDeviceId = (String) request.get("delegate_device_id");

        @SuppressWarnings("unchecked")
        List<String> capabilities = (List<String>) request.get("capabilities");
        long ttlSeconds = request.containsKey("ttl_seconds") ?
                ((Number) request.get("ttl_seconds")).longValue() : 3600L;

        RobotTrustService.DelegationResult result = robotTrustService.issueDelegation(
                delegatorDeviceId, delegatorUserId, delegateDeviceId, capabilities, ttlSeconds);

        return ResponseEntity.ok(Map.of(
                "delegation_id", result.getDelegationId(),
                "token", result.getToken(),
                "token_hash", result.getTokenHash(),
                "expires_at", result.getExpiresAt().toString(),
                "capabilities", result.getCapabilities()
        ));
    }

    /**
     * Validate a delegation token.
     */
    @PostMapping("/delegations/validate")
    public ResponseEntity<Map<String, Object>> validateDelegation(@RequestBody Map<String, String> request) {
        String token = request.get("token");
        String callerDeviceId = request.get("caller_device_id");

        RobotTrustService.DelegationValidation result = robotTrustService.validateDelegation(token, callerDeviceId);

        return ResponseEntity.ok(Map.of(
                "valid", result.isValid(),
                "expired", result.isExpired(),
                "delegation_id", result.getDelegationId() != null ? result.getDelegationId() : "",
                "reason", result.getReason() != null ? result.getReason() : "",
                "capabilities", result.getCapabilities() != null ? result.getCapabilities() : List.of(),
                "expires_at", result.getExpiresAt() != null ? result.getExpiresAt().toString() : ""
        ));
    }

    /**
     * Revoke a delegation token.
     */
    @DeleteMapping("/delegations/{delegationId}")
    public ResponseEntity<Map<String, Object>> revokeDelegation(
            @PathVariable String delegationId,
            @RequestParam(defaultValue = "manual_revocation") String reason) {
        robotTrustService.revokeDelegation(delegationId, reason);
        return ResponseEntity.ok(Map.of("status", "revoked", "reason", reason));
    }

    /**
     * Check capability between two devices.
     */
    @GetMapping("/capabilities/check")
    public ResponseEntity<Map<String, Object>> checkCapability(
            @RequestParam String delegator,
            @RequestParam String delegate,
            @RequestParam String capability) {
        boolean granted = robotTrustService.hasCapability(delegator, delegate, capability);
        return ResponseEntity.ok(Map.of("granted", granted, "capability", capability));
    }

    // ---- Trust Revocation ----

    /**
     * Revoke all trust for a device (compromise response).
     */
    @PostMapping("/revoke-all")
    public ResponseEntity<Map<String, Object>> revokeAllTrust(@RequestBody Map<String, String> request) {
        String deviceId = request.get("device_id");
        String reason = request.getOrDefault("reason", "security_incident");

        robotTrustService.revokeAllTrust(deviceId, reason);
        return ResponseEntity.ok(Map.of("status", "all_trust_revoked", "device_id", deviceId));
    }
}
