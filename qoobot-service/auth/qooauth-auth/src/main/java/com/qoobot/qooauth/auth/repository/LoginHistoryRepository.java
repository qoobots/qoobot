package com.qoobot.qooauth.auth.repository;

import com.qoobot.qooauth.auth.entity.LoginHistory;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.time.Instant;
import java.util.List;

@Repository
public interface LoginHistoryRepository extends JpaRepository<LoginHistory, String> {

    Page<LoginHistory> findByUserIdOrderByCreatedAtDesc(String userId, Pageable pageable);

    List<LoginHistory> findByUserIdAndCreatedAtAfter(String userId, Instant after);

    long countByUserIdAndSuccess(String userId, boolean success);

    List<LoginHistory> findByIpAddressAndSuccessFalseAndCreatedAtAfter(String ipAddress, Instant after);
}
