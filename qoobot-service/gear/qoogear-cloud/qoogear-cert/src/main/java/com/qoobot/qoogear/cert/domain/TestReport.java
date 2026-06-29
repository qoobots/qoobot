package com.qoobot.qoogear.cert.domain;

import com.qoobot.qoogear.common.entity.BaseEntity;
import jakarta.persistence.*;
import lombok.Data;
import lombok.EqualsAndHashCode;
import java.time.ZonedDateTime;
import java.util.List;

@Data
@Entity
@Table(name = "test_reports")
@EqualsAndHashCode(callSuper = true)
public class TestReport extends BaseEntity {

    @Column(name = "application_id", nullable = false)
    private Long applicationId;

    @Column(name = "laboratory_id", nullable = false)
    private Long laboratoryId;

    @Column(name = "test_engineer", length = 100)
    private String testEngineer;

    @Column(name = "overall_result", nullable = false, length = 20)
    private String overallResult;

    @Column(columnDefinition = "TEXT")
    private String summary;

    @Column(name = "test_data_json", columnDefinition = "JSONB")
    private String testDataJson;

    @Column(name = "attachments", columnDefinition = "varchar(500)[]")
    private List<String> attachments;

    @Column(name = "submitted_at", nullable = false)
    private ZonedDateTime submittedAt;
}
