package com.qoobot.qooauth.auth.config;

import com.qoobot.qooauth.common.util.AuditEventPublisher;
import jakarta.servlet.http.HttpServletRequest;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.aspectj.lang.ProceedingJoinPoint;
import org.aspectj.lang.annotation.Around;
import org.aspectj.lang.annotation.Aspect;
import org.aspectj.lang.annotation.Pointcut;
import org.springframework.stereotype.Component;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;

import java.security.Principal;
import java.util.Map;
import java.util.Optional;

/**
 * AOP aspect that automatically records audit events for key authentication operations.
 * <p>
 * Intercepts controller methods annotated with {@code @Auditable} or matching
 * known auth endpoint patterns, and publishes audit events via Kafka.
 */
@Slf4j
@Aspect
@Component
@RequiredArgsConstructor
public class AuditAspect {

    private final AuditEventPublisher auditEventPublisher;

    /**
     * Pointcut: all controller methods annotated with @Auditable.
     */
    @Pointcut("@annotation(com.qoobot.qooauth.auth.config.Auditable)")
    public void auditableMethod() {}

    /**
     * Pointcut: known auth controller methods that should always be audited.
     */
    @Pointcut("execution(* com.qoobot.qooauth.auth.controller.AuthController.login(..)) || " +
              "execution(* com.qoobot.qooauth.auth.controller.AuthController.register(..)) || " +
              "execution(* com.qoobot.qooauth.auth.controller.AuthController.logout(..)) || " +
              "execution(* com.qoobot.qooauth.auth.controller.AuthController.refreshToken(..)) || " +
              "execution(* com.qoobot.qooauth.auth.controller.AuthController.revokeToken(..))")
    public void knownAuthEndpoints() {}

    @Around("auditableMethod() || knownAuthEndpoints()")
    public Object audit(ProceedingJoinPoint joinPoint) throws Throwable {
        long startTime = System.currentTimeMillis();
        String action = resolveAction(joinPoint);
        String result = "SUCCESS";
        String errorCode = null;
        Object returnValue = null;

        try {
            returnValue = joinPoint.proceed();
            return returnValue;
        } catch (Exception e) {
            result = "FAILURE";
            errorCode = e.getClass().getSimpleName();
            throw e;
        } finally {
            long duration = System.currentTimeMillis() - startTime;
            try {
                publishAuditEvent(joinPoint, action, result, errorCode, duration);
            } catch (Exception e) {
                log.error("Failed to publish audit event via aspect: {}", e.getMessage());
            }
        }
    }

    private String resolveAction(ProceedingJoinPoint joinPoint) {
        // Check @Auditable annotation first
        Auditable annotation = null;
        try {
            annotation = joinPoint.getTarget().getClass()
                    .getMethod(joinPoint.getSignature().getName(),
                            ((org.aspectj.lang.reflect.MethodSignature) joinPoint.getSignature()).getParameterTypes())
                    .getAnnotation(Auditable.class);
        } catch (NoSuchMethodException ignored) {}

        if (annotation != null && !annotation.action().isEmpty()) {
            return annotation.action();
        }

        // Fallback: derive from method name
        String methodName = joinPoint.getSignature().getName().toUpperCase();
        return switch (methodName) {
            case "LOGIN" -> "LOGIN";
            case "REGISTER" -> "REGISTER";
            case "LOGOUT" -> "SESSION_DESTROY";
            case "REFRESHTOKEN" -> "TOKEN_REFRESH";
            case "REVOKETOKEN" -> "TOKEN_REVOKE";
            default -> methodName;
        };
    }

    private void publishAuditEvent(ProceedingJoinPoint joinPoint, String action,
                                    String result, String errorCode, long duration) {
        HttpServletRequest request = getCurrentRequest();
        String clientIp = request != null ? request.getRemoteAddr() : null;
        String userAgent = request != null ? request.getHeader("User-Agent") : null;

        // Extract actor from method arguments or security context
        String actorId = "SYSTEM";
        String actorName = null;
        String actorType = "SYSTEM";

        Principal principal = request != null ? request.getUserPrincipal() : null;
        if (principal != null) {
            actorId = principal.getName();
            actorName = principal.getName();
            actorType = "USER";
        }

        Map<String, Object> details = Map.of(
                "method", joinPoint.getSignature().toShortString(),
                "durationMs", duration
        );

        auditEventPublisher.publish(
                actorType, actorId, actorName,
                action,
                null, null, null,
                result, errorCode,
                clientIp, userAgent,
                null, null, null,
                details,
                null
        );
    }

    private HttpServletRequest getCurrentRequest() {
        ServletRequestAttributes attrs =
                (ServletRequestAttributes) RequestContextHolder.getRequestAttributes();
        return attrs != null ? attrs.getRequest() : null;
    }
}
