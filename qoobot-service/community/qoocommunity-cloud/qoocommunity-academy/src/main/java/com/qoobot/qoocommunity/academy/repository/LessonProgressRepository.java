package com.qoobot.qoocommunity.academy.repository;

import com.qoobot.qoocommunity.academy.domain.LessonProgress;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface LessonProgressRepository extends JpaRepository<LessonProgress, Long> {

    List<LessonProgress> findByUserId(String userId);

    Optional<LessonProgress> findByUserIdAndLessonId(String userId, Long lessonId);

    long countByUserIdAndIsCompletedTrue(String userId);
}
