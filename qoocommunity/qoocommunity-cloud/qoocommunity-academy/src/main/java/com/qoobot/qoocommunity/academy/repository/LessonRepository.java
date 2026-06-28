package com.qoobot.qoocommunity.academy.repository;

import com.qoobot.qoocommunity.academy.domain.Lesson;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface LessonRepository extends JpaRepository<Lesson, Long> {
    List<Lesson> findByCourseIdOrderBySortOrderAsc(Long courseId);
    long countByCourseId(Long courseId);
}
