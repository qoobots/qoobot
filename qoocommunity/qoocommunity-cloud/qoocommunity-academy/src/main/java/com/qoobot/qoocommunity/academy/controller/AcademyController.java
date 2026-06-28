package com.qoobot.qoocommunity.academy.controller;

import com.qoobot.qoocommunity.common.dto.ApiResponse;
import com.qoobot.qoocommunity.common.dto.PageResponse;
import com.qoobot.qoocommunity.academy.domain.*;
import com.qoobot.qoocommunity.academy.service.CourseService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/v1/academy")
@RequiredArgsConstructor
public class AcademyController {

    private final CourseService courseService;

    // ---- Courses ----

    @GetMapping("/courses")
    public ApiResponse<PageResponse<Course>> listCourses(
            @RequestParam(required = false) String level,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {
        if (level != null) {
            return ApiResponse.success(courseService.listByLevel(level.toUpperCase(), page, size));
        }
        return ApiResponse.success(courseService.listCourses(page, size));
    }

    @GetMapping("/courses/{id}")
    public ApiResponse<Course> getCourse(@PathVariable Long id) {
        return ApiResponse.success(courseService.getCourse(id));
    }

    @GetMapping("/courses/{id}/lessons")
    public ApiResponse<List<Lesson>> getLessons(@PathVariable Long id) {
        return ApiResponse.success(courseService.getLessons(id));
    }

    @GetMapping("/courses/{courseId}/lessons/{lessonId}")
    public ApiResponse<Lesson> getLesson(@PathVariable Long courseId, @PathVariable Long lessonId) {
        return ApiResponse.success(courseService.getLesson(courseId, lessonId));
    }

    @PostMapping("/courses/{id}/enroll")
    public ApiResponse<Enrollment> enroll(
            @PathVariable Long id, @RequestHeader("X-User-Id") String userId) {
        return ApiResponse.success(courseService.enroll(userId, id));
    }

    @PutMapping("/progress/{courseId}")
    public ApiResponse<Void> updateProgress(
            @PathVariable Long courseId,
            @RequestHeader("X-User-Id") String userId,
            @RequestBody Map<String, Integer> body) {
        courseService.updateProgress(userId, courseId, body.get("progressPct"));
        return ApiResponse.success("Updated", null);
    }

    @GetMapping("/my-courses")
    public ApiResponse<List<Enrollment>> getMyCourses(@RequestHeader("X-User-Id") String userId) {
        return ApiResponse.success(courseService.getMyCourses(userId));
    }

    // ---- Certifications ----

    @GetMapping("/certifications")
    public ApiResponse<List<Certification>> listCertifications() {
        return ApiResponse.success(courseService.listCertifications());
    }

    @PostMapping("/certifications/{id}/exam")
    public ApiResponse<UserCertification> takeExam(
            @PathVariable Long id,
            @RequestHeader("X-User-Id") String userId,
            @RequestBody Map<String, Integer> body) {
        return ApiResponse.success(courseService.takeExam(userId, id, body.get("score")));
    }

    @GetMapping("/certifications/my")
    public ApiResponse<List<UserCertification>> getMyCertifications(
            @RequestHeader("X-User-Id") String userId) {
        return ApiResponse.success(courseService.getMyCertifications(userId));
    }
}
