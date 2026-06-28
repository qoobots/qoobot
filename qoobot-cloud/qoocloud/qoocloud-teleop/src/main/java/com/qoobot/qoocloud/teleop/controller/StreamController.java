package com.qoobot.qoocloud.teleop.controller;

import com.qoobot.qoocloud.teleop.service.StreamForwarderService;
import com.qoobot.qoocloud.teleop.service.StreamForwarderService.*;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

/**
 * 媒体流管理 API
 */
@RestController
@RequestMapping("/api/v1/teleop/streams")
public class StreamController {

    private final StreamForwarderService streamService;

    public StreamController(StreamForwarderService streamService) {
        this.streamService = streamService;
    }

    /**
     * 注册媒体流
     */
    @PostMapping("/{sessionId}")
    public ResponseEntity<StreamInfo> registerStream(
            @PathVariable String sessionId,
            @RequestBody Map<String, Object> body) {
        String trackId = (String) body.get("trackId");
        StreamType type = StreamType.valueOf(
            ((String) body.get("type")).toUpperCase());
        StreamDirection direction = StreamDirection.valueOf(
            ((String) body.getOrDefault("direction", "UPSTREAM")).toUpperCase());
        @SuppressWarnings("unchecked")
        Map<String, Object> config = (Map<String, Object>) body.getOrDefault("config", Map.of());

        return ResponseEntity.ok(
            streamService.registerStream(sessionId, trackId, type, direction, config));
    }

    /**
     * 流控制（暂停/恢复/切换）
     */
    @PutMapping("/{sessionId}/{trackId}")
    public ResponseEntity<StreamInfo> controlStream(
            @PathVariable String sessionId,
            @PathVariable String trackId,
            @RequestBody Map<String, Object> body) {
        StreamAction action = StreamAction.valueOf(
            ((String) body.get("action")).toUpperCase());
        @SuppressWarnings("unchecked")
        Map<String, Object> params = (Map<String, Object>) body.getOrDefault("params", Map.of());

        return ResponseEntity.ok(
            streamService.controlStream(sessionId, trackId, action, params));
    }

    /**
     * 移除媒体流
     */
    @DeleteMapping("/{sessionId}/{trackId}")
    public ResponseEntity<Map<String, String>> unregisterStream(
            @PathVariable String sessionId,
            @PathVariable String trackId) {
        streamService.unregisterStream(sessionId, trackId);
        return ResponseEntity.ok(Map.of("status", "removed"));
    }

    /**
     * 更新流统计
     */
    @PutMapping("/{sessionId}/{trackId}/stats")
    public ResponseEntity<Map<String, String>> updateStats(
            @PathVariable String sessionId,
            @PathVariable String trackId,
            @RequestBody Map<String, Object> body) {
        StreamDirection direction = StreamDirection.valueOf(
            ((String) body.getOrDefault("direction", "UPSTREAM")).toUpperCase());
        long bytes = ((Number) body.getOrDefault("bytes", 0)).longValue();
        int bitrateKbps = ((Number) body.getOrDefault("bitrateKbps", 0)).intValue();
        int fps = ((Number) body.getOrDefault("fps", 0)).intValue();
        int rttMs = ((Number) body.getOrDefault("rttMs", 0)).intValue();
        int jitterMs = ((Number) body.getOrDefault("jitterMs", 0)).intValue();
        long packetsSent = ((Number) body.getOrDefault("packetsSent", 0)).longValue();
        long packetsLost = ((Number) body.getOrDefault("packetsLost", 0)).longValue();

        streamService.updateStreamStats(sessionId, trackId, direction,
            bytes, bitrateKbps, fps, rttMs, jitterMs, packetsSent, packetsLost);
        return ResponseEntity.ok(Map.of("status", "updated"));
    }

    /**
     * 获取所有流统计
     */
    @GetMapping("/{sessionId}/stats")
    public ResponseEntity<AllStreamStats> getAllStats(@PathVariable String sessionId) {
        return ResponseEntity.ok(streamService.getAllStreamStats(sessionId));
    }
}
