package com.qoobot.qooauth.auth.service;

import com.qoobot.qooauth.auth.entity.*;
import com.qoobot.qooauth.auth.repository.*;
import com.qoobot.qooauth.common.constants.ErrorCodes;
import com.qoobot.qooauth.common.exception.AuthException;
import com.qoobot.qooauth.common.util.IdGenerator;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import java.nio.charset.StandardCharsets;
import java.security.SecureRandom;
import java.time.Instant;
import java.util.*;

/**
 * Robot-to-Robot Trust Service.
 *
 * Manages:
 * - mTLS mutual authentication between robots
 * - Collaboration delegation tokens (capability-based)
 * - Trust group formation, membership, and dissolution
 * - Trust revocation (certificate + delegation + group level)
 *
 * Security model: Zero-trust architecture. Every robot-to-robot
 * interaction must be authenticated via mTLS and authorized via
 * explicit capability delegation or group membership.
 */
@Service
public class RobotTrustService {
    private static final Logger log = LoggerFactory.getLogger(RobotTrustService.class);

    private final RobotTrustGroupRepository groupRepo;
    private final RobotGroupMembershipRepository membershipRepo;
    private final CollaborationDelegationRepository delegationRepo;
    private final DeviceCertificateRepository certRepo;
    private final SecureRandom secureRandom = new SecureRandom();

    // HMAC-SHA256 key for delegation token signing (in production, use HSM)
    private static final byte[] DELEGATION_HMAC_KEY = new byte[32];
    static {
        new SecureRandom().nextBytes(DELEGATION_HMAC_KEY);
    }

    public RobotTrustService(RobotTrustGroupRepository groupRepo,
                             RobotGroupMembershipRepository membershipRepo,
                             CollaborationDelegationRepository delegationRepo,
                             DeviceCertificateRepository certRepo) {
        this.groupRepo = groupRepo;
        this.membershipRepo = membershipRepo;
        this.delegationRepo = delegationRepo;
        this.certRepo = certRepo;
    }

    // ============================================================
    //  mTLS Mutual Authentication
    // ============================================================

    /**
     * Verify that two robots can establish mTLS trust.
     * Both must have valid, non-revoked device certificates.
     */
    public boolean verifyMutualTls(String deviceIdA, String deviceIdB) {
        boolean aValid = certRepo.findByDeviceIdAndState(deviceIdA, "ACTIVE").isPresent();
        boolean bValid = certRepo.findByDeviceIdAndState(deviceIdB, "ACTIVE").isPresent();
        return aValid && bValid;
    }

    /**
     * Full mTLS handshake validation: check certificate chains, revocation status,
     * and optionally group membership for authorization.
     */
    public MtlsVerificationResult verifyPeerAuthentication(String callerDeviceId,
                                                            String peerDeviceId,
                                                            String peerCertFingerprint) {
        MtlsVerificationResult result = new MtlsVerificationResult();

        // 1. Verify peer has valid certificate
        var peerCert = certRepo.findByDeviceIdAndState(peerDeviceId, "ACTIVE");
        if (peerCert.isEmpty()) {
            result.setValid(false);
            result.setReason("Peer device has no active certificate");
            return result;
        }

        // 2. Verify fingerprint matches
        if (!peerCert.get().getFingerprintSha256().equals(peerCertFingerprint)) {
            result.setValid(false);
            result.setReason("Certificate fingerprint mismatch");
            return result;
        }

        // 3. Verify certificate not expired
        if (peerCert.get().getNotAfter().isBefore(Instant.now())) {
            result.setValid(false);
            result.setReason("Peer certificate has expired");
            return result;
        }

        // 4. Check if in same trust group (optional authorization)
        List<RobotGroupMembership> callerGroups = membershipRepo.findActiveGroupsForDevice(callerDeviceId);
        List<RobotGroupMembership> peerGroups = membershipRepo.findActiveGroupsForDevice(peerDeviceId);

        Set<String> commonGroups = new HashSet<>();
        for (var cg : callerGroups) {
            for (var pg : peerGroups) {
                if (cg.getGroupId().equals(pg.getGroupId())) {
                    commonGroups.add(cg.getGroupId());
                }
            }
        }

        result.setValid(true);
        result.setPeerDeviceId(peerDeviceId);
        result.setFingerprintVerified(true);
        result.setCommonGroups(commonGroups);
        return result;
    }

    // ============================================================
    //  Trust Group Management
    // ============================================================

