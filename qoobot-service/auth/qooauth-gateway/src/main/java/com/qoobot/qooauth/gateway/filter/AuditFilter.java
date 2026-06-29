package com.qoobot.qooauth.gateway.filter;

import lombok.extern.slf4j.Slf4j;
import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.cloud.gateway.filter.GlobalFilter;
import org.springframework.core.Ordered;
import org.springframework.http.HttpHeaders;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

import java.time.Instant;
import java.util.UUID;

/**
 * Request/response audit logging filter.
 * Captures and logs request metadata, response status, and timing information.
 */
@Slf4j
@Component
public class AuditFilter implements GlobalFilter, Ordered {

    private static final String REQUEST_ID_HEADER = "X-Request-Id";
    private static final String START_TIME_ATTR = "audit.request.startTime";

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        // Generate or propagate request ID
        String requestId = exchange.getRequest().getHeaders().getFirst(REQUEST_ID_HEADER);
        if (requestId == null || requestId.isBlank()) {
            requestId = UUID.randomUUID().toString().replace("-", "");
        }

        // Store start time for latency calculation
        exchange.getAttributes().put(START_TIME_ATTR, Instant.now());
        exchange.getAttributes().put(REQUEST_ID_HEADER, requestId);

        // Add request ID to response headers
        exchange.getResponse().getHeaders().add(REQUEST_ID_HEADER, requestId);

        String method = exchange.getRequest().getMethod().name();
        String path = exchange.getRequest().getURI().getPath();
        String clientIp = getClientIp(exchange);
        String userAgent = exchange.getRequest().getHeaders().getFirst(HttpHeaders.USER_AGENT);
        String userId = exchange.getRequest().getHeaders().getFirst("X-Auth-User-Id");

        // Log request
        log.info("AUDIT_REQUEST | id={} | method={} | path={} | client_ip={} | user_id={} | user_agent={}",
            requestId, method, path, clientIp, userId, userAgent);

        // Process the request and log response
        return chain.filter(exchange)
            .doOnSuccess(v -> logResponse(exchange, requestId))
            .doOnError(e -> logResponse(exchange, requestId));
    }

    @Override
    public int getOrder() {
        return Ordered.LOWEST_PRECEDENCE; // Execute after all other filters
    }

    private void logResponse(ServerWebExchange exchange, String requestId) {
        Instant startTime = exchange.getAttribute(START_TIME_ATTR);
        long latencyMs = startTime != null
            ? java.time.Duration.between(startTime, Instant.now()).toMillis()
            : -1;

        var statusCode = exchange.getResponse().getStatusCode();
        int status = statusCode != null ? statusCode.value() : 0;

        String path = exchange.getRequest().getURI().getPath();
        String method = exchange.getRequest().getMethod().name();

        log.info("AUDIT_RESPONSE | id={} | method={} | path={} | status={} | latency_ms={}",
            requestId, method, path, status, latencyMs);
    }

    private String getClientIp(ServerWebExchange exchange) {
        String xForwardedFor = exchange.getRequest().getHeaders().getFirst("X-Forwarded-For");
        if (xForwardedFor != null && !xForwardedFor.isBlank()) {
            return xForwardedFor.split(",")[0].trim();
        }
        var remoteAddress = exchange.getRequest().getRemoteAddress();
        return remoteAddress != null ? remoteAddress.getAddress().getHostAddress() : "unknown";
    }
}
