package com.qoobot.qooauth.auth.rbac;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class RbacServiceTest {

    @Mock
    private RoleRepository roleRepository;
    @Mock
    private PermissionRepository permissionRepository;
    @Mock
    private UserRoleRepository userRoleRepository;
    @Mock
    private AccessDecisionRepository accessDecisionRepository;

    private RbacService service;

    @BeforeEach
    void setUp() {
        service = new RbacService(roleRepository, permissionRepository,
                userRoleRepository, accessDecisionRepository);
    }

    @Test
    void superAdmin_ShouldHaveAllPermissions() {
        UserRoleEntity adminRole = new UserRoleEntity();
        adminRole.setRoleId("SUPER_ADMIN");

        RoleEntity role = new RoleEntity();
        role.setRoleId("SUPER_ADMIN");
        role.setPriority(1000);

        when(userRoleRepository.findActiveByUserId(any(), any()))
                .thenReturn(List.of(adminRole));
        when(roleRepository.findByRoleIds(any()))
                .thenReturn(List.of(role));

        boolean result = service.hasPermission("uid_admin", "system:config",
                "system", "sys_001", "manage");

        assertTrue(result, "Super admin should have all permissions");
    }

    @Test
    void guestUser_ShouldHaveReadOnlyAccess() {
        UserRoleEntity guestRole = new UserRoleEntity();
        guestRole.setRoleId("GUEST");

        RoleEntity role = new RoleEntity();
        role.setRoleId("GUEST");
        role.setPriority(100);

        when(userRoleRepository.findActiveByUserId(any(), any()))
                .thenReturn(List.of(guestRole));
        when(roleRepository.findByRoleIds(any()))
                .thenReturn(List.of(role));

        boolean readAllowed = service.hasPermission("uid_guest", "device:read",
                "device", "dev_001", "read");
        boolean manageDenied = service.hasPermission("uid_guest", "device:manage",
                "device", "dev_001", "manage");

        assertTrue(readAllowed, "Guest should have read access");
        assertFalse(manageDenied, "Guest should not have manage access");
    }

    @Test
    void assignRole_ShouldCreateAssignment() {
        RoleEntity role = new RoleEntity();
        role.setRoleId("DEVELOPER");
        role.setName("Developer");

        when(roleRepository.findByRoleId("DEVELOPER")).thenReturn(Optional.of(role));
        when(userRoleRepository.save(any())).thenAnswer(inv -> inv.getArgument(0));

        Map<String, Object> result = service.assignRole("uid_user", "DEVELOPER",
                "uid_admin", "device", "dev_001", null);

        assertEquals("uid_user", result.get("user_id"));
        assertEquals("DEVELOPER", result.get("role_id"));
        assertNotNull(result.get("granted_at"));
    }

    @Test
    void getMyRoles_ShouldReturnRoleList() {
        UserRoleEntity ur = new UserRoleEntity();
        ur.setUserId("uid_user");
        ur.setRoleId("USER");
        ur.setGrantedAt(Instant.now());

        RoleEntity role = new RoleEntity();
        role.setRoleId("USER");
        role.setName("Standard User");

        when(userRoleRepository.findActiveByUserId(any(), any()))
                .thenReturn(List.of(ur));
        when(roleRepository.findByRoleIds(any()))
                .thenReturn(List.of(role));

        List<Map<String, Object>> roles = service.getUserRoles("uid_user");

        assertNotNull(roles);
        assertEquals(1, roles.size());
        assertEquals("USER", roles.get(0).get("role_id"));
        assertEquals("Standard User", roles.get(0).get("role_name"));
    }

    @Test
    void noRoles_ShouldDenyAll() {
        when(userRoleRepository.findActiveByUserId(any(), any()))
                .thenReturn(List.of());

        boolean result = service.hasPermission("uid_no_role", "device:read",
                "device", "dev_001", "read");

        assertFalse(result, "User without roles should be denied");
    }
}
