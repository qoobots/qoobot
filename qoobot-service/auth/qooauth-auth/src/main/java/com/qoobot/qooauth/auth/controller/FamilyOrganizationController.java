package com.qoobot.qooauth.auth.controller;

import com.qoobot.qooauth.auth.entity.FamilyGroup;
import com.qoobot.qooauth.auth.entity.FamilyMember;
import com.qoobot.qooauth.auth.entity.OrganizationProfile;
import com.qoobot.qooauth.auth.service.FamilyOrganizationService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.*;

/**
 * REST controller for Family Sharing and Organization Management.
 */
@RestController
@RequestMapping("/api/v1/auth")
public class FamilyOrganizationController {

    private final FamilyOrganizationService familyOrgService;

    public FamilyOrganizationController(FamilyOrganizationService familyOrgService) {
        this.familyOrgService = familyOrgService;
    }

    // ---- Family Sharing ----

    @PostMapping("/families")
    public ResponseEntity<Map<String, Object>> createFamily(@RequestBody Map<String, String> request) {
        String name = request.get("name");
        String organizerUserId = request.get("organizer_user_id");
        String sharingSettings = request.get("sharing_settings");

        FamilyGroup family = familyOrgService.createFamily(name, organizerUserId, sharingSettings);

        return ResponseEntity.ok(Map.of(
                "family_id", family.getFamilyId(),
                "name", family.getName(),
                "organizer_user_id", family.getOrganizerUserId(),
                "state", family.getState(),
                "max_members", family.getMaxMembers(),
                "created_at", family.getCreatedAt().toString()
        ));
    }

    @PostMapping("/families/{familyId}/members")
    public ResponseEntity<Map<String, Object>> addMember(
            @PathVariable String familyId,
            @RequestBody Map<String, String> request) {
        String userId = request.get("user_id");
        String role = request.getOrDefault("role", "ADULT");
        String parentalControls = request.get("parental_controls");

        FamilyMember member = familyOrgService.addMember(familyId, userId, role, parentalControls);

        return ResponseEntity.ok(Map.of(
                "member_id", member.getMemberId(),
                "family_id", member.getFamilyId(),
                "user_id", member.getUserId(),
                "role", member.getRole(),
                "state", member.getState()
        ));
    }

    @GetMapping("/families/{familyId}/members")
    public ResponseEntity<List<Map<String, Object>>> getMembers(@PathVariable String familyId) {
        List<FamilyMember> members = familyOrgService.getFamilyMembers(familyId);
        List<Map<String, Object>> result = new ArrayList<>();
        for (var m : members) {
            result.add(Map.of(
                    "member_id", m.getMemberId(),
                    "user_id", m.getUserId(),
                    "role", m.getRole(),
                    "state", m.getState(),
                    "parental_controls", m.getParentalControls() != null ? m.getParentalControls() : "{}",
                    "joined_at", m.getJoinedAt().toString()
            ));
        }
        return ResponseEntity.ok(result);
    }

    // ---- Parental Controls ----

    @PutMapping("/families/{familyId}/parental-controls/{userId}")
    public ResponseEntity<Map<String, Object>> setParentalControls(
            @PathVariable String familyId,
            @PathVariable String userId,
            @RequestBody Map<String, String> request) {
        String controls = request.get("controls");
        FamilyMember member = familyOrgService.setParentalControls(familyId, userId, controls);

        return ResponseEntity.ok(Map.of(
                "user_id", member.getUserId(),
                "parental_controls", member.getParentalControls(),
                "updated_at", member.getUpdatedAt().toString()
        ));
    }

    @GetMapping("/families/{familyId}/parental-controls/check-purchase")
    public ResponseEntity<Map<String, Object>> checkPurchase(
            @PathVariable String familyId,
            @RequestParam String childUserId,
            @RequestParam String item,
            @RequestParam(defaultValue = "0") double amount) {
        boolean approved = familyOrgService.checkPurchaseApproval(familyId, childUserId, item, amount);
        return ResponseEntity.ok(Map.of(
                "approved", approved,
                "requires_parent_approval", !approved
        ));
    }

    @GetMapping("/families/{familyId}/parental-controls/check-screen-time")
    public ResponseEntity<Map<String, Object>> checkScreenTime(
            @PathVariable String familyId,
            @RequestParam String childUserId,
            @RequestParam int currentMinutes) {
        boolean allowed = familyOrgService.checkScreenTime(familyId, childUserId, currentMinutes);
        return ResponseEntity.ok(Map.of(
                "allowed", allowed,
                "current_minutes", currentMinutes
        ));
    }

    // ---- Organization Management ----

    @PostMapping("/organizations")
    public ResponseEntity<Map<String, Object>> createOrganization(@RequestBody Map<String, String> request) {
        String name = request.get("name");
        String adminUserId = request.get("admin_user_id");
        String mdmConfig = request.get("mdm_config");

        OrganizationProfile org = familyOrgService.createOrganization(name, adminUserId, mdmConfig);

        return ResponseEntity.ok(Map.of(
                "org_id", org.getOrgId(),
                "name", org.getName(),
                "admin_user_id", org.getAdminUserId(),
                "state", org.getState(),
                "max_devices", org.getMaxDevices(),
                "created_at", org.getCreatedAt().toString()
        ));
    }

    @GetMapping("/organizations/{orgId}")
    public ResponseEntity<Map<String, Object>> getOrganization(@PathVariable String orgId) {
        OrganizationProfile org = familyOrgService.getOrganization(orgId);
        if (org == null) {
            return ResponseEntity.ok(Map.of("org_id", orgId, "found", false));
        }
        return ResponseEntity.ok(Map.of(
                "org_id", org.getOrgId(),
                "name", org.getName(),
                "admin_user_id", org.getAdminUserId(),
                "state", org.getState(),
                "mdm_config", org.getMdmConfig(),
                "max_devices", org.getMaxDevices()
        ));
    }

    @PutMapping("/organizations/{orgId}/mdm-config")
    public ResponseEntity<Map<String, Object>> updateMdmConfig(
            @PathVariable String orgId,
            @RequestBody Map<String, String> request) {
        String mdmConfig = request.get("mdm_config");
        OrganizationProfile org = familyOrgService.updateMdmConfig(orgId, mdmConfig);

        return ResponseEntity.ok(Map.of(
                "org_id", org.getOrgId(),
                "mdm_config", org.getMdmConfig(),
                "updated_at", org.getUpdatedAt().toString()
        ));
    }

    @PostMapping("/organizations/{orgId}/devices/{deviceId}/apply-policies")
    public ResponseEntity<Map<String, Object>> applyMdmPolicies(
            @PathVariable String orgId,
            @PathVariable String deviceId) {
        Map<String, Object> policies = familyOrgService.applyMdmPolicies(orgId, deviceId);
        return ResponseEntity.ok(policies);
    }

    @PostMapping("/organizations/{orgId}/devices/{deviceId}/compliance")
    public ResponseEntity<Map<String, Object>> checkCompliance(
            @PathVariable String orgId,
            @PathVariable String deviceId,
            @RequestBody Map<String, String> deviceInfo) {
        FamilyOrganizationService.ComplianceReport report =
                familyOrgService.checkCompliance(orgId, deviceId, deviceInfo);
        return ResponseEntity.ok(report.toMap());
    }
}
