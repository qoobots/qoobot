package com.qoobot.qoostore.client;

import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;

import java.util.List;
import java.util.Map;

/**
 * qoocloud 设备管理客户端
 * 集成 qoocloud 服务进行设备查询、OTA推送
 */
@Slf4j
@Component
public class QoocloudClient {

    private final RestTemplate restTemplate;

    @Value("${qoocloud.base-url:http://localhost:8204}")
    private String qoocloudBaseUrl;

    public QoocloudClient() {
        this.restTemplate = new RestTemplate();
    }

    /**
     * 获取设备信息
     */
    @SuppressWarnings("unchecked")
    public Map<String, Object> getDeviceInfo(String deviceId) {
        try {
            String url = qoocloudBaseUrl + "/api/v1/devices/" + deviceId;
            return restTemplate.getForObject(url, Map.class);
        } catch (Exception e) {
            log.warn("Failed to get device info from qoocloud: deviceId={}, error={}", deviceId, e.getMessage());
            return Map.of("deviceId", deviceId, "status", "unknown");
        }
    }

    /**
     * 获取用户绑定的设备列表
     */
    @SuppressWarnings("unchecked")
    public List<Map<String, Object>> getUserDevices(String userId) {
        try {
            String url = qoocloudBaseUrl + "/api/v1/users/" + userId + "/devices";
            return restTemplate.getForObject(url, List.class);
        } catch (Exception e) {
            log.warn("Failed to get user devices from qoocloud: userId={}, error={}", userId, e.getMessage());
            return List.of();
        }
    }

    /**
     * 推送OTA更新通知到设备
     */
    public void pushOtaUpdate(String deviceId, String skillId, String version, String downloadUrl) {
        try {
            String url = qoocloudBaseUrl + "/api/v1/ota/push";
            Map<String, Object> payload = Map.of(
                    "deviceId", deviceId,
                    "type", "skill_update",
                    "skillId", skillId,
                    "version", version,
                    "downloadUrl", downloadUrl
            );
            restTemplate.postForObject(url, payload, Map.class);
            log.info("OTA push sent: deviceId={}, skillId={}, version={}", deviceId, skillId, version);
        } catch (Exception e) {
            log.warn("Failed to push OTA update: deviceId={}, skillId={}, error={}", deviceId, skillId, e.getMessage());
        }
    }

    /**
     * 检查设备在线状态
     */
    public boolean isDeviceOnline(String deviceId) {
        try {
            String url = qoocloudBaseUrl + "/api/v1/devices/" + deviceId + "/status";
            @SuppressWarnings("unchecked")
            Map<String, Object> response = restTemplate.getForObject(url, Map.class);
            return response != null && "online".equals(response.get("status"));
        } catch (Exception e) {
            log.warn("Failed to check device online status: deviceId={}, error={}", deviceId, e.getMessage());
            return false;
        }
    }
}
