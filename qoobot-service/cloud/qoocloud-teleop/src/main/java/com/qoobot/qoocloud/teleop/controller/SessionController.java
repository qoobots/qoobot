package com.qoobot.qoocloud.teleop.controller;

import com.qoobot.qoocloud.teleop.entity.TeleopSession;
import com.qoobot.qoocloud.teleop.entity.TeleopSession.*;
import com.qoobot.qoocloud.teleop.service.SessionService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

/**
 * 遥控会话管理 API
 */
@RestController
@RequestMapping("/api/v1/teleop/sessions")
public class SessionController {

    private final SessionService sessionService;

    public SessionController(SessionService sessionService) {
        this.sessionService = sessionService;
    }

    /**
     * 创建遥控会话
     */
    @PostMapping
    public ResponseEntity<TeleopSession> createSession(@RequestBody Map<String, Object> body) {
        String robotId = (String) body.get("robotId");
        String operatorId = (String) body.get("operatorId");
        String operatorName = (String) body.getOrDefault("operatorName", "");
        ControlMode mode = ControlMode.valueOf(
            ((String) body.getOrDefault("requestedMode", "AUTO")).toUpperCase());
        @SuppressWarnings("unchecked")
        List<String> mediaTypes = (List<String>) body.getOrDefault("mediaTypes", List.of("VIDEO", "AUDIO", "DATA"));
        @SuppressWarnings("unchecked")
        Map<String, String> metadata = (Map<String, String>) body.getOrDefault("metadata", Map.of());

        return ResponseEntity.ok(
            sessionService.createSession(robotId, operatorId, operatorName, mode, mediaTypes, metadata));
    }

    /**
     * 获取会话详情
     */
    @GetMapping("/{sessionId}")
    public ResponseEntity<TeleopSession> getSession(@PathVariable String sessionId) {
        return ResponseEntity.ok(sessionService.getSession(sessionId));
    }

    /**
     * 查询会话列表
     */
    @GetMapping
    public ResponseEntity<List<TeleopSession>> listSessions(
            @RequestParam(required = false) String robotId,
            @RequestParam(required = false) String operatorId,
            @RequestParam(required = false) String status,
            @RequestParam(defaultValue = "50") int limit) {
        SessionStatus statusFilter = status != null
            ? SessionStatus.valueOf(status.toUpperCase()) : null;
        return ResponseEntity.ok(
            sessionService.listSessions(robotId, operatorId, statusFilter, limit));
    }

    /**
     * 请求接管控制权
     */
    @PostMapping("/{sessionId}/takeover")
    public ResponseEntity<TeleopSession> requestTakeover(@PathVariable String sessionId) {
        return ResponseEntity.ok(sessionService.requestTakeover(sessionId));
    }

    /**
     * 交还控制权
     */
    @PostMapping("/{sessionId}/handover")
    public ResponseEntity<TeleopSession> handover(@PathVariable String sessionId) {
        return ResponseEntity.ok(sessionService.handover(sessionId));
    }

    /**
     * 心跳
     */
    @PostMapping("/{sessionId}/heartbeat")
    public ResponseEntity<Map<String, Object>> heartbeat(@PathVariable String sessionId) {
        TeleopSession session = sessionService.heartbeat(sessionId);
        return ResponseEntity.ok(Map.of(
            "sessionId", session.getSessionId(),
            "status", session.getSessionStatus().name(),
            "timestamp", System.currentTimeMillis()
        ));
    }

    /**
     * 更新 WebRTC 连接信息
     */
    @PutMapping("/{sessionId}/webrtc")
    public ResponseEntity<TeleopSession> updateWebRTC(
            @PathVariable String sessionId,
            @RequestBody Map<String, String> body) {
        return ResponseEntity.ok(sessionService.updateWebRTC(
            sessionId,
            body.get("sdpOffer"),
            body.get("sdpAnswer"),
            body.get("iceCandidates")
        ));
    }

    /**
     * 关闭会话
     */
    @DeleteMapping("/{sessionId}")
    public ResponseEntity<Map<String, Object>> closeSession(
            @PathVariable String sessionId,
            @RequestParam(defaultValue = "operator_request") String reason) {
        sessionService.closeSession(sessionId, reason);
        return ResponseEntity.ok(Map.of(
            "sessionId", sessionId,
            "status", "CLOSED",
            "reason", reason
        ));
    }

    /**
     * 获取会话统计
     */
    @GetMapping("/stats")
    public ResponseEntity<Map<String, Object>> getStats() {
        return ResponseEntity.ok(sessionService.getSessionStats());
    }
}
