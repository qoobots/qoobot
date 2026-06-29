package com.qoobot.qoocloud.teleop.entity;

import jakarta.persistence.*;
import java.time.Instant;
import java.util.UUID;

/**
 * 示教记录实体
 */
@Entity
@Table(name = "teaching_records", indexes = {
    @Index(name = "idx_teaching_robot", columnList = "robotId,createdAt DESC"),
    @Index(name = "idx_teaching_operator", columnList = "operatorId,createdAt DESC")
})
public class TeachingRecord {

    @Id
    @Column(name = "record_id", length = 36)
    private String recordId = UUID.randomUUID().toString();

    @Column(name = "session_id", nullable = false, length = 36)
    private String sessionId;

    @Column(name = "operator_id", nullable = false, length = 128)
    private String operatorId;

    @Column(name = "robot_id", nullable = false, length = 64)
    private String robotId;

    @Column(nullable = false, length = 256)
    private String name;

    @Column(columnDefinition = "text")
    private String description;

    @Column(columnDefinition = "jsonb")
    private String tags = "[]";

    @Column(name = "duration_ms")
    private Long durationMs;

    @Column(name = "frame_count")
    private Integer frameCount;

    @Column(name = "data_format", length = 32)
    private String dataFormat = "v1.0";

    @Column(name = "trajectory_path", length = 512)
    private String trajectoryPath;

    @Column(name = "sensor_data_path", length = 512)
    private String sensorDataPath;

    @Column(name = "video_path", length = 512)
    private String videoPath;

    @Column(name = "quality_score")
    private Float qualityScore;

    @Column(name = "is_verified")
    private Boolean isVerified = false;

    @Column(name = "created_at")
    private Instant createdAt = Instant.now();

    // ========== Getters & Setters ==========

    public String getRecordId() { return recordId; }
    public void setRecordId(String recordId) { this.recordId = recordId; }

    public String getSessionId() { return sessionId; }
    public void setSessionId(String sessionId) { this.sessionId = sessionId; }

    public String getOperatorId() { return operatorId; }
    public void setOperatorId(String operatorId) { this.operatorId = operatorId; }

    public String getRobotId() { return robotId; }
    public void setRobotId(String robotId) { this.robotId = robotId; }

    public String getName() { return name; }
    public void setName(String name) { this.name = name; }

    public String getDescription() { return description; }
    public void setDescription(String description) { this.description = description; }

    public String getTags() { return tags; }
    public void setTags(String tags) { this.tags = tags; }

    public Long getDurationMs() { return durationMs; }
    public void setDurationMs(Long durationMs) { this.durationMs = durationMs; }

    public Integer getFrameCount() { return frameCount; }
    public void setFrameCount(Integer frameCount) { this.frameCount = frameCount; }

    public String getDataFormat() { return dataFormat; }
    public void setDataFormat(String dataFormat) { this.dataFormat = dataFormat; }

    public String getTrajectoryPath() { return trajectoryPath; }
    public void setTrajectoryPath(String trajectoryPath) { this.trajectoryPath = trajectoryPath; }

    public String getSensorDataPath() { return sensorDataPath; }
    public void setSensorDataPath(String sensorDataPath) { this.sensorDataPath = sensorDataPath; }

    public String getVideoPath() { return videoPath; }
    public void setVideoPath(String videoPath) { this.videoPath = videoPath; }

    public Float getQualityScore() { return qualityScore; }
    public void setQualityScore(Float qualityScore) { this.qualityScore = qualityScore; }

    public Boolean getIsVerified() { return isVerified; }
    public void setIsVerified(Boolean isVerified) { this.isVerified = isVerified; }

    public Instant getCreatedAt() { return createdAt; }
    public void setCreatedAt(Instant createdAt) { this.createdAt = createdAt; }
}
