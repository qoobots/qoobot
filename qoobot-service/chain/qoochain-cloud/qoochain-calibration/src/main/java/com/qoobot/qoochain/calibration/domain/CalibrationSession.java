package com.qoobot.qoochain.calibration.domain;

import com.qoobot.qoochain.common.entity.BaseEntity;
import jakarta.persistence.*;
import lombok.*;
import java.time.Instant;

@Entity
@Table(name = "calibration_session")
@Data @NoArgsConstructor @AllArgsConstructor
@EqualsAndHashCode(callSuper = true)
public class CalibrationSession extends BaseEntity {
    @Column(name = "robot_id", nullable = false)
    private Long robotId;
    @Column(name = "session_version", nullable = false, length = 32)
    private String sessionVersion;
    @Column(name = "calib_type", nullable = false, length = 16)
    private String calibType; // CAMERA, IMU, LIDAR, KINEMATIC, FORCE, ALL
    @Column(name = "operator_id", nullable = false, length = 64)
    private String operatorId;
    @Column(nullable = false, length = 16)
    @Enumerated(EnumType.STRING)
    private SessionStatus status = SessionStatus.IN_PROGRESS;
    @Column(name = "started_at", nullable = false)
    private Instant startedAt = Instant.now();
    @Column(name = "completed_at")
    private Instant completedAt;
    @Column(name = "report_url", length = 512)
    private String reportUrl;

    public enum SessionStatus { IN_PROGRESS, PASSED, FAILED }
}
