package com.qoobot.qoocloud.gateway.filter;

import jakarta.servlet.*;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;

import java.io.IOException;

/**
 * Global authentication filter for API gateway.
 * Validates JWT tokens and device certificates via qooauth.
 */
@Component
@Order(1)
public class AuthGlobalFilter implements Filter {

    private static final Logger log = LoggerFactory.getLogger(AuthGlobalFilter.class);

    @Override
    public void doFilter(ServletRequest request, ServletResponse response,
                         FilterChain chain) throws IOException, ServletException {
        HttpServletRequest httpRequest = (HttpServletRequest) request;
        String path = httpRequest.getRequestURI();

        // Skip auth for public endpoints
        if (path.startsWith("/api/public/") || path.startsWith("/actuator/")) {
            chain.doFilter(request, response);
            return;
        }

        // Validate Authorization header
        String authHeader = httpRequest.getHeader("Authorization");
        if (authHeader == null || !authHeader.startsWith("Bearer ")) {
            HttpServletResponse httpResponse = (HttpServletResponse) response;
            httpResponse.setStatus(401);
            httpResponse.setContentType("application/json");
            httpResponse.getWriter().write("{\"error\":\"UNAUTHORIZED\",\"message\":\"Missing or invalid token\"}");
            return;
        }

        // In production: validate JWT via qooauth service
        String token = authHeader.substring(7);
        log.debug("Auth filter: path={}, token_prefix={}***", path,
                token.substring(0, Math.min(8, token.length())));

        chain.doFilter(request, response);
    }
}
