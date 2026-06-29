package com.qoobot.qoochain.aftermarket.domain;

import com.qoobot.qoochain.common.entity.BaseEntity;
import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;
import java.time.Instant;
import java.util.List;
import java.util.Map;

@Entity
@Table(name = "repair_order")
@Data @NoArgsConstructor @AllArgsConstructor
@EqualsAndHashCode(callSuper = true)
public class RepairOrder extends BaseEntity {
    @Column(name = "order_number", nullable = false, unique = true, length = 64)
    private String orderNumber;
    @Column(name = "robot_id", nullable = false)
    private Long robotId;
    @Column(name = "customer_name", length = 128)
    private String customerName;
    @Column(name = "fault_category", nullable = false, length = 64)
    private String faultCategory;
    @Column(name = "fault_description", columnDefinition = "TEXT")
    private String faultDescription;
    @Column(name = "diagnosis_result", columnDefinition = "TEXT")
    private String diagnosisResult;
    @Column(name = "repair_action", columnDefinition = "TEXT")
    private String repairAction;
    @Column(name = "spare_parts_used", columnDefinition = "jsonb")
    @JdbcTypeCode(SqlTypes.JSON)
    private List<Map<String, Object>> sparePartsUsed;
    @Column(nullable = false, length = 16)
    @Enumerated(EnumType.STRING)
    private RepairStatus status = RepairStatus.OPEN;
    @Column(length = 8)
    @Enumerated(EnumType.STRING)
    private Priority priority = Priority.NORMAL;
    @Column(name = "closed_at")
    private Instant closedAt;

    public enum RepairStatus { OPEN, DIAGNOSING, REPAIRING, TESTING, CLOSED }
    public enum Priority { LOW, NORMAL, HIGH, CRITICAL }
}
