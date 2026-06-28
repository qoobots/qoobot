package com.qoobot.qooauth.auth.config;

import java.lang.annotation.*;

/**
 * Annotation to mark controller methods for automatic audit logging.
 * <p>
 * Methods annotated with {@code @Auditable} will have their execution
 * automatically recorded as audit events via the {@link AuditAspect} AOP aspect.
 *
 * <pre>
 * {@code
 * @PostMapping("/login")
 * @Auditable(action = "LOGIN")
 * public LoginResponse login(@RequestBody LoginRequest request) { ... }
 * }
 * </pre>
 */
@Target(ElementType.METHOD)
@Retention(RetentionPolicy.RUNTIME)
@Documented
public @interface Auditable {

    /**
     * Audit action type (e.g., LOGIN, REGISTER, TOKEN_ISSUE).
     * If empty, the action is derived from the method name.
     */
    String action() default "";
}
