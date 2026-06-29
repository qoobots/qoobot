package com.qoobot.qooauth.auth.repository;

import com.qoobot.qooauth.auth.entity.DeveloperCertificate;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface DeveloperCertificateRepository extends JpaRepository<DeveloperCertificate, String> {

    List<DeveloperCertificate> findByUserId(String userId);

    List<DeveloperCertificate> findByUserIdAndState(String userId, String state);

    Optional<DeveloperCertificate> findBySerialNumber(String serialNumber);

    Optional<DeveloperCertificate> findByFingerprintSha256(String fingerprintSha256);

    @Query("SELECT c FROM DeveloperCertificate c WHERE c.userId = :userId AND c.certType = :certType AND c.state = 'ACTIVE'")
    List<DeveloperCertificate> findActiveByType(@Param("userId") String userId, @Param("certType") String certType);

    @Modifying
    @Query("UPDATE DeveloperCertificate c SET c.state = 'REVOKED', c.revokedAt = CURRENT_TIMESTAMP, c.revokeReason = :reason WHERE c.certId = :certId")
    void revokeCertificate(@Param("certId") String certId, @Param("reason") String reason);
}
