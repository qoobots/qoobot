package com.qoobot.qoogear.common.security;

import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Component;

import java.util.Optional;

/**
 * Utility to access the current authenticated user from Spring Security context.
 */
@Component
public class SecurityUtils {

    public Optional<QooGearPrincipal> getCurrentUser() {
        Authentication auth = SecurityContextHolder.getContext().getAuthentication();
        if (auth != null && auth.getPrincipal() instanceof QooGearPrincipal) {
            return Optional.of((QooGearPrincipal) auth.getPrincipal());
        }
        return Optional.empty();
    }

    public String requireCurrentUserId() {
        return getCurrentUser()
                .map(QooGearPrincipal::getUserId)
                .orElseThrow(() -> new SecurityException("Authentication required"));
    }

    public boolean hasRole(String role) {
        return getCurrentUser().map(p -> p.hasRole(role)).orElse(false);
    }
}
