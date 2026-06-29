package com.qoobot.qooauth.device.repository;

import com.qoobot.qooauth.device.entity.Certificate;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.OffsetDateTime;
import java.util.List;
import java.util.Optional;

/**
 * Spring Data JPA repository for {@link Certificate} entities.
 */
@Repository
public interface CertificateRepository extends JpaRepository<Certificate, Long> {

    /**
     * Find a certificate by its unique serial number.
     */
    Optional<Certificate> findBySerialNumber(String serialNumber);

    /**
     * Find all certificates issued to a specific device.
     */
    List<Certificate> findByDeviceId(String deviceId);

    /**
     * Find certificates by their state (ACTIVE / REVOKED / EXPIRED).
     */
    List<Certificate> findByState(String state);

    /**
     * Find the active certificate for a device.
     */
    @Query("SELECT c FROM Certificate c WHERE c.deviceId = :deviceId AND c.state = 'ACTIVE'")
    Optional<Certificate> findActiveByDeviceId(@Param("deviceId") String deviceId);

    /**
     * Find all currently valid (ACTIVE and within validity window) certificates.
     */
    @Query("SELECT c FROM Certificate c WHERE c.state = 'ACTIVE' AND c.notBefore <= :now AND c.notAfter >= :now")
    List<Certificate> findAllValid(@Param("now") OffsetDateTime now);

    /**
     * Find all certificates that have expired but are still marked ACTIVE.
     */
    @Query("SELECT c FROM Certificate c WHERE c.state = 'ACTIVE' AND c.notAfter < :now")
    List<Certificate> findExpiredButActive(@Param("now") OffsetDateTime now);

    /**
     * Revoke a certificate by its serial number.
     */
    @Modifying
    @Query("UPDATE Certificate c SET c.state = 'REVOKED', c.revokedAt = :now, c.revocationReason = :reason WHERE c.serialNumber = :serial")
    int revokeBySerialNumber(@Param("serial") String serialNumber, @Param("now") OffsetDateTime now, @Param("reason") String reason);

    /**
     * Count active certificates for a device.
     */
    long countByDeviceIdAndState(String deviceId, String state);

    /**
     * Check whether a serial number already exists.
     */
    boolean existsBySerialNumber(String serialNumber);

    /**
     * Find by SHA-256 fingerprint.
     */
    Optional<Certificate> findBySha256Fingerprint(String sha256Fingerprint);
}
