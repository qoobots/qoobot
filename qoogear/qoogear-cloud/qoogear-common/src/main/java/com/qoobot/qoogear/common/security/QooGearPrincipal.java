package com.qoobot.qoogear.common.security;

import lombok.AllArgsConstructor;
import lombok.Getter;

import java.util.List;

/**
 * Principal carrying authenticated user identity from JWT claims.
 */
@Getter
@AllArgsConstructor
public class QooGearPrincipal {
    private final String userId;
    private final String username;
    private final List<String> roles;

    public boolean hasRole(String role) {
        return roles.contains(role);
    }

    public boolean hasAnyRole(String... roles) {
        for (String r : roles) {
            if (this.roles.contains(r)) return true;
        }
        return false;
    }
}
