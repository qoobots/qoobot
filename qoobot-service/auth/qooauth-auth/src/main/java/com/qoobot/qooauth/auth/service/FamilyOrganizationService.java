package com.qoobot.qooauth.auth.service;

import com.qoobot.qooauth.auth.entity.*;
import com.qoobot.qooauth.common.constants.ErrorCodes;
import com.qoobot.qooauth.common.exception.AuthException;
import com.qoobot.qooauth.common.util.IdGenerator;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Family Sharing & Organization Management Service.
 *
 * Provides:
 * - Family groups (similar to Apple Family Sharing)
 * - Parental controls for child accounts
 * - Organization management for enterprise/team use
 * - MDM (Mobile Device Management) integration
 */
@Service
public class FamilyOrganizationService {
    private static final Logger log = LoggerFactory.getLogger(FamilyOrganizationService.class);

    // In-memory stores (production would use JPA repositories)
    private final ConcurrentHashMap<String, FamilyGroup> families = new ConcurrentHashMap<>();
    private final ConcurrentHashMap<String, List<FamilyMember>> familyMembers = new ConcurrentHashMap<>();
    private final ConcurrentHashMap<String, OrganizationProfile> organizations = new ConcurrentHashMap<>();

    // ============================================================
    //  Family Sharing
    // ============================================================

    @Transactional
    public FamilyGroup createFamily(String name, String organizerUserId, String sharingSettings) {
        FamilyGroup family = new FamilyGroup();
        family.setFamilyId(IdGenerator.generateUserId().replace("uid_", "fam_"));
        family.setName(name);
        family.setOrganizerUserId(organizerUserId);
        family.setState("ACTIVE");
        family.setMaxMembers(6);
        family.setSharingSettings(sharingSettings != null ? sharingSettings :
                "{\"share_purchases\":true,\"share_subscriptions\":true," +
                "\"share_location\":true,\"share_device_access\":false}");
        family.setCreatedAt(Instant.now());
        family.setUpdatedAt(Instant.now());

        families.put(family.getFamilyId(), family);

        // Add organizer as first member
        addMember(family.getFamilyId(), organizerUserId, "ORGANIZER", null);

        log.info("Family group {} created by user {}", family.getFamilyId(), organizerUserId);
        return family;
    }

    public FamilyMember addMember(String familyId, String userId, String role,
                                    String parentalControls) {
        FamilyGroup family = families.get(familyId);
        if (family == null) {
            throw new AuthException(ErrorCodes.GROUP_NOT_FOUND, "Family not found: " + familyId);
        }

        List<FamilyMember> members = familyMembers.computeIfAbsent(familyId, k -> new ArrayList<>());
        if (members.size() >= family.getMaxMembers()) {
            throw new AuthException(ErrorCodes.GROUP_FULL, "Family is full");
        }

        FamilyMember member = new FamilyMember();
        member.setMemberId(IdGenerator.generateMembershipId());
        member.setFamilyId(familyId);
        member.setUserId(userId);
        member.setRole(role != null ? role : "ADULT");
        member.setState("ACTIVE");
        member.setParentalControls(parentalControls);
        member.setJoinedAt(Instant.now());
        member.setUpdatedAt(Instant.now());

        members.add(member);
        family.setUpdatedAt(Instant.now());

        log.info("User {} added to family {} as {}", userId, familyId, member.getRole());
        return member;
    }

    public List<FamilyMember> getFamilyMembers(String familyId) {
        return familyMembers.getOrDefault(familyId, List.of());
    }

    // ============================================================
    //  Parental Controls
    // ============================================================

    public FamilyMember setParentalControls(String familyId, String userId,
                                              String controlsJson) {
        List<FamilyMember> members = familyMembers.get(familyId);
        if (members == null) {
            throw new AuthException(ErrorCodes.GROUP_NOT_FOUND, "Family not found");
        }

        for (FamilyMember member : members) {
            if (member.getUserId().equals(userId) && "CHILD".equals(member.getRole())) {
                member.setParentalControls(controlsJson);
                member.setUpdatedAt(Instant.now());
                log.info("Parental controls updated for child {} in family {}", userId, familyId);
                return member;
            }
        }
        throw new AuthException(ErrorCodes.MEMBERSHIP_NOT_FOUND, "Child member not found");
    }

    public boolean checkPurchaseApproval(String familyId, String childUserId,
                                           String purchaseItem, double amount) {
        List<FamilyMember> members = familyMembers.get(familyId);
        if (members == null) return false;

        for (FamilyMember member : members) {
            if (member.getUserId().equals(childUserId) && "CHILD".equals(member.getRole())) {
                if (member.getParentalControls() != null &&
                        member.getParentalControls().contains("\"purchase_approval_required\":true")) {
                    log.info("Purchase approval required for child {}: {} (${})",
                            childUserId, purchaseItem, amount);
                    return false; // Requires approval
                }
                return true; // No approval needed
            }
        }
        return false; // Not a child member
    }

