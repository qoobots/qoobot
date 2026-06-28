package com.qoobot.qooauth.auth.repository;

import com.qoobot.qooauth.auth.entity.DeviceCertificate;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.Instant;
import java.util.List;
import java.util.Optional;

@Repository
public interface DeviceCertificateRepository extends JpaRepository<DeviceCertificate, String> {

    List<DeviceCertificate> findByUserId(String userId);

    List<DeviceCertificate> findByDeviceId(String deviceId);

    Optional<DeviceCertificate> findBySerialNumber(String serialNumber);

    Optional<DeviceCertificate> findByFingerprintSha256(String fingerprint);

    List<DeviceCertificate> findByState(String state);

    @Query("SELECT c FROM DeviceCertificate c WHERE c.state = 'ACTIVE' AND c.autoRenew = true AND c.notAfter <= :renewDeadline")
    List<DeviceCertificate> findCertificatesDueForRenewal(@Param("renewDeadline") Instant renewDeadline);

    long countByDeviceIdAndState(String deviceId, String state);

    @Modifying
    @Query("UPDATE DeviceCertificate c SET c.state = 'EXPIRED' WHERE c.state = 'ACTIVE' AND c.notAfter <= :now")
    int expireOverdueCertificates(@Param("now") Instant now);
}
