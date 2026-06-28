package com.qoobot.qooauth.audit.repository;

import com.qoobot.qooauth.audit.entity.AuditIntegrityChain;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.Instant;
import java.util.List;
import java.util.Optional;

@Repository
public interface AuditIntegrityChainRepository extends JpaRepository<AuditIntegrityChain, Long> {

    Optional<AuditIntegrityChain> findByBucketStartAndBucketEnd(Instant bucketStart, Instant bucketEnd);

    @Query("SELECT a FROM AuditIntegrityChain a WHERE a.bucketEnd = :bucketEnd ORDER BY a.bucketStart ASC")
    List<AuditIntegrityChain> findChainUpTo(@Param("bucketEnd") Instant bucketEnd);

    @Query("SELECT a FROM AuditIntegrityChain a WHERE a.bucketStart >= :start AND a.bucketEnd <= :end " +
           "ORDER BY a.bucketStart ASC")
    List<AuditIntegrityChain> findChainInRange(@Param("start") Instant start, @Param("end") Instant end);

    Optional<AuditIntegrityChain> findTopByOrderByBucketEndDesc();

    List<AuditIntegrityChain> findByVerifiedAtIsNullOrderByBucketStartAsc();
}