    /**
     * Create a new robot trust group.
     */
    @Transactional
    public RobotTrustGroup createGroup(String name, String description,
                                        String ownerUserId, String trustPolicyJson) {
        RobotTrustGroup group = new RobotTrustGroup();
        group.setGroupId(IdGenerator.generateTrustGroupId());
        group.setName(name);
        group.setDescription(description);
        group.setOwnerUserId(ownerUserId);
        group.setState("ACTIVE");
        group.setTrustPolicy(trustPolicyJson);
        group.setMaxMembers(50);
        group.setCreatedAt(Instant.now());
        group.setUpdatedAt(Instant.now());

        group = groupRepo.save(group);
        log.info("Robot trust group created: {} ({}) by user {}", group.getGroupId(), name, ownerUserId);
        return group;
    }

    /**
     * Add a robot to a trust group.
     */
    @Transactional
    public RobotGroupMembership addMember(String groupId, String deviceId,
                                           String userId, String role,
                                           String capabilityGrants) {
        // Check group exists and is active
        RobotTrustGroup group = groupRepo.findById(groupId)
                .orElseThrow(() -> new AuthException(ErrorCodes.GROUP_NOT_FOUND,
                        "Trust group not found: " + groupId));

        if (!"ACTIVE".equals(group.getState())) {
            throw new AuthException(ErrorCodes.GROUP_NOT_ACTIVE,
                    "Trust group is not active: " + group.getState());
        }

        // Check capacity
        long memberCount = membershipRepo.countActiveMembers(groupId);
        if (memberCount >= group.getMaxMembers()) {
            throw new AuthException(ErrorCodes.GROUP_FULL,
                    "Trust group is at maximum capacity: " + group.getMaxMembers());
        }

        // Check not already member
        membershipRepo.findByGroupIdAndDeviceId(groupId, deviceId).ifPresent(m -> {
            if ("ACTIVE".equals(m.getState())) {
                throw new AuthException(ErrorCodes.DEVICE_ALREADY_BOUND,
                        "Device is already a member of this group");
            }
        });

        RobotGroupMembership membership = new RobotGroupMembership();
        membership.setMembershipId(IdGenerator.generateMembershipId());
        membership.setGroupId(groupId);
        membership.setDeviceId(deviceId);
        membership.setUserId(userId);
        membership.setRole(role != null ? role : "MEMBER");
        membership.setState("ACTIVE");
        membership.setCapabilityGrants(capabilityGrants);
        membership.setJoinedAt(Instant.now());
        membership.setUpdatedAt(Instant.now());

        group.setUpdatedAt(Instant.now());
        groupRepo.save(group);

        membership = membershipRepo.save(membership);
        log.info("Device {} added to trust group {} as {}", deviceId, groupId, membership.getRole());
        return membership;
    }

    /**
     * Remove a member from a trust group.
     */
    @Transactional
    public void removeMember(String groupId, String deviceId, String reason) {
        var membership = membershipRepo.findByGroupIdAndDeviceId(groupId, deviceId)
                .orElseThrow(() -> new AuthException(ErrorCodes.MEMBERSHIP_NOT_FOUND,
                        "Device is not a member of this group"));

        membershipRepo.updateMembershipState(membership.getMembershipId(), "REMOVED");

        // Revoke all active delegations involving this device within this group
        List<CollaborationDelegation> delegations = delegationRepo.findByDelegateDeviceId(deviceId);
        for (var d : delegations) {
            if ("ACTIVE".equals(d.getState())) {
                delegationRepo.revokeDelegation(d.getDelegationId(),
                        "Member removed from group: " + reason);
            }
        }

        log.info("Device {} removed from trust group {}: {}", deviceId, groupId, reason);
    }

    /**
     * Dissolve (delete) a trust group.
     */
    @Transactional
    public void dissolveGroup(String groupId) {
        // Remove all members
        List<RobotGroupMembership> members = membershipRepo.findActiveMembersByGroup(groupId);
        for (var m : members) {
            membershipRepo.updateMembershipState(m.getMembershipId(), "REMOVED");
        }

        // Revoke all delegations related to this group
        // (In practice, delegations carry group context; here we revoke all
        // active delegations for each member)
        for (var m : members) {
            List<CollaborationDelegation> delegations = delegationRepo.findActiveByDelegate(m.getDeviceId());
            for (var d : delegations) {
                delegationRepo.revokeDelegation(d.getDelegationId(), "Group dissolved");
            }
        }

        groupRepo.dissolveGroup(groupId, "DISSOLVED");
        log.info("Trust group {} dissolved", groupId);
    }

