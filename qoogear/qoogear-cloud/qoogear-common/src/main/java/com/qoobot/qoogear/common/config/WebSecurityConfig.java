package com.qoobot.qoogear.common.config;

import com.qoobot.qoogear.common.security.JwtAuthenticationFilter;
import com.qoobot.qoogear.common.security.JwtTokenProvider;
import lombok.RequiredArgsConstructor;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpMethod;
import org.springframework.security.config.annotation.method.configuration.EnableMethodSecurity;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;
import org.springframework.web.cors.CorsConfiguration;
import org.springframework.web.cors.CorsConfigurationSource;
import org.springframework.web.cors.UrlBasedCorsConfigurationSource;

import java.util.List;

/**
 * Spring Security configuration for qoogear microservices.
 * Stateless JWT-based authentication with role-based access control.
 */
@Configuration
@EnableWebSecurity
@EnableMethodSecurity
@RequiredArgsConstructor
public class WebSecurityConfig {

    private final JwtTokenProvider tokenProvider;

    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        http
                .cors(cors -> cors.configurationSource(corsConfigurationSource()))
                .csrf(csrf -> csrf.disable())
                .sessionManagement(sm -> sm.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                .authorizeHttpRequests(auth -> auth
                        // Public endpoints
                        .requestMatchers(HttpMethod.GET,
                                "/api/v1/cert/public/**",
                                "/api/v1/standard/public/**",
                                "/api/v1/developer/public/**",
                                "/actuator/health",
                                "/swagger-ui/**",
                                "/v3/api-docs/**"
                        ).permitAll()
                        // Developer self-service (authenticated developers)
                        .requestMatchers("/api/v1/developer/**").hasAnyRole("DEVELOPER", "ADMIN")
                        .requestMatchers("/api/v1/cert/application/**").hasAnyRole("DEVELOPER", "ADMIN")
                        // Lab operations
                        .requestMatchers("/api/v1/lab/**").hasAnyRole("LAB_TECHNICIAN", "ADMIN")
                        // Admin only
                        .requestMatchers("/api/v1/cert/admin/**",
                                "/api/v1/standard/admin/**",
                                "/api/v1/admin/**").hasRole("ADMIN")
                        // Security audit
                        .requestMatchers("/api/v1/security/**").hasAnyRole("ADMIN", "SECURITY_AUDITOR")
                        // All other requests need authentication
                        .anyRequest().authenticated()
                )
                .addFilterBefore(
                        new JwtAuthenticationFilter(tokenProvider),
                        UsernamePasswordAuthenticationFilter.class
                );

        return http.build();
    }

    @Bean
    public CorsConfigurationSource corsConfigurationSource() {
        CorsConfiguration config = new CorsConfiguration();
        config.setAllowedOrigins(List.of("http://localhost:5173", "http://localhost:3000"));
        config.setAllowedMethods(List.of("GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"));
        config.setAllowedHeaders(List.of("*"));
        config.setAllowCredentials(true);
        config.setMaxAge(3600L);

        UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
        source.registerCorsConfiguration("/api/**", config);
        return source;
    }
}
