package com.qoobot.qoogear.cert.repository;

import com.qoobot.qoogear.cert.domain.Certificate;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;
import java.time.ZonedDateTime;
import java.util.List;
import java.util.Optional;

@Repository
public interface CertificateRepository extends JpaRepository<Certificate, Long> {
    Optional<Certificate> findByCertNumber(String certNumber);
    Optional<Certificate> findByApplicationId(Long applicationId);
    Page<Certificate> findByDeveloperId(Long developerId, Pageable pageable);
    List<Certificate> findByProductCategory(String productCategory);

    @Query("SELECT c FROM Certificate c WHERE c.revokedAt IS NULL AND c.expiresAt > :now")
    Page<Certificate> findActiveCertificates(@Param("now") ZonedDateTime now, Pageable pageable);

    @Query("SELECT c FROM Certificate c WHERE c.revokedAt IS NULL AND c.expiresAt BETWEEN :now AND :soon")
    List<Certificate> findExpiringSoon(@Param("now") ZonedDateTime now, @Param("soon") ZonedDateTime soon);

    long countByRevokedAtIsNull();
}
