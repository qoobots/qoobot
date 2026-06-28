package com.qoobot.qoochain.logistics.domain;

import com.qoobot.qoochain.common.entity.BaseEntity;
import jakarta.persistence.*;
import lombok.*;

@Entity
@Table(name = "serial_number_pool")
@Data @NoArgsConstructor @AllArgsConstructor
@EqualsAndHashCode(callSuper = true)
public class SerialNumberPool extends BaseEntity {
    @Column(nullable = false, length = 32)
    private String prefix;
    @Column(name = "start_number", nullable = false)
    private long startNumber;
    @Column(name = "end_number", nullable = false)
    private long endNumber;
    @Column(name = "current_number", nullable = false)
    private long currentNumber;
    @Column(nullable = false, length = 16)
    @Enumerated(EnumType.STRING)
    private PoolStatus status = PoolStatus.ACTIVE;

    public enum PoolStatus { ACTIVE, EXHAUSTED, DISABLED }
}
