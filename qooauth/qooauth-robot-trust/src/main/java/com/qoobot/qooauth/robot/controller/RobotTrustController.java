package com.qoobot.qooauth.robot.controller;

import com.qoobot.qooauth.robot.dto.CollaborationAuthRequest;
import com.qoobot.qooauth.robot.entity.CollaborationToken;
import com.qoobot.qooauth.robot.entity.RobotTrustGroup;
import com.qoobot.qooauth.robot.service.CollaborationAuthService;
import com.qoobot.qooauth.robot.service.GroupTrustService;
import com.qoobot.qooauth.robot.service.MTlsService;
import com.qoobot.qooauth.robot.service.TrustRevocationService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.security.Principal;
import java.util.List;
import java.util.Map;
import java.util.Optional;

@RestController
@RequestMapping("/api/v1/robot-trust")
@RequiredArgsConstructor
public class RobotTrustController {

    private final MTlsService mTlsService;
    private final CollaborationAuthService collaborationAuthService;
    private final GroupTrustService groupTrustService;
    private final TrustRevocationService trustRevocationService;

    // ---- mTLS endpoints ----

    /**
     * Verify mTLS certificate for a device.
     */
    @PostMapping("/mTLS/verify")
    public ResponseEntity<Map<String, Object>> verifyMTls(
            @RequestBody Map<String, String> request,
            Principal principal) {
        String deviceId = principal.getName();
        String peerDeviceId = request.get("peer_device_id");

        boolean hasSharedTrust = mTlsService.verifyGroupTrust(deviceId, peerDeviceId);

        return ResponseEntity.ok(Map.of(
            "verified", hasSharedTrust,
            "device_id", deviceId,
            "peer_device_id", peerDeviceId
        ));
    }

    // ---- Collaboration token endpoints ----

    /**
     * Generate a new collaboration delegation token.
     */
    @PostMapping("/collaboration/token")
    public ResponseEntity<Map<String, Object>> generateToken(
            @Valid @RequestBody CollaborationAuthRequest request,
            Principal principal) {
        // Ensure issuer matches authenticated device
        if (!principal.getName().equals(request.getIssuerDeviceId())) {
            return ResponseEntity.status(HttpStatus.FORBIDDEN).build();
        }

        String rawToken = collaborationAuthService.generateToken(request);
        return ResponseEntity.status(HttpStatus.CREATED).body(Map.of(
            "token", rawToken,
            "expires_at", request.getExpiresAt().toString()
        ));
    }

    /**
     * Validate a collaboration delegation token.
     */
    @PostMapping("/collaboration/validate")
    public ResponseEntity<Map<String, Object>> validateToken(
            @RequestBody Map<String, String> request) {
        String rawToken = request.get("token");
        String issuerDeviceId = request.get("issuer_device_id");
        String recipientDeviceId = request.get("recipient_device_id");

        Optional<CollaborationToken> validated = collaborationAuthService.validateToken(
            rawToken, issuerDeviceId, recipientDeviceId);

        if (validated.isPresent()) {
            CollaborationToken token = validated.get();
            return ResponseEntity.ok(Map.of(
                "valid", true,
                "token_id", token.getTokenId(),
                "capabilities", token.getCapabilities(),
                "expires_at", token.getExpiresAt().toString()
            ));
        } else {
            return ResponseEntity.ok(Map.of("valid", false));
        }
    }

    // ---- Group management endpoints ----

    /**
     * Create a new trust group.
     */
    @PostMapping("/groups")
    public ResponseEntity<RobotTrustGroup> createGroup(
            @RequestBody Map<String, Object> request,
            Principal principal) {
        String name = (String) request.get("name");
        @SuppressWarnings("unchecked")
        Map<String, Object> policy = (Map<String, Object>) request.get("trust_policy");

        RobotTrustGroup group = groupTrustService.createGroup(name, principal.getName(), policy);
        return ResponseEntity.status(HttpStatus.CREATED).body(group);
    }

    /**
     * List trust groups for the authenticated device.
     */
    @GetMapping("/groups")
    public ResponseEntity<List<RobotTrustGroup>> listGroups(Principal principal) {
        List<RobotTrustGroup> groups = groupTrustService.getGroupsForDevice(principal.getName());
        return ResponseEntity.ok(groups);
    }

    /**
     * Add a member to a trust group.
     */
    @PostMapping("/groups/{groupId}/members")
    public ResponseEntity<Map<String, String>> addMember(
            @PathVariable String groupId,
            @RequestBody Map<String, String> request,
            Principal principal) {
        String deviceId = request.get("device_id");
        groupTrustService.addMember(groupId, deviceId, principal.getName());
        return ResponseEntity.ok(Map.of("status", "added", "device_id", deviceId, "group_id", groupId));
    }

    /**
     * Revoke trust for a device within a group (full-chain revocation).
     */
    @DeleteMapping("/groups/{groupId}/revoke")
    public ResponseEntity<Map<String, String>> revokeGroupTrust(
            @PathVariable String groupId,
            @RequestBody Map<String, String> request,
            Principal principal) {
        String deviceId = request.get("device_id");
        trustRevocationService.revokeDeviceTrust(groupId, deviceId, principal.getName());
        return ResponseEntity.ok(Map.of(
            "status", "revoked",
            "device_id", deviceId,
            "group_id", groupId
        ));
    }
}
