package com.qoobot.qoochain.quality.domain;

import com.qoobot.qoochain.common.entity.BaseEntity;
import jakarta.persistence.*;
import lombok.*;
import java.time.Instant;

@Entity
@Table(name = "burn_in_test")
@Data @NoArgsConstructor @AllArgsConstructor
@EqualsAndHashCode(callSuper = true)
public class BurnInTest extends BaseEntity {
    @Column(name = "robot_id", nullable = false)
    private Long robotId;
    @Column(name = "duration_hours", nullable = false)
    private int durationHours;
    @Column(name = "started_at", nullable = false)
    private Instant startedAt = Instant.now();
    @Column(name = "completed_at")
    private Instant completedAt;
    @Column(nullable = false, length = 16)
    @Enumerated(EnumType.STRING)
    private BurnInStatus status = BurnInStatus.RUNNING;
    @Column(name = "failure_reason", columnDefinition = "TEXT")
    private String failureReason;
    @Column(name = "log_url", length = 512)
    private String logUrl;

    public enum BurnInStatus { RUNNING, PASSED, FAILED, ABORTED }
}
