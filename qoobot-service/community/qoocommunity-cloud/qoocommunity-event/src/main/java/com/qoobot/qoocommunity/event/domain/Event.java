package com.qoobot.qoocommunity.event.domain;

import jakarta.persistence.*;
import lombok.Data;
import lombok.EqualsAndHashCode;

import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "events")
@EqualsAndHashCode(callSuper = true)
public class Event extends com.qoobot.qoocommunity.common.entity.BaseEntity {

    @Column(nullable = false, length = 500)
    private String title;

    @Column(nullable = false, unique = true, length = 200)
    private String slug;

    @Column(nullable = false, length = 30)
    private String type;

    @Column(columnDefinition = "TEXT")
    private String description;

    @Column(name = "content_html", columnDefinition = "TEXT")
    private String contentHtml;

    @Column(name = "cover_url", length = 512)
    private String coverUrl;

    @Column(length = 500)
    private String location;

    @Column(name = "start_time", nullable = false)
    private LocalDateTime startTime;

    @Column(name = "end_time", nullable = false)
    private LocalDateTime endTime;

    @Column(length = 50)
    private String timezone = "Asia/Shanghai";

    @Column(name = "max_attendees")
    private Integer maxAttendees;

    @Column(name = "current_attendees")
    private Integer currentAttendees = 0;

    @Column(length = 20)
    private String status = "DRAFT";

    @Column(name = "is_featured")
    private Boolean isFeatured = false;

    @Column(name = "created_by", nullable = false, length = 64)
    private String createdBy;
}
