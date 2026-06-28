package com.qoobot.qoogear.developer.domain;

import com.qoobot.qoogear.common.entity.BaseEntity;
import jakarta.persistence.*;
import lombok.Data;
import lombok.EqualsAndHashCode;
import java.time.ZonedDateTime;

@Data
@Entity
@Table(name = "reference_designs")
@EqualsAndHashCode(callSuper = true)
public class ReferenceDesign extends BaseEntity {

    @Column(nullable = false, length = 300)
    private String title;

    @Column(nullable = false, length = 50)
    private String category;

    @Column(columnDefinition = "TEXT")
    private String description;

    @Column(name = "files", nullable = false, columnDefinition = "JSONB")
    private String files;

    @Column(name = "download_count")
    private Long downloadCount = 0L;

    @Column(name = "published_at", nullable = false)
    private ZonedDateTime publishedAt;
}