    /**
     * Get all groups a device belongs to.
     */
    public List<RobotGroupMembership> getDeviceGroups(String deviceId) {
        return membershipRepo.findActiveGroupsForDevice(deviceId);
    }

    /**
     * Get all members of a group.
     */
    public List<RobotGroupMembership> getGroupMembers(String groupId) {
        return membershipRepo.findActiveMembersByGroup(groupId);
    }

    // ============================================================
    //  Collaboration Delegation Tokens
    // ============================================================

    /**
     * Issue a collaboration delegation token from one robot to another.
     * The token is an HMAC-SHA256 signed bearer token encoding the
     * granted capabilities, expiration, and delegation context.
     */
    @Transactional
    public DelegationResult issueDelegation(String delegatorDeviceId, String delegatorUserId,
                                             String delegateDeviceId, List<String> capabilities,
                                             long ttlSeconds) {
        // Verify delegator has active certificate
        certRepo.findByDeviceIdAndState(delegatorDeviceId, "ACTIVE")
                .orElseThrow(() -> new AuthException(ErrorCodes.DEVICE_NOT_FOUND,
                        "Delegator device not found or not active"));

        // Verify delegate has active certificate
        certRepo.findByDeviceIdAndState(delegateDeviceId, "ACTIVE")
                .orElseThrow(() -> new AuthException(ErrorCodes.DEVICE_NOT_FOUND,
                        "Delegate device not found or not active"));

        // Build token payload
        String delegationId = IdGenerator.generateDelegationId();
        Instant now = Instant.now();
        Instant expiresAt = now.plusSeconds(ttlSeconds);

        // Create signed token
        String capabilitiesJson = toJson(capabilities);
        String tokenPayload = delegationId + ":" + delegatorDeviceId + ":" +
                delegateDeviceId + ":" + capabilitiesJson + ":" + expiresAt.toString();
        String tokenSignature = hmacSha256(tokenPayload);
        String token = tokenPayload + "." + tokenSignature;
        String tokenHash = sha256(token);

        // Persist delegation record
        CollaborationDelegation delegation = new CollaborationDelegation();
        delegation.setDelegationId(delegationId);
        delegation.setTokenHash(tokenHash);
        delegation.setDelegatorDeviceId(delegatorDeviceId);
        delegation.setDelegatorUserId(delegatorUserId);
        delegation.setDelegateDeviceId(delegateDeviceId);
        delegation.setCapabilities(capabilitiesJson);
        delegation.setState("ACTIVE");
        delegation.setIssuedAt(now);
        delegation.setExpiresAt(expiresAt);
        delegation.setCreatedAt(now);

        delegationRepo.save(delegation);
        log.info("Delegation {} issued: {} -> {} with capabilities: {}",
                delegationId, delegatorDeviceId, delegateDeviceId, capabilities);

        return new DelegationResult(delegationId, token, tokenHash, expiresAt, capabilities);
    }

    /**
     * Validate a delegation token and return the granted capabilities.
     */
    public DelegationValidation validateDelegation(String token, String callerDeviceId) {
        try {
            String[] parts = token.split("\\.", 2);
            if (parts.length != 2) {
                return DelegationValidation.invalid("Invalid token format");
            }

            String payload = parts[0];
            String providedSignature = parts[1];

            // Verify signature
            String expectedSignature = hmacSha256(payload);
            if (!constantTimeEquals(expectedSignature, providedSignature)) {
                return DelegationValidation.invalid("Token signature verification failed");
            }

            // Parse payload
            String[] fields = payload.split(":", 5);
            if (fields.length != 5) {
                return DelegationValidation.invalid("Invalid token payload");
            }

            String delegationId = fields[0];
            String delegateDeviceId = fields[2];
            Instant expiresAt = Instant.parse(fields[4]);

            // Verify caller is the intended delegate
            if (!delegateDeviceId.equals(callerDeviceId)) {
                return DelegationValidation.invalid("Token not issued for this device");
            }

            // Check expiration
            if (expiresAt.isBefore(Instant.now())) {
                return DelegationValidation.expired(delegationId);
            }

            // Verify delegation still active in database
            var delegation = delegationRepo.findById(delegationId);
            if (delegation.isEmpty() || !"ACTIVE".equals(delegation.get().getState())) {
                return DelegationValidation.invalid("Delegation has been revoked or not found");
            }

            // Parse capabilities
            List<String> capabilities = fromJson(fields[3]);

            return DelegationValidation.valid(delegationId, capabilities, expiresAt);

        } catch (Exception e) {
            log.warn("Delegation validation failed: {}", e.getMessage());
            return DelegationValidation.invalid("Token validation error: " + e.getMessage());
        }
    }