    public boolean checkScreenTime(String familyId, String childUserId, int currentMinutes) {
        List<FamilyMember> members = familyMembers.get(familyId);
        if (members == null) return true;

        for (FamilyMember member : members) {
            if (member.getUserId().equals(childUserId) && "CHILD".equals(member.getRole())) {
                if (member.getParentalControls() != null) {
                    // Simple check: look for screen_time_limit_minutes in controls JSON
                    String controls = member.getParentalControls();
                    if (controls.contains("\"screen_time_limit_minutes\"")) {
                        int idx = controls.indexOf("\"screen_time_limit_minutes\":");
                        if (idx >= 0) {
                            String limitStr = controls.substring(idx + 29);
                            int commaIdx = limitStr.indexOf(',');
                            int braceIdx = limitStr.indexOf('}');
                            int endIdx = Math.min(commaIdx > 0 ? commaIdx : Integer.MAX_VALUE,
                                    braceIdx > 0 ? braceIdx : Integer.MAX_VALUE);
                            if (endIdx < Integer.MAX_VALUE) {
                                limitStr = limitStr.substring(0, endIdx).trim();
                                try {
                                    int limit = Integer.parseInt(limitStr);
                                    return currentMinutes <= limit;
                                } catch (NumberFormatException ignored) {}
                            }
                        }
                    }
                }
                return true;
            }
        }
        return true;
    }

    // ============================================================
    //  Organization Management
    // ============================================================

    @Transactional
    public OrganizationProfile createOrganization(String name, String adminUserId,
                                                    String mdmConfig) {
        OrganizationProfile org = new OrganizationProfile();
        org.setOrgId(IdGenerator.generateUserId().replace("uid_", "org_"));
        org.setName(name);
        org.setAdminUserId(adminUserId);
        org.setState("ACTIVE");
        org.setMdmConfig(mdmConfig != null ? mdmConfig :
                "{\"enforce_encryption\":true,\"min_os_version\":\"1.0.0\"}");
        org.setMaxDevices(100);
        org.setCreatedAt(Instant.now());
        org.setUpdatedAt(Instant.now());

        organizations.put(org.getOrgId(), org);
        log.info("Organization {} created by admin {}", org.getOrgId(), adminUserId);
        return org;
    }

    public OrganizationProfile getOrganization(String orgId) {
        return organizations.get(orgId);
    }

    public OrganizationProfile updateMdmConfig(String orgId, String mdmConfig) {
        OrganizationProfile org = organizations.get(orgId);
        if (org == null) {
            throw new AuthException(ErrorCodes.GROUP_NOT_FOUND, "Organization not found");
        }
        org.setMdmConfig(mdmConfig);
        org.setUpdatedAt(Instant.now());
        log.info("MDM config updated for organization {}", orgId);
        return org;
    }

    /**
     * Apply MDM policies to a device.
     */
    public Map<String, Object> applyMdmPolicies(String orgId, String deviceId) {
        OrganizationProfile org = organizations.get(orgId);
        if (org == null) {
            throw new AuthException(ErrorCodes.GROUP_NOT_FOUND, "Organization not found");
        }

        // Parse MDM config and return applicable policies
        Map<String, Object> policies = new LinkedHashMap<>();
        policies.put("org_id", orgId);
        policies.put("org_name", org.getName());
        policies.put("enforce_encryption", true);
        policies.put("min_os_version", "1.0.0");
        policies.put("remote_wipe_enabled", true);
        policies.put("device_compliance_required", true);
        policies.put("applied_at", Instant.now().toString());

        log.info("MDM policies applied to device {} for org {}", deviceId, orgId);
        return policies;
    }

    /**
     * Check device compliance against organization policies.
     */
    public ComplianceReport checkCompliance(String orgId, String deviceId,
                                              Map<String, String> deviceInfo) {
        OrganizationProfile org = organizations.get(orgId);
        ComplianceReport report = new ComplianceReport();
        report.deviceId = deviceId;
        report.orgId = orgId;
        report.violations = new ArrayList<>();
        report.compliant = true;

        if (org != null && org.getMdmConfig() != null) {
            String config = org.getMdmConfig();

            // Check OS version
            if (config.contains("\"min_os_version\"")) {
                String deviceVersion = deviceInfo.getOrDefault("os_version", "0.0.0");
                String minVersion = "1.0.0"; // Extract from config in production
                if (compareVersions(deviceVersion, minVersion) < 0) {
                    report.violations.add("OS version " + deviceVersion +
                            " below minimum " + minVersion);
                    report.compliant = false;
                }
            }

            // Check encryption
            if (config.contains("\"enforce_encryption\":true")) {
                if (!"true".equals(deviceInfo.get("encryption_enabled"))) {
                    report.violations.add("Device encryption not enabled");
                    report.compliant = false;
                }
            }
        }

        report.checkedAt = Instant.now();
        return report;
    }

    // ============================================================
    //  Helper Methods
    // ============================================================

    private int compareVersions(String v1, String v2) {
        String[] parts1 = v1.split("\\.");
        String[] parts2 = v2.split("\\.");
        int len = Math.max(parts1.length, parts2.length);
        for (int i = 0; i < len; i++) {
            int p1 = i < parts1.length ? Integer.parseInt(parts1[i]) : 0;
            int p2 = i < parts2.length ? Integer.parseInt(parts2[i]) : 0;
            if (p1 != p2) return p1 - p2;
        }
        return 0;
    }

    // ============================================================
    //  DTOs
    // ============================================================

    public static class ComplianceReport {
        public String deviceId;
        public String orgId;
        public boolean compliant;
        public List<String> violations;
        public Instant checkedAt;

        public Map<String, Object> toMap() {
            return Map.of(
                    "device_id", deviceId,
                    "org_id", orgId,
                    "compliant", compliant,
                    "violations", violations != null ? violations : List.of(),
                    "checked_at", checkedAt.toString()
            );
        }
    }
}
