package com.qoobot.qoocommunity.event.domain;

import jakarta.persistence.*;
import lombok.Data;
import lombok.EqualsAndHashCode;

@Data
@Entity
@Table(name = "event_materials")
@EqualsAndHashCode(callSuper = true)
public class EventMaterial extends com.qoobot.qoocommunity.common.entity.BaseEntity {

    @Column(name = "event_id", nullable = false)
    private Long eventId;

    @Column(nullable = false, length = 500)
    private String title;

    @Column(name = "file_url", nullable = false, length = 512)
    private String fileUrl;

    @Column(name = "file_type", length = 50)
    private String fileType;

    @Column(name = "file_size")
    private Long fileSize;

    @Column(name = "download_count")
    private Integer downloadCount = 0;
}