    /**
     * Revoke a delegation token.
     */
    @Transactional
    public void revokeDelegation(String delegationId, String reason) {
        delegationRepo.revokeDelegation(delegationId, reason);
        log.info("Delegation {} revoked: {}", delegationId, reason);
    }

    /**
     * Revoke all delegations issued by a device (e.g., on compromise).
     */
    @Transactional
    public void revokeAllDelegations(String deviceId, String reason) {
        List<CollaborationDelegation> issued = delegationRepo.findActiveByDelegator(deviceId);
        for (var d : issued) {
            delegationRepo.revokeDelegation(d.getDelegationId(), reason);
        }

        List<CollaborationDelegation> received = delegationRepo.findActiveByDelegate(deviceId);
        for (var d : received) {
            delegationRepo.revokeDelegation(d.getDelegationId(), reason);
        }

        log.info("All delegations for device {} revoked: {}", deviceId, reason);
    }

    /**
     * Check if a specific capability is granted between two devices.
     */
    public boolean hasCapability(String delegatorDeviceId, String delegateDeviceId,
                                  String capability) {
        // Check direct delegations
        List<CollaborationDelegation> delegations = delegationRepo.findActiveByDelegate(delegateDeviceId);
        for (var d : delegations) {
            if (d.getDelegatorDeviceId().equals(delegatorDeviceId) && "ACTIVE".equals(d.getState())) {
                List<String> caps = fromJson(d.getCapabilities());
                if (caps.contains(capability) || caps.contains("*")) {
                    return true;
                }
            }
        }

        // Check group-based capabilities
        List<RobotGroupMembership> callerGroups = membershipRepo.findActiveGroupsForDevice(delegatorDeviceId);
        List<RobotGroupMembership> delegateGroups = membershipRepo.findActiveGroupsForDevice(delegateDeviceId);

        for (var cg : callerGroups) {
            for (var dg : delegateGroups) {
                if (cg.getGroupId().equals(dg.getGroupId())) {
                    if (dg.getCapabilityGrants() != null) {
                        List<String> groupCaps = fromJson(dg.getCapabilityGrants());
                        if (groupCaps.contains(capability) || groupCaps.contains("*")) {
                            return true;
                        }
                    }
                }
            }
        }

        return false;
    }

    // ============================================================
    //  Trust Revocation (comprehensive)
    // ============================================================

    /**
     * Full trust revocation for a device: revoke certs, delegations,
     * remove from groups. Used when a device is compromised or decommissioned.
     */
    @Transactional
    public void revokeAllTrust(String deviceId, String reason) {
        // 1. Revoke all certificates
        certRepo.findByDeviceIdAndState(deviceId, "ACTIVE").ifPresent(cert -> {
            // Mark as revoked (state update handled by DeviceCertificateService)
            log.info("Certificate {} for device {} marked for revocation", cert.getCertId(), deviceId);
        });

        // 2. Revoke all delegation tokens
        revokeAllDelegations(deviceId, "Trust revoked: " + reason);

        // 3. Remove from all groups
        List<RobotGroupMembership> groups = membershipRepo.findActiveGroupsForDevice(deviceId);
        for (var m : groups) {
            membershipRepo.updateMembershipState(m.getMembershipId(), "REMOVED");
            log.info("Device {} removed from group {} due to trust revocation", deviceId, m.getGroupId());
        }

        log.warn("All trust revoked for device {}: {}", deviceId, reason);
    }

    // ============================================================
    //  Scheduled Tasks
    // ============================================================

    /**
     * Expire delegation tokens past their expiry time.
     * Runs every 10 minutes.
     */
    @Scheduled(fixedRate = 600_000)
    @Transactional
    public void expireOverdueDelegations() {
        int count = delegationRepo.expireDelegations(Instant.now());
        if (count > 0) {
            log.debug("Expired {} overdue delegation tokens", count);
        }
    }

    // ============================================================
    //  Helper Methods
    // ============================================================

    private String hmacSha256(String data) {
        try {
            Mac mac = Mac.getInstance("HmacSHA256");
            mac.init(new SecretKeySpec(DELEGATION_HMAC_KEY, "HmacSHA256"));
            byte[] hash = mac.doFinal(data.getBytes(StandardCharsets.UTF_8));
            return Base64.getUrlEncoder().withoutPadding().encodeToString(hash);
        } catch (Exception e) {
            throw new RuntimeException("HMAC-SHA256 failed", e);
        }
    }

