package com.qoobot.qooauth.auth.config;

import com.qoobot.qooauth.auth.security.JwtAuthenticationFilter;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.crypto.argon2.Argon2PasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;

@Configuration
@EnableWebSecurity
public class SecurityConfig {

    private final JwtAuthenticationFilter jwtAuthenticationFilter;

    public SecurityConfig(JwtAuthenticationFilter jwtAuthenticationFilter) {
        this.jwtAuthenticationFilter = jwtAuthenticationFilter;
    }

    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
        http
            .csrf(AbstractHttpConfigurer::disable)
            .sessionManagement(session ->
                session.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
            .authorizeHttpRequests(auth -> auth
                // Public endpoints — no authentication required
                .requestMatchers(
                    "/api/v1/auth/register",
                    "/api/v1/auth/login",
                    "/api/v1/auth/refresh",
                    "/api/v1/auth/mfa/totp/login",
                    "/api/v1/auth/mfa/fido2/login/start",
                    "/api/v1/auth/mfa/fido2/login/complete",
                    "/api/v1/auth/mfa/recovery/login",
                    // SSO — introspection and session validation are called by resource servers
                    "/api/v1/auth/sso/introspect",
                    "/api/v1/auth/sso/sessions/*/validate",
                    // API Key — validation is called by API gateway / resource servers
                    "/api/v1/auth/api-keys/validate",
                    // Device Certificates — CRL and validation are public (RFC 5280)
                    "/api/v1/auth/device-certs/crl",
                    "/api/v1/auth/device-certs/crl/delta",
                    "/api/v1/auth/device-certs/validate/**",
                    "/api/v1/auth/device-certs/bootstrap",
                    // Device Activations — challenge/verify called by unauthenticated devices
                    "/api/v1/auth/device-activations/*/challenge",
                    "/api/v1/auth/device-activations/*/verify",
                    // Account Recovery — public endpoints (unauthenticated users)
                    "/api/v1/account/recovery/initiate",
                    "/api/v1/account/recovery/verify",
                    "/api/v1/account/recovery/complete",
                    "/api/v1/account/recovery/session/**",
                    // Threat Protection — CAPTCHA check is public (called before login)
                    "/api/v1/auth/security/threat/captcha-required",
                    // Device Fingerprint — check-known is public (called before login)
                    "/api/v1/auth/security/threat/device-fingerprint/check-known",
                    // Robot Trust — mTLS verify and delegation validate are called by robots
                    "/api/v1/auth/robot-trust/mtls/verify-peer",
                    "/api/v1/auth/robot-trust/delegations/validate",
                    // Developer — skill signature verification is public
                    "/api/v1/auth/developer/skills/verify-signature",
                    // Privacy — labels are public (transparency)
                    "/api/v1/auth/privacy/labels",
                    "/api/v1/auth/privacy/labels/**",
                    "/.well-known/**",
                    "/oauth2/**",
                    "/actuator/health",
                    "/actuator/prometheus"
                ).permitAll()
                // All other endpoints require authentication
                .anyRequest().authenticated()
            )
            // Add JWT authentication filter before UsernamePasswordAuthenticationFilter
            .addFilterBefore(jwtAuthenticationFilter, UsernamePasswordAuthenticationFilter.class);
        return http.build();
    }

    @Bean
    public PasswordEncoder passwordEncoder() {
        return Argon2PasswordEncoder.defaultsForSpringSecurity_v5_8();
    }
}
