package com.qoobot.qoochain.line.domain;

import com.qoobot.qoochain.common.entity.BaseEntity;
import jakarta.persistence.*;
import lombok.*;
import java.time.Instant;

@Entity
@Table(name = "dfm_check")
@Data @NoArgsConstructor @AllArgsConstructor
@EqualsAndHashCode(callSuper = true)
public class DfmCheck extends BaseEntity {
    @Column(name = "product_id", nullable = false)
    private Long productId;
    @Column(name = "checklist_item", nullable = false, length = 256)
    private String checklistItem;
    @Column(nullable = false, length = 32)
    private String category; // DFM or DFA
    @Column(nullable = false, length = 16)
    @Enumerated(EnumType.STRING)
    private CheckStatus status = CheckStatus.OPEN;
    @Column(length = 8)
    @Enumerated(EnumType.STRING)
    private Severity severity = Severity.MEDIUM;
    @Column(length = 64)
    private String assignee;
    @Column(columnDefinition = "TEXT")
    private String resolution;
    @Column(name = "resolved_at")
    private Instant resolvedAt;

    public enum CheckStatus { OPEN, IN_PROGRESS, RESOLVED, CLOSED }
    public enum Severity { LOW, MEDIUM, HIGH, CRITICAL }
}