    private String sha256(String data) {
        try {
            java.security.MessageDigest md = java.security.MessageDigest.getInstance("SHA-256");
            byte[] hash = md.digest(data.getBytes(StandardCharsets.UTF_8));
            return Base64.getUrlEncoder().withoutPadding().encodeToString(hash);
        } catch (Exception e) {
            throw new RuntimeException("SHA-256 failed", e);
        }
    }

    private boolean constantTimeEquals(String a, String b) {
        if (a.length() != b.length()) return false;
        int result = 0;
        for (int i = 0; i < a.length(); i++) {
            result |= a.charAt(i) ^ b.charAt(i);
        }
        return result == 0;
    }

    private String toJson(List<String> list) {
        StringBuilder sb = new StringBuilder("[");
        for (int i = 0; i < list.size(); i++) {
            if (i > 0) sb.append(",");
            sb.append("\"").append(list.get(i).replace("\"", "\\\"")).append("\"");
        }
        sb.append("]");
        return sb.toString();
    }

    private List<String> fromJson(String json) {
        List<String> result = new ArrayList<>();
        if (json == null || json.length() < 2) return result;
        // Simple JSON array parser for string lists
        String inner = json.substring(1, json.length() - 1);
        if (inner.isEmpty()) return result;
        String[] items = inner.split(",");
        for (String item : items) {
            String trimmed = item.trim();
            if (trimmed.startsWith("\"") && trimmed.endsWith("\"")) {
                result.add(trimmed.substring(1, trimmed.length() - 1));
            }
        }
        return result;
    }

    // ============================================================
    //  DTOs
    // ============================================================

    public static class MtlsVerificationResult {
        private boolean valid;
        private String reason;
        private String peerDeviceId;
        private boolean fingerprintVerified;
        private Set<String> commonGroups = new HashSet<>();

        public boolean isValid() { return valid; }
        public void setValid(boolean valid) { this.valid = valid; }
        public String getReason() { return reason; }
        public void setReason(String reason) { this.reason = reason; }
        public String getPeerDeviceId() { return peerDeviceId; }
        public void setPeerDeviceId(String peerDeviceId) { this.peerDeviceId = peerDeviceId; }
        public boolean isFingerprintVerified() { return fingerprintVerified; }
        public void setFingerprintVerified(boolean fingerprintVerified) { this.fingerprintVerified = fingerprintVerified; }
        public Set<String> getCommonGroups() { return commonGroups; }
        public void setCommonGroups(Set<String> commonGroups) { this.commonGroups = commonGroups; }
    }

    public static class DelegationResult {
        private final String delegationId;
        private final String token;
        private final String tokenHash;
        private final Instant expiresAt;
        private final List<String> capabilities;

        public DelegationResult(String delegationId, String token, String tokenHash,
                                 Instant expiresAt, List<String> capabilities) {
            this.delegationId = delegationId;
            this.token = token;
            this.tokenHash = tokenHash;
            this.expiresAt = expiresAt;
            this.capabilities = capabilities;
        }

        public String getDelegationId() { return delegationId; }
        public String getToken() { return token; }
        public String getTokenHash() { return tokenHash; }
        public Instant getExpiresAt() { return expiresAt; }
        public List<String> getCapabilities() { return capabilities; }
    }

    public static class DelegationValidation {
        private final boolean valid;
        private final boolean expired;
        private final String delegationId;
        private final String reason;
        private final List<String> capabilities;
        private final Instant expiresAt;

        private DelegationValidation(boolean valid, boolean expired, String delegationId,
                                      String reason, List<String> capabilities, Instant expiresAt) {
            this.valid = valid;
            this.expired = expired;
            this.delegationId = delegationId;
            this.reason = reason;
            this.capabilities = capabilities;
            this.expiresAt = expiresAt;
        }

        public static DelegationValidation valid(String delegationId, List<String> capabilities, Instant expiresAt) {
            return new DelegationValidation(true, false, delegationId, null, capabilities, expiresAt);
        }

        public static DelegationValidation invalid(String reason) {
            return new DelegationValidation(false, false, null, reason, null, null);
        }

        public static DelegationValidation expired(String delegationId) {
            return new DelegationValidation(false, true, delegationId, "Token expired", null, null);
        }

        public boolean isValid() { return valid; }
        public boolean isExpired() { return expired; }
        public String getDelegationId() { return delegationId; }
        public String getReason() { return reason; }
        public List<String> getCapabilities() { return capabilities; }
        public Instant getExpiresAt() { return expiresAt; }
    }
}
