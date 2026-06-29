package com.qoobot.qoostore.service;

import com.qoobot.qoostore.entity.*;
import com.qoobot.qoostore.repository.*;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;
import java.util.UUID;

@Slf4j
@Service
@RequiredArgsConstructor
public class ReviewService {

    private final SubmissionRepository submissionRepository;
    private final SkillVersionRepository versionRepository;
    private final SkillRepository skillRepository;

    public Page<Submission> getPendingSubmissions(int page, int size) {
        Pageable pageable = PageRequest.of(page, size);
        return submissionRepository.findByStatus("pending", pageable);
    }

    public Submission getSubmissionDetail(Long submissionId) {
        return submissionRepository.findById(submissionId)
                .orElseThrow(() -> new RuntimeException("Submission not found: " + submissionId));
    }

    @Transactional
    public void approveSubmission(Long submissionId, UUID reviewerId) {
        Submission submission = submissionRepository.findById(submissionId)
                .orElseThrow(() -> new RuntimeException("Submission not found: " + submissionId));

        submission.setStatus("approved");
        submission.setReviewerId(reviewerId);
        submission.setReviewedAt(LocalDateTime.now());
        submissionRepository.save(submission);

        SkillVersion version = versionRepository.findById(submission.getVersionId())
                .orElseThrow(() -> new RuntimeException("Version not found"));
        version.setStatus("approved");
        versionRepository.save(version);

        Skill skill = skillRepository.findById(version.getSkillId())
                .orElseThrow(() -> new RuntimeException("Skill not found"));
        skill.setStatus("published");
        skill.setPublishedAt(LocalDateTime.now());
        skillRepository.save(skill);

        log.info("Submission approved: submissionId={}, skillId={}, reviewerId={}",
                submissionId, skill.getSkillId(), reviewerId);
    }

    @Transactional
    public void rejectSubmission(Long submissionId, UUID reviewerId, String reason) {
        Submission submission = submissionRepository.findById(submissionId)
                .orElseThrow(() -> new RuntimeException("Submission not found: " + submissionId));

        submission.setStatus("rejected");
        submission.setReviewerId(reviewerId);
        submission.setRejectReason(reason);
        submission.setReviewedAt(LocalDateTime.now());
        submissionRepository.save(submission);

        SkillVersion version = versionRepository.findById(submission.getVersionId())
                .orElseThrow(() -> new RuntimeException("Version not found"));
        version.setStatus("rejected");
        versionRepository.save(version);

        log.info("Submission rejected: submissionId={}, reason={}", submissionId, reason);
    }

    public long getPendingCount() {
        return submissionRepository.countByStatus("pending");
    }
}
