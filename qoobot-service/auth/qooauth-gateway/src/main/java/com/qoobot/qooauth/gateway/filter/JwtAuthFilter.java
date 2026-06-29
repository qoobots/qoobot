package com.qoobot.qooauth.gateway.filter;

import com.nimbusds.jose.JOSEException;
import com.nimbusds.jose.JWSAlgorithm;
import com.nimbusds.jose.jwk.source.JWKSource;
import com.nimbusds.jose.jwk.source.RemoteJWKSet;
import com.nimbusds.jose.proc.BadJOSEException;
import com.nimbusds.jose.proc.JWSKeySelector;
import com.nimbusds.jose.proc.JWSVerificationKeySelector;
import com.nimbusds.jose.proc.SecurityContext;
import com.nimbusds.jwt.JWTClaimsSet;
import com.nimbusds.jwt.proc.ConfigurableJWTProcessor;
import com.nimbusds.jwt.proc.DefaultJWTProcessor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.cloud.gateway.filter.GlobalFilter;
import org.springframework.core.Ordered;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.server.reactive.ServerHttpRequest;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

import java.net.MalformedURLException;
import java.net.URL;
import java.text.ParseException;
import java.util.List;
import java.util.Set;

/**
 * Global filter that extracts and validates Bearer JWT tokens from incoming requests.
 * Uses Nimbus JOSE+JWT library for validation.
 */
@Slf4j
@Component
public class JwtAuthFilter implements GlobalFilter, Ordered {

    private static final Set<String> PUBLIC_PATHS = Set.of(
        "/api/v1/auth/login",
        "/api/v1/auth/register",
        "/api/v1/auth/token",
        "/.well-known/",
        "/actuator/health",
        "/actuator/info",
        "/fallback/"
    );

    private final ConfigurableJWTProcessor<SecurityContext> jwtProcessor;

    public JwtAuthFilter(@Value("${gateway.jwt.jwk-set-uri:http://localhost:8081/.well-known/jwks.json}") String jwkSetUri) {
        this.jwtProcessor = new DefaultJWTProcessor<>();
        try {
            JWKSource<SecurityContext> keySource = new RemoteJWKSet<>(new URL(jwkSetUri));
            JWSKeySelector<SecurityContext> keySelector = new JWSVerificationKeySelector<>(
                JWSAlgorithm.RS256, keySource);
            jwtProcessor.setJWSKeySelector(keySelector);
        } catch (MalformedURLException e) {
            throw new RuntimeException("Invalid JWK set URI: " + jwkSetUri, e);
        }
    }

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        String path = exchange.getRequest().getURI().getPath();

        // Skip public paths
        if (isPublicPath(path)) {
            return chain.filter(exchange);
        }

        // Extract token from Authorization header
        String authHeader = exchange.getRequest().getHeaders().getFirst(HttpHeaders.AUTHORIZATION);
        if (authHeader == null || !authHeader.startsWith("Bearer ")) {
            log.debug("Missing or invalid Authorization header for path: {}", path);
            exchange.getResponse().setStatusCode(HttpStatus.UNAUTHORIZED);
            return exchange.getResponse().setComplete();
        }

        String token = authHeader.substring(7);

        try {
            // Validate JWT
            JWTClaimsSet claimsSet = jwtProcessor.process(token, null);

            // Extract claims for downstream propagation
            String subject = claimsSet.getSubject();
            String userId = claimsSet.getStringClaim("user_id");
            List<String> roles = claimsSet.getStringListClaim("roles");
            List<String> scopes = claimsSet.getStringListClaim("scope");

            // Propagate claims to downstream services via headers
            ServerHttpRequest modifiedRequest = exchange.getRequest().mutate()
                .header("X-Auth-User-Id", userId != null ? userId : subject)
                .header("X-Auth-Subject", subject)
                .header("X-Auth-Roles", roles != null ? String.join(",", roles) : "")
                .header("X-Auth-Scopes", scopes != null ? String.join(",", scopes) : "")
                .build();

            ServerWebExchange modifiedExchange = exchange.mutate().request(modifiedRequest).build();

            return chain.filter(modifiedExchange);

        } catch (ParseException e) {
            log.debug("Malformed JWT token for path {}: {}", path, e.getMessage());
            exchange.getResponse().setStatusCode(HttpStatus.UNAUTHORIZED);
            return exchange.getResponse().setComplete();
        } catch (BadJOSEException | JOSEException e) {
            log.debug("Invalid JWT token for path {}: {}", path, e.getMessage());
            exchange.getResponse().setStatusCode(HttpStatus.UNAUTHORIZED);
            return exchange.getResponse().setComplete();
        }
    }

    @Override
    public int getOrder() {
        return -100; // High priority - execute before other filters
    }

    private boolean isPublicPath(String path) {
        return PUBLIC_PATHS.stream().anyMatch(path::startsWith);
    }
}
