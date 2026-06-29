package com.qoobot.qoocompliance.repository;

import com.qoobot.qoocompliance.domain.ComplianceReview;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface ComplianceReviewRepository extends JpaRepository<ComplianceReview, Long> {

    List<ComplianceReview> findByProductId(String productId);

    List<ComplianceReview> findByReviewType(String reviewType);

    List<ComplianceReview> findByStatus(String status);

    List<ComplianceReview> findByReviewerId(String reviewerId);

    List<ComplianceReview> findByProductIdAndStatus(String productId, String status);

    List<ComplianceReview> findByProductIdAndReviewType(String productId, String reviewType);
}
