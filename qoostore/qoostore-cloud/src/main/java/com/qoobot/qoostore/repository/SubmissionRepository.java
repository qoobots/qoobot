package com.qoobot.qoostore.repository;

import com.qoobot.qoostore.entity.Submission;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import java.util.List;
import java.util.Optional;

@Repository
public interface SubmissionRepository extends JpaRepository<Submission, Long> {
    Optional<Submission> findByVersionId(Long versionId);
    List<Submission> findByStatusOrderByCreatedAtAsc(String status);
    Page<Submission> findByStatus(String status, Pageable pageable);
    long countByStatus(String status);
}
