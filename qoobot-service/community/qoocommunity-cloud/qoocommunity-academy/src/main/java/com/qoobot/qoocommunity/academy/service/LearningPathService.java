package com.qoobot.qoocommunity.academy.service;

import com.qoobot.qoocommunity.academy.domain.LearningPath;
import com.qoobot.qoocommunity.academy.domain.LessonProgress;
import com.qoobot.qoocommunity.academy.repository.LearningPathRepository;
import com.qoobot.qoocommunity.academy.repository.LessonProgressRepository;
import com.qoobot.qoocommunity.common.exception.QooCommunityException;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;

@Slf4j
@Service
@RequiredArgsConstructor
public class LearningPathService {

    private final LearningPathRepository learningPathRepository;
    private final LessonProgressRepository lessonProgressRepository;

    public List<LearningPath> listLearningPaths() {
        return learningPathRepository.findByIsPublishedTrueOrderBySortOrderAsc();
    }

    public LearningPath getLearningPath(String slug) {
        return learningPathRepository.findBySlug(slug)
                .orElseThrow(() -> QooCommunityException.notFound("LearningPath not found: " + slug));
    }

    public List<LessonProgress> getUserProgress(String userId) {
        return lessonProgressRepository.findByUserId(userId);
    }

    public long getUserCompletedLessons(String userId) {
        return lessonProgressRepository.countByUserIdAndIsCompletedTrue(userId);
    }

    @Transactional
    public LessonProgress markLessonComplete(String userId, Long lessonId) {
        LessonProgress progress = lessonProgressRepository
                .findByUserIdAndLessonId(userId, lessonId)
                .orElse(new LessonProgress());

        progress.setUserId(userId);
        progress.setLessonId(lessonId);
        progress.setIsCompleted(true);
        progress.setCompletedAt(LocalDateTime.now());

        log.info("User {} completed lesson {}", userId, lessonId);
        return lessonProgressRepository.save(progress);
    }

    @Transactional
    public void markLessonIncomplete(String userId, Long lessonId) {
        lessonProgressRepository.findByUserIdAndLessonId(userId, lessonId)
                .ifPresent(progress -> {
                    progress.setIsCompleted(false);
                    progress.setCompletedAt(null);
                    lessonProgressRepository.save(progress);
                    log.info("User {} unmarked lesson {}", userId, lessonId);
                });
    }
}
