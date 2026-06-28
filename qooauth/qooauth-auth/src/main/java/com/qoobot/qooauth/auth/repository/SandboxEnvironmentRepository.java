package com.qoobot.qooauth.auth.repository;

import com.qoobot.qooauth.auth.entity.SandboxEnvironment;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.Instant;
import java.util.List;
import java.util.Optional;

@Repository
public interface SandboxEnvironmentRepository extends JpaRepository<SandboxEnvironment, String> {

    List<SandboxEnvironment> findByUserId(String userId);

    List<SandboxEnvironment> findByUserIdAndState(String userId, String state);

    Optional<SandboxEnvironment> findByEnvIdAndUserId(String envId, String userId);

    @Query("SELECT s FROM SandboxEnvironment s WHERE s.state = 'ACTIVE' AND s.expiresAt < :now")
    List<SandboxEnvironment> findExpiredActive(@Param("now") Instant now);

    @Query("SELECT COUNT(s) FROM SandboxEnvironment s WHERE s.userId = :userId AND s.state = 'ACTIVE'")
    long countActiveByUser(@Param("userId") String userId);

    @Modifying
    @Query("UPDATE SandboxEnvironment s SET s.state = 'EXPIRED', s.updatedAt = CURRENT_TIMESTAMP WHERE s.state = 'ACTIVE' AND s.expiresAt < :now")
    int expireEnvironments(@Param("now") Instant now);
}
