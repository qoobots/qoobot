package com.qoobot.qoocloud.teleop.controller;

import com.qoobot.qoocloud.teleop.service.ControlRelayService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

/**
 * 控制指令中继 API
 */
@RestController
@RequestMapping("/api/v1/teleop/control")
public class ControlController {

    private final ControlRelayService controlRelayService;

    public ControlController(ControlRelayService controlRelayService) {
        this.controlRelayService = controlRelayService;
    }

    /**
     * 中继全身运动控制指令
     */
    @PostMapping("/{sessionId}/fullbody")
    public ResponseEntity<Map<String, Object>> relayFullbody(
            @PathVariable String sessionId,
            @RequestBody Map<String, Object> body) {
        @SuppressWarnings("unchecked")
        Map<String, Object> commandData = (Map<String, Object>) body.get("command");
        long clientTimestamp = ((Number) body.getOrDefault("timestamp", System.currentTimeMillis())).longValue();

        return ResponseEntity.ok(
            controlRelayService.relayCommand(sessionId, "fullbody", commandData, clientTimestamp));
    }

    /**
     * 中继单关节控制指令
     */
    @PostMapping("/{sessionId}/joint")
    public ResponseEntity<Map<String, Object>> relayJoint(
            @PathVariable String sessionId,
            @RequestBody Map<String, Object> body) {
        @SuppressWarnings("unchecked")
        Map<String, Object> commandData = (Map<String, Object>) body.get("command");
        long clientTimestamp = ((Number) body.getOrDefault("timestamp", System.currentTimeMillis())).longValue();

        return ResponseEntity.ok(
            controlRelayService.relayCommand(sessionId, "joint", commandData, clientTimestamp));
    }

    /**
     * 中继末端执行器控制指令
     */
    @PostMapping("/{sessionId}/gripper")
    public ResponseEntity<Map<String, Object>> relayGripper(
            @PathVariable String sessionId,
            @RequestBody Map<String, Object> body) {
        @SuppressWarnings("unchecked")
        Map<String, Object> commandData = (Map<String, Object>) body.get("command");
        long clientTimestamp = ((Number) body.getOrDefault("timestamp", System.currentTimeMillis())).longValue();

        return ResponseEntity.ok(
            controlRelayService.relayCommand(sessionId, "gripper", commandData, clientTimestamp));
    }

    /**
     * 中继头部控制指令
     */
    @PostMapping("/{sessionId}/head")
    public ResponseEntity<Map<String, Object>> relayHead(
            @PathVariable String sessionId,
            @RequestBody Map<String, Object> body) {
        @SuppressWarnings("unchecked")
        Map<String, Object> commandData = (Map<String, Object>) body.get("command");
        long clientTimestamp = ((Number) body.getOrDefault("timestamp", System.currentTimeMillis())).longValue();

        return ResponseEntity.ok(
            controlRelayService.relayCommand(sessionId, "head", commandData, clientTimestamp));
    }

    /**
     * 紧急停止
     */
    @PostMapping("/{sessionId}/estop")
    public ResponseEntity<Map<String, Object>> emergencyStop(
            @PathVariable String sessionId,
            @RequestBody Map<String, Object> body) {
        long clientTimestamp = ((Number) body.getOrDefault("timestamp", System.currentTimeMillis())).longValue();

        return ResponseEntity.ok(
            controlRelayService.relayCommand(sessionId, "estop", body, clientTimestamp));
    }

    /**
     * 模式切换
     */
    @PostMapping("/{sessionId}/mode-switch")
    public ResponseEntity<Map<String, Object>> modeSwitch(
            @PathVariable String sessionId,
            @RequestBody Map<String, Object> body) {
        long clientTimestamp = ((Number) body.getOrDefault("timestamp", System.currentTimeMillis())).longValue();

        return ResponseEntity.ok(
            controlRelayService.relayCommand(sessionId, "mode_switch", body, clientTimestamp));
    }

    /**
     * 获取当前序列号
     */
    @GetMapping("/{sessionId}/sequence")
    public ResponseEntity<Map<String, Object>> getSequence(@PathVariable String sessionId) {
        return ResponseEntity.ok(Map.of(
            "sessionId", sessionId,
            "currentSequence", controlRelayService.getCurrentSequence(sessionId)
        ));
    }
}
