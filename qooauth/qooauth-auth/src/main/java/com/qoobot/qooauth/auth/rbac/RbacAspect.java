package com.qoobot.qooauth.auth.rbac;

import com.qoobot.qooauth.common.constants.ErrorCodes;
import com.qoobot.qooauth.common.exception.AuthException;
import jakarta.servlet.http.HttpServletRequest;
import org.aspectj.lang.JoinPoint;
import org.aspectj.lang.annotation.Aspect;
import org.aspectj.lang.annotation.Before;
import org.aspectj.lang.reflect.MethodSignature;
import org.springframework.stereotype.Component;

import java.lang.reflect.Method;

/**
 * AOP aspect that enforces @RequirePermission annotations.
 * Runs before controller methods to check RBAC permissions.
 */
@Aspect
@Component
public class RbacAspect {

    private final RbacService rbacService;
    private final HttpServletRequest request;

    public RbacAspect(RbacService rbacService, HttpServletRequest request) {
        this.rbacService = rbacService;
        this.request = request;
    }

    @Before("@annotation(com.qoobot.qooauth.auth.rbac.RequirePermission) || " +
            "@within(com.qoobot.qooauth.auth.rbac.RequirePermission)")
    public void checkPermission(JoinPoint joinPoint) {
        // Extract annotation
        MethodSignature signature = (MethodSignature) joinPoint.getSignature();
        Method method = signature.getMethod();

        RequirePermission classAnnotation = method.getDeclaringClass().getAnnotation(RequirePermission.class);
        RequirePermission methodAnnotation = method.getAnnotation(RequirePermission.class);

        String permissionId = null;
        String resourceType = "";

        if (methodAnnotation != null) {
            permissionId = methodAnnotation.value();
            resourceType = methodAnnotation.resourceType();
        } else if (classAnnotation != null) {
            permissionId = classAnnotation.value();
            resourceType = classAnnotation.resourceType();
        }

        if (permissionId == null || permissionId.isEmpty()) {
            return; // No permission required
        }

        // Get userId from request attribute (set by JWT filter)
        String userId = (String) request.getAttribute("userId");
        if (userId == null) {
            throw new AuthException(ErrorCodes.INSUFFICIENT_PERMISSIONS,
                    "Authentication required for permission: " + permissionId);
        }

        // Extract resource ID from path if available
        String resourceId = extractResourceId();

        // Perform permission check
        rbacService.checkPermission(userId, permissionId, resourceType, resourceId, "access");
    }

    private String extractResourceId() {
        String path = request.getRequestURI();
        String[] segments = path.split("/");
        // Try to extract ID from path segments (e.g., /api/v1/devices/DEV123 -> DEV123)
        if (segments.length >= 4) {
            String last = segments[segments.length - 1];
            if (last.matches("[A-Za-z0-9_-]+")) {
                return last;
            }
        }
        return null;
    }
}
