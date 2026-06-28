package com.qoobot.qoocloud.teleop.entity;

import jakarta.persistence.*;
import java.time.Instant;
import java.util.List;
import java.util.UUID;

/**
 * 遥控会话实体
 */
@Entity
@Table(name = "teleop_sessions", indexes = {
    @Index(name = "idx_sessions_robot", columnList = "robotId,createdAt DESC"),
    @Index(name = "idx_sessions_operator", columnList = "operatorId,createdAt DESC"),
    @Index(name = "idx_sessions_status", columnList = "sessionStatus")
})
public class TeleopSession {

    @Id
    @Column(name = "session_id", length = 36)
    private String sessionId = UUID.randomUUID().toString();

    @Column(name = "robot_id", nullable = false, length = 64)
    private String robotId;

    @Column(name = "operator_id", nullable = false, length = 128)
    private String operatorId;

    @Column(name = "operator_name", length = 128)
    private String operatorName;

    @Enumerated(EnumType.STRING)
    @Column(name = "control_mode", length = 16)
    private ControlMode controlMode = ControlMode.AUTO;

    @Enumerated(EnumType.STRING)
    @Column(name = "session_status", length = 16)
    private SessionStatus sessionStatus = SessionStatus.INITIATING;

    @Column(name = "media_types", columnDefinition = "jsonb")
    private String mediaTypes = "[]";

    @Column(name = "sdp_offer", columnDefinition = "text")
    private String sdpOffer;

    @Column(name = "sdp_answer", columnDefinition = "text")
    private String sdpAnswer;

    @Column(name = "ice_candidates", columnDefinition = "jsonb")
    private String iceCandidates = "[]";

    @Column(name = "created_at")
    private Instant createdAt = Instant.now();

    @Column(name = "connected_at")
    private Instant connectedAt;

    @Column(name = "takeover_at")
    private Instant takeoverAt;

    @Column(name = "handover_at")
    private Instant handoverAt;

    @Column(name = "closed_at")
    private Instant closedAt;

    @Column(name = "last_heartbeat")
    private Instant lastHeartbeat;

    @Column(name = "command_count")
    private Long commandCount = 0L;

    @Column(name = "video_bytes_sent")
    private Long videoBytesSent = 0L;

    @Column(name = "audio_bytes_sent")
    private Long audioBytesSent = 0L;

    @Column(name = "max_latency_ms")
    private Integer maxLatencyMs = 0;

    @Column(name = "avg_latency_ms")
    private Integer avgLatencyMs = 0;

    // ========== 枚举 ==========

    public enum ControlMode {
        AUTO, HYBRID, TELEOP
    }

    public enum SessionStatus {
        INITIATING, CONNECTING, ACTIVE, PAUSED, CLOSING, CLOSED, REJECTED, TIMEOUT
    }

    public enum MediaType {
        VIDEO, AUDIO, DATA
    }

    // ========== Getters & Setters ==========

    public String getSessionId() { return sessionId; }
    public void setSessionId(String sessionId) { this.sessionId = sessionId; }

    public String getRobotId() { return robotId; }
    public void setRobotId(String robotId) { this.robotId = robotId; }

    public String getOperatorId() { return operatorId; }
    public void setOperatorId(String operatorId) { this.operatorId = operatorId; }

    public String getOperatorName() { return operatorName; }
    public void setOperatorName(String operatorName) { this.operatorName = operatorName; }

    public ControlMode getControlMode() { return controlMode; }
    public void setControlMode(ControlMode controlMode) { this.controlMode = controlMode; }

    public SessionStatus getSessionStatus() { return sessionStatus; }
    public void setSessionStatus(SessionStatus sessionStatus) { this.sessionStatus = sessionStatus; }

    public String getMediaTypes() { return mediaTypes; }
    public void setMediaTypes(String mediaTypes) { this.mediaTypes = mediaTypes; }

    public String getSdpOffer() { return sdpOffer; }
    public void setSdpOffer(String sdpOffer) { this.sdpOffer = sdpOffer; }

    public String getSdpAnswer() { return sdpAnswer; }
    public void setSdpAnswer(String sdpAnswer) { this.sdpAnswer = sdpAnswer; }

    public String getIceCandidates() { return iceCandidates; }
    public void setIceCandidates(String iceCandidates) { this.iceCandidates = iceCandidates; }

    public Instant getCreatedAt() { return createdAt; }
    public void setCreatedAt(Instant createdAt) { this.createdAt = createdAt; }

    public Instant getConnectedAt() { return connectedAt; }
    public void setConnectedAt(Instant connectedAt) { this.connectedAt = connectedAt; }

    public Instant getTakeoverAt() { return takeoverAt; }
    public void setTakeoverAt(Instant takeoverAt) { this.takeoverAt = takeoverAt; }

    public Instant getHandoverAt() { return handoverAt; }
    public void setHandoverAt(Instant handoverAt) { this.handoverAt = handoverAt; }

    public Instant getClosedAt() { return closedAt; }
    public void setClosedAt(Instant closedAt) { this.closedAt = closedAt; }

    public Instant getLastHeartbeat() { return lastHeartbeat; }
    public void setLastHeartbeat(Instant lastHeartbeat) { this.lastHeartbeat = lastHeartbeat; }

    public Long getCommandCount() { return commandCount; }
    public void setCommandCount(Long commandCount) { this.commandCount = commandCount; }

    public Long getVideoBytesSent() { return videoBytesSent; }
    public void setVideoBytesSent(Long videoBytesSent) { this.videoBytesSent = videoBytesSent; }

    public Long getAudioBytesSent() { return audioBytesSent; }
    public void setAudioBytesSent(Long audioBytesSent) { this.audioBytesSent = audioBytesSent; }

    public Integer getMaxLatencyMs() { return maxLatencyMs; }
    public void setMaxLatencyMs(Integer maxLatencyMs) { this.maxLatencyMs = maxLatencyMs; }

    public Integer getAvgLatencyMs() { return avgLatencyMs; }
    public void setAvgLatencyMs(Integer avgLatencyMs) { this.avgLatencyMs = avgLatencyMs; }
}
