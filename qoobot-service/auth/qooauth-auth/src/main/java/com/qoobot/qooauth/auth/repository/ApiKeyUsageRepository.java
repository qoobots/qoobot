package com.qoobot.qooauth.auth.repository;

import com.qoobot.qooauth.auth.entity.ApiKeyUsage;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.time.Instant;
import java.util.List;

@Repository
public interface ApiKeyUsageRepository extends JpaRepository<ApiKeyUsage, String> {

    Page<ApiKeyUsage> findByKeyIdOrderByCreatedAtDesc(String keyId, Pageable pageable);

    List<ApiKeyUsage> findByKeyIdAndCreatedAtAfter(String keyId, Instant since);

    long countByKeyIdAndCreatedAtAfter(String keyId, Instant since);
}
