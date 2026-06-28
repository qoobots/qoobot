package com.qoobot.qoocloud.teleop.controller;

import com.qoobot.qoocloud.teleop.entity.TeachingRecord;
import com.qoobot.qoocloud.teleop.service.TeachingService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

/**
 * 示教录制管理 API
 */
@RestController
@RequestMapping("/api/v1/teleop/teaching")
public class TeachingController {

    private final TeachingService teachingService;

    public TeachingController(TeachingService teachingService) {
        this.teachingService = teachingService;
    }

    /**
     * 开始示教录制
     */
    @PostMapping("/{sessionId}/start")
    public ResponseEntity<TeachingRecord> startRecording(
            @PathVariable String sessionId,
            @RequestBody Map<String, Object> body) {
        String robotId = (String) body.get("robotId");
        String operatorId = (String) body.get("operatorId");
        String name = (String) body.get("name");
        String description = (String) body.getOrDefault("description", "");
        @SuppressWarnings("unchecked")
        List<String> tags = (List<String>) body.getOrDefault("tags", List.of());

        return ResponseEntity.ok(
            teachingService.startRecording(sessionId, robotId, operatorId, name, description, tags));
    }

    /**
     * 追加示教数据帧
     */
    @PostMapping("/{sessionId}/frame")
    public ResponseEntity<TeachingService.TeachingFrameResult> appendFrame(
            @PathVariable String sessionId,
            @RequestBody Map<String, Object> frameData) {
        return ResponseEntity.ok(teachingService.appendFrame(sessionId, frameData));
    }

    /**
     * 停止示教录制
     */
    @PostMapping("/{sessionId}/stop")
    public ResponseEntity<TeachingRecord> stopRecording(@PathVariable String sessionId) {
        return ResponseEntity.ok(teachingService.stopRecording(sessionId));
    }

    /**
     * 获取示教记录
     */
    @GetMapping("/records/{recordId}")
    public ResponseEntity<TeachingRecord> getRecord(@PathVariable String recordId) {
        return ResponseEntity.ok(teachingService.getRecord(recordId));
    }

    /**
     * 按机器人查询示教记录
     */
    @GetMapping("/records")
    public ResponseEntity<List<TeachingRecord>> listRecords(
            @RequestParam(required = false) String robotId,
            @RequestParam(required = false) String operatorId,
            @RequestParam(required = false) String sessionId,
            @RequestParam(required = false) String keyword,
            @RequestParam(required = false) String tag) {
        if (keyword != null) {
            return ResponseEntity.ok(teachingService.search(keyword));
        }
        if (tag != null) {
            return ResponseEntity.ok(teachingService.findByTag(tag));
        }
        if (robotId != null) {
            return ResponseEntity.ok(teachingService.listByRobot(robotId));
        }
        if (operatorId != null) {
            return ResponseEntity.ok(teachingService.listByOperator(operatorId));
        }
        if (sessionId != null) {
            return ResponseEntity.ok(teachingService.listBySession(sessionId));
        }
        return ResponseEntity.ok(List.of());
    }

    /**
     * 验证示教记录
     */
    @PutMapping("/records/{recordId}/verify")
    public ResponseEntity<TeachingRecord> verifyRecord(
            @PathVariable String recordId,
            @RequestBody Map<String, String> body) {
        String verifiedBy = body.getOrDefault("verifiedBy", "system");
        return ResponseEntity.ok(teachingService.verifyRecord(recordId, verifiedBy));
    }

    /**
     * 删除示教记录
     */
    @DeleteMapping("/records/{recordId}")
    public ResponseEntity<Map<String, String>> deleteRecord(@PathVariable String recordId) {
        teachingService.deleteRecord(recordId);
        return ResponseEntity.ok(Map.of("recordId", recordId, "status", "deleted"));
    }

    /**
     * 获取示教统计
     */
    @GetMapping("/stats")
    public ResponseEntity<Map<String, Object>> getStats(
            @RequestParam(required = false) String robotId) {
        return ResponseEntity.ok(teachingService.getTeachingStats(robotId));
    }
}
