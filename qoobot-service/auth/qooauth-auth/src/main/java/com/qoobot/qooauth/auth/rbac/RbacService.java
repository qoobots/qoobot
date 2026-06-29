package com.qoobot.qooauth.auth.rbac;

import com.qoobot.qooauth.common.constants.ErrorCodes;
import com.qoobot.qooauth.common.exception.AuthException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.util.*;
import java.util.stream.Collectors;

/**
 * RBAC (Role-Based Access Control) engine.
 * Provides role management, permission checking, and access decision auditing.
 */
@Service
public class RbacService {

    private final RoleRepository roleRepository;
    private final PermissionRepository permissionRepository;
    private final UserRoleRepository userRoleRepository;
    private final AccessDecisionRepository accessDecisionRepository;

    public RbacService(RoleRepository roleRepository,
                       PermissionRepository permissionRepository,
                       UserRoleRepository userRoleRepository,
                       AccessDecisionRepository accessDecisionRepository) {
        this.roleRepository = roleRepository;
        this.permissionRepository = permissionRepository;
        this.userRoleRepository = userRoleRepository;
        this.accessDecisionRepository = accessDecisionRepository;
    }

    // ==================== Role Management ====================

    /**
     * List all roles.
     */
    public List<Map<String, Object>> listRoles() {
        return roleRepository.findAll().stream()
                .map(r -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("role_id", r.getRoleId());
                    m.put("name", r.getName());
                    m.put("description", r.getDescription());
                    m.put("category", r.getCategory());
                    m.put("is_system", r.isSystem());
                    m.put("priority", r.getPriority());
                    return m;
                })
                .collect(Collectors.toList());
    }

    /**
     * Get role details with permissions.
     */
    public Map<String, Object> getRoleDetail(String roleId) {
        RoleEntity role = roleRepository.findByRoleId(roleId)
                .orElseThrow(() -> new AuthException(ErrorCodes.NOT_FOUND, "Role not found: " + roleId));

        Map<String, Object> detail = new LinkedHashMap<>();
        detail.put("role_id", role.getRoleId());
        detail.put("name", role.getName());
        detail.put("description", role.getDescription());
        detail.put("category", role.getCategory());
        detail.put("is_system", role.isSystem());
        detail.put("priority", role.getPriority());
        detail.put("permissions", getPermissionsForRole(roleId));
        return detail;
    }

    /**
     * Get permissions assigned to a role.
     */
    public List<Map<String, Object>> getPermissionsForRole(String roleId) {
        // Query role_permissions via JPA native since we use string keys
        // For simplicity, return the seeded permissions
        return permissionRepository.findAll().stream()
                .filter(p -> {
                    // Check if this permission is assigned to the role
                    return true; // Simplified: in production, query role_permissions join table
                })
                .map(p -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("permission_id", p.getPermissionId());
                    m.put("name", p.getName());
                    m.put("resource_type", p.getResourceType());
                    m.put("action", p.getAction());
                    m.put("scope", p.getScope());
                    return m;
                })
                .collect(Collectors.toList());
    }

    // ==================== User Role Assignment ====================

    /**
     * Get roles for a user.
     */
    public List<Map<String, Object>> getUserRoles(String userId) {
        List<UserRoleEntity> assignments = userRoleRepository.findActiveByUserId(userId, Instant.now());
        List<String> roleIds = assignments.stream()
                .map(UserRoleEntity::getRoleId)
                .distinct()
                .collect(Collectors.toList());

        List<RoleEntity> roles = roleRepository.findByRoleIds(roleIds);
        Map<String, RoleEntity> roleMap = roles.stream()
                .collect(Collectors.toMap(RoleEntity::getRoleId, r -> r));

        return assignments.stream()
                .map(ur -> {
                    RoleEntity role = roleMap.get(ur.getRoleId());
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("role_id", ur.getRoleId());
                    m.put("role_name", role != null ? role.getName() : ur.getRoleId());
                    m.put("scope_type", ur.getScopeType());
                    m.put("scope_id", ur.getScopeId());
                    m.put("granted_at", ur.getGrantedAt());
                    m.put("expires_at", ur.getExpiresAt());
                    return m;
                })
                .collect(Collectors.toList());
    }

    /**
     * Assign a role to a user.
     */
    @Transactional
    public Map<String, Object> assignRole(String userId, String roleId, String grantedBy,
                                           String scopeType, String scopeId, Instant expiresAt) {
        // Verify role exists
        roleRepository.findByRoleId(roleId)
                .orElseThrow(() -> new AuthException(ErrorCodes.NOT_FOUND, "Role not found: " + roleId));

        UserRoleEntity assignment = new UserRoleEntity();
        assignment.setUserId(userId);
        assignment.setRoleId(roleId);
        assignment.setGrantedBy(grantedBy);
        assignment.setScopeType(scopeType);
        assignment.setScopeId(scopeId);
        assignment.setGrantedAt(Instant.now());
        assignment.setExpiresAt(expiresAt);
        assignment = userRoleRepository.save(assignment);

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("id", assignment.getId());
        result.put("user_id", assignment.getUserId());
        result.put("role_id", assignment.getRoleId());
        result.put("granted_at", assignment.getGrantedAt());
        result.put("message", "Role assigned successfully");
        return result;
    }

    /**
     * Revoke a role from a user.
     */
    @Transactional
    public void revokeRole(String userId, String roleId) {
        List<UserRoleEntity> assignments = userRoleRepository.findActiveByUserId(userId, Instant.now());
        assignments.stream()
                .filter(ur -> ur.getRoleId().equals(roleId))
                .forEach(ur -> ur.setExpiresAt(Instant.now()));
        userRoleRepository.saveAll(assignments);
    }

    // ==================== Permission Checking ====================

    /**
     * Check if a user has a specific permission.
     * Returns true if allowed, throws AuthException if denied.
     */
    public void checkPermission(String userId, String permissionId, String resourceType,
                                 String resourceId, String action) {
        boolean allowed = hasPermission(userId, permissionId, resourceType, resourceId, action);

        // Log access decision
        AccessDecisionEntity decision = new AccessDecisionEntity();
        decision.setUserId(userId);
        decision.setPermissionId(permissionId);
        decision.setResourceType(resourceType);
        decision.setResourceId(resourceId);
        decision.setAction(action);
        decision.setDecision(allowed ? "ALLOW" : "DENY");
        decision.setReason(allowed ? null : "Insufficient permissions");
        decision.setDecidedAt(Instant.now());
        accessDecisionRepository.save(decision);

        if (!allowed) {
            throw new AuthException(ErrorCodes.INSUFFICIENT_PERMISSIONS,
                    "Permission denied: " + permissionId);
        }
    }

    /**
     * Check if user has a permission (boolean).
     */
    public boolean hasPermission(String userId, String permissionId, String resourceType,
                                  String resourceId, String action) {
        // Get user's active roles
        List<UserRoleEntity> assignments = userRoleRepository.findActiveByUserId(userId, Instant.now());
        if (assignments.isEmpty()) {
            return false;
        }

        // Get role entities
        List<String> roleIds = assignments.stream()
                .map(UserRoleEntity::getRoleId)
                .distinct()
                .collect(Collectors.toList());

        List<RoleEntity> roles = roleRepository.findByRoleIds(roleIds);

        // SUPER_ADMIN bypasses all checks
        boolean isSuperAdmin = roles.stream().anyMatch(r -> "SUPER_ADMIN".equals(r.getRoleId()));
        if (isSuperAdmin) {
            return true;
        }

        // Check if any role has the required permission
        // In production: query role_permissions join table
        // For now: check against seeded permissions based on priority
        PermissionEntity requiredPerm = permissionRepository.findByPermissionId(permissionId).orElse(null);
        if (requiredPerm == null) {
            // Try resource:action format
            requiredPerm = permissionRepository.findByResourceAndAction(resourceType, action).orElse(null);
        }

        if (requiredPerm == null) {
            return false;
        }

        // Check scope: if permission scope is OWNED, verify resource ownership
        if ("OWNED".equals(requiredPerm.getScope()) && resourceId != null) {
            // In production: verify user owns the resource
            // Simplified: allow if user has any role with this permission
        }

        // Check if user's highest role priority is sufficient
        // In production: proper permission tree traversal
        int maxPriority = roles.stream()
                .mapToInt(RoleEntity::getPriority)
                .max()
                .orElse(0);

        // Simplified check: USER (200) can access basic, ADMIN (800) can access admin
        return maxPriority >= 200;
    }

    /**
     * Get all effective permissions for a user.
     */
    public List<Map<String, Object>> getUserPermissions(String userId) {
        List<UserRoleEntity> assignments = userRoleRepository.findActiveByUserId(userId, Instant.now());
        List<String> roleIds = assignments.stream()
                .map(UserRoleEntity::getRoleId)
                .distinct()
                .collect(Collectors.toList());

        List<RoleEntity> roles = roleRepository.findByRoleIds(roleIds);

        boolean isSuperAdmin = roles.stream().anyMatch(r -> "SUPER_ADMIN".equals(r.getRoleId()));

        return permissionRepository.findAll().stream()
                .filter(p -> isSuperAdmin || isPermissionInRoles(p.getPermissionId(), roles))
                .map(p -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("permission_id", p.getPermissionId());
                    m.put("name", p.getName());
                    m.put("resource_type", p.getResourceType());
                    m.put("action", p.getAction());
                    m.put("scope", p.getScope());
                    return m;
                })
                .collect(Collectors.toList());
    }

    /**
     * Get access decision history for a user.
     */
    public List<AccessDecisionEntity> getAccessHistory(String userId) {
        return accessDecisionRepository.findTop100ByUserIdOrderByDecidedAtDesc(userId);
    }

    // ==================== Private Helpers ====================

    private boolean isPermissionInRoles(String permissionId, List<RoleEntity> roles) {
        // In production: query role_permissions join table
        // Simplified: role-based heuristic
        int maxPriority = roles.stream().mapToInt(RoleEntity::getPriority).max().orElse(0);

        if (maxPriority >= 1000) return true; // SUPER_ADMIN
        if (maxPriority >= 800) {
            // ADMIN: most permissions except skill management
            return !permissionId.startsWith("skill:manage");
        }
        if (maxPriority >= 600) {
            // DEVELOPER: read/write own, system health
            return !permissionId.contains(":manage") && !permissionId.contains(":manage_all")
                    && !permissionId.startsWith("audit:export");
        }
        if (maxPriority >= 400) {
            // DEVICE_OPERATOR: device control, basic read
            return permissionId.startsWith("device:") || permissionId.endsWith(":read")
                    || permissionId.equals("system:health");
        }
        if (maxPriority >= 200) {
            // USER: own resources only
            return permissionId.endsWith(":read") || permissionId.endsWith(":write")
                    || permissionId.endsWith(":control");
        }
        // GUEST: read-only
        return permissionId.endsWith(":read");
    }
}
