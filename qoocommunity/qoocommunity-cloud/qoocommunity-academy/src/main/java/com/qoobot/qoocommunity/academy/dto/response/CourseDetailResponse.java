package com.qoobot.qoocommunity.academy.dto.response;

import lombok.Builder;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@Builder
public class CourseDetailResponse {

    private Long id;
    private String title;
    private String slug;
    private String description;
    private String coverUrl;
    private String level;
    private String category;
    private Integer lessonCount;
    private Integer enrolledCount;
    private Integer durationMinutes;
    private Boolean isEnrolled;
    private Integer progressPct;
    private LocalDateTime createdAt;
}
