package com.qoobot.qoocommunity.academy.repository;

import com.qoobot.qoocommunity.academy.domain.Enrollment;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;

public interface EnrollmentRepository extends JpaRepository<Enrollment, Long> {
    Optional<Enrollment> findByUserIdAndCourseId(String userId, Long courseId);
    List<Enrollment> findByUserIdOrderByUpdatedAtDesc(String userId);
    long countByCourseId(Long courseId);
}
