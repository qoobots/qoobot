package com.qoobot.qoogear.cert.domain;

import com.qoobot.qoogear.common.entity.BaseEntity;
import jakarta.persistence.*;
import lombok.Data;
import lombok.EqualsAndHashCode;
import java.time.ZonedDateTime;
import java.util.List;

@Data
@Entity
@Table(name = "cert_applications")
@EqualsAndHashCode(callSuper = true)
public class CertApplication extends BaseEntity {

    @Column(name = "developer_id", nullable = false)
    private Long developerId;

    @Column(name = "product_name", nullable = false, length = 200)
    private String productName;

    @Column(name = "product_category", nullable = false, length = 50)
    private String productCategory;

    @Column(name = "product_model", nullable = false, length = 100)
    private String productModel;

    @Column(name = "product_description", columnDefinition = "TEXT")
    private String productDescription;

    @Column(name = "cert_level", nullable = false, length = 20)
    private String certLevel;

    @Column(name = "standard_ids", columnDefinition = "bigint[]")
    private List<Long> standardIds;

    @Column(name = "mechanical_spec_url", length = 500)
    private String mechanicalSpecUrl;

    @Column(name = "electrical_spec_url", length = 500)
    private String electricalSpecUrl;

    @Column(name = "communication_protocol_url", length = 500)
    private String communicationProtocolUrl;

    @Column(name = "firmware_source_url", length = 500)
    private String firmwareSourceUrl;

    @Column(name = "test_samples_count")
    private Integer testSamplesCount = 2;

    @Column(nullable = false, length = 30)
    private String status = "draft";

    @Column(name = "submitted_at")
    private ZonedDateTime submittedAt;

    @Column(name = "reviewed_by")
    private Long reviewedBy;

    @Column(name = "review_comment", columnDefinition = "TEXT")
    private String reviewComment;

    @Column(name = "reviewed_at")
    private ZonedDateTime reviewedAt;

    @Column(name = "assigned_lab_id")
    private Long assignedLabId;

    @Column(name = "assigned_at")
    private ZonedDateTime assignedAt;

    @Column(name = "approved_at")
    private ZonedDateTime approvedAt;

    @Column(name = "rejection_reason", columnDefinition = "TEXT")
    private String rejectionReason;
}
