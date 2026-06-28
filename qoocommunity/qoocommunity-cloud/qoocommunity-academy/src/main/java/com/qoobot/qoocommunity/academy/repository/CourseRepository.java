package com.qoobot.qoocommunity.academy.repository;

import com.qoobot.qoocommunity.academy.domain.Course;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;

public interface CourseRepository extends JpaRepository<Course, Long> {
    Page<Course> findByIsPublishedTrueOrderByCreatedAtDesc(Pageable pageable);
    Page<Course> findByLevelAndIsPublishedTrue(String level, Pageable pageable);
    Page<Course> findByCategoryAndIsPublishedTrue(String category, Pageable pageable);
}
