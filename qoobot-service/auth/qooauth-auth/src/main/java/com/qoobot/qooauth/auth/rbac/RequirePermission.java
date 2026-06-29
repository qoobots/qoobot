package com.qoobot.qooauth.auth.rbac;

import java.lang.annotation.*;

/**
 * Annotation to require a specific permission for accessing a method.
 * Applied to controller methods; enforced by RbacAspect.
 */
@Target({ElementType.METHOD, ElementType.TYPE})
@Retention(RetentionPolicy.RUNTIME)
@Documented
public @interface RequirePermission {
    /** Permission identifier, e.g. "device:control" */
    String value();
    /** Resource type for scope checking */
    String resourceType() default "";
}
