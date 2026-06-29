package com.qoobot.qooauth.auth.rbac;

import com.qoobot.qooauth.common.dto.ApiResponse;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.Instant;
import java.util.List;
import java.util.Map;

/**
 * RBAC management endpoints.
 * Role CRUD, user-role assignment, permission checking.
 */
@RestController
@RequestMapping("/api/v1/rbac")
public class RbacController {

    private final RbacService rbacService;

    public RbacController(RbacService rbacService) {
        this.rbacService = rbacService;
    }

    // ==================== Roles ====================

    /**
     * List all roles.
     */
    @GetMapping("/roles")
    public ResponseEntity<ApiResponse<List<Map<String, Object>>>> listRoles() {
        return ResponseEntity.ok(ApiResponse.ok(rbacService.listRoles()));
    }

    /**
     * Get role detail with permissions.
     */
    @GetMapping("/roles/{roleId}")
    public ResponseEntity<ApiResponse<Map<String, Object>>> getRole(@PathVariable String roleId) {
        return ResponseEntity.ok(ApiResponse.ok(rbacService.getRoleDetail(roleId)));
    }

    // ==================== User Role Assignments ====================

    /**
     * Get roles assigned to a user.
     */
    @GetMapping("/users/{userId}/roles")
    public ResponseEntity<ApiResponse<List<Map<String, Object>>>> getUserRoles(
            @PathVariable String userId) {
        return ResponseEntity.ok(ApiResponse.ok(rbacService.getUserRoles(userId)));
    }

    /**
     * Get my roles (current user).
     */
    @GetMapping("/me/roles")
    public ResponseEntity<ApiResponse<List<Map<String, Object>>>> getMyRoles(
            @RequestAttribute("userId") String userId) {
        return ResponseEntity.ok(ApiResponse.ok(rbacService.getUserRoles(userId)));
    }

    /**
     * Assign a role to a user.
     */
    @PostMapping("/users/{userId}/roles")
    public ResponseEntity<ApiResponse<Map<String, Object>>> assignRole(
            @RequestAttribute("userId") String grantedBy,
            @PathVariable String userId,
            @RequestBody Map<String, String> body) {
        Map<String, Object> result = rbacService.assignRole(
                userId,
                body.get("role_id"),
                grantedBy,
                body.get("scope_type"),
                body.get("scope_id"),
                body.containsKey("expires_at") ? Instant.parse(body.get("expires_at")) : null
        );
        return ResponseEntity.status(HttpStatus.CREATED).body(ApiResponse.ok(result));
    }

    /**
     * Revoke a role from a user.
     */
    @DeleteMapping("/users/{userId}/roles/{roleId}")
    public ResponseEntity<ApiResponse<Void>> revokeRole(
            @RequestAttribute("userId") String adminId,
            @PathVariable String userId,
            @PathVariable String roleId) {
        rbacService.revokeRole(userId, roleId);
        return ResponseEntity.ok(ApiResponse.ok(null));
    }

    // ==================== Permissions ====================

    /**
     * Get all effective permissions for current user.
     */
    @GetMapping("/me/permissions")
    public ResponseEntity<ApiResponse<List<Map<String, Object>>>> getMyPermissions(
            @RequestAttribute("userId") String userId) {
        return ResponseEntity.ok(ApiResponse.ok(rbacService.getUserPermissions(userId)));
    }

    /**
     * Check if current user has a specific permission.
     */
    @PostMapping("/check")
    public ResponseEntity<ApiResponse<Map<String, Object>>> checkPermission(
            @RequestAttribute("userId") String userId,
            @RequestBody Map<String, String> body) {
        boolean allowed = rbacService.hasPermission(
                userId,
                body.get("permission_id"),
                body.get("resource_type"),
                body.get("resource_id"),
                body.get("action")
        );
        Map<String, Object> result = Map.of(
                "allowed", allowed,
                "permission_id", body.getOrDefault("permission_id", ""),
                "resource_type", body.getOrDefault("resource_type", "")
        );
        return ResponseEntity.ok(ApiResponse.ok(result));
    }

    // ==================== Access History ====================

    /**
     * Get access decision history for a user.
     */
    @GetMapping("/users/{userId}/access-history")
    public ResponseEntity<ApiResponse<List<AccessDecisionEntity>>> getAccessHistory(
            @PathVariable String userId) {
        return ResponseEntity.ok(ApiResponse.ok(rbacService.getAccessHistory(userId)));
    }

    /**
     * Get my access history.
     */
    @GetMapping("/me/access-history")
    public ResponseEntity<ApiResponse<List<AccessDecisionEntity>>> getMyAccessHistory(
            @RequestAttribute("userId") String userId) {
        return ResponseEntity.ok(ApiResponse.ok(rbacService.getAccessHistory(userId)));
    }
}
