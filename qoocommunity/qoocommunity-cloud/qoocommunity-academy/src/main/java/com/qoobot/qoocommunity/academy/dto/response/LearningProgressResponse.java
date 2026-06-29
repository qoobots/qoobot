package com.qoobot.qoocommunity.academy.dto.response;

import com.qoobot.qoocommunity.academy.domain.LessonProgress;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class LearningProgressResponse {

    private List<LessonProgress> progress;
    private long completedLessons;
    private Long courseId;
    private String courseTitle;
    private Integer totalLessons;
    private Integer progressPct;
    private Boolean isCompleted;

    public LearningProgressResponse(List<LessonProgress> progress, long completedLessons) {
        this.progress = progress;
        this.completedLessons = completedLessons;
    }
}
