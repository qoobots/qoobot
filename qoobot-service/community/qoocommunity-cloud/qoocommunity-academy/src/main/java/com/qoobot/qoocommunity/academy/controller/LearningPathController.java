package com.qoobot.qoocommunity.academy.controller;

import com.qoobot.qoocommunity.academy.domain.LearningPath;
import com.qoobot.qoocommunity.academy.domain.LessonProgress;
import com.qoobot.qoocommunity.academy.dto.request.ProgressUpdateRequest;
import com.qoobot.qoocommunity.academy.dto.response.LearningProgressResponse;
import com.qoobot.qoocommunity.academy.service.LearningPathService;
import com.qoobot.qoocommunity.common.dto.ApiResponse;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/v1/academy")
@RequiredArgsConstructor
public class LearningPathController {

    private final LearningPathService learningPathService;

    @GetMapping("/learning-paths")
    public ApiResponse<List<LearningPath>> listLearningPaths() {
        return ApiResponse.success(learningPathService.listLearningPaths());
    }

    @GetMapping("/learning-paths/{slug}")
    public ApiResponse<LearningPath> getLearningPath(@PathVariable String slug) {
        return ApiResponse.success(learningPathService.getLearningPath(slug));
    }

    @GetMapping("/my-progress")
    public ApiResponse<LearningProgressResponse> getMyProgress(
            @RequestHeader("X-User-Id") String userId) {
        List<LessonProgress> progress = learningPathService.getUserProgress(userId);
        long completed = learningPathService.getUserCompletedLessons(userId);
        return ApiResponse.success(new LearningProgressResponse(progress, completed));
    }

    @PostMapping("/lessons/{lessonId}/complete")
    public ApiResponse<LessonProgress> markLessonComplete(
            @PathVariable Long lessonId,
            @RequestHeader("X-User-Id") String userId) {
        return ApiResponse.success(learningPathService.markLessonComplete(userId, lessonId));
    }

    @DeleteMapping("/lessons/{lessonId}/complete")
    public ApiResponse<Void> markLessonIncomplete(
            @PathVariable Long lessonId,
            @RequestHeader("X-User-Id") String userId) {
        learningPathService.markLessonIncomplete(userId, lessonId);
        return ApiResponse.success("OK", null);
    }

    @PostMapping("/progress")
    public ApiResponse<LessonProgress> updateLessonProgress(
            @Valid @RequestBody ProgressUpdateRequest request,
            @RequestHeader("X-User-Id") String userId) {
        if (Boolean.TRUE.equals(request.getIsCompleted())) {
            return ApiResponse.success(learningPathService.markLessonComplete(userId, request.getLessonId()));
        }
        return ApiResponse.success(null);
    }
}
