package com.qoobot.qoocompliance.repository;

import com.qoobot.qoocompliance.domain.CertificationProgress;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface CertificationProgressRepository extends JpaRepository<CertificationProgress, Long> {

    List<CertificationProgress> findByProductId(String productId);

    List<CertificationProgress> findByMarket(String market);

    List<CertificationProgress> findByStatus(String status);

    List<CertificationProgress> findByProductIdAndMarket(String productId, String market);

    Optional<CertificationProgress> findByCertNumber(String certNumber);

    List<CertificationProgress> findByProductIdAndStatus(String productId, String status);
}
