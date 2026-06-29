package com.qoobot.qoostore.security;

import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;

import java.util.Map;

/**
 * qooauth 集成客户端
 * 调用 qooauth 服务进行 token 验证、用户信息查询、权限校验
 */
@Slf4j
@Component
public class QooauthClient {

    private final RestTemplate restTemplate;

    @Value("${qooauth.base-url:http://localhost:8201}")
    private String qooauthBaseUrl;

    public QooauthClient() {
        this.restTemplate = new RestTemplate();
    }

    /**
     * 验证 JWT token
     * @param token JWT token
     * @return token claims (sub, username, roles, etc.)
     */
    @SuppressWarnings("unchecked")
    public Map<String, Object> validateToken(String token) {
        try {
            String url = qooauthBaseUrl + "/api/v1/auth/token/validate";
            HttpHeaders headers = new HttpHeaders();
            headers.setBearerAuth(token);

            ResponseEntity<Map> response = restTemplate.exchange(
                    url, HttpMethod.GET, new HttpEntity<>(headers), Map.class);

            if (response.getBody() != null && Boolean.TRUE.equals(response.getBody().get("valid"))) {
                return (Map<String, Object>) response.getBody().get("claims");
            }
        } catch (Exception e) {
            log.warn("Failed to validate token with qooauth: {}", e.getMessage());
        }
        return null;
    }

    /**
     * 获取用户信息
     * @param userId 用户ID
     * @return 用户信息
     */
    @SuppressWarnings("unchecked")
    public Map<String, Object> getUserInfo(String userId) {
        try {
            String url = qooauthBaseUrl + "/api/v1/users/" + userId;
            ResponseEntity<Map> response = restTemplate.getForEntity(url, Map.class);
            return response.getBody();
        } catch (Exception e) {
            log.warn("Failed to get user info from qooauth: {}", e.getMessage());
            return Map.of();
        }
    }

    /**
     * 检查用户角色
     * @param userId 用户ID
     * @param role 角色名
     * @return 是否拥有该角色
     */
    public boolean hasRole(String userId, String role) {
        Map<String, Object> userInfo = getUserInfo(userId);
        if (userInfo != null && userInfo.containsKey("roles")) {
            @SuppressWarnings("unchecked")
            var roles = (java.util.List<String>) userInfo.get("roles");
            return roles.contains(role);
        }
        return false;
    }

    /**
     * 检查用户是否为开发者
     */
    public boolean isDeveloper(String userId) {
        return hasRole(userId, "developer");
    }

    /**
     * 检查用户是否为审核员
     */
    public boolean isReviewer(String userId) {
        return hasRole(userId, "reviewer") || hasRole(userId, "admin");
    }

    /**
     * 检查用户是否为管理员
     */
    public boolean isAdmin(String userId) {
        return hasRole(userId, "admin");
    }
}
