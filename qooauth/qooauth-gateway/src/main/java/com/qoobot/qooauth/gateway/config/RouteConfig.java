package com.qoobot.qooauth.gateway.config;

import org.springframework.cloud.gateway.route.RouteLocator;
import org.springframework.cloud.gateway.route.builder.RouteLocatorBuilder;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * Spring Cloud Gateway route definitions for all qooauth microservices.
 */
@Configuration
public class RouteConfig {

    private static final String AUTH_SERVICE = "http://localhost:8081";
    private static final String DEVICE_SERVICE = "http://localhost:8082";
    private static final String API_KEY_SERVICE = "http://localhost:8083";
    private static final String SECURITY_SERVICE = "http://localhost:8084";
    private static final String ROBOT_TRUST_SERVICE = "http://localhost:8085";
    private static final String DEVELOPER_SERVICE = "http://localhost:8086";
    private static final String USER_SERVICE = "http://localhost:8087";
    private static final String AUDIT_SERVICE = "http://localhost:8088";

    @Bean
    public RouteLocator customRouteLocator(RouteLocatorBuilder builder) {
        return builder.routes()
            // ---- Auth Service ----
            .route("auth-service", r -> r
                .path("/api/v1/auth/**", "/.well-known/**", "/oauth2/**")
                .filters(f -> f
                    .stripPrefix(0)
                    .circuitBreaker(config -> config
                        .setName("authCircuitBreaker")
                        .setFallbackUri("forward:/fallback/auth")))
                .uri(AUTH_SERVICE))

            // ---- User Service ----
            .route("user-service", r -> r
                .path("/api/v1/users/**")
                .filters(f -> f
                    .stripPrefix(0)
                    .circuitBreaker(config -> config
                        .setName("userCircuitBreaker")
                        .setFallbackUri("forward:/fallback/user")))
                .uri(USER_SERVICE))

            // ---- Device Service ----
            .route("device-service", r -> r
                .path("/api/v1/devices/**")
                .filters(f -> f
                    .stripPrefix(0)
                    .circuitBreaker(config -> config
                        .setName("deviceCircuitBreaker")
                        .setFallbackUri("forward:/fallback/device")))
                .uri(DEVICE_SERVICE))

            // ---- API Key Service ----
            .route("api-key-service", r -> r
                .path("/api/v1/api-keys/**")
                .filters(f -> f
                    .stripPrefix(0)
                    .circuitBreaker(config -> config
                        .setName("apiKeyCircuitBreaker")
                        .setFallbackUri("forward:/fallback/api-key")))
                .uri(API_KEY_SERVICE))

            // ---- Security Service ----
            .route("security-service", r -> r
                .path("/api/v1/security/**")
                .filters(f -> f
                    .stripPrefix(0)
                    .circuitBreaker(config -> config
                        .setName("securityCircuitBreaker")
                        .setFallbackUri("forward:/fallback/security")))
                .uri(SECURITY_SERVICE))

            // ---- Robot Trust Service ----
            .route("robot-trust-service", r -> r
                .path("/api/v1/robot-trust/**")
                .filters(f -> f
                    .stripPrefix(0)
                    .circuitBreaker(config -> config
                        .setName("robotTrustCircuitBreaker")
                        .setFallbackUri("forward:/fallback/robot-trust")))
                .uri(ROBOT_TRUST_SERVICE))

            // ---- Developer Service ----
            .route("developer-service", r -> r
                .path("/api/v1/developer/**")
                .filters(f -> f
                    .stripPrefix(0)
                    .circuitBreaker(config -> config
                        .setName("developerCircuitBreaker")
                        .setFallbackUri("forward:/fallback/developer")))
                .uri(DEVELOPER_SERVICE))

            // ---- Audit Service ----
            .route("audit-service", r -> r
                .path("/api/v1/audit/**")
                .filters(f -> f
                    .stripPrefix(0)
                    .circuitBreaker(config -> config
                        .setName("auditCircuitBreaker")
                        .setFallbackUri("forward:/fallback/audit")))
                .uri(AUDIT_SERVICE))

            .build();
    }
}
