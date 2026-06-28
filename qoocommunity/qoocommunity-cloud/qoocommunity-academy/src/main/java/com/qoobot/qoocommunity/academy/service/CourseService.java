package com.qoobot.qoocommunity.academy.service;

import com.qoobot.qoocommunity.common.dto.PageResponse;
import com.qoobot.qoocommunity.common.exception.QooCommunityException;
import com.qoobot.qoocommunity.academy.domain.*;
import com.qoobot.qoocommunity.academy.repository.*;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;

@Slf4j
@Service
@RequiredArgsConstructor
public class CourseService {

    private final CourseRepository courseRepository;
    private final LessonRepository lessonRepository;
    private final EnrollmentRepository enrollmentRepository;
    private final CertificationRepository certificationRepository;
    private final UserCertificationRepository userCertificationRepository;

    public PageResponse<Course> listCourses(int page, int size) {
        Page<Course> result = courseRepository.findByIsPublishedTrueOrderByCreatedAtDesc(PageRequest.of(page, size));
        return PageResponse.of(result.getContent(), result.getTotalElements(), page, size);
    }

    public PageResponse<Course> listByLevel(String level, int page, int size) {
        Page<Course> result = courseRepository.findByLevelAndIsPublishedTrue(level, PageRequest.of(page, size));
        return PageResponse.of(result.getContent(), result.getTotalElements(), page, size);
    }

    public Course getCourse(Long id) {
        return courseRepository.findById(id)
                .orElseThrow(() -> QooCommunityException.notFound("Course not found: " + id));
    }

    public List<Lesson> getLessons(Long courseId) {
        return lessonRepository.findByCourseIdOrderBySortOrderAsc(courseId);
    }

    public Lesson getLesson(Long courseId, Long lessonId) {
        return lessonRepository.findById(lessonId)
                .orElseThrow(() -> QooCommunityException.notFound("Lesson not found"));
    }

    @Transactional
    public Enrollment enroll(String userId, Long courseId) {
        if (!courseRepository.existsById(courseId)) {
            throw QooCommunityException.notFound("Course not found");
        }
        if (enrollmentRepository.findByUserIdAndCourseId(userId, courseId).isPresent()) {
            throw QooCommunityException.badRequest("Already enrolled");
        }
        Enrollment enrollment = new Enrollment();
        enrollment.setUserId(userId);
        enrollment.setCourseId(courseId);
        Enrollment saved = enrollmentRepository.save(enrollment);

        courseRepository.findById(courseId).ifPresent(c -> {
            c.setEnrolledCount((int) enrollmentRepository.countByCourseId(courseId));
            courseRepository.save(c);
        });

        return saved;
    }

    @Transactional
    public void updateProgress(String userId, Long courseId, int progressPct) {
        Enrollment enrollment = enrollmentRepository.findByUserIdAndCourseId(userId, courseId)
                .orElseThrow(() -> QooCommunityException.notFound("Not enrolled"));
        enrollment.setProgressPct(progressPct);
        enrollment.setUpdatedAt(LocalDateTime.now());
        if (progressPct >= 100) {
            enrollment.setCompletedAt(LocalDateTime.now());
        }
        enrollmentRepository.save(enrollment);
    }

    public List<Enrollment> getMyCourses(String userId) {
        return enrollmentRepository.findByUserIdOrderByUpdatedAtDesc(userId);
    }

    // ---- Certifications ----

    public List<Certification> listCertifications() {
        return certificationRepository.findByIsActiveTrue();
    }

    @Transactional
    public UserCertification takeExam(String userId, Long certId, int score) {
        Certification cert = certificationRepository.findById(certId)
                .orElseThrow(() -> QooCommunityException.notFound("Certification not found"));
        boolean passed = score >= cert.getPassScore();
        UserCertification uc = new UserCertification();
        uc.setUserId(userId);
        uc.setCertificationId(certId);
        uc.setScore(score);
        uc.setPassed(passed);
        if (passed) {
            uc.setExpiresAt(LocalDateTime.now().plusMonths(cert.getValidityMonths()));
        }
        return userCertificationRepository.save(uc);
    }

    public List<UserCertification> getMyCertifications(String userId) {
        return userCertificationRepository.findByUserId(userId);
    }
}
