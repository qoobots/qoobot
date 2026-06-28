package com.qoobot.qoogear.standard.domain;

import com.qoobot.qoogear.common.entity.BaseEntity;
import jakarta.persistence.*;
import lombok.Data;
import lombok.EqualsAndHashCode;
import java.time.ZonedDateTime;

@Data
@Entity
@Table(name = "standard_specs")
@EqualsAndHashCode(callSuper = true)
public class StandardSpec extends BaseEntity {

    @Column(name = "category_id", nullable = false)
    private Long categoryId;

    @Column(nullable = false, length = 300)
    private String title;

    @Column(name = "spec_number", nullable = false, length = 50)
    private String specNumber;

    @Column(nullable = false, length = 20)
    private String version;

    @Column(nullable = false, length = 20)
    private String status = "draft";

    @Column(columnDefinition = "TEXT")
    private String description;

    @Column(name = "spec_doc_url", nullable = false, length = 500)
    private String specDocUrl;

    @Column(columnDefinition = "TEXT")
    private String changelog;

    @Column(name = "published_at")
    private ZonedDateTime publishedAt;

    @Column(name = "deprecated_at")
    private ZonedDateTime deprecatedAt;

    public boolean isPublished() {
        return "published".equals(status);
    }

    public boolean isDeprecated() {
        return "deprecated".equals(status);
    }
}
