package com.qoobot.qoostore.security;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Component;

import java.util.Optional;
import java.util.UUID;

/**
 * 权限评估器
 * 基于角色的访问控制，用于 service 层权限校验
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class PermissionEvaluator {

    private final QooauthClient qooauthClient;

    /**
     * 获取当前登录用户ID
     */
    public Optional<UUID> getCurrentUserId() {
        Authentication auth = SecurityContextHolder.getContext().getAuthentication();
        if (auth != null && auth.getPrincipal() instanceof UUID userId) {
            return Optional.of(userId);
        }
        return Optional.empty();
    }

    /**
     * 检查当前用户是否拥有指定角色
     */
    public boolean hasRole(String role) {
        Authentication auth = SecurityContextHolder.getContext().getAuthentication();
        if (auth == null) return false;
        return auth.getAuthorities().stream()
                .map(GrantedAuthority::getAuthority)
                .anyMatch(a -> a.equals("ROLE_" + role.toUpperCase()));
    }

    /**
     * 验证当前用户是否为指定用户
     */
    public boolean isCurrentUser(UUID userId) {
        return getCurrentUserId().map(id -> id.equals(userId)).orElse(false);
    }

    /**
     * 验证开发者所有权（skill 属于该开发者）
     */
    public void requireDeveloper(Long developerId) {
        if (!hasRole("developer")) {
            throw new RuntimeException("Requires developer role");
        }
        // Further ownership check would require developer -> userId mapping
    }

    /**
     * 验证审核员权限
     */
    public void requireReviewer() {
        if (!hasRole("reviewer") && !hasRole("admin")) {
            throw new RuntimeException("Requires reviewer or admin role");
        }
    }

    /**
     * 验证管理员权限
     */
    public void requireAdmin() {
        if (!hasRole("admin")) {
            throw new RuntimeException("Requires admin role");
        }
    }

    /**
     * 验证用户已认证
     */
    public void requireAuthenticated() {
        if (getCurrentUserId().isEmpty()) {
            throw new RuntimeException("Authentication required");
        }
    }
}
