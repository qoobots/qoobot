package com.qoobot.qooauth.gateway.filter;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.http.server.reactive.ServerHttpRequest;
import org.springframework.http.server.reactive.ServerHttpResponse;
import org.springframework.web.cors.reactive.CorsUtils;
import org.springframework.web.server.ServerWebExchange;
import org.springframework.web.server.WebFilter;
import org.springframework.web.server.WebFilterChain;
import reactor.core.publisher.Mono;

/**
 * CORS configuration filter for the API gateway.
 * Allows cross-origin requests from configured origins.
 */
@Configuration
public class CorsFilter {

    private static final String ALLOWED_ORIGINS = "*";
    private static final String ALLOWED_METHODS = "GET,POST,PUT,PATCH,DELETE,OPTIONS";
    private static final String ALLOWED_HEADERS = "Authorization,Content-Type,X-Request-Id,X-Auth-User-Id,X-CSRF-Token";
    private static final String EXPOSED_HEADERS = "X-Request-Id,X-RateLimit-Remaining,X-RateLimit-Reset";
    private static final long MAX_AGE = 3600L;

    @Bean
    public WebFilter corsWebFilter() {
        return (ServerWebExchange exchange, WebFilterChain chain) -> {
            ServerHttpRequest request = exchange.getRequest();

            if (CorsUtils.isCorsRequest(request)) {
                ServerHttpResponse response = exchange.getResponse();
                HttpHeaders headers = response.getHeaders();

                headers.add(HttpHeaders.ACCESS_CONTROL_ALLOW_ORIGIN, ALLOWED_ORIGINS);
                headers.add(HttpHeaders.ACCESS_CONTROL_ALLOW_METHODS, ALLOWED_METHODS);
                headers.add(HttpHeaders.ACCESS_CONTROL_ALLOW_HEADERS, ALLOWED_HEADERS);
                headers.add(HttpHeaders.ACCESS_CONTROL_EXPOSE_HEADERS, EXPOSED_HEADERS);
                headers.add(HttpHeaders.ACCESS_CONTROL_MAX_AGE, String.valueOf(MAX_AGE));
                headers.add(HttpHeaders.ACCESS_CONTROL_ALLOW_CREDENTIALS, "true");

                // Handle preflight requests
                if (HttpMethod.OPTIONS.equals(request.getMethod())) {
                    response.setStatusCode(HttpStatus.NO_CONTENT);
                    return Mono.empty();
                }
            }

            return chain.filter(exchange);
        };
    }
}
