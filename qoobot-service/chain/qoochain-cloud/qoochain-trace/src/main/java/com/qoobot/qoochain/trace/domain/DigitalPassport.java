package com.qoobot.qoochain.trace.domain;

import com.qoobot.qoochain.common.entity.BaseEntity;
import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;
import java.time.Instant;
import java.util.Map;

@Entity
@Table(name = "digital_passport")
@Data @NoArgsConstructor @AllArgsConstructor
@EqualsAndHashCode(callSuper = true)
public class DigitalPassport extends BaseEntity {
    @OneToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "robot_id", nullable = false, unique = true)
    private Robot robot;
    @Column(name = "passport_data", nullable = false, columnDefinition = "jsonb")
    @JdbcTypeCode(SqlTypes.JSON)
    private Map<String, Object> passportData;
    @Column(name = "pdf_url", length = 512)
    private String pdfUrl;
    @Column(name = "digital_signature", columnDefinition = "TEXT")
    private String digitalSignature;
    @Column(name = "issued_at", nullable = false)
    private Instant issuedAt = Instant.now();
}
